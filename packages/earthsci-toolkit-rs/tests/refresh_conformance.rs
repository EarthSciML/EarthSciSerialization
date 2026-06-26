#![cfg(not(target_arch = "wasm32"))]
//! Cross-language REFRESH-PATH conformance for the Rust binding (bead
//! `ess-14f.12` / RS-R4, parent `ess-14f`; plan `esio-consumer-rust-plan`;
//! CONFORMANCE_SPEC.md §5.10).
//!
//! Drives the Rust discrete-cadence refresh consumer over the shared OFFLINE
//! fixture in `tests/conformance/refresh/` and asserts it reproduces the analytic
//! golden the Python and Julia siblings reproduce too — golden agreement *is*
//! cross-binding agreement (the same discipline as §5.7 cadence and §5.9 PDE).
//!
//! This is the **composition** capstone over two pieces that already have their
//! own conformance sets: §5.7 pins *which cadence class* each node is, §5.8 pins
//! the *regrid kernel geometry*; here we pin that the refresh executor composes
//! them — `refresh(t)` → **regrid** native→sim grid → write forcing buffer →
//! integrate the segment — into the same **refreshed+regridded arrays** and the
//! same **integrated trajectory** as the reference.
//!
//! Two bands (tolerances + grids read from the shared manifest/golden, never
//! hard-coded here):
//!
//! * **regrid band** — the forcing-buffer arrays after each refresh equal
//!   `golden.regridded_fields`. The genuine [`conservative_regrid`] kernel does a
//!   2:1 area-weighted coarsening of the coarse 6-cell native grid onto the
//!   3-cell sim grid; the distinct paired native values (`0` and `2` → `1`) make
//!   the averaging load-bearing — an `IdentityRegrid` pass-through fails here.
//! * **trajectory band** — each segment-boundary state equals
//!   `golden.trajectory` (piecewise-constant forcing ⇒ closed form).

use std::collections::HashMap;
use std::path::PathBuf;

use earthsci_toolkit::conservative_regrid;
use earthsci_toolkit::flatten::flatten;
use earthsci_toolkit::geometry::Manifold;
use earthsci_toolkit::provider::{
    CadenceProvider, ForcingBuffer, NativeField, ProviderError, RefreshExecutor, Regrid,
};
use earthsci_toolkit::simulate_array::ArrayCompiled;
use earthsci_toolkit::{SimulateOptions, Solution, SolverChoice, load};
use ndarray::{ArrayD, IxDyn};
use serde_json::Value;

// ===========================================================================
// Shared-tree access (mirrors cadence_conformance.rs / geometry_conformance.rs)
// ===========================================================================

/// Repo root = the crate dir's grandparent (`packages/earthsci-toolkit-rs/../..`).
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repo root resolves")
}

fn load_json(rel: &str) -> Value {
    let path = repo_root().join(rel);
    let text = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {path:?}: {e}"));
    serde_json::from_str(&text).unwrap_or_else(|e| panic!("parse {path:?}: {e}"))
}

fn f64s(v: &Value) -> Vec<f64> {
    v.as_array()
        .expect("array of numbers")
        .iter()
        .map(|x| x.as_f64().expect("number"))
        .collect()
}

/// `|got - want| <= atol + rtol*|want|`, the standard mixed tolerance.
fn close(got: f64, want: f64, rtol: f64, atol: f64) -> bool {
    (got - want).abs() <= atol + rtol * want.abs()
}

// ===========================================================================
// The two views of one shared fixture (see tests/conformance/refresh/README.md)
// ===========================================================================

/// Strip loader-fed `discrete` variables from every model so the typed
/// array-simulate compiler (no `Discrete` variable type) sees `src`/`scale` as
/// **forcing names** resolved through the live buffer. The raw document is left
/// to the cadence classifier untouched. Mirrors the two-literal split in
/// `segmented_refresh_solve.rs`, here derived from one shared file.
fn simulate_view(full: &Value) -> Value {
    let mut doc = full.clone();
    if let Some(models) = doc.get_mut("models").and_then(|m| m.as_object_mut()) {
        for (_name, model) in models.iter_mut() {
            if let Some(vars) = model.get_mut("variables").and_then(|v| v.as_object_mut()) {
                vars.retain(|_k, v| v.get("type").and_then(|t| t.as_str()) != Some("discrete"));
            }
        }
    }
    doc
}

/// Build the coupled `ArrayCompiled` from the simulate view of the fixture.
fn build_compiled(full: &Value) -> ArrayCompiled {
    let stripped = serde_json::to_string(&simulate_view(full)).expect("serialize simulate view");
    let file = load(&stripped).expect("load simulate view");
    let flat = flatten(&file).expect("flatten simulate view");
    ArrayCompiled::from_flattened(&flat).expect("from_flattened compiles coupled forced model")
}

// ===========================================================================
// Offline provider seeded from the golden's native fields
// ===========================================================================

/// An in-memory [`CadenceProvider`] feeding ONE forcing variable from the
/// golden's OFFLINE `native_fields` — the test stand-in for the EarthSciIO Rust
/// Provider. CONST loaders carry a `materialize` baseline; DISCRETE loaders carry
/// an anchor→native-field schedule. No I/O.
struct GoldenProvider {
    out_key: String,
    const_value: Option<Vec<f64>>,
    schedule: Vec<(f64, Vec<f64>)>,
}

impl GoldenProvider {
    fn const_loader(out_key: &str, value: Vec<f64>) -> Self {
        Self {
            out_key: out_key.to_string(),
            const_value: Some(value),
            schedule: Vec::new(),
        }
    }
    fn discrete_loader(out_key: &str, schedule: Vec<(f64, Vec<f64>)>) -> Self {
        Self {
            out_key: out_key.to_string(),
            const_value: None,
            schedule,
        }
    }
}

/// A 1-D native field from a value vector, tagging its native x-centers as coords
/// (documentation only — this fixture's source/target grids are fixed by the
/// shared manifest, so the regrid below holds them; a production ESD bridge would
/// instead derive the source rings from `native.coords`).
fn native(values: &[f64]) -> NativeField {
    let mut field =
        NativeField::new(ArrayD::from_shape_vec(IxDyn(&[values.len()]), values.to_vec()).unwrap());
    let centers: Vec<f64> = (0..values.len()).map(|k| k as f64 + 0.5).collect();
    field.coords.insert("x".to_string(), centers);
    field
}

impl CadenceProvider for GoldenProvider {
    fn materialize(&mut self) -> Result<HashMap<String, NativeField>, ProviderError> {
        let v = self
            .const_value
            .clone()
            .expect("materialize on a provider with no CONST baseline");
        Ok(HashMap::from([(self.out_key.clone(), native(&v))]))
    }
    fn refresh(&mut self, t: f64) -> Result<Option<HashMap<String, NativeField>>, ProviderError> {
        for (anchor, value) in &self.schedule {
            if *anchor == t {
                return Ok(Some(HashMap::from([(self.out_key.clone(), native(value))])));
            }
        }
        Ok(None)
    }
    fn refresh_times(&self) -> Vec<f64> {
        self.schedule.iter().map(|(t, _)| *t).collect()
    }
}

// ===========================================================================
// The genuine regrid seam: a conservative native→sim-grid remap
// ===========================================================================

/// A [`Regrid`] that conservatively remaps a 1-D native field onto the sim grid
/// using the library's [`conservative_regrid`] kernel — the SAME kernel the §5.8
/// geometry conformance and the Python/Julia consumers reproduce. The source and
/// target cells are 1-D intervals (`*_grid_edges` from the golden) lifted to unit
/// planar rectangles `[x0,x1] × [0,1]`, so the overlap areas are exact and the
/// remap reduces to an area-weighted average — but it runs through the real
/// polygon-overlap kernel, not a shortcut.
struct ConservativeRegrid {
    src_rings: Vec<Vec<(f64, f64)>>,
    tgt_rings: Vec<Vec<(f64, f64)>>,
    atol: f64,
}

/// Unit-height planar rectangles from 1-D cell edges: cell k = `[edges[k], edges[k+1]] × [0,1]`.
fn unit_rings(edges: &[f64]) -> Vec<Vec<(f64, f64)>> {
    edges
        .windows(2)
        .map(|w| vec![(w[0], 0.0), (w[1], 0.0), (w[1], 1.0), (w[0], 1.0)])
        .collect()
}

impl ConservativeRegrid {
    fn from_golden(regrid: &Value) -> Self {
        let src = f64s(&regrid["source_grid_edges"]);
        let tgt = f64s(&regrid["target_grid_edges"]);
        assert_eq!(
            regrid["method"].as_str(),
            Some("conservative"),
            "this adapter implements the conservative method"
        );
        assert_eq!(
            regrid["manifold"].as_str(),
            Some("planar"),
            "planar manifold"
        );
        Self {
            src_rings: unit_rings(&src),
            tgt_rings: unit_rings(&tgt),
            atol: 1e-12,
        }
    }
}

impl Regrid for ConservativeRegrid {
    fn regrid(&self, _var: &str, native: &NativeField) -> Result<ArrayD<f64>, ProviderError> {
        let f_src: Vec<f64> = native.array.iter().copied().collect();
        if f_src.len() != self.src_rings.len() {
            return Err(ProviderError(format!(
                "native field length {} != source cell count {}",
                f_src.len(),
                self.src_rings.len()
            )));
        }
        let (f_tgt, _a, _aj) = conservative_regrid(
            &f_src,
            &self.src_rings,
            &self.tgt_rings,
            Manifold::Planar,
            self.atol,
        )
        .map_err(|e| ProviderError(format!("conservative_regrid: {e}")))?;
        Ok(ArrayD::from_shape_vec(IxDyn(&[f_tgt.len()]), f_tgt).unwrap())
    }
}

// ===========================================================================
// Wiring + the segmented driver (the user-owned harness, not library API)
// ===========================================================================

/// Build the refresh executor for `full` (classifier view), seeded offline from
/// `golden.native_fields`, with the conservative regrid from `golden.regrid`.
fn build_executor(full: &Value, golden: &Value) -> RefreshExecutor {
    let nat = &golden["native_fields"];

    // CONST loaders → one GoldenProvider each (materialize baseline).
    // DISCRETE loaders → anchor→native schedule.
    // The fixture wires emis(DISCRETE)→Box.src, factors(CONST)→Box.scale.
    let scale = f64s(&nat["Box.scale"]["values"]);
    let factors = GoldenProvider::const_loader("Box.scale", scale);

    let by_anchor = nat["Box.src"]["by_anchor"]
        .as_object()
        .expect("Box.src.by_anchor");
    let mut schedule: Vec<(f64, Vec<f64>)> = by_anchor
        .iter()
        .map(|(k, v)| (k.parse::<f64>().expect("anchor key is a number"), f64s(v)))
        .collect();
    schedule.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let emis = GoldenProvider::discrete_loader("Box.src", schedule);

    let providers: HashMap<String, Box<dyn CadenceProvider>> = HashMap::from([
        (
            "emis".to_string(),
            Box::new(emis) as Box<dyn CadenceProvider>,
        ),
        (
            "factors".to_string(),
            Box::new(factors) as Box<dyn CadenceProvider>,
        ),
    ]);

    let regrid = ConservativeRegrid::from_golden(&golden["regrid"]);
    RefreshExecutor::new(&full["models"]["Box"], full, providers, Box::new(regrid))
        .expect("classify + pair providers")
}

fn base_opts() -> SimulateOptions {
    SimulateOptions {
        solver: SolverChoice::Bdf,
        abstol: 1e-10,
        reltol: 1e-8,
        max_steps: 100_000,
        output_times: None,
    }
}

fn zero_ics(compiled: &ArrayCompiled) -> HashMap<String, f64> {
    compiled
        .state_variable_names()
        .iter()
        .map(|n| (n.clone(), 0.0))
        .collect()
}

fn final_value(sol: &Solution, name: &str) -> f64 {
    let row = sol
        .state_variable_names
        .iter()
        .position(|n| n == name)
        .unwrap_or_else(|| {
            panic!(
                "state slot {name:?} not found; have {:?}",
                sol.state_variable_names
            )
        });
    *sol.state[row].last().expect("at least one output time")
}

/// Segmented solve that records each segment-boundary's full state (the
/// trajectory), refreshing the forcing once per boundary and threading state.
fn segmented_trajectory(
    compiled: &ArrayCompiled,
    exec: &mut RefreshExecutor,
    forcing: &ForcingBuffer,
    tspan: (f64, f64),
) -> Vec<(f64, HashMap<String, f64>)> {
    let (t0, t_end) = tspan;
    exec.materialize_const(forcing).expect("materialize const");

    let mut endpoints = vec![t0];
    for t in exec.refresh_times() {
        if t > t0 && t < t_end {
            endpoints.push(t);
        }
    }
    endpoints.push(t_end);

    let mut ics = zero_ics(compiled);
    let mut trajectory = Vec::new();
    for pair in endpoints.windows(2) {
        let (seg_start, seg_end) = (pair[0], pair[1]);
        exec.refresh_at(seg_start, forcing)
            .expect("refresh at boundary");

        let mut opts = base_opts();
        opts.output_times = Some(vec![seg_end]);
        let sol = compiled
            .simulate((seg_start, seg_end), &HashMap::new(), &ics, &opts)
            .expect("segment solve");

        let state: HashMap<String, f64> = compiled
            .state_variable_names()
            .iter()
            .map(|n| (n.clone(), final_value(&sol, n)))
            .collect();
        ics = state.clone();
        trajectory.push((seg_end, state));
    }
    trajectory
}

// ===========================================================================
// Tests
// ===========================================================================

/// The conformance dir the manifest's relative `fixture`/`golden` paths resolve against.
const REFRESH_DIR: &str = "tests/conformance/refresh";

fn fixture_and_golden() -> (Value, Value) {
    let manifest = load_json(&format!("{REFRESH_DIR}/manifest.json"));
    let fx = &manifest["fixtures"][0];
    let full = load_json(&format!(
        "{REFRESH_DIR}/{}",
        fx["fixture"].as_str().expect("fixture path")
    ));
    let golden = load_json(&format!(
        "{REFRESH_DIR}/{}",
        fx["golden"].as_str().expect("golden path")
    ));
    (full, golden)
}

fn tolerances() -> (f64, f64, f64, f64) {
    let manifest = load_json(&format!("{REFRESH_DIR}/manifest.json"));
    let t = &manifest["tolerances"];
    (
        t["regrid_rtol"].as_f64().unwrap(),
        t["regrid_atol"].as_f64().unwrap(),
        t["traj_rtol"].as_f64().unwrap(),
        t["traj_atol"].as_f64().unwrap(),
    )
}

/// The fixture's two views both build: the simulate view compiles to the coupled
/// state vector, and the classifier view resolves the loader cadence (CONST
/// `factors`, DISCRETE `emis` driving the anchors).
#[test]
fn fixture_builds_both_views() {
    let (full, golden) = fixture_and_golden();
    let compiled = build_compiled(&full);
    for slot in ["Box.c[1]", "Box.c[3]", "Sink.d[1]", "Sink.d[3]"] {
        assert!(
            compiled.state_variable_names().iter().any(|n| n == slot),
            "expected coupled state slot {slot}, have {:?}",
            compiled.state_variable_names()
        );
    }
    let exec = build_executor(&full, &golden);
    assert_eq!(
        exec.refresh_times(),
        f64s(&golden["cadence"]["refresh_times"]),
        "DISCRETE anchors (CONST adds none) must match the golden cadence"
    );
}

/// Regrid band: the forcing-buffer arrays after `materialize_const` (CONST
/// `Box.scale`) and after each `refresh_at` anchor (DISCRETE `Box.src`) equal the
/// golden's regridded fields — the conservative 2:1 coarsening of the coarse
/// native grid, run through the real kernel.
#[test]
fn refreshed_regridded_arrays_match_golden() {
    let (full, golden) = fixture_and_golden();
    let (rg_rtol, rg_atol, _, _) = tolerances();
    let compiled = build_compiled(&full);
    let mut exec = build_executor(&full, &golden);
    let forcing = compiled.forcing_handle();

    // CONST: materialized once.
    exec.materialize_const(&forcing).expect("materialize const");
    let want_scale = f64s(&golden["regridded_fields"]["Box.scale"]);
    {
        let buf = forcing.borrow();
        let got: Vec<f64> = buf["Box.scale"].iter().copied().collect();
        assert_regrid("Box.scale", &got, &want_scale, rg_rtol, rg_atol);
    }

    // DISCRETE: refreshed once per anchor; the buffer holds the regridded field.
    let src_anchors = golden["regridded_fields"]["Box.src"]["by_anchor"]
        .as_object()
        .expect("Box.src.by_anchor");
    for t in f64s(&golden["cadence"]["refresh_times"]) {
        exec.refresh_at(t, &forcing).expect("refresh at anchor");
        let key = format!("{t:.1}");
        let want = f64s(
            src_anchors
                .get(&key)
                .unwrap_or_else(|| panic!("golden anchor {key}")),
        );
        let buf = forcing.borrow();
        let got: Vec<f64> = buf["Box.src"].iter().copied().collect();
        assert_regrid(&format!("Box.src @ t={key}"), &got, &want, rg_rtol, rg_atol);
    }
}

fn assert_regrid(label: &str, got: &[f64], want: &[f64], rtol: f64, atol: f64) {
    assert_eq!(
        got.len(),
        want.len(),
        "{label}: length {} != golden {}",
        got.len(),
        want.len()
    );
    for (k, (&g, &w)) in got.iter().zip(want).enumerate() {
        assert!(
            close(g, w, rtol, atol),
            "{label}[{k}] = {g}, golden {w} (regrid band rtol={rtol} atol={atol}); \
             an identity pass-through would land the un-averaged native value here"
        );
    }
}

/// Trajectory band: the full segmented refresh+regrid+integrate run reproduces
/// the analytic golden trajectory at every cadence boundary (t = 1, 2, 3).
#[test]
fn refresh_path_trajectory_matches_golden() {
    let (full, golden) = fixture_and_golden();
    let (_, _, tj_rtol, tj_atol) = tolerances();
    let compiled = build_compiled(&full);
    let mut exec = build_executor(&full, &golden);
    let forcing = compiled.forcing_handle();

    let tspan = f64s(&golden["cadence"]["tspan"]);
    let trajectory = segmented_trajectory(&compiled, &mut exec, &forcing, (tspan[0], tspan[1]));

    let golden_traj = golden["trajectory"].as_object().expect("trajectory object");
    let mut checked = 0usize;
    for (time_key, slots) in golden_traj {
        let Ok(t) = time_key.parse::<f64>() else {
            continue;
        }; // skip "comment"
        let (_, state) = trajectory
            .iter()
            .find(|(seg_end, _)| (seg_end - t).abs() < 1e-9)
            .unwrap_or_else(|| panic!("no integrated segment ending at t={t}"));
        for (slot, want) in slots.as_object().expect("slot map") {
            let w = want.as_f64().expect("number");
            let g = *state
                .get(slot)
                .unwrap_or_else(|| panic!("state slot {slot} missing"));
            assert!(
                close(g, w, tj_rtol, tj_atol),
                "trajectory t={t} {slot} = {g}, golden {w} (traj band rtol={tj_rtol} atol={tj_atol})"
            );
            checked += 1;
        }
    }
    assert!(
        checked >= 12,
        "expected to check the full coupled trajectory, only did {checked}"
    );
}

/// Guard: the regrid is genuinely non-identity. The golden's native `Box.src` at
/// the first anchor is NOT equal to its regridded image, so a binding that
/// skipped the regrid (identity pass-through) could not pass
/// `refreshed_regridded_arrays_match_golden`. Pins that the fixture exercises the
/// regrid seam rather than smuggling already-on-grid data through it.
#[test]
fn regrid_is_load_bearing() {
    let (_full, golden) = fixture_and_golden();
    let native_src0 = f64s(&golden["native_fields"]["Box.src"]["by_anchor"]["0.0"]);
    let regridded_src0 = f64s(&golden["regridded_fields"]["Box.src"]["by_anchor"]["0.0"]);
    assert_ne!(
        native_src0.len(),
        regridded_src0.len(),
        "native grid (coarse) and sim grid must differ in size"
    );
    // And the averaging is real: native [0,2,...] -> regridded [1,...], so no
    // native cell value equals the regridded cell it feeds.
    assert!(
        !native_src0.contains(&regridded_src0[0]),
        "regridded value {} should be the AVERAGE of distinct native values, not a pass-through",
        regridded_src0[0]
    );
}
