module EarthSciSerializationMTKExt

using EarthSciSerialization
# Note: we deliberately do NOT import `Expr` from EarthSciSerialization into
# this extension's namespace — that would shadow Core.Expr and break the
# `Symbolics.@variables` macro call we use for programmatic variable creation
# (the macro's generated code references Core.Expr).
using EarthSciSerialization: FlattenedSystem, ModelVariable, StateVariable,
    ParameterVariable, ObservedVariable, BrownianVariable,
    NumExpr, IntExpr, VarExpr, OpExpr,
    Equation, AffectEquation, Model, EventType, ContinuousEvent, DiscreteEvent,
    ConditionTrigger, PeriodicTrigger, PresetTimesTrigger, FunctionalAffect,
    Domain, flatten, infer_array_shapes,
    GapReport, Metadata, EsmFile
# Explicit import so we can add methods to these generics.
import EarthSciSerialization: mtk2esm, mtk2esm_gaps
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

# Substitute every state variable reference in `expr` with
# `ModelingToolkit.Pre(var)`. Required on event-affect RHS expressions:
# current MTK interprets an un-`Pre`-wrapped affect equation as an
# algebraic constraint to hold after the callback, which renders
# assignments like `x ~ x + dose` unsatisfiable (see
# ModelingToolkit/callbacks.jl:85 warning). Parameters are left alone —
# they don't vary across the affect, and wrapping them would force the
# discrete-parameter machinery for no gain.
function _wrap_pre_states(expr, state_syms)
    isempty(state_syms) && return expr
    subs = Dict{Any,Any}()
    for sv in state_syms
        u = Symbolics.unwrap(sv)
        subs[u] = ModelingToolkit.Pre(sv)
    end
    if expr isa AbstractArray
        return map(e -> Symbolics.substitute(e, subs), expr)
    end
    return Symbolics.substitute(expr, subs)
end

function _affect_to_eq(affect, var_dict::Dict{String,Any}, t_sym, dim_dict,
                      state_syms)
    if affect isa AffectEquation
        if !haskey(var_dict, affect.lhs)
            @warn "Target variable $(affect.lhs) not found for event affect"
            return nothing
        end
        target = var_dict[affect.lhs]
        rhs = _esm_to_symbolic(affect.rhs, var_dict, t_sym, dim_dict)
        rhs = _wrap_pre_states(rhs, state_syms)
        return target ~ rhs
    elseif affect isa FunctionalAffect
        if !haskey(var_dict, affect.target)
            @warn "Target variable $(affect.target) not found for event affect"
            return nothing
        end
        target = var_dict[affect.target]
        rhs = _esm_to_symbolic(affect.expression, var_dict, t_sym, dim_dict)
        rhs = _wrap_pre_states(rhs, state_syms)
        # For compound operations the LHS target also appears on the RHS
        # and must refer to its pre-affect value.
        pre_target = ModelingToolkit.Pre(target)
        if affect.operation == "set"
            return target ~ rhs
        elseif affect.operation == "add"
            return target ~ pre_target + rhs
        elseif affect.operation == "multiply"
            return target ~ pre_target * rhs
        else
            @warn "Unknown affect operation: $(affect.operation)"
            return target ~ rhs
        end
    end
    return nothing
end

function _build_continuous_events(flat::FlattenedSystem, var_dict, t_sym, dim_dict,
                                  state_syms)
    cbs = Any[]
    for ev in flat.continuous_events
        conds = [_esm_to_symbolic(c, var_dict, t_sym, dim_dict) for c in ev.conditions]
        affects = filter(!isnothing,
                         [_affect_to_eq(a, var_dict, t_sym, dim_dict, state_syms)
                          for a in ev.affects])
        isempty(conds) || isempty(affects) && continue
        cb = ModelingToolkit.SymbolicContinuousCallback(conds[1], affects)
        push!(cbs, cb)
    end
    return cbs
end

function _build_discrete_events(flat::FlattenedSystem, var_dict, t_sym, dim_dict,
                                state_syms)
    cbs = Any[]
    for ev in flat.discrete_events
        affects = filter(!isnothing,
                         [_affect_to_eq(a, var_dict, t_sym, dim_dict, state_syms)
                          for a in ev.affects])
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

    # Symbolic handles for state variables (not their array-scalarized
    # elements) drive `Pre`-wrapping in affect equations.
    state_syms = Any[var_dict[vname] for vname in keys(flat.state_variables)]
    cont_cbs = _build_continuous_events(flat, var_dict, t_sym, dim_dict, state_syms)
    disc_cbs = _build_discrete_events(flat, var_dict, t_sym, dim_dict, state_syms)

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

# ========================================
# MTK → ESM export (gt-dod2; Phase 1 migration tooling)
# ========================================

"""
Return a user-facing system kind name used in warnings and TODO_GAP notes.
Catalyst.ReactionSystem is handled in the Catalyst extension; the cases
here cover plain MTK systems whose type-printed name matches the expected
system class.
"""
function _sys_kind(sys)
    t = string(typeof(sys))
    if occursin("PDESystem", t);       return "PDESystem"
    elseif occursin("SDESystem", t);   return "SDESystem"
    elseif occursin("ReactionSystem", t); return "ReactionSystem"
    elseif occursin("NonlinearSystem", t); return "NonlinearSystem"
    elseif occursin("ODESystem", t);   return "ODESystem"
    else;                              return "System"
    end
end

# Return `true` if the System *declares* brownian variables (SDE). We detect
# by presence of the `brownians` getter on AbstractSystem (MTK v11+). For
# older systems or systems without the field, return `false`.
function _mtk_brownians(sys)
    try
        return ModelingToolkit.brownians(sys)
    catch
        return Any[]
    end
end

# Return the MTK system's noise_eqs vector, or empty if not set.
function _mtk_noise_eqs(sys)
    try
        return ModelingToolkit.get_noiseeqs(sys)
    catch
        return nothing
    end
end

# Convert a symbolic to ESM expression using a known set of variable names
# to disambiguate callable-symbolic nodes like `x(t)` from operator calls.
# MTK states and observed variables appear in the symbolic tree as
# `Sym{FnType{...}}(t)`, which `_symbolic_to_esm` would otherwise emit as
# `OpExpr("x", [VarExpr("t")])` — the wrong shape for the ESM schema.
function _symbolic_to_esm_export(expr, known_vars::Set{String},
                                 strip_ns::Function=identity)
    # Scalar fast-paths
    if expr isa Bool
        return IntExpr(Int64(expr))
    elseif expr isa Integer
        return IntExpr(Int64(expr))
    elseif expr isa AbstractFloat
        return NumExpr(Float64(expr))
    elseif expr isa Real
        return NumExpr(Float64(expr))
    end
    raw = Symbolics.unwrap(expr)

    # Symbolic constants (e.g. `-1` produced by SymbolicUtils' multiplication
    # simplification `-k*x`) arrive as `BasicSymbolic{Int}` / `...{Real}`
    # with issym=false AND iscall=false. `Symbolics.value` extracts the
    # underlying Julia number without touching variable paths.
    if !Symbolics.issym(raw) && !Symbolics.iscall(raw)
        try
            val = Symbolics.value(raw)
            if val isa Bool;       return IntExpr(Int64(val))
            elseif val isa Integer; return IntExpr(Int64(val))
            elseif val isa Real;    return NumExpr(Float64(val))
            end
        catch
        end
    end

    if Symbolics.issym(raw)
        name = strip_ns(_strip_time(string(Symbolics.getname(raw))))
        return VarExpr(name)
    end

    is_diff = try
        Symbolics.is_derivative(raw)
    catch
        false
    end
    if is_diff
        inner = _symbolic_to_esm_export(Symbolics.arguments(raw)[1],
                                         known_vars, strip_ns)
        return OpExpr("D", EsmExpr[inner], wrt="t")
    end

    if Symbolics.iscall(raw)
        op = Symbolics.operation(raw)
        args = Symbolics.arguments(raw)

        # Callable-symbolic variable: `x(t)` where `x` is a state/observed
        # var. Recognize by checking if the operation's name is a known
        # variable. Preserve as a bare VarExpr(name), dropping the IV args
        # — the ESM schema implicitly threads time through state vars.
        if !isempty(args)
            opname = try
                strip_ns(_strip_time(string(Symbolics.getname(op))))
            catch
                ""
            end
            if !isempty(opname) && opname in known_vars
                return VarExpr(opname)
            end
        end

        esm_args = [_symbolic_to_esm_export(a, known_vars, strip_ns) for a in args]
        if op == (+); return OpExpr("+", esm_args)
        elseif op == (*); return OpExpr("*", esm_args)
        elseif op == (-); return OpExpr("-", esm_args)
        elseif op == (/); return OpExpr("/", esm_args)
        elseif op == (^); return OpExpr("^", esm_args)
        elseif op == exp; return OpExpr("exp", esm_args)
        elseif op == log; return OpExpr("log", esm_args)
        elseif op == log10; return OpExpr("log10", esm_args)
        elseif op == sin; return OpExpr("sin", esm_args)
        elseif op == cos; return OpExpr("cos", esm_args)
        elseif op == tan; return OpExpr("tan", esm_args)
        elseif op == sqrt; return OpExpr("sqrt", esm_args)
        elseif op == abs; return OpExpr("abs", esm_args)
        elseif op == ifelse; return OpExpr("ifelse", esm_args)
        else
            opname = try
                string(nameof(op))
            catch
                string(op)
            end
            return OpExpr(opname, esm_args)
        end
    end
    return VarExpr(string(expr))
end

function _symbolic_to_esm_with_gaps(expr, known_vars::Set{String},
                                    gaps::Vector{GapReport}, where_str::String;
                                    strip_ns::Function=identity)
    try
        return _symbolic_to_esm_export(expr, known_vars, strip_ns)
    catch e
        push!(gaps, GapReport("unknown",
            "unable to serialize symbolic node: $(sprint(showerror, e))",
            where_str))
        return VarExpr("__TODO_GAP__")
    end
end

"""
    mtk2esm(sys::ModelingToolkit.AbstractSystem; metadata=(;)) -> Dict

Walk a non-reaction MTK system and emit a schema-valid ESM `Dict` with a
top-level `models.<name>` entry. Reaction systems are handled in the
Catalyst extension via a more specific method.

Fields populated from the MTK IR:
- `variables` (state / parameter / observed / brownian, with units +
  defaults extracted from symbolic metadata where present)
- `equations` (D(x)~rhs using the spec's Expression ops)
- `continuous_events`, `discrete_events` (from MTK callback lists)

Fields left as placeholders (filled in Phase 2 per-model migrations):
- `description`, `version`, `reference`, `tests`, `examples`
- `metadata.tags`, `metadata.source_ref` (populated from `metadata` kwarg)
"""
function mtk2esm(sys::ModelingToolkit.AbstractSystem; metadata=(;))
    gaps = GapReport[]

    kind = _sys_kind(sys)

    # Extract the name: caller-supplied `metadata.name` wins; else use
    # `nameof(sys)` if non-anonymous; else fall back to a literal placeholder
    # so the output file is still addressable.
    name_kw = try
        getproperty(metadata, :name)
    catch
        nothing
    end
    sys_name = if name_kw !== nothing
        String(name_kw)
    else
        try
            sn = String(nameof(sys))
            sn == "" ? "UnnamedSystem" : sn
        catch
            "UnnamedSystem"
        end
    end

    # 1. Variables -----------------------------------------------------------
    esm_vars = Dict{String,ModelVariable}()
    # System-level defaults dict — variables declared via `defaults=Dict(...)`
    # on System construction surface here rather than on the symbolic
    # metadata. We look up both and prefer the system-level value.
    sys_defaults = try
        ModelingToolkit.defaults(sys)
    catch
        Dict()
    end

    # When an MTK System was built via our ESM.Model → MTK.System path, the
    # flatten step sanitizes names as "<SystemName>_<var>" (dots → underscores).
    # We strip that prefix so the exported ESM names round-trip back to the
    # same bare names they had in the source Model. Direct-Symbolics-built
    # systems without the prefix pass through untouched.
    sys_name_prefix = sys_name * "_"
    strip_ns = s -> startswith(s, sys_name_prefix) ?
        s[length(sys_name_prefix)+1:end] : s

    # Collect all known variable names up-front so we can disambiguate
    # callable-symbolic variables `x(t)` from operator calls inside the
    # equation walk.
    known_vars = Set{String}()

    for state in ModelingToolkit.unknowns(sys)
        var_name = strip_ns(_strip_time(string(ModelingToolkit.getname(state))))
        push!(known_vars, var_name)
        default_val = _lookup_default(state, sys_defaults)
        units_str = _get_units_str(state)
        desc_str = _get_description_str(state)
        esm_vars[var_name] = ModelVariable(StateVariable;
            default=default_val, units=units_str, description=desc_str)
    end

    for param in ModelingToolkit.parameters(sys)
        pname = strip_ns(string(ModelingToolkit.getname(param)))
        push!(known_vars, pname)
        default_val = _lookup_default(param, sys_defaults)
        units_str = _get_units_str(param)
        desc_str = _get_description_str(param)
        esm_vars[pname] = ModelVariable(ParameterVariable;
            default=default_val, units=units_str, description=desc_str)
    end

    obs_exprs = try
        ModelingToolkit.observed(sys)
    catch
        []
    end
    for obs in obs_exprs
        oname = strip_ns(_strip_time(string(ModelingToolkit.getname(obs.lhs))))
        push!(known_vars, oname)
        rhs_esm = _symbolic_to_esm_with_gaps(obs.rhs, known_vars, gaps,
            "observed[$oname].rhs"; strip_ns=strip_ns)
        esm_vars[oname] = ModelVariable(ObservedVariable;
            expression=rhs_esm)
    end

    # Brownian variables (SDE noise sources) — gt-kuxo gate.
    brownians = _mtk_brownians(sys)
    if !isempty(brownians)
        push!(gaps, GapReport("gt-kuxo",
            "system has $(length(brownians)) brownian variable(s); " *
            "SDE noise serialization requires gt-kuxo to land first",
            "system.brownians"))
        for b in brownians
            bname = string(ModelingToolkit.getname(b))
            esm_vars[bname] = ModelVariable(BrownianVariable;
                noise_kind="wiener")
        end
    end

    noise_eqs = _mtk_noise_eqs(sys)
    if noise_eqs !== nothing && !isempty(noise_eqs)
        push!(gaps, GapReport("gt-kuxo",
            "system has explicit noise_eqs matrix; serialization of SDE " *
            "diffusion terms requires gt-kuxo to land first",
            "system.noise_eqs"))
    end

    # 2. Equations -----------------------------------------------------------
    esm_equations = Equation[]
    raw_eqs = try
        ModelingToolkit.equations(sys)
    catch
        []
    end
    for (i, eq) in enumerate(raw_eqs)
        lhs_esm = _symbolic_to_esm_with_gaps(eq.lhs, known_vars, gaps,
            "equations[$i].lhs"; strip_ns=strip_ns)
        rhs_esm = _symbolic_to_esm_with_gaps(eq.rhs, known_vars, gaps,
            "equations[$i].rhs"; strip_ns=strip_ns)
        push!(esm_equations, Equation(lhs_esm, rhs_esm))
    end

    # init equations (gt-ebuq gate) — present on MTK v11 systems
    init_eqs = try
        ModelingToolkit.initialization_equations(sys)
    catch
        []
    end
    if !isempty(init_eqs)
        push!(gaps, GapReport("gt-ebuq",
            "system declares $(length(init_eqs)) init equation(s); " *
            "serialization of initialization blocks requires gt-ebuq",
            "system.initialization_equations"))
    end

    # registered symbolic functions (gt-p3ep gate): detected by scanning the
    # symbolic AST for unknown `iscall` operations whose operation has a
    # non-Base name. Done during the recursive _symbolic_to_esm walk when a
    # call to a user-registered function produces an OpExpr with a non-
    # standard op name — conservatively report a generic gap note if we saw
    # operator names not in the schema's standard op set.
    _detect_registered_call_gaps!(gaps, esm_equations)

    # 3. Events --------------------------------------------------------------
    cont_events = ContinuousEvent[]
    disc_events = DiscreteEvent[]

    cont_cbs = try
        ModelingToolkit.continuous_events(sys)
    catch
        []
    end
    for (i, cb) in enumerate(cont_cbs)
        ce = _continuous_cb_to_esm(cb, known_vars, gaps, "continuous_events[$i]")
        ce !== nothing && push!(cont_events, ce)
    end

    disc_cbs = try
        ModelingToolkit.discrete_events(sys)
    catch
        []
    end
    for (i, cb) in enumerate(disc_cbs)
        de = _discrete_cb_to_esm(cb, known_vars, gaps, "discrete_events[$i]")
        de !== nothing && push!(disc_events, de)
    end

    # 4. Domain (PDE only) ---------------------------------------------------
    esm_domain = nothing
    if kind == "PDESystem"
        # PDESystem carries domain info; we flag as gap for now since the
        # round-trip of domain specs requires dedicated lowering logic.
        push!(gaps, GapReport("gt-vzwk",
            "PDESystem domain specification is not yet serialized — see gt-vzwk",
            "system.domain"))
    end

    # 5. Build ESM Model and wrap in EsmFile --------------------------------
    esm_model = Model(esm_vars, esm_equations;
        discrete_events=disc_events, continuous_events=cont_events,
        domain=esm_domain)

    # Serialize directly to a Dict so callers can mutate and embed
    # TODO_GAP notes before writing to disk. We bypass the EsmFile type
    # because the tests/examples fields are intentionally empty placeholders
    # the downstream migration step fills in later.
    model_dict = EarthSciSerialization.serialize_model(esm_model)

    # Build the Model-level `reference` entry. The schema defines Reference
    # with {doi, citation, url, notes} — we fold the migration description,
    # source_ref, and TODO_GAP notes into `notes` as a human-readable string
    # so the file stays schema-conformant. Later migration steps overwrite
    # this with a real citation when the source docstring is scraped.
    ref_notes_lines = String[]
    source_ref = _meta_string(metadata, :source_ref, "")
    if !isempty(source_ref)
        push!(ref_notes_lines, "source_ref: $source_ref")
    end
    version_str = _meta_string(metadata, :version, "0.1.0")
    if version_str != "0.1.0"
        push!(ref_notes_lines, "version: $version_str")
    end
    mod_desc = _meta_string(metadata, :description, "")
    if !isempty(mod_desc)
        push!(ref_notes_lines, mod_desc)
    end
    if !isempty(gaps)
        for g in gaps
            push!(ref_notes_lines, _gap_to_note(g))
        end
    end
    if !isempty(ref_notes_lines)
        model_dict["reference"] = Dict{String,Any}(
            "notes" => join(ref_notes_lines, "\n"))
    end
    # Preserve placeholder tests/examples only when the Model schema actually
    # requires them (it doesn't — they're optional arrays). Leave them out
    # when empty so validation doesn't have to iterate empty arrays, but add
    # them back when callers want a clear signal that content is "to be filled".
    model_dict["tests"] = Any[]
    model_dict["examples"] = Any[]

    # 6. Wrap in EsmFile-shaped Dict ----------------------------------------
    file_meta = Dict{String,Any}("name" => sys_name)
    file_desc = _meta_string(metadata, :description, "")
    if !isempty(file_desc)
        file_meta["description"] = file_desc
    end
    authors = _meta_vec_string(metadata, :authors)
    if authors !== nothing
        file_meta["authors"] = authors
    end
    ftags = _meta_vec_string(metadata, :tags)
    if ftags !== nothing
        file_meta["tags"] = ftags
    end

    out = Dict{String,Any}(
        "esm" => "0.1.0",
        "metadata" => file_meta,
        "models" => Dict{String,Any}(sys_name => model_dict),
    )

    # 7. Emit warnings --------------------------------------------------------
    if !isempty(gaps)
        gap_lines = join(["  - [$(g.bead_id)] $(g.description) @ $(g.where)"
                          for g in gaps], "\n")
        @warn "mtk2esm: $(length(gaps)) schema-gap construct(s) in " *
              "$(kind) $(sys_name):\n$(gap_lines)"
    end

    return out
end

# --- metadata helpers ---

function _meta_string(metadata, key::Symbol, default::String)
    try
        v = getproperty(metadata, key)
        return v === nothing ? default : String(v)
    catch
        return default
    end
end

function _meta_vec_string(metadata, key::Symbol)
    try
        v = getproperty(metadata, key)
        v === nothing && return nothing
        return [String(x) for x in v]
    catch
        return nothing
    end
end

function _gap_to_note(g::GapReport)
    "TODO_GAP: $(g.bead_id) - $(g.description) @ $(g.where)"
end

# --- symbolic metadata extraction ---

function _get_default_or(var, default)
    try
        val = ModelingToolkit.getdefault(var)
        val isa Number && return Float64(val)
        return default
    catch
        return default
    end
end

"""
Prefer the system-level defaults map (set via `System(...; defaults=...)`)
over per-symbol metadata. Returns `nothing` when no default is found so
the ESM `default` field is omitted rather than fabricated.
"""
function _lookup_default(var, sys_defaults)
    # System-level defaults dict uses the symbolic variable itself (with its
    # time dependence intact) as the key.
    if haskey(sys_defaults, var)
        v = sys_defaults[var]
        v isa Number && return Float64(v)
    end
    return _get_default_or(var, nothing)
end

function _get_units_str(var)
    raw = Symbolics.unwrap(var)
    try
        desc = Symbolics.getmetadata(raw, ModelingToolkit.VariableDescription, nothing)
        if desc isa AbstractString
            m = match(r"\(units=([^)]+)\)", desc)
            m !== nothing && return String(m.captures[1])
        end
    catch
    end
    return nothing
end

function _get_description_str(var)
    raw = Symbolics.unwrap(var)
    try
        desc = Symbolics.getmetadata(raw, ModelingToolkit.VariableDescription, nothing)
        if desc isa AbstractString
            # Strip the embedded (units=...) suffix we inject ourselves on
            # the reverse path; preserve the human description, if any.
            stripped = replace(desc, r"\s*\(units=[^)]+\)\s*$" => "")
            return isempty(stripped) ? nothing : String(stripped)
        end
    catch
    end
    return nothing
end

# --- event conversion (MTK → ESM) ---

function _continuous_cb_to_esm(cb, known_vars::Set{String},
                               gaps::Vector{GapReport}, where_str::String)
    # MTK callbacks expose fields via property access that differs across
    # versions; we try a few shapes and fall back to a gap report if we
    # can't extract the pieces we need.
    try
        conds = cb.conditions isa AbstractArray ? cb.conditions : [cb.conditions]
        esm_conds = EsmExpr[]
        for c in conds
            push!(esm_conds, _symbolic_to_esm_with_gaps(c, known_vars, gaps,
                where_str * ".condition"))
        end
        affects = cb.affects isa AbstractArray ? cb.affects : [cb.affects]
        esm_affs = AffectEquation[]
        for a in affects
            ae = _affect_to_esm(a, known_vars, gaps, where_str * ".affect")
            ae !== nothing && push!(esm_affs, ae)
        end
        return ContinuousEvent(esm_conds, esm_affs)
    catch e
        push!(gaps, GapReport("unknown",
            "unable to serialize continuous callback: $(sprint(showerror, e))",
            where_str))
        return nothing
    end
end

function _discrete_cb_to_esm(cb, known_vars::Set{String},
                             gaps::Vector{GapReport}, where_str::String)
    try
        trig_raw = hasproperty(cb, :condition) ? cb.condition : cb.conditions
        trigger = if trig_raw isa Real
            PeriodicTrigger(Float64(trig_raw))
        elseif trig_raw isa AbstractVector{<:Real}
            PresetTimesTrigger(Float64.(trig_raw))
        else
            ConditionTrigger(_symbolic_to_esm_with_gaps(trig_raw, known_vars,
                gaps, where_str * ".condition"))
        end
        affects = cb.affects isa AbstractArray ? cb.affects : [cb.affects]
        esm_affs = FunctionalAffect[]
        for a in affects
            af = _affect_to_functional(a, known_vars, gaps,
                where_str * ".affect")
            af !== nothing && push!(esm_affs, af)
        end
        return DiscreteEvent(trigger, esm_affs)
    catch e
        push!(gaps, GapReport("unknown",
            "unable to serialize discrete callback: $(sprint(showerror, e))",
            where_str))
        return nothing
    end
end

function _affect_to_esm(a, known_vars::Set{String},
                        gaps::Vector{GapReport}, where_str::String)
    try
        lhs_sym = hasproperty(a, :lhs) ? a.lhs : a[1]
        rhs_sym = hasproperty(a, :rhs) ? a.rhs : a[2]
        lhs_name = _strip_time(string(ModelingToolkit.getname(lhs_sym)))
        rhs_esm = _symbolic_to_esm_with_gaps(rhs_sym, known_vars, gaps,
            where_str * ".rhs")
        return AffectEquation(lhs_name, rhs_esm)
    catch
        return nothing
    end
end

function _affect_to_functional(a, known_vars::Set{String},
                               gaps::Vector{GapReport}, where_str::String)
    try
        lhs_sym = hasproperty(a, :lhs) ? a.lhs : a[1]
        rhs_sym = hasproperty(a, :rhs) ? a.rhs : a[2]
        lhs_name = _strip_time(string(ModelingToolkit.getname(lhs_sym)))
        rhs_esm = _symbolic_to_esm_with_gaps(rhs_sym, known_vars, gaps,
            where_str * ".rhs")
        return FunctionalAffect(lhs_name, rhs_esm; operation="set")
    catch
        return nothing
    end
end

# --- registered-function gap detection ---

const _KNOWN_OPS = Set([
    "+", "-", "*", "/", "^",
    "exp", "log", "log10", "sin", "cos", "tan", "sinh", "cosh", "tanh",
    "asin", "acos", "atan", "sqrt", "abs",
    ">", "<", ">=", "<=", "==", "!=",
    "D", "grad", "div", "laplacian",
    "arrayop", "makearray", "index", "broadcast", "reshape", "transpose",
    "concat", "Pre", "ifelse", "call",
])

function _detect_registered_call_gaps!(gaps::Vector{GapReport},
                                       equations::Vector{Equation})
    seen = Set{String}()
    for (i, eq) in enumerate(equations)
        _walk_expr_for_gaps!(eq.lhs, seen, gaps, "equations[$i].lhs")
        _walk_expr_for_gaps!(eq.rhs, seen, gaps, "equations[$i].rhs")
    end
end

function _walk_expr_for_gaps!(expr, seen::Set{String}, gaps::Vector{GapReport},
                              where_str::String)
    if expr isa OpExpr
        if !(expr.op in _KNOWN_OPS) && !(expr.op in seen)
            push!(seen, expr.op)
            push!(gaps, GapReport("gt-p3ep",
                "non-standard op '$(expr.op)' likely requires a registered " *
                "function declaration — see gt-p3ep",
                where_str))
        end
        for a in expr.args
            _walk_expr_for_gaps!(a, seen, gaps, where_str)
        end
    end
end

"""
    mtk2esm_gaps(sys::ModelingToolkit.AbstractSystem) -> Vector{GapReport}

Pre-flight scan: returns any schema-gap constructs in `sys` without
producing the full ESM export. Use this to decide whether a model is ready
to migrate before running the full round-trip.
"""
function mtk2esm_gaps(sys::ModelingToolkit.AbstractSystem)
    # The simplest implementation runs mtk2esm and discards the output;
    # gap detection has the same pass structure. We suppress the @warn here
    # by capturing the logger.
    gaps = GapReport[]
    append!(gaps, _mtk_brownians(sys) |> b -> isempty(b) ? GapReport[] :
        [GapReport("gt-kuxo",
            "system has $(length(b)) brownian variable(s)",
            "system.brownians")])
    return gaps
end

# ========================================
# PDE discretization on AbstractCurvilinearGrid (esm-2qw)
# ========================================
# Port of EarthSciDiscretizations' SciMLBase.discretize(sys::PDESystem,
# disc::FVCubedSphere) refactored against the esm-a3z Grid trait. The original
# code took a CubedSphereGrid and addressed cells with (panel, i, j) tuples;
# this version takes any AbstractCurvilinearGrid and uses flat cell indices
# resolved via neighbor_indices(grid, axis, ±1). The chain-rule transform
# from computational (ξ, η) to physical (target) coordinates uses
# coord_jacobian(grid, target) and coord_jacobian_second(grid, target).

"""
    EarthSciSerialization.discretize(sys::ModelingToolkit.PDESystem,
                                     grid::AbstractCurvilinearGrid;
                                     target::Symbol=:auto,
                                     xi_axis::Symbol=:xi,
                                     eta_axis::Symbol=:eta,
                                     kwargs...) -> ODEProblem

Discretize a `ModelingToolkit.PDESystem` onto a curvilinear grid via the
2D centered-FD chain-rule pipeline ported from EarthSciDiscretizations.
Returns an `ODEProblem` ready for `solve`.

The grid is queried only through the esm-a3z Grid trait — no struct fields:

  - `n_cells(grid)`, `cell_centers(grid, axis)`, `cell_widths(grid, axis)`
  - `neighbor_indices(grid, axis, ±1)` for ξ/η stencil neighbors. Cross-panel
    / periodic / cubed-sphere connectivity is resolved inside the impl.
    Sentinel `0` (boundary) falls back to the cell itself.
  - `coord_jacobian(grid, target)`        — `(N, 2, 2)`, `∂(comp)/∂(target)`
  - `coord_jacobian_second(grid, target)` — `(N, 2, 2, 2)`, second derivs

`target` defaults to a symbol joining the spatial IV names (e.g. for
`(t, lon, lat)` the default is `:lon_lat`). `xi_axis`/`eta_axis` name the
two computational axes the grid impl exposes through `cell_widths` and
`neighbor_indices` — pass `:x`/`:y` for the test-Cartesian grid.

Each spatial Differential is interpreted as either:
  - direct in (`:xi`, `:eta`, `:ξ`, `:η`, `xi_axis`, `eta_axis`) → centered
    finite difference in computational space, or
  - target axis matching one of the spatial IVs → chain-rule expansion via
    `coord_jacobian` (and `coord_jacobian_second` for second derivatives).

Initial conditions come from BCs of the form `dv(t0, ivs...) ~ rhs(ivs...)`;
unmatched DVs default to zero. The single time domain in `sys.domain`
defines `tspan`.
"""
function EarthSciSerialization.discretize(
        sys::PDESystem,
        grid::EarthSciSerialization.AbstractCurvilinearGrid;
        target::Symbol = :auto,
        xi_axis::Symbol = :xi,
        eta_axis::Symbol = :eta,
        kwargs...,
    )
    ESM_ = EarthSciSerialization
    N = ESM_.n_cells(grid)
    dξ = ESM_._uniform_dx(grid, xi_axis)
    dη = ESM_._uniform_dx(grid, eta_axis)

    # Split sys.ivs into the time IV and the spatial IVs (in declared order).
    spatial_ivs = Any[]
    t_iv = nothing
    for iv in sys.ivs
        nm = Symbol(Symbolics.tosymbol(iv, escape=false))
        if nm === :t
            t_iv = iv
        else
            push!(spatial_ivs, iv)
        end
    end
    t_iv === nothing &&
        error("discretize: PDESystem missing a time independent variable named :t")
    isempty(spatial_ivs) &&
        error("discretize: PDESystem has no spatial independent variables")
    spatial_iv_names = Symbol[
        Symbol(Symbolics.tosymbol(iv, escape=false)) for iv in spatial_ivs
    ]

    if target === :auto
        target = Symbol(join(string.(spatial_iv_names), "_"))
    end

    # Bulk metric arrays. The chain-rule path needs the coordinate Jacobian
    # and its second derivative; the FV stencil itself is built from neighbor
    # indices + dξ, dη, so we don't need metric_g / metric_ginv here.
    cj  = ESM_.coord_jacobian(grid, target)         # (N, 2, T)
    cj2 = ESM_.coord_jacobian_second(grid, target)  # (N, 2, T, T)
    size(cj, 1)  == N || error("discretize: coord_jacobian first dim $(size(cj,1)) != n_cells=$N")
    size(cj2, 1) == N || error("discretize: coord_jacobian_second first dim $(size(cj2,1)) != n_cells=$N")

    # Neighbor index arrays. Boundary sentinels (0) fall back to self so the
    # generated stencils stay well-defined; concrete grids that wrap (periodic,
    # cubed-sphere, MPAS) hide the boundary inside neighbor_indices.
    self_idx = collect(1:N)
    _safe(arr) = map((n, s) -> n == 0 ? s : n, arr, self_idx)
    nbE  = _safe(ESM_.neighbor_indices(grid, xi_axis,  +1))
    nbW  = _safe(ESM_.neighbor_indices(grid, xi_axis,  -1))
    nbNp = _safe(ESM_.neighbor_indices(grid, eta_axis, +1))
    nbSp = _safe(ESM_.neighbor_indices(grid, eta_axis, -1))
    nbNE = _safe(ESM_.neighbor_indices(grid, eta_axis, +1)[nbE])
    nbNW = _safe(ESM_.neighbor_indices(grid, eta_axis, +1)[nbW])
    nbSE = _safe(ESM_.neighbor_indices(grid, eta_axis, -1)[nbE])
    nbSW = _safe(ESM_.neighbor_indices(grid, eta_axis, -1)[nbW])

    # Per-cell symbolic state arrays of length N, one per dependent variable.
    dvs = sys.dvs
    disc_vars = Dict{Any,Any}()
    for dv in dvs
        nm = Symbol(replace(String(Symbolics.tosymbol(dv, escape=false)), '.' => '_'))
        arr = _make_array_dep_var(nm, Any[t_iv], [1:N])
        disc_vars[dv] = arr
    end

    # Per-cell ODE equations. Each PDE equation expands into N scalar eqns.
    Dt = ModelingToolkit.Differential(t_iv)
    all_eqs = Symbolics.Equation[]
    for eq in sys.eqs
        lhs_dv = _identify_lhs_dv_pde(eq.lhs, dvs)
        lhs_arr = disc_vars[lhs_dv]
        for c in 1:N
            nb = (E=nbE[c], W=nbW[c], Np=nbNp[c], Sp=nbSp[c],
                  NE=nbNE[c], NW=nbNW[c], SE=nbSE[c], SW=nbSW[c])
            rhs_c = _substitute_at_cell(
                eq.rhs, disc_vars, dvs, spatial_iv_names,
                xi_axis, eta_axis, c, nb, dξ, dη, cj, cj2,
            )
            push!(all_eqs, Dt(lhs_arr[c]) ~ rhs_c)
        end
    end

    sys_disc = ModelingToolkit.System(all_eqs, t_iv; name=:disc_pde)
    compiled = ModelingToolkit.mtkcompile(sys_disc)

    u0 = _build_u0_pde(sys, disc_vars, dvs, spatial_ivs, spatial_iv_names, grid, t_iv)
    tspan = _extract_tspan_pde(sys, t_iv)
    return ModelingToolkit.ODEProblem(compiled, u0, tspan; kwargs...)
end

# Identify which dependent variable's time derivative sits on the LHS of an
# equation `D(u(t, ...)) ~ rhs`.
function _identify_lhs_dv_pde(lhs, dvs)
    ex = Symbolics.unwrap(lhs)
    if Symbolics.iscall(ex) && Symbolics.operation(ex) isa ModelingToolkit.Differential
        inner = Symbolics.wrap(Symbolics.arguments(ex)[1])
        for dv in dvs
            isequal(Symbolics.unwrap(inner), Symbolics.unwrap(dv)) && return dv
        end
        # Name-based fallback (common when the LHS DV came from a different
        # @variables call than the one stored in sys.dvs).
        inner_name = Symbol(Symbolics.tosymbol(inner, escape=false))
        for dv in dvs
            Symbol(Symbolics.tosymbol(dv, escape=false)) == inner_name && return dv
        end
    end
    error("discretize: cannot identify dependent variable for LHS $(lhs)")
end

# Read the order field off a Differential, falling back to 1 for older
# Symbolics versions that don't carry one.
_diff_order(op::ModelingToolkit.Differential) =
    hasproperty(op, :order) ? Int(getproperty(op, :order)) : 1

# Resolve a Differential's wrt-symbol to either a direct computational axis
# tag (`:xi`, `:eta`) or a `(:target, k)` tag indicating the k-th target
# axis (chain-rule path via `coord_jacobian[:, :, k]`).
function _resolve_axis(name::Symbol, xi_axis::Symbol, eta_axis::Symbol,
                      spatial_iv_names::Vector{Symbol})
    name == xi_axis  && return :xi
    name == eta_axis && return :eta
    name in (:xi, :ξ)  && return :xi
    name in (:eta, :η) && return :eta
    for (k, nm) in pairs(spatial_iv_names)
        nm == name && return (:target, k)
    end
    error("discretize: cannot resolve axis '$name' (not $xi_axis, $eta_axis, or one of $(spatial_iv_names))")
end

# Recursively walk a symbolic RHS expression at flat cell index `c`,
# substituting DV calls with `disc_vars[dv][c]` and Differential nodes with
# their centered-FD form (with chain-rule transform when the wrt-axis is a
# target axis). Nonlinear terms are preserved by recursing into operator
# arguments — `u^2` becomes `u_arr[c]^2`, `sin(u)` becomes `sin(u_arr[c])`.
function _substitute_at_cell(expr, disc_vars, dvs, spatial_iv_names,
                              xi_axis, eta_axis, c, nb, dξ, dη, cj, cj2)
    ex = Symbolics.unwrap(expr)
    if !Symbolics.iscall(ex)
        return Symbolics.wrap(ex)
    end
    op = Symbolics.operation(ex)
    args = Symbolics.arguments(ex)

    # DV call (e.g. u(t, lon, lat))?
    for dv in dvs
        isequal(Symbolics.wrap(ex), dv) && return disc_vars[dv][c]
    end

    # Differential — first or second order. Symbolics ≥ 7 fuses repeated
    # Differentials in the same variable into a single `Differential(x, 2)`
    # node carrying an `order` field, so we need to handle BOTH that fused
    # form AND the explicit `Differential(y)(Differential(x)(u))` nesting
    # (which stays separate when the wrt-variables differ).
    if op isa ModelingToolkit.Differential
        outer = _resolve_axis(Symbol(op.x), xi_axis, eta_axis, spatial_iv_names)
        inner_arg = args[1]
        order = _diff_order(op)

        if order == 2
            # ∂²/∂x² form — outer and inner axis are the same.
            return _second_deriv_cell(inner_arg, outer, outer, disc_vars, dvs,
                                       c, nb, dξ, dη, cj, cj2)
        end
        order > 2 && error("discretize: Differential order $(order) not supported (≤ 2 only)")

        # First-order outer Differential. Look for a nested Differential to
        # promote to a mixed second derivative ∂²/∂x∂y.
        if Symbolics.iscall(inner_arg) &&
           Symbolics.operation(inner_arg) isa ModelingToolkit.Differential
            inner_op = Symbolics.operation(inner_arg)
            inner_order = _diff_order(inner_op)
            inner_order == 1 ||
                error("discretize: nested Differential of order $(inner_order) not supported")
            inner = _resolve_axis(Symbol(inner_op.x), xi_axis, eta_axis, spatial_iv_names)
            innermost = Symbolics.arguments(inner_arg)[1]
            return _second_deriv_cell(innermost, outer, inner, disc_vars, dvs,
                                       c, nb, dξ, dη, cj, cj2)
        end
        return _first_deriv_cell(inner_arg, outer, disc_vars, dvs,
                                  c, nb, dξ, dη, cj)
    end

    # General operator — recurse into arguments (preserves nonlinear structure).
    new_args = [
        _substitute_at_cell(Symbolics.wrap(a), disc_vars, dvs, spatial_iv_names,
                            xi_axis, eta_axis, c, nb, dξ, dη, cj, cj2)
        for a in args
    ]
    return Symbolics.wrap(op(Symbolics.unwrap.(new_args)...))
end

# Evaluate a (possibly nonlinear) symbolic expression at neighbor cell `cn`,
# replacing every DV call with `disc_vars[dv][cn]`. Used to build the value
# of `f(u, v, ...)` at each stencil point during second-derivative assembly.
function _eval_expr_at(expr, disc_vars, dvs, cn)
    ex = Symbolics.unwrap(expr)
    if !Symbolics.iscall(ex)
        return Symbolics.wrap(ex)
    end
    for dv in dvs
        isequal(Symbolics.wrap(ex), dv) && return disc_vars[dv][cn]
    end
    op = Symbolics.operation(ex)
    args = Symbolics.arguments(ex)
    new_args = [_eval_expr_at(Symbolics.wrap(a), disc_vars, dvs, cn) for a in args]
    return Symbolics.wrap(op(Symbolics.unwrap.(new_args)...))
end

# Centered first derivative w.r.t. an axis, with chain-rule transform when
# the axis is a physical target axis.
function _first_deriv_cell(inner_arg, outer, disc_vars, dvs,
                            c, nb, dξ, dη, cj)
    f_E = _eval_expr_at(inner_arg, disc_vars, dvs, nb.E)
    f_W = _eval_expr_at(inner_arg, disc_vars, dvs, nb.W)
    f_N = _eval_expr_at(inner_arg, disc_vars, dvs, nb.Np)
    f_S = _eval_expr_at(inner_arg, disc_vars, dvs, nb.Sp)
    df_dξ = (f_E - f_W) / (2 * dξ)
    df_dη = (f_N - f_S) / (2 * dη)
    if outer === :xi
        return df_dξ
    elseif outer === :eta
        return df_dη
    elseif outer isa Tuple && outer[1] === :target
        k = outer[2]
        return cj[c, 1, k] * df_dξ + cj[c, 2, k] * df_dη
    end
    error("discretize: bad outer axis tag $(outer)")
end

# Full chain-rule second derivative at cell `c`:
#   ∂²u/∂x∂y = Σ_kl (∂ξ_k/∂x)(∂ξ_l/∂y) ∂²u/(∂ξ_k∂ξ_l)
#            + Σ_k  (∂²ξ_k/∂x∂y)         ∂u/∂ξ_k
# Computational-axis derivatives use plain centered second / mixed FD.
function _second_deriv_cell(innermost, outer, inner, disc_vars, dvs,
                              c, nb, dξ, dη, cj, cj2)
    f_C  = _eval_expr_at(innermost, disc_vars, dvs, c)
    f_E  = _eval_expr_at(innermost, disc_vars, dvs, nb.E)
    f_W  = _eval_expr_at(innermost, disc_vars, dvs, nb.W)
    f_N  = _eval_expr_at(innermost, disc_vars, dvs, nb.Np)
    f_S  = _eval_expr_at(innermost, disc_vars, dvs, nb.Sp)
    f_NE = _eval_expr_at(innermost, disc_vars, dvs, nb.NE)
    f_NW = _eval_expr_at(innermost, disc_vars, dvs, nb.NW)
    f_SE = _eval_expr_at(innermost, disc_vars, dvs, nb.SE)
    f_SW = _eval_expr_at(innermost, disc_vars, dvs, nb.SW)

    d2f_dξ2  = (f_E - 2 * f_C + f_W) / dξ^2
    d2f_dη2  = (f_N - 2 * f_C + f_S) / dη^2
    d2f_dξdη = (f_NE - f_NW - f_SE + f_SW) / (4 * dξ * dη)
    df_dξ    = (f_E - f_W) / (2 * dξ)
    df_dη    = (f_N - f_S) / (2 * dη)

    a_ξ_o, a_η_o = _chain_coeffs(outer, c, cj)
    a_ξ_i, a_η_i = _chain_coeffs(inner, c, cj)
    b_ξ,   b_η   = _second_chain_coeffs(outer, inner, c, cj2)

    return (
        a_ξ_o * a_ξ_i * d2f_dξ2 +
        (a_ξ_o * a_η_i + a_η_o * a_ξ_i) * d2f_dξdη +
        a_η_o * a_η_i * d2f_dη2 +
        b_ξ * df_dξ + b_η * df_dη
    )
end

# (∂ξ/∂axis, ∂η/∂axis): identity for computational axes, coord-jacobian
# lookup for target axes.
function _chain_coeffs(axis, c, cj)
    if axis === :xi
        return (1.0, 0.0)
    elseif axis === :eta
        return (0.0, 1.0)
    elseif axis isa Tuple && axis[1] === :target
        k = axis[2]
        return (cj[c, 1, k], cj[c, 2, k])
    end
    error("discretize: bad axis tag $(axis)")
end

# (∂²ξ/∂outer∂inner, ∂²η/∂outer∂inner): nonzero only when both axes are
# target (physical) axes — second derivatives of computational axes vanish.
function _second_chain_coeffs(outer, inner, c, cj2)
    if outer isa Tuple && outer[1] === :target &&
       inner isa Tuple && inner[1] === :target
        ko, ki = outer[2], inner[2]
        return (cj2[c, 1, ko, ki], cj2[c, 2, ko, ki])
    end
    return (0.0, 0.0)
end

# Project initial conditions from `sys.bcs` of form `dv(t0, ivs...) ~ rhs(ivs...)`
# onto each cell. Unmatched DVs default to zero per the ESD reference.
function _build_u0_pde(sys, disc_vars, dvs, spatial_ivs, spatial_iv_names,
                       grid, t_iv)
    N = EarthSciSerialization.n_cells(grid)
    tspan = _extract_tspan_pde(sys, t_iv)
    t0 = tspan[1]

    # Cache cell-center coordinates per spatial IV.
    coord_arrays = Dict{Symbol,Vector{Float64}}()
    for nm in spatial_iv_names
        coord_arrays[nm] = Vector{Float64}(EarthSciSerialization.cell_centers(grid, nm))
    end

    u0 = Pair[]
    for dv in dvs
        arr = disc_vars[dv]
        ic_found = false
        for bc in sys.bcs
            if _is_initial_condition_pde(bc, dv, t0)
                rhs = bc.rhs
                for c in 1:N
                    val = _eval_ic_pde(rhs, spatial_ivs, spatial_iv_names,
                                        coord_arrays, c)
                    push!(u0, arr[c] => val)
                end
                ic_found = true
                break
            end
        end
        if !ic_found
            for c in 1:N
                push!(u0, arr[c] => 0.0)
            end
        end
    end
    return u0
end

function _is_initial_condition_pde(bc, dv, t0)
    lhs = Symbolics.unwrap(bc.lhs)
    Symbolics.iscall(lhs) || return false
    args = Symbolics.arguments(lhs)
    isempty(args) && return false
    lhs_name = Symbol(Symbolics.tosymbol(Symbolics.wrap(lhs), escape=false))
    dv_name  = Symbol(Symbolics.tosymbol(dv, escape=false))
    lhs_name == dv_name || return false
    t_val = Symbolics.value(Symbolics.wrap(args[1]))
    return t_val isa Number && isapprox(Float64(t_val), t0)
end

function _eval_ic_pde(rhs, spatial_ivs, spatial_iv_names, coord_arrays, c)
    subs = Dict{Any,Any}()
    for (iv, nm) in zip(spatial_ivs, spatial_iv_names)
        val = coord_arrays[nm][c]
        # Insert under both wrapped and unwrapped forms so substitute matches
        # whichever form the BC's RHS happens to carry.
        subs[iv] = val
        subs[Symbolics.unwrap(iv)] = val
    end
    v = Symbolics.value(Symbolics.substitute(rhs, subs))
    if v isa Number
        return Float64(v)
    end
    # Fall through: substitute left a still-symbolic form (e.g. `cos(0.5)`
    # that the simplifier didn't fold). Round-trip through Julia's expression
    # evaluator — matches ESD's `_eval_ic` reference path.
    return Float64(Core.eval(Main, Symbolics.toexpr(v)))
end

function _extract_tspan_pde(sys, t_iv)
    t_name = Symbol(Symbolics.tosymbol(t_iv, escape=false))
    for d in sys.domain
        Symbol(d.variables) == t_name &&
            return (Float64(d.domain.left), Float64(d.domain.right))
    end
    error("discretize: no time domain found in PDESystem.domain")
end

end # module EarthSciSerializationMTKExt
