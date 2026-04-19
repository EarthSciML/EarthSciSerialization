"""
Mock MTK/Catalyst system types.

These are the no-MTK fallbacks for `ModelingToolkit.System`,
`ModelingToolkit.PDESystem`, and `Catalyst.ReactionSystem`. When the
corresponding Julia package is loaded, the real extension-provided
constructors become available; otherwise, users can still call the
`MockMTKSystem`, `MockPDESystem`, and `MockCatalystSystem` constructors
directly and get pure-Julia snapshots of the flattened system.

The mock constructors enforce the same ODE-vs-PDE split as the real ones:
calling `MockMTKSystem(::Model)` on a model that flattens to a PDE errors
with a clear redirect to `MockPDESystem`, and vice versa.
"""

using OrderedCollections: OrderedDict

# ========================================
# Mock system struct definitions
# ========================================

"""
    MockMTKSystem

No-MTK fallback for `ModelingToolkit.System`. Captures the ODE form of a
flattened ESM system as plain-Julia collections.

Fields:
- `name::Symbol`: system name.
- `state_variables::Vector{String}`: namespaced state-variable names.
- `parameters::Vector{String}`: namespaced parameter names.
- `observed_variables::Vector{String}`: namespaced observed-variable names.
- `equations::Vector{String}`: string dump of the flattened equations
  (one per equation, e.g. `"D(x, t) ~ -k * x"`).
- `events::Vector{String}`: string summaries of continuous/discrete events.
- `metadata::Dict{String,Any}`: provenance (source system, creation time, ...).
"""
struct MockMTKSystem
    name::Symbol
    state_variables::Vector{String}
    parameters::Vector{String}
    observed_variables::Vector{String}
    equations::Vector{String}
    events::Vector{String}
    metadata::Dict{String,Any}
end

"""
    MockPDESystem

No-MTK fallback for `ModelingToolkit.PDESystem`. Captures the PDE form of a
flattened ESM system as plain-Julia collections.

Fields:
- `name::Symbol`: system name.
- `independent_variables::Vector{Symbol}`: e.g. `[:t, :x, :y]`.
- `state_variables::Vector{String}`: namespaced spatial-field names.
- `parameters::Vector{String}`: namespaced parameter names.
- `observed_variables::Vector{String}`: namespaced observed-variable names.
- `equations::Vector{String}`: string dump of the flattened PDE equations.
- `boundary_conditions::Vector{String}`: string dump of BCs derived from
  the domain and slice-based coupling patterns.
- `initial_conditions::Vector{String}`: string dump of ICs from variable
  defaults.
- `domain::Union{Domain,Nothing}`: the target domain of the flattened system.
- `metadata::Dict{String,Any}`: provenance.
"""
struct MockPDESystem
    name::Symbol
    independent_variables::Vector{Symbol}
    state_variables::Vector{String}
    parameters::Vector{String}
    observed_variables::Vector{String}
    equations::Vector{String}
    boundary_conditions::Vector{String}
    initial_conditions::Vector{String}
    domain::Union{Domain,Nothing}
    metadata::Dict{String,Any}
end

"""
    MockCatalystSystem

No-Catalyst fallback for `Catalyst.ReactionSystem`. Captures the structure
of an ESM `ReactionSystem` as plain-Julia collections.

Fields:
- `name::Symbol`: system name.
- `species::Vector{String}`: species names.
- `parameters::Vector{String}`: parameter names.
- `reactions::Vector{String}`: string-rendered reactions (e.g. `"A + B → C, rate: k*A*B"`).
- `events::Vector{String}`: string summaries of any reaction-system events.
- `constraints::Vector{String}`: string dump of any constraint equations.
- `metadata::Dict{String,Any}`: provenance.
"""
struct MockCatalystSystem
    name::Symbol
    species::Vector{String}
    parameters::Vector{String}
    reactions::Vector{String}
    events::Vector{String}
    constraints::Vector{String}
    metadata::Dict{String,Any}
end

# ========================================
# Helpers
# ========================================

_sym_name(name::Symbol) = name
_sym_name(name::AbstractString) = Symbol(name)

"""
    _pde_independent_vars(flat::FlattenedSystem) -> Bool

Return true when the flattened system has spatial independent variables
(i.e. needs a PDESystem rather than an ODESystem). A FlattenedSystem with
`[:t]` only is a pure ODE; anything else is a PDE.
"""
function _pde_independent_vars(flat::FlattenedSystem)
    return !(length(flat.independent_variables) == 1 &&
             flat.independent_variables[1] == :t)
end

"""
    _expr_to_string(expr::Expr) -> String

Render an ESM Expr tree as a readable string. Shared helper for mock
system equation rendering.
"""
function _expr_to_string(expr::Expr)
    if expr isa IntExpr
        return string(expr.value)
    elseif expr isa NumExpr
        return string(expr.value)
    elseif expr isa VarExpr
        return expr.name
    elseif expr isa OpExpr
        if expr.op == "D"
            inner = isempty(expr.args) ? "?" : _expr_to_string(expr.args[1])
            wrt = expr.wrt === nothing ? "t" : expr.wrt
            return "D($inner, $wrt)"
        elseif expr.op in ("+", "-", "*", "/", "^") && length(expr.args) == 2
            l = _expr_to_string(expr.args[1])
            r = _expr_to_string(expr.args[2])
            return "($l $(expr.op) $r)"
        elseif expr.op == "-" && length(expr.args) == 1
            return "(-$(_expr_to_string(expr.args[1])))"
        else
            args_str = join([_expr_to_string(a) for a in expr.args], ", ")
            return "$(expr.op)($args_str)"
        end
    else
        return string(expr)
    end
end

function _equation_string(eq::Equation)
    return "$(_expr_to_string(eq.lhs)) ~ $(_expr_to_string(eq.rhs))"
end

# ========================================
# MockMTKSystem constructors (ODE path)
# ========================================

"""
    MockMTKSystem(flat::FlattenedSystem; name=:anonymous)

Construct a `MockMTKSystem` from a `FlattenedSystem`. Errors with a clear
redirect to `MockPDESystem` when the flattened system has spatial
independent variables (i.e. is actually a PDE).
"""
function MockMTKSystem(flat::FlattenedSystem;
                       name::Union{Symbol,AbstractString}=:anonymous)
    if _pde_independent_vars(flat)
        throw(ArgumentError(
            "Flattened system has independent variables $(flat.independent_variables), " *
            "which indicates a PDE. Use MockPDESystem(...) instead of MockMTKSystem(...)."
        ))
    end

    state_vars = collect(keys(flat.state_variables))
    params = collect(keys(flat.parameters))
    obs_vars = collect(keys(flat.observed_variables))
    equations = [_equation_string(eq) for eq in flat.equations]

    events = String[]
    for (i, ev) in enumerate(flat.continuous_events)
        push!(events, "continuous_event_$i: $(length(ev.conditions)) condition(s)")
    end
    for (i, ev) in enumerate(flat.discrete_events)
        push!(events, "discrete_event_$i: trigger=$(typeof(ev.trigger))")
    end

    metadata = Dict{String,Any}(
        "creation_time" => string(Dates.now()),
        "source_systems" => flat.metadata.source_systems,
        "coupling_rules_applied" => flat.metadata.coupling_rules_applied,
        "mock_system" => true,
    )

    return MockMTKSystem(_sym_name(name), state_vars, params, obs_vars,
                         equations, events, metadata)
end

"""
    MockMTKSystem(model::Model; name=:anonymous)

Convenience constructor: flatten the model first, then build the
`MockMTKSystem` from the resulting `FlattenedSystem`.
"""
function MockMTKSystem(model::Model;
                       name::Union{Symbol,AbstractString}=:anonymous)
    flat = flatten(model; name=String(_sym_name(name)))
    return MockMTKSystem(flat; name=name)
end

# ========================================
# MockPDESystem constructors (PDE path)
# ========================================

"""
    MockPDESystem(flat::FlattenedSystem; name=:anonymous)

Construct a `MockPDESystem` from a `FlattenedSystem`. Errors with a clear
redirect to `MockMTKSystem` when the flattened system is a pure ODE
(i.e. has only `:t` as its independent variable).
"""
function MockPDESystem(flat::FlattenedSystem;
                       name::Union{Symbol,AbstractString}=:anonymous)
    if !_pde_independent_vars(flat)
        throw(ArgumentError(
            "Flattened system has independent variables [t] only — this is a " *
            "pure ODE system. Use MockMTKSystem(...) instead of MockPDESystem(...)."
        ))
    end

    state_vars = collect(keys(flat.state_variables))
    params = collect(keys(flat.parameters))
    obs_vars = collect(keys(flat.observed_variables))
    equations = [_equation_string(eq) for eq in flat.equations]

    bcs = String[]
    ics = String[]
    if flat.domain !== nothing
        # Initial conditions from state-variable defaults
        for (vname, mvar) in flat.state_variables
            if mvar.default !== nothing
                push!(ics, "$vname(t=0) = $(mvar.default)")
            end
        end
    end

    events = String[]
    for (i, ev) in enumerate(flat.continuous_events)
        push!(events, "continuous_event_$i: $(length(ev.conditions)) condition(s)")
    end
    for (i, ev) in enumerate(flat.discrete_events)
        push!(events, "discrete_event_$i: trigger=$(typeof(ev.trigger))")
    end

    metadata = Dict{String,Any}(
        "creation_time" => string(Dates.now()),
        "source_systems" => flat.metadata.source_systems,
        "coupling_rules_applied" => flat.metadata.coupling_rules_applied,
        "events" => events,
        "mock_system" => true,
    )

    return MockPDESystem(_sym_name(name), flat.independent_variables,
                         state_vars, params, obs_vars,
                         equations, bcs, ics, flat.domain, metadata)
end

"""
    MockPDESystem(model::Model; name=:anonymous)

Convenience constructor: flatten the model first, then build the
`MockPDESystem` from the resulting `FlattenedSystem`.
"""
function MockPDESystem(model::Model;
                       name::Union{Symbol,AbstractString}=:anonymous)
    flat = flatten(model; name=String(_sym_name(name)))
    return MockPDESystem(flat; name=name)
end

# ========================================
# MockCatalystSystem constructors
# ========================================

"""
    MockCatalystSystem(rsys::ReactionSystem; name=:anonymous)

Build a `MockCatalystSystem` snapshot from an ESM `ReactionSystem`.
"""
function MockCatalystSystem(rsys::ReactionSystem;
                            name::Union{Symbol,AbstractString}=:anonymous)
    species = [sp.name for sp in rsys.species]
    params = [p.name for p in rsys.parameters]

    reactions = String[]
    for rxn in rsys.reactions
        reactant_str = if isempty(rxn.reactants)
            "∅"
        else
            join([stoich > 1 ? "$stoich $spec" : spec
                  for (spec, stoich) in rxn.reactants], " + ")
        end
        product_str = if isempty(rxn.products)
            "∅"
        else
            join([stoich > 1 ? "$stoich $spec" : spec
                  for (spec, stoich) in rxn.products], " + ")
        end
        rate_str = _expr_to_string(rxn.rate)
        arrow = rxn.reversible ? " ⇌ " : " → "
        push!(reactions, "$reactant_str$arrow$product_str, rate: $rate_str")
    end

    metadata = Dict{String,Any}(
        "creation_time" => string(Dates.now()),
        "species_count" => length(species),
        "parameters_count" => length(params),
        "reactions_count" => length(reactions),
        "mock_system" => true,
    )

    return MockCatalystSystem(_sym_name(name), species, params, reactions,
                              String[], String[], metadata)
end
