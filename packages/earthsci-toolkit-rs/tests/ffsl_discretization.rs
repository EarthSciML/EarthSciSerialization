//! Conformance: flux-form semi-Lagrangian (FFSL) discretization rules
//! (RFC §7.7, esm-1rj).
//!
//! Verifies the Rust binding parses and schema-validates the CAM5 FFSL
//! fixture and rejects structural violations of the discriminator contract.

use earthsci_toolkit::{EsmError, load};

const FIXTURE: &str = include_str!("../../../tests/discretizations/cam5_ffsl_advection.esm");

#[test]
fn ffsl_fixture_loads_and_validates() {
    let parsed = load(FIXTURE).expect("CAM5 FFSL fixture must load and validate");
    assert_eq!(parsed.esm, "0.2.0");
    assert_eq!(
        parsed.metadata.name.as_deref(),
        Some("CAM5FvFfslAdvection1D")
    );
}

#[test]
fn ffsl_rule_with_stencil_is_rejected() {
    // An FFSL rule MUST NOT carry `stencil`. Inject one and verify the
    // schema rejects the document.
    let doc: serde_json::Value = serde_json::from_str(FIXTURE).unwrap();
    let mut doc = doc;
    doc["discretizations"]["cam5_ffsl_1d"]["stencil"] = serde_json::json!([
        { "selector": { "kind": "cartesian", "axis": "x", "offset": 0 }, "coeff": 1 }
    ]);
    let bad = serde_json::to_string(&doc).unwrap();
    match load(&bad) {
        Err(EsmError::SchemaValidation(_)) => {}
        other => panic!("expected SchemaValidation error, got {:?}", other),
    }
}

#[test]
fn ffsl_rule_missing_cfl_policy_is_rejected() {
    let doc: serde_json::Value = serde_json::from_str(FIXTURE).unwrap();
    let mut doc = doc;
    doc["discretizations"]["cam5_ffsl_1d"]
        .as_object_mut()
        .unwrap()
        .remove("cfl_policy");
    let bad = serde_json::to_string(&doc).unwrap();
    match load(&bad) {
        Err(EsmError::SchemaValidation(_)) => {}
        other => panic!("expected SchemaValidation error, got {:?}", other),
    }
}

#[test]
fn stencil_rule_with_ffsl_field_is_rejected() {
    // Conversely, a stencil rule MUST NOT carry reconstruction/remap/etc.
    let stencil_fixture = include_str!("../../../tests/discretizations/centered_2nd_uniform.esm");
    let mut doc: serde_json::Value = serde_json::from_str(stencil_fixture).unwrap();
    doc["discretizations"]["centered_2nd_uniform"]["reconstruction"] =
        serde_json::json!({ "order": "PPM" });
    let bad = serde_json::to_string(&doc).unwrap();
    match load(&bad) {
        Err(EsmError::SchemaValidation(_)) => {}
        other => panic!("expected SchemaValidation error, got {:?}", other),
    }
}
