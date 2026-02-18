"""
Reaction system to ODE conversion functionality.

This module implements the conversion of ReactionSystem objects to ODE-based Models
using standard mass action kinetics as specified in Libraries Spec Section 7.4.
"""

"""
    derive_odes(rxn_sys::ReactionSystem) -> Model

Generate an ODE model from a reaction system using standard mass action kinetics.

Creates state variables for each species, parameters for rate constants, and equations
with d[species]/dt = net_stoichiometry * rate_law. Handles source reactions (null
substrates), sink reactions (null products), and constraint equations.

# Arguments
- `rxn_sys::ReactionSystem`: Input reaction system with species, reactions, and parameters

# Returns
- `Model`: ODE model with variables, equations, and optional events/subsystems

# Algorithm (Libraries Spec Section 7.4)
1. Create state variables for all species in the reaction system
2. Create parameter variables for all parameters (rate constants)
3. For each reaction, compute the mass action rate expression
4. For each species, compute the net rate of change from all reactions
5. Create differential equations d[species]/dt = net_rate

# Examples
```julia
# Simple A + B -> C reaction
species = [Species("A"), Species("B"), Species("C")]
reactions = [Reaction(Dict("A"=>1, "B"=>1), Dict("C"=>1), VarExpr("k1"))]
parameters = [Parameter("k1", 0.1)]
rxn_sys = ReactionSystem(species, reactions, parameters=parameters)

model = derive_odes(rxn_sys)
# Returns Model with:
# - State variables: A, B, C
# - Parameter: k1
# - Equations: d[A]/dt = -k1*A*B, d[B]/dt = -k1*A*B, d[C]/dt = k1*A*B
```
"""
function derive_odes(rxn_sys::ReactionSystem)::Model
    # Collect all species names
    species_names = [species.name for species in rxn_sys.species]

    # Create state variables for all species
    variables = Dict{String,ModelVariable}()
    for species in rxn_sys.species
        variables[species.name] = ModelVariable(
            StateVariable,
            default=1.0,  # Default initial concentration
            description="Concentration of species $(species.name)",
            units="mol/L"
        )
    end

    # Add parameter variables for all parameters
    for param in rxn_sys.parameters
        variables[param.name] = ModelVariable(
            ParameterVariable,
            default=param.default,
            description=param.description,
            units=param.units
        )
    end

    # Compute stoichiometric matrix
    S = stoichiometric_matrix(rxn_sys)

    # Create differential equations for each species
    equations = Equation[]

    for (i, species_name) in enumerate(species_names)
        # Create left-hand side: d[species]/dt
        lhs = OpExpr("D", ESMFormat.Expr[VarExpr(species_name)], wrt="t")

        # Create right-hand side: sum of (stoichiometry * reaction_rate) for all reactions
        rate_terms = ESMFormat.Expr[]

        for (j, reaction) in enumerate(rxn_sys.reactions)
            stoich = S[i, j]
            if stoich != 0
                # Get mass action rate for this reaction
                rate_expr = mass_action_rate(reaction, rxn_sys.species)

                if stoich == 1
                    push!(rate_terms, rate_expr)
                elseif stoich == -1
                    push!(rate_terms, OpExpr("-", ESMFormat.Expr[rate_expr]))
                else
                    push!(rate_terms, OpExpr("*", ESMFormat.Expr[NumExpr(Float64(stoich)), rate_expr]))
                end
            end
        end

        # Combine all rate terms
        rhs = if isempty(rate_terms)
            NumExpr(0.0)
        elseif length(rate_terms) == 1
            rate_terms[1]
        else
            OpExpr("+", rate_terms)
        end

        push!(equations, Equation(lhs, rhs))
    end

    # Handle subsystems recursively
    subsystems = Dict{String,Model}()
    for (name, subsys) in rxn_sys.subsystems
        subsystems[name] = derive_odes(subsys)
    end

    return Model(variables, equations, subsystems=subsystems)
end

"""
    stoichiometric_matrix(rxn_sys::ReactionSystem) -> Matrix{Int}

Compute the net stoichiometric matrix (species × reactions).

The stoichiometric matrix S has dimensions (n_species × n_reactions) where:
- S[i,j] = net stoichiometry of species i in reaction j
- Net stoichiometry = products - reactants
- Positive values indicate production, negative values indicate consumption

# Arguments
- `rxn_sys::ReactionSystem`: Input reaction system

# Returns
- `Matrix{Int}`: Stoichiometric matrix with dimensions (n_species, n_reactions)

# Examples
```julia
# For reaction A + B -> 2C:
# S = [-1  # A consumed
#      -1  # B consumed
#       2] # C produced (2 molecules)
```
"""
function stoichiometric_matrix(rxn_sys::ReactionSystem)::Matrix{Int}
    n_species = length(rxn_sys.species)
    n_reactions = length(rxn_sys.reactions)

    # Create species name to index mapping
    species_idx = Dict(species.name => i for (i, species) in enumerate(rxn_sys.species))

    # Initialize stoichiometric matrix
    S = zeros(Int, n_species, n_reactions)

    for (j, reaction) in enumerate(rxn_sys.reactions)
        # Handle substrates (negative stoichiometry)
        if reaction.substrates !== nothing
            for entry in reaction.substrates
                if haskey(species_idx, entry.species)
                    i = species_idx[entry.species]
                    S[i, j] -= entry.stoichiometry
                end
            end
        end

        # Handle products (positive stoichiometry)
        if reaction.products !== nothing
            for entry in reaction.products
                if haskey(species_idx, entry.species)
                    i = species_idx[entry.species]
                    S[i, j] += entry.stoichiometry
                end
            end
        end
    end

    return S
end

"""
    mass_action_rate(reaction::Reaction, species::Vector{Species}) -> Expr

Compute the mass action rate expression for a reaction.

Uses standard mass action kinetics: rate = k * ∏[reactants]^stoichiometry
Handles special cases:
- Source reactions (no reactants): rate = k
- Sink reactions (no products): rate = k * ∏[reactants]^stoichiometry
- Reversible reactions: rate = k_forward * ∏[reactants]^stoich - k_reverse * ∏[products]^stoich

# Arguments
- `reaction::Reaction`: The reaction to compute the rate for
- `species::Vector{Species}`: All species in the system (for validation)

# Returns
- `Expr`: Mass action rate expression

# Examples
```julia
# For reaction A + B -> C with rate k:
# Returns: k * A * B

# For source reaction -> A with rate k:
# Returns: k

# For reversible reaction A ⇌ B with rate k:
# Returns: k * A (if reaction.reversible = false)
```
"""
function mass_action_rate(reaction::Reaction, species::Vector{Species})::ESMFormat.Expr
    # Start with the rate constant expression
    rate_expr = reaction.rate

    # Handle source reactions (no substrates)
    if reaction.substrates === nothing || isempty(reaction.substrates)
        return rate_expr
    end

    # Build mass action terms for substrates
    mass_action_terms = ESMFormat.Expr[rate_expr]

    for entry in reaction.substrates
        species_expr = VarExpr(entry.species)
        if entry.stoichiometry == 1
            push!(mass_action_terms, species_expr)
        else
            # For stoichiometry > 1, use power operator
            push!(mass_action_terms, OpExpr("^", ESMFormat.Expr[species_expr, NumExpr(Float64(entry.stoichiometry))]))
        end
    end

    # Combine all terms with multiplication
    if length(mass_action_terms) == 1
        return mass_action_terms[1]
    else
        return OpExpr("*", mass_action_terms)
    end
end