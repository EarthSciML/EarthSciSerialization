module EarthSciSerializationMTKExt

using EarthSciSerialization
# Note: we deliberately do NOT import `Expr` from EarthSciSerialization into
# this extension's namespace — that would shadow Core.Expr and break the
# `Symbolics.@variables` macro call we use for programmatic variable creation
# (the macro's generated code references Core.Expr).
using EarthSciSerialization: FlattenedSystem, ModelVariable, StateVariable,
    ParameterVariable, ObservedVariable, NumExpr, VarExpr, OpExpr,
    Equation, AffectEquation, Model, EventType, ContinuousEvent, DiscreteEvent,
    ConditionTrigger, PeriodicTrigger, PresetTimesTrigger, FunctionalAffect,
    Domain, flatten
const EsmExpr = EarthSciSerialization.Expr
using ModelingToolkit
using ModelingToolkit: @variables, @parameters, Differential, System, PDESystem
using Symbolics
using Symbolics: Num
using DomainSets: Interval

# ========================================
# ESM Expr → Symbolics conversion
# ========================================

"""
Build a Symbolics.jl expression from an ESM `Expr` tree, using the given
variable dictionary (name → symbolic variable) and the time symbol `t_sym`.
Spatial dimension symbols are created on demand and cached in `dim_dict`.
"""
function _esm_to_symbolic(expr::EsmExpr, var_dict::Dict{String,Any},
                          t_sym, dim_dict::Dict{String,Any})
    if expr isa NumExpr
        return expr.value
    elseif expr isa VarExpr
        if haskey(var_dict, expr.name)
            return var_dict[expr.name]
        elseif haskey(dim_dict, expr.name)
            return dim_dict[expr.name]
        else
            error("Variable '$(expr.name)' not found in variable dictionary")
        end
    elseif expr isa OpExpr
        op = expr.op
        if op == "D"
            arg = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            wrt_name = expr.wrt === nothing ? "t" : expr.wrt
            if wrt_name == "t"
                return Differential(t_sym)(arg)
            else
                dim_sym = _get_or_make_dim(dim_dict, wrt_name)
                return Differential(dim_sym)(arg)
            end
        elseif op == "grad"
            arg = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            expr.dim === nothing && error("grad operator requires dim parameter")
            dim_sym = _get_or_make_dim(dim_dict, expr.dim)
            return Differential(dim_sym)(arg)
        elseif op == "div"
            arg = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            expr.dim === nothing && error("div operator requires dim parameter")
            dim_sym = _get_or_make_dim(dim_dict, expr.dim)
            return Differential(dim_sym)(arg)
        elseif op == "laplacian"
            arg = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            x_sym = _get_or_make_dim(dim_dict, "x")
            y_sym = _get_or_make_dim(dim_dict, "y")
            z_sym = _get_or_make_dim(dim_dict, "z")
            Dx = Differential(x_sym)
            Dy = Differential(y_sym)
            Dz = Differential(z_sym)
            return Dx(Dx(arg)) + Dy(Dy(arg)) + Dz(Dz(arg))
        elseif op == "+"
            args = [_esm_to_symbolic(a, var_dict, t_sym, dim_dict) for a in expr.args]
            return length(args) == 1 ? args[1] : sum(args)
        elseif op == "-"
            args = [_esm_to_symbolic(a, var_dict, t_sym, dim_dict) for a in expr.args]
            return length(args) == 1 ? -args[1] : args[1] - args[2]
        elseif op == "*"
            args = [_esm_to_symbolic(a, var_dict, t_sym, dim_dict) for a in expr.args]
            return length(args) == 1 ? args[1] : prod(args)
        elseif op == "/"
            l = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            r = _esm_to_symbolic(expr.args[2], var_dict, t_sym, dim_dict)
            return l / r
        elseif op == "^"
            l = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            r = _esm_to_symbolic(expr.args[2], var_dict, t_sym, dim_dict)
            return l^r
        elseif op in ("exp", "log", "log10", "sin", "cos", "tan",
                      "sinh", "cosh", "tanh", "asin", "acos", "atan",
                      "sqrt", "abs")
            arg = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            fn = getfield(Base, Symbol(op))
            return fn(arg)
        elseif op == "ifelse"
            cond = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            t_val = _esm_to_symbolic(expr.args[2], var_dict, t_sym, dim_dict)
            f_val = _esm_to_symbolic(expr.args[3], var_dict, t_sym, dim_dict)
            return ifelse(cond, t_val, f_val)
        elseif op == "Pre"
            arg = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            return ModelingToolkit.Pre(arg)
        elseif op in (">", "<", ">=", "<=", "==", "!=")
            l = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
            r = _esm_to_symbolic(expr.args[2], var_dict, t_sym, dim_dict)
            return op == ">"  ? l > r  :
                   op == "<"  ? l < r  :
                   op == ">=" ? l >= r :
                   op == "<=" ? l <= r :
                   op == "==" ? l == r :
                                l != r
        else
            error("Unsupported operator: $op")
        end
    end
    error("Unknown expression type: $(typeof(expr))")
end

function _get_or_make_dim(dim_dict::Dict{String,Any}, name::AbstractString)
    if haskey(dim_dict, name)
        return dim_dict[name]
    end
    v = Symbolics.variable(Symbol(name))
    dim_dict[String(name)] = v
    return v
end

"""
    _make_dep_var(name::Symbol, iv_syms::Vector{Any}) -> Num

Construct a symbolic variable of the form `name(iv1, iv2, ...)`, where the
`iv_syms` vector contains the actual symbolic objects to use as arguments.
Uses the public `Symbolics.@variables` macro via `Core.eval` so we remain
robust to changes in `FnType`'s parameter list across Symbolics versions.

We build a quoted expression of the form
```
let
    \$iv1_ref = \$iv1
    ...
    @variables name(\$iv1_ref, ...)
end
```
so the IVs are passed by value into the macro's scope.
"""
function _make_dep_var(name::Symbol, iv_syms::Vector{Any})
    # Invent placeholder names so the macro sees valid identifiers
    holder_names = [Symbol("__esm_iv_", i) for i in 1:length(iv_syms)]
    bindings = [Core.Expr(:(=), holder_names[i], iv_syms[i]) for i in 1:length(iv_syms)]
    call_expr = Core.Expr(:call, name, holder_names...)
    block_expr = Core.Expr(:block, bindings..., :(Symbolics.@variables $(call_expr)))
    let_expr = Core.Expr(:let, Core.Expr(:block), block_expr)
    vars = Core.eval(Symbolics, let_expr)
    return vars[1]
end

"""
    _make_param(name::Symbol) -> Num

Construct a plain parameter symbol `name` using `Symbolics.@parameters`.
"""
function _make_param(name::Symbol)
    vars = Core.eval(Symbolics, :(@variables $(name)))
    return vars[1]
end

# ========================================
# Build symbolic variable dictionaries from a FlattenedSystem
# ========================================

function _pde_independent_vars(flat::FlattenedSystem)
    return !(length(flat.independent_variables) == 1 &&
             flat.independent_variables[1] == :t)
end

"""
Create Symbolics.jl variable/parameter symbols for every state, parameter, and
observed variable in a flattened system. Returns `(var_dict, t_sym, dim_dict,
states, parameters, observed)` where the collections are typed `Vector{Num}`.

For ODE systems, state variables are functions of `t` only. For PDE systems,
state variables are functions of `t` and the spatial dimensions declared in
`flat.independent_variables` (minus `:t`).
"""
function _build_var_dict(flat::FlattenedSystem)
    is_pde = _pde_independent_vars(flat)

    # Independent variables
    t_sym = _get_or_make_dim(Dict{String,Any}(), "t")
    dim_dict = Dict{String,Any}("t" => t_sym)

    spatial_syms = Any[]
    if is_pde
        for iv in flat.independent_variables
            iv == :t && continue
            dim_sym = _get_or_make_dim(dim_dict, String(iv))
            push!(spatial_syms, dim_sym)
        end
    end

    var_dict = Dict{String,Any}()
    states = Vector{Num}()
    parameters = Vector{Num}()
    observed = Vector{Num}()

    # Concrete IV symbol objects to pass to the @variables macro via our
    # _make_dep_var helper (see the bindings trick inside that function).
    iv_syms_any = Any[t_sym]
    for s in spatial_syms
        push!(iv_syms_any, s)
    end

    # Sanitize names for use as Julia symbols (dots in "System.var" would
    # otherwise produce invalid symbols in the generated @variables call).
    _san(s::AbstractString) = Symbol(replace(String(s), '.' => '_'))

    # State variables — functions of independent variables
    for (vname, _mvar) in flat.state_variables
        sym_name = _san(vname)
        v_num = _make_dep_var(sym_name, iv_syms_any)
        push!(states, v_num)
        var_dict[vname] = v_num
    end

    # Parameters — plain symbols
    for (pname, _mvar) in flat.parameters
        p_num = _make_param(_san(pname))
        push!(parameters, p_num)
        var_dict[pname] = p_num
    end

    # Observed variables — same shape as states
    for (oname, _mvar) in flat.observed_variables
        ov_num = _make_dep_var(_san(oname), iv_syms_any)
        push!(observed, ov_num)
        var_dict[oname] = ov_num
    end

    return var_dict, t_sym, dim_dict, states, parameters, observed, spatial_syms
end

# ========================================
# Event conversion
# ========================================

function _affect_to_eq(affect, var_dict::Dict{String,Any}, t_sym, dim_dict)
    if affect isa AffectEquation
        if !haskey(var_dict, affect.lhs)
            @warn "Target variable $(affect.lhs) not found for event affect"
            return nothing
        end
        target = var_dict[affect.lhs]
        rhs = _esm_to_symbolic(affect.rhs, var_dict, t_sym, dim_dict)
        return target ~ rhs
    elseif affect isa FunctionalAffect
        if !haskey(var_dict, affect.target)
            @warn "Target variable $(affect.target) not found for event affect"
            return nothing
        end
        target = var_dict[affect.target]
        rhs = _esm_to_symbolic(affect.expression, var_dict, t_sym, dim_dict)
        if affect.operation == "set"
            return target ~ rhs
        elseif affect.operation == "add"
            return target ~ target + rhs
        elseif affect.operation == "multiply"
            return target ~ target * rhs
        else
            @warn "Unknown affect operation: $(affect.operation)"
            return target ~ rhs
        end
    end
    return nothing
end

function _build_continuous_events(flat::FlattenedSystem, var_dict, t_sym, dim_dict)
    cbs = Any[]
    for ev in flat.continuous_events
        conds = [_esm_to_symbolic(c, var_dict, t_sym, dim_dict) for c in ev.conditions]
        affects = filter(!isnothing,
                         [_affect_to_eq(a, var_dict, t_sym, dim_dict) for a in ev.affects])
        isempty(conds) || isempty(affects) && continue
        cb = ModelingToolkit.SymbolicContinuousCallback(conds[1], affects)
        push!(cbs, cb)
    end
    return cbs
end

function _build_discrete_events(flat::FlattenedSystem, var_dict, t_sym, dim_dict)
    cbs = Any[]
    for ev in flat.discrete_events
        affects = filter(!isnothing,
                         [_affect_to_eq(a, var_dict, t_sym, dim_dict) for a in ev.affects])
        isempty(affects) && continue
        if ev.trigger isa ConditionTrigger
            cond = _esm_to_symbolic(ev.trigger.expression, var_dict, t_sym, dim_dict)
            push!(cbs, ModelingToolkit.SymbolicDiscreteCallback(cond, affects))
        elseif ev.trigger isa PeriodicTrigger
            push!(cbs, ModelingToolkit.SymbolicDiscreteCallback(ev.trigger.period, affects))
        elseif ev.trigger isa PresetTimesTrigger
            if !isempty(ev.trigger.times)
                push!(cbs, ModelingToolkit.SymbolicDiscreteCallback(ev.trigger.times[1], affects))
            end
        end
    end
    return cbs
end

# ========================================
# ModelingToolkit.System constructors
# ========================================

"""
    ModelingToolkit.System(flat::FlattenedSystem; name=:anonymous, kwargs...)

Build a real `ModelingToolkit.ODESystem`/`System` from a flattened ESM system.
Errors with a clear redirect to `ModelingToolkit.PDESystem` when the flattened
system has spatial independent variables.
"""
function ModelingToolkit.System(flat::FlattenedSystem;
                                name::Union{Symbol,AbstractString}=:anonymous,
                                kwargs...)
    if _pde_independent_vars(flat)
        throw(ArgumentError(
            "Flattened system has independent variables $(flat.independent_variables), " *
            "which indicates a PDE. Use ModelingToolkit.PDESystem(...) instead of " *
            "ModelingToolkit.System(...)."
        ))
    end

    var_dict, t_sym, dim_dict, states, parameters, observed, _ =
        _build_var_dict(flat)

    MTKEquation = ModelingToolkit.Equation
    eqs = Vector{MTKEquation}()
    for eq in flat.equations
        lhs = _esm_to_symbolic(eq.lhs, var_dict, t_sym, dim_dict)
        rhs = _esm_to_symbolic(eq.rhs, var_dict, t_sym, dim_dict)
        push!(eqs, lhs ~ rhs)
    end

    cont_cbs = _build_continuous_events(flat, var_dict, t_sym, dim_dict)
    disc_cbs = _build_discrete_events(flat, var_dict, t_sym, dim_dict)

    sys_name = name isa Symbol ? name : Symbol(name)

    sys = if !isempty(cont_cbs) && !isempty(disc_cbs)
        ModelingToolkit.System(eqs, t_sym, states, parameters;
            name=sys_name,
            continuous_events=cont_cbs,
            discrete_events=disc_cbs, kwargs...)
    elseif !isempty(cont_cbs)
        ModelingToolkit.System(eqs, t_sym, states, parameters;
            name=sys_name, continuous_events=cont_cbs, kwargs...)
    elseif !isempty(disc_cbs)
        ModelingToolkit.System(eqs, t_sym, states, parameters;
            name=sys_name, discrete_events=disc_cbs, kwargs...)
    else
        ModelingToolkit.System(eqs, t_sym, states, parameters;
            name=sys_name, kwargs...)
    end
    return sys
end

"""
    ModelingToolkit.System(model::Model; name=:anonymous, kwargs...)

Convenience: flatten the model first, then build the `System`.
"""
function ModelingToolkit.System(model::Model;
                                name::Union{Symbol,AbstractString}=:anonymous,
                                kwargs...)
    flat = flatten(model; name=String(name isa Symbol ? name : Symbol(name)))
    return ModelingToolkit.System(flat; name=name, kwargs...)
end

# ========================================
# ModelingToolkit.PDESystem constructors
# ========================================

"""
    ModelingToolkit.PDESystem(flat::FlattenedSystem; name=:anonymous, kwargs...)

Build a `ModelingToolkit.PDESystem` from a flattened ESM system. Errors with
a clear redirect to `ModelingToolkit.System` when the flattened system is a
pure ODE.

Boundary conditions are derived from the flattened system's domain and any
slice-derived surface source patterns (see below). Initial conditions come
from variable defaults.

## Surface-source → flux boundary condition lowering

When the flattened system includes a state variable of the form `V.at_z`
that is defined by both:
1. A slice connector `V.at_z = V(t, ..., z_0)`, and
2. An ODE `D(V.at_z, t) = f(...)`,
and `V` itself participates in a diffusive PDE `D(V, t) = D_coeff *
Differential(z)(Differential(z)(V))`, the constructor emits a flux boundary
condition at `z = z_0` of the form
`D_coeff * Differential(z)(V)(t, z_0) ~ f(...)` and drops the ODE on the slice
variable. This implements the Julia-specific convention (§5.1) that
slice-derived surface source equations become flux BCs rather than pointwise
source terms in the lowest grid cell.
"""
function ModelingToolkit.PDESystem(flat::FlattenedSystem;
                                   name::Union{Symbol,AbstractString}=:anonymous,
                                   kwargs...)
    if !_pde_independent_vars(flat)
        throw(ArgumentError(
            "Flattened system has independent variables [t] only — this is a " *
            "pure ODE system. Use ModelingToolkit.System(...) instead of " *
            "ModelingToolkit.PDESystem(...)."
        ))
    end

    var_dict, t_sym, dim_dict, states, parameters, observed, spatial_syms =
        _build_var_dict(flat)

    # ------------------------------------------------------------
    # Detect slice-derived surface source pattern
    # ------------------------------------------------------------
    # For each state variable with a name of the form "<prefix>.at_<dim>",
    # check if there is:
    #   (1) a connector equation "<prefix>.at_<dim> ~ <base>(t, ..., <dim_0>)"
    #   (2) an ODE equation "D(<prefix>.at_<dim>, t) ~ f(...)"
    #   (3) a base variable <base> that appears in a diffusive PDE equation.
    # If so, emit a flux BC and drop the slice-ODE.
    slice_bcs, slice_vars_to_drop = _lower_slice_sources_to_bcs!(
        flat, var_dict, t_sym, dim_dict)

    MTKEquation = ModelingToolkit.Equation
    eqs = Vector{MTKEquation}()
    for eq in flat.equations
        # Skip ODEs on slice variables that were lowered to flux BCs
        if _is_odelhs_for_slice_var(eq, slice_vars_to_drop)
            continue
        end
        lhs = _esm_to_symbolic(eq.lhs, var_dict, t_sym, dim_dict)
        rhs = _esm_to_symbolic(eq.rhs, var_dict, t_sym, dim_dict)
        push!(eqs, lhs ~ rhs)
    end

    # ------------------------------------------------------------
    # Initial conditions from variable defaults
    # ------------------------------------------------------------
    ics = MTKEquation[]
    for (vname, mvar) in flat.state_variables
        if mvar.default !== nothing && haskey(var_dict, vname)
            v = var_dict[vname]
            push!(ics, v ~ Float64(mvar.default))
        end
    end

    # Merge slice-derived BCs with any domain-declared BCs
    bcs = slice_bcs

    # Build the independent variable vector and domain specification
    iv_syms = [t_sym; spatial_syms...]

    domain_spec = _build_domain_spec(flat.domain, dim_dict, t_sym, spatial_syms)

    sys_name = name isa Symbol ? name : Symbol(name)

    dvars = [Num(v) for v in states]

    return ModelingToolkit.PDESystem(eqs, bcs, domain_spec, iv_syms, dvars,
                                     parameters; name=sys_name, kwargs...)
end

"""
    ModelingToolkit.PDESystem(model::Model; name=:anonymous, kwargs...)
"""
function ModelingToolkit.PDESystem(model::Model;
                                   name::Union{Symbol,AbstractString}=:anonymous,
                                   kwargs...)
    flat = flatten(model; name=String(name isa Symbol ? name : Symbol(name)))
    return ModelingToolkit.PDESystem(flat; name=name, kwargs...)
end

# ------------------------------------------------------------
# Slice-source detection helpers
# ------------------------------------------------------------

"""
Return the list of state-variable names of the form `"<prefix>.at_<dim>"`
that look like slice connectors for a spatial dimension declared in `flat.
independent_variables`.
"""
function _find_slice_candidates(flat::FlattenedSystem)
    spatial_dims = [String(iv) for iv in flat.independent_variables if iv != :t]
    candidates = String[]
    for vname in keys(flat.state_variables)
        idx = findlast('.', vname)
        idx === nothing && continue
        tail = vname[(idx+1):end]
        startswith(tail, "at_") || continue
        dim = tail[4:end]
        dim in spatial_dims && push!(candidates, vname)
    end
    return candidates
end

"""
Walk the flattened equations and, for each slice-candidate state variable,
check for both a connector-form algebraic equation and a D(·,t) ODE. If
both exist and the base variable has a diffusive equation in the PDE set,
emit a flux boundary condition and mark the slice variable for removal.
"""
function _lower_slice_sources_to_bcs!(flat::FlattenedSystem,
                                      var_dict, t_sym, dim_dict)
    MTKEquation = ModelingToolkit.Equation
    bcs = MTKEquation[]
    drop = Set{String}()

    candidates = _find_slice_candidates(flat)
    isempty(candidates) && return bcs, drop

    for slice_name in candidates
        # Extract base prefix + slice dim from the candidate name
        base_dot = findlast('.', slice_name)
        base_dot === nothing && continue
        prefix = slice_name[1:(base_dot-1)]
        tail = slice_name[(base_dot+1):end]  # e.g. "at_z"
        dim_name = tail[4:end]                # "z"
        base_name = prefix                    # we emit flux BC on the "prefix" base var
        haskey(var_dict, base_name) || continue

        # Find an ODE equation on the slice variable
        ode_rhs = nothing
        for eq in flat.equations
            if _lhs_is_D_of(eq.lhs, slice_name)
                ode_rhs = eq.rhs
                break
            end
        end
        ode_rhs === nothing && continue

        # Find a diffusive equation on the base variable to extract the
        # diffusion coefficient. Pattern: D(base, t) ~ D_coeff * Differential(dim)(Differential(dim)(base))
        D_coeff_sym = nothing
        for eq in flat.equations
            if _lhs_is_D_of(eq.lhs, base_name)
                D_coeff_sym = _extract_diffusion_coefficient(eq.rhs, base_name, dim_name)
                D_coeff_sym !== nothing && break
            end
        end
        D_coeff_sym === nothing && continue

        # Substitute slice-variable references with the base variable in the
        # ODE rhs: the BC RHS should reference the base field at z=0, not the
        # slice-connector intermediate.
        ode_rhs_sub = _substitute_varname(ode_rhs, slice_name, base_name)

        dim_sym = _get_or_make_dim(dim_dict, dim_name)
        base_var = var_dict[base_name]
        D_coeff_val = _esm_to_symbolic(D_coeff_sym, var_dict, t_sym, dim_dict)
        rhs_sym = _esm_to_symbolic(ode_rhs_sub, var_dict, t_sym, dim_dict)

        # Flux BC: D_coeff * ∂(base)/∂dim ~ rhs_of_slice_ode (with slice var
        # rewritten to base var). For now we emit the BC unconditionally —
        # users can pin it to `dim = 0` via the domain spec.
        flux_lhs = D_coeff_val * Differential(dim_sym)(base_var)
        push!(bcs, flux_lhs ~ rhs_sym)

        push!(drop, slice_name)
    end

    return bcs, drop
end

"Substitute every `VarExpr(old)` with `VarExpr(new)` in an Expr tree."
function _substitute_varname(expr::EsmExpr, old::AbstractString, new::AbstractString)
    if expr isa VarExpr
        return expr.name == old ? VarExpr(String(new)) : expr
    elseif expr isa NumExpr
        return expr
    elseif expr isa OpExpr
        new_args = EsmExpr[_substitute_varname(a, old, new) for a in expr.args]
        return OpExpr(expr.op, new_args; wrt=expr.wrt, dim=expr.dim)
    else
        return expr
    end
end

function _lhs_is_D_of(lhs::EsmExpr, var_name::String)
    lhs isa OpExpr || return false
    lhs.op == "D" || return false
    length(lhs.args) >= 1 || return false
    inner = lhs.args[1]
    inner isa VarExpr || return false
    return inner.name == var_name
end

"""
Look for a diffusion term `D_coeff * Differential(dim)(Differential(dim)(base))`
in an Expr tree and return `D_coeff` as an Expr. Very simple pattern matcher:
expects the Expr to be a `*` with two operands or a `+`/`-` with one operand
shaped this way. Returns `nothing` if not found.
"""
function _extract_diffusion_coefficient(expr::EsmExpr, base_name::String,
                                        dim_name::String)
    expr isa OpExpr || return nothing
    if expr.op == "*" && length(expr.args) == 2
        a, b = expr.args
        if _is_d2_of(b, base_name, dim_name)
            return a
        elseif _is_d2_of(a, base_name, dim_name)
            return b
        end
    elseif expr.op == "laplacian" && length(expr.args) == 1
        inner = expr.args[1]
        if inner isa VarExpr && inner.name == base_name
            # D * laplacian(base) not expressible here without outer coefficient
            return nothing
        end
    elseif expr.op in ("+", "-")
        for arg in expr.args
            found = _extract_diffusion_coefficient(arg, base_name, dim_name)
            found !== nothing && return found
        end
    end
    return nothing
end

function _is_d2_of(expr::EsmExpr, var_name::String, dim_name::String)
    expr isa OpExpr || return false
    expr.op == "grad" || return false
    expr.dim == dim_name || return false
    length(expr.args) == 1 || return false
    inner = expr.args[1]
    inner isa OpExpr || return false
    inner.op == "grad" || return false
    inner.dim == dim_name || return false
    length(inner.args) == 1 || return false
    innermost = inner.args[1]
    return innermost isa VarExpr && innermost.name == var_name
end

_is_odelhs_for_slice_var(eq::Equation, drop::Set{String}) =
    _lhs_is_D_of(eq.lhs, "") ? false :
    any(v -> _lhs_is_D_of(eq.lhs, v), drop)

# ------------------------------------------------------------
# Domain specification helper
# ------------------------------------------------------------

function _build_domain_spec(domain::Union{Domain,Nothing}, dim_dict,
                            t_sym, spatial_syms)
    if domain === nothing
        # Default: 0 ≤ t, and each spatial dim over [0, 1]
        specs = Any[t_sym ∈ Interval(0.0, 1.0)]
        for sym in spatial_syms
            push!(specs, sym ∈ Interval(0.0, 1.0))
        end
        return specs
    end

    specs = Any[]
    if domain.temporal !== nothing
        for (name, bounds) in domain.temporal
            haskey(dim_dict, name) || continue
            lo, hi = _parse_bounds(bounds)
            push!(specs, dim_dict[name] ∈ Interval(lo, hi))
        end
    end
    if domain.spatial !== nothing
        for (name, bounds) in domain.spatial
            haskey(dim_dict, name) || continue
            lo, hi = _parse_bounds(bounds)
            push!(specs, dim_dict[name] ∈ Interval(lo, hi))
        end
    end
    return specs
end

function _parse_bounds(bounds)
    if bounds isa AbstractVector && length(bounds) >= 2
        return Float64(bounds[1]), Float64(bounds[2])
    elseif bounds isa AbstractDict
        lo = get(bounds, "min", get(bounds, :min, 0.0))
        hi = get(bounds, "max", get(bounds, :max, 1.0))
        return Float64(lo), Float64(hi)
    end
    return 0.0, 1.0
end

# ========================================
# Reverse direction: MTK → ESM Model
# ========================================

"""
    EarthSciSerialization.Model(sys::ModelingToolkit.AbstractSystem)

Convert a ModelingToolkit System back to an ESM `Model`. Supports ODESystems
and systems that expose `unknowns`, `parameters`, and `equations`.
"""
function EarthSciSerialization.Model(sys::ModelingToolkit.AbstractSystem)
    variables = Dict{String,ModelVariable}()

    for state in ModelingToolkit.unknowns(sys)
        var_name = _strip_time(string(ModelingToolkit.getname(state)))
        default_val = try
            ModelingToolkit.getdefault(state)
        catch
            0.0
        end
        variables[var_name] = ModelVariable(StateVariable; default=default_val)
    end

    for param in ModelingToolkit.parameters(sys)
        pname = string(ModelingToolkit.getname(param))
        default_val = try
            ModelingToolkit.getdefault(param)
        catch
            1.0
        end
        variables[pname] = ModelVariable(ParameterVariable; default=default_val)
    end

    try
        for obs in ModelingToolkit.observed(sys)
            oname = _strip_time(string(ModelingToolkit.getname(obs.lhs)))
            variables[oname] = ModelVariable(ObservedVariable;
                expression=_symbolic_to_esm(obs.rhs))
        end
    catch
    end

    equations = Equation[]
    for eq in ModelingToolkit.equations(sys)
        push!(equations, Equation(_symbolic_to_esm(eq.lhs),
                                  _symbolic_to_esm(eq.rhs)))
    end

    return Model(variables, equations)
end

_strip_time(s::AbstractString) = endswith(s, "(t)") ? s[1:end-3] : s

function _symbolic_to_esm(expr)
    if expr isa Real || expr isa Integer || expr isa AbstractFloat
        return NumExpr(Float64(expr))
    end
    raw = Symbolics.unwrap(expr)
    if Symbolics.issym(raw)
        name = _strip_time(string(Symbolics.getname(raw)))
        return VarExpr(name)
    end
    is_diff = try
        Symbolics.is_derivative(raw)
    catch
        false
    end
    if is_diff
        inner = _symbolic_to_esm(Symbolics.arguments(raw)[1])
        return OpExpr("D", EsmExpr[inner], wrt="t")
    end
    if Symbolics.iscall(raw)
        op = Symbolics.operation(raw)
        args = Symbolics.arguments(raw)
        esm_args = [_symbolic_to_esm(a) for a in args]
        if op == (+); return OpExpr("+", esm_args)
        elseif op == (*); return OpExpr("*", esm_args)
        elseif op == (-); return OpExpr("-", esm_args)
        elseif op == (/); return OpExpr("/", esm_args)
        elseif op == (^); return OpExpr("^", esm_args)
        elseif op == exp; return OpExpr("exp", esm_args)
        elseif op == log; return OpExpr("log", esm_args)
        elseif op == sin; return OpExpr("sin", esm_args)
        elseif op == cos; return OpExpr("cos", esm_args)
        elseif op == sqrt; return OpExpr("sqrt", esm_args)
        elseif op == abs; return OpExpr("abs", esm_args)
        else
            opname = string(nameof(op))
            return OpExpr(opname, esm_args)
        end
    end
    return VarExpr(string(expr))
end

end # module EarthSciSerializationMTKExt
