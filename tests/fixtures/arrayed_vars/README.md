# Arrayed-variable fixtures

Test fixtures for variables with optional `shape` and `location` fields
(discretization RFC §10.2). Each binding must round-trip these files through
parse → serialize → parse without losing the two new fields.

- `scalar_no_shape.esm` — the pre-0.2 form: `shape` and `location` absent. Must
  keep parsing as a plain scalar variable (regression guard).
- `scalar_explicit.esm` — `shape` set to the empty list; still scalar but
  explicit. Bindings must preserve the empty-list form rather than normalizing
  it away.
- `one_d.esm` — a 1-D cell-centered variable on an `x` dimension.
- `two_d_faces.esm` — two 2-D variables, one `cell_center` and one on the
  `x_face` staggering, referencing the same `x`,`y` domain.
- `vertex_located.esm` — a 2-D variable whose staggering is `vertex`.

These fixtures exercise the minimum coverage required by the bead:
scalar, 1-D, 2-D, and vertex-located variables.
