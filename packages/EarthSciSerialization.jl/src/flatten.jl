"""
Coupled System Flattening for ESM Format.

Implements spec §4.7.5 (flattening algorithm) and §4.7.6 (dimension promotion).

`flatten(::EsmFile)` produces a `FlattenedSystem`: a single flat equation system
with dot-namespaced variables and real Expr-tree equations. Reactions are lowered
to ODEs via `lower_reactions_to_equations`; coupling rules merge RHS terms;
`variable_map` substitutes parameters; `operator_apply`/`callback` are recorded
opaquely in metadata.
"""

using OrderedCollections: OrderedDict

# ========================================
# Error Types (§4.7.5 / §4.7.6 taxonomy)
# ========================================

"""
    ConflictingDerivativeError

Raised when a species appears both as the left-hand side of an explicit
differential equation (`D(X, t) = ...`) and as a substrate or product of any
reaction in the same flattened file. Such a system is over-determined: the
reaction contribution to `d[X]/dt` would silently shadow the user's equation.

Fields:
- `species::Vector{String}`: fully-qualified (dot-namespaced) names of every
  offending species.
"""
struct ConflictingDerivativeError <: Exception
    species::Vector{String}
end

function Base.showerror(io::IO, e::ConflictingDerivativeError)
    names = join(e.species, ", ")
    print(io, "ConflictingDerivativeError: species have both an explicit ",
          "derivative equation and a reaction contribution: ", names)
end

"""
    DimensionPromotionError

Raised during flatten when a variable or equation cannot be promoted from
its source domain to the target domain given the available `Interface` rules
(§4.7.6).
"""
struct DimensionPromotionError <: Exception
    details::String
end
Base.showerror(io::IO, e::DimensionPromotionError) =
    print(io, "DimensionPromotionError: ", e.details)

"""
    UnmappedDomainError

Raised when two systems on different domains are coupled without an `Interface`
that defines their dimension mapping (§4.7.6).
"""
struct UnmappedDomainError <: Exception
    source::String
    target::String
end
Base.showerror(io::IO, e::UnmappedDomainError) =
    print(io, "UnmappedDomainError: no Interface maps domain '", e.source,
          "' to domain '", e.target, "'")

"""
    UnsupportedMappingError

Raised when an `Interface` requests a `dimension_mapping` type or regridding
strategy that is not supported by the current library tier (§4.7.6). The
`mapping_type` field carries the offending type or strategy name (e.g.
`"slice"`, `"project"`, `"regrid"`, or a specific regridding method like
`"cubic_spline"`). Matches the Rust `FlattenError::UnsupportedMapping` variant
and the Python `UnsupportedMappingError` exception for cross-language
error-name parity.
"""
struct UnsupportedMappingError <: Exception
    mapping_type::String
end
Base.showerror(io::IO, e::UnsupportedMappingError) =
    print(io, "UnsupportedMappingError: mapping type '",
          e.mapping_type, "' is not supported by this library tier")

"""
    DomainUnitMismatchError

Raised when coupling across an `Interface` requires a unit conversion that
was not declared by the user (§4.7.6).
"""
struct DomainUnitMismatchError <: Exception
    variable::String
    source_units::String
    target_units::String
end
Base.showerror(io::IO, e::DomainUnitMismatchError) =
    print(io, "DomainUnitMismatchError: variable '", e.variable,
          "' has units '", e.source_units, "' on source and '",
          e.target_units, "' on target")

"""
    DomainExtentMismatchError

Defined for cross-language error-name parity with the Rust `FlattenError`
taxonomy and the Python `flatten()` exception set. Would be raised when an
`identity` mapping bridges two domains whose spatial extents on a shared
independent variable disagree. The Julia flatten pipeline does not currently
perform this check, so this type is reserved and never raised by the current
implementation — it exists so consumers can catch it by name.
"""
struct DomainExtentMismatchError <: Exception
    variable::String
end
Base.showerror(io::IO, e::DomainExtentMismatchError) =
    print(io, "DomainExtentMismatchError: domain extent mismatch on ",
          "independent variable '", e.variable, "' under identity mapping")

"""
    SliceOutOfDomainError

Defined for cross-language error-name parity; only raised if `slice` is ever
implemented at a higher tier in the Julia flatten pipeline. Would be raised
when a `slice` mapping's fixed coordinate lies outside the source variable's
declared domain extent.
"""
struct SliceOutOfDomainError <: Exception
    coordinate::String
    value::String
end
Base.showerror(io::IO, e::SliceOutOfDomainError) =
    print(io, "SliceOutOfDomainError: slice coordinate '", e.coordinate,
          "' = ", e.value, " lies outside the source domain extent")

"""
    CyclicPromotionError

Defined for cross-language error-name parity. Not raised by Core-tier Julia
because no promotion graph is built — reserved for a future tier upgrade that
does promotion-graph analysis. Would signal that the declared `Interface`
rules form a cycle (A promotes to B, B promotes back to A on a different
axis).
"""
struct CyclicPromotionError <: Exception
    variables::Vector{String}
end
Base.showerror(io::IO, e::CyclicPromotionError) =
    print(io, "CyclicPromotionError: cyclic promotion detected involving ",
          "variables ", e.variables)

# ========================================
# Types
# ========================================

"""
    FlattenMetadata

Provenance metadata for a flattened system.

Fields:
- `source_systems::Vector{String}`: names of the component systems that were
  flattened (sorted for determinism).
- `coupling_rules_applied::Vector{String}`: human-readable summary of each
  coupling entry applied.
- `dimension_promotions_applied::Vector{NamedTuple}`: records of each dimension
  promotion — e.g. `(variable="Chem.O3", source_domain=nothing, target_domain="grid2d", kind=:broadcast)`.
- `opaque_coupling_refs::Vector{String}`: opaque runtime references recorded
  for `operator_apply` and `callback` couplings.
"""
struct FlattenMetadata
    source_systems::Vector{String}
    coupling_rules_applied::Vector{String}
    dimension_promotions_applied::Vector{NamedTuple}
    opaque_coupling_refs::Vector{String}
end

FlattenMetadata(source_systems::Vector{String}=String[],
                coupling_rules_applied::Vector{String}=String[];
                dimension_promotions_applied::Vector{<:NamedTuple}=NamedTuple[],
                opaque_coupling_refs::Vector{String}=String[]) =
    FlattenMetadata(source_systems, coupling_rules_applied,
                    NamedTuple[dp for dp in dimension_promotions_applied],
                    opaque_coupling_refs)

"""
    FlattenedSystem

A coupled ESM file flattened into a single symbolic representation.

All variables, parameters, and species are dot-namespaced (e.g.
`"SimpleOzone.O3"`, `"Atmosphere.Chemistry.NO2"`). Equations are real
`Equation` objects whose Expr trees reference namespaced names via `VarExpr`.
This is the canonical intermediate form consumed by MTK/PDESystem constructors
(in the Julia extension) and by cross-language code generators.

Fields:
- `independent_variables::Vector{Symbol}`: `[:t]` for pure-ODE systems, or
  `[:t, :x, :y, ...]` when spatial operators are present.
- `state_variables::OrderedDict{String, ModelVariable}`: namespaced state
  variables and (former-reaction) species.
- `parameters::OrderedDict{String, ModelVariable}`: namespaced parameters,
  minus any promoted to variables by `variable_map`.
- `observed_variables::OrderedDict{String, ModelVariable}`: namespaced
  observed variables.
- `equations::Vector{Equation}`: all equations after reaction lowering and
  coupling, with variable references rewritten to namespaced form.
- `continuous_events::Vector{ContinuousEvent}`: collected from every source
  model with references rewritten.
- `discrete_events::Vector{DiscreteEvent}`: ditto.
- `domain::Union{Domain, Nothing}`: the target domain after any dimension
  promotion (§4.7.6), or `nothing` for purely 0D systems.
- `metadata::FlattenMetadata`: provenance.
"""
struct FlattenedSystem
    independent_variables::Vector{Symbol}
    state_variables::OrderedDict{String, ModelVariable}
    parameters::OrderedDict{String, ModelVariable}
    observed_variables::OrderedDict{String, ModelVariable}
    equations::Vector{Equation}
    continuous_events::Vector{ContinuousEvent}
    discrete_events::Vector{DiscreteEvent}
    domain::Union{Domain, Nothing}
    metadata::FlattenMetadata
end

# ========================================
# Reaction Lowering Helper (§4.6 + §4.7.6)
# ========================================

"""
    lower_reactions_to_equations(reactions, species, domain=nothing) -> Vector{Equation}

Produce the ODE equations induced by a set of reactions using standard
mass-action kinetics: `d[X]/dt = Σ (stoich_ij * rate_j)`.

Shared by `derive_odes` (reaction → Model) and `flatten` (EsmFile → FlattenedSystem)
so there is exactly one place that turns stoichiometry into equations.

On a 0D domain (`domain === nothing`), the LHS is `D(X, t)`. On a PDE domain,
the LHS is still `D(X, t)` symbolically — dimension promotion (§4.7.6) is
applied by `flatten`, not here. The resulting equation lives on the caller's
domain; spatial operators are added downstream when coupling adds them.
"""
function lower_reactions_to_equations(reactions::Vector{Reaction},
                                      species::Vector{Species},
                                      domain::Union{Domain, Nothing}=nothing)::Vector{Equation}
    equations = Equation[]
    if isempty(species)
        return equations
    end

    species_names = [sp.name for sp in species]
    species_idx = Dict{String, Int}(name => i for (i, name) in enumerate(species_names))

    n_species = length(species_names)
    n_rxns = length(reactions)
    S = zeros(Float64, n_species, n_rxns)

    for (j, rxn) in enumerate(reactions)
        substrates = getfield(rxn, :substrates)
        if substrates !== nothing
            for entry in substrates
                if haskey(species_idx, entry.species)
                    S[species_idx[entry.species], j] -= entry.stoichiometry
                end
            end
        end
        products = getfield(rxn, :products)
        if products !== nothing
            for entry in products
                if haskey(species_idx, entry.species)
                    S[species_idx[entry.species], j] += entry.stoichiometry
                end
            end
        end
    end

    for (i, name) in enumerate(species_names)
        lhs = OpExpr("D", EarthSciSerialization.Expr[VarExpr(name)], wrt="t")
        terms = EarthSciSerialization.Expr[]
        for (j, rxn) in enumerate(reactions)
            stoich = S[i, j]
            stoich == 0 && continue
            rate_expr = mass_action_rate(rxn, species)
            if stoich == 1
                push!(terms, rate_expr)
            elseif stoich == -1
                push!(terms, OpExpr("-", EarthSciSerialization.Expr[rate_expr]))
            else
                push!(terms, OpExpr("*",
                    EarthSciSerialization.Expr[NumExpr(Float64(stoich)), rate_expr]))
            end
        end
        rhs = if isempty(terms)
            NumExpr(0.0)
        elseif length(terms) == 1
            terms[1]
        else
            OpExpr("+", terms)
        end
        push!(equations, Equation(lhs, rhs))
    end

    return equations
end

# ========================================
# Namespacing
# ========================================

"""
    namespace_expr(expr, prefix, local_names) -> Expr

Return a new Expr tree with every VarExpr referencing a name in `local_names`
rewritten as `"<prefix>.<name>"`. For dotted names (e.g. `Sub.var`), the first
segment is treated as the local symbol: if it is in `local_names` (a local
subsystem), the whole dotted path is prefixed; otherwise the reference is
already external and is left unchanged. Numeric literals are unchanged.
"""
function namespace_expr(expr::NumExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
    return expr
end

function namespace_expr(expr::IntExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
    return expr
end

function namespace_expr(expr::VarExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
    if occursin('.', expr.name)
        first_part = String(split(expr.name, '.')[1])
        if first_part in local_names
            return VarExpr("$(prefix).$(expr.name)")
        end
        return expr
    end
    if expr.name in local_names
        return VarExpr("$(prefix).$(expr.name)")
    end
    return expr
end

function namespace_expr(expr::OpExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
    new_args = EarthSciSerialization.Expr[namespace_expr(a, prefix, local_names) for a in expr.args]
    # Recurse into array-op subtrees so variables inside arrayop bodies,
    # makearray values, etc. get their prefix rewrites too.
    new_expr_body = expr.expr_body === nothing ? nothing :
        namespace_expr(expr.expr_body, prefix, local_names)
    new_values = expr.values === nothing ? nothing :
        EarthSciSerialization.Expr[namespace_expr(v, prefix, local_names) for v in expr.values]
    return OpExpr(expr.op, new_args;
        wrt=expr.wrt, dim=expr.dim,
        output_idx=expr.output_idx,
        expr_body=new_expr_body,
        reduce=expr.reduce,
        ranges=expr.ranges,
        regions=expr.regions,
        values=new_values,
        shape=expr.shape,
        perm=expr.perm,
        axis=expr.axis,
        fn=expr.fn,
        name=expr.name,
        value=expr.value)
end

"""
    lhs_dependent_variable(expr) -> Union{String, Nothing}

Extract the dependent variable name from an equation LHS. For `D(x, t)`, returns
`"x"`. For a bare `VarExpr("x")`, returns `"x"`. Otherwise returns `nothing`.
"""
function lhs_dependent_variable(expr::EarthSciSerialization.Expr)::Union{String, Nothing}
    if expr isa VarExpr
        return expr.name
    elseif expr isa OpExpr && expr.op == "D" && !isempty(expr.args) && expr.args[1] isa VarExpr
        return (expr.args[1]::VarExpr).name
    end
    return nothing
end

"""
    has_spatial_operator(expr) -> Bool

True if the expression contains any spatial operator (`grad`, `div`,
`laplacian`, or `D` with `wrt != "t"`).
"""
function has_spatial_operator(expr::EarthSciSerialization.Expr)::Bool
    if expr isa NumExpr || expr isa IntExpr || expr isa VarExpr
        return false
    end
    if expr isa OpExpr
        if expr.op in ("grad", "div", "laplacian")
            return true
        end
        if expr.op == "D" && expr.wrt !== nothing && expr.wrt != "t"
            return true
        end
        for a in expr.args
            has_spatial_operator(a) && return true
        end
    end
    return false
end

"""
    spatial_dims_in_expr(expr) -> Set{Symbol}

Collect all spatial dimension names referenced by spatial operators in `expr`.
"""
function spatial_dims_in_expr(expr::EarthSciSerialization.Expr)::Set{Symbol}
    dims = Set{Symbol}()
    _collect_spatial_dims!(dims, expr)
    return dims
end

function _collect_spatial_dims!(dims::Set{Symbol}, expr::EarthSciSerialization.Expr)
    if expr isa OpExpr
        if expr.op in ("grad", "div") && expr.dim !== nothing
            push!(dims, Symbol(expr.dim))
        elseif expr.op == "D" && expr.wrt !== nothing && expr.wrt != "t"
            push!(dims, Symbol(expr.wrt))
        elseif expr.op == "laplacian"
            # laplacian doesn't carry dim; caller assumes domain's full spatial
            # axes. We'll fill that in from the domain spec below.
        end
        for a in expr.args
            _collect_spatial_dims!(dims, a)
        end
    end
end

# ========================================
# Per-system collection
# ========================================

"""
Collect a Model's variables and equations into the flattener accumulators,
recursing through subsystems. All names are rewritten to `prefix.local_name`.
"""
function _collect_model!(states::OrderedDict{String, ModelVariable},
                         params::OrderedDict{String, ModelVariable},
                         observeds::OrderedDict{String, ModelVariable},
                         equations::Vector{Equation},
                         continuous_events::Vector{ContinuousEvent},
                         discrete_events::Vector{DiscreteEvent},
                         model::Model, prefix::String)
    local_names = Set{String}(keys(model.variables))
    # Also include subsystem-qualified names from this level's subsystems so
    # that references inside the model to subsystem variables get namespaced.
    for (sub_name, _) in model.subsystems
        push!(local_names, sub_name)
    end

    for (name, var) in model.variables
        namespaced = "$(prefix).$(name)"
        if var.type == StateVariable
            states[namespaced] = var
        elseif var.type == ParameterVariable
            params[namespaced] = var
        elseif var.type == ObservedVariable
            observeds[namespaced] = var
        end
    end

    explicit_lhs_names = Set{String}()
    for eq in model.equations
        lhs = namespace_expr(eq.lhs, prefix, local_names)
        rhs = namespace_expr(eq.rhs, prefix, local_names)
        push!(equations, Equation(lhs, rhs; _comment=eq._comment))
        if lhs isa VarExpr
            push!(explicit_lhs_names, lhs.name)
        end
    end

    # Observed variables carry their defining expression in `expression`
    # (per esm-spec §6.2: "must include an `expression` field"). Emit
    # `obs ~ expression` as a flattened equation so the enclosing System
    # is well-determined (one equation per observed var). Skip when an
    # explicit `equations` entry already provides the definition — some
    # fixtures use a sentinel `expression: 0.0` plus an explicit equation.
    for (name, var) in model.variables
        var.type == ObservedVariable || continue
        var.expression === nothing && continue
        namespaced = "$(prefix).$(name)"
        namespaced in explicit_lhs_names && continue
        lhs = VarExpr(namespaced)
        rhs = namespace_expr(var.expression, prefix, local_names)
        push!(equations, Equation(lhs, rhs))
    end

    for ev in model.continuous_events
        new_conds = EarthSciSerialization.Expr[namespace_expr(c, prefix, local_names) for c in ev.conditions]
        new_affects = AffectEquation[
            AffectEquation(startswith(a.lhs, prefix * ".") || occursin('.', a.lhs) ? a.lhs : "$(prefix).$(a.lhs)",
                           namespace_expr(a.rhs, prefix, local_names))
            for a in ev.affects
        ]
        push!(continuous_events,
              ContinuousEvent(new_conds, new_affects; description=ev.description))
    end

    for ev in model.discrete_events
        new_affects = FunctionalAffect[
            FunctionalAffect(
                occursin('.', a.target) ? a.target : "$(prefix).$(a.target)",
                namespace_expr(a.expression, prefix, local_names);
                operation=a.operation)
            for a in ev.affects
        ]
        new_trigger = if ev.trigger isa ConditionTrigger
            ConditionTrigger(namespace_expr(ev.trigger.expression, prefix, local_names))
        else
            ev.trigger
        end
        push!(discrete_events,
              DiscreteEvent(new_trigger, new_affects; description=ev.description))
    end

    for (sub_name, sub_model) in model.subsystems
        _collect_model!(states, params, observeds, equations,
                        continuous_events, discrete_events,
                        sub_model, "$(prefix).$(sub_name)")
    end
end

"""
Lower a ReactionSystem into the flattener accumulators. Species become state
variables, rate constants become parameters, and reactions are converted to
ODE equations via `lower_reactions_to_equations`. Both species and equation
variables are then namespaced by `prefix`.
"""
function _collect_reaction_system!(states::OrderedDict{String, ModelVariable},
                                   params::OrderedDict{String, ModelVariable},
                                   equations::Vector{Equation},
                                   rsys::ReactionSystem, prefix::String,
                                   file_domains::Union{Dict{String, Domain}, Nothing})
    local_names = Set{String}()
    for sp in rsys.species
        push!(local_names, sp.name)
    end
    for p in rsys.parameters
        push!(local_names, p.name)
    end
    for (sub_name, _) in rsys.subsystems
        push!(local_names, sub_name)
    end

    for sp in rsys.species
        namespaced = "$(prefix).$(sp.name)"
        states[namespaced] = ModelVariable(StateVariable;
            default=sp.default, description=sp.description, units=sp.units)
    end
    for p in rsys.parameters
        namespaced = "$(prefix).$(p.name)"
        params[namespaced] = ModelVariable(ParameterVariable;
            default=p.default, description=p.description, units=p.units)
    end

    sys_domain = if rsys.domain !== nothing && file_domains !== nothing &&
                    haskey(file_domains, rsys.domain)
        file_domains[rsys.domain]
    else
        nothing
    end

    raw_eqs = lower_reactions_to_equations(rsys.reactions, rsys.species, sys_domain)
    for eq in raw_eqs
        lhs = namespace_expr(eq.lhs, prefix, local_names)
        rhs = namespace_expr(eq.rhs, prefix, local_names)
        push!(equations, Equation(lhs, rhs; _comment=eq._comment))
    end

    for (sub_name, sub_rsys) in rsys.subsystems
        _collect_reaction_system!(states, params, equations,
                                  sub_rsys, "$(prefix).$(sub_name)", file_domains)
    end
end

# ========================================
# Conflicting-derivative detection (item E)
# ========================================

"""
    _find_conflicting_derivatives(file) -> Vector{String}

Return the sorted list of fully-qualified species names that appear both as
the LHS dependent variable of an explicit `D(X, t) = ...` equation in any
`models[*]` (including subsystems) AND as a substrate or product of a
reaction in any `reaction_systems[*]` (after namespacing).

Used by `flatten` to throw `ConflictingDerivativeError` before any lowering,
and by `validate_structural` to catch the same class of error at load time.
"""
function _find_conflicting_derivatives(file::EsmFile)::Vector{String}
    explicit_lhs = Set{String}()
    if file.models !== nothing
        for (name, model) in file.models
            _collect_explicit_derivative_lhs!(explicit_lhs, model, name)
        end
    end

    reaction_species = Set{String}()
    if file.reaction_systems !== nothing
        for (name, rsys) in file.reaction_systems
            _collect_reaction_species!(reaction_species, rsys, name)
        end
    end

    conflicting = sort!(collect(intersect(explicit_lhs, reaction_species)))
    return conflicting
end

function _collect_explicit_derivative_lhs!(acc::Set{String}, model::Model, prefix::String)
    for eq in model.equations
        if eq.lhs isa OpExpr && eq.lhs.op == "D" && !isempty(eq.lhs.args) &&
           eq.lhs.args[1] isa VarExpr
            raw = (eq.lhs.args[1]::VarExpr).name
            # A bare name refers to a variable in this model's scope.
            push!(acc, occursin('.', raw) ? raw : "$(prefix).$(raw)")
        end
    end
    for (sub_name, sub) in model.subsystems
        _collect_explicit_derivative_lhs!(acc, sub, "$(prefix).$(sub_name)")
    end
end

function _collect_reaction_species!(acc::Set{String}, rsys::ReactionSystem, prefix::String)
    for rxn in rsys.reactions
        substrates = getfield(rxn, :substrates)
        if substrates !== nothing
            for entry in substrates
                push!(acc, "$(prefix).$(entry.species)")
            end
        end
        products = getfield(rxn, :products)
        if products !== nothing
            for entry in products
                push!(acc, "$(prefix).$(entry.species)")
            end
        end
    end
    for (sub_name, sub) in rsys.subsystems
        _collect_reaction_species!(acc, sub, "$(prefix).$(sub_name)")
    end
end

# ========================================
# Hybrid-flattening preflight checks (§4.7.6)
# ========================================

const _SUPPORTED_REGRIDDING_METHODS = Set{String}(["identity"])

"""
Validate that every declared `Interface` names a dimension mapping and
regridding strategy that the Julia flatten pipeline actually implements.

§4.7.6 defines five canonical mapping types: `broadcast`, `identity`, `slice`,
`project`, `regrid`. The Julia library's flatten pipeline currently wires only
`broadcast` and `identity` (the Core-tier minimum). Interfaces that declare
`slice` or `project` raise `DimensionPromotionError`; interfaces that declare
a regridding method outside the supported set raise `UnsupportedMappingError`.
"""
function _check_interfaces!(file::EsmFile)
    file.interfaces === nothing && return
    for (iface_name, iface) in file.interfaces
        dm = iface.dimension_mapping
        dm_type = get(dm, "type", nothing)
        if dm_type !== nothing
            t = String(dm_type)
            if t == "regrid"
                method = iface.regridding === nothing ? "unspecified" :
                         String(get(iface.regridding, "method", "unspecified"))
                throw(UnsupportedMappingError(method))
            elseif t in ("slice", "project")
                throw(DimensionPromotionError(
                    "interface '$(iface_name)': dimension_mapping type '$(t)' " *
                    "is Analysis-tier and not yet implemented by the Julia flatten pipeline"))
            end
        end

        if iface.regridding !== nothing
            method_val = get(iface.regridding, "method", nothing)
            if method_val !== nothing
                method = String(method_val)
                if !(method in _SUPPORTED_REGRIDDING_METHODS)
                    throw(UnsupportedMappingError(method))
                end
            end
        end
    end
    return
end

"""
Build a mapping `system_name => domain_name` from a file's models and
reaction systems. Systems without a declared domain are omitted.
"""
function _collect_system_domains(file::EsmFile)::Dict{String, String}
    sysdom = Dict{String, String}()
    if file.models !== nothing
        for (name, model) in file.models
            if model.domain !== nothing
                sysdom[name] = model.domain
            end
        end
    end
    if file.reaction_systems !== nothing
        for (name, rsys) in file.reaction_systems
            if rsys.domain !== nothing
                sysdom[name] = rsys.domain
            end
        end
    end
    return sysdom
end

"""
True if `file.interfaces` contains an Interface whose `domains` vector covers
both `d_a` and `d_b` (order-insensitive).
"""
function _interface_covers(file::EsmFile, d_a::String, d_b::String)::Bool
    file.interfaces === nothing && return false
    for (_, iface) in file.interfaces
        if d_a in iface.domains && d_b in iface.domains
            return true
        end
    end
    return false
end

"""
For every coupling entry that references two or more systems (`operator_compose`,
`couple`), raise `UnmappedDomainError` if any pair of referenced systems lives
on distinct, non-null domains and no declared `Interface` covers both domains.

§4.7.6: "Any other hybrid coupling (N-D ↔ M-D with N ≠ M, or different grids
of the same dimensionality) requires an explicit Interface in the file's
interfaces section; its absence raises `UnmappedDomainError`."
"""
function _check_coupling_domain_coverage!(file::EsmFile)
    isempty(file.coupling) && return
    sysdom = _collect_system_domains(file)
    isempty(sysdom) && return

    for entry in file.coupling
        systems = if entry isa CouplingOperatorCompose || entry isa CouplingCouple
            entry.systems
        else
            continue
        end
        length(systems) < 2 && continue
        for i in 1:length(systems), j in (i+1):length(systems)
            a, b = systems[i], systems[j]
            (haskey(sysdom, a) && haskey(sysdom, b)) || continue
            da, db = sysdom[a], sysdom[b]
            da == db && continue
            if !_interface_covers(file, da, db)
                throw(UnmappedDomainError(da, db))
            end
        end
    end
    return
end

"""
Walk every `variable_map` coupling entry with `transform == "identity"` and
raise `DomainUnitMismatchError` when the source and target variables carry
non-empty, declared-different units. `param_to_var` and `conversion_factor`
transforms are exempt: `conversion_factor` declares the conversion explicitly;
`param_to_var` replaces a parameter with a variable and does not imply unit
equivalence at the mapping site (units are still validated elsewhere).
"""
function _check_variable_map_units!(file::EsmFile)
    isempty(file.coupling) && return
    for entry in file.coupling
        entry isa CouplingVariableMap || continue
        entry.transform == "identity" || continue
        src_units = _lookup_variable_units(file, entry.from)
        tgt_units = _lookup_variable_units(file, entry.to)
        (src_units === nothing || tgt_units === nothing) && continue
        if src_units != tgt_units
            throw(DomainUnitMismatchError(entry.from, src_units, tgt_units))
        end
    end
    return
end

"""
Look up a dot-qualified variable's declared units across models, subsystems,
and reaction systems (species + parameters). Returns `nothing` when the
variable is missing or carries no declared units.
"""
function _lookup_variable_units(file::EsmFile, qualified::String)::Union{String, Nothing}
    parts = split(qualified, ".")
    length(parts) >= 2 || return nothing
    root = String(parts[1])
    tail = String(join(parts[2:end], "."))

    if file.models !== nothing && haskey(file.models, root)
        return _lookup_model_units(file.models[root], tail)
    end
    if file.reaction_systems !== nothing && haskey(file.reaction_systems, root)
        return _lookup_rsys_units(file.reaction_systems[root], tail)
    end
    return nothing
end

function _lookup_model_units(model::Model, name::String)::Union{String, Nothing}
    if haskey(model.variables, name)
        return model.variables[name].units
    end
    # Recurse into subsystems for nested names like "Inner.T".
    dot = findfirst('.', name)
    if dot !== nothing
        head = String(SubString(name, 1, dot - 1))
        rest = String(SubString(name, dot + 1))
        if haskey(model.subsystems, head)
            return _lookup_model_units(model.subsystems[head], rest)
        end
    end
    return nothing
end

function _lookup_rsys_units(rsys::ReactionSystem, name::String)::Union{String, Nothing}
    for sp in rsys.species
        sp.name == name && return sp.units
    end
    for p in rsys.parameters
        p.name == name && return p.units
    end
    dot = findfirst('.', name)
    if dot !== nothing
        head = String(SubString(name, 1, dot - 1))
        rest = String(SubString(name, dot + 1))
        if haskey(rsys.subsystems, head)
            return _lookup_rsys_units(rsys.subsystems[head], rest)
        end
    end
    return nothing
end

# ========================================
# Coupling rule application (§4.7.5 step 3)
# ========================================

"""
Apply a `CouplingOperatorCompose` entry: for each equation LHS dependent
variable (with `translate` and `_var` placeholder expansion), find matching
equations across the listed systems and sum their RHS terms. In the flattened
representation, "matching" means "has the same namespaced dependent variable".
"""
function _apply_operator_compose!(equations::Vector{Equation},
                                  entry::CouplingOperatorCompose,
                                  file::EsmFile)
    translate = entry.translate === nothing ? Dict{String, Any}() : entry.translate

    # Build placeholder targets: if any equation's LHS uses VarExpr("_var"),
    # that equation is a template to be expanded for every state variable
    # in the other systems referenced by this compose entry.
    placeholder_indices = Int[]
    normal_indices = Int[]
    for (i, eq) in enumerate(equations)
        dep = lhs_dependent_variable(eq.lhs)
        if dep !== nothing && (dep == "_var" || endswith(dep, "._var"))
            push!(placeholder_indices, i)
        else
            push!(normal_indices, i)
        end
    end

    # Expand placeholder equations into concrete ones, one per state variable
    # that belongs to any of the other systems in `entry.systems`.
    if !isempty(placeholder_indices)
        target_vars = _collect_target_state_vars(equations, normal_indices, entry.systems)
        new_equations = Equation[]
        delete_indices = Set{Int}()
        for i in placeholder_indices
            tmpl = equations[i]
            push!(delete_indices, i)
            placeholder_lhs_dep = lhs_dependent_variable(tmpl.lhs)
            for var in target_vars
                new_lhs = _substitute_placeholder(tmpl.lhs, placeholder_lhs_dep, var)
                new_rhs = _substitute_placeholder(tmpl.rhs, placeholder_lhs_dep, var)
                push!(new_equations, Equation(new_lhs, new_rhs; _comment=tmpl._comment))
            end
        end
        # Remove originals and append the expansions.
        kept = Equation[]
        for (i, eq) in enumerate(equations)
            if !(i in delete_indices)
                push!(kept, eq)
            end
        end
        append!(kept, new_equations)
        empty!(equations)
        append!(equations, kept)
    end

    # Now merge equations with identical dependent variables.
    by_dep = OrderedDict{String, Vector{Int}}()
    for (i, eq) in enumerate(equations)
        dep = lhs_dependent_variable(eq.lhs)
        dep === nothing && continue
        # Apply translation to land on a canonical name.
        canonical = get(translate, dep, dep)
        canonical = canonical isa String ? canonical : dep
        push!(get!(by_dep, canonical, Int[]), i)
    end

    merged = Equation[]
    merged_indices = Set{Int}()
    for (dep, indices) in by_dep
        if length(indices) < 2
            continue
        end
        # Sum all RHS terms into a single equation; keep the first equation's LHS.
        first_idx = indices[1]
        lhs = equations[first_idx].lhs
        terms = EarthSciSerialization.Expr[equations[i].rhs for i in indices]
        new_rhs = length(terms) == 1 ? terms[1] : OpExpr("+", terms)
        push!(merged, Equation(lhs, new_rhs))
        for i in indices
            push!(merged_indices, i)
        end
    end

    if isempty(merged)
        return
    end

    kept = Equation[]
    for (i, eq) in enumerate(equations)
        if !(i in merged_indices)
            push!(kept, eq)
        end
    end
    append!(kept, merged)
    empty!(equations)
    append!(equations, kept)
    return
end

function _collect_target_state_vars(equations::Vector{Equation},
                                    normal_indices::Vector{Int},
                                    system_names::Vector{String})::Vector{String}
    vars = String[]
    seen = Set{String}()
    for i in normal_indices
        dep = lhs_dependent_variable(equations[i].lhs)
        dep === nothing && continue
        parts = split(dep, ".")
        length(parts) >= 2 || continue
        root = String(parts[1])
        if root in system_names && !(dep in seen)
            push!(vars, dep)
            push!(seen, dep)
        end
    end
    return vars
end

function _substitute_placeholder(expr::EarthSciSerialization.Expr,
                                 placeholder::Union{String, Nothing},
                                 target::String)::EarthSciSerialization.Expr
    placeholder === nothing && return expr
    if expr isa NumExpr || expr isa IntExpr
        return expr
    elseif expr isa VarExpr
        if expr.name == "_var" || expr.name == placeholder ||
           endswith(expr.name, "._var")
            return VarExpr(target)
        end
        return expr
    elseif expr isa OpExpr
        new_args = EarthSciSerialization.Expr[_substitute_placeholder(a, placeholder, target) for a in expr.args]
        new_expr_body = expr.expr_body === nothing ? nothing :
            _substitute_placeholder(expr.expr_body, placeholder, target)
        new_values = expr.values === nothing ? nothing :
            EarthSciSerialization.Expr[_substitute_placeholder(v, placeholder, target) for v in expr.values]
        return OpExpr(expr.op, new_args;
            wrt=expr.wrt, dim=expr.dim,
            output_idx=expr.output_idx,
            expr_body=new_expr_body,
            reduce=expr.reduce,
            ranges=expr.ranges,
            regions=expr.regions,
            values=new_values,
            shape=expr.shape,
            perm=expr.perm,
            axis=expr.axis,
            fn=expr.fn)
    end
    return expr
end

"""
Apply a `CouplingCouple` entry: attach the connector equations to the
flattened equation list. The connector.equations field may contain full
equation structures; we accept both raw Equation objects and dict-shaped
connector entries.
"""
function _apply_couple!(equations::Vector{Equation},
                        entry::CouplingCouple,
                        file::EsmFile)
    connector = entry.connector
    if haskey(connector, "equations")
        raw = connector["equations"]
        if raw isa AbstractVector
            for item in raw
                if item isa Equation
                    push!(equations, item)
                elseif item isa AbstractDict
                    # If the connector equation is a dict-shaped entry (spec
                    # form) record it as a comment equation placeholder — we
                    # cannot parse expressions here without the full parser.
                    # The typical call path constructs full Equation objects.
                    push!(equations, _coerce_connector_equation(item))
                end
            end
        end
    end
    return
end

function _coerce_connector_equation(entry::AbstractDict)::Equation
    # Minimal coercion: accept already-parsed Expr fields if present; otherwise
    # emit a placeholder that carries the raw dict as a comment so downstream
    # code can still see it was applied.
    lhs = get(entry, "lhs", nothing)
    rhs = get(entry, "rhs", nothing)
    if lhs isa EarthSciSerialization.Expr && rhs isa EarthSciSerialization.Expr
        return Equation(lhs, rhs; _comment="couple")
    end
    return Equation(VarExpr("__coupling_placeholder__"), NumExpr(0.0);
                    _comment=string("couple: ", entry))
end

"""
Apply a `CouplingVariableMap` entry: substitute the `to` parameter/variable
with the `from` variable in every flattened equation. For `param_to_var` and
`conversion_factor`, also promote `to` out of the parameters map.
"""
function _apply_variable_map!(equations::Vector{Equation},
                              params::OrderedDict{String, ModelVariable},
                              entry::CouplingVariableMap)
    from = entry.from
    to = entry.to
    transform = entry.transform

    # Build replacement Expr
    replacement::EarthSciSerialization.Expr = VarExpr(from)
    if transform == "conversion_factor" && entry.factor !== nothing
        replacement = OpExpr("*",
            EarthSciSerialization.Expr[NumExpr(entry.factor::Float64), VarExpr(from)])
    end

    bindings = Dict{String, EarthSciSerialization.Expr}(to => replacement)
    for (i, eq) in enumerate(equations)
        equations[i] = Equation(
            substitute(eq.lhs, bindings),
            substitute(eq.rhs, bindings);
            _comment=eq._comment,
        )
    end

    # For param_to_var / conversion_factor, remove target param from parameter list.
    if (transform == "param_to_var" || transform == "conversion_factor") &&
       haskey(params, to)
        delete!(params, to)
    end
    return
end

# ========================================
# Independent-variable detection
# ========================================

function _compute_independent_variables(equations::Vector{Equation},
                                        file_domains::Union{Dict{String, Domain}, Nothing})::Vector{Symbol}
    ivs = Symbol[:t]
    seen = Set{Symbol}([:t])

    for eq in equations
        for expr in (eq.lhs, eq.rhs)
            for sym in spatial_dims_in_expr(expr)
                if !(sym in seen)
                    push!(ivs, sym)
                    push!(seen, sym)
                end
            end
        end
    end

    # Also inspect the file's top-level domains for spatial axes, so that even
    # an all-ODE reaction system on a 2D domain is reported as living on [t,x,y].
    if file_domains !== nothing
        for (_, dom) in file_domains
            if dom.spatial !== nothing
                for dim_name in keys(dom.spatial)
                    sym = Symbol(dim_name)
                    if !(sym in seen)
                        push!(ivs, sym)
                        push!(seen, sym)
                    end
                end
            end
        end
    end

    return ivs
end

# ========================================
# Top-level flatten (§4.7.5)
# ========================================

"""
    flatten(file::EsmFile) -> FlattenedSystem

Flatten the coupled systems in `file` into a single symbolic representation
per spec §4.7.5 (+ §4.7.6 for hybrid dimension-promoted cases).

Throws `ConflictingDerivativeError` if any species is both the LHS of an
explicit `D(X, t) = ...` equation and a reactant/product of a reaction — such
a system is over-determined.
"""
function flatten(file::EsmFile)::FlattenedSystem
    # Step 0: Pre-flight conflict detection. Spec §4.7.5 item E.
    conflicting = _find_conflicting_derivatives(file)
    if !isempty(conflicting)
        throw(ConflictingDerivativeError(conflicting))
    end

    # Step 0b: Hybrid-flattening preflight checks (§4.7.6 error taxonomy).
    _check_interfaces!(file)
    _check_coupling_domain_coverage!(file)
    _check_variable_map_units!(file)

    states = OrderedDict{String, ModelVariable}()
    params = OrderedDict{String, ModelVariable}()
    observeds = OrderedDict{String, ModelVariable}()
    equations = Equation[]
    continuous_events = ContinuousEvent[]
    discrete_events = DiscreteEvent[]
    source_systems = String[]

    file_domains = file.domains

    # Step 1+2: Collect models.
    if file.models !== nothing
        for (name, model) in file.models
            push!(source_systems, name)
            _collect_model!(states, params, observeds, equations,
                            continuous_events, discrete_events,
                            model, name)
        end
    end

    # Step 1+2: Lower reaction systems to ODEs and collect.
    if file.reaction_systems !== nothing
        for (name, rsys) in file.reaction_systems
            push!(source_systems, name)
            _collect_reaction_system!(states, params, equations,
                                      rsys, name, file_domains)
        end
    end

    # Step 3: Apply coupling rules.
    coupling_rules_applied = String[]
    opaque_refs = String[]
    dimension_promotions = NamedTuple[]

    for entry in file.coupling
        push!(coupling_rules_applied, describe_coupling_entry(entry))
        if entry isa CouplingOperatorCompose
            _apply_operator_compose!(equations, entry, file)
        elseif entry isa CouplingCouple
            _apply_couple!(equations, entry, file)
        elseif entry isa CouplingVariableMap
            _apply_variable_map!(equations, params, entry)
        elseif entry isa CouplingOperatorApply
            push!(opaque_refs, "operator_apply:$(entry.operator)")
        elseif entry isa CouplingCallback
            push!(opaque_refs, "callback:$(entry.callback_id)")
        elseif entry isa CouplingEvent
            push!(opaque_refs, "event:$(entry.event_type)")
        end
    end

    # Step 4: Compute independent variables.
    ivs = _compute_independent_variables(equations, file_domains)

    # Step 5: Assemble FlattenedSystem.
    # Pick a representative domain if the file has exactly one; else nothing.
    target_domain = if file_domains !== nothing && length(file_domains) == 1
        first(values(file_domains))
    else
        nothing
    end

    metadata = FlattenMetadata(
        sort!(collect(source_systems)),
        coupling_rules_applied;
        dimension_promotions_applied=dimension_promotions,
        opaque_coupling_refs=opaque_refs,
    )

    return FlattenedSystem(
        ivs, states, params, observeds,
        equations, continuous_events, discrete_events,
        target_domain, metadata,
    )
end

"""
    flatten(model::Model; name::String="anonymous") -> FlattenedSystem

Convenience: wrap a single Model in a synthetic EsmFile (with a default system
name) and run the full flattener. This is the call path used by
`ModelingToolkit.System(::Model)` in the Julia extension (see gt-fpw).
"""
function flatten(model::Model; name::String="anonymous")::FlattenedSystem
    file = EsmFile("0.1.0", Metadata(name);
                   models=Dict{String, Model}(name => model))
    return flatten(file)
end

"""
    flatten(rsys::ReactionSystem; name::String="anonymous") -> FlattenedSystem

Convenience: wrap a ReactionSystem in a synthetic EsmFile and flatten.
"""
function flatten(rsys::ReactionSystem; name::String="anonymous")::FlattenedSystem
    file = EsmFile("0.1.0", Metadata(name);
                   reaction_systems=Dict{String, ReactionSystem}(name => rsys))
    return flatten(file)
end

# ========================================
# Coupling entry descriptions (unchanged from prior implementation)
# ========================================

"""
    describe_coupling_entry(entry::CouplingEntry) -> String

Produce a human-readable description of a coupling entry for the flattened
system's metadata.
"""
function describe_coupling_entry(entry::CouplingEntry)::String
    if entry isa CouplingOperatorCompose
        systems_str = join(entry.systems, " + ")
        desc = "operator_compose($(systems_str))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingCouple
        systems_str = join(entry.systems, " <-> ")
        desc = "couple($(systems_str))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingVariableMap
        desc = "variable_map($(entry.from) -> $(entry.to), transform=$(entry.transform))"
        if entry.factor !== nothing
            desc *= " [factor=$(entry.factor)]"
        end
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingOperatorApply
        desc = "operator_apply($(entry.operator))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingCallback
        desc = "callback($(entry.callback_id))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingEvent
        desc = "event($(entry.event_type))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    else
        return "unknown_coupling($(typeof(entry)))"
    end
end

# ========================================
# Array-variable shape inference (gt-vt3)
# ========================================

"""
    infer_array_shapes(equations::Vector{Equation}) -> Dict{String, Vector{UnitRange{Int}}}

Walk every `arrayop`, `makearray`, and `index` node in the equation set and
compute, for each array-shaped variable, the union of ranges observed across
all references. The result maps variable name → per-axis `UnitRange{Int}`
vector (empty for scalar variables; one entry per dimension for array
variables). Only variables that actually appear inside an array operator get
a shape — scalar variables are absent from the result dict.

Semantics:
- For a `VarExpr` appearing as the first argument of an `index` node, each
  subsequent argument is an index expression (literal int, symbolic index
  name, or affine offset like `i+1`). The range of that index determines the
  variable's length on that axis. Affine offsets widen the required range
  (e.g. `u[i-1]` and `u[i+1]` in `i in 2:9` force `u` to span `1:10`).
- For an `arrayop`, its `output_idx` and `ranges` combined define the
  iteration space. Index names with no explicit range are left for
  inference from their usages inside the body.
- Conflicts: if a variable is referenced with inconsistent dimensionality
  across equations, this function raises an `ArgumentError`.

This pass is deliberately standalone — it does not mutate `FlattenedSystem`.
It is called at MTK build time from `ext/EarthSciSerializationMTKExt.jl` so
scalar-only callers pay no cost.
"""
function infer_array_shapes(equations::Vector{Equation})
    shapes = Dict{String,Vector{UnitRange{Int}}}()
    for eq in equations
        _scan_shape!(shapes, eq.lhs, Dict{String,UnitRange{Int}}())
        _scan_shape!(shapes, eq.rhs, Dict{String,UnitRange{Int}}())
    end
    return shapes
end

# Walk an expression tree recording per-variable axis extents. `idx_env`
# maps index-symbol name (`"i"`, `"j"`) to the UnitRange it iterates over
# in the enclosing `arrayop`, so `index(u, i-1, j+1)` inside `i in 2:9` can
# be resolved to a concrete range on each axis.
function _scan_shape!(shapes::Dict{String,Vector{UnitRange{Int}}},
                      expr::Expr,
                      idx_env::Dict{String,UnitRange{Int}})
    if expr isa NumExpr || expr isa IntExpr || expr isa VarExpr
        return
    end
    expr isa OpExpr || return

    if expr.op == "index"
        _record_index!(shapes, expr, idx_env)
        for a in expr.args[2:end]
            _scan_shape!(shapes, a, idx_env)
        end
        return
    end

    if expr.op == "arrayop"
        # Extend idx_env with any explicit ranges declared on this node.
        new_env = copy(idx_env)
        if expr.ranges !== nothing
            for (name, r) in expr.ranges
                lo, hi = _range_bounds(r)
                new_env[name] = lo:hi
            end
        end
        if expr.expr_body !== nothing
            _scan_shape!(shapes, expr.expr_body, new_env)
        end
        for a in expr.args
            _scan_shape!(shapes, a, new_env)
        end
        return
    end

    if expr.op == "makearray"
        if expr.values !== nothing
            for v in expr.values
                _scan_shape!(shapes, v, idx_env)
            end
        end
        for a in expr.args
            _scan_shape!(shapes, a, idx_env)
        end
        return
    end

    # Generic recursion for other operators (+, -, *, /, ^, elementary
    # functions, D, grad, etc.). The optional `expr_body` field is scanned
    # only for array ops above, so we skip it here.
    for a in expr.args
        _scan_shape!(shapes, a, idx_env)
    end
end

function _range_bounds(r::Vector{Int})
    if length(r) == 2
        return r[1], r[2]
    elseif length(r) == 3
        return r[1], r[3]  # [start, step, stop]
    end
    throw(ArgumentError("range must have 2 or 3 entries, got $(length(r))"))
end

# Record a shape entry for `u` from `index(u, i1, i2, ...)`. Each index
# expression is evaluated against `idx_env` to determine the range it
# sweeps over on that axis. Returns nothing on a miss (scalar access).
function _record_index!(shapes::Dict{String,Vector{UnitRange{Int}}},
                        idx_node::OpExpr,
                        idx_env::Dict{String,UnitRange{Int}})
    isempty(idx_node.args) && return
    first_arg = idx_node.args[1]
    first_arg isa VarExpr || return
    vname = first_arg.name
    axis_ranges = UnitRange{Int}[]
    for idx_expr in idx_node.args[2:end]
        r = _eval_index_range(idx_expr, idx_env)
        r === nothing && return  # opaque — can't infer this axis
        push!(axis_ranges, r)
    end

    if haskey(shapes, vname)
        existing = shapes[vname]
        if length(existing) != length(axis_ranges)
            throw(ArgumentError(
                "Inconsistent dimensionality for variable '$vname': " *
                "saw $(length(existing))-D and $(length(axis_ranges))-D references"))
        end
        for (i, r) in enumerate(axis_ranges)
            existing[i] = min(first(existing[i]), first(r)):max(last(existing[i]), last(r))
        end
    else
        shapes[vname] = axis_ranges
    end
end

# Evaluate an index expression against the index-symbol environment.
# Supports: integer literals, bare index symbols (VarExpr in idx_env), and
# affine offsets `op("+", [idx, NumExpr(k)])` / `op("-", ...)` with either
# operand order. Returns a UnitRange representing the range that expression
# sweeps, or `nothing` if the shape cannot be inferred from this node alone.
function _eval_index_range(idx_expr::Expr, idx_env::Dict{String,UnitRange{Int}})
    if idx_expr isa IntExpr
        v = Int(idx_expr.value)
        return v:v
    elseif idx_expr isa NumExpr
        v = Int(idx_expr.value)
        return v:v
    elseif idx_expr isa VarExpr
        if haskey(idx_env, idx_expr.name)
            return idx_env[idx_expr.name]
        end
        return nothing
    elseif idx_expr isa OpExpr && idx_expr.op in ("+", "-") && length(idx_expr.args) == 2
        a, b = idx_expr.args
        base, offset = _split_affine(a, b)
        base === nothing && return nothing
        haskey(idx_env, base) || return nothing
        env_r = idx_env[base]
        shift = idx_expr.op == "+" ? offset : -offset
        return (first(env_r) + shift):(last(env_r) + shift)
    end
    return nothing
end

function _split_affine(a::Expr, b::Expr)
    if a isa VarExpr && b isa IntExpr
        return a.name, Int(b.value)
    elseif a isa IntExpr && b isa VarExpr
        return b.name, Int(a.value)
    elseif a isa VarExpr && b isa NumExpr
        return a.name, Int(b.value)
    elseif a isa NumExpr && b isa VarExpr
        return b.name, Int(a.value)
    end
    return nothing, 0
end
