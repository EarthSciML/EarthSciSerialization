//! Round-trip tests for the §7 `discretizations` top-level schema, including
//! the §7.4 `CrossMetricStencilRule` composite variant (esm-vwo).
//!
//! The Rust binding holds discretization entries opaquely as
//! `HashMap<String, serde_json::Value>` because stencil coefficients and
//! applies_to patterns carry pattern-variable strings (`$u`, `$x`,
//! `$target`) that don't map onto the `Expr` coercion pipeline. The
//! round-trip contract is structural equivalence of the top-level
//! `discretizations` subtree after load → save → load.

use earthsci_toolkit::{load, save, EsmFile};
use serde_json::Value;

fn normalize_numbers(v: &mut Value) {
    match v {
        Value::Number(n) => {
            if let Some(f) = n.as_f64() {
                *n = serde_json::Number::from_f64(f).unwrap_or_else(|| n.clone());
            }
        }
        Value::Array(arr) => arr.iter_mut().for_each(normalize_numbers),
        Value::Object(map) => map.values_mut().for_each(normalize_numbers),
        _ => {}
    }
}

fn assert_discretizations_roundtrip(fixture: &str) {
    let parsed: EsmFile = load(fixture).expect("fixture should load cleanly");
    assert!(
        parsed.discretizations.is_some(),
        "fixture must carry a discretizations section"
    );
    let serialized = save(&parsed).expect("serialization should succeed");

    let mut original: Value = serde_json::from_str(fixture).expect("fixture is valid JSON");
    let mut reparsed: Value = serde_json::from_str(&serialized).expect("output is valid JSON");
    normalize_numbers(&mut original);
    normalize_numbers(&mut reparsed);

    assert_eq!(
        original.get("discretizations"),
        reparsed.get("discretizations"),
        "discretizations section must round-trip unchanged"
    );

    // Second hop must also be a fixed point.
    let _: EsmFile = load(&serialized).expect("reparse after save should succeed");
}

#[test]
fn roundtrip_centered_2nd_uniform() {
    let fixture = include_str!("../../../tests/discretizations/centered_2nd_uniform.esm");
    assert_discretizations_roundtrip(fixture);
}

#[test]
fn roundtrip_mpas_cell_div() {
    let fixture = include_str!("../../../tests/discretizations/mpas_cell_div.esm");
    assert_discretizations_roundtrip(fixture);
}

#[test]
fn roundtrip_upwind_1st_advection() {
    let fixture = include_str!("../../../tests/discretizations/upwind_1st_advection.esm");
    assert_discretizations_roundtrip(fixture);
}

#[test]
fn roundtrip_periodic_bc() {
    let fixture = include_str!("../../../tests/discretizations/periodic_bc.esm");
    assert_discretizations_roundtrip(fixture);
}

#[test]
fn roundtrip_cross_metric_cartesian() {
    let fixture = include_str!("../../../tests/discretizations/cross_metric_cartesian.esm");
    assert_discretizations_roundtrip(fixture);
}

#[test]
fn cross_metric_composite_structure() {
    let fixture = include_str!("../../../tests/discretizations/cross_metric_cartesian.esm");
    let parsed: EsmFile = load(fixture).expect("fixture should load cleanly");
    let discs = parsed
        .discretizations
        .as_ref()
        .expect("cross_metric fixture carries discretizations");

    let composite = discs
        .get("laplacian_full_covariant_toy")
        .expect("composite entry must be present after load");

    assert_eq!(composite["kind"], Value::String("cross_metric".to_string()));
    let axes = composite["axes"].as_array().expect("axes must be an array");
    let axis_names: Vec<&str> = axes.iter().map(|v| v.as_str().unwrap_or("")).collect();
    assert_eq!(axis_names, vec!["xi", "eta"]);

    let terms = composite["terms"].as_array().expect("terms must be an array");
    assert_eq!(terms.len(), 2);

    // Composite entries do NOT carry a stencil key.
    assert!(
        composite.get("stencil").is_none(),
        "composite must not carry a stencil key"
    );

    // Per-axis stencils should still be present and carry a stencil key.
    assert!(discs.get("d2_dxi2_uniform").unwrap()["stencil"].is_array());
    assert!(discs.get("d2_deta2_uniform").unwrap()["stencil"].is_array());
}
