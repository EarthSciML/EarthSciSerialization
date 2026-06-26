# Refresh-Path Conformance (`tests/conformance/refresh/`)

Cross-language conformance for the **discrete-cadence loader + dependent-variable
refresh** consumer (epic `ess-14f`; bead `ess-14f.12` / RS-R4 wires the Rust
binding). Governed by **CONFORMANCE_SPEC.md §5.10**.

This set pins the **composition** the refresh consumer performs each cadence
boundary:

```
provider.refresh(t)  ->  regrid native field onto sim grid  ->  write forcing buffer  ->  integrate segment
```

It is the capstone over two pieces that already have their own conformance sets:

* **§5.7 cadence PARTITION** (`tests/conformance/cadence/`) — *which class* each
  node is (CONST / DISCRETE / CONTINUOUS) and where it materializes. No runtime
  values.
* **§5.8 regrid KERNEL geometry** (`tests/conformance/geometry/`) — the overlap
  areas / conservation invariants of a single regrid. No cadence, no integration.

§5.10 asserts the two compose to the same **refreshed+regridded arrays** and the
same **integrated trajectory** across bindings.

## Layout

| File | What it is |
|------|------------|
| `manifest.json` | Fixture list, tolerances, pinned integrators, required/optional bindings. |
| `fixtures/coupled_refresh_regrid.esm` | The shared model: a discretized, COUPLED, non-PDE forced model with one CONST and one DISCRETE loader-fed field, both delivered on a coarse 6-cell native grid. |
| `golden/coupled_refresh_regrid.json` | The analytic golden: offline native loader fields, the regridded arrays, and the integrated trajectory. |

Strictly **offline** — the providers are seeded from the golden's
`native_fields`; no network, no file I/O.

## The two-view contract (important for adapter authors)

A loader-fed field is declared `discrete` + `data_ingest` in the `.esm` so the
**cadence classifier** can resolve it CONST vs DISCRETE (its loader's `temporal`
block decides). But the **typed array-simulate compiler** has no `Discrete`
variable type — it resolves `Box.src` / `Box.scale` as **forcing names** through
the live forcing buffer. So an adapter keeps two views of the one fixture:

1. **classifier view** — the raw document, unchanged (`classify_loader_bindings`
   / the cadence partition reads the `discrete` declarations + `data_loaders`).
2. **simulate view** — the same document with the loader-fed `discrete`
   variables **stripped** from each model's `variables`, so the RHS compiler
   sees `src` / `scale` as forcing names.

This mirrors `packages/earthsci-toolkit-rs/tests/segmented_refresh_solve.rs`
(RS-R3), which kept the two views as two literals; here they derive from one
shared file.

## Adapter contract

For each fixture a binding's adapter:

1. Loads the fixture; builds the **simulate view** (strip loader-`discrete`
   vars) and compiles the coupled RHS + its forcing buffer.
2. Builds the refresh executor from the **classifier view**, wired with:
   * one provider per loader, seeded **offline** from `golden.native_fields`
     (CONST `factors` returns `Box.scale`; DISCRETE `emis` returns `Box.src` at
     each `refresh_times` anchor);
   * a **conservative** regrid (`golden.regrid`) mapping the coarse native grid
     onto the sim grid.
3. `materialize_const` once, then drives the segmented solve over
     `golden.cadence.refresh_times` ∩ `tspan`, refreshing the buffer once per
     boundary and threading state across segments.
4. **Asserts** (loudly, non-zero exit on divergence):
   * **regrid band** — the forcing-buffer arrays after each refresh equal
     `golden.regridded_fields` within `regrid_rtol` / `regrid_atol`. (Distinct
     paired native values make the averaging load-bearing — an identity
     pass-through fails here.)
   * **trajectory band** — each segment-boundary state equals
     `golden.trajectory` within `traj_rtol` / `traj_atol`.

## Tolerances

From `manifest.json` (`tolerances`); see §5.10 for the rationale.

| Band | rtol | atol |
|------|------|------|
| Regridded forcing arrays (vs analytic) | 1e-9 | 1e-11 |
| Integrated trajectory (vs analytic) | 1e-4 | 1e-6 |

The regrid band is tight (a conservative remap on exact unit areas is exact up to
floating-point); the trajectory band absorbs integrator truncation, matching the
§5.9 manufactured-solution band.

## Bindings

`bindings_required` is currently `["rust"]` — RS-R4 establishes the shared
fixture + golden and the Rust producer. The Python and Julia consumer adapters
(`ess-14f.2`, `ess-14f.6`) reproduce the same golden and move themselves into
`bindings_required` when wired.
