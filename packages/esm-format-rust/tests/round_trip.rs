//! Round-trip tests for all valid fixtures
//!
//! Tests that valid ESM files can be loaded and saved back without losing information.

use esm_format::*;

/// Test round-trip serialization for minimal chemistry fixture
#[test]
fn test_minimal_chemistry_round_trip() {
    let fixture = include_str!("../../../tests/valid/minimal_chemistry.esm");

    let parsed: EsmFile = load(fixture).expect("Failed to parse minimal chemistry fixture");
    let serialized = save(&parsed).expect("Failed to serialize back to JSON");

    // Parse again to ensure roundtrip works
    let reparsed: EsmFile = load(&serialized).expect("Failed to reparse serialized output");

    // Basic structural checks
    assert_eq!(parsed.esm, reparsed.esm);
    assert_eq!(parsed.metadata.name, reparsed.metadata.name);
}

/// Test round-trip for metadata variations
#[test]
fn test_metadata_variations_round_trip() {
    let fixtures = [
        include_str!("../../../tests/valid/metadata_minimal.esm"),
        include_str!("../../../tests/valid/metadata_author_variations.esm"),
        include_str!("../../../tests/valid/metadata_reference_types.esm"),
        include_str!("../../../tests/valid/metadata_date_formats.esm"),
        include_str!("../../../tests/valid/metadata_tags_license.esm"),
    ];

    for (i, fixture) in fixtures.iter().enumerate() {
        let parsed: EsmFile = load(fixture)
            .unwrap_or_else(|e| panic!("Failed to parse metadata fixture {}: {}", i, e));
        let serialized = save(&parsed)
            .unwrap_or_else(|e| panic!("Failed to serialize metadata fixture {}: {}", i, e));
        let reparsed: EsmFile = load(&serialized)
            .unwrap_or_else(|e| panic!("Failed to reparse metadata fixture {}: {}", i, e));

        assert_eq!(parsed.esm, reparsed.esm);
        assert_eq!(parsed.metadata.name, reparsed.metadata.name);
    }
}

/// Test round-trip for coupled atmospheric system
#[test]
fn test_coupled_atmospheric_system_round_trip() {
    let fixture = include_str!("../../../tests/end_to_end/coupled_atmospheric_system.esm");

    let parsed: EsmFile = load(fixture).expect("Failed to parse coupled atmospheric system");
    let serialized = save(&parsed).expect("Failed to serialize coupled atmospheric system");
    let reparsed: EsmFile = load(&serialized).expect("Failed to reparse coupled atmospheric system");

    assert_eq!(parsed.esm, reparsed.esm);
    if let (Some(models1), Some(models2)) = (&parsed.models, &reparsed.models) {
        assert_eq!(models1.len(), models2.len());
    }
    if let (Some(rs1), Some(rs2)) = (&parsed.reaction_systems, &reparsed.reaction_systems) {
        assert_eq!(rs1.len(), rs2.len());
    }
}

/// Test round-trip for comprehensive events
#[test]
fn test_comprehensive_events_round_trip() {
    let fixture = include_str!("../../../tests/events/comprehensive_events.esm");

    let parsed: EsmFile = load(fixture).expect("Failed to parse comprehensive events");
    let serialized = save(&parsed).expect("Failed to serialize comprehensive events");
    let reparsed: EsmFile = load(&serialized).expect("Failed to reparse comprehensive events");

    assert_eq!(parsed.esm, reparsed.esm);
    // Check that events are preserved
    if let (Some(models1), Some(models2)) = (&parsed.models, &reparsed.models) {
        for (name, model1) in models1 {
            let model2 = &models2[name];
            // Compare discrete events
            match (&model1.discrete_events, &model2.discrete_events) {
                (Some(events1), Some(events2)) => assert_eq!(events1.len(), events2.len()),
                (None, None) => {},
                _ => panic!("Discrete events structure mismatch for model {}", name),
            }
            // Compare continuous events
            match (&model1.continuous_events, &model2.continuous_events) {
                (Some(events1), Some(events2)) => assert_eq!(events1.len(), events2.len()),
                (None, None) => {},
                _ => panic!("Continuous events structure mismatch for model {}", name),
            }
        }
    }
}

/// Test round-trip for spatial operators
#[test]
fn test_spatial_operators_round_trip() {
    let fixtures = [
        include_str!("../../../tests/spatial/finite_difference_operators.esm"),
        include_str!("../../../tests/spatial/boundary_conditions.esm"),
    ];

    for (i, fixture) in fixtures.iter().enumerate() {
        let parsed: EsmFile = load(fixture)
            .unwrap_or_else(|e| panic!("Failed to parse spatial fixture {}: {}", i, e));
        let serialized = save(&parsed)
            .unwrap_or_else(|e| panic!("Failed to serialize spatial fixture {}: {}", i, e));
        let reparsed: EsmFile = load(&serialized)
            .unwrap_or_else(|e| panic!("Failed to reparse spatial fixture {}: {}", i, e));

        assert_eq!(parsed.esm, reparsed.esm);
        // Check operators are preserved
        if let (Some(ops1), Some(ops2)) = (&parsed.operators, &reparsed.operators) {
            assert_eq!(ops1.len(), ops2.len());
        }
    }
}

/// Test round-trip for coupling scenarios
#[test]
fn test_coupling_round_trip() {
    let fixtures = [
        include_str!("../../../tests/coupling/advanced_coupling.esm"),
        include_str!("../../../tests/coupling/complete_coupling_types.esm"),
        include_str!("../../../tests/coupling/coupling_resolution_algorithm.esm"),
    ];

    for (i, fixture) in fixtures.iter().enumerate() {
        let parsed: EsmFile = load(fixture)
            .unwrap_or_else(|e| panic!("Failed to parse coupling fixture {}: {}", i, e));
        let serialized = save(&parsed)
            .unwrap_or_else(|e| panic!("Failed to serialize coupling fixture {}: {}", i, e));
        let reparsed: EsmFile = load(&serialized)
            .unwrap_or_else(|e| panic!("Failed to reparse coupling fixture {}: {}", i, e));

        assert_eq!(parsed.esm, reparsed.esm);
        // Check coupling is preserved
        if let (Some(coupling1), Some(coupling2)) = (&parsed.coupling, &reparsed.coupling) {
            assert_eq!(coupling1.len(), coupling2.len());
        }
    }
}

/// Test round-trip for data loaders
#[test]
fn test_data_loaders_round_trip() {
    let fixture = include_str!("../../../tests/valid/data_loaders_comprehensive.esm");

    let parsed: EsmFile = load(fixture).expect("Failed to parse data loaders");
    let serialized = save(&parsed).expect("Failed to serialize data loaders");
    let reparsed: EsmFile = load(&serialized).expect("Failed to reparse data loaders");

    assert_eq!(parsed.esm, reparsed.esm);
    if let (Some(loaders1), Some(loaders2)) = (&parsed.data_loaders, &reparsed.data_loaders) {
        assert_eq!(loaders1.len(), loaders2.len());
    }
}

/// Test round-trip for version compatibility fixtures
#[test]
fn test_version_compatibility_round_trip() {
    let fixtures = [
        include_str!("../../../tests/version_compatibility/version_0_1_0_baseline.esm"),
        include_str!("../../../tests/version_compatibility/version_0_2_0_minor_upgrade.esm"),
        include_str!("../../../tests/version_compatibility/version_0_1_5_patch_upgrade.esm"),
        include_str!("../../../tests/version_compatibility/version_0_0_1_backwards_compat.esm"),
    ];

    for (i, fixture) in fixtures.iter().enumerate() {
        let parsed: EsmFile = load(fixture)
            .unwrap_or_else(|e| panic!("Failed to parse version fixture {}: {}", i, e));
        let serialized = save(&parsed)
            .unwrap_or_else(|e| panic!("Failed to serialize version fixture {}: {}", i, e));
        let reparsed: EsmFile = load(&serialized)
            .unwrap_or_else(|e| panic!("Failed to reparse version fixture {}: {}", i, e));

        assert_eq!(parsed.esm, reparsed.esm);
        assert_eq!(parsed.metadata.name, reparsed.metadata.name);
    }
}

/// Test round-trip for mathematical correctness fixtures
#[test]
fn test_mathematical_correctness_round_trip() {
    let fixtures = [
        include_str!("../../../tests/mathematical_correctness/conservation_laws.esm"),
        include_str!("../../../tests/mathematical_correctness/dimensional_analysis.esm"),
        include_str!("../../../tests/validation/mathematical_correctness.esm"),
    ];

    for (i, fixture) in fixtures.iter().enumerate() {
        let parsed: EsmFile = load(fixture)
            .unwrap_or_else(|e| panic!("Failed to parse math fixture {}: {}", i, e));
        let serialized = save(&parsed)
            .unwrap_or_else(|e| panic!("Failed to serialize math fixture {}: {}", i, e));
        let reparsed: EsmFile = load(&serialized)
            .unwrap_or_else(|e| panic!("Failed to reparse math fixture {}: {}", i, e));

        assert_eq!(parsed.esm, reparsed.esm);
    }
}

/// Test round-trip for scoping fixtures
#[test]
fn test_scoping_round_trip() {
    let fixtures = [
        include_str!("../../../tests/scoping/nested_subsystems.esm"),
        include_str!("../../../tests/scoping/hierarchical_subsystems.esm"),
    ];

    for (i, fixture) in fixtures.iter().enumerate() {
        let parsed: EsmFile = load(fixture)
            .unwrap_or_else(|e| panic!("Failed to parse scoping fixture {}: {}", i, e));
        let serialized = save(&parsed)
            .unwrap_or_else(|e| panic!("Failed to serialize scoping fixture {}: {}", i, e));
        let reparsed: EsmFile = load(&serialized)
            .unwrap_or_else(|e| panic!("Failed to reparse scoping fixture {}: {}", i, e));

        assert_eq!(parsed.esm, reparsed.esm);
    }
}

/// Test round-trip for metadata inheritance
#[test]
fn test_metadata_inheritance_round_trip() {
    let fixture = include_str!("../../../tests/valid/metadata_inheritance_coupled.esm");

    let parsed: EsmFile = load(fixture).expect("Failed to parse metadata inheritance");
    let serialized = save(&parsed).expect("Failed to serialize metadata inheritance");
    let reparsed: EsmFile = load(&serialized).expect("Failed to reparse metadata inheritance");

    assert_eq!(parsed.esm, reparsed.esm);
    assert_eq!(parsed.metadata.name, reparsed.metadata.name);
}