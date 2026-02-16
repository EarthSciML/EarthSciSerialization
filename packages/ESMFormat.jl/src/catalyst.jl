"""
ESM to Catalyst.jl Conversion Module.

This module implements conversion from ESM ReactionSystem format to Catalyst.jl
ReactionSystem objects. It provides the core functionality needed for Julia-based
chemical kinetics modeling with ESM format data.

KEY FEATURES:
- Species mapping: ESM Species → @species declarations
- Parameter conversion: ESM Parameter → @parameters declarations
- Reaction conversion: ESM Reaction → Catalyst.Reaction objects
- Rate expression conversion through symbolic translation
- Support for constraint equations as additional equations
- Event system support (when available)
- Proper handling of null substrates (source reactions) and null products (sink reactions)
"""

# Conditional imports to handle missing dependencies gracefully
const CATALYST_AVAILABLE = Ref(false)
const SYMBOLICS_AVAILABLE = Ref(false)

try
    using Catalyst
    global CATALYST_AVAILABLE[] = true
catch e
    @warn "Catalyst.jl not available, using mock implementation: $e"
end

try
    using Symbolics
    global SYMBOLICS_AVAILABLE[] = true
catch e
    @warn "Symbolics.jl not available, using mock implementation: $e"
end

"""
    to_catalyst_system(rs::ReactionSystem)::Union{ReactionSystem, MockCatalystSystem}

Convert an ESM ReactionSystem to a Catalyst.jl ReactionSystem.

This function implements the ESM → Catalyst system conversion task by:
1. Mapping ESM species to @species declarations
2. Converting ESM parameters to @parameters declarations
3. Translating ESM reactions to Reaction() objects
4. Handling null substrates for source reactions (no reactants)
5. Handling null products for sink reactions (no products)
6. Converting rate expressions via symbolic expression mapping
7. Processing constraint_equations as additional equations (if present)
8. Copying events (if present in the ReactionSystem)

# Arguments
- `rs::ReactionSystem`: ESM ReactionSystem to convert

# Returns
- `Union{ReactionSystem, MockCatalystSystem}`: Catalyst ReactionSystem or mock equivalent

# Examples
```julia
# Simple A → B reaction
species = [Species("A"), Species("B")]
parameters = [Parameter("k", 0.1)]
reactions = [Reaction(Dict("A" => 1), Dict("B" => 1), VarExpr("k"))]
rs = ReactionSystem(species, reactions; parameters=parameters)

catalyst_sys = to_catalyst_system(rs)
```

# Error Handling
- Gracefully falls back to mock implementation if Catalyst.jl unavailable
- Warns about unsupported features but continues processing
- Validates species and parameter references in reactions
"""
function to_catalyst_system(rs::ReactionSystem)
    if !CATALYST_AVAILABLE[]
        @info "Using mock Catalyst system (Catalyst.jl not available)"
        return create_mock_catalyst_system(rs)
    end

    try
        return create_real_catalyst_system(rs)
    catch e
        @warn "Failed to create real Catalyst system, using mock: $e"
        return create_mock_catalyst_system(rs)
    end
end

"""
    create_real_catalyst_system(rs::ReactionSystem) -> ReactionSystem

Create a real Catalyst.jl ReactionSystem from an ESM ReactionSystem.
Handles the full conversion pipeline with proper symbolic mathematics.
"""
function create_real_catalyst_system(rs::ReactionSystem)
    # Independent time variable
    t = Symbolics.variable(:t, T=Symbolics.Real)

    # Convert species to @species declarations
    species_symbols = []
    species_dict = Dict{String, Any}()

    for species in rs.species
        # Create symbolic species variable
        spec_sym = Symbolics.variable(Symbol(species.name), T=Symbolics.Real)
        push!(species_symbols, spec_sym)
        species_dict[species.name] = spec_sym
    end

    # Convert parameters to @parameters declarations
    parameter_symbols = []
    param_dict = Dict{String, Any}()

    for param in rs.parameters
        # Create symbolic parameter
        param_sym = Symbolics.variable(Symbol(param.name), T=Symbolics.Real)
        push!(parameter_symbols, param_sym)
        param_dict[param.name] = param_sym
    end

    # Convert reactions to Reaction() objects
    catalyst_reactions = []
    all_vars = merge(species_dict, param_dict)

    for (i, esm_reaction) in enumerate(rs.reactions)
        try
            # Handle substrates (reactants)
            reactants = []
            reactant_stoich = []

            if !isempty(esm_reaction.reactants)
                for (species_name, stoich) in esm_reaction.reactants
                    if haskey(species_dict, species_name)
                        push!(reactants, species_dict[species_name])
                        push!(reactant_stoich, stoich)
                    else
                        @warn "Species '$species_name' not found in species list for reaction $i"
                    end
                end
            end

            # Handle products
            products = []
            product_stoich = []

            if !isempty(esm_reaction.products)
                for (species_name, stoich) in esm_reaction.products
                    if haskey(species_dict, species_name)
                        push!(products, species_dict[species_name])
                        push!(product_stoich, stoich)
                    else
                        @warn "Species '$species_name' not found in species list for reaction $i"
                    end
                end
            end

            # Convert rate expression via expression mapping
            rate_expr = esm_to_symbolic(esm_reaction.rate, all_vars)

            # Create Catalyst Reaction object with proper handling of null cases
            catalyst_reaction = if isempty(reactants) && !isempty(products)
                # Source reaction: null substrates → products
                Reaction(rate_expr, nothing, products, nothing, product_stoich)
            elseif !isempty(reactants) && isempty(products)
                # Sink reaction: reactants → null products
                Reaction(rate_expr, reactants, nothing, reactant_stoich, nothing)
            elseif !isempty(reactants) && !isempty(products)
                # Normal reaction: reactants → products
                Reaction(rate_expr, reactants, products, reactant_stoich, product_stoich)
            else
                # Edge case: null → null (should probably warn)
                @warn "Reaction $i has no reactants or products - skipping"
                continue
            end

            push!(catalyst_reactions, catalyst_reaction)

        catch e
            @warn "Failed to convert reaction $i: $e"
        end
    end

    # Handle constraint equations as additional equations (if present)
    # Note: This is a placeholder - ReactionSystem type may not have constraint_equations field
    # We would add this functionality when the ESM spec is extended
    additional_equations = []
    if hasfield(typeof(rs), :constraint_equations)
        constraint_eqs = getfield(rs, :constraint_equations)
        for eq in constraint_eqs
            try
                lhs_symbolic = esm_to_symbolic(eq.lhs, all_vars)
                rhs_symbolic = esm_to_symbolic(eq.rhs, all_vars)
                push!(additional_equations, lhs_symbolic ~ rhs_symbolic)
            catch e
                @warn "Failed to convert constraint equation: $e"
            end
        end
    end

    # Copy events (if present)
    # Note: Current ReactionSystem type may not have events field
    events_kwargs = Dict()
    if hasfield(typeof(rs), :events) && !isempty(getfield(rs, :events))
        esm_events = getfield(rs, :events)
        continuous_events, discrete_events = process_reaction_events(esm_events, all_vars)

        if !isempty(continuous_events)
            events_kwargs[:continuous_events] = continuous_events
        end
        if !isempty(discrete_events)
            events_kwargs[:discrete_events] = discrete_events
        end
    end

    # Create the Catalyst ReactionSystem
    catalyst_sys = if isempty(additional_equations) && isempty(events_kwargs)
        # Simple case: just reactions
        Catalyst.ReactionSystem(catalyst_reactions, t, species_symbols, parameter_symbols)
    else
        # Complex case: include additional equations and/or events
        Catalyst.ReactionSystem(catalyst_reactions, t, species_symbols, parameter_symbols;
                               equations=additional_equations, events_kwargs...)
    end

    return catalyst_sys
end

"""
    create_mock_catalyst_system(rs::ReactionSystem) -> MockCatalystSystem

Create a mock Catalyst system for testing when Catalyst.jl is not available.
Preserves all the structural information in a testable format.
"""
function create_mock_catalyst_system(rs::ReactionSystem)
    species = [spec.name for spec in rs.species]
    parameters = [param.name for param in rs.parameters]

    # Convert reactions to string representations
    reactions = String[]
    for (i, rxn) in enumerate(rs.reactions)
        reactant_str = if isempty(rxn.reactants)
            "∅"  # null reactants (source)
        else
            join([stoich > 1 ? "$stoich $(spec)" : spec
                  for (spec, stoich) in rxn.reactants], " + ")
        end

        product_str = if isempty(rxn.products)
            "∅"  # null products (sink)
        else
            join([stoich > 1 ? "$stoich $(spec)" : spec
                  for (spec, stoich) in rxn.products], " + ")
        end

        rate_str = expr_to_string(rxn.rate)
        arrow = rxn.reversible ? " ⇌ " : " → "

        reaction_desc = "$reactant_str$arrow$product_str, rate: $rate_str"
        push!(reactions, reaction_desc)
    end

    # Handle events if present
    events = String[]
    if hasfield(typeof(rs), :events)
        esm_events = getfield(rs, :events)
        for (i, event) in enumerate(esm_events)
            if event isa ContinuousEvent
                push!(events, "continuous_event_$i")
            elseif event isa DiscreteEvent
                push!(events, "discrete_event_$i")
            else
                push!(events, "unknown_event_$i")
            end
        end
    end

    # Handle constraint equations if present
    constraints = String[]
    if hasfield(typeof(rs), :constraint_equations)
        constraint_eqs = getfield(rs, :constraint_equations)
        for (i, eq) in enumerate(constraint_eqs)
            lhs_str = expr_to_string(eq.lhs)
            rhs_str = expr_to_string(eq.rhs)
            push!(constraints, "constraint_$i: $lhs_str = $rhs_str")
        end
    end

    metadata = Dict{String, Any}(
        "creation_time" => string(Dates.now()),
        "species_count" => length(species),
        "parameters_count" => length(parameters),
        "reactions_count" => length(reactions),
        "events_count" => length(events),
        "constraints_count" => length(constraints),
        "mock_system" => true
    )

    return MockCatalystSystem("ESM_ReactionSystem", species, parameters, reactions,
                             events, constraints, metadata)
end

"""
    MockCatalystSystem

Mock Catalyst system for testing and fallback when Catalyst.jl is unavailable.
Preserves all structural information from the ESM ReactionSystem.
"""
struct MockCatalystSystem
    name::String
    species::Vector{String}
    parameters::Vector{String}
    reactions::Vector{String}
    events::Vector{String}
    constraints::Vector{String}  # Additional field for constraint equations
    metadata::Dict{String, Any}
end

"""
    esm_to_symbolic(expr::Expr, var_dict::Dict) -> Any

Convert ESM expression to symbolic form for Catalyst.jl.
Handles the expression mapping required for rate expressions.
"""
function esm_to_symbolic(expr::Expr, var_dict::Dict)
    if expr isa NumExpr
        return expr.value
    elseif expr isa VarExpr
        if haskey(var_dict, expr.name)
            return var_dict[expr.name]
        else
            # Create new symbolic variable if not found
            if SYMBOLICS_AVAILABLE[]
                var_sym = Symbolics.variable(Symbol(expr.name), T=Symbolics.Real)
                var_dict[expr.name] = var_sym  # Cache for future use
                return var_sym
            else
                return Symbol(expr.name)  # Fallback for mock system
            end
        end
    elseif expr isa OpExpr
        # Convert arguments recursively
        args = [esm_to_symbolic(arg, var_dict) for arg in expr.args]

        # Handle different operators
        op = expr.op
        if op == "+"
            return SYMBOLICS_AVAILABLE[] ? sum(args) : Expr(:call, :+, args...)
        elseif op == "*"
            return SYMBOLICS_AVAILABLE[] ? prod(args) : Expr(:call, :*, args...)
        elseif op == "-"
            if length(args) == 1
                return SYMBOLICS_AVAILABLE[] ? -args[1] : Expr(:call, :-, args[1])
            else
                return SYMBOLICS_AVAILABLE[] ? args[1] - args[2] : Expr(:call, :-, args[1], args[2])
            end
        elseif op == "/"
            return SYMBOLICS_AVAILABLE[] ? args[1] / args[2] : Expr(:call, :/, args[1], args[2])
        elseif op == "^"
            return SYMBOLICS_AVAILABLE[] ? args[1] ^ args[2] : Expr(:call, :^, args[1], args[2])
        elseif op == "exp"
            return SYMBOLICS_AVAILABLE[] ? exp(args[1]) : Expr(:call, :exp, args[1])
        elseif op == "log"
            return SYMBOLICS_AVAILABLE[] ? log(args[1]) : Expr(:call, :log, args[1])
        elseif op == "sin"
            return SYMBOLICS_AVAILABLE[] ? sin(args[1]) : Expr(:call, :sin, args[1])
        elseif op == "cos"
            return SYMBOLICS_AVAILABLE[] ? cos(args[1]) : Expr(:call, :cos, args[1])
        elseif op == "sqrt"
            return SYMBOLICS_AVAILABLE[] ? sqrt(args[1]) : Expr(:call, :sqrt, args[1])
        elseif op == "abs"
            return SYMBOLICS_AVAILABLE[] ? abs(args[1]) : Expr(:call, :abs, args[1])
        else
            # Generic function call
            func_sym = Symbol(op)
            return SYMBOLICS_AVAILABLE[] ?
                   eval(func_sym)(args...) :
                   Expr(:call, func_sym, args...)
        end
    end

    error("Unknown expression type: $(typeof(expr))")
end

"""
    process_reaction_events(events::Vector, var_dict::Dict) -> (Vector, Vector)

Process ESM events for inclusion in Catalyst ReactionSystem.
Returns (continuous_events, discrete_events).
"""
function process_reaction_events(events::Vector, var_dict::Dict)
    continuous_events = []
    discrete_events = []

    if !CATALYST_AVAILABLE[]
        return continuous_events, discrete_events
    end

    for event in events
        try
            if event isa ContinuousEvent
                # Convert continuous event conditions and affects
                conditions = [esm_to_symbolic(cond, var_dict) for cond in event.conditions]

                affects = []
                for affect in event.affects
                    if affect isa AffectEquation
                        if haskey(var_dict, affect.lhs)
                            target_var = var_dict[affect.lhs]
                            affect_expr = esm_to_symbolic(affect.rhs, var_dict)
                            push!(affects, target_var ~ affect_expr)
                        end
                    end
                end

                # Create Catalyst continuous callback
                if !isempty(conditions) && !isempty(affects)
                    for condition in conditions
                        cb = Catalyst.SymbolicContinuousCallback(condition, affects)
                        push!(continuous_events, cb)
                    end
                end

            elseif event isa DiscreteEvent
                # Convert discrete event triggers and affects
                affects = []
                for affect in event.affects
                    if affect isa FunctionalAffect
                        if haskey(var_dict, affect.target)
                            target_var = var_dict[affect.target]
                            affect_expr = esm_to_symbolic(affect.expression, var_dict)

                            # Apply operation
                            if affect.operation == "set"
                                push!(affects, target_var ~ affect_expr)
                            elseif affect.operation == "add"
                                push!(affects, target_var ~ target_var + affect_expr)
                            elseif affect.operation == "multiply"
                                push!(affects, target_var ~ target_var * affect_expr)
                            end
                        end
                    end
                end

                if event.trigger isa ConditionTrigger
                    condition = esm_to_symbolic(event.trigger.expression, var_dict)
                    cb = Catalyst.SymbolicDiscreteCallback(condition, affects)
                    push!(discrete_events, cb)
                elseif event.trigger isa PeriodicTrigger
                    cb = Catalyst.SymbolicDiscreteCallback(event.trigger.period, affects)
                    push!(discrete_events, cb)
                elseif event.trigger isa PresetTimesTrigger
                    cb = Catalyst.SymbolicDiscreteCallback(event.trigger.times, affects)
                    push!(discrete_events, cb)
                end
            end
        catch e
            @warn "Failed to process event: $e"
        end
    end

    return continuous_events, discrete_events
end

"""
    expr_to_string(expr::Expr) -> String

Convert ESM expression to string representation for mock systems.
"""
function expr_to_string(expr::Expr)
    if expr isa NumExpr
        return string(expr.value)
    elseif expr isa VarExpr
        return expr.name
    elseif expr isa OpExpr
        if expr.op == "D" && expr.wrt !== nothing
            arg_str = join([expr_to_string(arg) for arg in expr.args], ", ")
            return "D($arg_str, $(expr.wrt))"
        else
            args_str = join([expr_to_string(arg) for arg in expr.args], ", ")
            return "$(expr.op)($args_str)"
        end
    else
        return string(expr)
    end
end

# Import necessary modules conditionally
if !isdefined(Main, :Dates)
    using Dates
end