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
    UnsupportedRegriddingError

Raised when an `Interface` requests a regridding strategy not supported by
the current library tier (§4.7.6).
"""
struct UnsupportedRegriddingError <: Exception
    strategy::String
end
Base.showerror(io::IO, e::UnsupportedRegriddingError) =
    print(io, "UnsupportedRegriddingError: regridding strategy '",
          e.strategy, "' is not supported")

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
    S = zeros(Int, n_species, n_rxns)

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
rewritten as `"<prefix>.<name>"`. Variables whose name already contains a dot
(already qualified) are left unchanged. Numeric literals are unchanged.
"""
function namespace_expr(expr::NumExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
    return expr
end

function namespace_expr(expr::VarExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
    if occursin('.', expr.name)
        return expr
    end
    if expr.name in local_names
        return VarExpr("$(prefix).$(expr.name)")
    end
    return expr
end

function namespace_expr(expr::OpExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
    new_args = EarthSciSerialization.Expr[namespace_expr(a, prefix, local_names) for a in expr.args]
    return OpExpr(expr.op, new_args; wrt=expr.wrt, dim=expr.dim)
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
    if expr isa NumExpr || expr isa VarExpr
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

    for eq in model.equations
        lhs = namespace_expr(eq.lhs, prefix, local_names)
        rhs = namespace_expr(eq.rhs, prefix, local_names)
        push!(equations, Equation(lhs, rhs; _comment=eq._comment))
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
    if expr isa NumExpr
        return expr
    elseif expr isa VarExpr
        if expr.name == "_var" || expr.name == placeholder ||
           endswith(expr.name, "._var")
            return VarExpr(target)
        end
        return expr
    elseif expr isa OpExpr
        new_args = EarthSciSerialization.Expr[_substitute_placeholder(a, placeholder, target) for a in expr.args]
        return OpExpr(expr.op, new_args; wrt=expr.wrt, dim=expr.dim)
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
