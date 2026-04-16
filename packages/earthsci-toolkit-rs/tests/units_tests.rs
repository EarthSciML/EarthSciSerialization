//! Units tests
//!
//! Parsing, dimensional consistency, and conversion tests for the units module.
//! Consolidated from `basic_functionality::test_units` and
//! `analysis_features::test_units_functionality`.

use earthsci_toolkit::*;
use std::collections::HashMap;
use std::path::PathBuf;

fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/valid")
        .join(name)
}

#[test]
fn parse_basic() {
    parse_unit("m").expect("Failed to parse m");
    parse_unit("cm").expect("Failed to parse cm");
}

#[test]
fn parse_compound() {
    parse_unit("m/s").expect("Failed to parse m/s");
    parse_unit("mol/L").expect("Failed to parse mol/L");
}

#[test]
fn dimensional_consistency_pass() {
    let m = parse_unit("m").expect("Failed to parse m");
    let cm = parse_unit("cm").expect("Failed to parse cm");
    check_dimensional_consistency(&m, &cm).expect("m and cm should be dimensionally consistent");
}

#[test]
fn dimensional_consistency_fail() {
    let m_per_s = parse_unit("m/s").expect("Failed to parse m/s");
    let mol_per_l = parse_unit("mol/L").expect("Failed to parse mol/L");
    assert!(
        check_dimensional_consistency(&m_per_s, &mol_per_l).is_err(),
        "Should detect dimensional inconsistency between m/s and mol/L"
    );
}

#[test]
fn convert_same_dimension() {
    let m = parse_unit("m").expect("Failed to parse m");
    let cm = parse_unit("cm").expect("Failed to parse cm");
    let conversion = convert_units(1.0, &m, &cm).expect("Failed to convert m to cm");
    assert!(
        (conversion - 100.0).abs() < 1e-10,
        "1 m should equal 100 cm"
    );
}

#[test]
fn convert_cross_dimension_fails() {
    let m_per_s = parse_unit("m/s").expect("Failed to parse m/s");
    let mol_per_l = parse_unit("mol/L").expect("Failed to parse mol/L");
    assert!(
        convert_units(1.0, &m_per_s, &mol_per_l).is_err(),
        "Converting m/s to mol/L should fail"
    );
}

/// Canonical bead example: given `h` with units `m` and `v` with units `m/s`,
/// verify that `D(h) ~ v` is dimensionally consistent via expression-level
/// propagation.
#[test]
fn propagate_dh_equals_v() {
    let mut env: HashMap<String, Unit> = HashMap::new();
    env.insert("h".to_string(), parse_unit("m").unwrap());
    env.insert("v".to_string(), parse_unit("m/s").unwrap());

    let dh = Expr::Operator(ExpressionNode {
        op: "D".to_string(),
        args: vec![Expr::Variable("h".to_string())],
        wrt: Some("t".to_string()),
        ..ExpressionNode::default()
    });

    let eq = Equation {
        lhs: dh,
        rhs: Expr::Variable("v".to_string()),
    };

    validate_equation_dimensions(&eq, &env)
        .expect("D(h)/dt should match v (both are m/s)");
}

/// Loading the fixture `units_propagation.esm` and validating it should
/// surface no dimensional warnings — all observed-variable expressions have
/// matching declared units.
#[test]
fn validate_units_propagation_fixture_warning_free() {
    let path = fixture_path("units_propagation.esm");
    let json = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("failed to read {}: {}", path.display(), e));

    let result = validate_complete(&json);
    let dim_warnings: Vec<_> = result
        .unit_warnings
        .iter()
        .filter(|w| w.contains("Dimension mismatch"))
        .collect();
    assert!(
        dim_warnings.is_empty(),
        "Fixture should be dimensionally consistent; got: {:?}",
        dim_warnings
    );
}
