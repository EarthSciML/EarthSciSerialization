# Scheme parsing + expansion per discretization RFC §7 / §7.2 / §7.2.1.
#
# Type definitions (`Selector`, `CartesianSelector`, `StencilEntry`,
# `Scheme`) live in `scheme_types.jl` (loaded before `rule_engine.jl`).
# This file holds the parser for `discretizations.<name>` blocks plus the
# `materialize` / `expand_scheme` runtime invoked by the rule engine
# when a rule's replacement is `use: <scheme>`.
#
# Cartesian-family foundation only (bead esm-j1u). Cubed-sphere `panel`
# and unstructured `indirect` / `reduction` selectors land in follow-up
# beads (esm-57f, esm-bpr).

# ============================================================================
# Parsing — discretizations.<name>
# ============================================================================

"""
    parse_scheme(name, raw) -> Scheme

Build a [`Scheme`](@ref) from a decoded JSON object. Required fields:
`applies_to`, `grid_family`, `stencil`. `combine` defaults to `"+"`;
`target_binding` defaults to `"\$target"`. Selector kinds are
discriminated by `selector.kind`. Cartesian selectors require `axis`
(string, possibly a pvar reference) and `offset` (integer).
"""
function parse_scheme(name::AbstractString, raw)::Scheme
    sname = String(name)
    _is_dict_like(raw) || throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $sname: must be an object"))

    applies_to_raw = _getkey(raw, "applies_to"; default=nothing)
    applies_to_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $sname: missing required field `applies_to`"))
    applies_to = _parse_expr(applies_to_raw)

    grid_family_raw = _getkey(raw, "grid_family"; default=nothing)
    grid_family_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $sname: missing required field `grid_family`"))
    grid_family = String(grid_family_raw)
    grid_family in ("cartesian", "cubed_sphere", "unstructured") ||
        throw(RuleEngineError("E_SCHEME_PARSE",
            "scheme $sname: unknown grid_family `$grid_family` " *
            "(closed set: cartesian, cubed_sphere, unstructured)"))

    combine_raw = _getkey(raw, "combine"; default="+")
    combine = String(combine_raw)
    combine in ("+", "*", "min", "max") || throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $sname: combine `$combine` must be one of +, *, min, max"))

    stencil_raw = _getkey(raw, "stencil"; default=nothing)
    stencil_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $sname: missing required field `stencil`"))
    stencil_raw isa AbstractVector || throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $sname: `stencil` must be an array"))
    stencil = StencilEntry[_parse_stencil_entry(sname, grid_family, e)
                           for e in stencil_raw]
    isempty(stencil) && throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $sname: `stencil` must contain at least one entry"))

    accuracy_raw = _getkey(raw, "accuracy"; default=nothing)
    accuracy = accuracy_raw === nothing ? nothing : String(accuracy_raw)

    order_raw = _getkey(raw, "order"; default=nothing)
    order = nothing
    if order_raw !== nothing
        order_raw isa Integer || throw(RuleEngineError("E_SCHEME_PARSE",
            "scheme $sname: `order` must be an integer"))
        order = Int(order_raw)
        order > 0 || throw(RuleEngineError("E_SCHEME_PARSE",
            "scheme $sname: `order` must be a positive integer, got $order"))
    end

    requires_locations_raw = _getkey(raw, "requires_locations"; default=nothing)
    requires_locations = String[]
    if requires_locations_raw !== nothing
        requires_locations_raw isa AbstractVector || throw(RuleEngineError(
            "E_SCHEME_PARSE",
            "scheme $sname: `requires_locations` must be an array of strings"))
        requires_locations = String[String(s) for s in requires_locations_raw]
    end

    emits_location_raw = _getkey(raw, "emits_location"; default=nothing)
    emits_location = emits_location_raw === nothing ? nothing :
        String(emits_location_raw)

    target_binding_raw = _getkey(raw, "target_binding"; default="\$target")
    target_binding = String(target_binding_raw)

    return Scheme(sname, applies_to, grid_family, combine, stencil,
                  accuracy, order, requires_locations,
                  emits_location, target_binding)
end

function _parse_stencil_entry(scheme_name::String, grid_family::String, raw)::StencilEntry
    _is_dict_like(raw) || throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $scheme_name: stencil entry must be an object"))
    sel_raw = _getkey(raw, "selector"; default=nothing)
    sel_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $scheme_name: stencil entry missing required field `selector`"))
    coeff_raw = _getkey(raw, "coeff"; default=nothing)
    coeff_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $scheme_name: stencil entry missing required field `coeff`"))
    sel = _parse_selector(scheme_name, grid_family, sel_raw)
    coeff = _parse_expr(coeff_raw)
    return StencilEntry(sel, coeff)
end

function _parse_selector(scheme_name::String, grid_family::String, raw)::Selector
    _is_dict_like(raw) || throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $scheme_name: selector must be an object"))
    kind_raw = _getkey(raw, "kind"; default=nothing)
    kind_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $scheme_name: selector missing required field `kind`"))
    kind = String(kind_raw)
    if kind == "cartesian"
        grid_family == "cartesian" || throw(RuleEngineError("E_SCHEME_PARSE",
            "scheme $scheme_name: cartesian selector incompatible with " *
            "grid_family=$grid_family"))
        axis_raw = _getkey(raw, "axis"; default=nothing)
        axis_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
            "scheme $scheme_name: cartesian selector missing `axis`"))
        offset_raw = _getkey(raw, "offset"; default=nothing)
        offset_raw === nothing && throw(RuleEngineError("E_SCHEME_PARSE",
            "scheme $scheme_name: cartesian selector missing `offset`"))
        offset_raw isa Integer || throw(RuleEngineError("E_SCHEME_PARSE",
            "scheme $scheme_name: cartesian selector `offset` must be integer"))
        return CartesianSelector(String(axis_raw), Int(offset_raw))
    end
    # Other selector kinds are deferred to follow-up beads.
    throw(RuleEngineError("E_SCHEME_PARSE",
        "scheme $scheme_name: selector kind `$kind` not yet supported " *
        "(cartesian foundation only; cubed_sphere/unstructured land later)"))
end

"""
    parse_schemes(raw) -> Dict{String,Scheme}

Parse the top-level `discretizations` block into a name-keyed registry
of [`Scheme`](@ref). Accepts the JSON-object-keyed-by-name form. Returns
an empty dict for `nothing` / empty / missing input.
"""
function parse_schemes(raw)::Dict{String,Scheme}
    out = Dict{String,Scheme}()
    raw === nothing && return out
    _is_dict_like(raw) || return out
    for (k, v) in _iterate_dict(raw)
        sk = String(k)
        # Skip non-stencil entries (e.g. dimensional_split composites under §7.5)
        # for the cartesian foundation. They land on a follow-up bead.
        kind_raw = _is_dict_like(v) ? _getkey(v, "kind"; default=nothing) : nothing
        if kind_raw !== nothing && String(kind_raw) != "stencil"
            continue
        end
        out[sk] = parse_scheme(sk, v)
    end
    return out
end

# ============================================================================
# Materialize — neighbor selector → list of index expressions (§7.2 row 1)
# ============================================================================

# Canonical $target component names for cartesian grids per RFC §7.1.1.
const _CARTESIAN_CANONICAL_NAMES = ("i", "j", "k", "l", "m")

"""
    materialize(sel::CartesianSelector, target::Vector{Expr}, axis_pos::Int) -> Vector{Expr}

Materialize a cartesian selector at the given target index list per
RFC §7.2 row 1: replace the component at `axis_pos` with
`{op: "+", args: [target[axis_pos], offset]}`; pass the rest through
unchanged. `axis_pos` is the 1-based position of the selector's axis
within the grid's dimension-declaration order (per §7.1.1's "dimension
name → \$target component" mapping).
"""
function materialize(sel::CartesianSelector, target::Vector{Expr},
                     axis_pos::Int)::Vector{Expr}
    1 <= axis_pos <= length(target) || throw(RuleEngineError(
        "E_SCHEME_MATERIALIZE",
        "cartesian selector axis position $axis_pos out of range " *
        "[1,$(length(target))]"))
    out = Vector{Expr}(undef, length(target))
    for (i, comp) in enumerate(target)
        if i == axis_pos
            out[i] = OpExpr("+", Expr[comp, IntExpr(sel.offset)])
        else
            out[i] = comp
        end
    end
    return out
end

# ============================================================================
# Scheme expansion — entry point invoked from the rule engine
# ============================================================================

"""
    expand_scheme(scheme, bindings, ctx) -> Expr

Apply a §7 scheme at the rule's bound subtree. `bindings` carries the
pattern-variable substitution from rule matching (`\$u`, `\$x`, `\$target`,
…). `ctx.grids` and `ctx.variables` provide the grid metadata needed to
resolve canonical \$target component names (§7.1.1) and to choose the
operand variable's spatial-dim order.

Returns the lowered AST per §7.2:
`combine_k(coeff_k * operand_ref_k)`.

Throws [`RuleEngineError`](@ref) with code `E_SCHEME_MISMATCH` when the
scheme's `applies_to` cannot be reconciled with the rule's bindings, or
`E_SCHEME_MATERIALIZE` when target/grid metadata is insufficient to
resolve a selector.
"""
function expand_scheme(scheme::Scheme,
                       bindings::Dict{String,Expr},
                       ctx::RuleContext)::Expr
    # Recover the operand variable name. The scheme's `applies_to` is a
    # depth-1 pattern (§7.2.1); for the cartesian foundation it always has
    # the shape `{op: <op>, args: ["$u"], dim: "$x"}`, so the operand is
    # the first arg's pvar binding.
    operand_var = _scheme_operand(scheme, bindings)

    grid_name = _operand_grid(operand_var, ctx)
    spatial_dims = _grid_spatial_dims(grid_name, ctx)
    target = _cartesian_target(spatial_dims)

    terms = Expr[_expand_stencil_entry(scheme, e, operand_var, target,
                                       spatial_dims, bindings)
                 for e in scheme.stencil]

    if length(terms) == 1
        return terms[1]
    end
    # `combine` over the term list. Spec §7 defines "+", "*" as variadic n-ary
    # combinators; "min" / "max" reduce sequentially via the same op name.
    return OpExpr(scheme.combine, terms)
end

function _scheme_operand(scheme::Scheme, bindings::Dict{String,Expr})::Expr
    pat = scheme.applies_to
    pat isa OpExpr || throw(RuleEngineError("E_SCHEME_MISMATCH",
        "scheme $(scheme.name): applies_to must be an op node"))
    isempty(pat.args) && throw(RuleEngineError("E_SCHEME_MISMATCH",
        "scheme $(scheme.name): applies_to has no args; cannot identify operand"))
    operand_pat = pat.args[1]
    operand_pat isa VarExpr && _is_pvar(operand_pat) || throw(RuleEngineError(
        "E_SCHEME_MISMATCH",
        "scheme $(scheme.name): applies_to first arg must be a pattern variable " *
        "(e.g. \$u)"))
    pname = operand_pat.name
    haskey(bindings, pname) || throw(RuleEngineError("E_SCHEME_MISMATCH",
        "scheme $(scheme.name): operand pattern variable $pname not bound by " *
        "rule pattern"))
    return bindings[pname]
end

function _operand_grid(operand::Expr, ctx::RuleContext)::String
    name = operand isa VarExpr ? operand.name : nothing
    name === nothing && throw(RuleEngineError("E_SCHEME_MATERIALIZE",
        "operand of a cartesian scheme must be a bare variable reference; " *
        "complex AST operands are not yet supported"))
    meta = get(ctx.variables, name, nothing)
    meta === nothing && throw(RuleEngineError("E_SCHEME_MATERIALIZE",
        "operand variable `$name` not present in RuleContext.variables"))
    grid = get(meta, "grid", nothing)
    grid === nothing && throw(RuleEngineError("E_SCHEME_MATERIALIZE",
        "operand variable `$name` has no associated grid metadata"))
    return String(grid)
end

function _grid_spatial_dims(grid_name::String, ctx::RuleContext)::Vector{String}
    meta = get(ctx.grids, grid_name, nothing)
    meta === nothing && throw(RuleEngineError("E_SCHEME_MATERIALIZE",
        "grid `$grid_name` not present in RuleContext.grids"))
    dims = get(meta, "spatial_dims", nothing)
    (dims isa AbstractVector && !isempty(dims)) || throw(RuleEngineError(
        "E_SCHEME_MATERIALIZE",
        "grid `$grid_name` has no spatial_dims metadata"))
    return String[String(d) for d in dims]
end

function _cartesian_target(spatial_dims::Vector{String})::Vector{Expr}
    n = length(spatial_dims)
    n <= length(_CARTESIAN_CANONICAL_NAMES) || throw(RuleEngineError(
        "E_SCHEME_MATERIALIZE",
        "cartesian schemes support up to $(length(_CARTESIAN_CANONICAL_NAMES)) " *
        "dimensions per RFC §7.1.1; grid has $n"))
    return Expr[VarExpr(_CARTESIAN_CANONICAL_NAMES[i]) for i in 1:n]
end

function _expand_stencil_entry(scheme::Scheme, entry::StencilEntry,
                               operand_var::Expr, target::Vector{Expr},
                               spatial_dims::Vector{String},
                               bindings::Dict{String,Expr})::Expr
    sel = entry.selector
    sel isa CartesianSelector || throw(RuleEngineError("E_SCHEME_MATERIALIZE",
        "scheme $(scheme.name): non-cartesian selectors not supported in this " *
        "binding yet"))
    axis_name = _resolve_axis_pvar(scheme, sel.axis, bindings)
    axis_pos = findfirst(==(axis_name), spatial_dims)
    axis_pos === nothing && throw(RuleEngineError("E_SCHEME_MATERIALIZE",
        "scheme $(scheme.name): selector axis `$axis_name` not in grid " *
        "spatial_dims $(spatial_dims)"))

    indices = materialize(sel, target, axis_pos)
    operand_ref = OpExpr("index", Expr[operand_var, indices...])

    coeff = apply_bindings(entry.coeff, bindings)

    return OpExpr("*", Expr[coeff, operand_ref])
end

function _resolve_axis_pvar(scheme::Scheme, axis::String,
                            bindings::Dict{String,Expr})::String
    if _is_pvar_string(axis)
        haskey(bindings, axis) || throw(RuleEngineError("E_SCHEME_MISMATCH",
            "scheme $(scheme.name): axis pattern variable `$axis` is not bound " *
            "by rule pattern"))
        v = bindings[axis]
        v isa VarExpr || throw(RuleEngineError("E_SCHEME_MISMATCH",
            "scheme $(scheme.name): axis pattern variable `$axis` must bind a " *
            "bare name; got $(typeof(v))"))
        return v.name
    end
    return axis
end
