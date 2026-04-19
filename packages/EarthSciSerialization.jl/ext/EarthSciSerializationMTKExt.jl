module EarthSciSerializationMTKExt

using EarthSciSerialization
# Note: we deliberately do NOT import `Expr` from EarthSciSerialization into
# this extension's namespace — that would shadow Core.Expr and break the
# `Symbolics.@variables` macro call we use for programmatic variable creation
# (the macro's generated code references Core.Expr).
using EarthSciSerialization: FlattenedSystem, ModelVariable, StateVariable,
    ParameterVariable, ObservedVariable, NumExpr, IntExpr, VarExpr, OpExpr,
    Equation, AffectEquation, Model, EventType, ContinuousEvent, DiscreteEvent,
    ConditionTrigger, PeriodicTrigger, PresetTimesTrigger, FunctionalAffect,
    Domain, flatten, infer_array_shapes
const EsmExpr = EarthSciSerialization.Expr
using ModelingToolkit
using ModelingToolkit: @variables, @parameters, Differential, System, PDESystem
using Symbolics
using Symbolics: Num
# SymbolicUtils ships inside Symbolics (via @reexport); access the module
# through Symbolics.SymbolicUtils so we don't need to declare a separate
# weak dep in Project.toml. Alias it locally for readability.
const SymUtils = Symbolics.SymbolicUtils
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
    if expr isa IntExpr
        return expr.value
    elseif expr isa NumExpr
        # Integer-valued NumExpr is promoted to Int so arrayop index
        # expressions like `i - 1` stay integer-typed when fixtures
        # still encode whole numbers as NumExpr.
        v = expr.value
        return v == floor(v) ? Int(v) : v
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
        elseif op == "arrayop"
            return _build_arrayop(expr, var_dict, t_sym, dim_dict)
        elseif op == "makearray"
            return _build_makearray(expr, var_dict, t_sym, dim_dict)
        elseif op == "index"
            return _build_index(expr, var_dict, t_sym, dim_dict)
        elseif op == "broadcast"
            return _build_broadcast(expr, var_dict, t_sym, dim_dict)
        elseif op == "reshape"
            return _build_reshape(expr, var_dict, t_sym, dim_dict)
        elseif op == "transpose"
            return _build_transpose(expr, var_dict, t_sym, dim_dict)
        elseif op == "concat"
            return _build_concat(expr, var_dict, t_sym, dim_dict)
        else
            error("Unsupported operator: $op")
        end
    end
    error("Unknown expression type: $(typeof(expr))")
end

# ========================================
# Array op dispatch helpers (gt-vt3)
# ========================================

# Map reduce-name string from the schema to the Julia reducer callable used
# by the low-level `SymbolicUtils.ArrayOp` constructor.
function _reduce_fn(name::Union{Nothing,AbstractString})
    name === nothing && return +
    return name == "+" ? (+) :
           name == "*" ? (*) :
           name == "max" ? max :
           name == "min" ? min :
           error("Unsupported arrayop reduce: $name")
end

# Pre-scalarize an ESM `arrayop` node into a native `Array{Num}` of scalar
# symbolic expressions. This avoids SymbolicUtils's `_scalarize_arrayop`
# path, which has an off-by-one when an index variable with an explicit
# range (e.g. `i in 2:9`) appears both in `output_idx` and in offset
# accesses like `u[i-1]`: `arrayop_shape` stores the output shape as
# `1:length(range)` and `scalarize` substitutes `i` with 1..length, not
# with the declared range values, producing `u[0]` → BoundsError.
#
# We iterate the declared ranges ourselves, substitute integer index
# values into the body via `_esm_to_symbolic`, and assemble a native array
# of Num. The caller's equation loop handles vector-shaped LHS/RHS by
# broadcasting element-wise equations (see `ModelingToolkit.System`).
function _build_arrayop(expr::OpExpr, var_dict::Dict{String,Any},
                        t_sym, dim_dict::Dict{String,Any})
    output_idx = expr.output_idx === nothing ? Any[] : expr.output_idx
    body = expr.expr_body
    body === nothing && error("arrayop node missing 'expr' body")
    reduce_fn = _reduce_fn(expr.reduce)

    expr.ranges === nothing && error(
        "arrayop without explicit 'ranges' is not supported — all index " *
        "variables must declare a concrete range")
    ranges = Dict{String,UnitRange{Int}}()
    for (name, r) in expr.ranges
        lo, hi = _range_bounds_int(r)
        ranges[name] = lo:hi
    end

    output_names = String[]
    singleton_axes = Int[]  # aligned with output_idx: 0 for named, 1 for singleton
    for entry in output_idx
        if entry isa AbstractString
            name = String(entry)
            haskey(ranges, name) ||
                error("arrayop output index '$name' has no declared range")
            push!(output_names, name)
            push!(singleton_axes, 0)
        elseif entry == 1
            push!(singleton_axes, 1)
        else
            error("arrayop output_idx entry must be a string or 1, got $(entry)")
        end
    end

    reduce_names = String[]
    for (name, _) in ranges
        name in output_names && continue
        push!(reduce_names, name)
    end

    # var_dict is extended with the integer index values during body
    # evaluation. Any key collisions (unlikely — index names are `i, j, k`
    # while ESM vars are state/param names) are saved and restored so we
    # don't clobber a real variable.
    function _eval_with(iv_map::Dict{String,Int})
        saved = Dict{String,Any}()
        for (k, v) in iv_map
            if haskey(var_dict, k)
                saved[k] = var_dict[k]
            end
            var_dict[k] = v
        end
        try
            return _esm_to_symbolic(body, var_dict, t_sym, dim_dict)
        finally
            for k in keys(iv_map)
                if haskey(saved, k)
                    var_dict[k] = saved[k]
                else
                    delete!(var_dict, k)
                end
            end
        end
    end

    function _reduce_over(output_vals::Dict{String,Int})
        if isempty(reduce_names)
            return _eval_with(output_vals)
        end
        reduce_range_tuple = Tuple(ranges[n] for n in reduce_names)
        acc = nothing
        iv_map = copy(output_vals)
        for red_vals in Iterators.product(reduce_range_tuple...)
            for (k, v) in zip(reduce_names, red_vals)
                iv_map[k] = v
            end
            contrib = _eval_with(iv_map)
            acc = acc === nothing ? contrib : reduce_fn(acc, contrib)
        end
        return acc
    end

    if isempty(output_names) && all(==(1), singleton_axes)
        # Fully scalar output (pure reduction or empty output tuple).
        return _reduce_over(Dict{String,Int}())
    end

    # Build a Num-typed result whose shape matches `output_idx`. Singleton
    # axes (`1` entries) contribute a length-1 dimension to preserve the
    # caller's index arity.
    out_shape = Int[]
    for entry in output_idx
        if entry == 1
            push!(out_shape, 1)
        else
            push!(out_shape, length(ranges[String(entry)]))
        end
    end
    result = Array{Symbolics.Num}(undef, out_shape...)

    named_range_tuple = Tuple(ranges[n] for n in output_names)
    named_range_lo = Tuple(first(r) for r in named_range_tuple)
    for named_vals in Iterators.product(named_range_tuple...)
        out_vals = Dict{String,Int}()
        for (n, v) in zip(output_names, named_vals)
            out_vals[n] = v
        end
        scalar = _reduce_over(out_vals)

        # Compute the Cartesian position in `result`. Named axes map range
        # values to 1-based offsets; singleton axes always pin to 1.
        cart = Int[]
        named_i = 1
        for entry in output_idx
            if entry == 1
                push!(cart, 1)
            else
                push!(cart, named_vals[named_i] - named_range_lo[named_i] + 1)
                named_i += 1
            end
        end
        result[cart...] = scalar isa Symbolics.Num ? scalar : Symbolics.Num(scalar)
    end
    return result
end

# Decode a range field `[lo, hi]` or `[lo, step, hi]` to integer bounds.
function _range_bounds_int(r::Vector{Int})
    if length(r) == 2
        return r[1], r[2]
    elseif length(r) == 3
        return r[1], r[3]
    end
    error("range must have 2 or 3 entries, got $(length(r))")
end

# Walk an ESM expression tree collecting variable names in order of first
# occurrence. Used to build eval-time bindings for `_build_arrayop`.
function _collect_var_refs(expr::EsmExpr, acc::Vector{String}=String[])
    if expr isa VarExpr
        push!(acc, expr.name)
    elseif expr isa OpExpr
        for a in expr.args
            _collect_var_refs(a, acc)
        end
        if expr.expr_body !== nothing
            _collect_var_refs(expr.expr_body, acc)
        end
        if expr.values !== nothing
            for v in expr.values
                _collect_var_refs(v, acc)
            end
        end
    end
    return acc
end

# Translate an ESM expression tree to a raw Julia AST that uses the
# `Symbol`s in `var_name_to_sym` for named variables and leaves unknown
# `VarExpr` names as bare symbols (used for array-op indices like `i, j`).
# Numeric literals become Julia numbers; operators become `Expr(:call, ...)`
# nodes; array indexing becomes `Expr(:ref, ...)`. Nested array ops inside
# an arrayop body (e.g. `makearray` inside an arrayop) are not common but
# we still handle `index` nodes since those are the primary way variables
# are indexed inside an `@arrayop` body.
function _esm_to_julia_ast(expr::EsmExpr, var_name_to_sym::Dict{String,Symbol})
    if expr isa IntExpr
        # Integer literal — emit as Int for index offsets etc.
        return Int(expr.value)
    elseif expr isa NumExpr
        # Prefer integer literals when the value is whole — this matters for
        # expressions like `u[i-1]` where the macro's offset-range inference
        # needs integer offsets, not 1.0 floats.
        v = expr.value
        return v == floor(v) ? Int(v) : v
    elseif expr isa VarExpr
        return get(var_name_to_sym, expr.name, Symbol(expr.name))
    elseif expr isa OpExpr
        op = expr.op
        if op == "index"
            arr = _esm_to_julia_ast(expr.args[1], var_name_to_sym)
            idxs = [_esm_to_julia_ast(a, var_name_to_sym) for a in expr.args[2:end]]
            return Core.Expr(:ref, arr, idxs...)
        elseif op in ("+", "-", "*", "/", "^")
            args_ast = [_esm_to_julia_ast(a, var_name_to_sym) for a in expr.args]
            if length(args_ast) == 1 && op == "-"
                return Core.Expr(:call, :-, args_ast[1])
            end
            return Core.Expr(:call, Symbol(op), args_ast...)
        elseif op in ("exp", "log", "log10", "sin", "cos", "tan",
                      "sinh", "cosh", "tanh", "asin", "acos", "atan",
                      "sqrt", "abs")
            args_ast = [_esm_to_julia_ast(a, var_name_to_sym) for a in expr.args]
            return Core.Expr(:call, Symbol(op), args_ast...)
        elseif op == "D"
            # D(u[i]) inside an @arrayop body: emit a bare `D` symbol; the
            # let-block wrapping the macro call binds `D = Differential(t_sym)`.
            inner = _esm_to_julia_ast(expr.args[1], var_name_to_sym)
            return Core.Expr(:call, :D, inner)
        else
            error("Unsupported operator inside arrayop body: $op")
        end
    end
    error("Unknown expression type in arrayop body: $(typeof(expr))")
end

# Build a native `Array{Num}` from a `makearray` node. We construct the
# output array directly rather than going through `SymbolicUtils.ArrayMaker`,
# whose public binding disappeared in the Symbolics v7 / SymbolicUtils v4
# rewrite (the type moved to `BSImpl.ArrayMaker` with a different
# constructor; `Symbolics.ArrayMaker` is no longer a defined name).
#
# Regions are 1-based and may overlap; later regions in the sequence
# override earlier ones, matching both the schema contract and the
# `@makearray` runtime semantics. Each region's value is currently a
# scalar expression that is broadcast across the region; array-valued
# region fills (not used by any fixture) would need additional handling.
function _build_makearray(expr::OpExpr, var_dict::Dict{String,Any},
                          t_sym, dim_dict::Dict{String,Any})
    expr.regions === nothing && error("makearray node missing 'regions'")
    expr.values === nothing && error("makearray node missing 'values'")
    length(expr.regions) == length(expr.values) ||
        error("makearray regions and values length mismatch")

    nd = length(expr.regions[1])
    sz = fill(0, nd)
    for region in expr.regions
        length(region) == nd || error("makearray regions must all share ndims")
        for (axis, pair) in enumerate(region)
            pair[1] >= 1 || error("makearray regions must be 1-based")
            sz[axis] = max(sz[axis], pair[2])
        end
    end

    result = Array{Symbolics.Num}(undef, sz...)
    fill!(result, Symbolics.Num(0))
    for (region, val_expr) in zip(expr.regions, expr.values)
        v = _esm_to_symbolic(val_expr, var_dict, t_sym, dim_dict)
        v_num = v isa Symbolics.Num ? v : Symbolics.Num(v)
        region_axes = Tuple(pair[1]:pair[2] for pair in region)
        for idx in Iterators.product(region_axes...)
            result[idx...] = v_num
        end
    end
    return result
end

# Build an `index` node: `args[1]` is the array-shaped operand, `args[2:]`
# are the index expressions. This is used outside arrayop bodies (inside an
# arrayop body, the `index` op is consumed by `_esm_to_julia_ast`).
function _build_index(expr::OpExpr, var_dict::Dict{String,Any},
                      t_sym, dim_dict::Dict{String,Any})
    arr = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
    idxs = Any[]
    for a in expr.args[2:end]
        if a isa IntExpr
            push!(idxs, Int(a.value))
        elseif a isa NumExpr
            push!(idxs, Int(a.value))
        else
            push!(idxs, _esm_to_symbolic(a, var_dict, t_sym, dim_dict))
        end
    end
    return getindex(arr, idxs...)
end

function _build_broadcast(expr::OpExpr, var_dict::Dict{String,Any},
                          t_sym, dim_dict::Dict{String,Any})
    expr.fn === nothing && error("broadcast node missing 'fn'")
    fn_name = expr.fn
    operands = [_esm_to_symbolic(a, var_dict, t_sym, dim_dict) for a in expr.args]
    fn = fn_name == "+" ? (+) :
         fn_name == "-" ? (-) :
         fn_name == "*" ? (*) :
         fn_name == "/" ? (/) :
         fn_name == "^" ? (^) :
         fn_name == "exp" ? exp :
         fn_name == "log" ? log :
         fn_name == "log10" ? log10 :
         fn_name == "sin" ? sin :
         fn_name == "cos" ? cos :
         fn_name == "sqrt" ? sqrt :
         fn_name == "abs" ? abs :
         error("Unsupported broadcast fn: $fn_name")
    return Base.materialize(Base.broadcasted(fn, operands...))
end

function _build_reshape(expr::OpExpr, var_dict::Dict{String,Any},
                        t_sym, dim_dict::Dict{String,Any})
    expr.shape === nothing && error("reshape node missing 'shape'")
    arr = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
    dims = Int[]
    for entry in expr.shape
        if entry isa Integer
            push!(dims, Int(entry))
        else
            error("reshape currently only supports integer shape entries, got $(entry)")
        end
    end
    return Symbolics.reshape(arr, dims...)
end

function _build_transpose(expr::OpExpr, var_dict::Dict{String,Any},
                          t_sym, dim_dict::Dict{String,Any})
    arr = _esm_to_symbolic(expr.args[1], var_dict, t_sym, dim_dict)
    if expr.perm !== nothing
        # Schema perm is 0-based; Julia permutedims expects 1-based axes.
        perm1 = [p + 1 for p in expr.perm]
        return permutedims(arr, perm1)
    end
    return transpose(arr)
end

function _build_concat(expr::OpExpr, var_dict::Dict{String,Any},
                       t_sym, dim_dict::Dict{String,Any})
    expr.axis === nothing && error("concat node missing 'axis'")
    arrs = [_esm_to_symbolic(a, var_dict, t_sym, dim_dict) for a in expr.args]
    return cat(arrs...; dims=expr.axis + 1)
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

Construct a plain parameter symbol `name` using `ModelingToolkit.@parameters`.
"""
# @parameters (not @variables) stamps isparameter=true, which AffectSystem
# relies on to classify symbols inside a SymbolicDiscreteCallback affect.
function _make_param(name::Symbol)
    vars = Core.eval(ModelingToolkit, :(@parameters $(name)))
    return vars[1]
end

"""
    _build_description(desc, units) -> Union{String,Nothing}

Assemble a description string that encodes both the ESM variable's textual
description and its units. MTK's `VariableDescription` metadata is a plain
string, so we embed the unit as a `(units=...)` suffix. Returns `nothing`
when there is nothing to attach — the caller uses that to skip metadata.

The ESM binding intentionally does NOT feed units into MTK's own unit
metadata system (that path has latent bugs and duplicates the work of
`src/units.jl`); stuffing units into the description is a version-stable
alternative that still surfaces in error messages and plot labels.
"""
function _build_description(desc::Union{String,Nothing},
                            units::Union{String,Nothing})
    if desc === nothing && units === nothing
        return nothing
    elseif units === nothing
        return desc
    elseif desc === nothing
        return "(units=$(units))"
    else
        return "$(desc) (units=$(units))"
    end
end

"""
    _make_array_dep_var(name::Symbol, iv_syms::Vector{Any}, shape::Vector{UnitRange{Int}})

Construct a shape-annotated symbolic variable of the form
`name(iv1, iv2, ...)[range1, range2, ...]` — the array form produced by
`@variables (u(t))[1:N]`. We build the macro call via `Core.eval` in the
Symbolics module so `iv_syms` can be passed by value. The result is the
array-shaped `Symbolics.Arr` object that supports element-wise indexing
via `u[i]`, `u[i, j]`, etc.
"""
function _make_array_dep_var(name::Symbol, iv_syms::Vector{Any},
                             shape::Vector{UnitRange{Int}})
    holder_names = [Symbol("__esm_iv_", i) for i in 1:length(iv_syms)]
    bindings = [Core.Expr(:(=), holder_names[i], iv_syms[i]) for i in 1:length(iv_syms)]
    call_expr = Core.Expr(:call, name, holder_names...)
    # Always pad the low side of the shape to 1. MTK's init path treats
    # Symbolics.Arr indices as raw 1-based Vector positions, so declaring
    # `@variables flux(t)[3:17]` produces a 15-slot backing Vector but
    # `flux[17]` then resolves to internal position 17 and raises
    # BoundsError during `generate_initializesystem_timevarying`. Using
    # `1:last(r)` makes the backing Vector large enough that every used
    # index is a valid position; the low slots that fall outside the
    # inferred range are simply left out of `states` in `_build_var_dict`.
    ranges_ast = [Core.Expr(:call, :(:), 1, last(r)) for r in shape]
    ref_expr = Core.Expr(:ref, call_expr, ranges_ast...)
    # `(name(iv...)[range...])` — the parenthesized form the macro expects.
    paren_expr = Core.Expr(:block, ref_expr)
    block_expr = Core.Expr(:block, bindings...,
                           :(Symbolics.@variables $(paren_expr)))
    let_expr = Core.Expr(:let, Core.Expr(:block), block_expr)
    vars = Core.eval(Symbolics, let_expr)
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

When the flattened system contains `arrayop`/`makearray`/`index` nodes,
shape inference is run first and any variable that appears inside an array
operator is declared as a shaped `@variables (u(t))[1:N]` instead of a
scalar `u(t)`. The `states`/`observed` vectors then contain the individual
scalar elements of those array variables (so `length(states) == M*N` for a
2-D array), matching the scalar dvs list passed to
`System(..., dvs, [])` in the MTK fork's native `@arrayop` tests.
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

    # Shape inference: scalar-only systems get an empty dict and pay nothing.
    inferred_shapes = infer_array_shapes(flat.equations)

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

    # Attach a default value to a Symbolics variable via VariableDefaultValue
    # metadata. MTK v11 uses this to wire initial conditions on states and
    # parameter values into ODEProblem/PDESystem construction without
    # requiring the caller to pass u0/p maps manually.
    _with_default(v, val) =
        val === nothing ? v : Symbolics.setdefaultval(v, Float64(val))

    _with_description(v, desc_text) =
        desc_text === nothing ? v :
            Symbolics.setmetadata(v, ModelingToolkit.VariableDescription, desc_text)

    # State variables — functions of independent variables
    for (vname, mvar) in flat.state_variables
        sym_name = _san(vname)
        shape = get(inferred_shapes, vname, nothing)
        desc_text = _build_description(mvar.description, mvar.units)
        if shape === nothing
            v_num = _with_description(
                _with_default(_make_dep_var(sym_name, iv_syms_any), mvar.default),
                desc_text)
            push!(states, v_num)
            var_dict[vname] = v_num
        else
            array_var = _make_array_dep_var(sym_name, iv_syms_any, shape)
            var_dict[vname] = array_var
            # Enumerate the individual scalar elements for the dvs vector.
            # Description metadata is attached per-element because
            # Symbolics.setmetadata has no method for Symbolics.Arr.
            for idx in Iterators.product(shape...)
                elt = _with_description(Num(array_var[idx...]), desc_text)
                push!(states, elt)
            end
        end
    end

    # Parameters — plain symbols
    for (pname, mvar) in flat.parameters
        p_num = _with_description(
            _with_default(_make_param(_san(pname)), mvar.default),
            _build_description(mvar.description, mvar.units))
        push!(parameters, p_num)
        var_dict[pname] = p_num
    end

    # Observed variables — same shape as states
    for (oname, mvar) in flat.observed_variables
        ov_num = _with_description(
            _with_default(_make_dep_var(_san(oname), iv_syms_any), mvar.default),
            _build_description(mvar.description, mvar.units))
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
            # MTK routes a Vector{<:Real} condition to PresetTimeCallback
            # (fires at exactly those times); a scalar Real goes to
            # PeriodicCallback (fires at tspan[1]+period, 2*period, ...).
            # Pass the full times vector so multi-time triggers are honored.
            if !isempty(ev.trigger.times)
                push!(cbs, ModelingToolkit.SymbolicDiscreteCallback(
                    collect(ev.trigger.times), affects))
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
        # Pre-scalarized arrayop nodes return an `Array{Num}`. Expand into
        # one scalar equation per element so the MTK structural checker sees
        # only scalar `lhs ~ rhs` pairs.
        if lhs isa AbstractArray || rhs isa AbstractArray
            lhs isa AbstractArray && rhs isa AbstractArray ||
                error("arrayop equation side-shape mismatch: one side is array, the other scalar")
            size(lhs) == size(rhs) ||
                error("arrayop equation size mismatch: LHS $(size(lhs)) vs RHS $(size(rhs))")
            for i in eachindex(lhs)
                push!(eqs, lhs[i] ~ rhs[i])
            end
        else
            push!(eqs, lhs ~ rhs)
        end
    end

    # Observed variables need to appear in the unknowns (dvs) list so that
    # references to them elsewhere in the equations pass MTK's structural
    # check. Their defining equation (`obs ~ expr`) stays in the main
    # equation list; `mtkcompile`'s alias elimination pass moves them to
    # the compiled system's `observed` section automatically.
    dvs = copy(states)
    append!(dvs, observed)

    cont_cbs = _build_continuous_events(flat, var_dict, t_sym, dim_dict)
    disc_cbs = _build_discrete_events(flat, var_dict, t_sym, dim_dict)

    # Array-op equations must bypass MTK's structural checks — the LHS and
    # RHS are typically `ArrayOp`-wrapped expressions whose scalar form is
    # only accessible after `mtkcompile`, so the builder would otherwise
    # reject them as non-scalar. Scalar-only systems still use default checks.
    has_array = _has_array_op(flat.equations)
    extra_kwargs = has_array ? (; checks=false) : (;)

    sys_name = name isa Symbol ? name : Symbol(name)

    sys = if !isempty(cont_cbs) && !isempty(disc_cbs)
        ModelingToolkit.System(eqs, t_sym, dvs, parameters;
            name=sys_name,
            continuous_events=cont_cbs,
            discrete_events=disc_cbs, extra_kwargs..., kwargs...)
    elseif !isempty(cont_cbs)
        ModelingToolkit.System(eqs, t_sym, dvs, parameters;
            name=sys_name, continuous_events=cont_cbs, extra_kwargs..., kwargs...)
    elseif !isempty(disc_cbs)
        ModelingToolkit.System(eqs, t_sym, dvs, parameters;
            name=sys_name, discrete_events=disc_cbs, extra_kwargs..., kwargs...)
    else
        ModelingToolkit.System(eqs, t_sym, dvs, parameters;
            name=sys_name, extra_kwargs..., kwargs...)
    end
    return sys
end

# Detect whether any equation (LHS or RHS) contains an array-op node.
# Cheap recursive scan — short-circuits on the first hit.
function _has_array_op(equations::Vector{Equation})
    for eq in equations
        _expr_has_array_op(eq.lhs) && return true
        _expr_has_array_op(eq.rhs) && return true
    end
    return false
end

function _expr_has_array_op(expr::EsmExpr)
    expr isa OpExpr || return false
    if expr.op in ("arrayop", "makearray", "index", "broadcast",
                   "reshape", "transpose", "concat")
        return true
    end
    for a in expr.args
        _expr_has_array_op(a) && return true
    end
    if expr.expr_body !== nothing && _expr_has_array_op(expr.expr_body)
        return true
    end
    if expr.values !== nothing
        for v in expr.values
            _expr_has_array_op(v) && return true
        end
    end
    return false
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
    append!(dvars, Num(v) for v in observed)

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
    elseif expr isa NumExpr || expr isa IntExpr
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
    # Distinguish integer from float at the round-trip boundary (RFC §5.4.1).
    if expr isa Bool
        return IntExpr(Int64(expr))  # defensive; shouldn't happen in ESM exprs
    elseif expr isa Integer
        return IntExpr(Int64(expr))
    elseif expr isa AbstractFloat
        return NumExpr(Float64(expr))
    elseif expr isa Real
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
