//! Round-trip coverage for the `call` op + `registered_functions` registry
//! introduced in gt-p3ep. The fixtures live in `tests/registered_funcs/`
//! and exercise the calling contract — handler bodies are supplied by the
//! host at runtime through a handler registry (esm-spec §4.4 / §9.2).

use earthsci_toolkit::{load, save, Expr, EsmFile};

const PURE_MATH: &str = include_str!("../../../tests/registered_funcs/pure_math.esm");
const ONE_D: &str = include_str!("../../../tests/registered_funcs/one_d_interpolator.esm");
const TWO_D: &str = include_str!("../../../tests/registered_funcs/two_d_table_lookup.esm");

fn round_trip(fixture: &str) -> (EsmFile, EsmFile) {
    let parsed: EsmFile = load(fixture).expect("fixture must load");
    let first = save(&parsed).expect("save 1 must succeed");
    let reloaded: EsmFile = load(&first).expect("reload must succeed");
    let second = save(&reloaded).expect("save 2 must succeed");

    let first_json: serde_json::Value = serde_json::from_str(&first).unwrap();
    let second_json: serde_json::Value = serde_json::from_str(&second).unwrap();
    assert_eq!(
        first_json, second_json,
        "serializer must be idempotent on call + registered_functions"
    );
    (parsed, reloaded)
}

#[test]
fn pure_math_round_trip() {
    let (parsed, _) = round_trip(PURE_MATH);
    let registry = parsed
        .registered_functions
        .expect("registered_functions must be populated");
    let sq = registry.get("sq").expect("sq entry must parse");
    assert_eq!(sq.id, "sq");
    assert_eq!(sq.signature.arg_count, 1);
    assert_eq!(
        sq.signature.arg_types.as_deref(),
        Some(&["scalar".to_string()][..])
    );
}

#[test]
fn one_d_interpolator_round_trip() {
    let (parsed, _) = round_trip(ONE_D);
    let registry = parsed.registered_functions.expect("registry");
    let entry = registry.get("flux_interp_O3").expect("flux_interp_O3");
    assert_eq!(entry.units.as_deref(), Some("s^-1"));
    let arg_units = entry.arg_units.as_ref().expect("arg_units");
    assert_eq!(arg_units.len(), 1);
    assert_eq!(arg_units[0].as_deref(), Some("rad"));
}

#[test]
fn two_d_table_lookup_round_trip() {
    let (parsed, _) = round_trip(TWO_D);
    let registry = parsed.registered_functions.expect("registry");
    assert!(registry.contains_key("A_table"));
    assert!(registry.contains_key("r_c_wesely"));

    // The null-entry in r_c_wesely's arg_units must survive the round-trip.
    let r_c = registry.get("r_c_wesely").unwrap();
    let arg_units = r_c.arg_units.as_ref().expect("arg_units present");
    assert_eq!(arg_units.len(), 3);
    assert_eq!(arg_units[0].as_deref(), Some("K"));
    assert_eq!(arg_units[1].as_deref(), Some("m^2/m^2"));
    assert!(arg_units[2].is_none(), "null arg_unit must survive");
}

#[test]
fn call_op_handler_id_preserved() {
    let parsed: EsmFile = load(PURE_MATH).expect("load");
    let models = parsed.models.as_ref().expect("models");
    let model = models.get("PureMathCall").expect("PureMathCall");
    let rhs = &model.equations[0].rhs;
    let node = match rhs {
        Expr::Operator(n) => n,
        _ => panic!("RHS must be an operator node"),
    };
    assert_eq!(node.op, "call");
    assert_eq!(node.handler_id.as_deref(), Some("sq"));
}
