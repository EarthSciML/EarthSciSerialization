# RFC — Language-agnostic Discretization in ESM

**Status:** Draft (v2, revised per review gt-tlw2)
**Bead:** gt-dq0f (v1), gt-yx9y (v2 revision)
**Affects spec version:** 0.1.0 → 0.2.0 (**breaking**; see §10 and §16 for migration)
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
   Voronoi (MPAS, including variable-valence cells).
2. Lets any binding turn a PDE `.esm` file into a discretized ODE/DAE system
   without calling into Julia.
3. Emits bitwise-identical expression output across bindings on the conformance
   harness, via a normatively-defined canonical AST form (§5.4).
4. Reuses the existing expression AST (including `index`, now extended per
   §5.1), `substitute` / `evaluate` / `free_variables` / `simplify` primitives,
   `parameters`, domains, and the `data_loaders` subsystem.
5. Does **not** introduce a second file format.

## 2. Non-goals

- Time integration. ODE/DAE systems produced by discretization are handed to
  MTK, SciPy/SUNDIALS/Diffrax, DifferentialEquations.jl, diffsol, etc.
  Time-stepping schemes, implicit solvers, operator-splitting, and adaptive
  timestep control are out of scope.
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
rewrites it, via a named scheme, into an expression that references the grid's
metric arrays as `index`-addressed variables.

Two further existing-section changes are required (see §10 for details and
§16 for migration):

- `models.<M>.boundary_conditions` is promoted to first-class (structurally
  parallel to `coupling`). `domains.<d>.boundary_conditions` is **removed**.
- `variables.<name>` gains optional `shape` and `location` fields to describe
  arrayed and staggered state variables (spec §6.1 amendment).

No new file format, no additional top-level sections beyond the three above,
and no new AST node types beyond the pattern/guard sub-language of §5.2. The
new §5.3 `regrid` op is specified below and is the only AST-level addition.

## 4. Unifying abstraction: the neighbor selector

All three target grid families reduce to a single stencil template:

```
output[target] = ⊕_k coeff_k · var[neighbor_k(target)]
```

where `⊕` is `+` for linear schemes and may be `*`, `min`, or `max` for
reductions (see §4.2). They differ only in how `neighbor_k` is addressed. The
RFC introduces **one** selector abstraction with four concrete forms:

| Form | Fields | Grid family |
|---|---|---|
| `cartesian` | `axis`, `offset` | Logically-rectangular (MOL) |
| `panel` | `side ∈ {-i,+i,-j,+j}` (panel-connectivity resolves the target) | Cubed sphere (FV3) |
| `indirect` | `table`, `index_expr` | Unstructured fixed-valence (e.g. edge→cell) |
| `reduction` | `table`, `count_expr`, `k_bound`, `combine ∈ {+,*,min,max}` | Unstructured variable-valence (e.g. cell→edges) |

Exactly one selector kind lives inside a stencil-template entry, chosen by the
grid family the scheme is declared for. Rules attach a scheme to a grid at
application time, so a scheme's selector kind must be compatible with the
grid's declared family.

The **reduction** selector (new in v2) closes the MPAS variable-valence gap
identified in review M2. It expands, at materialization time, into a reduction
over a loader-provided contiguous index range (e.g. `edgesOnCell[c, 0
.. nEdgesOnCell[c] - 1]`), combining via the declared operator. See §7.2 for
the expansion rule and §7.3 for the worked MPAS divergence example.

## 5. AST extensions

### 5.1 Extended contexts for `index` (resolves C1)

The existing `index` op (spec §4.3.3) is sufficient for every array-element
reference this RFC needs. `index` is **not** restricted to appearing inside
`arrayop.expr`; the parenthetical in §4.3.3 — "as a string, when inside an
`arrayop.expr`" — qualifies only the interpretation of a bare-string index
argument as a symbolic index variable, not the op's legal contexts.

This RFC normatively confirms and adds:

1. **`index` is legal in any expression context**, including the `rhs` of a
   model equation, a coupling expression, or a BC replacement AST. Outside
   `arrayop.expr`, bare-string index arguments are resolved as ordinary
   parameter references (§6.2 of the spec), not as symbolic index variables.
2. **Integer literals and composite index expressions** are permitted:
   `{op:"index", args:["u", 0]}`, `{op:"index", args:["u", {op:"+",
   args:["i", 1]}]}`, and `{op:"index", args:["cellsOnEdge", "$e", 1]}` are
   all valid. This is already consistent with §4.3.3 — this RFC only pins it.
3. **Resolution of `index` on a non-`arrayop` expression.** Given
   `{op:"index", args:[E, i_1, ..., i_n]}` where `E` is not a bare variable
   name:
   - If `E` is a `makearray`, reduce by the `makearray` axes' extents
     (spec §4.3.2) and return the element expression.
   - If `E` is a `broadcast`, distribute: `index(broadcast(fn, A, B), i) =
     broadcast_scalar(fn, index(A, i), index(B, i))`.
   - If `E` is a `reshape`/`transpose`/`concat`, inverse-map the indices per
     that op's semantics and recurse.
   - Otherwise, the expression is ill-formed and must be rejected by the
     loader.

Validation rule (new, applied by the loader after resolving `ref`s): given
`{op:"index", args:[V, i_1, ..., i_n]}` where `V` is a bare variable name,
`V` must resolve to either (a) a declared variable (model/reaction/grid
metric) whose `shape` field (see §11 below and spec §6.1 amendment) has
length `n`, or (b) a connectivity table declared under a grid (§6.3, §6.4).
Integer bounds are **not** checked statically; out-of-bounds access is a
runtime concern.

**The parallel `idx` op proposed in v1 is dropped.** All of this RFC's
array-element references use `index`.

### 5.2 Pattern variables and rule engine

Rewrite rules cannot be expressed with positional `substitute`. The RFC adds a
small pattern sub-language, analogous to SymbolicUtils `@rule`, that is itself
serializable. A rule object has three fields:

| Field | Type | Purpose |
|---|---|---|
| `pattern` | AST with `$`-prefixed pattern variables | Matches an input expression |
| `where` | array of guard objects | Optional constraints on pattern variables |
| `replacement` | AST over the same pattern variables (or `use:<scheme>`) | Output expression |

Pattern variables are strings prefixed by `$`: `"$u"`, `"$x"`. The sub-language
is a closed AST shape, not a DSL string; every binding can load it with its
ordinary JSON parser.

#### 5.2.1 What a pattern variable binds to

The binding class of a pattern variable depends on **where it appears in the
pattern tree**, not on the variable's name. The three binding classes are:

| Class | Appears in | Binds |
|---|---|---|
| **name** | a sibling-field position whose spec-defined type is a string identifier (`dim`, `wrt`, `side`, `kind`, `axis`, `fn`) | A bare string (variable, dimension, or enum name) |
| **leaf** | an `args` position whose surrounding op requires a bare name (e.g. the operand of `D`, the variable of `bc`, the target of `grad`) | A bare string (variable name) |
| **subtree** | an `args` position whose surrounding op permits any Expression | Any AST subtree |

The legal sibling-field positions for **name**-class pattern variables are
enumerated per op and are fixed by this RFC:

| Op | name-class fields |
|---|---|
| `D` | `wrt` |
| `grad`, `div`, `laplacian` | `dim` (when present) |
| `bc` | `kind`, `side` |
| `index` | (none — all args are Expression) |
| `arrayop` | `idx` (each entry), `reduce.op` |
| `broadcast` | `fn` |
| `transpose` | (none — `perm` is a literal list) |
| `regrid` (new; §5.3) | `from`, `to` |

Guards (§5.2.4) may additionally constrain a pattern variable.

#### 5.2.2 Non-linear patterns

A pattern variable that appears in multiple positions within the same pattern
must bind to equal values at every occurrence. Equality is **AST-equal after
canonicalization** (§5.4). Two different pattern variables may bind to equal
values; the RFC imposes no anti-unification.

#### 5.2.3 Associative / commutative matching

**No AC matching.** A pattern `{op:"+", args:["$a", "$b"]}` matches a `+`
node with exactly two args; it does not match a three-arg sum, and it does
not match `b + a` (the match is positional). Authors who want to match an
n-ary sum use a canonical-form preprocessing pass (§5.4) or write multiple
rules.

This choice is load-bearing: it lets the pattern matcher be a bounded-depth
tree-equality check with pattern-variable bindings, which is reimplementable
in ~50 lines per binding. The cost — authors must write patterns in canonical
form — is paid once per scheme, not per model.

#### 5.2.4 Guard vocabulary

A guard object constrains a pattern variable. Guards are combined by AND.

| Guard | Example | Meaning |
|---|---|---|
| `dim_is_spatial_dim_of` | `{guard: "dim_is_spatial_dim_of", pvar: "$x", grid: "atmos_rect"}` | `$x` must name a spatial dimension of the given grid (renamed from v1 `var_is_spatial_dim_of` for consistency with m4) |
| `var_location_is` | `{guard: "var_location_is", pvar: "$u", location: "cell_center"}` | `$u` must carry the given staggered location (§11) |
| `var_has_grid` | `{guard: "var_has_grid", pvar: "$u", grid: "$g"}` | `$u` must be bound to grid `$g` |
| `dim_is_periodic` | `{guard: "dim_is_periodic", pvar: "$x", grid: "$g"}` | `$x`'s dimension has periodic BC under `$g` |
| `dim_is_nonuniform` | `{guard: "dim_is_nonuniform", pvar: "$x", grid: "$g"}` | `$x`'s `extents.$x.spacing` is `"nonuniform"` |
| `var_shape_rank` | `{guard: "var_shape_rank", pvar: "$u", rank: 2}` | Integer check on `$u.shape` |

New guards require a spec version bump. This keeps the pattern-matcher
trivially reimplementable in each binding (tree equality plus a dozen type
checks).

#### 5.2.5 Termination

The engine is a fixed-point loop over passes. Each pass walks every equation's
AST top-down; at each subtree, each rule is tried in `rules`-listing order;
the first match fires; after a rewrite, **the rewritten subtree is not
re-matched by any rule for the remainder of the current pass** (rule (i) in
review C5.5). A new pass begins once the previous pass completes; a pass that
produces no rewrites terminates the loop.

If the iteration count exceeds `max_passes = 32` without converging, the
engine must abort with error code `E_RULES_NOT_CONVERGED`. Authors may raise
the limit via a model-level `rules.max_passes` override; this is a spec-level
field, not a runtime flag.

#### 5.2.6 Worked example (one-page)

**Rule:**

```json
{
  "grad_x_interior": {
    "pattern":     { "op": "grad", "args": ["$u"], "dim": "$x" },
    "where":       [ { "guard": "var_has_grid", "pvar": "$u", "grid": "atmos_rect" },
                     { "guard": "dim_is_spatial_dim_of", "pvar": "$x", "grid": "atmos_rect" } ],
    "use":         "centered_2nd_uniform",
    "region":      "interior"
  }
}
```

**Input tree (one equation RHS):**

```json
{ "op": "grad", "args": ["T"], "dim": "x" }
```

After matching (with `$u := "T"`, `$x := "x"`), the engine invokes the
`centered_2nd_uniform` scheme (§7) which expands at target index `[i, j, k]`
(provided implicitly by the enclosing `models.<M>.grid` binding, see §7.2) to:

```json
{ "op": "+",
  "args": [
    { "op": "*", "args": [
       { "op": "/", "args": [ -1, { "op": "*", "args": [ 2, "dx" ] } ] },
       { "op": "index", "args": [ "T", { "op": "-", "args": ["i", 1] }, "j", "k" ] } ] },
    { "op": "*", "args": [
       { "op": "/", "args": [  1, { "op": "*", "args": [ 2, "dx" ] } ] },
       { "op": "index", "args": [ "T", { "op": "+", "args": ["i", 1] }, "j", "k" ] } ] }
  ]
}
```

After canonicalization (§5.4), every binding emits the **byte-identical** JSON
above. This is the byte-for-byte reference any binding must meet.

### 5.3 `regrid` op (new)

```json
{ "op": "regrid", "args": [<expr>], "from": "<grid>", "to": "<grid>", "method": "<name>" }
```

Required whenever a rewritten expression crosses grids — for example, when
`coupling.<c>` maps a variable from grid A to grid B and a downstream rule
re-indexes it on grid B. Without a `regrid` wrapper, the result is ill-formed.
This resolves review question Q6 (coupling ∘ rewrite interaction): rewrite
runs post-coupling (§11 pipeline), and cross-grid index expressions must be
wrapped in `regrid`.

`method` names a regridding algorithm that the target binding recognizes
(e.g. `"bilinear"`, `"conservative"`, `"nearest"`); the set of algorithms is
not schema-validated beyond being a string.

### 5.4 Canonical AST form (normative, new; resolves C3)

Every binding must apply the following canonicalization to every AST subtree
produced by the rule engine (and to every `.esm` expression at load time
when the file declares `spec.canonical_form_applied: true`). Two ASTs are
equal iff their canonical forms are JSON-equal.

#### 5.4.1 Integer / float promotion

An integer literal and a float literal are distinct AST nodes. Canonical form
**never auto-promotes**: `{op:"+", args:[1, 2.0]}` does not canonicalize to
`3.0`. Promotion happens only in `evaluate`, not in `simplify`/canonicalize.

#### 5.4.2 Commutative-op ordering

For `+` and `*`, the args list is sorted by the following total order, applied
lexicographically:

1. Numeric literals first, sorted ascending by numeric value (integer before
   float at equal magnitude).
2. Bare string references, sorted lexicographically (Unicode codepoint).
3. Non-leaf nodes, sorted by a stable serialization: recursively canonicalize,
   then compare their JSON serializations as byte strings (UTF-8, sorted keys,
   no extraneous whitespace).

The output argument list is stable, total, and deterministic.

#### 5.4.3 N-ary flattening

For `+` and `*`, nested same-op children are flattened: `+(+(a,b), c)` →
`+(a,b,c)`. Applied before §5.4.2 ordering.

#### 5.4.4 Zero / identity elimination

- `+(0, x, ...)` → `+(x, ...)`. If only `0` remains, replace with `0`.
- `+()` → `0`. `+(x)` → `x`.
- `*(1, x, ...)` → `*(x, ...)`. Similar singleton rules.
- `*(0, ...)` → `0` (zero annihilates).
- `/(x, 1)` → `x`. `-(0)` → `0`. `-(x, 0)` → `x`.

`0` and `1` are compared by numeric value across integer/float, matching
§5.4.1's non-promotion rule (the canonical form of `*(1.0, x)` is `x`, and
the resulting expression has no type tag — type is inferred from the
surviving operand).

#### 5.4.5 String-vs-number in variable references

A bare variable reference is always a string. Numeric literals are always
JSON numbers. A name that happens to be all digits (`"0"` as a variable)
requires the authoring tool to quote it unambiguously; the canonicalizer
does not disambiguate.

#### 5.4.6 Worked example

Input: `{op:"+", args:[{op:"*", args:["a", 0]}, "b", {op:"+", args:["a", 1]}]}`

1. Flatten: outer `+` has an inner `+`: `{op:"+", args:[{op:"*",
   args:["a", 0]}, "b", "a", 1]}`.
2. Eliminate: `*(a, 0)` → `0`: `{op:"+", args:[0, "b", "a", 1]}`.
3. Order: numerics first (`0, 1`), then strings (`"a", "b"`): `{op:"+",
   args:[0, 1, "a", "b"]}`.
4. Eliminate: `+(0, ...)` → remove 0: `{op:"+", args:[1, "a", "b"]}`.

Every binding must produce exactly this output. The conformance harness
compares post-canonicalization JSON byte-wise (keys sorted, no optional
whitespace). Algebraic equivalence beyond this list (e.g. distributivity,
factoring) is **not** part of canonical form.

### 5.5 No other new calculus ops

`D`, `grad`, `div`, `laplacian` already exist. Beyond `regrid` (§5.3), no
additional continuous-math ops are introduced. Ghost-cell addressing and
boundary regions are expressed through `index` plus rule replacements; no new
op for "boundary region" is defined in the MVP slice.

## 6. Schema — `grids`

### 6.1 Top-level

```json
{
  "grids": {
    "atmos_rect":   { "family": "cartesian",     ... },
    "mpas_cvmesh":  { "family": "unstructured",  ... },
    "cubed_c48":    { "family": "cubed_sphere",  ... }
  }
}
```

Each key is a grid name; the value is an object whose `family` field selects
one of three schemas below. All grids support the following common fields:

| Field | Required | Description |
|---|---|---|
| `family` | ✓ | `"cartesian"`, `"cubed_sphere"`, or `"unstructured"` |
| `dimensions` | ✓ | Ordered list of logical dimension names |
| `locations` | | Declared stagger locations (see §11) |
| `metric_arrays` | | Declarations of metric arrays (see §6.5) |
| `parameters` | | Ordinary ESM parameter entries (see §6.6) |
| `domain` | | Name of the `domains` entry this grid refines (optional) |

The `parameters` block **reuses** the existing ESM `parameters` schema (§6.2
of the spec) verbatim. Grid-level parameters are visible to `substitute`,
`free_variables`, and the conformance harness without any new machinery.

**Interaction with `domains.<d>.spatial.<dim>.grid_spacing`** (review m1):
if a grid names a domain, any `grid_spacing` the domain declares is advisory
only. The grid's `extents.<dim>.spacing` wins; authors may set
`spatial.<dim>.grid_spacing` to the same value for documentation, but the
loader does not cross-check. (Future work: deprecate the domain-level field.)

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
    "dx": { "rank": 0, "generator": { "kind": "expression",
             "expr": { "op": "/", "args": [ { "op": "-", "args": ["x_max", "x_min"] }, "Nx" ] } } },
    "dz": { "rank": 1, "dim": "z", "generator": { "kind": "loader", "loader": "zlev_csv", "field": "dz" } }
  },
  "parameters": {
    "Nx": { "value": 64 }, "Ny": { "value": 64 }, "Nz": { "value": 32 },
    "x_min": { "value": 0.0 }, "x_max": { "value": 1.0 }
  }
}
```

- `extents[<dim>].n` — expression referencing a parameter giving the count
  along that dimension.
- `extents[<dim>].spacing` — `"uniform"` lets rules reference `dx` as a
  rank-0 scalar; `"nonuniform"` **requires** the metric array to have
  `rank: 1` with `dim: "<x>"`. The engine auto-rewrites scalar references
  to `index`ed references when `spacing = "nonuniform"` (§6.2.1 below;
  resolves M1 per option (b)).

#### 6.2.1 Scalar → indexed metric rewrite

When a scheme's `coeff` expression contains a bare string reference `"dx"`
(or any other metric-array name) and the enclosing rule's operand axis `$x`
binds to a dimension whose `extents.$x.spacing = "nonuniform"`, the engine
rewrites the reference to `{op:"index", args:["dx", <target-index-for-$x>]}`
during scheme expansion (§7.2), *before* canonicalization.

Lookup rule: the target index for axis `$x` is the expansion target's index
for that axis (i.e., `i` for a cartesian scheme whose stencil offsets along
`x` from target `[i, j, k]`; neighbor offsets are applied separately to the
operand variable, not to the metric).

This is a pure AST transform; it preserves bit-identity because all bindings
apply the same rewrite rule at the same point in the pipeline.

### 6.3 Family: `unstructured`

```json
{
  "family": "unstructured",
  "dimensions": ["cell", "edge", "vertex"],
  "locations": ["cell_center", "edge_normal", "vertex"],
  "connectivity": {
    "cellsOnEdge":   { "shape": ["nEdges", 2],    "rank": 2, "loader": "mpas_mesh", "field": "cellsOnEdge" },
    "edgesOnCell":   { "shape": ["nCells", "maxEdges"], "rank": 2, "loader": "mpas_mesh", "field": "edgesOnCell" },
    "verticesOnEdge":{ "shape": ["nEdges", 2],    "rank": 2, "loader": "mpas_mesh", "field": "verticesOnEdge" },
    "nEdgesOnCell":  { "shape": ["nCells"],       "rank": 1, "loader": "mpas_mesh", "field": "nEdgesOnCell" }
  },
  "metric_arrays": {
    "dcEdge":  { "rank": 1, "dim": "edge", "generator": { "kind": "loader", "loader": "mpas_mesh", "field": "dcEdge" } },
    "dvEdge":  { "rank": 1, "dim": "edge", "generator": { "kind": "loader", "loader": "mpas_mesh", "field": "dvEdge" } },
    "areaCell":{ "rank": 1, "dim": "cell", "generator": { "kind": "loader", "loader": "mpas_mesh", "field": "areaCell" } }
  },
  "parameters": {
    "nCells": { "value": "from_loader" },
    "nEdges": { "value": "from_loader" },
    "maxEdges": { "value": "from_loader" }
  }
}
```

`connectivity[<name>]` declares an integer table addressable by rules. Rules
that use the `indirect` or `reduction` selector name one of these tables in
`selector.table`.

The `{loader, field}` pair references an entry of the top-level
`data_loaders` section; see §8 for the mesh-loader extension this RFC adds.

### 6.4 Family: `cubed_sphere`

```json
{
  "family": "cubed_sphere",
  "dimensions": ["panel", "i", "j"],
  "extents": { "panel": { "n": 6 }, "i": { "n": "Nc" }, "j": { "n": "Nc" } },
  "locations": ["cell_center", "i_edge", "j_edge", "vertex"],
  "panel_connectivity": {
    "neighbors":  { "shape": [6, 4], "rank": 2, "generator": { "kind": "builtin", "name": "gnomonic_c6_neighbors" } },
    "axis_flip":  { "shape": [6, 4], "rank": 2, "generator": { "kind": "builtin", "name": "gnomonic_c6_d4_action" } }
  },
  "metric_arrays": {
    "dxC": { "rank": 3, "dims": ["panel","i","j"],
             "generator": { "kind": "expression", "expr":
                { "op": "/", "args": [ "cube_edge_length",
                    { "op": "*", "args": [ "Nc",
                        { "op": "cos", "args": [ { "op": "atan2", "args": [ "j_coord", "i_coord" ] } ] } ] } ] } } }
  },
  "parameters": { "Nc": { "value": 48 }, "cube_edge_length": { "value": 1.0 } }
}
```

`panel_connectivity.neighbors[p, side]` gives the neighboring panel index for
each (panel, side ∈ {0: −i, 1: +i, 2: −j, 3: +j}); `axis_flip[p, side]` is
a single integer encoding an element of the dihedral group D₄ acting on the
local (Δi, Δj) displacement.

#### 6.4.1 `axis_flip` D₄ group action (resolves M4)

Each integer `a ∈ {0..7}` encodes an (orientation, mirror) pair as the signed
permutation of the local axes:

| a | (Δi', Δj') = | description |
|---|---|---|
| 0 | (+Δi, +Δj) | identity |
| 1 | (+Δj, −Δi) | rotate CCW 90° |
| 2 | (−Δi, −Δj) | rotate 180° |
| 3 | (−Δj, +Δi) | rotate CW 90° |
| 4 | (+Δj, +Δi) | reflect across i=j |
| 5 | (−Δi, +Δj) | reflect across i axis |
| 6 | (−Δj, −Δi) | reflect across i+j=0 |
| 7 | (+Δi, −Δj) | reflect across j axis |

This is the full D₄ action, enumerated so two independent bindings produce
byte-identical index expressions. The table is canonical: 0 is the identity,
1–3 are rotations in CCW order, 4–7 are reflections in the order
(main-diag, horizontal, anti-diag, vertical). Deviation from this table
is non-conforming.

The `{kind:"builtin", "name": ...}` generator encodes that these tables are
produced by a well-known algorithm rather than a file; the set of legal
`builtin` names is closed (`gnomonic_c6_neighbors`, `gnomonic_c6_d4_action`
are the only two defined in v0.2.0).

#### 6.4.2 Worked panel-selector example (resolves m2)

A centered gradient along `i` at target `[p, i, j]`, when `i = Nc-1` (so the
`+i` neighbor lives on a different panel):

```json
{ "op": "+", "args": [
    { "op": "*", "args": [
        { "op": "/", "args": [ -1, { "op": "*", "args": [ 2, { "op": "index", "args": ["dxC", "p", "i", "j"] } ] } ] },
        { "op": "index", "args": ["T", "p", { "op": "-", "args": ["i", 1] }, "j"] } ] },
    { "op": "*", "args": [
        { "op": "/", "args": [  1, { "op": "*", "args": [ 2, { "op": "index", "args": ["dxC", "p", "i", "j"] } ] } ] },
        { "op": "regrid", "args": [ { "op": "index", "args": ["T",
            { "op": "index", "args": ["neighbors", "p", 1] },
            { "op": "apply_axis_flip", "args": [ { "op": "index", "args": ["axis_flip", "p", 1] },
                { "op": "+", "args": ["i", 1] }, "j" ] } ] } ],
          "from": "cubed_c48", "to": "cubed_c48", "method": "panel_seam" } ] }
]}
```

`apply_axis_flip` is **not** a new AST op — it is an alias for the table
lookup in §6.4.1, emitted as the canonical JSON form of the case `a ∈ {0..7}`
expanded into a piecewise expression. (Bindings may internalize it; the
canonical on-wire form is the piecewise expansion. The `apply_axis_flip`
spelling above is illustrative; the materialized form is deterministic per
§6.4.1's enumerated table.)

### 6.5 Metric-array generators

A metric array's contents come from exactly one of:

| Kind | Fields | Semantics |
|---|---|---|
| `expression` | `expr` | An ordinary ESM expression; all free variables must be grid `parameters` or (for analytic grids) dimension indices. Computed at discretization time, cached per-session within the rewriting binding. |
| `loader` | `loader`, `field` | Names an entry in the top-level `data_loaders` map, and a named field produced by that loader. Grid JSON never contains bulk values. See §8 for the loader-extension this RFC adds. |
| `builtin` | `name` | Names a built-in, canonical generator from a closed list (see §6.4). Used for mathematical tables (D₄ action, standard connectivity) whose definition is textual rather than file-resident. |

Per design decision, analytic grids use `expression`; irregular grids (MPAS)
use `loader`. This matches existing loader semantics and keeps `.esm` files
diff-friendly.

### 6.6 Parameter flow

Grid generator parameters are ordinary ESM parameters. A rectangular grid
with `Nx` cells exposes `Nx` exactly like any other scalar parameter: it
appears in `free_variables`, participates in `substitute`, and the
conformance harness validates its presence via the existing schema.

Grid-level parameters with `value: "from_loader"` are resolved at load time
by reading the metadata of the referenced loader; this is a loader-side
obligation specified in §8 below.

## 7. Schema — `discretizations`

A discretization is a named stencil template. Each template maps an operator
class to a combination (sum, product, min/max reduction) over neighbors with
symbolic coefficients.

```json
{
  "discretizations": {
    "centered_2nd_uniform": {
      "applies_to": { "op": "grad", "args": ["$u"], "dim": "$x" },
      "grid_family": "cartesian",
      "combine": "+",
      "stencil": [
        { "selector": { "kind": "cartesian", "axis": "$x", "offset": -1 },
          "coeff":    { "op": "/", "args": [-1, { "op": "*", "args": [2, "dx"] }] } },
        { "selector": { "kind": "cartesian", "axis": "$x", "offset":  1 },
          "coeff":    { "op": "/", "args": [ 1, { "op": "*", "args": [2, "dx"] }] } }
      ]
    }
  }
}
```

### 7.1 Discretization fields

| Field | Required | Description |
|---|---|---|
| `applies_to` | ✓ | A shallow AST pattern (§5.2 syntax) identifying the operator this scheme discretizes. Pattern variables in `applies_to` are visible to `stencil` and `coeff`. |
| `grid_family` | ✓ | `"cartesian"`, `"cubed_sphere"`, or `"unstructured"` |
| `combine` | | `"+"` (default), `"*"`, `"min"`, or `"max"` — how stencil entries are combined. |
| `stencil` | ✓ | Array of `{ selector, coeff }` entries (see §4). Exactly one entry for a `reduction` selector; one-or-more for the others. |
| `accuracy` | | Informational: truncation order (string) |
| `requires_locations` | | If set, the operand variable must carry one of these locations |
| `emits_location` | | The output's staggered location (for staggered schemes) |
| `target_binding` | | Reserved name for the target index (default: `"$target"`). Per grid family, `$target` resolves to the enclosing equation's LHS index (cartesian: `[i, j, k, ...]`; unstructured: bound to the iteration index of the operand's location, e.g. `c` for `cell`, `e` for `edge`, `v` for `vertex`; cubed sphere: `[p, i, j]`). |

The `stencil` entries' `selector.kind` must match `grid_family`. `coeff`
expressions may reference the grid's metric arrays (as bare strings or
`index` nodes), the grid's parameters, pattern variables bound by
`applies_to`, and the reserved `$target` components (see below).

#### 7.1.1 `$target` and implicit location indices (resolves M3)

`$target` names the LHS index of the equation being rewritten, decomposed
per the grid family:

| Grid family | `$target` components |
|---|---|
| `cartesian` | `[i, j, k, ...]` — one per dimension |
| `cubed_sphere` | `[p, i, j]` (panel, panel-i, panel-j) |
| `unstructured` | one of `c` (cell), `e` (edge), `v` (vertex) — chosen by the operand's `location` |

Within a scheme, authors may reference `$target`'s components by their
canonical names above; the component names are reserved keywords and may
not be used as user variable names within a scheme. The v1 `mpas_edge_grad`
example's `$e` is an implicit binding to `$target` for an edge-operand
scheme; `$e` in that position is synonymous with `$target`.

### 7.2 Expansion semantics

Given a PDE operator match at point `$target`, the discretization expands to

```
combine_k( coeff_k · operand_ref_k )
```

where `combine_k` is the `combine` op (default `+`), `coeff_k` is
`coeff` after §6.2.1 auto-indexing, and `operand_ref_k` is
`{op:"index", args:[operand_var, ...materialize(selector_k, $target)]}`.

`materialize` turns a neighbor selector into a concrete list of index
expressions:

| Selector kind | `materialize(selector, target)` |
|---|---|
| `cartesian` | For target `[..., axis_idx, ...]`, output the same list with `axis_idx` replaced by `{op:"+", args:[axis_idx, offset]}`. |
| `panel` | Lookup `panel_connectivity.neighbors[p, side]` for the new panel, and apply `axis_flip[p, side]` (§6.4.1) to the (di, dj) displacement. |
| `indirect` | Emit `[index_expr]` after `$target`-substitution. `index_expr` is a single index expression into the indexed variable. |
| `reduction` | Lower to an `arrayop` over the index `k` running `0 .. count_expr - 1`, with element `coeff · index(operand, table[target, k])`, reducing via `combine`. |

All cases are pure AST transforms; no runtime array data is touched.

### 7.3 Worked MPAS divergence (resolves M2 / C4)

Scheme:

```json
{
  "mpas_cell_div": {
    "applies_to":   { "op": "div", "args": ["$F"], "dim": "cell" },
    "grid_family":  "unstructured",
    "requires_locations": ["edge_normal"],
    "emits_location":     "cell_center",
    "combine":      "+",
    "stencil": [
      {
        "selector": {
          "kind":       "reduction",
          "table":      "edgesOnCell",
          "count_expr": { "op": "index", "args": ["nEdgesOnCell", "$target"] },
          "k_bound":    "k",
          "combine":    "+"
        },
        "coeff": {
          "op": "/",
          "args": [
            { "op": "index", "args": ["dvEdge", { "op": "index", "args": ["edgesOnCell", "$target", "k"] } ] },
            { "op": "index", "args": ["areaCell", "$target"] }
          ]
        }
      }
    ]
  }
}
```

Expansion at cell `c` lowers (§7.2 `reduction` row) to:

```json
{ "op": "arrayop",
  "idx": ["k"],
  "ranges": { "k": { "lo": 0, "hi": { "op": "-", "args": [ { "op": "index", "args": ["nEdgesOnCell", "c"] }, 1 ] } } },
  "reduce": { "op": "+", "init": 0 },
  "expr": { "op": "*", "args": [
      { "op": "/", "args": [
          { "op": "index", "args": ["dvEdge", { "op": "index", "args": ["edgesOnCell", "c", "k"] } ] },
          { "op": "index", "args": ["areaCell", "c"] } ] },
      { "op": "index", "args": [ "F", { "op": "index", "args": ["edgesOnCell", "c", "k"] } ] }
  ]}
}
```

The inner `index` on `edgesOnCell` is a dynamic index: `k` is a symbolic
index variable valid inside `arrayop.expr` (per spec §4.3.3), so `"k"` as a
bare string is permitted and resolves to the arrayop index variable — no
`regrid` is needed because we remain on grid `mpas_cvmesh`.

This is the same `arrayop` shape the existing spec §4.3.1 supports; no new
AST node is introduced for the reduction. MPAS thus "reduces to" the stencil
template after one lowering step to `arrayop`, consistent with §4's
architectural claim.

## 8. Amendments to §8 (`data_loaders`) — inline (resolves C4)

v0.2.0 extends `data_loaders` with a new `kind: "mesh"` that covers MPAS-
style connectivity and metric provision. The RFC's Step 4 acceptance depends
on these additions; they are therefore part of this RFC, not an unscheduled
follow-up.

### 8.A New `kind: "mesh"`

```json
{
  "data_loaders": {
    "mpas_mesh": {
      "kind": "mesh",
      "source": { "url_template": "./mpas/x1.2562.grid.nc" },
      "mesh": {
        "topology": "mpas_voronoi",
        "connectivity_fields": ["cellsOnEdge", "edgesOnCell", "verticesOnEdge", "nEdgesOnCell"],
        "metric_fields":       ["dcEdge", "dvEdge", "areaCell"],
        "dimension_sizes":     { "nCells": "from_file", "nEdges": "from_file", "maxEdges": "from_file" }
      },
      "determinism": {
        "endian": "little",
        "float_format": "ieee754_double",
        "integer_width": 32
      },
      "reference": { "doi": "10.5194/gmd-5-1115-2012" }
    }
  }
}
```

#### 8.A.1 Mesh-loader fields (additions to the §8.1 table)

| Field | Required | Description |
|---|---|---|
| `kind: "mesh"` | ✓ | Distinguishes from `"grid"`, `"points"`, `"static"`. |
| `mesh.topology` | ✓ | Closed enum: `"mpas_voronoi"` (MVP), `"fesom_triangular"` (future), `"icon_triangular"` (future). Adding a value is a minor version bump. |
| `mesh.connectivity_fields` | ✓ | List of integer-typed fields exposed under `grids.<g>.connectivity.<name>`. |
| `mesh.metric_fields` | ✓ | List of float-typed fields exposed under `grids.<g>.metric_arrays.<name>`. |
| `mesh.dimension_sizes` | | Map of dimension name → integer or `"from_file"`. Values populate grid-level `parameters` marked `from_loader`. |
| `determinism` | | Endian / format / integer-width declarations. Required for bit-exact reproducibility guarantees. A binding that cannot honor these must reject at load. |

#### 8.A.2 Addressing

A grid's `metric_arrays.<m>.generator.{loader, field}` or
`connectivity.<c>.{loader, field}` references a mesh loader by its top-level
`data_loaders` key and picks out one field by name from the loader's exposed
`metric_fields` / `connectivity_fields`. This resolves review C4's
"addressing inconsistency" (the RFC v1's `{kind, name, params}` shape was
incompatible with existing loader keying; v2 uses the existing-key + field
pattern).

#### 8.A.3 Time-dependent loader fields for BCs (resolves M5)

A loader with `kind: "grid"` or `kind: "mesh"` may expose time-varying
fields (e.g., observed SST at prescribed BCs) that are referenceable from
a model-level `boundary_conditions` entry's `value` AST. The mechanism:

1. The loader declares the time-varying field under `variables.<schema_name>`
   (existing §8.5 mechanism). No schema change here.
2. A BC's `value` AST may contain `{op:"index", args:["observed_SST",
   "t", <face_coord_0>, <face_coord_1>]}`. `observed_SST` is a bare string
   that the loader resolves. The `t` argument is **explicit**: `t` is the
   model's time variable (spec §11.3 `independent_variable`, default
   `"t"`), bound as a free variable of the BC expression. It is **not**
   implicit. The face-coordinate arguments are the face's (dim-reduced)
   index within the BC's `side` (see §9.2 below for the exact shape).
3. The rule engine does not evaluate the loader field at rewrite time; it
   passes the `index` expression through. The downstream ODE/DAE assembler
   wires `"observed_SST"` to a runtime handle.
4. The canonical form (§5.4) preserves the ordering of arguments: `t` is
   always first, spatial coords follow in declaration order of `side`'s
   reduced dimensions.

This keeps rewrite static while letting loader outputs serve as BC sources.

## 9. Schema — model-level `boundary_conditions` (resolves C2)

Boundary conditions are promoted from a domain property to a first-class
model-level section, structurally parallel to `coupling`. This is a
**breaking change** from v0.1; see §10 for migration.

### 9.1 Top-level under a model

```json
{
  "models": {
    "atmos": {
      "domain": "atmosphere",
      "grid":   "atmos_rect",
      "boundary_conditions": {
        "u_dirichlet_xmin": {
          "variable": "u",
          "side":     "xmin",
          "kind":     "dirichlet",
          "value":    "u_xmin_value"
        },
        "SO2_flux_zmin": {
          "variable": "SO2",
          "side":     "zmin",
          "kind":     "neumann",
          "value": {
            "op": "*",
            "args": [ { "op": "-", "args": ["v_dep"] }, { "op": "index", "args": ["SO2", "i", "j", 0] } ]
          },
          "contributed_by": { "component": "dry_deposition", "flux_sign": "-" }
        }
      }
    }
  }
}
```

### 9.2 Boundary condition fields

| Field | Required | Description |
|---|---|---|
| `variable` | ✓ | Name of the model variable the BC constrains. |
| `side` | ✓ | Boundary side: `"xmin"`, `"xmax"`, `"ymin"`, ..., `"panel_seam"` (cubed sphere), `"mesh_boundary"` (unstructured). |
| `kind` | ✓ | `"constant"`, `"dirichlet"`, `"neumann"`, `"robin"`, `"zero_gradient"`, `"periodic"`, `"flux_contrib"` (for component-contributed flux terms, see §9.3). |
| `value` | | Expression or number; semantics per `kind`. |
| `robin_alpha` / `_beta` / `_gamma` | | As in spec §11.5, when `kind: "robin"`. |
| `face_coords` | | Declares the reduced face-coordinate index names used when `value` contains `index` into a loader-provided time-varying field. E.g., for `side: "zmin"` on a 3D grid, `face_coords: ["i", "j"]`. |
| `contributed_by` | | Optional; identifies the model component contributing this flux. The v2 canonical way for a deposition module (or any component) to declare a boundary-flux contribution (resolves decision 3(c)). |

Rules (§10) rewrite `boundary_conditions` entries into discretized form the
same way they rewrite interior equations. A BC pattern is matched via
`{op: "bc", args:["$u"], kind: "dirichlet", side: "xmin"}` against the
entry's `{variable, kind, side}` (synthetic `op: "bc"` node; the entry's
`value` is carried as the sole Expression arg after `$u`).

### 9.3 Components as BC contributors

Per owner decision 3(c): a model-level component (deposition, emissions,
surface-flux scheme) declares a boundary-flux contribution as an entry in
the target model's `boundary_conditions` map, with `kind: "flux_contrib"`,
`contributed_by.component = "<its own name>"`, and a `value` AST that
references its local state and parameters. The rewrite engine sums all
`flux_contrib` entries for the same (variable, side) pair into a single
aggregated flux, then applies the enclosing `kind`'s BC template.

### 9.4 `produces`: emitting new equations

A rule may emit additional equations via `produces[k]`:

| `kind` | Meaning |
|---|---|
| `algebraic` | Emit the `emit`/`value` expression as an algebraic constraint (= 0). |
| `ghost_var` | Declare a new ghost-cell variable with indices; the rule body defines it. Ghost variables are local to the discretized output and are not visible to `free_variables` on the original continuous model (validation rule: loader must reject a pre-discretization `.esm` that references a `ghost_var`). |

The v1 `state_var` option is **removed** from the MVP (resolves m9); there
was no compelling worked example. It can be re-added with a spec-version
bump if a use case surfaces.

## 10. Interaction with existing sections and migration

| Section | Interaction |
|---|---|
| `domains` | `boundary_conditions` **removed** (breaking — see §16 migration). `spatial.<dim>.grid_spacing` becomes advisory if a grid refines the domain (§6.1). |
| `models.<M>.domain` | Unchanged; still names a domain. A new optional field `models.<M>.grid` names a grid that refines that domain. |
| `models.<M>.boundary_conditions` | **New** first-class section (§9). |
| `models.<M>.equations` | Equations stay continuous. Discretization is an out-of-band operation (§11). |
| `data_loaders` | Extended with `kind: "mesh"` (§8.A). |
| `interfaces` | Unchanged. Regridding between domains continues to use `interfaces.<I>.regridding`. For grid-to-grid regridding *within* a rewrite, use the §5.3 `regrid` op. |
| `coupling` | Unchanged. Cross-system coupling still refers to continuous variables; the discretized pipeline applies rules *post-coupling* (§11). Cross-grid indices in a coupled expression must be wrapped in `regrid`. |
| `variables.<name>` | Gains optional `shape` (list of dimension names) and `location` fields (spec §6.1 amendment below). |

### 10.1 Breaking-change summary (version 0.1 → 0.2)

1. `domains.<d>.boundary_conditions` **removed**. Pre-0.2 files carrying
   this field are invalid under the 0.2 schema. Migration rule in §16.
2. `variables.<name>` adds `shape` and `location` optional fields. Pre-0.2
   files without these remain valid (default: `shape: null` = scalar,
   `location: "cell_center"` when a grid is attached).
3. `data_loaders.<ℓ>.kind` accepts `"mesh"`. Pre-0.2 files without it are
   unaffected.

A file carrying `spec.version: "0.1"` is not loadable by a 0.2-only
binding; it must be migrated with the `spec.migrate_0_1_to_0_2` convention
described in §16.

### 10.2 Spec §6.1 amendment — inline

Add to the per-variable field table (spec §6.3 Variable Types):

| Field | Required | Description |
|---|---|---|
| `shape` | | List of dimension names (from the variable's domain's grid). A scalar has `shape: null` or omitted. Used by the discretization pipeline's output and validated by `index` in §5.1. |
| `location` | | Staggered location within the grid (e.g. `"cell_center"`, `"x_face"`, `"edge_normal"`). Default: `"cell_center"` if the variable's model has a `grid`, else omitted. Assignment of non-default `location` is the job of the spatialization tooling (see §11, m5). |

This amendment is part of this RFC's deliverable (§16), not a dangling
spec change.

## 11. Discretization as a pipeline

Given a model + grid + discretization + rules, a binding produces a
discretized ODE/DAE system via the following deterministic pipeline:

1. **Load and resolve** — parse the `.esm` file; resolve `ref` subsystems;
   validate against the schema. Reject files with `spec.version < "0.2"`
   unless the `spec.migrate_0_1_to_0_2` flag is present (§16).
2. **Tag locations** — for each variable on a model bound to a grid, assign
   a `location` (default `cell_center`; explicit overrides propagate).
   "Spatialization" here is the sub-phase that writes `location` onto
   previously-scalar variables; it is part of pipeline Step 2 (resolves m5),
   not an out-of-spec tooling concern.
3. **Expand metric generators** — for each metric array declared with
   `generator.kind = "expression"`, evaluate and cache the expression
   (cache scope: current process / session; §15 Q4 pins this). For
   `loader` or `builtin`, record the handle; do not materialize bulk data.
4. **Apply couplings** — resolve `coupling.<c>.variable_map.transforms`
   on continuous variables. After this step the equation system is on
   possibly-multiple grids. Cross-grid references are wrapped with `regrid`.
5. **Rewrite** — apply the rule engine (§5.2) to every equation in
   `models.*` and to every entry of `models.*.boundary_conditions`. Emit
   additional equations from `rules[*].produces`.
6. **Canonicalize** — apply §5.4 canonical form to every emitted AST.
7. **Check rule coverage** — for every equation, if `models.<M>.grid` is
   set and the post-rewrite AST still contains a PDE operator on a gridded
   variable (resolves review Q3, decision 7):
   - Error by default with code `E_UNREWRITTEN_PDE_OP`.
   - If the equation (or boundary_condition) has `passthrough: true`, skip.
     `passthrough` is a new boolean field on equations and BCs; it is
     authorial opt-in and must be paired with a note in the file describing
     why.
8. **Collect** — the output is a set of equations over `index`-addressed
   variables plus the original scalar variables, ready to be handed to the
   host-language ODE/DAE assembler.

Step 8 output is still ESM-representable: it is a `models` entry with
arrayed variables (per §10.2 shape) plus algebraic constraints, no new
node types introduced. A `discretized: true` boolean on the output model
is the only metadata change.

## 12. DAE support and binding contract (resolves review Q5, decision 6)

If the rewrite produces an equation with `produces: algebraic`, the
resulting system is a DAE, not an ODE. A binding that receives a
discretized model containing algebraic equations **must** either:

(a) hand the system to a DAE assembler (MTK for Julia; SUNDIALS/IDA or
Diffrax's DAE modes for Python; diffsol for Rust; TBD for Go/TS), or

(b) abort with error code `E_NO_DAE_SUPPORT` and a message identifying
the binding and the algebraic-equation-producing rules. Silent omission
of constraints, or demotion of an algebraic constraint to an ODE residual,
is **non-conforming**.

Spec-level contract: if a binding advertises discretization support without
DAE support, that is the binding's bug, not the model author's problem.
Each binding's documentation must state its DAE assembler.

## 13. Conformance

The conformance harness (`CONFORMANCE_SPEC.md`) gains a new fixture class
`tests/conformance/discretization/`. Each fixture is an input `.esm`
(model + grid + discretizations + rules) plus a canonical discretized
`.esm` output. Each binding must produce byte-identical output after the
§5.4 canonical form is applied by the harness.

Because coefficients are kept symbolic and §5.4 defines a normative normal
form, bit-identity across bindings reduces to AST equality after
canonicalization. This closes the gap identified in review C3.

### 13.1 Rollout — 4 steps with acceptance criteria

Each step lands reference implementations in **at least Julia + Rust** and
extends the conformance harness such that Julia and Rust emit bitwise-
identical discretized expressions (post-canonicalization).

#### Step 1 — Infrastructure (new; absorbs prior Step 1 + review M8)

**Scope.** Everything Step 2 onwards depends on:

- `index` extension for out-of-`arrayop` contexts in all five bindings
  (§5.1).
- Pattern-match / rule engine in all five bindings (§5.2).
- `regrid` AST op in all five bindings (§5.3).
- Canonical AST form in all five bindings (§5.4).
- Arrayed-variable schema: `shape`, `location` on `variables.<name>` (§10.2).
- Model-level `boundary_conditions` section (§9).
- `passthrough` annotation on equations / BCs (§11).
- `rules.max_passes` model-level override (§5.2.5).
- Migration tooling: the `spec.migrate_0_1_to_0_2` convention (§16), with
  a command-line verb `esm migrate` in each binding that performs the
  BC relocation rule.
- A schema-migration fixture test (bead filed as follow-up to gt-yx9y)
  with at least three input files carrying `domains.<d>.boundary_conditions`
  and their expected 0.2-form equivalents.

**Acceptance:**

- All five bindings parse, canonicalize, and serialize every fixture in
  `tests/conformance/discretization/infra/` to the byte-identical canonical
  form.
- `esm migrate` on the three schema-migration fixtures produces expected
  output (tests/conformance/migration/0_1_to_0_2/*).
- No `rules` / `discretizations` / `grids` section is exercised yet — Step 1
  is pure infrastructure.

#### Step 1b — Rectangular grids, first scheme set (absorbs prior Step 1 schemes)

**Scope:** `cartesian` family, uniform spacing, periodic BCs. Centered and
upwind stencils for `grad` and `laplacian`.

**Acceptance:**
- Julia binding reproduces the `ArrayDiscretization` output captured as
  fixtures in `tests/conformance/discretization/rect_1d_*.esm` and
  `rect_2d_diffusion_5point_periodic.esm`. These fixtures were produced
  once from MethodOfLines.jl PR #531 at commit SHA pinned in the fixture
  header; subsequent upstream changes to that PR do not invalidate the
  fixtures (resolves M7).
- Rust binding emits bit-identical canonical AST.
- Python, Go, TS bindings: `index`-extension and rule-engine already
  present from Step 1; need not emit discretized output yet, but must
  round-trip the fixtures without loss.

The MVP fixtures are:

- `rect_1d_advection_centered_periodic.esm`
- `rect_1d_advection_upwind_periodic.esm`
- `rect_2d_diffusion_5point_periodic.esm`

#### Step 2 — Dirichlet / Neumann / Robin BCs

**Scope:** Model-level `boundary_conditions`. BC rewrite rules with `emit`
(or `value`) + `produces`. Ghost-cell `produces` variant. Time-dependent
BCs from loaders (§8.A.3). Auto scalar→indexed metric rewrite for
non-uniform spacing (§6.2.1) — this folds in what v1 called Step 3.

**Acceptance:**
- All three BC kinds on a 1D diffusion problem match an analytic reference
  to 1e-12 per cell in a Julia runtime solve.
- Conformance harness gains fixtures (Dirichlet at xmin, Neumann at xmax,
  Robin at both sides, mixed, SST-forced Dirichlet from a loader). Julia
  + Rust bit-identical.
- A non-uniform 1D diffusion fixture on a stretched grid (geometric
  progression) round-trips Julia → ESM → Rust bit-identical.

#### Step 3 — Unstructured neighbor + reduction selectors (MPAS)

**Scope:** `unstructured` family. `indirect` and `reduction` selectors.
`connectivity` tables. `kind: "mesh"` data loader (§8.A). Scheme set:
MPAS edge-gradient + cell-divergence (§7.3).

**Acceptance:**
- An icosahedral-mesh diffusion problem is discretized from
  `.esm` + an MPAS mesh loader and solved; Julia + Rust emit bit-identical
  canonical AST.
- Full MPAS `x1.2562` mesh loads and the discretization step completes
  without error in both Julia and Rust (solve step not required in CI).

#### Step 4 — Cubed-sphere panel-aware selector

**Scope:** `cubed_sphere` family. `panel` selector. `panel_connectivity`
tables with the `gnomonic_c6_*` builtins. D₄ `axis_flip` action (§6.4.1).
FV-flux scheme parity with `EarthSciDiscretizations.jl` on the C48 cubed
sphere. `regrid` op wraps cross-panel references.

**Acceptance:**
- Steady-state advection on C48 matches `EarthSciDiscretizations.jl` to
  round-off in a Julia runtime solve.
- Rust emits bit-identical canonical AST for the discretization-only step;
  solve step is out of scope for the Rust conformance test.

## 14. Risks and open questions

1. **Pattern-matcher vocabulary.** §5.2.4 ships a closed guard list. Known
   limitations (review m6), explicitly acknowledged as out of MVP:
   - Negation guards.
   - Constant-folding guards (is-numeric-literal).
   - Arity guards (n-ary vs. binary `+`).
   - Structural guards (subtree-contains).
   These can be added with a minor spec version bump once scheme authors
   demonstrate the need.
2. **Rule ordering.** Deterministic top-down fixed-point (§5.2.5) is
   adequate for the current schemes. If two rules legitimately match the
   same subtree, the first-listed rule wins; authors can reorder to express
   priority explicitly. Non-convergence aborts with `E_RULES_NOT_CONVERGED`.
3. **Ghost-cell lifetime.** `produces: ghost_var` declares a variable that
   exists only in the discretized system; the loader must reject a pre-
   discretization `.esm` that references a `ghost_var` (§9.4). This is a
   validator rule, shipped in Step 1.
4. **Loader determinism.** Mesh loaders expose a `determinism` block
   (§8.A). Bindings that cannot guarantee the declared endian / format /
   integer width must reject at load.
5. **Cache scope.** Expression-kind metric generators cache per-session
   within the rewriting binding (resolves review Q4). Cross-session
   caching is a runtime concern and is not part of the spec.
6. **ODE/DAE assembler coverage.** Per §12, each binding must declare its
   DAE assembler or reject algebraic-producing rewrites (resolves review
   Q5). This is a binding-documentation requirement, not a spec gap.
7. **Spec-version gate.** The RFC is a breaking change (0.1 → 0.2) but
   Steps 2, 3, 4 extend 0.2 additively within 0.2.x. Step 1 lands the
   0.2.0 release; subsequent steps roll in as 0.2.x minor versions.

## 15. Why not alternatives

### 15.1 MLIR / StableHLO as the discretized IR

**Rejected.** MLIR is a compiler IR; emitting it as a sibling format would
either (a) double the authoring surface (`.esm` for continuous, `.mlir` for
discretized) — violating §1 goal 5 — or (b) require the `.esm` AST to
embed MLIR textual payloads, pushing round-trip fidelity onto every binding
and re-introducing the "math parser" dependency §4 of the base spec forbids.
Additionally, MLIR's dialect space is a moving target; pinning to a dialect
would couple ESM's stability to LLVM's release cadence. We prefer the
in-format `arrayop` lowering (§7.3) for MPAS because it reuses the existing
AST and stays diff-friendly.

### 15.2 SymPy Wild / Replacer DSL

**Rejected as an on-wire format; subset borrowed for §5.2.** SymPy's
`Wild`/`Replacer` has well-tested semantics and arguably richer guards
than the RFC's closed vocabulary (§5.2.4). But Wild/Replacer is not
serializable without a Python runtime, and several of its features (AC
matching, non-commutative Wild) are precisely the features §5.2.3 rejects
for cross-binding determinism. The RFC's pattern language *is* a subset of
SymPy's Replacer, intentionally: binding-authors who want richer matching
can compose multiple rules, at the cost of verbosity — not at the cost of
cross-binding divergence.

### 15.3 OpenFOAM `fvSchemes` as the architectural analog

**Partially accepted; see §8 `data_loaders` and §9 BC scheme contributions.**
Review gt-tlw2 is right that OpenFOAM's field-operator formalism is the
closest architectural analog: `fvc::grad(p)` with the scheme chosen from
`fvSchemes`, plus stored boundary conditions on the mesh, is a near-mirror
of `{grid, discretizations, rules}` with model-level `boundary_conditions`.
The RFC differs from OpenFOAM in three deliberate ways:

1. **Declarative, not callable.** `fvc::grad` is a C++ function that
   resolves at link time against a scheme library. ESM rules are data; a
   `.esm` file carries the rule binding explicitly, so the same file runs
   under any conforming binding. This is the cross-language commitment
   from §1.
2. **Symbolic coefficients, not runtime arrays.** OpenFOAM's schemes
   materialize matrix coefficients numerically; ESM's schemes emit
   symbolic AST and defer numerics to the ODE/DAE assembler. This is
   what lets §13 demand bit-identity.
3. **Grid families are closed; schemes are open.** OpenFOAM's
   `fvSchemes` assumes a polyhedral FV mesh. ESM declares three grid
   families up front (cartesian, cubed_sphere, unstructured) and closes
   that list at v0.2; new families require a spec version bump. This
   trades OpenFOAM's flexibility for cross-binding testability.

Authors coming from OpenFOAM should find ESM's authoring surface familiar.
The RFC's choice to model schemes as data (rather than library hooks) is
the specific departure.

### 15.4 `makearray + single arrayop` compression

**Rejected for the general case, accepted for reductions (§7.3).**
Review gt-tlw2 correctly notes that the v1 rejection of "fully-materialized
arrayop" was too strong. For *rectangular* interior regions the output
compresses to a single `makearray` with one `arrayop` body — O(1) file
size. But boundary regions (ghost cells, side-specific rules) require
region-specific rewrites; a single arrayop per region is necessary.
The MVP keeps interior regions as per-cell expressions (consistent with
MOL PR #531's output) and uses `arrayop` for reductions (§7.3). A later
optimization pass could collapse identical per-cell forms into `makearray`
without any schema change — this is a runtime/binding concern and out of
scope for v0.2.

### 15.5 Reuse the existing `operators` section as opaque transforms

**Rejected.** Spec §9 `operators` registers opaque, binding-specific
transforms with only an input/output descriptor. Using it for
discretization would satisfy §1 goal 5 (no second format) but fail goal 3
(bit-identical output): the transform is a runtime box, not a data-level
spec, so two bindings can legitimately produce different ASTs. This is
the status-quo-plus option the RFC set out to replace.

### 15.6 Status quo (runtime side-effect)

**Rejected by the architectural goal.** Every non-Julia binding currently
cannot round-trip discretized PDEs; this RFC exists because that gap is
blocking.

### 15.7 Introduce a second file format for discretized systems

**Rejected.** Every additional format is a perennial cross-language-drift
liability; this is the mistake §15.1 would make in a different dialect.

## 16. Deliverable checklist

This RFC is the deliverable of gt-dq0f (v1) and gt-yx9y (v2 revision).
Implementation work is tracked separately under the 4-step rollout. On
acceptance of this RFC:

- `spec.version` bumps to `0.2.0-draft` on the branch that lands Step 1,
  and to `0.2.0` on merge of Step 1 to main.
- `esm-schema.json` gains JSON-schema entries for:
  - `grids` section (per §6)
  - `discretizations` section (per §7)
  - `rules` section (per §5.2 and §9)
  - Extended `index` contexts (per §5.1)
  - `regrid` op (per §5.3)
  - `variables.<name>.shape` and `.location` (per §10.2)
  - Model-level `boundary_conditions` (per §9)
  - `data_loaders.<ℓ>.kind: "mesh"` (per §8.A)
  - `rules.max_passes`, `passthrough` flags (per §5.2.5, §11)
- `esm-spec.md` gains:
  - A new top-level section §16 "Discretization" that cross-references
    this RFC for rationale and §6/§7/§5 for normative grammar.
  - Inline §6.1 amendment adding `shape` / `location` fields to variables.
  - Inline §8 amendment adding `kind: "mesh"` to data loaders.
  - **Removal** of §11.5 `boundary_conditions` from the `domains` schema.
- `CONFORMANCE_SPEC.md` gains:
  - `discretization/` fixture class (per Steps 1b–4).
  - `migration/0_1_to_0_2/` fixture class for the breaking change.
- A new **migration tool** per binding, invokable as `esm migrate
  <infile.esm> <outfile.esm>`, that applies the `spec.migrate_0_1_to_0_2`
  convention (below).
- A follow-up bead (to be filed) for a schema-migration fixture-test suite
  under `tests/conformance/migration/` with at least three input fixtures.

### 16.1 The `spec.migrate_0_1_to_0_2` convention

A file carrying `spec.version: "0.1"` is migrated to `0.2` by applying:

1. **BC relocation.** For each `domains.<d>.boundary_conditions[k]`:
   - Find every `models.<M>` with `models.<M>.domain == "<d>"`.
   - For each such model and each variable whose domain includes the BC's
     `side`, emit a `models.<M>.boundary_conditions["<auto-key>"]` entry
     with `variable`, `side`, `kind`, and `value`/`robin_*` copied from
     the domain-level entry.
   - Delete `domains.<d>.boundary_conditions`.
2. **Bump version.** Set `spec.version = "0.2.0"`.
3. **Add marker.** Set `spec.migrated_from = "0.1"` for provenance (loaders
   must preserve this field on subsequent saves).

The migration is 1-to-1 per (domain-BC × applicable variable). If a single
domain-level `periodic` BC applies to five models, it fans out to five
model-level entries; this is intentional (explicit per-model BC makes the
eventual rewrite rules straightforward).

A binding may expose the migration as a one-off verb (`esm migrate`) or
fold it into its loader for `version < 0.2` files. The canonical output
of the migration is defined by Step 1 fixtures (`tests/conformance/
migration/0_1_to_0_2/`), so all bindings migrate to the same byte form.

## 17. Review response

This section summarizes how v2 addresses the critical and major review
findings in `docs/rfcs/discretization-review.md`, so a second reviewer can
diff quickly.

**Critical issues:**

- **C1 (idx vs index).** Resolved: `idx` dropped; §5.1 extends `index`
  contexts and documents composite index expressions and non-`arrayop`
  resolution semantics.
- **C2 (BCs duplicate domain BCs).** Resolved: §9 introduces model-level
  `boundary_conditions`; §10.1 documents removal of
  `domains.<d>.boundary_conditions` as a breaking change; §16.1 gives
  the migration rule.
- **C3 (canonical form missing).** Resolved: §5.4 defines canonical form
  normatively (argument ordering, n-ary flattening, zero/identity
  elimination, integer/float non-promotion, string-vs-number canonical).
  A worked example and byte-exact output is given. §13 acceptance
  explicitly tests post-canonicalization bit-identity.
- **C4 (metric loader refs a nonexistent extension).** Resolved: §8
  amendments (§8.A) extend `data_loaders` with `kind: "mesh"` inline, so
  Step 3 acceptance is provable.
- **C5 (pattern-match semantics underspecified).** Resolved: §5.2.1
  defines binding classes per position; §5.2.2 pins non-linear patterns
  to post-canonicalization AST-equality; §5.2.3 rejects AC matching and
  explains why; §5.2.4 enumerates legal sibling-field positions; §5.2.5
  picks termination rule (i) with a pass budget. §5.2.6 ships a one-page
  worked example.

**Major issues:**

- **M1 (scalar dx vs dx[i]).** Resolved: §6.2.1 option (b) — engine
  auto-rewrites scalar metric refs to `index` when `spacing: "nonuniform"`.
- **M2 (MPAS variable-valence).** Resolved: §4 + §7 add the `reduction`
  selector; §7.3 ships a worked MPAS divergence that lowers to `arrayop`.
- **M3 (`$e` target binding).** Resolved: §7.1.1 defines `$target` and
  its components per grid family; `$e` for edge-operand schemes is an
  implicit alias for `$target`.
- **M4 (axis_flip group action).** Resolved: §6.4.1 enumerates the D₄
  action with an 8-row table.
- **M5 (time-dependent loader BCs).** Resolved: §8.A.3 specifies the
  mechanism end-to-end; `t` is explicit, face coords declared via
  `face_coords` on the BC entry.
- **M6 (arrayed variables have no schema).** Resolved: §10.2 adds
  `shape` and `location` to `variables.<name>` inline.
- **M7 (PR #531 moving target).** Resolved: §13 Step 1b captures outputs
  as fixtures and states acceptance as "fixtures pass"; PR #531 cited as
  origin of the initial fixture set, not an ongoing pin.
- **M8 (rollout skipped infrastructure).** Resolved: §13 rewritten. Step 1
  is pure infrastructure (rule engine, canonical form, index extension,
  arrayed-variable schema, BC-op schema, migration tooling). Step 1b is
  the first scheme set. Steps 2, 3, 4 follow.

**Minor issues:**

- **m1 (`grid_spacing` duplication).** Addressed in §6.1: domain-level
  field becomes advisory when a grid refines the domain.
- **m2 (panel selector worked example).** Addressed in §6.4.2.
- **m3 (`<analytic on cube>` placeholder).** Addressed in §6.4 example
  (concrete gnomonic metric using `atan2`, `cos`).
- **m4 (guard name inconsistency).** Addressed: renamed to
  `dim_is_spatial_dim_of` (§5.2.4).
- **m5 (spatialization responsibility vague).** Addressed in §11
  pipeline Step 2.
- **m6 (closed vocabulary risks).** Addressed in §14 risk 1 as a
  known-limitations list.
- **m7 (CSV loader by name).** Addressed: §13 Step 2 fixtures do not
  promise a CSV loader; the `loader:` form points to whatever loader the
  fixture declares (`zlev_csv` in §6.2 is an authored loader name, not a
  schema-reserved one).
- **m8 (two-stage matching).** Clarified in §7.1: a rule fires first; a
  scheme's `applies_to` is matched against the rule's `$u` / `$target`
  binding at expansion time. There is no second pass of rule matching
  against `applies_to`.
- **m9 (`produces: state_var`).** Removed from MVP (§9.4).

**Review questions:**

- **Q1 (nested scheme determinism).** §5.2.5 termination rule (i): a
  rewritten subtree is not re-matched in the same pass. Cross-pass
  ordering is top-down each time. This gives determinism.
- **Q2 (schema-validation reach).** §16 deliverable explicitly enumerates
  the JSON-schema additions. Rule-cycle detection, pattern-variable
  scoping, and grid/scheme compatibility are loader-side validations
  beyond what JSON Schema can encode.
- **Q3 (rule miss behavior).** §11 Step 7 errors by default;
  `passthrough: true` opts out.
- **Q4 (output caching).** §14 risk 5: per-session, within the rewriting
  binding.
- **Q5 (DAE interop assumption).** §12 pins the binding contract: DAE
  assembler or explicit error.
- **Q6 (coupling × rewrite).** §11 Step 4 runs coupling before rewrite;
  §5.3 `regrid` wraps cross-grid references.

---

*End of v2.*
