"""
MTK → ESM export scaffolder (Phase 1 migration tooling, gt-dod2).

This file defines the public stubs for `mtk2esm`, the forward-direction
serializer that walks a ModelingToolkit system and emits a schema-valid ESM
`Dict`. The real implementations live in the MTK and Catalyst extensions
because they require those packages to be loaded — this file only declares
the stubs and the `GapReport` type used to collect unsupported-construct
warnings.

See `scripts/roundtrip.jl` for the validator CLI that exercises this path
as the EarthSciModels migration acceptance gate.
"""

"""
    GapReport

Structured record of schema-gap constructs encountered while exporting an
MTK system to ESM. The migration tool uses these to attach `TODO_GAP`
notes and to emit `@warn`s listing the gap IDs so callers know which
downstream beads must land before their model can be migrated cleanly.

Each entry carries:
- `bead_id`: the upstream bead tracking the gap (or `"unknown"`)
- `description`: human-readable one-liner (shown in warnings and JSON)
- `where`: location hint (variable or equation index) for the user
"""
struct GapReport
    bead_id::String
    description::String
    where::String
end

"""
    mtk2esm(sys; metadata=(;))

Export a ModelingToolkit system to an ESM-format `Dict{String,Any}` suitable
for JSON serialization. The concrete dispatch lives in
`EarthSciSerializationMTKExt` / `EarthSciSerializationCatalystExt`.

# Arguments
- `sys`: an MTK `System` / `ODESystem` / `ReactionSystem` / `SDESystem` /
  `NonlinearSystem` / `PDESystem`, or a Catalyst `ReactionSystem`.

# Keyword arguments
- `metadata`: NamedTuple-like of migration metadata. Recognized fields:
  `tags` (`Vector{String}`), `source_ref` (`String`), `description`
  (`String`), `authors` (`Vector{String}`), `version` (`String`),
  `name` (overrides `nameof(sys)`).

# Returns
A `Dict{String,Any}` shaped like a full ESM file: `esm`, `metadata`, and
either `models.<name>` or `reaction_systems.<name>`. Any schema-gap
constructs produce `TODO_GAP` entries inside the emitted component's
`metadata.notes` field plus an `@warn` listing the gaps.

Raises a clear `ArgumentError` if the MTK/Catalyst extension hasn't been
loaded — the stub in `src/mtk_export.jl` has no way to walk an MTK system
on its own.
"""
function mtk2esm end

"""
    mtk2esm_gaps(sys)

Internal helper: returns a `Vector{GapReport}` for any schema-gap constructs
found in `sys` without running the full export. Useful for pre-flight
checks. Extensions override this with concrete implementations.
"""
function mtk2esm_gaps end
