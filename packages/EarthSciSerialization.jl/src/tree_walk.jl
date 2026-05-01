"""
Tree-walk evaluator for discretized `.esm` models (gt-e8yw).

Compiles the canonical-form equations of a `Model` into a plain
`f!(du, u, p, t)` by walking the expression AST at every RHS call.
Bypasses ModelingToolkit entirely, so compile time is independent of
the system size — the path is intended for discretized PDEs whose
scalar count exceeds MTK's tearing/codegen ceiling.

Public API:

    build_evaluator(model::Model; kwargs...)
        → (f!, u0::Vector{Float64}, p::NamedTuple, tspan::Tuple{Float64,Float64},
           var_map::Dict{String,Int})

The returned tuple plugs straight into `ODEProblem(f!, u0, tspan, p)`.
`var_map` is the state-name → index lookup so callers can probe the
solution at specific variables.

Dict and EsmFile convenience entry points select a model by name (or
the single model, if the file carries only one).
"""

# ============================================================
# 1. Error type
# ============================================================

"""
    TreeWalkError

Raised when the walker encounters an operator or construct it cannot
evaluate. `code` is always one of the `E_TREEWALK_*` codes from the
bead's acceptance criterion; `detail` carries op name or variable name
for diagnostics.
"""
struct TreeWalkError <: Exception
    code::String
    detail::String
end

Base.showerror(io::IO, e::TreeWalkError) =
    print(io, "$(e.code): $(e.detail)")

# ============================================================
# 2. Build — entry points
# ============================================================

"""
    build_evaluator(model::Model; initial_conditions=Dict(),
                    parameter_overrides=Dict(), tspan=nothing,
                    registered_functions=Dict())

Build a tree-walk ODE RHS evaluator for `model`.

All state variables must be scalar (shape === nothing) — the walker
assumes equations have already been scalarized by the discretize
pipeline. Array-typed ops (`arrayop`, `makearray`, `broadcast`,
`reshape`, `transpose`, `concat`) therefore raise
`E_TREEWALK_UNSUPPORTED_OP` if they appear in an RHS.

The returned `f!` closure reads `u`, the captured parameter vector
`p` (a NamedTuple keyed by parameter name), and `t`, and writes
time-derivatives into `du`. Observed variables are substituted into
RHS expressions at build time.

Keyword arguments:

* `initial_conditions::Dict{String,<:Real}` — override the default
  values in `model.variables` for specific state variables.
* `parameter_overrides::Dict{String,<:Real}` — override the default
  values for specific parameters.
* `tspan::Union{Nothing,Tuple{Real,Real}}` — explicit time span. If
  `nothing`, the first inline `tests` block's `time_span` is used; if
  the model has no tests, the null default `(0.0, 1.0)` is returned.
* `registered_functions::Dict{String,<:Function}` — handlers for
  `call` ops, keyed by `handler_id`.
"""
function build_evaluator(model::Model;
                         initial_conditions::AbstractDict=Dict{String,Float64}(),
                         parameter_overrides::AbstractDict=Dict{String,Float64}(),
                         tspan::Union{Nothing,Tuple{<:Real,<:Real}}=nothing,
                         registered_functions::AbstractDict=Dict{String,Function}())
    # ---- Partition variables ----
    state_names = String[]
    param_names = String[]
    observed_names = String[]
    for (name, v) in model.variables
        if v.shape !== nothing
            throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_SHAPE", name))
        end
        if v.type == StateVariable
            push!(state_names, name)
        elseif v.type == ParameterVariable
            push!(param_names, name)
        elseif v.type == ObservedVariable
            push!(observed_names, name)
        elseif v.type == BrownianVariable
            throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_BROWNIAN", name))
        end
    end
    sort!(state_names)
    sort!(param_names)

    # ---- Index map & initial condition vector ----
    var_map = Dict{String,Int}(name => i for (i, name) in enumerate(state_names))
    u0 = Vector{Float64}(undef, length(state_names))
    for (i, name) in enumerate(state_names)
        if haskey(initial_conditions, name)
            u0[i] = Float64(initial_conditions[name])
        else
            d = model.variables[name].default
            u0[i] = d === nothing ? 0.0 : Float64(d)
        end
    end

    # ---- Parameter NamedTuple ----
    p_vals = Float64[]
    p_syms = Symbol[]
    for name in param_names
        push!(p_syms, Symbol(name))
        if haskey(parameter_overrides, name)
            push!(p_vals, Float64(parameter_overrides[name]))
        else
            d = model.variables[name].default
            push!(p_vals, d === nothing ? 0.0 : Float64(d))
        end
    end
    p = NamedTuple{Tuple(p_syms)}(Tuple(p_vals))

    # ---- Observed substitution ----
    observed_exprs = Dict{String,Expr}()
    derivative_eqs = Equation[]
    for eq in model.equations
        if _is_time_derivative_lhs(eq.lhs)
            push!(derivative_eqs, eq)
        elseif isa(eq.lhs, VarExpr) && eq.lhs.name in observed_names
            observed_exprs[eq.lhs.name] = eq.rhs
        else
            # Algebraic constraint / unsupported equation form.
            # The tree-walk path is ODE-only; see bead's "Not in scope".
            throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_EQUATION",
                                _equation_tag(eq)))
        end
    end
    resolved_obs = _resolve_observed(observed_exprs)

    # ---- Registered-function handlers ----
    reg_funcs = Dict{String,Any}(String(k) => v
                                 for (k, v) in registered_functions)

    # ---- Build per-derivative compiled-IR list ----
    # Each entry is (state_index, compiled-node). The RHS is inlined
    # with observed variables, then compiled to the compact `_Node`
    # form so the per-step inner loop is a single type-stable dispatch.
    param_sym_set = Set(p_syms)
    rhs_list = Vector{Tuple{Int,_Node}}(undef, length(derivative_eqs))
    covered = falses(length(state_names))
    for (k, eq) in enumerate(derivative_eqs)
        state_name = (eq.lhs::OpExpr).args[1]
        if !isa(state_name, VarExpr)
            throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_LHS",
                                string(typeof(state_name))))
        end
        idx = get(var_map, state_name.name, 0)
        if idx == 0
            throw(TreeWalkError("E_TREEWALK_UNKNOWN_STATE", state_name.name))
        end
        if covered[idx]
            throw(TreeWalkError("E_TREEWALK_DUPLICATE_DERIVATIVE",
                                state_name.name))
        end
        covered[idx] = true
        rhs = isempty(resolved_obs) ? eq.rhs :
              _sub_preserving(eq.rhs, resolved_obs)
        rhs_list[k] = (idx, _compile(rhs, var_map, param_sym_set, reg_funcs))
    end
    # States without a D(...) equation get du=0 (integrator leaves them
    # at their initial value — a common pattern for reified constants).

    # ---- Default tspan ----
    tspan_default = _pick_tspan(tspan, model)

    # ---- Closure ----
    f! = _make_rhs(rhs_list)

    return f!, u0, p, tspan_default, var_map
end

"""
    build_evaluator(file::EsmFile; model_name=nothing, kwargs...)

Delegate to the typed entry point after selecting the model.
"""
function build_evaluator(file::EsmFile;
                         model_name::Union{Nothing,AbstractString}=nothing,
                         kwargs...)
    model = _select_model(file, model_name)
    return build_evaluator(model; kwargs...)
end

"""
    build_evaluator(esm::AbstractDict; model_name=nothing, kwargs...)

Parse a raw ESM dict, then delegate. This is the signature from the
bead description; the typed entry point is faster for callers that
already have a parsed `Model`.
"""
function build_evaluator(esm::AbstractDict;
                         model_name::Union{Nothing,AbstractString}=nothing,
                         kwargs...)
    # `coerce_esm_file` expects a JSON3-style object (property-access
    # getters). Round-trip through JSON3 so raw Julia Dict inputs — the
    # signature from the bead description — work.
    file = coerce_esm_file(JSON3.read(JSON3.write(esm)))
    return build_evaluator(file; model_name=model_name, kwargs...)
end

"""
    evaluate_expr(expr::Expr, bindings::AbstractDict;
                  registered_functions::AbstractDict=Dict{String,Function}())::Float64

Evaluate a single AST expression at the supplied numeric `bindings` by
running it through the same compile + walker pipeline as
[`build_evaluator`](@ref). All keys of `bindings` are exposed as readable
state variables; the special name `"t"` (if present) is bound to the
walker's time argument as well. Adding an op to the tree-walk evaluator
transparently extends this entry point — there is no separate dispatch
table.

Throws `UnboundVariableError` when `expr` references a name that is not
in `bindings` and is not the time variable; other failures surface as
[`TreeWalkError`](@ref).
"""
function evaluate_expr(expr::Expr, bindings::AbstractDict;
                       registered_functions::AbstractDict=Dict{String,Function}())::Float64
    var_map = Dict{String,Int}()
    u = Vector{Float64}(undef, length(bindings))
    i = 0
    for (name, _) in bindings
        i += 1
        sname = String(name)
        var_map[sname] = i
        u[i] = Float64(bindings[name])
    end
    reg_funcs = Dict{String,Any}(String(k) => v for (k, v) in registered_functions)
    node = try
        _compile(expr, var_map, Set{Symbol}(), reg_funcs)
    catch e
        if e isa TreeWalkError && e.code == "E_TREEWALK_UNBOUND_VARIABLE"
            throw(UnboundVariableError(e.detail,
                  "Variable '$(e.detail)' not found in bindings"))
        end
        rethrow(e)
    end
    t = haskey(bindings, "t") ? Float64(bindings["t"]) : 0.0
    return _eval_node(node, u, NamedTuple(), t)
end

# ============================================================
# 3. Compiled-IR — one-shot compilation to a compact, type-stable tree
# ============================================================
#
# `_eval` below walks the raw `OpExpr` tree. That's correct but every
# op dispatch is an O(N) chain of String comparisons, and every
# VarExpr lookup does a Dict probe. For 4096-equation models the
# overhead dominates. `_compile` walks the expression once at build
# time and produces `_Node` trees where:
#
#   * op is a `Symbol` (pointer compare, not byte compare)
#   * state refs have their u-index baked in
#   * parameter refs have their `Val{sym}` type param baked in for
#     `getfield(p, Val)` — monomorphic NamedTuple access
#   * literals are pre-promoted to Float64
#   * registered-function handlers are looked up and captured once
#
# The compiled tree keeps semantics identical to walking `OpExpr`
# directly; `_eval` stays available for the unit-test helper which
# exercises the fallback path.

# _NKind encodes what a node is. Keeping it as a Bare integer (UInt8)
# gives a fast `kind === K_*` dispatch inside `_eval_node`.
const _NK_LITERAL = UInt8(1)
const _NK_STATE   = UInt8(2)   # read u[idx]
const _NK_PARAM   = UInt8(3)   # read p.<sym>
const _NK_TIME    = UInt8(4)   # return t
const _NK_OP      = UInt8(5)   # apply op to children

struct _Node
    kind::UInt8
    op::Symbol
    literal::Float64
    idx::Int
    sym::Symbol
    handler::Any
    children::Vector{_Node}
end

function _mknode(; kind::UInt8, op::Symbol=Symbol(""),
                 literal::Float64=0.0, idx::Int=0,
                 sym::Symbol=Symbol(""), handler=nothing,
                 children::Vector{_Node}=_Node[])
    return _Node(kind, op, literal, idx, sym, handler, children)
end

# `param_syms` is a `Set{Symbol}` so parameters can be distinguished
# from unbound-variable errors without another pass.
function _compile(expr::NumExpr, var_map, param_syms, reg_funcs)
    return _mknode(kind=_NK_LITERAL, literal=expr.value)
end
function _compile(expr::IntExpr, var_map, param_syms, reg_funcs)
    return _mknode(kind=_NK_LITERAL, literal=Float64(expr.value))
end
function _compile(expr::VarExpr, var_map, param_syms, reg_funcs)
    name = expr.name
    if name == "t"
        return _mknode(kind=_NK_TIME)
    end
    idx = get(var_map, name, 0)
    if idx != 0
        return _mknode(kind=_NK_STATE, idx=idx)
    end
    sym = Symbol(name)
    if sym in param_syms
        return _mknode(kind=_NK_PARAM, sym=sym)
    end
    throw(TreeWalkError("E_TREEWALK_UNBOUND_VARIABLE", name))
end
function _compile(expr::OpExpr, var_map, param_syms, reg_funcs)
    op_sym = Symbol(expr.op)
    handler = nothing
    if op_sym === :fn
        # Closed function registry (esm-spec §9.2 / esm-tzp). The function
        # name is captured in the node's `handler` slot as a tuple of
        # (name::String, const_array_or_nothing). For
        # `interp.searchsorted` the second arg is a const-op array which
        # we pre-extract so the runtime hot path doesn't walk the AST.
        fname = expr.name
        fname === nothing &&
            throw(TreeWalkError("E_TREEWALK_FN_MISSING_NAME", expr.op))
        if !(fname in _CLOSED_FUNCTION_NAMES)
            throw(TreeWalkError("E_TREEWALK_UNKNOWN_CLOSED_FUNCTION", fname))
        end
        if fname == "interp.searchsorted"
            length(expr.args) == 2 ||
                throw(TreeWalkError("E_TREEWALK_FN_ARITY",
                    "interp.searchsorted expects 2 args, got $(length(expr.args))"))
            tab = expr.args[2]
            if !(tab isa OpExpr && tab.op == "const" && tab.value isa AbstractVector)
                throw(TreeWalkError("E_TREEWALK_FN_ARG_NOT_CONST",
                    "interp.searchsorted: 2nd arg must be a `const`-op array"))
            end
            # Compile only the scalar first arg as a child; carry the
            # constant array on the node so the runtime call is one
            # _eval_node + one closed-function dispatch.
            children = _Node[_compile(expr.args[1], var_map, param_syms, reg_funcs)]
            handler = (fname, Any[tab.value])
        elseif fname == "interp.linear"
            # Args = (table, axis, x). Const arrays at positions [1, 2];
            # scalar query at [3]. Pre-extract the const arrays so the
            # runtime hot path skips AST traversal.
            length(expr.args) == 3 ||
                throw(TreeWalkError("E_TREEWALK_FN_ARITY",
                    "interp.linear expects 3 args, got $(length(expr.args))"))
            tbl  = _require_const_array(expr.args[1], "interp.linear", "table")
            axs  = _require_const_array(expr.args[2], "interp.linear", "axis")
            children = _Node[_compile(expr.args[3], var_map, param_syms, reg_funcs)]
            handler = (fname, Any[tbl, axs])
        elseif fname == "interp.bilinear"
            # Args = (table, axis_x, axis_y, x, y). Const arrays at [1, 2, 3];
            # scalar queries at [4, 5].
            length(expr.args) == 5 ||
                throw(TreeWalkError("E_TREEWALK_FN_ARITY",
                    "interp.bilinear expects 5 args, got $(length(expr.args))"))
            tbl  = _require_const_array(expr.args[1], "interp.bilinear", "table")
            axx  = _require_const_array(expr.args[2], "interp.bilinear", "axis_x")
            axy  = _require_const_array(expr.args[3], "interp.bilinear", "axis_y")
            children = _Node[
                _compile(expr.args[4], var_map, param_syms, reg_funcs),
                _compile(expr.args[5], var_map, param_syms, reg_funcs),
            ]
            handler = (fname, Any[tbl, axx, axy])
        else
            children = _Node[_compile(a, var_map, param_syms, reg_funcs)
                             for a in expr.args]
            handler = (fname, nothing)
        end
        return _mknode(kind=_NK_OP, op=op_sym, children=children, handler=handler)
    end

    children = _Node[_compile(a, var_map, param_syms, reg_funcs)
                     for a in expr.args]
    if op_sym === :const
        # Scalar `const` ops fold to a literal at compile time. Non-scalar
        # `const` only ever appears as an argument to ops that consume
        # arrays (handled in their respective compile paths above).
        v = expr.value
        if v isa Real && !(v isa Bool)
            return _mknode(kind=_NK_LITERAL, literal=Float64(v))
        end
        throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_OP",
            "non-scalar `const` op outside an array-consuming position"))
    elseif op_sym === :enum
        throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_OP",
            "`enum` op encountered after lowering — call `lower_enums!` before compile"))
    elseif op_sym === :call
        # Removed in v0.3.0 (esm-spec §9 closure). `parse_expression` already
        # rejects file-loaded `call` ops; reaching this arm means a caller
        # constructed a `call` OpExpr programmatically.
        throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_OP",
            "`call` op was removed in v0.3.0 — migrate to `fn` ops " *
            "or AST equations (esm-spec §9 closure, RFC closed-function-registry)"))
    elseif op_sym === :D
        throw(TreeWalkError("E_TREEWALK_D_IN_RHS",
                            "D(...) only allowed in equation LHS"))
    elseif op_sym === :grad || op_sym === :div || op_sym === :laplacian
        # esm-i7b: spatial differential operators MUST be rewritten by ESD
        # discretization rules into `arrayop` AST before reaching the
        # simulator. Encountering one here means the canonical pipeline
        # broke; surface the violation rather than substituting zero (the
        # historical stub behaviour in other bindings).
        throw(TreeWalkError("E_TREEWALK_UNREACHABLE_SPATIAL_OP",
            "UnreachableSpatialOperatorError: encountered '$(expr.op)' node " *
            "in simulation evaluation. Spatial operators must be rewritten " *
            "by ESD discretization rules before reaching the simulator. " *
            "Pipeline contract violated."))
    elseif op_sym === :arrayop || op_sym === :makearray ||
           op_sym === :broadcast || op_sym === :reshape ||
           op_sym === :transpose || op_sym === :concat ||
           op_sym === :index || op_sym === :bc
        throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_OP",
                            "$(expr.op) (must be pre-scalarized before tree-walk)"))
    end
    return _mknode(kind=_NK_OP, op=op_sym, children=children, handler=handler)
end

# ============================================================
# 4. Compiled walker
# ============================================================

@inline function _eval_node(n::_Node, u, p, t)
    k = n.kind
    if k === _NK_LITERAL
        return n.literal
    elseif k === _NK_STATE
        @inbounds return u[n.idx]
    elseif k === _NK_PARAM
        return getfield(p, n.sym)
    elseif k === _NK_TIME
        return t
    else
        return _eval_node_op(n, u, p, t)
    end
end

function _eval_node_op(n::_Node, u, p, t)
    op = n.op
    c = n.children

    # Arithmetic — the hot paths.
    if op === :+
        length(c) == 1 && return _eval_node(c[1], u, p, t)
        acc = _eval_node(c[1], u, p, t)
        @inbounds for i in 2:length(c)
            acc += _eval_node(c[i], u, p, t)
        end
        return acc
    elseif op === :*
        length(c) == 1 && return _eval_node(c[1], u, p, t)
        acc = _eval_node(c[1], u, p, t)
        @inbounds for i in 2:length(c)
            acc *= _eval_node(c[i], u, p, t)
        end
        return acc
    elseif op === :-
        if length(c) == 1
            return -_eval_node(c[1], u, p, t)
        elseif length(c) == 2
            return _eval_node(c[1], u, p, t) - _eval_node(c[2], u, p, t)
        end
        throw(TreeWalkError("E_TREEWALK_ARITY", "- expects 1 or 2 args"))
    elseif op === :neg
        # Canonical-form unary negation. `canonicalize` rewrites unary
        # `-x` to `neg(x)`, so any AST that has been through `discretize`
        # may carry `neg` ops where the source had `-x`.
        _expect_arity_n(op, c, 1)
        return -_eval_node(c[1], u, p, t)
    elseif op === :/
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) / _eval_node(c[2], u, p, t)
    elseif op === :^ || op === :pow
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) ^ _eval_node(c[2], u, p, t)

    # Comparisons → 1.0/0.0 (match `evaluate` semantics)
    elseif op === :<
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) <  _eval_node(c[2], u, p, t) ? 1.0 : 0.0
    elseif op === Symbol("<=")
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) <= _eval_node(c[2], u, p, t) ? 1.0 : 0.0
    elseif op === :>
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) >  _eval_node(c[2], u, p, t) ? 1.0 : 0.0
    elseif op === Symbol(">=")
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) >= _eval_node(c[2], u, p, t) ? 1.0 : 0.0
    elseif op === Symbol("==")
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) == _eval_node(c[2], u, p, t) ? 1.0 : 0.0
    elseif op === Symbol("!=")
        _expect_arity_n(op, c, 2)
        return _eval_node(c[1], u, p, t) != _eval_node(c[2], u, p, t) ? 1.0 : 0.0

    # Logical
    elseif op === :and
        for child in c
            _eval_node(child, u, p, t) == 0 && return 0.0
        end
        return 1.0
    elseif op === :or
        for child in c
            _eval_node(child, u, p, t) != 0 && return 1.0
        end
        return 0.0
    elseif op === :not
        _expect_arity_n(op, c, 1)
        return _eval_node(c[1], u, p, t) == 0 ? 1.0 : 0.0

    elseif op === :ifelse
        _expect_arity_n(op, c, 3)
        return _eval_node(c[1], u, p, t) != 0 ?
               _eval_node(c[2], u, p, t) :
               _eval_node(c[3], u, p, t)

    # Elementary functions
    elseif op === :sin;   _expect_arity_n(op, c, 1); return sin(_eval_node(c[1], u, p, t))
    elseif op === :cos;   _expect_arity_n(op, c, 1); return cos(_eval_node(c[1], u, p, t))
    elseif op === :tan;   _expect_arity_n(op, c, 1); return tan(_eval_node(c[1], u, p, t))
    elseif op === :asin;  _expect_arity_n(op, c, 1); return asin(_eval_node(c[1], u, p, t))
    elseif op === :acos;  _expect_arity_n(op, c, 1); return acos(_eval_node(c[1], u, p, t))
    elseif op === :atan
        if length(c) == 1
            return atan(_eval_node(c[1], u, p, t))
        elseif length(c) == 2
            return atan(_eval_node(c[1], u, p, t), _eval_node(c[2], u, p, t))
        end
        throw(TreeWalkError("E_TREEWALK_ARITY", "atan expects 1 or 2 args"))
    elseif op === :atan2
        _expect_arity_n(op, c, 2)
        return atan(_eval_node(c[1], u, p, t), _eval_node(c[2], u, p, t))
    elseif op === :exp;   _expect_arity_n(op, c, 1); return exp(_eval_node(c[1], u, p, t))
    elseif op === :log;   _expect_arity_n(op, c, 1); return log(_eval_node(c[1], u, p, t))
    elseif op === :log10; _expect_arity_n(op, c, 1); return log10(_eval_node(c[1], u, p, t))
    elseif op === :sqrt;  _expect_arity_n(op, c, 1); return sqrt(_eval_node(c[1], u, p, t))
    elseif op === :abs;   _expect_arity_n(op, c, 1); return abs(_eval_node(c[1], u, p, t))
    elseif op === :sign;  _expect_arity_n(op, c, 1); return sign(_eval_node(c[1], u, p, t))
    elseif op === :floor; _expect_arity_n(op, c, 1); return floor(_eval_node(c[1], u, p, t))
    elseif op === :ceil;  _expect_arity_n(op, c, 1); return ceil(_eval_node(c[1], u, p, t))
    elseif op === :min
        # n-ary min (esm-spec §4.2 — arity ≥ 2)
        length(c) < 2 && throw(TreeWalkError("E_TREEWALK_ARITY", "min needs ≥2 args"))
        acc = _eval_node(c[1], u, p, t)
        @inbounds for i in 2:length(c); acc = min(acc, _eval_node(c[i], u, p, t)); end
        return acc
    elseif op === :max
        # n-ary max (esm-spec §4.2 — arity ≥ 2)
        length(c) < 2 && throw(TreeWalkError("E_TREEWALK_ARITY", "max needs ≥2 args"))
        acc = _eval_node(c[1], u, p, t)
        @inbounds for i in 2:length(c); acc = max(acc, _eval_node(c[i], u, p, t)); end
        return acc

    elseif op === :pi || op === :π
        return Float64(pi)
    elseif op === :e
        return Float64(ℯ)

    elseif op === :Pre
        _expect_arity_n(op, c, 1)
        return _eval_node(c[1], u, p, t)

    elseif op === :fn
        # `n.handler` is `(fname::String, const_args_or_nothing)`. The
        # tuple's second slot is `nothing` for closed functions whose args
        # are all scalar (e.g. `datetime.*`). For closed functions with
        # const-array args (`interp.searchsorted`, `interp.linear`,
        # `interp.bilinear`) it is a `Vector{Any}` carrying the pre-extracted
        # arrays in spec arg-position order; the remaining scalar args are
        # the node's children, also in spec order.
        fname, const_args = n.handler::Tuple{String,Any}
        if const_args === nothing
            args_evaluated = Any[_eval_node(ci, u, p, t) for ci in c]
            return Float64(evaluate_closed_function(fname, args_evaluated))
        elseif fname == "interp.searchsorted"
            # Spec arg order: (x, xs); xs is const, x is the only child.
            x = _eval_node(c[1], u, p, t)
            return Float64(evaluate_closed_function(fname, Any[x, const_args[1]]))
        elseif fname == "interp.linear"
            # Spec arg order: (table, axis, x); table & axis are const; x is the only child.
            x = _eval_node(c[1], u, p, t)
            return Float64(evaluate_closed_function(fname,
                Any[const_args[1], const_args[2], x]))
        elseif fname == "interp.bilinear"
            # Spec arg order: (table, axis_x, axis_y, x, y); first three are
            # const; x and y are children in order.
            x = _eval_node(c[1], u, p, t)
            y = _eval_node(c[2], u, p, t)
            return Float64(evaluate_closed_function(fname,
                Any[const_args[1], const_args[2], const_args[3], x, y]))
        end

    else
        throw(TreeWalkError("E_TREEWALK_UNSUPPORTED_OP", String(op)))
    end
end

@inline function _require_const_array(arg, fname::String, arg_label::String)
    if arg isa OpExpr && arg.op == "const" && arg.value isa AbstractVector
        return arg.value
    end
    throw(TreeWalkError("E_TREEWALK_FN_ARG_NOT_CONST",
        "$(fname): `$(arg_label)` argument must be a `const`-op array node"))
end

@inline function _expect_arity_n(op::Symbol, c::Vector{_Node}, n::Int)
    length(c) == n ||
        throw(TreeWalkError("E_TREEWALK_ARITY",
                            "$op expects $n args, got $(length(c))"))
    return nothing
end

# Inner closure generator — separated so the closure's body is small
# enough to stay inferable. `rhs_list` is captured by the closure;
# Julia specializes the generated method to the captured types.
function _make_rhs(rhs_list::Vector{Tuple{Int,_Node}})
    function f!(du, u, p, t)
        @inbounds for k in 1:length(rhs_list)
            idx_and_node = rhs_list[k]
            du[idx_and_node[1]] = _eval_node(idx_and_node[2], u, p, t)
        end
        return nothing
    end
    return f!
end

# ============================================================
# 5. Misc helpers
# ============================================================

function _is_time_derivative_lhs(lhs)
    return isa(lhs, OpExpr) && lhs.op == "D" && lhs.wrt == "t" &&
           length(lhs.args) == 1
end

function _equation_tag(eq::Equation)
    if eq._comment !== nothing
        return eq._comment
    end
    return string(typeof(eq.lhs))
end

# Variable substitution that preserves every OpExpr field — the
# package-level `substitute` only carries `wrt`/`dim` and drops
# `handler_id`, `fn`, etc., which would corrupt `call`/`broadcast`
# nodes on their way through. Scoped here because this module is the
# only caller that needs the full preservation.
function _sub_preserving(expr::NumExpr, bindings::Dict{String,Expr})
    return expr
end
function _sub_preserving(expr::IntExpr, bindings::Dict{String,Expr})
    return expr
end
function _sub_preserving(expr::VarExpr, bindings::Dict{String,Expr})
    return get(bindings, expr.name, expr)
end
function _sub_preserving(expr::OpExpr, bindings::Dict{String,Expr})
    new_args = Expr[_sub_preserving(a, bindings) for a in expr.args]
    new_body = expr.expr_body === nothing ?
               nothing : _sub_preserving(expr.expr_body, bindings)
    new_values = expr.values === nothing ?
                 nothing : Expr[_sub_preserving(v, bindings) for v in expr.values]
    return OpExpr(expr.op, new_args;
                  wrt=expr.wrt, dim=expr.dim,
                  output_idx=expr.output_idx, expr_body=new_body,
                  reduce=expr.reduce, ranges=expr.ranges,
                  regions=expr.regions, values=new_values,
                  shape=expr.shape, perm=expr.perm, axis=expr.axis,
                  fn=expr.fn, name=expr.name, value=expr.value)
end

# Resolve observed-into-observed substitutions to a fixed point. After
# this runs, no RHS in the returned dict contains another observed
# variable as a free variable — so inlining observed names into a
# model equation is a single `_sub_preserving` call. Iteration cap =
# depth of the longest valid chain; exceeding it means there's a cycle.
function _resolve_observed(obs::Dict{String,Expr})
    resolved = Dict{String,Expr}()
    for (k, v) in obs
        resolved[k] = v
    end
    names = Set(keys(obs))
    # Max chain depth before we call it a cycle. One pass per observer
    # is always enough to collapse any acyclic chain.
    for _ in 1:(length(obs) + 1)
        any_change = false
        for (k, v) in resolved
            fv = free_variables(v)
            if any(n -> n in names, fv)
                resolved[k] = _sub_preserving(v, resolved)
                any_change = true
            end
        end
        any_change || return resolved
    end
    throw(TreeWalkError("E_TREEWALK_OBSERVED_CYCLE",
                        join(sort(collect(keys(obs))), ",")))
end

function _pick_tspan(tspan, model::Model)
    tspan === nothing || return (Float64(tspan[1]), Float64(tspan[2]))
    if !isempty(model.tests)
        ts = model.tests[1].time_span
        return (Float64(ts.start), Float64(ts.stop))
    end
    return (0.0, 1.0)
end

function _select_model(file::EsmFile, name::Union{Nothing,AbstractString})
    file.models === nothing &&
        throw(TreeWalkError("E_TREEWALK_NO_MODEL", "EsmFile.models is nothing"))
    models = file.models
    if name !== nothing
        haskey(models, String(name)) ||
            throw(TreeWalkError("E_TREEWALK_NO_MODEL", String(name)))
        return models[String(name)]
    end
    length(models) == 1 ||
        throw(TreeWalkError("E_TREEWALK_AMBIGUOUS_MODEL",
                            "specify model_name; have: " *
                            join(collect(keys(models)), ", ")))
    return first(values(models))
end
