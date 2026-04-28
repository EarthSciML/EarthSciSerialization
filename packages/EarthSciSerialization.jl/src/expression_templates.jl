"""
    expression_templates.jl

Parse-time expansion of `expression_templates` (RFC v2 §4 Option A
always-expanded; docs/content/rfcs/ast-expression-templates.md, esm-giy).

Operates on a native-Julia dict tree (the output of `_to_native_json`)
before `coerce_esm_file` walks it. After expansion every
`apply_expression_template` reference has been replaced by the
substituted body, and the originating `expression_templates` block
inside each Model / ReactionSystem has been removed.
"""

const APPLY_TEMPLATE_OP = "apply_expression_template"

"""
    expand_expression_templates!(data::Dict{String,Any})

Expand templates in place across `data["models"]` and
`data["reaction_systems"]`. Throws `ParseError` if the file declares
`esm: < 0.4.0` while using templates or `apply_expression_template`.
"""
function expand_expression_templates!(data::Dict{String,Any})
    has_use = _scan_for_apply_template(data)
    has_block = false
    for section in ("models", "reaction_systems")
        comps = get(data, section, nothing)
        if isa(comps, Dict)
            for c in values(comps)
                if isa(c, Dict)
                    t = get(c, "expression_templates", nothing)
                    if isa(t, Dict) && !isempty(t)
                        has_block = true
                        break
                    end
                end
            end
        end
        has_block && break
    end

    if has_use || has_block
        v = get(data, "esm", "")
        if !_esm_version_at_least(string(v), 0, 4, 0)
            throw(ParseError(
                "expression_templates / apply_expression_template require esm: 0.4.0 or later " *
                "(file declares esm: \"$v\")"
            ))
        end
    end

    for section in ("models", "reaction_systems")
        comps = get(data, section, nothing)
        if isa(comps, Dict)
            for (_, c) in comps
                if isa(c, Dict)
                    _expand_in_component!(c)
                end
            end
        end
    end
    return data
end

function _expand_in_component!(component::Dict)
    templates_raw = pop!(component, "expression_templates", Dict{String,Any}())
    templates = isa(templates_raw, Dict) ? templates_raw : Dict{String,Any}()

    if !isempty(templates)
        for (k, v) in collect(component)
            k == "subsystems" && continue
            component[k] = _expand_walk(v, templates)
        end
    end

    subs = get(component, "subsystems", nothing)
    if isa(subs, Dict)
        for (_, sub) in subs
            if isa(sub, Dict) && !haskey(sub, "ref")
                _expand_in_component!(sub)
            end
        end
    end
    return component
end

function _expand_walk(node, templates)
    if isa(node, Dict)
        if get(node, "op", nothing) == APPLY_TEMPLATE_OP
            return _expand_apply_node(node, templates)
        end
        out = Dict{String,Any}()
        for (k, v) in node
            out[string(k)] = _expand_walk(v, templates)
        end
        return out
    elseif isa(node, AbstractVector)
        return [_expand_walk(v, templates) for v in node]
    else
        return node
    end
end

function _expand_apply_node(node::Dict, templates::Dict)
    name = string(get(node, "name", ""))
    template = get(templates, name, nothing)
    if !isa(template, Dict)
        throw(ParseError("apply_expression_template references unknown template \"$name\""))
    end
    params_raw = get(template, "params", Any[])
    params = String[string(p) for p in params_raw]
    bindings_raw = get(node, "bindings", nothing)
    if !isa(bindings_raw, Dict)
        throw(ParseError("apply_expression_template \"$name\" missing 'bindings' object"))
    end
    bindings = Dict{String,Any}(string(k) => v for (k, v) in bindings_raw)
    for p in params
        if !haskey(bindings, p)
            throw(ParseError("apply_expression_template \"$name\" missing binding \"$p\""))
        end
    end
    for k in keys(bindings)
        if !(k in params)
            throw(ParseError("apply_expression_template \"$name\" has unknown binding \"$k\""))
        end
    end
    body = _deep_copy_json(get(template, "body", nothing))
    return _substitute_template_body(body, bindings)
end

function _substitute_template_body(body, bindings::Dict)
    if isa(body, AbstractString)
        if haskey(bindings, body)
            return _deep_copy_json(bindings[body])
        end
        return body
    elseif isa(body, Dict)
        out = Dict{String,Any}()
        for (k, v) in body
            kk = string(k)
            if kk == "args" || kk == "values"
                if isa(v, AbstractVector)
                    out[kk] = Any[_substitute_template_body(x, bindings) for x in v]
                else
                    out[kk] = v
                end
            elseif kk == "expr"
                out[kk] = _substitute_template_body(v, bindings)
            else
                out[kk] = v
            end
        end
        return out
    elseif isa(body, AbstractVector)
        return Any[_substitute_template_body(x, bindings) for x in body]
    else
        return body
    end
end

function _deep_copy_json(v)
    if isa(v, Dict)
        out = Dict{String,Any}()
        for (k, val) in v
            out[string(k)] = _deep_copy_json(val)
        end
        return out
    elseif isa(v, AbstractVector)
        return Any[_deep_copy_json(x) for x in v]
    else
        return v
    end
end

function _scan_for_apply_template(node)
    if isa(node, Dict)
        if get(node, "op", nothing) == APPLY_TEMPLATE_OP
            return true
        end
        for v in values(node)
            _scan_for_apply_template(v) && return true
        end
    elseif isa(node, AbstractVector)
        for v in node
            _scan_for_apply_template(v) && return true
        end
    end
    return false
end

function _esm_version_at_least(v::AbstractString, ma::Int, mi::Int, pa::Int)
    m = match(r"^(\d+)\.(\d+)\.(\d+)$", v)
    m === nothing && return false
    a = parse(Int, m.captures[1])
    b = parse(Int, m.captures[2])
    c = parse(Int, m.captures[3])
    a != ma && return a > ma
    b != mi && return b > mi
    return c >= pa
end

"""
    DictView(d::Dict)

Tiny wrapper that gives a `Dict{String,Any}` JSON3-style property access
(`view.foo` ≡ `d["foo"]`). Used by `load()` after
`expand_expression_templates!` to feed `coerce_esm_file` without
round-tripping through JSON3 (which otherwise widens deeply-nested
integer literals to Float64). Recursive: nested Dicts are wrapped
on demand and Vectors get their Dict elements wrapped element-wise.
"""
struct DictView
    inner::Dict{String,Any}
end

function _wrap_for_view(v)
    if isa(v, Dict)
        return DictView(Dict{String,Any}(string(k) => val for (k, val) in v))
    elseif isa(v, AbstractVector)
        return Any[_wrap_for_view(x) for x in v]
    else
        return v
    end
end

function Base.getproperty(view::DictView, k::Symbol)
    k === :inner && return getfield(view, :inner)
    inner = getfield(view, :inner)
    haskey(inner, string(k)) || throw(KeyError(k))
    return _wrap_for_view(inner[string(k)])
end

function Base.haskey(view::DictView, k::Symbol)
    return haskey(getfield(view, :inner), string(k))
end

function Base.haskey(view::DictView, k::AbstractString)
    return haskey(getfield(view, :inner), String(k))
end

function Base.getindex(view::DictView, k)
    return _wrap_for_view(getfield(view, :inner)[string(k)])
end

function Base.pairs(view::DictView)
    return Iterators.map(p -> (Symbol(p.first) => _wrap_for_view(p.second)),
                         pairs(getfield(view, :inner)))
end

function Base.keys(view::DictView)
    return Iterators.map(Symbol, keys(getfield(view, :inner)))
end

function Base.length(view::DictView)
    return length(getfield(view, :inner))
end

function Base.iterate(view::DictView, state...)
    return iterate(pairs(view), state...)
end

function Base.get(view::DictView, k::Symbol, default)
    inner = getfield(view, :inner)
    haskey(inner, string(k)) ? _wrap_for_view(inner[string(k)]) : default
end

function Base.get(view::DictView, k::AbstractString, default)
    inner = getfield(view, :inner)
    haskey(inner, String(k)) ? _wrap_for_view(inner[String(k)]) : default
end
