//! Round-trip test for §7.4 `staggering_rules` top-level schema support
//! (esm-15f). Loads the MPAS C-grid staggering fixture, re-serializes it,
//! reparses, and asserts the `staggering_rules` subtree is byte-for-byte
//! equal at the JSON-value level.

use earthsci_toolkit::{EsmFile, load, save};
use serde_json::Value;

#[test]
fn roundtrip_mpas_c_grid_staggering() {
    let fixture = include_str!("../../../tests/grids/mpas_c_grid_staggering.esm");
    let parsed: EsmFile = load(fixture).expect("fixture should load cleanly");

    // The staggering_rules section must survive into the typed model.
    let rules = parsed
        .staggering_rules
        .as_ref()
        .expect("staggering_rules missing after load");
    assert_eq!(rules.len(), 1, "expected exactly one staggering rule");
    let rule = rules
        .get("mpas_c_grid_staggering")
        .expect("mpas_c_grid_staggering entry missing");
    assert_eq!(rule.kind, "unstructured_c_grid");
    assert_eq!(rule.grid, "mpas_cvmesh");
    assert_eq!(
        rule.edge_normal_convention.as_deref(),
        Some("outward_from_first_cell")
    );
    let cqls = rule
        .cell_quantity_locations
        .as_ref()
        .expect("cell_quantity_locations missing");
    assert_eq!(cqls.get("u").map(String::as_str), Some("edge_midpoint"));
    assert_eq!(cqls.get("zeta").map(String::as_str), Some("vertex"));

    let serialized = save(&parsed).expect("serialize should succeed");
    let original: Value = serde_json::from_str(fixture).expect("fixture is JSON");
    let reparsed: Value = serde_json::from_str(&serialized).expect("output is JSON");

    assert_eq!(
        original.get("staggering_rules"),
        reparsed.get("staggering_rules"),
        "staggering_rules section must round-trip unchanged"
    );

    // Sanity: re-loading the serialized form must succeed.
    let _: EsmFile = load(&serialized).expect("reparse after save should succeed");
}
