# Discretization pipeline per discretization RFC §11 (gt-gbs2) and
# DAE support / binding contract per RFC §12 (gt-q7sh).
#
# The public entry point is `discretize(esm::AbstractDict)`, which walks a
# parsed ESM document and emits a discretized ESM:
#
#   1. Canonicalize all expressions (§5.4).
#   2. Resolve model-level boundary conditions into a synthetic `bc` op so
#      they flow through the same rule engine as interior equations.
#   3. Apply the rule engine (§5.2) to every equation RHS and every BC
#      value with a max-pass budget.
#   4. Re-canonicalize the rewritten ASTs.
#   5. Check for unrewritten PDE ops (§11 Step 7) — error or
#      passthrough-annotate depending on `strict_unrewritten`.
#   6. RFC §12: classify each equation as `differential` vs `algebraic`
#      (LHS `D(x, wrt=<indep>)` versus anything else), count algebraic
#      equations across all models, stamp `metadata.system_class` on the
#      output (`"ode"` or `"dae"`), and either hand the DAE off to the
#      host assembler or abort with `E_NO_DAE_SUPPORT` per the
#      `dae_support` knob.
#   7. Record `metadata.discretized_from` provenance.
#
# Scheme-expansion of `use:<scheme>` rules (§7.2.1) is deferred to Step 1b
# and is out of scope here. Cross-grid `regrid` wrapping is likewise out
# of scope. The Julia binding's DAE **strategy** is direct hand-off to
# ModelingToolkit.jl, which natively accepts mixed differential/algebraic
# equation sets; we do not attempt index reduction here. See
# `docs/rfcs/discretization.md` §12 and `docs/rfcs/dae-binding-strategies.md`
# for the normative per-binding strategies.

"""
    discretize(esm::AbstractDict; max_passes::Int=32, strict_unrewritten::Bool=true,
               dae_support::Bool=true) -> Dict{String,Any}

Run the RFC §11 discretization pipeline on an ESM document and apply
the RFC §12 DAE binding contract.

`esm` is the parsed ESM payload as a `Dict{String,Any}` (the form produced
by [`load`](@ref) followed by `_to_native_json`, or by direct JSON
decoding). The function returns a new `Dict{String,Any}`; the input is not
mutated.

Behavior:

- Every equation in every model, and every boundary condition `value`
  expression, is first canonicalized per §5.4, then rewritten by the rule
  engine built from `esm["rules"]` (optional top-level, per RFC §5.2) plus
  any per-model `rules`, then canonicalized again.
- `max_passes` is the per-expression rule-engine budget (§5.2.5).
- With `strict_unrewritten=true` (the default) a rewritten expression that
  still carries a PDE op (`grad`, `div`, `laplacian`, `D`, `bc`) raises
  [`RuleEngineError`](@ref) with code `E_UNREWRITTEN_PDE_OP`. With
  `strict_unrewritten=false` the offending equation/BC is instead marked
  `passthrough: true` and retained verbatim.
- After the pipeline, every equation is classified as either
  `differential` (LHS is `D(x, wrt=<independent_variable>)`) or
  `algebraic` (anything else — includes `produces: algebraic` output
  once rule `produces` lands, and authored non-differential equations).
  The total and per-model algebraic counts are written to the top-level
  `metadata.dae_info` (`{algebraic_equation_count, per_model}`), and
  `metadata.system_class` is set to `"dae"` if any model has at least
  one algebraic equation, else `"ode"`. (Model schemas use
  `additionalProperties: false`, so the counts live only on the
  top-level metadata, not inside each model.)
- If any model contains algebraic equations **and** `dae_support=false`
  (or the environment variable `ESM_DAE_SUPPORT=0`), `discretize` throws
  [`RuleEngineError`](@ref) with code `E_NO_DAE_SUPPORT`. The message
  names the first model and algebraic equation path found. Per RFC §12
  the Julia binding's default strategy is direct DAE hand-off to
  ModelingToolkit, so `dae_support=true` is the normal setting.
- `metadata.discretized_from` is set on the output to the input's
  `metadata.name`.
"""
function discretize(esm::AbstractDict;
                    max_passes::Int = 32,
                    strict_unrewritten::Bool = true,
                    dae_support::Bool = _default_dae_support())::Dict{String,Any}
    out = _deep_native(esm)
    out isa Dict{String,Any} || throw(ArgumentError(
        "discretize: input must be a JSON object / Dict; got $(typeof(esm))"))

    # Parse rules declared at the top level.
    top_rules = _load_rules(get(out, "rules", nothing))

    ctx = _build_rule_context(out)

    models = get(out, "models", nothing)
    if models isa AbstractDict
        for (mname, mraw) in models
            model = mraw isa Dict{String,Any} ? mraw : Dict{String,Any}(String(k) => v for (k, v) in mraw)
            _discretize_model!(String(mname), model, top_rules, ctx,
                               max_passes, strict_unrewritten)
            models[mname] = model
        end
    end

    # RFC §12 — DAE classification + binding contract.
    _apply_dae_contract!(out, dae_support)

    _record_discretized_from!(out)
    return out
end

# Default `dae_support` honors the `ESM_DAE_SUPPORT` env var (RFC §12 says
# bindings MAY expose either an env var or a binding-specific flag; Julia
# exposes both). Any falsy value ("0", "false", "off", "no") disables.
function _default_dae_support()::Bool
    raw = get(ENV, "ESM_DAE_SUPPORT", nothing)
    raw === nothing && return true
    v = lowercase(strip(String(raw)))
    return !(v in ("0", "false", "off", "no"))
end

# ============================================================================
# Rule-context assembly (grids + variables)
# ============================================================================

function _build_rule_context(esm::Dict{String,Any})::RuleContext
    grids = Dict{String,Dict{String,Any}}()
    grids_raw = get(esm, "grids", nothing)
    if grids_raw isa AbstractDict
        for (gname, graw) in grids_raw
            grids[String(gname)] = _extract_grid_meta(graw)
        end
    end

    variables = Dict{String,Dict{String,Any}}()
    models = get(esm, "models", nothing)
    if models isa AbstractDict
        for (_, mraw) in models
            mgrid = _string_or_nothing_any(get(mraw, "grid", nothing))
            vars = get(mraw, "variables", nothing)
            vars isa AbstractDict || continue
            for (vname, vraw) in vars
                meta = Dict{String,Any}()
                if mgrid !== nothing
                    meta["grid"] = mgrid
                end
                shape = get(vraw, "shape", nothing)
                if shape !== nothing
                    meta["shape"] = shape
                end
                loc = get(vraw, "location", nothing)
                if loc !== nothing
                    meta["location"] = String(loc)
                end
                variables[String(vname)] = meta
            end
        end
    end
    return RuleContext(grids, variables)
end

function _extract_grid_meta(graw)::Dict{String,Any}
    meta = Dict{String,Any}()
    dims_raw = get(graw, "dimensions", nothing)
    if dims_raw isa AbstractVector
        spatial = String[]
        periodic = String[]
        nonuniform = String[]
        for d in dims_raw
            name = get(d, "name", nothing)
            name === nothing && continue
            push!(spatial, String(name))
            periodicity = get(d, "periodic", nothing)
            if periodicity === true
                push!(periodic, String(name))
            end
            spacing = get(d, "spacing", nothing)
            if spacing isa AbstractString && String(spacing) in ("nonuniform", "stretched")
                push!(nonuniform, String(name))
            elseif spacing === "nonuniform" || spacing == "nonuniform"
                push!(nonuniform, String(name))
            end
        end
        meta["spatial_dims"] = spatial
        meta["periodic_dims"] = periodic
        meta["nonuniform_dims"] = nonuniform
    end
    return meta
end

_string_or_nothing_any(x) = x === nothing ? nothing : String(x)

# ============================================================================
# Model-level pipeline
# ============================================================================

function _discretize_model!(mname::String, model::Dict{String,Any},
                             top_rules::Vector{Rule}, ctx::RuleContext,
                             max_passes::Int, strict_unrewritten::Bool)
    # Collect rules: model-local overrides/extends top-level.
    local_rules_raw = get(model, "rules", nothing)
    local_rules = _load_rules(local_rules_raw)
    rules = isempty(local_rules) ? top_rules : vcat(top_rules, local_rules)

    # Per-model max_passes override (§5.2.5).
    mp = _lookup_max_passes(model, max_passes)

    # Equations
    eqns = get(model, "equations", nothing)
    if eqns isa AbstractVector
        for (i, eqn_any) in enumerate(eqns)
            eqn = eqn_any isa Dict{String,Any} ? eqn_any :
                Dict{String,Any}(String(k) => v for (k, v) in eqn_any)
            _discretize_equation!("models.$mname.equations[$i]", eqn,
                                   rules, ctx, mp, strict_unrewritten)
            eqns[i] = eqn
        end
    end

    # Boundary conditions (model-level).
    bcs = get(model, "boundary_conditions", nothing)
    if bcs isa AbstractDict
        for (bc_name, bc_any) in bcs
            bc = bc_any isa Dict{String,Any} ? bc_any :
                Dict{String,Any}(String(k) => v for (k, v) in bc_any)
            _discretize_bc!("models.$mname.boundary_conditions.$bc_name",
                             bc, rules, ctx, mp, strict_unrewritten)
            bcs[bc_name] = bc
        end
    end
end

function _lookup_max_passes(model::Dict{String,Any}, default::Int)::Int
    rules_meta = get(model, "rules_config", nothing)
    if rules_meta isa AbstractDict
        mp = get(rules_meta, "max_passes", nothing)
        mp isa Integer && return Int(mp)
    end
    return default
end

# ============================================================================
# Per-equation / per-BC rewrite
# ============================================================================

function _discretize_equation!(path::String, eqn::Dict{String,Any},
                                rules::Vector{Rule}, ctx::RuleContext,
                                max_passes::Int, strict_unrewritten::Bool)
    passthrough = _as_bool(get(eqn, "passthrough", false))
    # Rewrite RHS. The LHS is of the form D(x, wrt=t) or x; we canonicalize it
    # without running the rule engine, so that time derivatives are preserved.
    if haskey(eqn, "rhs")
        eqn["rhs"] = _rewrite_or_passthrough!(
            "$path.rhs", eqn["rhs"], rules, ctx,
            max_passes, strict_unrewritten, passthrough,
            (v) -> (eqn["passthrough"] = v))
    end
    if haskey(eqn, "lhs")
        eqn["lhs"] = _canonicalize_value(eqn["lhs"])
    end
end

function _discretize_bc!(path::String, bc::Dict{String,Any},
                          rules::Vector{Rule}, ctx::RuleContext,
                          max_passes::Int, strict_unrewritten::Bool)
    passthrough = _as_bool(get(bc, "passthrough", false))
    variable = _string_or_nothing_any(get(bc, "variable", nothing))
    kind     = _string_or_nothing_any(get(bc, "kind", nothing))
    side     = _string_or_nothing_any(get(bc, "side", nothing))
    value_raw = get(bc, "value", nothing)

    # Step 1: try matching a `bc` rule pattern (§9.2 — synthetic wrapper).
    # Rules MAY rewrite the BC into an algebraic equation or other form; if
    # no rule matches, we fall through and treat `value` as the BC payload.
    rewritten_via_bc_rule = false
    if variable !== nothing && kind !== nothing && !isempty(rules)
        wrapper = Dict{String,Any}(
            "op" => "bc",
            "args" => Any[variable],
            "kind" => kind,
        )
        if side !== nothing
            wrapper["side"] = side
        end
        if value_raw !== nothing
            push!(wrapper["args"], value_raw)
        end
        bc_expr = parse_expression(wrapper)
        rewrite_out = rewrite(canonicalize(bc_expr), rules, ctx; max_passes=max_passes)
        if !(rewrite_out isa OpExpr && rewrite_out.op == "bc")
            # A rule fired at the bc node; emit the rewritten form as `value`.
            final = canonicalize(rewrite_out)
            if _has_pde_op(final) && !passthrough
                if strict_unrewritten
                    op = _first_pde_op(final)
                    throw(RuleEngineError("E_UNREWRITTEN_PDE_OP",
                        "$path.value still contains PDE op '$op' after rewrite; " *
                        "annotate the BC with 'passthrough: true' to opt out"))
                end
                bc["passthrough"] = true
            end
            bc["value"] = serialize_expression(final)
            rewritten_via_bc_rule = true
        end
    end

    # Step 2: default path — canonicalize the `value` expression and run the
    # rule engine on it. The PDE-op coverage check applies only to the value,
    # never to the synthetic `bc` wrapper.
    if !rewritten_via_bc_rule && value_raw !== nothing
        bc["value"] = _rewrite_or_passthrough!(
            "$path.value", value_raw, rules, ctx,
            max_passes, strict_unrewritten, passthrough,
            (v) -> (bc["passthrough"] = v))
    end
end

function _rewrite_or_passthrough!(path::String, value_raw, rules::Vector{Rule},
                                   ctx::RuleContext, max_passes::Int,
                                   strict_unrewritten::Bool,
                                   passthrough::Bool,
                                   set_passthrough::Function)
    expr = parse_expression(value_raw)
    canon0 = canonicalize(expr)
    rewritten = isempty(rules) ? canon0 :
        rewrite(canon0, rules, ctx; max_passes=max_passes)
    canon1 = canonicalize(rewritten)
    if passthrough
        # Authorial opt-out: keep the rewritten form but do not enforce
        # coverage. `bc` ops with no matching rule fall through here too.
        return serialize_expression(canon1)
    end
    if _has_pde_op(canon1)
        if strict_unrewritten
            op = _first_pde_op(canon1)
            throw(RuleEngineError("E_UNREWRITTEN_PDE_OP",
                "$path still contains PDE op '$op' after rewrite; " *
                "annotate the equation/BC with 'passthrough: true' to opt out"))
        end
        set_passthrough(true)
    end
    return serialize_expression(canon1)
end

function _canonicalize_value(value_raw)
    expr = parse_expression(value_raw)
    return serialize_expression(canonicalize(expr))
end

# ============================================================================
# DAE classification and binding contract (RFC §12)
# ============================================================================

"""
    _apply_dae_contract!(esm, dae_support)

Classify every equation as differential vs algebraic, record the
per-model algebraic count, and either stamp `metadata.system_class`
on the output or throw `E_NO_DAE_SUPPORT`.

An equation is **differential** iff its LHS is an `OpExpr` with `op == "D"`
and `wrt` equal to the enclosing model's independent variable (the
domain's `independent_variable`, defaulting to `"t"`). Every other
equation — authored algebraic constraints, observed equations whose
LHS is a plain variable, equations emitted by a `produces: algebraic`
rule (once that lands) — is algebraic for the purpose of this contract.

This is deliberately inclusive: any binding that claims ODE-only
support and hands off a system to an ODE integrator would drop an
observed-equation LHS just as surely as a true DAE constraint. RFC §12
pins the contract as "hand to a DAE assembler, or abort".
"""
function _apply_dae_contract!(esm::Dict{String,Any}, dae_support::Bool)
    total_algebraic = 0
    per_model = Dict{String,Int}()
    first_algebraic_path::Union{Nothing,String} = nothing

    models = get(esm, "models", nothing)
    if models isa AbstractDict
        indep_by_domain = _indep_var_by_domain(esm)
        for (mname, mraw) in models
            mraw isa AbstractDict || continue
            indep = _model_independent_variable(mraw, indep_by_domain)
            count = 0
            eqns = get(mraw, "equations", nothing)
            if eqns isa AbstractVector
                for (i, eqn) in enumerate(eqns)
                    eqn isa AbstractDict || continue
                    _is_algebraic_equation(eqn, indep) || continue
                    count += 1
                    if first_algebraic_path === nothing
                        first_algebraic_path = "models.$(mname).equations[$i]"
                    end
                end
            end
            total_algebraic += count
            per_model[String(mname)] = count
        end
    end

    # Write classification to top-level metadata so downstream (MTK export,
    # conformance harness) can read it without re-walking. We do not mutate
    # per-model dicts because `Model` has `additionalProperties: false`.
    out_meta = _ensure_dict!(esm, "metadata")
    out_meta["system_class"] = total_algebraic > 0 ? "dae" : "ode"
    out_meta["dae_info"] = Dict{String,Any}(
        "algebraic_equation_count" => total_algebraic,
        "per_model" => Dict{String,Any}(k => v for (k, v) in per_model),
    )

    if total_algebraic > 0 && !dae_support
        where_ = first_algebraic_path === nothing ? "(unknown)" : first_algebraic_path
        throw(RuleEngineError("E_NO_DAE_SUPPORT",
            "discretize() output contains $(total_algebraic) algebraic " *
            "equation(s) (first at $(where_)); DAE support is disabled " *
            "(dae_support=false / ESM_DAE_SUPPORT=0). Enable DAE support " *
            "or remove the algebraic constraint(s). See RFC §12."))
    end
    return esm
end

# Resolve domain -> independent_variable (default "t").
function _indep_var_by_domain(esm::Dict{String,Any})::Dict{String,String}
    out = Dict{String,String}()
    domains = get(esm, "domains", nothing)
    domains isa AbstractDict || return out
    for (dname, draw) in domains
        draw isa AbstractDict || continue
        iv = get(draw, "independent_variable", nothing)
        out[String(dname)] = iv isa AbstractString ? String(iv) : "t"
    end
    return out
end

function _model_independent_variable(model::AbstractDict,
                                      indep_by_domain::Dict{String,String})::String
    dname = get(model, "domain", nothing)
    dname isa AbstractString || return "t"
    return get(indep_by_domain, String(dname), "t")
end

function _is_algebraic_equation(eqn::AbstractDict, indep::String)::Bool
    # An explicit marker wins if present (future `produces: algebraic`
    # output can stamp this directly).
    if haskey(eqn, "produces")
        p = eqn["produces"]
        if p == "algebraic" || (p isa AbstractDict && get(p, "kind", nothing) == "algebraic")
            return true
        end
    end
    if _as_bool(get(eqn, "algebraic", false))
        return true
    end
    lhs_raw = get(eqn, "lhs", nothing)
    lhs_raw === nothing && return true  # malformed — treat as algebraic
    # Parse defensively; if we can't parse the LHS, treat as algebraic so
    # the contract fails closed rather than silently dropping a constraint.
    lhs = try
        parse_expression(lhs_raw)
    catch
        return true
    end
    if lhs isa OpExpr && lhs.op == "D"
        wrt = lhs.wrt
        if wrt === nothing || wrt == indep
            return false
        end
    end
    return true
end

function _ensure_dict!(container::AbstractDict, key::AbstractString)::Dict{String,Any}
    raw = get(container, key, nothing)
    if raw isa Dict{String,Any}
        return raw
    elseif raw isa AbstractDict
        d = Dict{String,Any}(String(k) => v for (k, v) in raw)
        container[key] = d
        return d
    else
        d = Dict{String,Any}()
        container[key] = d
        return d
    end
end

# ============================================================================
# Leftover-PDE-op scan (RFC §11 Step 7)
# ============================================================================

const _DISCRETIZE_PDE_OPS = Set(["grad", "div", "laplacian", "D", "bc"])

function _has_pde_op(e)::Bool
    return _first_pde_op(e) !== nothing
end

function _first_pde_op(e)::Union{String,Nothing}
    if e isa OpExpr
        if e.op == "D"
            # A leading D(var, wrt="t") on the LHS is legitimate; on the RHS of
            # an equation it is a PDE-op (time-derivative placed inside the
            # RHS after some rewrite). Treat it as PDE-op here; the LHS does
            # not flow through this check.
            return "D"
        end
        e.op in _DISCRETIZE_PDE_OPS && return e.op
        for a in e.args
            r = _first_pde_op(a)
            r === nothing || return r
        end
    end
    return nothing
end

# ============================================================================
# Rule loading (permissive: accept array form or keyed-object form)
# ============================================================================

function _load_rules(raw)::Vector{Rule}
    raw === nothing && return Rule[]
    raw isa AbstractDict || raw isa AbstractVector || return Rule[]
    isempty(raw) && return Rule[]
    return parse_rules(raw)
end

# ============================================================================
# Deep-copy of JSON-shaped data + light normalization
# ============================================================================

_deep_native(x::AbstractDict) =
    Dict{String,Any}(String(k) => _deep_native(v) for (k, v) in x)
_deep_native(x::AbstractVector) = Any[_deep_native(v) for v in x]
_deep_native(x::JSON3.Object) =
    Dict{String,Any}(String(k) => _deep_native(x[k]) for k in keys(x))
_deep_native(x::JSON3.Array) = Any[_deep_native(v) for v in x]
_deep_native(x) = x

_as_bool(x::Bool) = x
_as_bool(x::AbstractString) = (lowercase(String(x)) == "true")
_as_bool(::Nothing) = false
_as_bool(x) = x == true

# ============================================================================
# Metadata: discretized_from provenance
# ============================================================================

function _record_discretized_from!(esm::Dict{String,Any})
    meta_raw = get(esm, "metadata", nothing)
    meta = meta_raw isa Dict{String,Any} ? meta_raw :
        (meta_raw isa AbstractDict ?
            Dict{String,Any}(String(k) => v for (k, v) in meta_raw) :
            Dict{String,Any}())
    src_name = get(meta, "name", nothing)
    # `discretized_from` lives under metadata as a sub-object so we can later
    # add rule-engine provenance (version, fixture hash, etc.) without spec
    # churn. For now: name + input-hash placeholder.
    provenance = Dict{String,Any}()
    if src_name !== nothing
        provenance["name"] = String(src_name)
    end
    meta["discretized_from"] = provenance
    tags = get(meta, "tags", nothing)
    if tags isa AbstractVector
        if !("discretized" in (String(t) for t in tags))
            push!(tags, "discretized")
        end
    else
        meta["tags"] = Any["discretized"]
    end
    esm["metadata"] = meta
    return esm
end
