//! Units tests
//!
//! Parsing, dimensional consistency, and conversion tests for the units module.
//! Consolidated from `basic_functionality::test_units` and
//! `analysis_features::test_units_functionality`.

use earthsci_toolkit::*;

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
