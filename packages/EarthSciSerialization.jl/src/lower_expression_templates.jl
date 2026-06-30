"""
Load-time rewrite pass for `expression_templates` (esm-spec §9.6,
docs/rfcs/ast-expression-templates.md, esm-giy).

`expression_templates` is the single structural-substitution mechanism in the
format. Each entry is a rewrite rule with `params` (metavariables) and a `body`
(the replacement Expression), applied in one of two ways:

- WITHOUT a `match` field — invoked explicitly by an `apply_expression_template`
  node whose `bindings` supply each param's AST (named-template expansion).
- WITH a `match` field — an auto-applied rewrite rule: `match` is a pattern
  Expression whose param occurrences are wildcards, fired wherever it
  structurally matches a node. A param in an operand/`args` position binds to the
  matched sub-AST; a param in a scalar field (`dim`, `side`, …) binds to the
  matched literal.

Rewriting is a SINGLE bottom-up pass over each component's expression trees
(`_rewrite`): children are rewritten first; then a node is expanded (apply) or
matched against the `match` rules in template DECLARATION order (first match
wins). A replacement is NOT re-scanned, so the pass terminates in one sweep; a
`match` rule whose `body` re-introduces its own pattern is rejected up front
(`rewrite_rule_nonterminating`). After the pass the tree contains no
`apply_expression_template` ops and no `expression_templates` blocks — downstream
consumers see only normal Expression ASTs (Option A round-trip).

Operates on the raw JSON view (JSON3.Object/Array or Dict/Vector) and
returns a `Dict{String,Any}` view ready for `coerce_esm_file`.
"""

const APPLY_EXPRESSION_TEMPLATE_OP = "apply_expression_template"

"""
    JSONLikeDict

Thin wrapper around `Dict{String,Any}` that exposes string-keyed
entries via property syntax (`view.esm`, `view.metadata`, ...) so the
existing JSON3-compatible code paths in `coerce_esm_file` work
uniformly on the post-template-expansion view.

Indexing via `view[:key]` and `view["key"]`, `haskey`, `pairs`, and
iteration are all forwarded to the underlying dict; anything not
covered here is intentionally not implemented (this wrapper exists
only for the load-time path).
"""
struct JSONLikeDict
    data::Dict{String,Any}
end

_wrap(x) = x isa Dict{String,Any} ? JSONLikeDict(x) :
           x isa AbstractDict ? JSONLikeDict(Dict{String,Any}(string(k) => v for (k,v) in pairs(x))) :
           x isa AbstractVector ? Any[_wrap(v) for v in x] :
           x

Base.getproperty(v::JSONLikeDict, sym::Symbol) =
    sym === :data ? getfield(v, :data) : _wrap(getfield(v, :data)[string(sym)])

Base.hasproperty(v::JSONLikeDict, sym::Symbol) =
    sym === :data || haskey(getfield(v, :data), string(sym))

Base.haskey(v::JSONLikeDict, key::Symbol) = haskey(getfield(v, :data), string(key))
Base.haskey(v::JSONLikeDict, key::AbstractString) = haskey(getfield(v, :data), String(key))

Base.getindex(v::JSONLikeDict, key::Symbol) = _wrap(getfield(v, :data)[string(key)])
Base.getindex(v::JSONLikeDict, key::AbstractString) = _wrap(getfield(v, :data)[String(key)])

function Base.get(v::JSONLikeDict, key::Symbol, default)
    d = getfield(v, :data); s = string(key)
    haskey(d, s) ? _wrap(d[s]) : default
end
function Base.get(v::JSONLikeDict, key::AbstractString, default)
    d = getfield(v, :data); s = String(key)
    haskey(d, s) ? _wrap(d[s]) : default
end

# Iteration / pairs wrap nested values so `coerce_*` functions that
# do `(k, v) in pairs(file.models)` see JSONLikeDict-wrapped models.
struct _JSONLikePairs
    inner::Dict{String,Any}
end
Base.iterate(p::_JSONLikePairs) = _step(p.inner, iterate(p.inner))
Base.iterate(p::_JSONLikePairs, state) = _step(p.inner, iterate(p.inner, state))
Base.length(p::_JSONLikePairs) = length(p.inner)
function _step(_::Dict{String,Any}, it)
    it === nothing && return nothing
    (kv, state) = it
    return (Pair(kv.first, _wrap(kv.second)), state)
end

Base.pairs(v::JSONLikeDict) = _JSONLikePairs(getfield(v, :data))
Base.keys(v::JSONLikeDict) = keys(getfield(v, :data))
Base.iterate(v::JSONLikeDict) = iterate(_JSONLikePairs(getfield(v, :data)))
Base.iterate(v::JSONLikeDict, state) = iterate(_JSONLikePairs(getfield(v, :data)), state)
Base.length(v::JSONLikeDict) = length(getfield(v, :data))

"""
    ExpressionTemplateError <: Exception

Exception raised when expression-template expansion fails. Carries a
stable `code` matching one of:

- `apply_expression_template_unknown_template`
- `apply_expression_template_bindings_mismatch`
- `apply_expression_template_recursive_body`
- `apply_expression_template_invalid_declaration`
- `apply_expression_template_version_too_old`
- `rewrite_rule_nonterminating`
"""
struct ExpressionTemplateError <: Exception
    code::String
    message::String
end

Base.showerror(io::IO, e::ExpressionTemplateError) =
    print(io, "[$(e.code)] $(e.message)")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_is_object(x) = (x isa AbstractDict || x isa JSON3.Object)
_is_array(x)  = (x isa AbstractVector || x isa JSON3.Array)

function _to_dict(x)::Dict{String,Any}
    out = Dict{String,Any}()
    for (k, v) in pairs(x)
        out[string(k)] = _normalize(v)
    end
    return out
end

function _normalize(x)
    if _is_object(x)
        return _to_dict(x)
    elseif _is_array(x)
        return Any[_normalize(v) for v in x]
    else
        return x
    end
end

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

function _assert_no_nested_apply(body, template_name::String, path::String)
    if _is_array(body)
        for (i, child) in enumerate(body)
            _assert_no_nested_apply(child, template_name, "$path/$(i-1)")
        end
        return
    end
    if _is_object(body)
        op = get(body, :op, get(body, "op", nothing))
        if op === nothing
            # Some objects may use string-keyed maps post-normalization.
            op = get(body, "op", nothing)
        end
        op_str = op === nothing ? "" : string(op)
        if op_str == APPLY_EXPRESSION_TEMPLATE_OP
            throw(ExpressionTemplateError(
                "apply_expression_template_recursive_body",
                "expression_templates.$(template_name): body contains nested 'apply_expression_template' at $path; templates MUST NOT call other templates"))
        end
        for (k, v) in pairs(body)
            _assert_no_nested_apply(v, template_name, "$path/$(string(k))")
        end
    end
end

function _validate_templates(templates::Dict{String,Any}, scope::String)
    for (name, decl) in templates
        if !_is_object(decl)
            throw(ExpressionTemplateError(
                "apply_expression_template_invalid_declaration",
                "$scope.expression_templates.$name: entry must be an object with params + body"))
        end
        params = get(decl, "params", get(decl, :params, nothing))
        if params === nothing || !_is_array(params) || length(params) == 0
            throw(ExpressionTemplateError(
                "apply_expression_template_invalid_declaration",
                "$scope.expression_templates.$name: 'params' must be a non-empty array of strings"))
        end
        seen = Set{String}()
        for p in params
            if !(p isa AbstractString) || isempty(p)
                throw(ExpressionTemplateError(
                    "apply_expression_template_invalid_declaration",
                    "$scope.expression_templates.$name: param names must be non-empty strings"))
            end
            ps = string(p)
            if ps in seen
                throw(ExpressionTemplateError(
                    "apply_expression_template_invalid_declaration",
                    "$scope.expression_templates.$name: param '$ps' is declared twice"))
            end
            push!(seen, ps)
        end
        body = get(decl, "body", get(decl, :body, nothing))
        if body === nothing
            throw(ExpressionTemplateError(
                "apply_expression_template_invalid_declaration",
                "$scope.expression_templates.$name: 'body' is required"))
        end
        _assert_no_nested_apply(body, name, "/body")

        # esm-spec §9.6: an optional `match` pattern turns the entry into an
        # auto-applied rewrite rule. The pattern is an Expression in which the
        # declared params are wildcards; it MUST NOT contain nested
        # apply_expression_template ops. Rewriting is single-pass with no
        # re-scan, so a rule whose `body` re-introduces its own pattern would
        # loop under any future multi-pass evaluator and is rejected here
        # (esm-spec §9.6.3 rule 2, diagnostic `rewrite_rule_nonterminating`).
        match = get(decl, "match", get(decl, :match, nothing))
        if match !== nothing
            _assert_no_nested_apply(match, name, "/match")
            param_set = Set{String}(string(p) for p in params)
            if _body_reintroduces_pattern(match, param_set, body)
                throw(ExpressionTemplateError(
                    "rewrite_rule_nonterminating",
                    "$scope.expression_templates.$name: the `match` rule's `body` " *
                    "re-introduces its own pattern; single-pass rewriting forbids " *
                    "self-reintroducing rules (esm-spec §9.6.3)"))
            end
        end
    end
end

# ---------------------------------------------------------------------------
# Substitution
# ---------------------------------------------------------------------------

function _substitute(body, bindings::Dict{String,Any})
    if body isa AbstractString
        s = string(body)
        if haskey(bindings, s)
            return deepcopy(bindings[s])
        end
        return body
    end
    if _is_array(body)
        return Any[_substitute(c, bindings) for c in body]
    end
    if _is_object(body)
        out = Dict{String,Any}()
        for (k, v) in pairs(body)
            out[string(k)] = _substitute(v, bindings)
        end
        return out
    end
    return body
end

function _expand_apply(node, templates::Dict{String,Any}, scope::String)
    name_raw = get(node, "name", get(node, :name, nothing))
    if name_raw === nothing
        throw(ExpressionTemplateError(
            "apply_expression_template_invalid_declaration",
            "$scope: apply_expression_template node missing 'name'"))
    end
    name = string(name_raw)
    decl = get(templates, name, nothing)
    if decl === nothing
        throw(ExpressionTemplateError(
            "apply_expression_template_unknown_template",
            "$scope: apply_expression_template references undeclared template '$name'"))
    end
    bindings_raw = get(node, "bindings", get(node, :bindings, nothing))
    if bindings_raw === nothing || !_is_object(bindings_raw)
        throw(ExpressionTemplateError(
            "apply_expression_template_bindings_mismatch",
            "$scope: apply_expression_template '$name' missing 'bindings' object"))
    end
    decl_params_raw = get(decl, "params", get(decl, :params, []))
    decl_params = String[string(p) for p in decl_params_raw]
    declared = Set(decl_params)
    provided = Set{String}([string(k) for (k, _) in pairs(bindings_raw)])
    for p in decl_params
        if !(p in provided)
            throw(ExpressionTemplateError(
                "apply_expression_template_bindings_mismatch",
                "$scope: apply_expression_template '$name' missing binding for param '$p'"))
        end
    end
    for p in provided
        if !(p in declared)
            throw(ExpressionTemplateError(
                "apply_expression_template_bindings_mismatch",
                "$scope: apply_expression_template '$name' supplies unknown param '$p'"))
        end
    end
    # The bindings have already been rewritten in place by the bottom-up
    # `_rewrite` pass (children are rewritten before their parent apply node is
    # expanded), so they are consumed as-is here. The template `body` is
    # instantiated by pure structural substitution and is NOT re-scanned
    # (esm-spec §9.6.3 rule 2: a replacement body is not re-matched).
    resolved = Dict{String,Any}()
    for (k, v) in pairs(bindings_raw)
        resolved[string(k)] = v
    end
    body = get(decl, "body", get(decl, :body, nothing))
    return _substitute(body, resolved)
end

# ---------------------------------------------------------------------------
# Structural pattern matching (auto-applied `match` rewrite rules, esm-spec §9.6)
# ---------------------------------------------------------------------------

# Structural equality over the normalized JSON view (Dict / Vector / scalar /
# String). Used to enforce that a metavariable bound twice in the same pattern
# binds to identical sub-trees.
function _json_equal(a, b)::Bool
    if a isa Bool || b isa Bool
        return (a isa Bool) && (b isa Bool) && a == b
    elseif a isa Number
        return (b isa Number) && a == b
    elseif a isa AbstractString
        return (b isa AbstractString) && string(a) == string(b)
    elseif _is_array(a)
        _is_array(b) || return false
        length(a) == length(b) || return false
        for (x, y) in zip(a, b)
            _json_equal(x, y) || return false
        end
        return true
    elseif _is_object(a)
        _is_object(b) || return false
        ka = Set(string(k) for (k, _) in pairs(a))
        kb = Set(string(k) for (k, _) in pairs(b))
        ka == kb || return false
        for k in ka
            _json_equal(get(a, k, get(a, Symbol(k), nothing)),
                        get(b, k, get(b, Symbol(k), nothing))) || return false
        end
        return true
    else
        return a === b || a == b
    end
end

"""
    _match_pattern(pattern, node, params, bindings) -> Bool

Structurally match `pattern` (an Expression with the declared `params` as
wildcards) against `node`, accumulating metavariable bindings in `bindings`.
A param string in an operand / `args` position binds to the matched sub-AST; a
param string in a scalar field (`dim`, `side`, …) binds to the matched literal
(esm-spec §9.6) — the same rule, since a bound param simply takes whatever the
corresponding node value is. Non-param strings, numbers, and booleans must
match literally; arrays match elementwise (same length); objects match when
every pattern key is present on `node` and matches (extra `node` keys are
allowed, so a pattern constrains only the fields it names).
"""
function _match_pattern(pattern, node, params::Set{String}, bindings::Dict{String,Any})::Bool
    if pattern isa Bool
        return (node isa Bool) && node == pattern
    elseif pattern isa AbstractString
        s = string(pattern)
        if s in params
            if haskey(bindings, s)
                return _json_equal(bindings[s], node)
            end
            bindings[s] = node
            return true
        end
        return (node isa AbstractString) && string(node) == s
    elseif pattern isa Number
        return (node isa Number) && !(node isa Bool) && node == pattern
    elseif _is_array(pattern)
        _is_array(node) || return false
        length(pattern) == length(node) || return false
        for (pp, nn) in zip(pattern, node)
            _match_pattern(pp, nn, params, bindings) || return false
        end
        return true
    elseif _is_object(pattern)
        _is_object(node) || return false
        for (k, pv) in pairs(pattern)
            ks = string(k)
            nv = get(node, ks, get(node, Symbol(ks), nothing))
            (nv === nothing && !_has_key(node, ks)) && return false
            _match_pattern(pv, nv, params, bindings) || return false
        end
        return true
    else
        # nothing / null literal in the pattern.
        return pattern === node
    end
end

_has_key(node, ks::AbstractString) =
    (haskey(node, ks) || haskey(node, Symbol(ks)))

"""
    _pattern_occurs(pattern, params, tree) -> Bool

True if `pattern` (params as wildcards) structurally matches `tree` itself or
any sub-node of `tree`. Used by the nontermination check.
"""
function _pattern_occurs(pattern, params::Set{String}, tree)::Bool
    if _match_pattern(pattern, tree, params, Dict{String,Any}())
        return true
    end
    if _is_array(tree)
        for c in tree
            _pattern_occurs(pattern, params, c) && return true
        end
    elseif _is_object(tree)
        for (_, v) in pairs(tree)
            _pattern_occurs(pattern, params, v) && return true
        end
    end
    return false
end

"""
    _body_reintroduces_pattern(pattern, params, body) -> Bool

True if instantiating `body` could re-introduce the rule's own `pattern`
(esm-spec §9.6.3 rule 2). For an operator (object) pattern this is any
structural occurrence of the pattern in `body`, including at its root (a `body`
that *is* a `grad` for a `grad`-matching rule). A bare-metavariable pattern
matches every node, so its trivial root self-match is ignored — only a deeper
re-introduction (in a proper sub-node) is flagged.
"""
function _body_reintroduces_pattern(pattern, params::Set{String}, body)::Bool
    if _is_object(pattern)
        return _pattern_occurs(pattern, params, body)
    end
    if _is_array(body)
        return any(_pattern_occurs(pattern, params, c) for c in body)
    elseif _is_object(body)
        return any(_pattern_occurs(pattern, params, v) for (_, v) in pairs(body))
    end
    return false
end

"""
    _rewrite(node, named, match_rules, scope) -> rewritten node

The single load-time rewrite pass (esm-spec §9.6.3): one bottom-up traversal of
the expression tree. Children are rewritten first; then this node is, in order,
(1) expanded if it is an `apply_expression_template` op, otherwise (2) matched
against the `match_rules` in declaration order, the FIRST matching rule firing.
Either replacement is returned WITHOUT re-scanning it (no re-match of a produced
body), so the pass terminates in a single sweep.

- `named`       : name → template declaration, for `apply_expression_template`.
- `match_rules` : ordered `(name, pattern, params::Set, body)` auto-rules.
"""
function _rewrite(node, named::Dict{String,Any}, match_rules::Vector{Any}, scope::String)
    if _is_array(node)
        return Any[_rewrite(c, named, match_rules, scope) for c in node]
    end
    if !_is_object(node)
        return node
    end
    # Bottom-up: rewrite every child before considering this node.
    rewritten = Dict{String,Any}()
    for (k, v) in pairs(node)
        rewritten[string(k)] = _rewrite(v, named, match_rules, scope)
    end
    op = get(rewritten, "op", nothing)
    op_str = op === nothing ? "" : string(op)
    if op_str == APPLY_EXPRESSION_TEMPLATE_OP
        # Named-template expansion; bindings are already rewritten. The
        # substituted body is the canonical expanded form and is not re-scanned.
        return _expand_apply(rewritten, named, scope)
    end
    # Auto-applied `match` rules, in template declaration order. First match
    # wins; the instantiated body is returned as-is (no re-scan).
    for rule in match_rules
        (_name, pattern, rparams, body) = rule
        bindings = Dict{String,Any}()
        if _match_pattern(pattern, rewritten, rparams, bindings)
            return _substitute(body, bindings)
        end
    end
    return rewritten
end

# ---------------------------------------------------------------------------
# Scan utilities
# ---------------------------------------------------------------------------

function _find_apply_paths!(hits::Vector{String}, x, path::String)
    if _is_array(x)
        for (i, child) in enumerate(x)
            _find_apply_paths!(hits, child, "$path/$(i-1)")
        end
        return
    end
    if _is_object(x)
        op = get(x, "op", get(x, :op, nothing))
        op_str = op === nothing ? "" : string(op)
        if op_str == APPLY_EXPRESSION_TEMPLATE_OP
            push!(hits, path)
        end
        for (k, v) in pairs(x)
            _find_apply_paths!(hits, v, "$path/$(string(k))")
        end
    end
end

function _has_apply_op(x)
    if _is_array(x)
        for child in x
            _has_apply_op(child) && return true
        end
        return false
    end
    if _is_object(x)
        op = get(x, "op", get(x, :op, nothing))
        op !== nothing && string(op) == APPLY_EXPRESSION_TEMPLATE_OP && return true
        for (_, v) in pairs(x)
            _has_apply_op(v) && return true
        end
    end
    return false
end

"""
    _has_template_machinery(raw_data) -> Bool

True if `raw_data` either declares any non-empty `expression_templates`
block under `models`/`reaction_systems`, or contains any
`apply_expression_template` op anywhere in the tree. Used by
[`lower_expression_templates`](@ref) to short-circuit on files that need
no template expansion (and so should not be wrapped in `JSONLikeDict`).
"""
function _has_template_machinery(raw_data)
    raw_data === nothing && return false
    _is_object(raw_data) || return false
    for compkind in ("models", "reaction_systems")
        comps = get(raw_data, Symbol(compkind), get(raw_data, compkind, nothing))
        comps === nothing && continue
        _is_object(comps) || continue
        for (_, comp) in pairs(comps)
            _is_object(comp) || continue
            tpl = get(comp, "expression_templates", get(comp, :expression_templates, nothing))
            if _is_object(tpl) && length(collect(pairs(tpl))) > 0
                return true
            end
        end
    end
    return _has_apply_op(raw_data)
end

# ---------------------------------------------------------------------------
# Pre-version-0.4.0 rejection
# ---------------------------------------------------------------------------

"""
    reject_expression_templates_pre_v04(raw_data)

Reject `expression_templates` blocks and `apply_expression_template` ops in
files declaring `esm` < 0.4.0. Mirrors the equivalent TS / Python / Rust /
Go checks for cross-binding-uniform diagnostics.
"""
function reject_expression_templates_pre_v04(raw_data)
    raw_data === nothing && return
    !_is_object(raw_data) && return
    esm_raw = get(raw_data, :esm, get(raw_data, "esm", nothing))
    esm_raw === nothing && return
    m = match(r"^(\d+)\.(\d+)\.(\d+)$", string(esm_raw))
    m === nothing && return
    major = parse(Int, m.captures[1])
    minor = parse(Int, m.captures[2])
    is_pre_v04 = (major == 0 && minor < 4)
    !is_pre_v04 && return

    offences = String[]
    for compkind in ("models", "reaction_systems")
        comps = get(raw_data, Symbol(compkind), get(raw_data, compkind, nothing))
        comps === nothing && continue
        _is_object(comps) || continue
        for (cname, comp) in pairs(comps)
            _is_object(comp) || continue
            if haskey(comp, "expression_templates") || haskey(comp, :expression_templates)
                push!(offences, "/$compkind/$(string(cname))/expression_templates")
            end
        end
    end
    _find_apply_paths!(offences, raw_data, "")

    if !isempty(offences)
        throw(ExpressionTemplateError(
            "apply_expression_template_version_too_old",
            "expression_templates / apply_expression_template require esm >= 0.4.0; file declares $(string(esm_raw)). Offending paths: $(join(offences, ", "))"))
    end
end

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

"""
    lower_expression_templates(raw_data) -> Dict{String,Any}

Expand every `apply_expression_template` node in `raw_data` against the
component-local `expression_templates` block, then strip those blocks
from the returned tree. The output is a normalized `Dict{String,Any}`
view ready to be passed to `coerce_esm_file`.

Throws [`ExpressionTemplateError`](@ref) on any of:

- file declares `esm` < 0.4.0 but uses templates
- `apply_expression_template` references an undeclared template name
- bindings do not exactly match the template's `params`
- template body contains a nested `apply_expression_template`
- declaration is malformed (params missing, body missing, etc.)
"""
function lower_expression_templates(raw_data)
    reject_expression_templates_pre_v04(raw_data)

    # Fast path: files that neither declare `expression_templates` blocks
    # nor use any `apply_expression_template` op need no expansion at all.
    # Return raw_data unchanged so downstream `coerce_esm_file` sees the
    # original JSON3.Object / Dict shape — no `JSONLikeDict` wrapping. This
    # keeps non-template files on the legacy code path, including those
    # that exercise downstream coercers (`coerce_function_tables`,
    # `coerce_grids`, etc.) whose type-gates predate JSONLikeDict.
    if !_has_template_machinery(raw_data)
        return raw_data
    end

    root = _to_dict(raw_data)::Dict{String,Any}

    for compkind in ("models", "reaction_systems")
        comps = get(root, compkind, nothing)
        comps === nothing && continue
        _is_object(comps) || continue
        for (cname, compraw) in pairs(comps)
            _is_object(compraw) || continue
            comp = compraw::Dict{String,Any}
            tplraw = get(comp, "expression_templates", nothing)
            # `named`       — every template keyed by name, consulted by
            #                 `apply_expression_template` (order-independent).
            # `match_rules` — the auto-applied `match` rules, in template
            #                 DECLARATION order (esm-spec §9.6.3).
            named = Dict{String,Any}()
            match_rules = Vector{Any}()
            if _is_object(tplraw)
                templates = Dict{String,Any}()
                for (tname, tdecl) in pairs(tplraw)
                    templates[string(tname)] = tdecl
                end
                _validate_templates(templates, "$compkind.$(string(cname))")
                for tname in _ordered_template_names(raw_data, compkind, string(cname), templates)
                    decl = templates[tname]
                    named[tname] = decl
                    m = get(decl, "match", get(decl, :match, nothing))
                    if m !== nothing
                        params = Set{String}(string(p) for p in get(decl, "params", String[]))
                        body = get(decl, "body", nothing)
                        push!(match_rules, (tname, m, params, body))
                    end
                end
            end
            # One bottom-up rewrite sweep per non-template field (esm-spec §9.6.3):
            # expands `apply_expression_template` ops AND fires auto `match` rules.
            for k in collect(keys(comp))
                k == "expression_templates" && continue
                comp[k] = _rewrite(comp[k], named, match_rules,
                                   "$compkind.$(string(cname)).$k")
            end
            delete!(comp, "expression_templates")
        end
    end

    leftover = String[]
    _find_apply_paths!(leftover, root, "")
    if !isempty(leftover)
        throw(ExpressionTemplateError(
            "apply_expression_template_unknown_template",
            "apply_expression_template ops remain after expansion at: $(join(leftover, ", ")) — likely referenced from a component lacking an expression_templates block"))
    end

    return JSONLikeDict(root)
end

"""
    _ordered_template_names(raw_data, compkind, cname, templates) -> Vector{String}

Template names of a component in DECLARATION order. The order is read from the
original (order-preserving) source view `raw_data` — `_to_dict` produces an
unordered `Dict`, but `match`-rule precedence (esm-spec §9.6.3) requires the
authored order. Any name not found in the source view (e.g. when `raw_data` is
an already-native, unordered dict) is appended by sorted name so the result is
still deterministic.
"""
function _ordered_template_names(raw_data, compkind, cname, templates::Dict{String,Any})
    ordered = String[]
    seen = Set{String}()
    comps = raw_data === nothing ? nothing :
        get(raw_data, Symbol(compkind), get(raw_data, compkind, nothing))
    comp = comps === nothing ? nothing :
        get(comps, Symbol(cname), get(comps, cname, nothing))
    tpl = (comp === nothing || !_is_object(comp)) ? nothing :
        get(comp, :expression_templates, get(comp, "expression_templates", nothing))
    if tpl !== nothing && _is_object(tpl)
        for (k, _) in pairs(tpl)
            ks = string(k)
            if haskey(templates, ks) && !(ks in seen)
                push!(ordered, ks)
                push!(seen, ks)
            end
        end
    end
    for ks in sort(collect(keys(templates)))
        ks in seen || (push!(ordered, ks); push!(seen, ks))
    end
    return ordered
end

function _strip_expression_templates(root::Dict{String,Any})::Dict{String,Any}
    for compkind in ("models", "reaction_systems")
        comps = get(root, compkind, nothing)
        comps === nothing && continue
        _is_object(comps) || continue
        for (_, compraw) in pairs(comps)
            _is_object(compraw) || continue
            delete!(compraw, "expression_templates")
        end
    end
    return root
end
