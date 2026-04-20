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

    # Equations come from the shared lowering helper used by flatten.
    equations = lower_reactions_to_equations(rxn_sys.reactions, rxn_sys.species)

    # Handle subsystems recursively
    subsystems = Dict{String,Model}()
    for (name, subsys) in rxn_sys.subsystems
        subsystems[name] = derive_odes(subsys)
    end

    return Model(variables, equations, subsystems=subsystems)
end

"""
    stoichiometric_matrix(rxn_sys::ReactionSystem) -> Matrix{Float64}

Compute the net stoichiometric matrix (species × reactions).

The stoichiometric matrix S has dimensions (n_species × n_reactions) where:
- S[i,j] = net stoichiometry of species i in reaction j
- Net stoichiometry = products - reactants
- Positive values indicate production, negative values indicate consumption

Values are `Float64` because v0.2.x allows fractional stoichiometries
(e.g. `ISOP+O3 → 0.87 CH2O`). Integer-only systems produce a matrix whose
entries happen to be exact integers stored as `Float64`.

# Arguments
- `rxn_sys::ReactionSystem`: Input reaction system

# Returns
- `Matrix{Float64}`: Stoichiometric matrix with dimensions (n_species, n_reactions)

# Examples
```julia
# For reaction A + B -> 2C:
# S = [-1  # A consumed
#      -1  # B consumed
#       2] # C produced (2 molecules)
```
"""
function stoichiometric_matrix(rxn_sys::ReactionSystem)::Matrix{Float64}
    n_species = length(rxn_sys.species)
    n_reactions = length(rxn_sys.reactions)

    # Create species name to index mapping
    species_idx = Dict(species.name => i for (i, species) in enumerate(rxn_sys.species))

    # Initialize stoichiometric matrix
    S = zeros(Float64, n_species, n_reactions)

    for (j, reaction) in enumerate(rxn_sys.reactions)
        # Use getfield to bypass the backward-compat getproperty overrides that
        # would convert :products into a Dict of Pairs — StoichiometryEntry has
        # .species/.stoichiometry and does not match the Pair API.
        substrates = getfield(reaction, :substrates)
        if substrates !== nothing
            for entry in substrates
                if haskey(species_idx, entry.species)
                    i = species_idx[entry.species]
                    S[i, j] -= entry.stoichiometry
                end
            end
        end

        products = getfield(reaction, :products)
        if products !== nothing
            for entry in products
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

Uses standard mass action kinetics: `rate = k * ∏[reactants]^stoichiometry`.

`reaction.rate` is treated as the **rate coefficient** (e.g. `k` or a
temperature-dependent Arrhenius expression). If it already references any
substrate concentration, this function assumes the user supplied a full rate
law and returns it unchanged — otherwise it multiplies the coefficient by
`∏[substrate]^stoich` to form the full rate law. This detect-and-skip behavior
matches `enhance_rate_with_mass_action` in `earthsci-toolkit-rs` for
cross-language parity.

Handles special cases:
- Source reactions (no substrates): `rate = k` (no multiplication).
- Rate already contains substrate variables: returned as-is to avoid
  double-applying mass action (would produce `k*A²*B²` instead of `k*A*B`).

# Arguments
- `reaction::Reaction`: The reaction to compute the rate for
- `species::Vector{Species}`: All species in the system (unused by this
  helper; retained for API stability and future validation)

# Returns
- `Expr`: Mass action rate expression

# Examples
```julia
# For reaction A + B -> C with rate="k":
# Returns: k * A * B
#
# For reaction A + B -> C with rate="k*A*B" (already a full rate law):
# Returns: k * A * B  (unchanged — detected that A and B are already present)
#
# For source reaction -> A with rate="k":
# Returns: k
```
"""
function mass_action_rate(reaction::Reaction, species::Vector{Species})::EarthSciSerialization.Expr
    rate_expr = reaction.rate

    # Source reactions (no substrates): the rate expression IS the full rate.
    if reaction.substrates === nothing || isempty(reaction.substrates)
        return rate_expr
    end

    # Detect whether the user-supplied rate already references any substrate
    # concentration. If it does, they gave us a full rate law — do not
    # double-apply mass action (would yield `k*A²*B²` for `rate=k*A*B`).
    if any(entry -> _expr_contains_var(rate_expr, entry.species),
           reaction.substrates)
        return rate_expr
    end

    # Otherwise multiply the rate coefficient by ∏[substrate]^stoich.
    mass_action_terms = EarthSciSerialization.Expr[rate_expr]
    for entry in reaction.substrates
        species_expr = VarExpr(entry.species)
        if entry.stoichiometry == 1
            push!(mass_action_terms, species_expr)
        else
            exponent_expr = isinteger(entry.stoichiometry) ?
                IntExpr(Int64(entry.stoichiometry)) :
                NumExpr(entry.stoichiometry)
            push!(mass_action_terms, OpExpr("^",
                EarthSciSerialization.Expr[species_expr, exponent_expr]))
        end
    end

    return length(mass_action_terms) == 1 ? mass_action_terms[1] :
           OpExpr("*", mass_action_terms)
end

"""
    _expr_contains_var(expr, name) -> Bool

True if the Expr tree `expr` contains a `VarExpr` whose `name` matches.
Recurses through `OpExpr` args; `NumExpr` always returns `false`.
"""
function _expr_contains_var(expr::EarthSciSerialization.Expr, name::String)::Bool
    if expr isa VarExpr
        return expr.name == name
    elseif expr isa OpExpr
        return any(a -> _expr_contains_var(a, name), expr.args)
    end
    return false
end