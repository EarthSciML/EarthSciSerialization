# Scheme type definitions per discretization RFC §7.
#
# Loaded before `rule_engine.jl` so that `RuleContext` can carry a
# `schemes::Dict{String,Scheme}` registry. The actual parsing,
# materialization, and expansion live in `scheme_expansion.jl`, which is
# loaded after `rule_engine.jl` (it depends on rule-engine helpers like
# `apply_bindings`, `_parse_expr`, `_is_pvar_string`, …).

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
           order, requires_locations, emits_location, target_binding)

A `discretizations.<name>` entry per RFC §7.1. Held verbatim across
parse/expansion; a scheme is consulted only when a rule's replacement
form is `use: <name>` (RFC §5.2 / §7.2.1).
"""
struct Scheme
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
end
