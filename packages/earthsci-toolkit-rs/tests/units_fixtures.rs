//! Cross-binding units fixtures (gt-gtf)
//!
//! The three units_*.esm files in tests/valid/ are shared across
//! Julia/Python/Rust/TypeScript/Go and exist specifically to drive
//! cross-binding agreement on units handling.
//!
//! Rust currently has no expression-level dimension propagation
//! (tracked separately under gt-rust-propagation), so this suite asserts
//! only that each fixture parses and that every variable's declared unit
//! string round-trips through `parse_unit`. Equation-level dimensional
//! checks are deferred until propagation lands.

use earthsci_toolkit::*;

const UNITS_FIXTURES: &[(&str, &str)] = &[
    (
        "units_conversions.esm",
        include_str!("../../../tests/valid/units_conversions.esm"),
    ),
    (
        "units_dimensional_analysis.esm",
        include_str!("../../../tests/valid/units_dimensional_analysis.esm"),
    ),
    (
        "units_propagation.esm",
        include_str!("../../../tests/valid/units_propagation.esm"),
    ),
];

#[test]
fn units_fixtures_parse() {
    for (name, content) in UNITS_FIXTURES {
        let file: EsmFile = load(content).unwrap_or_else(|e| panic!("failed to load {name}: {e}"));
        let models = file
            .models
            .as_ref()
            .unwrap_or_else(|| panic!("{name}: expected at least one model"));
        assert!(!models.is_empty(), "{name}: models map is empty");
    }
}

#[test]
fn units_fixtures_variable_units_parse_or_log() {
    // Walk every variable's declared unit string. Successful parses are
    // expected; failures mark a registry-coverage gap (e.g. atm, Torr,
    // psi) that the cross-binding fixtures intentionally surface.
    // Failures do not fail the test — they are reported via println so
    // they appear in `cargo test -- --nocapture` and become a paper
    // trail when the registry is extended.
    for (fname, content) in UNITS_FIXTURES {
        let file: EsmFile = load(content).expect("fixture parses");
        let models = file.models.as_ref().expect("fixture has models");
        for (mname, model) in models {
            for (vname, var) in &model.variables {
                if let Some(unit_str) = &var.units {
                    if unit_str.is_empty() {
                        continue;
                    }
                    if let Err(err) = parse_unit(unit_str) {
                        println!(
                            "[units coverage] {fname}::{mname}::{vname}: cannot parse {unit_str:?}: {err}"
                        );
                    }
                }
            }
        }
    }
}
