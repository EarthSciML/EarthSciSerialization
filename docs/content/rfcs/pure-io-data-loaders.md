---
title: "Pure-I/O data loaders: separating read-from-disk from regridding and reprojection"
description: "Strip the data loader down to a single responsibility — read/update a slice of data from disk — by moving regridding (value transfer) and reprojection (coordinate transform) out of the loader and into a model component built from existing ESD pieces. The loader's native grid is expressed once, in the shared GDD Grid format. A pure-I/O loader is then a model subsystem and a single-component file becomes externally referenceable, closing the loader-reuse gap (ESS issue #24)."
---

> **Status:** Draft proposal. **Bead:** unassigned.
> **Target repos (cross-rig):**
> - **EarthSciSerialization (ESS)** — the `.esm` schema/spec: `DataLoader`,
>   the GDD `Grid` family, subsystem inclusion (§4.7), top-level document
>   validation, and a small expression-operator-set addition (hyperbolic trig).
> - **EarthSciDiscretizations (ESD)** — a new `reprojection/` rule directory and
>   two new regridder kernels alongside the existing
>   `regridding/conservative_regrid_overlap_join.esm`.
> - **EarthSciModels (downstream)** — the `components/earthsci_data/*.esm`
>   files are rewritten into pure loader + regridding-model pairs (migration).

---

## 1. Summary

Today a `DataLoader` does three different jobs at once: it (a) locates and reads
data from disk, (b) describes the data's native grid **and** carries a coordinate
reference system (`spatial.crs` / `grid_type`), and (c) configures regridding
(`regridding.fill_value` / `extrapolation`). Conflating I/O with transformation
is the root cause of the loader-reuse gap in ESS issue #24 and of the format's
two parallel grid representations.

This RFC reduces the loader to **one** responsibility — *read/update a slice of
data from disk* — and relocates the two transformation concerns:

- **Reprojection** (coordinate transform between CRSs) → new declarative
  **ESD `reprojection/`** rules.
- **Regridding** (value transfer onto a target grid) → the existing
  **ESD `regridding/`** component, plus two new interpolation kernels (bilinear/
  nearest and staggered B-spline).

Both transforms are composed by an ordinary **model component associated with
the loader** (the ERA5/WRF-style model that already exists in every
`earthsci_data` file). The loader's *native* grid is expressed once, in the
shared **GDD `Grid`** format, rather than the bespoke `DataLoaderSpatial` schema.

A loader reduced to pure I/O is no longer a special externally-registered
artifact: it is a plain component that can be a **model subsystem** and can be
**referenced across files** when it is the sole top-level component — which is
exactly what issue #24 asked for, obtained by *subtraction* rather than by adding
a new reference channel.

## 2. Motivation

### 2.1 Immediate trigger — the loader-reuse gap (issue #24)

A coupling/simulation file that wants to drive several models from authoritative,
already-published loaders cannot reuse those loaders by reference: §4.7 subsystem
inclusion is restricted to a file containing *exactly one top-level model or
reaction system* that *must not carry `kind`*, and a `DataLoader` is identified
*by* `kind`. So a consumer must inline copies of loader definitions (which then
drift on every upstream change) or omit them (and the `.esm` is no longer
self-describing). See issue #24 for the full analysis.

### 2.2 Deeper problem — I/O conflated with transform

The reuse gap is a symptom. A loader carries `spatial.crs`/`grid_type` (a
projection) and a `regridding` block — transformation concerns — even though the
transformation target (the consuming model's grid) is not a property of the data
on disk. That conflation produces two further costs:

1. **Two grid representations.** The loader describes grids with
   `DataLoaderSpatial` (`crs` strings, a `grid_type` enum); ESD describes grids
   with the GDD `Grid` family (parametric `family` + `parameters`). The same
   geometric object has two encodings that cannot be cross-validated.
2. **The loader is "the only externally-registered mechanism"** (esm-spec §14)
   partly *because* it bundles runtime-specific regridding. Strip the regridding
   and a loader is just a typed reader — no longer categorically special.

### 2.3 Why the obvious alternatives don't work (and why this one does)

Three restructurings were considered and rejected before arriving at this design
(full reasoning preserved from the issue #24 discussion):

- **Nest the loader inside the model unchanged.** The `Model` schema has no
  `data_loaders` slot and `subsystems` is typed `oneOf:[Model, ReactionSystem,
  SubsystemRef]`; nesting needs a schema change regardless, and a loader that
  still regrids inverts ownership (loaders are shared by many consumers, each on
  its own grid).
- **Strip the file to a loader only.** A `data_loaders`-only document fails
  top-level validation today (the document `anyOf` requires `models`,
  `reaction_systems`, or a GDD `kind`), and §4.7 still requires the referenced
  single component to be a *model or reaction system*.
- **Treat the loader as a model subcomponent while it still regrids.** The
  format wires loaders and models as **coupling peers** (scoped references treat
  a `data_loaders` key as a top-level root; the coupling section connects
  "models, reaction systems, and data loaders"); a still-transforming loader is
  a peer, not a child.

The resolving insight: the loader is a subcomponent only **after** the transform
is removed from it. Once the loader is pure I/O, "loader is a subsystem of the
regridding model" is the correct ownership, the existing §4.7 mechanism applies
(with a one-line extension), and no new reference channel or fragment selector is
needed.

## 3. Design overview — a three-stage pipeline

Getting source data onto a model's grid is three composable stages:

```
 ┌────────────────────┐   ┌──────────────────────┐   ┌─────────────────────┐
 │ 1. READ SLICE      │   │ 2. REPROJECT         │   │ 3. REGRID           │
 │ data loader        │ → │ ESD reprojection/    │ → │ ESD regridding/     │
 │ (pure I/O)         │   │ (coordinate xform)   │   │ (value transfer)    │
 │ native GDD Grid    │   │ native CRS → common  │   │ → target GDD Grid   │
 └────────────────────┘   └──────────────────────┘   └─────────────────────┘
        owned by the data loader        composed by the regridding MODEL component
```

- **Stage 1 — loader.** Returns a coordinate-aware slice: raw values plus the
  *native* grid, expressed as a GDD `Grid` (including the native CRS as
  description, not as a transform). Nothing else.
- **Stage 2 — reprojection.** A declarative ESD rule transforms coordinates
  between CRSs (e.g. WRF Lambert-Conformal cell corners → lat-lon), producing
  cell geometries in a common frame. Closed-form forward **and** inverse.
- **Stage 3 — regridding.** A declarative ESD program transfers values from the
  (reprojected) source cells onto the target GDD `Grid`: conservative
  (area-weighted), interpolating (bilinear/nearest), or staggered (B-spline).

Stages 2–3 are composed by an ordinary **model** (§6). The loader is that
model's subsystem.

## 4. ESS changes — the `.esm` format

### 4.1 Data loader becomes pure I/O

`DataLoader` loses everything except what is needed to *locate, read, and slice*
bytes, plus a *description* of the native grid:

- **Removed:** the `regridding` block (`DataLoaderRegridding` = `fill_value`,
  `extrapolation`). Regridding is a model concern (§5.2, §6).
- **Replaced:** the bespoke `spatial` block (`DataLoaderSpatial` = `crs`,
  `grid_type`, `extent`, `resolution`, `staggering`) is replaced by a reference
  to / embedding of a GDD `Grid` describing the native grid (§4.2). The native
  CRS is retained — as *description of what is on disk*, used by stage 2 as the
  source CRS — but expressed in the unified grid format, and the loader performs
  **no** reprojection itself.
- **Retained:** `kind`, `source`, `temporal`, `variables`, `mesh` (for
  `kind: mesh`), `determinism`, `reference`, `metadata`.

Per Q1: the native grid (including the CRS) stays with the loader, but is
expressed in the GDD format.

This pure-I/O reduction and GDD-`Grid` native representation apply to **all**
loader kinds in scope: `grid` (the `crs`-bearing families below), `points`
(OpenAQ — native `Grid` family `unstructured`), and `mesh` (connectivity +
metric fields already live in `Grid`). None of them regrid or reproject; that is
always the model's job.

### 4.2 One grid representation — the GDD `Grid`, extended for projection

The loader's native grid is expressed using the same GDD `Grid` that ESD
discretization already uses (`discretizations/grids/...`, `discretizations/gdd/
*.gdd.json`). This unifies loader-native grids, model-target grids, and
discretization grids under one schema that can be cross-validated.

The current `Grid` (`required: [family, dimensions]`; props `connectivity`,
`description`, `domain`, `extents`, `locations`, `metric_arrays`, `parameters`)
has **no CRS / projection slot** — it cannot represent a projected native grid
such as WRF's Lambert Conformal. This RFC adds an optional projection descriptor
to `Grid`, orthogonal to the topological `family`:

```jsonc
// Grid (GDD) — added field
"crs": {
  "projection": "lambert_conformal",   // longlat | lambert_conformal | mercator | polar_stereographic | rotated_pole
  "datum": "sphere",                    // sphere(R) | WGS84 | ...
  "R": 6370000.0,                       // sphere radius, when datum=sphere
  "parameters": { "lat_1": 30.0, "lat_2": 60.0, "lat_0": 38.999996, "lon_0": -97.0 }
}
```

A geographic grid uses `projection: longlat` (the identity case). The
`crs.parameters` are exactly the parameters consumed by the stage-2 reprojection
rule (§5.1), so the descriptor that *names* the projection and the rule that
*evaluates* it share one parameter set.

> The `grid_type` enum already in `DataLoaderSpatial`
> (`latlon`/`lambert_conformal`/`mercator`/`polar_stereographic`/`rotated_pole`/
> `unstructured`) is the migration source for `crs.projection`.

### 4.3 Data loaders as model subsystems

A pure-I/O loader may appear as a subsystem of a model. Concretely, `subsystems`
gains the loader alternative:

```jsonc
// before: "subsystems": { "<name>": oneOf[Model, ReactionSystem, SubsystemRef] }
// after:  "subsystems": { "<name>": oneOf[Model, ReactionSystem, DataLoader, SubsystemRef] }
```

The regridding model (§6) declares its loader as a subsystem; the model's
equations consume the loader's variables by the existing dot-notation
(`Parent.Loader.var`) and feed them through reprojection + regridding.

### 4.4 External references to single-component files (extend §4.7)

§4.7's file-shape rule is generalized from "exactly one top-level model or
reaction system" to **"exactly one top-level model, reaction system, or data
loader."** Two concrete edits:

1. **Top-level document validity.** Add an `anyOf` branch permitting a document
   whose sole component is `data_loaders` (today the `anyOf` requires `models`,
   `reaction_systems`, or `kind: grid_discretization_descriptor`).
2. **`SubsystemRef` resolution.** A referenced file containing exactly one
   top-level data loader resolves to that loader, named by the parent's
   subsystem key — exactly as for a single model. No fragment selector is
   required because the file is single-component (this is the structural reason
   the migration in §7 splits co-located `model + loader` files).

This is the issue #24 fix: a single-loader file (or a single-model file that
*owns* its loader as a subsystem) is referenceable through the mechanism that
already exists.

### 4.5 Operator-set addition — hyperbolic trig

Verified against origin/main, the expression operator set already provides full
trig and inverse-trig (`sin`/`cos`/`tan`/`asin`/`acos`/`atan`/`atan2`),
`exp`/`log` (natural)/`log10`, `sqrt`, and `^` (power) — so the reprojection
math in §5.1 needs **no** new function operators. The one transcendental gap is
**hyperbolic trig**: `sinh`, `cosh`, `tanh` and the inverses `asinh`, `acosh`,
`atanh` are all absent.

This RFC adds them to the operator set across all three bindings + the Go/TS
generated types, spec'd with fixed signatures and tolerances exactly like the
existing transcendentals (and mirroring the pending `mod`/`round` addition in
issue #20). They are ordinary unary elementwise operators dispatched exactly like
`sin`/`exp` — no new engine *control* primitive.

Motivation: hyperbolic functions are required for the Mercator-class
reprojections named in §5.1 (the Gudermannian inverse `φ = atan(sinh(y/R))`),
round out the transcendental set for general expressiveness, and were requested
as part of this work.

> The closed **`fn` registry** (`registered_functions.md`) is a different
> mechanism — it holds only `datetime.*` + `interp.searchsorted`, and is **not**
> involved here. Trig/exp/hyperbolic are expression *operators*, not `fn`
> entries.

### 4.6 Schema / spec delta (summary)

| `$def` / artifact | Change |
|---|---|
| `DataLoaderRegridding` | **Deleted.** |
| `DataLoader.regridding` | **Removed.** |
| `DataLoaderSpatial` | **Deleted**; `DataLoader` references a GDD `Grid` for the native grid instead. |
| `Grid` | **Add** optional `crs` (projection + datum + parameters). |
| `subsystems` value | `oneOf` **gains** `DataLoader`. |
| top-level `anyOf` | **Add** a `data_loaders`-only branch. |
| `SubsystemRef` | Resolution **accepts** a single top-level data loader. |
| expression operators | **Add** `sinh`/`cosh`/`tanh`/`asinh`/`acosh`/`atanh` (§4.5). |
| esm format version | **Bumped** (breaking — §7). |

## 5. ESD changes — rules and components

### 5.1 New `reprojection/` directory

A new top-level `reprojection/` directory in ESD holds declarative coordinate
transforms, one rule per projection family, parameterized by the projection
parameters and expressed over the **expression operator set**
(`sin`/`cos`/`tan`/`asin`/`acos`/`atan`/`atan2`/`log`/`exp`/`^`/`sqrt`, plus the
new hyperbolic ops from §4.5). Each rule provides **forward** (lon,lat → x,y) and
**inverse** (x,y → lon,lat) closed-form transforms, consistent with the
declarative-or-fail principle (no imperative fallback; a projection whose inverse
is not closed-form is reported, not hacked in).

Initial coverage (the distinct projections actually used in
`EarthSciModels/components/earthsci_data`, see Appendix A):

- `reprojection/longlat.json` — geographic WGS84 identity (degenerate forward =
  inverse = identity; included so the pipeline is uniform for unprojected grids).
- `reprojection/lambert_conformal.json` — Lambert Conformal Conic, spherical,
  parameterized by `{lat_1, lat_2, lat_0, lon_0, R}`. Closed-form both
  directions (Appendix B). This is the only genuinely projected grid currently in
  use (WRF).

The remaining families in the `grid_type` enum (`mercator`,
`polar_stereographic`, `rotated_pole`) are specified as the same rule shape and
added when a dataset needs them — not pre-built speculatively. (Mercator's
inverse is where the §4.5 hyperbolic ops are first needed.)

### 5.2 Regridder kernels — conservative + interpolating + staggered

Per Q2 (and the expanded scope), ESD grows from one regridder to three, because
the loaders span field semantics — the meteorology loaders (ERA5/GEOS-FP/WRF) are
not conservatively remapped (their current `regridding` config,
`extrapolation: clamp` with per-variable overrides, is interpolation-style):

- **Existing (conservative):** `regridding/conservative_regrid_overlap_join.esm`
  — area-weighted (overlap join → clip → polygon_area → A_j → apply → normalize).
  Appropriate for flux/emissions fields (CEDS/EDGAR/NEI) where mass conservation
  matters.
- **New (interpolating):** `regridding/bilinear_regrid.esm` (and a nearest
  variant) — declarative interpolation onto the target GDD `Grid`, honoring an
  `extrapolation` policy (`clamp`/`zero`) at the boundary. Appropriate for
  cell-centered continuous meteorology fields.
- **New (staggered B-spline):** `regridding/bspline_regrid.esm` — the
  staggered-grid B-spline interpolation kernel (the EarthSciData
  `InterpolatingRegridder`), for edge/face-staggered fields such as wind
  components on Arakawa-C grids. Declarative polynomial evaluation; no
  transcendentals. **In scope** in this RFC (previously deferred).

All three are declarative `.esm` programs evaluated through the ESS engine,
selected by the regridding model (§6) by field semantics (conservative for
flux/emissions, bilinear/nearest for cell-centered continuous fields, B-spline
for staggered fields).

### 5.3 Projected grids in the GDD `Grid` family

ESD's grid construction (`discretizations/grids/`) currently builds
`cartesian`/`lat_lon`/`arakawa`/`duo` families with no projection. To hold a
projected native grid (WRF LCC), the GDD `Grid` gains the `crs` descriptor (§4.2)
and ESD adds a `lambert_conformal` grid example/fixture. Construction stays
declarative (closed-form, no iteration): the projected grid's cell-corner
coordinates are produced by applying the `reprojection/lambert_conformal.json`
**inverse** to the regular projected (x,y) lattice.

## 6. The regridding/reprojection model component (convention)

Per Q3, no new schema kind is introduced. The component that performs
reprojection + regridding is an ordinary `model` — the same `WRFCoupler`/
`LANDFIRECoupler`/… models that already exist in every `earthsci_data` file —
restructured so that:

1. it declares the (now pure-I/O) loader as a **subsystem**;
2. its equations feed the loader's slice through the ESD `reprojection/` rule for
   the loader's native `crs` and then through the ESD `regridding/` program for
   the field semantics; and
3. it exposes the regridded fields on the model's (target) GDD `Grid` for
   downstream coupling — which is what consumers reference.

**Worked example — ERA5 (geographic → model grid):**

```
ERA5 model
├── subsystems.raw  = data_loaders/era5_loader.esm   (pure I/O; native Grid: longlat 0.25°)
├── reproject:  longlat (identity) — no-op coordinate transform
└── regrid:     bilinear → model target Grid → exposes ERA5.wind, ERA5.T, ...
```

**Worked example — WRF (Lambert Conformal → model grid):**

```
WRF model
├── subsystems.raw  = data_loaders/wrf_loader.esm     (pure I/O; native Grid: lambert_conformal LCC)
├── reproject:  lambert_conformal{lat_1:30,lat_2:60,lat_0:39,lon_0:-97,R:6.37e6} → lon/lat
└── regrid:     bilinear (clamp) → model target Grid → exposes WRF.U, WRF.V, ...
              (B-spline staggered kernel for the C-grid wind components)
```

A consumer (e.g. a Camp Fire simulation) references the **WRF model** (single
top-level component, owns its loader subsystem) by `{ "ref": "./wrf.esm" }` and
gets the regridded fields — closing issue #24's use case through §4.7 alone.

## 7. Migration — hard break + lockstep (Q4)

Removing `regridding` and `DataLoaderSpatial` is breaking. Per Q4 we take a clean
flag-day cut rather than a deprecation window:

1. **Bump the esm format version.** A loader carrying `regridding` or the old
   `spatial` shape is **rejected** at load (clear error pointing here).
2. **Rewrite all ten `EarthSciModels/components/earthsci_data/*.esm` files** in
   lockstep into:
   - a **pure-I/O loader** (`source`/`temporal`/`variables` + native GDD `Grid`
     with `crs`), and
   - a **regridding model** (existing coupler model + loader subsystem +
     reproject + regrid), per §6.
   Files: `ceds`, `edgar_v81_monthly`, `era5`, `geosfp`, `landfire`,
   `ncep_ncar`, `nei2016_monthly`, `openaq`, `usgs3dep`, `wrf`. All but `wrf`
   are geographic (`longlat`, identity reprojection); `wrf` uses
   `lambert_conformal`. Emissions (`ceds`/`edgar`/`nei`) regrid **conservatively**;
   meteorology (`era5`/`geosfp`/`ncep_ncar`/`wrf`) regrid **bilinearly** (B-spline
   for staggered wind); `landfire`/`usgs3dep` (static fields) per field
   semantics; `openaq` is points.
3. **Cross-binding lockstep.** The schema change + operator addition land in all
   three ESS bindings (Julia/Rust/Python) + Go/TS generated types simultaneously;
   the ESD rules land with their conformance fixtures; EarthSciModels updates in
   the same coordinated wave.

## 8. Conformance & testing

- **Reprojection round-trip.** For each projection rule, `inverse ∘ forward ≈
  identity` to tolerance over the grid domain, cross-binding byte-identical where
  the closed-form is exact; LCC validated against known proj4 reference points.
- **Hyperbolic ops.** `sinh`/`cosh`/`tanh`/`asinh`/`acosh`/`atanh` get the same
  cross-binding value + tolerance fixtures as the existing `sin`/`exp` operators.
- **Regridding invariants.** Conservative: `Σ_j A_j F_tgt = Σ_i A_i F_src`
  (conservation) and `Σ_i W_ij = 1` (partition of unity). Bilinear: reproduction
  of linear fields exactly; boundary `clamp`/`zero` honored. B-spline:
  reproduction of the spline's polynomial degree exactly on staggered locations.
- **GDD grid parity.** A loader's migrated native `Grid` reproduces the geometry
  the old `DataLoaderSpatial` described (extent/resolution/staggering), validated
  by a fixture per migrated dataset.
- **End-to-end.** A consumer file `{ref}`-including a migrated single-component
  model resolves, regrids, and produces fields identical (to tolerance) to the
  pre-migration inline pipeline.
- **Engine.** All ESD rules are declarative `.esm` evaluated through the ESS
  engine — no new engine *control* primitive (the §4.5 hyperbolic ops are
  elementwise math, dispatched exactly like `sin`/`exp`); if a stage appears to
  need a control/guard primitive, stop and report.

## 9. Open questions / future work

1. **Iterative-inverse projections.** `longlat` and spherical `lcc` invert in
   closed form; ellipsoidal datums or `polar_stereographic` edge cases may not.
   Declarative-or-fail: report, don't add an imperative solver.
2. **Default regridding by role.** Should `metadata.tags` (emissions vs
   meteorology) drive a default conservative/bilinear/B-spline choice, or must
   the model state it explicitly? (Leaning explicit.)
3. **GDD `Grid` `crs` vs `family`.** Confirm projection belongs in a `crs`
   sub-object orthogonal to `family`, vs. new projected `family` values.

## Appendix A — Projection inventory (`earthsci_data`)

| File | Native CRS | `grid_type` | Reprojection | Regridding (proposed) |
|---|---|---|---|---|
| `wrf` | `+proj=lcc +lat_1=30 +lat_2=60 +lat_0=39 +lon_0=-97 +a=b=6.37e6` | `lambert_conformal` | LCC ↔ lonlat | bilinear (clamp) + B-spline (staggered wind) |
| `geosfp` | `+proj=longlat +datum=WGS84` (0.3125°×0.25°) | `latlon` | identity | bilinear |
| `era5` | geographic (lat-lon) | `latlon` | identity | bilinear |
| `ncep_ncar` | geographic (lat-lon) | `latlon` | identity | bilinear |
| `landfire` | `+proj=longlat +datum=WGS84` (~30 m) | `latlon` | identity | per field |
| `usgs3dep` | `EPSG:4326` (~10 m) | `latlon` | identity | per field |
| `ceds` | geographic (lat-lon) | `latlon` | identity | conservative |
| `edgar_v81_monthly` | geographic (lat-lon) | `latlon` | identity | conservative |
| `nei2016_monthly` | geographic (lat-lon) | `latlon` | identity | conservative |
| `openaq` | geographic points | `unstructured` | identity | n/a (points) |

> `era5`/`ncep_ncar`/`ceds`/`edgar`/`nei` CRS read from naming + the confirmed
> pattern (GEOSFP/LANDFIRE/USGS3DEP verified verbatim); confirm each during
> migration. The only projected grid is `wrf`.

## Appendix B — Lambert Conformal Conic (spherical), closed form

Forward (λ, φ) → (x, y), with standard parallels φ₁, φ₂, origin (λ₀, φ₀),
radius R:

```
n  = log(cos φ₁ / cos φ₂) / log( tan(π/4 + φ₂/2) / tan(π/4 + φ₁/2) )
F  = cos φ₁ · tan(π/4 + φ₁/2)^n / n
ρ  = R · F / tan(π/4 + φ/2)^n
ρ₀ = R · F / tan(π/4 + φ₀/2)^n
x  = ρ · sin( n (λ − λ₀) )
y  = ρ₀ − ρ · cos( n (λ − λ₀) )
```

Inverse (x, y) → (λ, φ), closed form:

```
ρ  = sign(n) · sqrt(x² + (ρ₀ − y)²)
θ  = atan2( x, ρ₀ − y )
λ  = λ₀ + θ / n
φ  = 2 · atan( (R F / ρ)^(1/n) ) − π/2
```

All operators (`sin`, `cos`, `tan`, `atan`, `atan2`, `log`, `^`, `sqrt`,
`sign`) are in the expression operator set (`log` = natural log; power is `^`),
so the rule is declarative and cross-language byte-comparable to tolerance.
