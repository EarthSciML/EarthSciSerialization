# RFC — Language-agnostic Discretization in ESM

**Status:** Draft
**Bead:** gt-dq0f
**Affects spec version:** 0.1.0 → 0.2.0 (additive)
**Scope:** Spatial discretization only. Time integration remains a runtime concern.

---

## 1. Motivation

ESM today fully specifies continuous PDE systems (models, reactions, coupling,
domains, interfaces) but stops short of describing *how* those PDEs are
discretized in space. Every consumer must defer to a language-specific engine
— currently MethodOfLines.jl (rectangular grids) and EarthSciDiscretizations.jl
(cubed sphere FV). Python, Rust, Go, and TS bindings therefore cannot produce
an ODE/DAE system from a `.esm` file without re-implementing every discretization
in every language, and the Julia implementations have already diverged in
coverage and numerics.

The goal of this RFC is to extend the existing ESM format with a complete,
language-agnostic specification of spatial discretization that:

1. Covers the three grid families that currently matter to earth-system modeling:
   logically-rectangular (MOL), cubed-sphere panel (FV3), and unstructured
   Voronoi (MPAS).
2. Lets any binding turn a PDE `.esm` file into a discretized ODE/DAE system
   without calling into Julia.
3. Emits bitwise-identical expression output across bindings on the conformance
   harness.
4. Reuses the existing expression AST, `substitute` / `evaluate` /
   `free_variables` / `simplify` primitives, `parameters`, domains, and BCs.
5. Does **not** introduce a second file format.

## 2. Non-goals

- Time integration. ODE/DAE systems produced by discretization are handed to
  MTK, SciPy, DifferentialEquations.jl, etc. Time-stepping schemes, implicit
  solvers, operator-splitting, and adaptive timestep control are out of scope.
- New numerical methods. The RFC specifies a *serialization* for existing
  discretization strategies, not new ones.
- Runtime performance tuning. Sparsity patterns, tile sizes, vectorization
  hints, and GPU mappings are runtime concerns and are explicitly excluded from
  the schema (cf. §4.3.6 of the existing spec).
- Grid *generation* algorithms. The schema describes how metric arrays are
  *obtained* (analytic expression or opaque loader); it does not prescribe the
  algorithms that produce them.

## 3. Architectural commitment

Extend the existing ESM top-level object with three new sections:

| Section | Purpose |
|---|---|
| `grids` | Topology and metric-array declarations for a spatial grid |
| `discretizations` | Named numerical schemes (stencil templates) |
| `rules` | Pattern-match rewrite rules from PDE operators to schemes |

Discretization is the composition *rules ∘ discretizations ∘ grids*: a rule
matches a PDE operator on a variable whose `domain` uses a particular grid and
rewrites it with a scheme, producing a discretized expression that references
the grid's metric arrays as *indexed variables*.

No new file format, no new top-level type beyond the three sections above, and
no changes to the existing `models` / `reaction_systems` / `coupling` /
`domains` / `interfaces` semantics.

## 4. Unifying abstraction: the neighbor selector

All three target grid families reduce to a single stencil template:

```
output[target] = Σ_k coeff_k · var[neighbor_k(target)]
```

They differ only in how `neighbor_k` is addressed. The RFC introduces **one**
selector abstraction with three concrete forms:

| Form | Fields | Grid family |
|---|---|---|
| `cartesian` | `axis`, `offset` | Logically-rectangular (MOL) |
| `panel` | `panel_rel`, `di`, `dj` (resolved via panel-connectivity table) | Cubed sphere (FV3) |
| `indirect` | `table`, `index_expr` | Unstructured Voronoi (MPAS) |

Exactly one selector kind lives inside a stencil-template entry, chosen by the
grid family the scheme is declared for. Rules attach a scheme to a grid at
application time, so a scheme's selector kind must be compatible with the
grid's declared family.

## 5. AST extensions

The following additions to §4 of the spec are required. They are additive and
do not alter the meaning of any existing node.

### 5.1 Indexed variable node (`idx`)

```json
{ "op": "idx", "var": "<name>", "indices": [<expr>, ...] }
```

`idx` references a single element of an array-valued variable or metric array.
It is the scalar-world counterpart to `index` (§4.3.3): `index` operates inside
`arrayop.expr`, where index symbols are local; `idx` operates in any expression
context, and its `indices` are ordinary `Expression` values (integer literals,
parameter references, or composite expressions such as `{op:"+", args:["i",1]}`).

The five bindings must extend the core traversal primitives:

- `substitute(expr, map)` — recurse into `var` (if `var` is a key in `map`) and
  into each entry of `indices`.
- `free_variables(expr)` — collect `var` plus `free_variables(indices[k])`.
- `evaluate(expr, env)` — look up `env[var]`, evaluate each index, perform
  array access.
- `simplify(expr)` — recurse into `indices`; the node itself has no arithmetic
  identities.

**Validation rule.** `var` must resolve to either (a) a declared model/reaction
variable that has been tagged with a grid (see §6.4), or (b) a grid metric
array declared under the variable's grid. `indices.length` must match the
grid's logical rank for (a) and the metric array's declared rank for (b).

### 5.2 Pattern variables and rule engine

Rewrite rules cannot be expressed with positional `substitute`. The RFC adds a
small pattern sub-language, analogous to SymbolicUtils `@rule`, that is itself
serializable:

| Field | Type | Purpose |
|---|---|---|
| `pattern` | AST with `$`-prefixed pattern variables | Matches an input expression |
| `where` | array of guard objects | Optional constraints on pattern variables |
| `replacement` | AST over the same pattern variables | Output expression |

Pattern variables are strings prefixed by `$`: `"$u"`, `"$x"`. A guard object
constrains a pattern variable to a class:

| Guard | Example | Meaning |
|---|---|---|
| `var_is_spatial_dim_of` | `{guard: "var_is_spatial_dim_of", pvar: "$x", grid: "$g"}` | `$x` must name a spatial dimension of grid `$g` |
| `var_location_is` | `{guard: "var_location_is", pvar: "$u", location: "cell_center"}` | `$u` must carry the given staggered location (§6.4) |
| `var_has_grid` | `{guard: "var_has_grid", pvar: "$u", grid: "$g"}` | `$u` must be bound to grid `$g` |
| `dim_is_periodic` | `{guard: "dim_is_periodic", pvar: "$x"}` | `$x`'s dimension has periodic BC |

Guards are combined by AND. The guard vocabulary is small and closed — new
guards require a spec version bump. This keeps the pattern-matcher trivially
reimplementable in each binding (tree equality plus a dozen type checks).

The rule engine is a two-pass fixed-point loop: each rule is tried at every
subtree, top-down, until no rule fires. Order of application is deterministic:
rules are applied in the order listed under `rules`; within one pass, earlier
subtrees are rewritten before later ones. This is sufficient for the schemes
enumerated in §8 and produces bitwise-identical output across bindings.

### 5.3 New calculus ops — none required

`D`, `grad`, `div`, `laplacian` already exist. No additional continuous-math
ops are introduced. Ghost-cell addressing and boundary regions are expressed
through `idx` plus rule replacements; no new op for "boundary region" is
defined in the MVP slice. (Re-evaluated after step 2 of the rollout.)

## 6. Schema — `grids`

### 6.1 Top-level

```json
{
  "grids": {
    "atmos_rect": { "family": "cartesian", ... },
    "mpas_cvmesh": { "family": "unstructured", ... },
    "cubed_c48":   { "family": "cubed_sphere", ... }
  }
}
```

Each key is a grid name; the value is an object whose `family` field selects
one of three schemas below. All grids support the following common fields:

| Field | Required | Description |
|---|---|---|
| `family` | ✓ | `"cartesian"`, `"cubed_sphere"`, or `"unstructured"` |
| `dimensions` | ✓ | Ordered list of logical dimension names |
| `locations` | | Declared stagger locations (see §6.4) |
| `metric_arrays` | | Declarations of metric arrays (see §6.5) |
| `parameters` | | Ordinary ESM parameter entries (see §6.6) |
| `domain` | | Name of the `domains` entry this grid refines (optional) |

The `parameters` block **reuses** the existing ESM `parameters` schema (§6.2
of the spec) verbatim. Grid-level parameters are visible to `substitute`,
`free_variables`, and the conformance harness without any new machinery.

### 6.2 Family: `cartesian`

```json
{
  "family": "cartesian",
  "dimensions": ["x", "y", "z"],
  "extents": {
    "x": { "n": "Nx", "spacing": "uniform" },
    "y": { "n": "Ny", "spacing": "uniform" },
    "z": { "n": "Nz", "spacing": "nonuniform" }
  },
  "locations": ["cell_center", "x_face", "y_face", "z_face"],
  "metric_arrays": {
    "dx": { "rank": 1, "dim": "x", "generator": { "kind": "expression",
             "expr": { "op": "/", "args": [ { "op": "-", "args": ["x_max", "x_min"] }, "Nx" ] } } },
    "dz": { "rank": 1, "dim": "z", "generator": { "kind": "loader",
             "name": "csv_mesh", "params": { "path": "zlev.csv" } } }
  },
  "parameters": {
    "Nx": { "value": 64 }, "Ny": { "value": 64 }, "Nz": { "value": 32 },
    "x_min": { "value": 0.0 }, "x_max": { "value": 1.0 }
  }
}
```

- `extents[<dim>].n` — expression referencing a parameter giving the count
  along that dimension.
- `extents[<dim>].spacing` — `"uniform"` lets rules assume a scalar `dx`;
  `"nonuniform"` forces the rule to emit `dx[i]` (indexed) references.

### 6.3 Family: `unstructured`

```json
{
  "family": "unstructured",
  "dimensions": ["cell", "edge", "vertex"],
  "locations": ["cell_center", "edge_normal", "vertex"],
  "connectivity": {
    "cellsOnEdge":   { "shape": ["nEdges", 2],    "rank": 2 },
    "edgesOnCell":   { "shape": ["nCells", "maxEdges"], "rank": 2 },
    "verticesOnEdge":{ "shape": ["nEdges", 2],    "rank": 2 }
  },
  "metric_arrays": {
    "dcEdge":  { "rank": 1, "dim": "edge", "generator": { "kind": "loader", "name": "mpas_mesh", "params": { "field": "dcEdge" } } },
    "dvEdge":  { "rank": 1, "dim": "edge", "generator": { "kind": "loader", "name": "mpas_mesh", "params": { "field": "dvEdge" } } },
    "areaCell":{ "rank": 1, "dim": "cell", "generator": { "kind": "loader", "name": "mpas_mesh", "params": { "field": "areaCell" } } }
  },
  "parameters": {
    "nCells": { "value": "from_loader" },
    "nEdges": { "value": "from_loader" },
    "maxEdges": { "value": 10 }
  }
}
```

`connectivity[<name>]` declares an integer table addressable by rules. Rules
that use the `indirect` selector name one of these tables in
`selector.table`.

### 6.4 Family: `cubed_sphere`

```json
{
  "family": "cubed_sphere",
  "dimensions": ["panel", "i", "j"],
  "extents": { "panel": { "n": 6 }, "i": { "n": "Nc" }, "j": { "n": "Nc" } },
  "locations": ["cell_center", "i_edge", "j_edge", "vertex"],
  "panel_connectivity": {
    "neighbors": { "shape": [6, 4], "rank": 2 },
    "axis_flip": { "shape": [6, 4], "rank": 2 }
  },
  "metric_arrays": {
    "dxC":  { "rank": 3, "dims": ["panel", "i", "j"], "generator": { "kind": "expression", "expr": "<analytic on cube>" } },
    "dyC":  { "rank": 3, "dims": ["panel", "i", "j"], "generator": { "kind": "expression", "expr": "<analytic on cube>" } },
    "area": { "rank": 3, "dims": ["panel", "i", "j"], "generator": { "kind": "expression", "expr": "<analytic on cube>" } }
  },
  "parameters": { "Nc": { "value": 48 } }
}
```

`panel_connectivity.neighbors[p, side]` gives the neighboring panel index for
each (panel, side ∈ {−i, +i, −j, +j}); `axis_flip[p, side]` carries the local
axis transformation applied when crossing that seam. Rules that use the
`panel` selector consult these tables.

### 6.5 Metric-array generators

A metric array's contents come from exactly one of:

| Kind | Fields | Semantics |
|---|---|---|
| `expression` | `expr` | An ordinary ESM expression; all free variables must be grid `parameters`. The metric is computed at discretization time. |
| `loader` | `name`, `params` | Names a registered loader (§8 of the spec) whose output provides the array. Grid JSON never contains bulk values. |

Per design decision (1), analytic grids use `expression`; irregular grids
(MPAS) use `loader`. This matches existing loader semantics and keeps `.esm`
files diff-friendly.

### 6.6 Parameter flow

Grid generator parameters are ordinary ESM parameters (decision 2). A
rectangular grid with `Nx` cells exposes `Nx` exactly like any other scalar
parameter: it appears in `free_variables`, participates in `substitute`, and
the conformance harness validates its presence via the existing schema.

## 7. Schema — `discretizations`

A discretization is a named stencil template. Each template maps an operator
class to a sum over neighbors with symbolic coefficients.

```json
{
  "discretizations": {
    "centered_2nd_uniform": {
      "applies_to": { "op": "grad", "dim": "$x" },
      "grid_family": "cartesian",
      "stencil": [
        { "selector": { "kind": "cartesian", "axis": "$x", "offset": -1 },
          "coeff":    { "op": "/", "args": [-1, { "op": "*", "args": [2, "dx"] }] } },
        { "selector": { "kind": "cartesian", "axis": "$x", "offset":  1 },
          "coeff":    { "op": "/", "args": [ 1, { "op": "*", "args": [2, "dx"] }] } }
      ]
    },
    "mpas_edge_grad": {
      "applies_to": { "op": "grad", "dim": "edge" },
      "grid_family": "unstructured",
      "stencil": [
        { "selector": { "kind": "indirect", "table": "cellsOnEdge",
                        "index_expr": { "op": "idx", "var": "cellsOnEdge",
                                        "indices": ["$e", 0] } },
          "coeff":    { "op": "/", "args": [-1, { "op": "idx", "var": "dcEdge", "indices": ["$e"] }] } },
        { "selector": { "kind": "indirect", "table": "cellsOnEdge",
                        "index_expr": { "op": "idx", "var": "cellsOnEdge",
                                        "indices": ["$e", 1] } },
          "coeff":    { "op": "/", "args": [ 1, { "op": "idx", "var": "dcEdge", "indices": ["$e"] }] } }
      ]
    }
  }
}
```

### 7.1 Discretization fields

| Field | Required | Description |
|---|---|---|
| `applies_to` | ✓ | A shallow AST pattern (§5.2 syntax) identifying the operator this scheme discretizes |
| `grid_family` | ✓ | Which grid family this scheme targets |
| `stencil` | ✓ | Array of `{ selector, coeff }` entries (see §4) |
| `accuracy` | | Informational: truncation order (string) |
| `requires_locations` | | If set, the operand variable must carry one of these locations |
| `emits_location` | | The output's staggered location (for staggered schemes) |

The `stencil` entries' `selector.kind` must match `grid_family`. `coeff`
expressions may reference the grid's metric arrays (as `idx` nodes), the grid's
parameters, and pattern variables bound by `applies_to`.

### 7.2 Expansion semantics

Given a PDE operator match at point `$target`, the discretization expands to

```
Σ_k coeff_k · idx(var=$u, indices=materialize(selector_k, $target))
```

where `materialize` turns a neighbor selector into a concrete index expression:

| Selector kind | `materialize(selector, target)` |
|---|---|
| `cartesian` | Index expression = target with `target[axis]` replaced by `target[axis] + offset` |
| `panel` | Lookup `panel_connectivity.neighbors[target.panel, side]` and apply `axis_flip` to (di, dj) |
| `indirect` | Return the selector's `index_expr` (with `$target` pattern-substituted) |

All three cases are pure AST transforms; no runtime array data is touched.

## 8. Schema — `rules`

Rules bind a PDE operator to a scheme at application time. The `rules` section
is where authoring happens for a specific model — it is the only section that
changes when a user picks "upwind-1st" over "centered-2nd" for an advection
term.

```json
{
  "rules": {
    "grad_x_interior": {
      "pattern": { "op": "grad", "args": ["$u"], "dim": "$x" },
      "where": [
        { "guard": "var_has_grid", "pvar": "$u", "grid": "atmos_rect" },
        { "guard": "var_is_spatial_dim_of", "pvar": "$x", "grid": "atmos_rect" }
      ],
      "use": "centered_2nd_uniform",
      "region": "interior"
    },
    "grad_x_boundary_periodic": {
      "pattern": { "op": "grad", "args": ["$u"], "dim": "$x" },
      "where": [
        { "guard": "var_has_grid", "pvar": "$u", "grid": "atmos_rect" },
        { "guard": "dim_is_periodic", "pvar": "$x" }
      ],
      "use": "centered_2nd_uniform",
      "region": "boundary",
      "wrap": "modulo"
    }
  }
}
```

### 8.1 Rule fields

| Field | Required | Description |
|---|---|---|
| `pattern` | ✓ | AST with pattern variables (§5.2) |
| `where` | | Array of guards |
| `use` | one of `use`/`emit` | Name of a `discretizations` entry to apply at the match site |
| `emit` | one of `use`/`emit` | Inline replacement AST (used for BC rules that don't fit a stencil template) |
| `region` | | `"interior"` (default), `"boundary"`, or `"all"` |
| `wrap` | | For boundary rules: `"modulo"` (periodic), `"reflect"`, `"ghost"` |
| `produces` | | Optional array of additional equations to emit into the discretized system (§8.3) |

### 8.2 Boundary conditions as rules

Per decision 6, BCs are model-level declarations (a new `boundary_conditions`
section under each model, structurally parallel to `coupling`). Discretization
rules rewrite BC declarations the same way they rewrite interior PDE
operators. A BC's replacement AST is a full ESM expression and may reference:

- Interior state (deposition feedback → `idx(var="SO2", indices=[...])`)
- Parameters (`"v_dep"`)
- Data-loader sources (`"observed_SST"`)
- Ghost-cell variables introduced by `produces`

Example — Dirichlet BC at `x=0` on variable `u`:

```json
{
  "rules": {
    "u_dirichlet_xmin": {
      "pattern": { "op": "bc", "args": ["$u"], "kind": "dirichlet", "side": "xmin" },
      "where": [ { "guard": "var_has_grid", "pvar": "$u", "grid": "atmos_rect" } ],
      "emit": { "op": "-", "args": [
        { "op": "idx", "var": "$u", "indices": [0] },
        "u_xmin_value"
      ]},
      "produces": [ { "kind": "algebraic" } ]
    }
  }
}
```

### 8.3 Emitting new equations

A key capability (decision 6): rules must be able to emit *new* equations, not
only rewrite existing ones. `produces[k]` may be:

| `kind` | Meaning |
|---|---|
| `algebraic` | Emit the `emit` expression as an algebraic constraint (= 0) |
| `ghost_var` | Declare a new ghost-cell variable with indices; the body of the rule defines it |
| `state_var` | Promote to a differential state variable |

This is how ghost cells for high-order stencils, algebraic closures for
Dirichlet BCs, and Robin mixed conditions all compose without special cases.

## 9. Variable staggering

Per decision 4, variables carry an optional `location` field:

```json
{ "variables": { "u": { "location": "x_face" }, "T": { "location": "cell_center" } } }
```

Default: `"cell_center"`. The staggering tag is added during the spatialization
step — it is *not* hand-authored on pre-spatialization continuous models.
Tools that translate a continuous PDE model to its spatialized form are
responsible for assigning locations; vector components (u, v, w on MAC grids)
and staggered scalars (edge-normal winds on MPAS) get explicit overrides.

Rules pattern-match on `location` via the `var_location_is` guard (§5.2).

## 10. Interaction with existing sections

| Section | Interaction |
|---|---|
| `domains` | Unchanged. A `grids` entry *may* name a `domain` to inherit temporal extent and coordinate system; if absent, the grid stands alone. |
| `models.<M>.domain` | Unchanged; still names a domain. A new optional field `models.<M>.grid` names a grid that refines that domain. |
| `models.<M>.equations` | Equations stay continuous. Discretization is an out-of-band operation (§11). |
| `data_loaders` | Metric-array loaders reuse the existing data-loader machinery. |
| `interfaces` | Unchanged. Regridding between domains continues to use `interfaces.<I>.regridding`. |
| `coupling` | Unchanged. Cross-system coupling still refers to continuous variables; the discretized pipeline applies rules to both sides before solving. |

Existing `.esm` files remain valid. A file that omits `grids`, `discretizations`,
and `rules` continues to mean "continuous PDE; discretization is the consumer's
problem" — identical to today's behavior.

## 11. Discretization as a pipeline

Given a model + grid + discretization + rules, a binding produces a
discretized ODE/DAE system via the following deterministic pipeline:

1. **Load and resolve** — parse the `.esm` file; resolve `ref` subsystems;
   validate against the schema.
2. **Tag locations** — for each variable on a model bound to a grid, assign a
   `location` (default `cell_center`; explicit overrides propagate).
3. **Expand metric generators** — for each metric array declared with
   `generator.kind = "expression"`, evaluate and cache the expression.
   For `loader`, record the loader handle; do not materialize.
4. **Rewrite** — apply the rule engine (§5.2) to every equation in `models.*`
   and to each entry of `boundary_conditions`. Emit additional equations from
   `rules[*].produces`.
5. **Collect** — the output is a set of equations over `idx`-addressed variables
   plus the original `models` scalar variables, ready to be handed to the
   host language's ODE/DAE assembler.

Step 5 output is still ESM-representable: it is a `models` entry with arrayed
variables plus algebraic constraints, no new node types introduced. A
`discretized: true` boolean on the output model is the only metadata change.

## 12. Conformance

The conformance harness (see `CONFORMANCE_SPEC.md`) adds a new fixture class
under `tests/conformance/discretization/`. Each fixture is an input `.esm`
(model + grid + discretizations + rules) plus a canonical discretized `.esm`
output. Each binding must produce byte-identical output (modulo whitespace
normalization performed by the existing harness).

Because coefficients are kept symbolic, bit-identity across bindings is
tractable: it reduces to AST equality after canonical ordering (addition
associativity, commutativity normalized as in the existing harness).

The MVP fixtures (after step 1 of the rollout) are:

- `rect_1d_advection_centered_periodic.esm`
- `rect_1d_advection_upwind_periodic.esm`
- `rect_2d_diffusion_5point_periodic.esm`

## 13. Rollout — 5 steps with acceptance criteria

Each step lands reference implementations in **at least Julia + Rust** and
extends the conformance harness such that Julia and Rust emit bitwise-identical
discretized expressions.

### Step 1 — Rectangular grids, MOL PR #531 parity

**Scope:** `cartesian` family only, uniform spacing, periodic BCs. Centered
and upwind stencils for `grad` and `laplacian`. Cartesian neighbor selector
only. `idx` AST node in all five bindings.

**Acceptance:**
- Julia binding reproduces the `ArrayDiscretization` output of
  MethodOfLines.jl PR #531 on at least three test systems (1D advection, 1D
  diffusion, 2D diffusion).
- Rust binding emits identical AST.
- Conformance harness includes the three fixtures in §12 and passes for Julia
  + Rust (Python, Go, TS gain `idx` support but need not emit discretized
  output yet).

### Step 2 — Dirichlet / Neumann / Robin BCs

**Scope:** `boundary_conditions` section on models. BC rewrite rules with
`emit` + `produces`. Ghost-cell `produces` variant.

**Acceptance:**
- All three BC kinds on a 1D diffusion problem match an analytic reference
  to 1e-12 per cell in a Julia runtime solve.
- Conformance harness gains four fixtures (Dirichlet at xmin, Neumann at xmax,
  Robin at both sides, mixed). Julia + Rust bit-identical.

### Step 3 — Non-uniform 1D grids

**Scope:** `extents.<dim>.spacing = "nonuniform"`. Metric arrays declared with
`generator.kind = "loader"` (CSV loader for prototype). Indexed `dx` usage in
stencil coefficients.

**Acceptance:**
- A 1D diffusion on a stretched grid (geometric progression) round-trips
  Julia → ESM → Rust and produces the same discretized system.
- Conformance fixture `rect_1d_diffusion_stretched.esm` passes Julia + Rust.

### Step 4 — Unstructured neighbor selector (MPAS)

**Scope:** `unstructured` family. Indirect neighbor selector. `connectivity`
tables. MPAS mesh loader. Scheme: MPAS edge-gradient + cell-divergence.

**Acceptance:**
- An icosahedral-mesh diffusion problem is discretized from
  `.esm` + MPAS mesh file and solved; Julia + Rust emit identical AST.
- Full MPAS `x1.2562` mesh loads and discretizes without error (does not need
  to finish solving in CI; discretization-only test).

### Step 5 — Cubed-sphere panel-aware selector

**Scope:** `cubed_sphere` family. Panel selector. `panel_connectivity.neighbors`
and `axis_flip` tables. FV-flux scheme parity with `EarthSciDiscretizations.jl`
on the C48 cubed sphere.

**Acceptance:**
- Steady-state advection on C48 matches `EarthSciDiscretizations.jl` to
  round-off in a Julia runtime solve.
- Rust emits identical AST for the discretization-only step; solve step is
  out of scope for the Rust conformance test.

## 14. Risks and open questions

1. **Pattern-matcher complexity.** The guard vocabulary is closed (§5.2), but
   scheme authors may want richer guards (e.g., "operand is constant"). Plan:
   ship the MVP vocabulary, gather scheme-author feedback after step 2, add
   guards with a spec version bump.
2. **Rule ordering.** Deterministic top-down fixed-point is adequate for the
   current schemes. If two rules legitimately match the same subtree (e.g.,
   a user wants centered-2nd in the interior and upwind-1st near a shock),
   the first-listed rule wins. This is explicit in §5.2.
3. **Ghost-cell lifetime.** `produces: ghost_var` declares a variable that
   exists only in the discretized system; ensure it does not leak into
   `free_variables` of the original continuous model. Validation rule to be
   added during step 2.
4. **Loader determinism.** MPAS meshes load from NetCDF — reproducibility of
   metric arrays across platforms must be guaranteed by the loader spec. This
   is already an existing data-loader concern (not new).
5. **Spec-version gate.** The RFC is additive. Proposed version bump: ESM
   0.2.0 on merge of step 1. Each subsequent rollout step is additive within
   0.2.x.

## 15. Why not alternatives

- **Embed a DSL (e.g., SymbolicUtils `@rule` literal strings).** Rejected:
  violates the "unambiguous and parseable in any language without a math
  parser" principle from §4 of the spec.
- **Represent stencils as fully-materialized `arrayop` nodes.** Rejected:
  scales to MPAS (millions of edges) as one expression per edge — prohibitive
  file size and loss of locality for GPU codegen.
- **Make discretization a runtime side-effect (keep the status quo).**
  Rejected by the architectural goal: every non-Julia binding currently
  cannot round-trip discretized PDEs.
- **Introduce a second file format for discretized systems.** Rejected: every
  additional format is a perennial cross-language-drift liability.

## 16. Deliverable checklist

This RFC is the deliverable of gt-dq0f. Implementation work is tracked
separately under the 5-step rollout. On acceptance of this RFC:

- Spec version bumps to 0.2.0-draft on the branch that lands step 1.
- `esm-schema.json` gains JSON-schema entries for `grids`, `discretizations`,
  `rules`, the new `idx` AST node, and the pattern-variable / guard sub-schema.
- `esm-spec.md` gains a new top-level section ("§16 Discretization") that
  cross-references this RFC for rationale and the schema for normative
  grammar.
- `CONFORMANCE_SPEC.md` gains a `discretization/` fixture class with the
  three step-1 fixtures.
