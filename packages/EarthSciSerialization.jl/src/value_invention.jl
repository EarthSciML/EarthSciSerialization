# ============================================================
# Build-time value-invention front-door
# (RFC semiring-faq-unified-ir §6.1 cadence-partition / §5.5 / §7.3)
# ============================================================
#
# Replaces the `E_TREEWALK_DERIVED_INDEX_SET` throw (tree_walk.jl). A
# `kind:"derived"` index set whose `from_faq` names a value-invention aggregate
# (skolem / distinct / rank) is materialised here, ONCE at setup, off the
# per-step hot path — the §6.1 CONST/DISCRETE materialisation point. The
# aggregate's keys are evaluated over the build-time const-array factors and run
# through the `Relational` engine (skolem / distinct / equijoin, §5.5
# determinism); the distinct set's cardinality is handed to the tree-walk
# index-set resolver as the dense extent `[1, n]` — exactly as
# `_materialize_geometry_rings` does for an `intersect_polygon` clip ring (§8.1),
# now generalised to the relational engine.
#
# The pass runs on the RAW JSON model document, not the typed `OpExpr` IR: the
# value-invention vocabulary (the aggregate `key`, the `distinct` flag) lives in
# fields the typed IR does not preserve (mirrors the `Cadence` module, which
# walks raw JSON for the same reason).

# Base variable name of a typed-IR LHS (`VarExpr` / `index` / `D`), used by
# build_evaluator to drop value-invention equations from the ODE.
function _vi_typed_lhs_base(expr)
    expr isa VarExpr && return expr.name
    if expr isa OpExpr && (expr.op == "index" || expr.op == "D")
        isempty(expr.args) || return _vi_typed_lhs_base(expr.args[1])
    end
    return nothing
end

# ---- Raw-node accessors ----------------------------------------------------

_vi_get(d, k, default=nothing) = isa(d, AbstractDict) ? get(d, k, default) : default

# The relational body ops that mark a value-invention output (excluded from the ODE).
const _VI_BODY_OPS = ("skolem", "rank", "distinct")

# Arg-witness reducer ops (RFC §5.7 rule 6): a build-time reduction over a
# contracted candidate range that emits the ARG — the witnessing index — rather
# than the reduced value. The nearest-generator INDEX assignment. NET-NEW: the
# closed semiring registry (§5.1) returns values and value-invention
# (distinct/skolem/rank) returns sets — NEITHER returns the arg. Materialised as
# an integer per-element buffer at CONST cadence, exactly like the `:map` skolem
# bin buffers.
const _VI_ARGWITNESS_OPS = ("argmin", "argmax")

"""
    _vi_node_kind(node) -> Symbol

Classify a raw aggregate node's value-invention role:

- `:producer` — `distinct:true` (an index-set-producing aggregate; materialises a
  derived index set via `from_faq`).
- `:map`      — a per-element map whose body is `skolem` (e.g.
  `src_bin[i] = skolem("bin", floor(...), floor(...))`): a value-invention buffer
  the producer's `join`/`key` references; materialised so the join can gate on it.
  Also a per-element map whose body is an arg-witness reducer (`argmin`/`argmax`,
  e.g. `assign[i] = argmin_g dist(point_i, gen_g)`): an integer assignment buffer
  emitted by the inner reduction (§5.7 rule 6).
- `:exclude`  — another value-invention output (e.g. a `rank` dense-id buffer like
  `edge_dense_id`) that is dropped from the ODE but needs no setup materialisation
  (nothing downstream of the front-door consumes its values in v1).
- `:none`     — an ordinary numeric aggregate.
"""
function _vi_node_kind(node)
    isa(node, AbstractDict) || return :none
    _vi_get(node, "op") == "aggregate" || return :none
    _vi_get(node, "distinct", false) === true && return :producer
    body = _vi_get(node, "expr")
    if isa(body, AbstractDict)
        bop = _vi_get(body, "op")
        (bop == "skolem" || bop in _VI_ARGWITNESS_OPS) && return :map
        bop in _VI_BODY_OPS && return :exclude
    end
    key = _vi_get(node, "key")
    isa(key, AbstractDict) && _vi_get(key, "op") == "skolem" && return :map
    return :none
end

# Base variable name written by a raw LHS node: `name`, `{op:index,args:[name,…]}`
# or `{op:D,args:[name,…]}`. Returns `nothing` for an unrecognised form.
function _vi_lhs_base(lhs)
    isa(lhs, AbstractString) && return lhs
    if isa(lhs, AbstractDict)
        op = _vi_get(lhs, "op")
        if op == "index" || op == "D"
            args = _vi_get(lhs, "args", Any[])
            !isempty(args) && return _vi_lhs_base(args[1])
        end
    end
    return nothing
end

# Every (lhs, rhs) value-expression pair in a raw model: the equation list plus
# the `expression` of each observed variable.
function _vi_model_assignments(model_json)
    out = Tuple{Any,Any}[]
    for eq in _vi_get(model_json, "equations", Any[])
        push!(out, (_vi_get(eq, "lhs"), _vi_get(eq, "rhs")))
    end
    for (vname, v) in _vi_get(model_json, "variables", Dict{String,Any}())
        expr = _vi_get(v, "expression")
        expr === nothing || push!(out, (vname, expr))
    end
    return out
end

"""
    _vi_detect(model_json) -> (has_vi, vi_var_names, maps, producers)

Scan a raw model for value-invention assignments. `vi_var_names` is the set of
LHS variables produced by skolem/distinct/rank (excluded from the ODE state, as
the geometry clip-ring vars are); `maps`/`producers` are `(lhs, node)` pairs to
materialise.
"""
function _vi_detect(model_json)
    vi_var_names = Set{String}()
    maps = Tuple{String,Any}[]
    producers = Tuple{String,Any}[]
    for (lhs, rhs) in _vi_model_assignments(model_json)
        kind = _vi_node_kind(rhs)
        kind == :none && continue
        base = _vi_lhs_base(lhs)
        base === nothing && continue
        push!(vi_var_names, base)   # every value-invention output leaves the ODE
        kind == :producer && push!(producers, (base, rhs))
        kind == :map && push!(maps, (base, rhs))
    end
    has_vi = !isempty(maps) || !isempty(producers)
    return (has_vi=has_vi, vi_var_names=vi_var_names, maps=maps, producers=producers)
end

# ---- Build-time evaluation context -----------------------------------------

struct _ViCtx
    const_arrays::Dict{String,Any}
    params::Dict{String,Float64}
    index_sets::Dict{String,Any}
    variables::Dict{String,Any}
    maps::Dict{String,Dict{Any,Any}}   # materialised map var → (output-index → value)
end

# Coerce a build-time numeric to an exact integer relational key component
# (CONFORMANCE_SPEC.md §5.5.1 rule 1: no floats in keys). A non-integral float is
# a misuse — fail loudly rather than emit a non-deterministic key.
function _vi_key_int(x)
    isa(x, Integer) && return Int(x)
    if isa(x, AbstractFloat)
        isinteger(x) || throw(TreeWalkError("E_TREEWALK_VI_FLOAT_KEY",
            "value-invention key component $(repr(x)) is not integer-valued; relational " *
            "keys must be integer / categorical IDs (CONFORMANCE_SPEC.md §5.5.1 rule 1)"))
        return Int(x)
    end
    throw(TreeWalkError("E_TREEWALK_VI_KEY", "non-numeric key component $(repr(x))"))
end

# Resolve a scalar parameter value (dx/dy/atol …) from overrides-or-default.
function _vi_param(ctx::_ViCtx, name::AbstractString)
    haskey(ctx.params, name) && return ctx.params[name]
    v = get(ctx.variables, name, nothing)
    if v !== nothing
        d = _vi_get(v, "default")
        d !== nothing && return Float64(d)
    end
    throw(TreeWalkError("E_TREEWALK_VI_PARAM",
        "value-invention scalar parameter '$name' has no override or default"))
end

# Evaluate a raw value-invention sub-expression. Returns an Int / Float64 / Bool
# / String tag / Tuple key, depending on the op.
function _vi_eval(node, ctx::_ViCtx, bindings::AbstractDict)
    if isa(node, Bool)
        return node
    elseif isa(node, Integer)
        return Int(node)
    elseif isa(node, Real)
        return Float64(node)
    elseif isa(node, AbstractString)
        haskey(bindings, node) && return bindings[node]   # bound range symbol
        haskey(ctx.const_arrays, node) && return node     # bare factor name (used by index)
        haskey(ctx.variables, node) && _vi_get(ctx.variables[node], "type") == "parameter" &&
            return _vi_param(ctx, node)                    # scalar parameter
        return node                                        # relation tag ("edge"/"bin"/"pair")
    elseif isa(node, AbstractDict)
        op = _vi_get(node, "op")
        args = _vi_get(node, "args", Any[])
        if op == "index"
            return _vi_index(node, ctx, bindings)
        elseif op == "skolem"
            return _vi_skolem(node, ctx, bindings)
        elseif op == "true"
            return true
        elseif op == "false"
            return false
        elseif op == "floor"
            return floor(Int, Float64(_vi_eval(args[1], ctx, bindings)))
        elseif op == "ceil"
            return ceil(Int, Float64(_vi_eval(args[1], ctx, bindings)))
        elseif op == "/"
            return Float64(_vi_eval(args[1], ctx, bindings)) / Float64(_vi_eval(args[2], ctx, bindings))
        elseif op == "*"
            return prod(Float64(_vi_eval(a, ctx, bindings)) for a in args)
        elseif op == "+"
            return sum(Float64(_vi_eval(a, ctx, bindings)) for a in args)
        elseif op == "-"
            return length(args) == 1 ? -Float64(_vi_eval(args[1], ctx, bindings)) :
                   Float64(_vi_eval(args[1], ctx, bindings)) - Float64(_vi_eval(args[2], ctx, bindings))
        elseif op in ("<", ">", "<=", ">=", "==", "!=")
            a = Float64(_vi_eval(args[1], ctx, bindings))
            b = Float64(_vi_eval(args[2], ctx, bindings))
            op == "<"  && return a < b
            op == ">"  && return a > b
            op == "<=" && return a <= b
            op == ">=" && return a >= b
            op == "==" && return a == b
            return a != b
        end
        throw(TreeWalkError("E_TREEWALK_VI_OP",
            "value-invention build-time evaluator does not support op '$op'"))
    end
    throw(TreeWalkError("E_TREEWALK_VI_NODE", "unevaluable value-invention node $(repr(node))"))
end

# index(factor, i, …): gather from a const-array factor (1-based). The factor is
# build-time data supplied in `const_arrays`.
function _vi_index(node, ctx::_ViCtx, bindings::AbstractDict)
    args = _vi_get(node, "args", Any[])
    name = args[1]
    isa(name, AbstractString) && haskey(ctx.const_arrays, name) ||
        throw(TreeWalkError("E_TREEWALK_VI_INDEX",
            "value-invention index target '$(repr(name))' must be a const-array factor"))
    arr = ctx.const_arrays[name]
    idxs = Tuple(Int(_vi_eval(a, ctx, bindings)) for a in args[2:end])
    # A factor carrying a declared per-dimension boundary policy resolves an
    # out-of-range gather declaratively (periodic-wrap / edge-extend), exactly
    # as the tree_walk const_array gather does (ess-gj4). Plain factors keep the
    # existing behavior, so genuine connectivity OOB still surfaces.
    if isa(arr, BoundedConstArray)
        ndims(arr) == length(idxs) ||
            throw(TreeWalkError("E_TREEWALK_CONSTARRAY_NDIM",
                "const array '$(name)' is $(ndims(arr))D but got $(length(idxs)) indices"))
        idxs = ntuple(d -> _resolve_const_index(arr, String(name), d, idxs[d], size(arr, d)),
                      length(idxs))
    end
    return arr[idxs...]
end

# skolem(tag?, c1, c2, …) → the canonical key tuple. A leading STRING literal is
# the relation tag (the "sort"/relation name) and is NOT part of the emitted key
# — this is what makes the materialised set byte-identical to the M3 determinism
# golden (edges `[[1,2],…]`, candidate pairs `(i,j)`), which carry no tag (the
# `Relational.skolem_edge` / projected-pair form). The remaining components are
# exact integer IDs (§5.5.1 rule 4). A single component degrades to a scalar key.
function _vi_skolem(node, ctx::_ViCtx, bindings::AbstractDict)
    comps = Any[_vi_eval(a, ctx, bindings) for a in _vi_get(node, "args", Any[])]
    if !isempty(comps) && isa(comps[1], AbstractString)
        comps = comps[2:end]   # strip the relation tag
    end
    key = Tuple(_vi_key_int(c) for c in comps)
    length(key) == 1 && return key[1]
    return key
end

# ---- Range resolution ------------------------------------------------------

# Order range symbols so a ragged range's `of` parents precede it (a stable
# topological order over the per-symbol `of` dependency).
function _vi_order_syms(ranges)
    syms = collect(keys(ranges))
    ordered = String[]
    remaining = copy(syms)
    while !isempty(remaining)
        progressed = false
        for s in copy(remaining)
            of = _vi_get(ranges[s], "of", Any[])
            if all(p -> p in ordered || !(p in syms), of)
                push!(ordered, s)
                deleteat!(remaining, findfirst(==(s), remaining))
                progressed = true
            end
        end
        progressed || throw(TreeWalkError("E_TREEWALK_VI_RANGE_CYCLE",
            "value-invention ranges have a cyclic `of` dependency: $(remaining)"))
    end
    return ordered
end

# The element values a range symbol binds to, given the current bindings.
# interval/categorical → 1-based positions; ragged → the MEMBER values gathered
# from the set's `values` factor sliced by its `offsets` factor (so a range
# symbol over `face_vertices` binds to the vertex IDs of the parent face, §5.2).
function _vi_range_values(spec, ctx::_ViCtx, bindings::AbstractDict)
    from = _vi_get(spec, "from")
    is = get(ctx.index_sets, from, nothing)
    is === nothing && throw(TreeWalkError("E_TREEWALK_VI_RANGE",
        "value-invention range references undeclared index set '$(repr(from))'"))
    kind = _vi_get(is, "kind")
    if kind == "interval"
        return collect(1:Int(_vi_get(is, "size")))
    elseif kind == "categorical"
        return collect(1:length(_vi_get(is, "members", Any[])))
    elseif kind == "ragged"
        of = _vi_get(spec, "of", Any[])
        isempty(of) && throw(TreeWalkError("E_TREEWALK_VI_RANGE",
            "ragged value-invention range '$(from)' needs an `of` parent"))
        parent = Int(bindings[of[1]])
        offs = ctx.const_arrays[_vi_get(is, "offsets")]
        vals = ctx.const_arrays[_vi_get(is, "values")]
        nmem = Int(offs[parent])
        return Any[_vi_key_int(vals[parent, l]) for l in 1:nmem]
    end
    throw(TreeWalkError("E_TREEWALK_VI_RANGE",
        "value-invention range over index set kind '$(repr(kind))' is unsupported"))
end

# Enumerate every full binding of an aggregate's `ranges`, calling `cb(bindings)`
# at each leaf (bindings is reused — copy if retained).
function _vi_enumerate(ranges, ctx::_ViCtx, cb)
    syms = _vi_order_syms(ranges)
    bindings = Dict{String,Any}()
    function rec(k)
        if k > length(syms)
            cb(bindings)
            return
        end
        s = syms[k]
        for v in _vi_range_values(ranges[s], ctx, bindings)
            bindings[s] = v
            rec(k + 1)
        end
        delete!(bindings, s)
    end
    rec(1)
    return
end

# ---- Materialisation -------------------------------------------------------

# The index range symbol of a join-key variable within the producer's ranges:
# the producer range whose `from` equals the variable's (1-D) shape index set.
function _vi_join_index_sym(vname, producer_ranges, ctx::_ViCtx)
    v = get(ctx.variables, vname, nothing)
    v === nothing && throw(TreeWalkError("E_TREEWALK_VI_JOIN",
        "join references unknown variable '$(vname)'"))
    shape = _vi_get(v, "shape", Any[])
    length(shape) == 1 || throw(TreeWalkError("E_TREEWALK_VI_JOIN",
        "value-invention join key '$(vname)' must be a 1-D buffer; shape=$(shape)"))
    target = shape[1]
    for (sym, spec) in producer_ranges
        _vi_get(spec, "from") == target && return sym
    end
    throw(TreeWalkError("E_TREEWALK_VI_JOIN",
        "no producer range binds the index set '$(target)' of join key '$(vname)'"))
end

# True iff every `join.on` key-column pair compares equal at this binding (the
# value-equality equi-join gate, §5.3); each key is a materialised map buffer.
function _vi_join_ok(join, producer_ranges, ctx::_ViCtx, bindings::AbstractDict)
    for clause in join
        for pair in _vi_get(clause, "on", Any[])
            lname, rname = pair[1], pair[2]
            ls = _vi_join_index_sym(lname, producer_ranges, ctx)
            rs = _vi_join_index_sym(rname, producer_ranges, ctx)
            lval = ctx.maps[lname][bindings[ls]]
            rval = ctx.maps[rname][bindings[rs]]
            lval == rval || return false
        end
    end
    return true
end

# Arg-witness reducer (RFC §5.7 rule 6). Over the inner contracted `ranges`
# (which EXTEND the outer map binding so `value` may read both the point and the
# candidate), evaluate the scalar `value` body at each candidate and return the
# `arg` index symbol's value at the optimum — `argmin` keeps the least value,
# `argmax` the greatest. The NORMATIVE tie-break is the SMALLEST arg (the
# smallest generator ID): equal values resolve to the lower candidate index, so
# the emitted integer buffer is byte-identical across bindings irrespective of
# enumeration order (the §5.7 byte-identical-determinism contract — this op's
# analogue of the `distinct` sorted-order / `rank` numbering rules). An optional
# `join` (a bin-Skolem broad-phase prune, §5.3) and/or `filter` restrict the
# candidate set; an empty candidate set is an error (no index witnesses an empty
# argmin — a point with no candidate generator is undefined).
function _vi_argreduce(node, ctx::_ViCtx, outer_bindings::AbstractDict, outer_ranges)
    op = _vi_get(node, "op")
    inner_ranges = _vi_get(node, "ranges", Dict{String,Any}())
    arg_sym = _vi_get(node, "arg")
    arg_sym === nothing && throw(TreeWalkError("E_TREEWALK_VI_ARG",
        "arg-witness op '$op' requires an `arg` naming the witnessing index symbol"))
    arg_sym = String(arg_sym)
    value_expr = _vi_get(node, "expr")
    value_expr === nothing && throw(TreeWalkError("E_TREEWALK_VI_ARG",
        "arg-witness op '$op' requires an `expr` body (the scalar to optimise)"))
    haskey(inner_ranges, arg_sym) || throw(TreeWalkError("E_TREEWALK_VI_ARG",
        "arg-witness `arg`='$arg_sym' must name one of the contracted `ranges` symbols"))
    haskey(outer_bindings, arg_sym) && throw(TreeWalkError("E_TREEWALK_VI_ARG",
        "arg-witness `arg`='$arg_sym' shadows an outer index symbol"))
    filt = _vi_get(node, "filter")
    join = _vi_get(node, "join")
    # Combined ranges so a `join` column over an OUTER-indexed map buffer (the
    # point's bin) resolves alongside the inner candidate's bin (§5.3 equi-join).
    # `Base.merge` — the module shadows `merge` with an `EsmFile` method.
    combined = Base.merge(Dict{String,Any}(outer_ranges), Dict{String,Any}(inner_ranges))
    syms = _vi_order_syms(inner_ranges)
    bindings = Dict{String,Any}(outer_bindings)
    best_val = nothing
    best_arg = nothing
    function rec(k)
        if k > length(syms)
            if filt !== nothing
                fv = _vi_eval(filt, ctx, bindings)
                (fv === true || (isa(fv, Real) && fv > 0)) || return
            end
            if join !== nothing && !_vi_join_ok(join, combined, ctx, bindings)
                return
            end
            v = Float64(_vi_eval(value_expr, ctx, bindings))
            a = _vi_key_int(bindings[arg_sym])
            if best_arg === nothing
                best_val = v; best_arg = a
            else
                better = op == "argmax" ? (v > best_val) : (v < best_val)
                # Strict improvement OR an exact tie resolved to the smaller arg.
                if better || (v == best_val && a < best_arg)
                    best_val = v; best_arg = a
                end
            end
            return
        end
        s = syms[k]
        for val in _vi_range_values(inner_ranges[s], ctx, bindings)
            bindings[s] = val
            rec(k + 1)
        end
        delete!(bindings, s)
    end
    rec(1)
    best_arg === nothing && throw(TreeWalkError("E_TREEWALK_VI_ARGEMPTY",
        "arg-witness op '$op' has an empty candidate set; no index witnesses the " *
        "optimum (a point with no candidate generator is undefined)"))
    return best_arg
end

# Materialise a per-element value-invention map var → Dict(output-index → value).
function _vi_materialize_map!(ctx::_ViCtx, vname::AbstractString, node)
    output_idx = _vi_get(node, "output_idx", Any[])
    length(output_idx) == 1 || throw(TreeWalkError("E_TREEWALK_VI_MAP",
        "value-invention map '$(vname)' must have a single output index; got $(output_idx)"))
    body = _vi_get(node, "expr")
    body === nothing && throw(TreeWalkError("E_TREEWALK_VI_MAP",
        "value-invention map '$(vname)' has no `expr` body"))
    outer_ranges = _vi_get(node, "ranges", Dict{String,Any}())
    is_arg = isa(body, AbstractDict) && _vi_get(body, "op") in _VI_ARGWITNESS_OPS
    out = Dict{Any,Any}()
    sym = String(output_idx[1])
    _vi_enumerate(outer_ranges, ctx, bindings -> begin
        # An arg-witness body runs the inner reduction (with the outer point bound)
        # and emits the witnessing INDEX; an ordinary body (skolem) emits its value.
        out[bindings[sym]] = is_arg ? _vi_argreduce(body, ctx, bindings, outer_ranges) :
                                      _vi_eval(body, ctx, bindings)
    end)
    ctx.maps[vname] = out
    return out
end

# Materialise an index-set-producing aggregate → the distinct member set (§5.5
# sorted total order, via the Relational engine). Returns the member vector.
function _vi_materialize_producer(ctx::_ViCtx, node)
    key = _vi_get(node, "key")
    key === nothing && throw(TreeWalkError("E_TREEWALK_VI_PRODUCER",
        "value-invention producer aggregate requires a `key` (§5.5)"))
    ranges = _vi_get(node, "ranges", Dict{String,Any}())
    filt = _vi_get(node, "filter")
    join = _vi_get(node, "join")
    members = Any[]
    _vi_enumerate(ranges, ctx, bindings -> begin
        if filt !== nothing
            fv = _vi_eval(filt, ctx, bindings)
            (fv === true || (isa(fv, Real) && fv > 0)) || return
        end
        if join !== nothing && !_vi_join_ok(join, ranges, ctx, bindings)
            return
        end
        push!(members, _vi_skolem(key, ctx, bindings))
    end)
    return Relational.distinct(members)
end

# A model copy whose value-invention MAP vars are re-typed to their body's
# cadence class (`const`→parameter, `discrete`→discrete), so a producer joining
# on a map buffer classifies by the buffer's true (input-derived) cadence rather
# than the seed of its declared `state` kind (§6.1). A `continuous` body is left
# unchanged so the §5.7 guard still rejects state-dependent topology.
function _vi_classification_model(model_json, maps)
    isempty(maps) && return model_json
    native = Cadence.to_native(model_json)
    vars = Dict{String,Any}(get(native, "variables", Dict{String,Any}()))
    for (vname, node) in maps
        haskey(vars, vname) || continue
        body = _vi_get(node, "expr")
        body === nothing && continue
        bcls = Cadence.classify(body, native)
        newtype = bcls == "const" ? "parameter" : bcls == "discrete" ? "discrete" : nothing
        newtype === nothing && continue
        v = Dict{String,Any}(vars[vname]); v["type"] = newtype; vars[vname] = v
    end
    out = Dict{String,Any}(native); out["variables"] = vars
    return out
end

"""
    materialize_value_invention(model_json, const_arrays, params) -> NamedTuple

Run the build-time value-invention engine over a raw model document. Returns:

- `extents::Dict{String,Int}` — `from_faq` producer id → derived index-set
  cardinality (the dense extent `[1, n]` the tree-walk resolver consumes).
- `members::Dict{String,Vector}` — `from_faq` producer id → the distinct member
  tuples in §5.5.1 sorted order (for byte-identity assertions).
- `assignments::Dict{String,Vector{Int}}` — arg-witness map var → the integer
  nearest-generator INDEX buffer, dense in output-index order (the SCVT
  assignment; §5.7 rule 6, byte-identical across bindings).
- `vi_var_names::Set{String}` — value-invention LHS vars to drop from the ODE.
- `maps::Dict{String,Dict}` — materialised per-element map buffer (e.g. `src_bin`)
  → (1-based output position → bin-key value). A downstream FAQ's
  `join.on [[src_bin, tgt_bin]]` gates on these buffers (§5.3): the broad-phase
  bin key is data-derived, so it cannot be a categorical index-set member — the
  tree-walk join resolver reads the key value per position from here.
- `map_sets::Dict{String,String}` — map buffer → its 1-D shape index-set name,
  so the join resolver can find the range symbol the buffer is indexed by.

`const_arrays` supplies the build-time factor arrays (the connectivity / coords
the keys are computed from); `params` supplies scalar parameter overrides. A
producer (or arg-witness assignment) that classifies CONTINUOUS is rejected
(§5.7 guard 2).
"""
function materialize_value_invention(model_json, const_arrays::AbstractDict,
                                     params::AbstractDict)
    det = _vi_detect(model_json)
    extents = Dict{String,Int}()
    members = Dict{String,Vector{Any}}()
    assignments = Dict{String,Vector{Int}}()
    map_sets = Dict{String,String}()
    det.has_vi || return (extents=extents, members=members, assignments=assignments,
                          vi_var_names=det.vi_var_names,
                          maps=Dict{String,Dict{Any,Any}}(), map_sets=map_sets)

    ctx = _ViCtx(
        Dict{String,Any}(String(k) => v for (k, v) in const_arrays),
        Dict{String,Float64}(String(k) => Float64(v) for (k, v) in params),
        Dict{String,Any}(Cadence.to_native(_vi_get(model_json, "index_sets", Dict{String,Any}()))),
        Dict{String,Any}(Cadence.to_native(_vi_get(model_json, "variables", Dict{String,Any}()))),
        Dict{String,Dict{Any,Any}}())

    # Cadence classification model: a value-invention MAP output (e.g. `src_bin`)
    # is a setup-materialized buffer, so its cadence is `class(its definition)` per
    # §6.1 (max over inputs) — NOT the seed of its declared `state`/`discrete`
    # kind. Re-type each map var to its body's class so the §5.7 guard 2 below
    # classifies a producer/arg-witness that joins on it correctly (a CONST-derived
    # bin map passes; a genuinely state-dependent one still classifies CONTINUOUS →
    # reject). It depends only on the model structure, so it is built before
    # materialisation.
    cls_model = _vi_classification_model(model_json, det.maps)

    # §5.7 guard 2 for arg-witness assignments: a state-dependent nearest-generator
    # buffer (continuous cadence) may not be materialised at build time — its
    # topology would change every step (out of scope for v1, like a continuous
    # `distinct`). The Lloyd/SCVT outer loop re-invokes the build with updated
    # generators; within one build the assignment is CONST/DISCRETE.
    for (vname, node) in det.maps
        body = _vi_get(node, "expr")
        (isa(body, AbstractDict) && _vi_get(body, "op") in _VI_ARGWITNESS_OPS) || continue
        Cadence.classify(node, cls_model) == "continuous" && throw(TreeWalkError(
            "E_TREEWALK_VI_CONTINUOUS",
            "arg-witness map '$vname' classifies CONTINUOUS — a build-time assignment " *
            "buffer's inputs must be CONST/DISCRETE (RFC §5.7 guard 2)"))
    end

    # Maps first (a producer's join/key — or an arg-witness `join` — may reference them).
    for (vname, node) in det.maps
        _vi_materialize_map!(ctx, vname, node)
        # Record the buffer's 1-D shape index set so a downstream FAQ's
        # `join.on [[vname, …]]` can find the range symbol it is indexed by.
        v = get(ctx.variables, vname, nothing)
        v === nothing && continue
        shape = _vi_get(v, "shape", Any[])
        length(shape) == 1 && (map_sets[vname] = String(shape[1]))
    end

    # Surface the arg-witness buffers (the integer nearest-generator INDEX
    # assignment), dense in output-index order, for byte-identity assertions and
    # the downstream grouped reduction the SCVT step consumes.
    for (vname, node) in det.maps
        body = _vi_get(node, "expr")
        (isa(body, AbstractDict) && _vi_get(body, "op") in _VI_ARGWITNESS_OPS) || continue
        m = ctx.maps[vname]
        assignments[vname] = Int[Int(m[k]) for k in sort!(collect(keys(m)))]
    end

    # `from_faq` id → derived index-set name (so we only materialise producers a
    # derived set actually names; geometry producers are handled elsewhere).
    faq_to_set = Dict{String,String}()
    for (sname, is) in ctx.index_sets
        _vi_get(is, "kind") == "derived" || continue
        faq = _vi_get(is, "from_faq")
        faq === nothing || (faq_to_set[String(faq)] = String(sname))
    end

    for (_, node) in det.producers
        id = _vi_get(node, "id")
        id === nothing && throw(TreeWalkError("E_TREEWALK_VI_PRODUCER",
            "value-invention producer aggregate requires an `id` naming it for `from_faq`"))
        id = String(id)
        haskey(faq_to_set, id) || continue   # no derived set names this producer
        # §5.7 guard 2: a relational node may not run on the hot path.
        cls = Cadence.classify(node, cls_model)
        cls == "continuous" && throw(TreeWalkError("E_TREEWALK_VI_CONTINUOUS",
            "value-invention producer '$id' classifies CONTINUOUS — it may not run per " *
            "step (RFC §5.7 guard 2); its inputs must be CONST/DISCRETE"))
        mem = _vi_materialize_producer(ctx, node)
        members[id] = mem
        extents[id] = length(mem)
    end

    return (extents=extents, members=members, assignments=assignments,
            vi_var_names=det.vi_var_names, maps=ctx.maps, map_sets=map_sets)
end
