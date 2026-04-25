# Rule engine per discretization RFC §5.2.
#
# Pattern-match rewriting over the expression AST with typed pattern
# variables, guards, non-linear matching (via canonical equality), and a
# top-down fixed-point loop with per-pass sealing of rewritten subtrees.
#
# This module implements the core infrastructure required by RFC §13.1
# Step 1: load rules, apply them to expressions, produce canonicalized
# output. Scheme expansion (the `use:` rule form, §7.2.1) is NOT
# implemented here — only the `replacement` form is — and is tracked as
# follow-up work for Step 1b.

"""
    RuleEngineError(code::String, message::String)

Error raised by the rule engine. The `code` field carries one of the
RFC §5.2 / §11 stable error codes:

- `E_RULES_NOT_CONVERGED` — fixed-point loop exceeded `max_passes`.
- `E_UNREWRITTEN_PDE_OP` — a PDE op (`grad`, `div`, `laplacian`, `D`, `bc`)
  remained after rewriting on an equation not annotated `passthrough: true`.
- `E_SCHEME_MISMATCH` — rule/scheme `applies_to` disagreement (reserved for
  the `use:` rule form; not emitted in the MVP).
"""
struct RuleEngineError <: Exception
    code::String
    message::String
end

Base.showerror(io::IO, e::RuleEngineError) =
    print(io, "RuleEngineError(", e.code, "): ", e.message)

"""
    Guard(name::String, params::Dict{String,Any})

A single constraint on pattern-variable bindings. `name` is one of the
§5.2.4 closed-set guard names; `params` carries the fields from the JSON
guard object (`pvar`, `grid`, `location`, `rank`, …).
"""
struct Guard
    name::String
    params::Dict{String,Any}
end

"""
    RuleRegion

Spatial scope of a rule (RFC §5.2.7). Abstract type with four concrete
variants:

- [`RegionBoundary`](@ref) — `{kind:"boundary", side}`
- [`RegionPanelBoundary`](@ref) — `{kind:"panel_boundary", panel, side}`
- [`RegionMaskField`](@ref) — `{kind:"mask_field", field}`
- [`RegionIndexRange`](@ref) — `{kind:"index_range", axis, lo, hi}`

The legacy advisory string form is stored as a plain `String` on the
enclosing [`Rule`](@ref) and does not use this type.
"""
abstract type RuleRegion end

"""
    RegionBoundary(side::String)

`{kind:"boundary", side}` scope (RFC §5.2.7).
"""
struct RegionBoundary <: RuleRegion
    side::String
end

"""
    RegionPanelBoundary(panel::Int, side::String)

`{kind:"panel_boundary", panel, side}` scope (cubed_sphere only).
"""
struct RegionPanelBoundary <: RuleRegion
    panel::Int
    side::String
end

"""
    RegionMaskField(field::String)

`{kind:"mask_field", field}` scope. `field` names a boolean-valued mask
resolved at rewrite time against [`RuleContext.mask_fields`](@ref
RuleContext). The scope fires at a given query point iff
`ctx.mask_fields[field]` contains a truthy entry for that point.
"""
struct RegionMaskField <: RuleRegion
    field::String
end

"""
    RegionIndexRange(axis::String, lo::Int, hi::Int)

`{kind:"index_range", axis, lo, hi}` scope (inclusive bounds).
"""
struct RegionIndexRange <: RuleRegion
    axis::String
    lo::Int
    hi::Int
end

"""
    Rule(name, pattern, where, replacement, region, where_expr)

A rewrite rule. `pattern` is an AST with `\$`-prefixed pattern variables;
`where` is a vector of [`Guard`](@ref) constraints applied at rule-
selection time; `replacement` is an AST over the pattern variables. The
MVP supports only the inline `replacement` form; `use:<scheme>` is
reserved for Step 1b.

`region` is the rule's spatial scope (RFC §5.2.7). It may be
`nothing`, a `String` (legacy advisory tag — no runtime effect), or a
concrete [`RuleRegion`](@ref) object (normative per-point scope).

`where_expr` is an optional per-query-point boolean predicate AST
(RFC §5.2.7). Mutually exclusive at the author level with guard-list
`where`; structurally distinguished by JSON shape at parse time.
"""
struct Rule
    name::String
    pattern::Expr
    where::Vector{Guard}
    replacement::Expr
    region::Union{String,RuleRegion,Nothing}
    where_expr::Union{Expr,Nothing}
end

Rule(name::String, pattern::Expr, replacement::Expr;
     where::Vector{Guard}=Guard[],
     region::Union{String,RuleRegion,Nothing}=nothing,
     where_expr::Union{Expr,Nothing}=nothing) =
    Rule(name, pattern, where, replacement, region, where_expr)

# Backward-compatible 5-arg positional constructor (pre-§5.2.7 callers).
Rule(name::String, pattern::Expr, where::Vector{Guard}, replacement::Expr,
     region::Union{String,RuleRegion,Nothing}) =
    Rule(name, pattern, where, replacement, region, nothing)

# ============================================================================
# Pattern variable detection
# ============================================================================

_is_pvar_string(s::AbstractString) = length(s) >= 2 && first(s) == '$'
_is_pvar_string(::Any) = false

_is_pvar(e::VarExpr) = _is_pvar_string(e.name)
_is_pvar(::Any) = false

# ============================================================================
# Match — returns Dict of bindings or nothing
# ============================================================================

"""
    match_pattern(pattern::Expr, expr::Expr) -> Union{Dict{String,Expr}, Nothing}

Attempt to match `pattern` against `expr`. On success, returns a
substitution mapping each pattern-variable name (including the leading
`\$`) to the AST or bare name it binds. Bare-name bindings (for sibling
fields like `wrt`, `dim`) are wrapped as [`VarExpr`](@ref) so the
substitution has a uniform type. On failure, returns `nothing`.

Non-linear patterns (§5.2.2): a pattern variable that appears in
multiple positions must bind to canonically-equal values at every
occurrence.
"""
function match_pattern(pattern::Expr, expr::Expr)::Union{Dict{String,Expr},Nothing}
    return _match(pattern, expr, Dict{String,Expr}())
end

function _match(pat::Expr, expr::Expr, b::Dict{String,Expr})
    # Pattern variable in an Expression position (subtree class).
    if pat isa VarExpr && _is_pvar(pat)
        return _unify(pat.name, expr, b)
    end
    if pat isa IntExpr
        return (expr isa IntExpr && expr.value == pat.value) ? b : nothing
    end
    if pat isa NumExpr
        return (expr isa NumExpr && expr.value == pat.value) ? b : nothing
    end
    if pat isa VarExpr
        return (expr isa VarExpr && expr.name == pat.name) ? b : nothing
    end
    if pat isa OpExpr
        expr isa OpExpr || return nothing
        pat.op == expr.op || return nothing
        length(pat.args) == length(expr.args) || return nothing
        b = _match_sibling_name(pat.wrt, expr.wrt, b)
        b === nothing && return nothing
        b = _match_sibling_name(pat.dim, expr.dim, b)
        b === nothing && return nothing
        for (pa, ea) in zip(pat.args, expr.args)
            b = _match(pa, ea, b)
            b === nothing && return nothing
        end
        return b
    end
    return nothing
end

function _match_sibling_name(pat::Union{String,Nothing}, val::Union{String,Nothing},
                             b::Dict{String,Expr})
    if pat === nothing
        return val === nothing ? b : nothing
    end
    if _is_pvar_string(pat)
        val === nothing && return nothing
        return _unify(pat, VarExpr(val::String), b)
    end
    return (val !== nothing && val == pat) ? b : nothing
end

function _unify(pname::AbstractString, candidate::Expr, b::Dict{String,Expr})
    name = String(pname)
    if haskey(b, name)
        # Non-linear: existing binding must match candidate (AST-equal after
        # canonicalization).
        try
            prev_json = canonical_json(b[name])
            new_json = canonical_json(candidate)
            return prev_json == new_json ? b : nothing
        catch
            # Canonicalization failure (e.g. NaN) aborts the match.
            return nothing
        end
    end
    nb = copy(b)
    nb[name] = candidate
    return nb
end

# ============================================================================
# Apply bindings — build the replacement AST
# ============================================================================

"""
    apply_bindings(template::Expr, bindings::Dict{String,Expr}) -> Expr

Substitute pattern variables in `template` with their bound values.
Throws [`RuleEngineError`](@ref) if `template` references a pattern
variable that is not in `bindings`.
"""
function apply_bindings(template::Expr, b::Dict{String,Expr})::Expr
    if template isa VarExpr && _is_pvar(template)
        haskey(b, template.name) || throw(RuleEngineError(
            "E_PATTERN_VAR_UNBOUND",
            "pattern variable $(template.name) is not bound"))
        return b[template.name]
    end
    if template isa OpExpr
        new_args = Expr[apply_bindings(a, b) for a in template.args]
        new_wrt = _apply_name_field(template.wrt, b)
        new_dim = _apply_name_field(template.dim, b)
        return OpExpr(template.op, new_args;
                      wrt=new_wrt, dim=new_dim,
                      output_idx=template.output_idx,
                      expr_body=template.expr_body,
                      reduce=template.reduce, ranges=template.ranges,
                      regions=template.regions, values=template.values,
                      shape=template.shape, perm=template.perm,
                      axis=template.axis, fn=template.fn,
                      handler_id=template.handler_id)
    end
    return template
end

function _apply_name_field(field::Union{String,Nothing}, b::Dict{String,Expr})
    field === nothing && return nothing
    if _is_pvar_string(field)
        haskey(b, field) || throw(RuleEngineError(
            "E_PATTERN_VAR_UNBOUND",
            "pattern variable $field is not bound"))
        v = b[field]
        v isa VarExpr || throw(RuleEngineError(
            "E_PATTERN_VAR_TYPE",
            "pattern variable $field used in name-class field must bind a bare name"))
        return v.name
    end
    return field
end

# ============================================================================
# Guards (§5.2.4)
# ============================================================================

"""
    RuleContext(grids, variables)

Context supplied to [`rewrite`](@ref) and guard evaluation. Holds the
grid metadata and variable table needed by the closed-set guards in
§5.2.4. Callers build this by projecting the relevant pieces of an
`EsmFile` model.

- `grids::Dict{String, Dict{String,Any}}`: per-grid metadata. Each entry
  may carry `"spatial_dims"` (Vector{String}), `"periodic_dims"`
  (Vector{String}), `"nonuniform_dims"` (Vector{String}).
- `variables::Dict{String, Dict{String,Any}}`: per-variable metadata.
  Each entry may carry `"grid"` (String), `"location"` (String),
  `"shape"` (Vector or Vector{String}).
- `mask_fields::Dict{String, Vector{Dict{String,Int}}}`: per-point
  boolean masks resolving [`RegionMaskField`](@ref) scope (RFC §5.2.7).
  Each entry is the list of query points at which the mask is truthy;
  the evaluator fires the rule iff `ctx.query_point` matches one of
  the listed points on all keys the mask entry declares. Production
  callers populate this by materializing the relevant `data_loaders`
  entry (or a boolean variable) at the current rewrite time; tests
  inject it directly.
"""
struct RuleContext
    grids::Dict{String,Dict{String,Any}}
    variables::Dict{String,Dict{String,Any}}
    query_point::Dict{String,Int}
    grid_name::Union{String,Nothing}
    mask_fields::Dict{String,Vector{Dict{String,Int}}}
end

RuleContext() = RuleContext(Dict{String,Dict{String,Any}}(),
                            Dict{String,Dict{String,Any}}(),
                            Dict{String,Int}(),
                            nothing,
                            Dict{String,Vector{Dict{String,Int}}}())

RuleContext(grids, variables) = RuleContext(grids, variables,
                                            Dict{String,Int}(), nothing,
                                            Dict{String,Vector{Dict{String,Int}}}())

# Backward-compatible 4-arg constructor (pre-mask_field callers).
RuleContext(grids::Dict{String,Dict{String,Any}},
            variables::Dict{String,Dict{String,Any}},
            query_point::Dict{String,Int},
            grid_name::Union{String,Nothing}) =
    RuleContext(grids, variables, query_point, grid_name,
                Dict{String,Vector{Dict{String,Int}}}())

"""
    with_query_point(ctx, point; grid=nothing) -> RuleContext

Return a copy of `ctx` with the given per-point index bindings (e.g.
`Dict("i"=>0, "j"=>3)`) installed, used to evaluate per-query-point
`region` / `where`-expression scopes per RFC §5.2.7. `grid`, when
supplied, names which grid entry in `ctx.grids` the point refers to —
used to resolve `region.boundary.side` against grid dim bounds.
"""
with_query_point(ctx::RuleContext, point::Dict{String,Int};
                 grid::Union{String,Nothing}=nothing) =
    RuleContext(ctx.grids, ctx.variables, point,
                grid === nothing ? ctx.grid_name : grid,
                ctx.mask_fields)

"""
    check_guards(guards, bindings, ctx) -> Union{Dict{String,Expr}, Nothing}

Evaluate the guard list left-to-right, threading bindings. Each guard
may read or extend the binding map; a guard whose pvar-valued `grid`
field is unbound at entry binds it to the variable's actual grid
(§9.2.1 example pattern). Returns the extended bindings on success,
`nothing` on any failure.
"""
function check_guards(guards::Vector{Guard}, bindings::Dict{String,Expr},
                      ctx::RuleContext)
    b = bindings
    for g in guards
        b = check_guard(g, b, ctx)
        b === nothing && return nothing
    end
    return b
end

"""
    check_guard(guard, bindings, ctx) -> Union{Dict{String,Expr}, Nothing}

Evaluate a single guard per §5.2.4. Returns an extended binding map on
success (possibly the same `bindings` if no new pvar was bound), or
`nothing` on failure.
"""
function check_guard(g::Guard, b::Dict{String,Expr}, ctx::RuleContext)
    if g.name == "var_has_grid"
        return _guard_var_has_grid(g, b, ctx)
    elseif g.name == "dim_is_spatial_dim_of"
        return _guard_dim_is_spatial_dim_of(g, b, ctx)
    elseif g.name == "dim_is_periodic"
        return _guard_dim_is_periodic(g, b, ctx)
    elseif g.name == "dim_is_nonuniform"
        return _guard_dim_is_nonuniform(g, b, ctx)
    elseif g.name == "var_location_is"
        return _guard_var_location_is(g, b, ctx)
    elseif g.name == "var_shape_rank"
        return _guard_var_shape_rank(g, b, ctx)
    end
    throw(RuleEngineError("E_UNKNOWN_GUARD",
        "unknown guard: $(g.name) (§5.2.4 closed set)"))
end

function _resolve_name(b::Dict{String,Expr}, key::String)::Union{String,Nothing}
    haskey(b, key) || return nothing
    v = b[key]
    return v isa VarExpr ? v.name : nothing
end

# Resolve a guard's field that may be a literal string or a pvar reference.
# If `field_val` is a pvar and the pvar is already bound, returns the bound
# name and `(b, false)` — no new binding. If unbound, returns
# `(nothing, true)` to indicate the caller should set it from context, and
# will bind via `_bind_pvar_name`. If `field_val` is a literal, returns
# `(field_val, false)`.
function _resolve_or_mark(g::Guard, b::Dict{String,Expr},
                          field::String)::Tuple{Union{String,Nothing},Bool,Union{String,Nothing}}
    v = get(g.params, field, nothing)
    v === nothing && return (nothing, false, nothing)
    s = String(v)
    if _is_pvar_string(s)
        bound = _resolve_name(b, s)
        return (bound, bound === nothing, s)
    end
    return (s, false, nothing)
end

function _bind_pvar_name(b::Dict{String,Expr}, pvar::String, name::String)
    nb = copy(b)
    nb[pvar] = VarExpr(name)
    return nb
end

function _guard_var_has_grid(g, b, ctx)
    pvar = String(g.params["pvar"])
    var_name = _resolve_name(b, pvar)
    var_name === nothing && return nothing
    meta = get(ctx.variables, var_name, nothing)
    meta === nothing && return nothing
    actual = get(meta, "grid", nothing)
    actual === nothing && return nothing
    (wanted, need_bind, pname) = _resolve_or_mark(g, b, "grid")
    if need_bind
        return _bind_pvar_name(b, pname, actual)
    end
    return (wanted === actual) ? b : nothing
end

function _guard_dim_is_spatial_dim_of(g, b, ctx)
    pvar = String(g.params["pvar"])
    dim_name = _resolve_name(b, pvar)
    dim_name === nothing && return nothing
    (grid, _, _) = _resolve_or_mark(g, b, "grid")
    grid === nothing && return nothing
    meta = get(ctx.grids, grid, nothing)
    meta === nothing && return nothing
    return (dim_name in get(meta, "spatial_dims", String[])) ? b : nothing
end

function _guard_dim_is_periodic(g, b, ctx)
    pvar = String(g.params["pvar"])
    dim_name = _resolve_name(b, pvar)
    if dim_name === nothing
        # §9.2.1 accepts a bare string in pvar (e.g. "x") — treat as a literal
        # dimension name when the string is not a pvar.
        pv = String(g.params["pvar"])
        dim_name = _is_pvar_string(pv) ? nothing : pv
    end
    dim_name === nothing && return nothing
    (grid, _, _) = _resolve_or_mark(g, b, "grid")
    grid === nothing && return nothing
    meta = get(ctx.grids, grid, nothing)
    meta === nothing && return nothing
    return (dim_name in get(meta, "periodic_dims", String[])) ? b : nothing
end

function _guard_dim_is_nonuniform(g, b, ctx)
    pvar = String(g.params["pvar"])
    dim_name = _resolve_name(b, pvar)
    if dim_name === nothing
        pv = String(g.params["pvar"])
        dim_name = _is_pvar_string(pv) ? nothing : pv
    end
    dim_name === nothing && return nothing
    (grid, _, _) = _resolve_or_mark(g, b, "grid")
    grid === nothing && return nothing
    meta = get(ctx.grids, grid, nothing)
    meta === nothing && return nothing
    return (dim_name in get(meta, "nonuniform_dims", String[])) ? b : nothing
end

function _guard_var_location_is(g, b, ctx)
    pvar = String(g.params["pvar"])
    var_name = _resolve_name(b, pvar)
    var_name === nothing && return nothing
    target = String(g.params["location"])
    meta = get(ctx.variables, var_name, nothing)
    meta === nothing && return nothing
    return (get(meta, "location", nothing) == target) ? b : nothing
end

function _guard_var_shape_rank(g, b, ctx)
    pvar = String(g.params["pvar"])
    var_name = _resolve_name(b, pvar)
    var_name === nothing && return nothing
    want = Int(g.params["rank"])
    meta = get(ctx.variables, var_name, nothing)
    meta === nothing && return nothing
    shape = get(meta, "shape", nothing)
    shape === nothing && return nothing
    return (length(shape) == want) ? b : nothing
end

# ============================================================================
# Rewriter (§5.2.5)
# ============================================================================

"""
    rewrite(expr, rules, ctx; max_passes=32) -> Expr

Run the rule engine on `expr` per RFC §5.2.5: each pass walks top-down,
the first rule whose pattern matches fires, the rewritten subtree is
sealed for the remainder of the pass (walker does NOT descend into the
rewrite), then we continue with siblings. A pass that produces no
rewrites terminates the loop. If `max_passes` is reached without
convergence, throws [`RuleEngineError`](@ref) with code
`E_RULES_NOT_CONVERGED`.
"""
function rewrite(expr::Expr, rules::Vector{Rule}, ctx::RuleContext=RuleContext();
                 max_passes::Int=32)::Expr
    current = expr
    for pass in 1:max_passes
        changed = Ref(false)
        current = _rewrite_pass(current, rules, ctx, changed)
        changed[] || return current
    end
    throw(RuleEngineError("E_RULES_NOT_CONVERGED",
        "rule engine did not converge within $max_passes passes"))
end

function _rewrite_pass(expr::Expr, rules::Vector{Rule}, ctx::RuleContext,
                       changed::Ref{Bool})::Expr
    for rule in rules
        m = match_pattern(rule.pattern, expr)
        m === nothing && continue
        m2 = check_guards(rule.where, m, ctx)
        m2 === nothing && continue
        check_scope(rule, m2, ctx) || continue
        new_expr = apply_bindings(rule.replacement, m2)
        changed[] = true
        return new_expr  # sealed: do not descend
    end
    if expr isa OpExpr
        new_args = Expr[_rewrite_pass(a, rules, ctx, changed) for a in expr.args]
        # Structural equality check avoids allocating a new node when nothing
        # below changed. Here we always allocate; OpExpr is immutable, cheap.
        return OpExpr(expr.op, new_args;
                      wrt=expr.wrt, dim=expr.dim,
                      output_idx=expr.output_idx,
                      expr_body=expr.expr_body,
                      reduce=expr.reduce, ranges=expr.ranges,
                      regions=expr.regions, values=expr.values,
                      shape=expr.shape, perm=expr.perm,
                      axis=expr.axis, fn=expr.fn,
                      handler_id=expr.handler_id)
    end
    return expr
end

# ============================================================================
# JSON loading (rules and expressions)
# ============================================================================

"""
    parse_rule(obj) -> Rule
    parse_rule(name::AbstractString, obj) -> Rule

Build a [`Rule`](@ref) from a decoded JSON object (a `Dict` or similar).
The object must contain `pattern` and `replacement` fields. Optional:
`where` (array of guard objects OR an expression-AST predicate per
RFC §5.2.7), `region` (legacy advisory string OR a scope object per
RFC §5.2.7).
"""
function parse_rule(name::AbstractString, obj)::Rule
    pat = _parse_expr(_getkey(obj, "pattern"))
    repl_raw = _getkey(obj, "replacement"; default=nothing)
    repl_raw === nothing && throw(RuleEngineError("E_RULE_REPLACEMENT_MISSING",
        "rule $name: MVP supports only the 'replacement' form; 'use:' rules are deferred"))
    repl = _parse_expr(repl_raw)
    where_raw = _getkey(obj, "where"; default=nothing)
    guards, where_expr = _parse_where(String(name), where_raw)
    region_raw = _getkey(obj, "region"; default=nothing)
    region = _parse_region(String(name), region_raw)
    return Rule(String(name), pat, guards, repl, region, where_expr)
end

# Discriminate array-of-guards vs expression predicate (RFC §5.2.7).
function _parse_where(name::String, raw)
    raw === nothing && return (Guard[], nothing)
    if raw isa AbstractVector
        return ([_parse_guard(g) for g in raw], nothing)
    end
    if _is_dict_like(raw)
        # Must have an `op` field to be a valid expression predicate.
        op = _getkey(raw, "op"; default=nothing)
        op === nothing && throw(RuleEngineError("E_RULE_PARSE",
            "rule $name: `where` object must be an expression node with an `op` field"))
        return (Guard[], _parse_expr(raw))
    end
    throw(RuleEngineError("E_RULE_PARSE",
        "rule $name: `where` must be an array of guards or an expression object"))
end

# Discriminate legacy advisory string vs per-point scope object.
function _parse_region(name::String, raw)::Union{String,RuleRegion,Nothing}
    raw === nothing && return nothing
    if raw isa AbstractString
        return String(raw)
    end
    if _is_dict_like(raw)
        kind = _getkey(raw, "kind"; default=nothing)
        kind === nothing && throw(RuleEngineError("E_RULE_PARSE",
            "rule $name: `region` object must carry a `kind` field"))
        k = String(kind)
        if k == "boundary"
            side = _getkey(raw, "side"; default=nothing)
            side === nothing && throw(RuleEngineError("E_RULE_PARSE",
                "rule $name: region.boundary requires `side`"))
            return RegionBoundary(String(side))
        elseif k == "panel_boundary"
            panel = _getkey(raw, "panel"; default=nothing)
            side = _getkey(raw, "side"; default=nothing)
            (panel === nothing || side === nothing) && throw(RuleEngineError(
                "E_RULE_PARSE",
                "rule $name: region.panel_boundary requires `panel` and `side`"))
            return RegionPanelBoundary(Int(panel), String(side))
        elseif k == "mask_field"
            field = _getkey(raw, "field"; default=nothing)
            field === nothing && throw(RuleEngineError("E_RULE_PARSE",
                "rule $name: region.mask_field requires `field`"))
            return RegionMaskField(String(field))
        elseif k == "index_range"
            axis = _getkey(raw, "axis"; default=nothing)
            lo = _getkey(raw, "lo"; default=nothing)
            hi = _getkey(raw, "hi"; default=nothing)
            (axis === nothing || lo === nothing || hi === nothing) && throw(
                RuleEngineError("E_RULE_PARSE",
                    "rule $name: region.index_range requires `axis`, `lo`, `hi`"))
            return RegionIndexRange(String(axis), Int(lo), Int(hi))
        end
        throw(RuleEngineError("E_RULE_PARSE",
            "rule $name: unknown region.kind `$k` (closed set: boundary, panel_boundary, mask_field, index_range)"))
    end
    throw(RuleEngineError("E_RULE_PARSE",
        "rule $name: `region` must be a string (legacy advisory) or object (normative scope)"))
end

parse_rule(obj) = parse_rule(_getkey(obj, "name"), obj)

function _parse_guard(obj)::Guard
    name = String(_getkey(obj, "guard"))
    params = Dict{String,Any}()
    for (k, v) in _iterate_dict(obj)
        sk = String(k)
        sk == "guard" && continue
        params[sk] = _jvalue(v)
    end
    return Guard(name, params)
end

"""
    parse_rules(obj) -> Vector{Rule}

Parse the `rules` section of a model into an ordered vector of
[`Rule`](@ref). Accepts either the JSON-object-keyed-by-name form or the
JSON-array form per RFC §5.2.5.
"""
function parse_rules(obj)::Vector{Rule}
    if obj isa AbstractVector
        return Rule[parse_rule(r) for r in obj]
    end
    result = Rule[]
    for (k, v) in _iterate_dict(obj)
        push!(result, parse_rule(String(k), v))
    end
    return result
end

# Load an expression from a JSON-decoded value. Integers come through as
# `Integer`, floats as `AbstractFloat`, variable/pattern-variable strings
# as `AbstractString`, and operator nodes as dict-like objects with `op`.
function _parse_expr(v)::Expr
    if v isa Expr
        return v
    elseif v isa Integer
        return IntExpr(Int64(v))
    elseif v isa AbstractFloat
        return NumExpr(Float64(v))
    elseif v isa AbstractString
        return VarExpr(String(v))
    elseif _is_dict_like(v)
        op = String(_getkey(v, "op"))
        args_raw = _getkey(v, "args"; default=[])
        args = Expr[_parse_expr(a) for a in args_raw]
        wrt = _string_or_nothing(_getkey(v, "wrt"; default=nothing))
        dim = _string_or_nothing(_getkey(v, "dim"; default=nothing))
        return OpExpr(op, args; wrt=wrt, dim=dim)
    end
    throw(RuleEngineError("E_RULE_PARSE",
        "cannot parse expression of type $(typeof(v))"))
end

_string_or_nothing(x) = x === nothing ? nothing : String(x)

_is_dict_like(x) = x isa AbstractDict || (x isa JSON3.Object)

function _getkey(obj, key::AbstractString; default=nothing)
    if obj isa AbstractDict
        return haskey(obj, key) ? obj[key] : default
    end
    if obj isa JSON3.Object
        sym = Symbol(key)
        return haskey(obj, sym) ? obj[sym] : default
    end
    throw(RuleEngineError("E_RULE_PARSE",
        "cannot read key '$key' from value of type $(typeof(obj))"))
end

function _iterate_dict(obj)
    if obj isa AbstractDict
        return collect(pairs(obj))
    elseif obj isa JSON3.Object
        return [(String(k), obj[k]) for k in keys(obj)]
    end
    throw(RuleEngineError("E_RULE_PARSE",
        "cannot iterate value of type $(typeof(obj))"))
end

function _jvalue(v)
    if v isa AbstractString
        return String(v)
    elseif v isa Integer
        return Int64(v)
    elseif v isa AbstractFloat
        return Float64(v)
    elseif v isa Bool
        return v
    elseif v isa AbstractVector
        return Any[_jvalue(x) for x in v]
    end
    return v
end

# ============================================================================
# Scope evaluation — region object + where expression (RFC §5.2.7)
# ============================================================================

"""
    check_scope(rule, bindings, ctx) -> Bool

Evaluate a rule's `region` scope (if an object) and `where_expr`
predicate (if present) against `ctx.query_point`. Returns `true` when
the rule should fire at the current query point, `false` otherwise
(conservative fall-through).

When `ctx.query_point` is empty and the rule carries any per-point
scope, the rule is disabled (returns `false`) — see RFC §5.2.7's
`W_UNEVAL_SCOPE` handling. A legacy string `region` and a missing
`where_expr` pass unconditionally, preserving backwards compatibility.
"""
function check_scope(rule::Rule, bindings::Dict{String,Expr}, ctx::RuleContext)::Bool
    # Region check.
    if rule.region isa RuleRegion
        _eval_region(rule.region, bindings, ctx) || return false
    end
    # Per-point where-expression check.
    if rule.where_expr !== nothing
        _eval_where_expr(rule.where_expr, bindings, ctx) || return false
    end
    return true
end

function _eval_region(r::RegionIndexRange, b::Dict{String,Expr}, ctx::RuleContext)::Bool
    isempty(ctx.query_point) && return false
    haskey(ctx.query_point, r.axis) || return false
    v = ctx.query_point[r.axis]
    return r.lo <= v <= r.hi
end

function _eval_region(r::RegionBoundary, b::Dict{String,Expr}, ctx::RuleContext)::Bool
    isempty(ctx.query_point) && return false
    ctx.grid_name === nothing && return false
    meta = get(ctx.grids, ctx.grid_name, nothing)
    meta === nothing && return false
    bounds = get(meta, "dim_bounds", nothing)
    bounds === nothing && return false
    side = r.side
    # Map side name to (axis, lo-or-hi).
    side_map = Dict(
        "xmin" => ("x", :lo), "xmax" => ("x", :hi),
        "ymin" => ("y", :lo), "ymax" => ("y", :hi),
        "zmin" => ("z", :lo), "zmax" => ("z", :hi),
        "west" => ("x", :lo), "east" => ("x", :hi),
        "south" => ("y", :lo), "north" => ("y", :hi),
        "bottom" => ("z", :lo), "top" => ("z", :hi),
    )
    haskey(side_map, side) || return false
    (dim, which) = side_map[side]
    haskey(bounds, dim) || return false
    dim_bounds = bounds[dim]
    # Look up the canonical index name for that dim via grid.spatial_dims order.
    spatial_dims = get(meta, "spatial_dims", String[])
    idx_pos = findfirst(==(dim), spatial_dims)
    idx_pos === nothing && return false
    canonical = ("i", "j", "k", "l", "m")
    idx_pos > length(canonical) && return false
    idx_name = canonical[idx_pos]
    haskey(ctx.query_point, idx_name) || return false
    v = ctx.query_point[idx_name]
    target = which == :lo ? Int(dim_bounds[1]) : Int(dim_bounds[2])
    return v == target
end

"""
    _eval_region(r::RegionPanelBoundary, bindings, ctx) -> Bool

Evaluate a `{kind:"panel_boundary", panel, side}` scope against
`ctx.query_point` (RFC §5.2.7, §6.4). Cubed_sphere only.

A grid is recognized as cubed_sphere when its metadata entry in
`ctx.grids` carries a `"panel_connectivity"` sub-dict (the
`neighbors` / `axis_flip` tables of §6.4). Applying the rule to a grid
without that marker throws [`RuleEngineError`](@ref) with code
`E_REGION_GRID_MISMATCH`.

The canonical cubed_sphere query-point axes are `p`, `i`, `j` (§7 query-
point table). `side` names map to the panel-local axes: `xmin`/`west` →
`-i`, `xmax`/`east` → `+i`, `ymin`/`south` → `-j`, `ymax`/`north` → `+j`.
Edge detection uses the `dim_bounds` entries on the grid; absence or a
side name outside the closed set falls through (returns `false`).
"""
function _eval_region(r::RegionPanelBoundary, ::Dict{String,Expr}, ctx::RuleContext)::Bool
    ctx.grid_name === nothing && return false
    meta = get(ctx.grids, ctx.grid_name, nothing)
    meta === nothing && return false
    haskey(meta, "panel_connectivity") || throw(RuleEngineError(
        "E_REGION_GRID_MISMATCH",
        "rule region.panel_boundary applied to grid `$(ctx.grid_name)` " *
        "which has no panel_connectivity metadata (cubed_sphere-only scope)"))
    isempty(ctx.query_point) && return false
    haskey(ctx.query_point, "p") || return false
    ctx.query_point["p"] == r.panel || return false
    side_map = Dict(
        "xmin" => ("i", :lo), "xmax" => ("i", :hi),
        "west" => ("i", :lo), "east" => ("i", :hi),
        "ymin" => ("j", :lo), "ymax" => ("j", :hi),
        "south" => ("j", :lo), "north" => ("j", :hi),
    )
    haskey(side_map, r.side) || return false
    (axis, which) = side_map[r.side]
    bounds = get(meta, "dim_bounds", nothing)
    bounds === nothing && return false
    haskey(bounds, axis) || return false
    axis_bounds = bounds[axis]
    target = which == :lo ? Int(axis_bounds[1]) : Int(axis_bounds[2])
    haskey(ctx.query_point, axis) || return false
    return ctx.query_point[axis] == target
end

function _eval_region(r::RegionMaskField, b::Dict{String,Expr}, ctx::RuleContext)::Bool
    isempty(ctx.query_point) && return false
    haskey(ctx.mask_fields, r.field) || return false
    points = ctx.mask_fields[r.field]
    for pt in points
        _point_subset_matches(pt, ctx.query_point) && return true
    end
    return false
end

# A truthy mask entry matches when every (axis, value) it declares
# agrees with the corresponding entry in `ctx.query_point`. Axes present
# in the query point but absent from the mask entry are ignored —
# mask entries can be as coarse as the mask's intrinsic dimensionality
# (e.g. a 2D surface mask on a 3D grid matches on i,j regardless of k).
function _point_subset_matches(mask_pt::Dict{String,Int},
                               query_pt::Dict{String,Int})::Bool
    isempty(mask_pt) && return false
    for (axis, v) in mask_pt
        haskey(query_pt, axis) || return false
        query_pt[axis] == v || return false
    end
    return true
end

"""
    _eval_where_expr(expr, bindings, ctx) -> Bool

Evaluate `expr` under pattern-variable bindings and query-point indices,
returning a boolean. Supports the scalar subset of §4 ops: arithmetic,
comparison, logical ops, and bare-string index references resolved
against `ctx.query_point` and `bindings` (bindings to `VarExpr` are
resolved as index names; bindings to `IntExpr` / `NumExpr` as constants).
Unsupported ops, unresolved names, or non-scalar results cause the
predicate to evaluate `false` (conservative fall-through).
"""
function _eval_where_expr(expr::Expr, b::Dict{String,Expr}, ctx::RuleContext)::Bool
    isempty(ctx.query_point) && return false
    val = _eval_scalar(expr, b, ctx)
    val === nothing && return false
    if val isa Bool
        return val
    elseif val isa Integer
        return val != 0
    elseif val isa AbstractFloat
        return val != 0.0
    end
    return false
end

function _eval_scalar(e::Expr, b::Dict{String,Expr}, ctx::RuleContext)
    if e isa IntExpr
        return e.value
    elseif e isa NumExpr
        return e.value
    elseif e isa VarExpr
        n = e.name
        # Pattern variable bound to something concrete?
        if _is_pvar_string(n) && haskey(b, n)
            return _eval_scalar(b[n], b, ctx)
        end
        # Query-point index?
        haskey(ctx.query_point, n) && return ctx.query_point[n]
        return nothing
    elseif e isa OpExpr
        return _eval_op(e, b, ctx)
    end
    return nothing
end

function _eval_op(e::OpExpr, b, ctx)
    op = e.op
    args = [_eval_scalar(a, b, ctx) for a in e.args]
    any(a -> a === nothing, args) && !(op in ("and", "or")) && return nothing
    if op == "+"
        return reduce(+, args; init=0)
    elseif op == "-"
        length(args) == 1 && return -args[1]
        return args[1] - reduce(+, args[2:end]; init=0)
    elseif op == "*"
        return reduce(*, args; init=1)
    elseif op == "/"
        length(args) >= 2 || return nothing
        return args[1] / args[2]
    elseif op == "=="
        length(args) == 2 || return nothing
        return args[1] == args[2]
    elseif op == "!="
        length(args) == 2 || return nothing
        return args[1] != args[2]
    elseif op == "<"
        length(args) == 2 || return nothing
        return args[1] < args[2]
    elseif op == "<="
        length(args) == 2 || return nothing
        return args[1] <= args[2]
    elseif op == ">"
        length(args) == 2 || return nothing
        return args[1] > args[2]
    elseif op == ">="
        length(args) == 2 || return nothing
        return args[1] >= args[2]
    elseif op == "and"
        return all(a -> a === true || (a isa Number && a != 0), args)
    elseif op == "or"
        return any(a -> a === true || (a isa Number && a != 0), args)
    elseif op == "not"
        length(args) == 1 || return nothing
        v = args[1]
        return !(v === true || (v isa Number && v != 0))
    end
    return nothing
end

# ============================================================================
# Unrewritten PDE op check (§11 Step 7)
# ============================================================================

const _PDE_OPS = Set(["grad", "div", "laplacian", "D", "bc"])

"""
    check_unrewritten_pde_ops(expr) -> Nothing

Scan `expr` for leftover PDE ops (`grad`, `div`, `laplacian`, `D`, `bc`)
and throw [`RuleEngineError`](@ref) `E_UNREWRITTEN_PDE_OP` if any are
found. Authors opt out by marking an equation `passthrough: true` at the
pipeline layer (§11); this check is run only on non-passthrough
equations.
"""
function check_unrewritten_pde_ops(expr::Expr)
    found = _find_pde_op(expr)
    if found !== nothing
        throw(RuleEngineError("E_UNREWRITTEN_PDE_OP",
            "equation still contains PDE op '$found' after rewrite; " *
            "annotate the equation with 'passthrough: true' to opt out"))
    end
    return nothing
end

function _find_pde_op(e::Expr)::Union{String,Nothing}
    if e isa OpExpr
        e.op in _PDE_OPS && return e.op
        for a in e.args
            r = _find_pde_op(a)
            r === nothing || return r
        end
    end
    return nothing
end
