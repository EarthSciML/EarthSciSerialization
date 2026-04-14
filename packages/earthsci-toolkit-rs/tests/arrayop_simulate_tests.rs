//! Conformance tests for the array-op runtime (gt-oxr).
//!
//! Loads every `*.esm` fixture under
//! `../EarthSciSerialization.jl/test/fixtures/arrayop/`, compiles each model
//! through [`earthsci_toolkit::simulate`], and verifies that every assertion
//! inside every inline test matches within the declared tolerance.
//!
//! The fixtures were authored by the Julia sibling (gt-gey) to drive
//! cross-language conformance. They contain `tests`/`tolerance` blocks
//! inside each model — fields that are schema-valid but not yet carried by
//! the Rust `Model` struct. The harness parses those extra fields directly
//! from the raw JSON so the Rust implementation doesn't depend on further
//! type-system work.

#![cfg(not(target_arch = "wasm32"))]

use earthsci_toolkit::{SimulateOptions, SolverChoice, load, simulate};
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

const FIXTURE_DIRS: &[&str] = &["../EarthSciSerialization.jl/test/fixtures/arrayop"];

#[derive(Debug, Clone)]
struct Tolerance {
    rel: Option<f64>,
    abs: Option<f64>,
}

impl Tolerance {
    fn from_value(v: &Value) -> Option<Self> {
        if !v.is_object() {
            return None;
        }
        let rel = v.get("rel").and_then(|x| x.as_f64());
        let abs = v.get("abs").and_then(|x| x.as_f64());
        Some(Tolerance { rel, abs })
    }
}

#[derive(Debug, Clone)]
struct Assertion {
    variable: String,
    time: f64,
    expected: f64,
    tolerance: Option<Tolerance>,
}

#[derive(Debug, Clone)]
struct FixtureTest {
    id: String,
    initial_conditions: HashMap<String, f64>,
    t_start: f64,
    t_end: f64,
    assertions: Vec<Assertion>,
    tolerance: Option<Tolerance>,
}

#[derive(Debug, Clone)]
struct FixtureModel {
    name: String,
    tolerance: Option<Tolerance>,
    tests: Vec<FixtureTest>,
}

fn parse_fixture(json_text: &str) -> Vec<FixtureModel> {
    let root: Value = serde_json::from_str(json_text).expect("fixture is valid JSON");
    let models = match root.get("models") {
        Some(Value::Object(obj)) => obj,
        _ => return Vec::new(),
    };
    let mut out = Vec::new();
    for (mname, m) in models {
        let tolerance = m.get("tolerance").and_then(Tolerance::from_value);
        let tests_arr = m
            .get("tests")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();
        let mut tests = Vec::new();
        for t in tests_arr {
            let id = t
                .get("id")
                .and_then(|v| v.as_str())
                .unwrap_or("test")
                .to_string();
            let ic_obj = t
                .get("initial_conditions")
                .and_then(|v| v.as_object())
                .cloned()
                .unwrap_or_default();
            let mut initial_conditions: HashMap<String, f64> = HashMap::new();
            for (k, v) in ic_obj {
                if let Some(f) = v.as_f64() {
                    initial_conditions.insert(k, f);
                }
            }
            let ts = t.get("time_span").cloned().unwrap_or(Value::Null);
            let t_start = ts.get("start").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let t_end = ts.get("end").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let assertions_arr = t
                .get("assertions")
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default();
            let mut assertions = Vec::new();
            for a in assertions_arr {
                let variable = a
                    .get("variable")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                let time = a.get("time").and_then(|v| v.as_f64()).unwrap_or(0.0);
                let expected = a
                    .get("expected")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(f64::NAN);
                let tolerance = a.get("tolerance").and_then(Tolerance::from_value);
                assertions.push(Assertion {
                    variable,
                    time,
                    expected,
                    tolerance,
                });
            }
            let test_tol = t.get("tolerance").and_then(Tolerance::from_value);
            tests.push(FixtureTest {
                id,
                initial_conditions,
                t_start,
                t_end,
                assertions,
                tolerance: test_tol,
            });
        }
        out.push(FixtureModel {
            name: mname.clone(),
            tolerance,
            tests,
        });
    }
    out
}

fn effective_tolerance(
    assertion: Option<&Tolerance>,
    test: Option<&Tolerance>,
    model: Option<&Tolerance>,
) -> (f64, f64) {
    for c in [assertion, test, model] {
        if let Some(t) = c {
            let rel = t.rel.unwrap_or(0.0);
            let abs = t.abs.unwrap_or(0.0);
            if rel > 0.0 || abs > 0.0 {
                return (rel, abs);
            }
        }
    }
    (1e-6, 0.0)
}

fn approximately_equal(actual: f64, expected: f64, rel: f64, abs: f64) -> bool {
    if !actual.is_finite() && !expected.is_finite() {
        return true;
    }
    let diff = (actual - expected).abs();
    if diff <= abs {
        return true;
    }
    if rel > 0.0 {
        let scale = expected.abs().max(actual.abs());
        if diff <= rel * scale {
            return true;
        }
    }
    false
}

fn run_fixture(path: &PathBuf) {
    let json_text = fs::read_to_string(path).unwrap_or_else(|e| panic!("read {path:?}: {e}"));
    let file = match load(&json_text) {
        Ok(f) => f,
        Err(e) => panic!("load {path:?}: {e}"),
    };
    let fixture_models = parse_fixture(&json_text);
    for m in fixture_models {
        for t in &m.tests {
            // Run simulate with output_times covering every assertion time.
            let mut sorted_times: Vec<f64> = t.assertions.iter().map(|a| a.time).collect();
            sorted_times.sort_by(|a, b| a.partial_cmp(b).unwrap());
            sorted_times.dedup_by(|a, b| (*a - *b).abs() < 1e-12);
            let opts = SimulateOptions {
                solver: SolverChoice::Bdf,
                abstol: 1e-10,
                reltol: 1e-8,
                max_steps: 100_000,
                output_times: Some(sorted_times.clone()),
            };
            let params: HashMap<String, f64> = HashMap::new();
            let sol = match simulate(
                &file,
                (t.t_start, t.t_end),
                &params,
                &t.initial_conditions,
                &opts,
            ) {
                Ok(s) => s,
                Err(e) => panic!(
                    "[{}/{}/{}] simulate failed: {}",
                    path.file_name().unwrap().to_string_lossy(),
                    m.name,
                    t.id,
                    e
                ),
            };
            // Resolve each assertion: find the state slot by name and pick
            // the output time.
            for a in &t.assertions {
                let slot = match sol
                    .state_variable_names
                    .iter()
                    .position(|n| n == &a.variable)
                {
                    Some(i) => i,
                    None => panic!(
                        "[{}/{}/{}] unknown assertion variable '{}'. Known: {:?}",
                        path.file_name().unwrap().to_string_lossy(),
                        m.name,
                        t.id,
                        a.variable,
                        sol.state_variable_names
                    ),
                };
                // Find time index closest to assertion time.
                let tix = sol
                    .time
                    .iter()
                    .enumerate()
                    .min_by(|(_, x), (_, y)| {
                        (*x - a.time)
                            .abs()
                            .partial_cmp(&(*y - a.time).abs())
                            .unwrap()
                    })
                    .map(|(i, _)| i)
                    .unwrap_or(0);
                let actual = sol.state[slot][tix];
                let (rel, abs) = effective_tolerance(
                    a.tolerance.as_ref(),
                    t.tolerance.as_ref(),
                    m.tolerance.as_ref(),
                );
                assert!(
                    approximately_equal(actual, a.expected, rel, abs),
                    "[{}/{}/{}] assertion failed: {} @ t={} expected {} got {} (rel_tol={}, abs_tol={})",
                    path.file_name().unwrap().to_string_lossy(),
                    m.name,
                    t.id,
                    a.variable,
                    a.time,
                    a.expected,
                    actual,
                    rel,
                    abs
                );
            }
        }
    }
}

fn fixture_paths() -> Vec<PathBuf> {
    let manifest = env!("CARGO_MANIFEST_DIR");
    let mut out = Vec::new();
    for dir in FIXTURE_DIRS {
        let p = PathBuf::from(manifest).join(dir);
        if !p.exists() {
            continue;
        }
        let entries = fs::read_dir(&p).unwrap_or_else(|e| panic!("read_dir {p:?}: {e}"));
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("esm") {
                out.push(path);
            }
        }
    }
    out.sort();
    out
}

#[test]
fn arrayop_fixture_01_pure_ode_analytical() {
    let p = find_fixture("01_pure_ode_analytical.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_02_mixed_ode_algebraic() {
    let p = find_fixture("02_mixed_ode_algebraic.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_03_1d_stencil_mass_conservation() {
    let p = find_fixture("03_1d_stencil_mass_conservation.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_04_weno_wide_stencil() {
    let p = find_fixture("04_weno_wide_stencil.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_06_rearranged_algebraic() {
    let p = find_fixture("06_rearranged_algebraic.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_08_2d_arrayop_analytical() {
    let p = find_fixture("08_2d_arrayop_analytical.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_09_makearray_block_assembly() {
    let p = find_fixture("09_makearray_block_assembly.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_10_index_extraction() {
    let p = find_fixture("10_index_extraction.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_11_reshape_roundtrip() {
    let p = find_fixture("11_reshape_roundtrip.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_12_transpose_2d() {
    let p = find_fixture("12_transpose_2d.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_13_concat_1d() {
    let p = find_fixture("13_concat_1d.esm");
    run_fixture(&p);
}

#[test]
fn arrayop_fixture_14_broadcast_elementwise() {
    let p = find_fixture("14_broadcast_elementwise.esm");
    run_fixture(&p);
}

fn find_fixture(name: &str) -> PathBuf {
    for p in fixture_paths() {
        if p.file_name().and_then(|n| n.to_str()) == Some(name) {
            return p;
        }
    }
    panic!("fixture {name} not found")
}
