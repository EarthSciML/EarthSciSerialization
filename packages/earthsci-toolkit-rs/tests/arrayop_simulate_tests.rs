//! Conformance tests for the array-op runtime (gt-oxr).
//!
//! Loads every `*.esm` fixture under
//! `../EarthSciSerialization.jl/test/fixtures/arrayop/`, compiles each model
//! through [`earthsci_toolkit::simulate`], and verifies that every assertion
//! inside every inline test matches within the declared tolerance.
//!
//! The fixtures were authored by the Julia sibling (gt-gey) to drive
//! cross-language conformance. The `tests` and `tolerance` blocks on each
//! model are now carried directly by the Rust [`Model`] struct (gt-c6w),
//! so the harness consumes the typed fields rather than re-parsing the raw
//! JSON.

#![cfg(not(target_arch = "wasm32"))]

use earthsci_toolkit::simulate::Solution;
use earthsci_toolkit::{
    Model, ModelTest, ModelTestAssertion, SimulateOptions, SolverChoice, Tolerance, load, simulate,
};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

const FIXTURE_DIRS: &[&str] = &["../EarthSciSerialization.jl/test/fixtures/arrayop"];

fn effective_tolerance(
    assertion: Option<&Tolerance>,
    test: Option<&Tolerance>,
    model: Option<&Tolerance>,
) -> (f64, f64) {
    for t in [assertion, test, model].into_iter().flatten() {
        let rel = t.rel.unwrap_or(0.0);
        let abs = t.abs.unwrap_or(0.0);
        if rel > 0.0 || abs > 0.0 {
            return (rel, abs);
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

fn model_iter(file: &earthsci_toolkit::EsmFile) -> Vec<(&String, &Model)> {
    file.models
        .as_ref()
        .map(|m| m.iter().collect::<Vec<_>>())
        .unwrap_or_default()
}

fn run_fixture(path: &PathBuf) {
    let json_text = fs::read_to_string(path).unwrap_or_else(|e| panic!("read {path:?}: {e}"));
    let file = match load(&json_text) {
        Ok(f) => f,
        Err(e) => panic!("load {path:?}: {e}"),
    };
    let mname_path = path.file_name().unwrap().to_string_lossy().into_owned();
    for (mname, model) in model_iter(&file) {
        let Some(tests) = model.tests.as_ref() else {
            continue;
        };
        for t in tests {
            run_model_test(&mname_path, mname, &file, model, t);
        }
    }
}

fn run_model_test(
    fixture_name: &str,
    model_name: &str,
    file: &earthsci_toolkit::EsmFile,
    model: &Model,
    t: &ModelTest,
) {
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
    let initial_conditions: HashMap<String, f64> =
        t.initial_conditions.as_ref().cloned().unwrap_or_default();
    let sol = match simulate(
        file,
        (t.time_span.start, t.time_span.end),
        &params,
        &initial_conditions,
        &opts,
    ) {
        Ok(s) => s,
        Err(e) => panic!(
            "[{fixture_name}/{model_name}/{}] simulate failed: {e}",
            t.id
        ),
    };
    // Resolve each assertion: find the state slot by name and pick
    // the output time.
    for a in &t.assertions {
        check_assertion(fixture_name, model_name, model, t, a, &sol);
    }
}

fn check_assertion(
    fixture_name: &str,
    model_name: &str,
    model: &Model,
    t: &ModelTest,
    a: &ModelTestAssertion,
    sol: &Solution,
) {
    let slot = match sol
        .state_variable_names
        .iter()
        .position(|n| n == &a.variable)
    {
        Some(i) => i,
        None => panic!(
            "[{fixture_name}/{model_name}/{}] unknown assertion variable '{}'. Known: {:?}",
            t.id, a.variable, sol.state_variable_names
        ),
    };
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
        model.tolerance.as_ref(),
    );
    assert!(
        approximately_equal(actual, a.expected, rel, abs),
        "[{fixture_name}/{model_name}/{}] assertion failed: {} @ t={} expected {} got {} (rel_tol={rel}, abs_tol={abs})",
        t.id,
        a.variable,
        a.time,
        a.expected,
        actual
    );
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
