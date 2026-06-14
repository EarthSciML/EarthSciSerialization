# Scheme type definitions per discretization RFC §7 / §7.9.
#
# Loaded before `rule_engine.jl` so that `RuleContext` can carry a
# `schemes::Dict{String,AbstractScheme}` registry. The actual parsing,
# materialization, and expansion live in `scheme_expansion.jl`, which is
# loaded after `rule_engine.jl` (it depends on rule-engine helpers like
# `apply_bindings`, `_parse_expr`, `_is_pvar_string`, …).

"""
    abstract type AbstractScheme end

Abstract base for `discretizations.<name>` scheme entries (RFC §7).
Concrete subtypes: [`Scheme`](@ref) (§7.1 flat stencil),
[`MultiOutputStencilScheme`](@ref) (§7.9 multi-output).
"""
abstract type AbstractScheme end

"""
    abstract type Selector end

Abstract base for §7.2 neighbor selectors. Concrete subtypes:
[`CartesianSelector`](@ref). Cubed-sphere `panel`, unstructured
`indirect`, and unstructured `reduction` selectors are out of scope for
the cartesian foundation bead and will land in follow-up work
(esm-57f / esm-bpr).
"""
abstract type Selector end

"""
    CartesianSelector(axis::String, offset::Int)

`{kind: "cartesian", axis, offset}` per RFC §7.2 row 1. `axis` is either
a literal cartesian dimension name or a pattern-variable reference (e.g.
`"\$x"`); the pattern-variable form is resolved against the rule's
bindings at expansion time. `offset` is the integer displacement along
that axis.
"""
struct CartesianSelector <: Selector
    axis::String
    offset::Int
end

"""
    StencilEntry(selector::Selector, coeff::Expr)

One row of a scheme's `stencil` array (RFC §7.1 / §7.2). `coeff` is the
symbolic coefficient AST; pattern variables bound by the triggering
rule (and by §7.1.1 `\$target` components, which are not pvars but
reserved local names) flow into `coeff` by name during expansion.
"""
struct StencilEntry
    selector::Selector
    coeff::Expr
end

"""
    Scheme(name, applies_to, grid_family, combine, stencil, accuracy,
           order, requires_locations, emits_location, target_binding,
           requires)

A `discretizations.<name>` entry per RFC §7.1. Held verbatim across
parse/expansion; a scheme is consulted only when a rule's replacement
form is `use: <name>` (RFC §5.2 / §7.2.1).

`requires` maps local names used inside `stencil` coefficients to provider
references of the form `"<sibling-scheme>#<output>"` per RFC §7.9.
"""
struct Scheme <: AbstractScheme
    name::String
    applies_to::Expr
    grid_family::String
    combine::String
    stencil::Vector{StencilEntry}
    accuracy::Union{String,Nothing}
    order::Union{Int,Nothing}
    requires_locations::Vector{String}
    emits_location::Union{String,Nothing}
    target_binding::String
    requires::Dict{String,String}
end

"""
    MultiOutputStencilScheme(name, applies_to, grid_family, outputs, stencil,
                             primary, emits_location, accuracy, order,
                             requires_locations, target_binding)

A `discretizations.<name>` entry with `kind: "multi_output_stencil"` per RFC §7.9.
Emits multiple named output fields from one stencil application (e.g. PPM
reconstruction producing `q_left_edge` and `q_right_edge`).

Fields:
- `outputs`: ordered list of output names; equals the key set of `stencil`.
- `stencil`: Dict keyed by output name; each value is a §7.1 stencil-entry list.
- `primary`: output name substituted at the match site; `nothing` for provider-only.
"""
struct MultiOutputStencilScheme <: AbstractScheme
    name::String
    applies_to::Expr
    grid_family::String
    outputs::Vector{String}
    stencil::Dict{String,Vector{StencilEntry}}
    primary::Union{String,Nothing}
    emits_location::Union{String,Nothing}
    accuracy::Union{String,Nothing}
    order::Union{Int,Nothing}
    requires_locations::Vector{String}
    target_binding::String
end
