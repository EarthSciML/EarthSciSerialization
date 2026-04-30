"""
Load-time expansion pass for `apply_expression_template` AST ops
(esm-spec §9.6, docs/rfcs/ast-expression-templates.md, esm-giy).

Walks each `models.<m>` and `reaction_systems.<rs>` block; if an
`expression_templates` block is present, every `apply_expression_template`
node anywhere in that component's expressions is replaced by the
substituted template body. After the pass, the file's typed tree
contains no `apply_expression_template` ops and no `expression_templates`
blocks — downstream consumers see only normal Expression ASTs (Option A
round-trip).

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
    # Recursively expand bindings (template bodies cannot contain
    # apply_expression_template, but the *bindings* may).
    resolved = Dict{String,Any}()
    for (k, v) in pairs(bindings_raw)
        resolved[string(k)] = _walk(v, templates, scope)
    end
    body = get(decl, "body", get(decl, :body, nothing))
    return _substitute(body, resolved)
end

function _walk(node, templates::Dict{String,Any}, scope::String)
    if _is_array(node)
        return Any[_walk(c, templates, scope) for c in node]
    end
    if _is_object(node)
        op = get(node, "op", get(node, :op, nothing))
        op_str = op === nothing ? "" : string(op)
        if op_str == APPLY_EXPRESSION_TEMPLATE_OP
            return _expand_apply(node, templates, scope)
        end
        out = Dict{String,Any}()
        for (k, v) in pairs(node)
            out[string(k)] = _walk(v, templates, scope)
        end
        return out
    end
    return node
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

    apply_paths = String[]
    _find_apply_paths!(apply_paths, root, "")
    if isempty(apply_paths)
        # No apply ops, but there ARE template blocks → strip and wrap.
        return JSONLikeDict(_strip_expression_templates(root))
    end

    for compkind in ("models", "reaction_systems")
        comps = get(root, compkind, nothing)
        comps === nothing && continue
        _is_object(comps) || continue
        for (cname, compraw) in pairs(comps)
            _is_object(compraw) || continue
            comp = compraw::Dict{String,Any}
            tplraw = get(comp, "expression_templates", nothing)
            templates = Dict{String,Any}()
            if _is_object(tplraw)
                for (tname, tdecl) in pairs(tplraw)
                    templates[string(tname)] = tdecl
                end
                _validate_templates(templates, "$compkind.$(string(cname))")
            end
            for k in collect(keys(comp))
                k == "expression_templates" && continue
                comp[k] = _walk(comp[k], templates, "$compkind.$(string(cname)).$k")
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
