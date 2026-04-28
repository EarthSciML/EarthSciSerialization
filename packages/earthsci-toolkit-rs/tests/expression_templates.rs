//! Tests for parse-time expansion of expression_templates (RFC v2 §4, esm-giy).

use earthsci_toolkit::Expr;
use earthsci_toolkit::load;
use serde_json::{json, Value};

const FIXTURE: &str = include_str!("../../../tests/valid/expression_templates_arrhenius.esm");

fn arrhenius_inline(a_pre: f64, ea: i64) -> Value {
    json!({
        "op": "*",
        "args": [
            a_pre,
            {
                "op": "exp",
                "args": [{"op": "/", "args": [{"op": "-", "args": [ea]}, "T"]}],
            },
            "num_density",
        ],
    })
}

fn rate_to_json(expr: &Expr) -> Value {
    serde_json::to_value(expr).expect("rate must serialize")
}

#[test]
fn loads_fixture_with_expanded_rates() {
    let esm = load(FIXTURE).expect("fixture must load");
    let rs = esm
        .reaction_systems
        .as_ref()
        .and_then(|m| m.get("ToyArrhenius"))
        .expect("ToyArrhenius reaction_system must exist");
    assert_eq!(rs.reactions.len(), 3);

    let cases: &[(&str, f64, i64)] = &[
        ("R1", 1.8e-12, 1500),
        ("R2", 3.0e-13, 460),
        ("R3", 4.5e-14, 920),
    ];
    for (id, a_pre, ea) in cases {
        let r = rs
            .reactions
            .iter()
            .find(|r| r.id.as_deref() == Some(*id))
            .unwrap_or_else(|| panic!("reaction {id} not found"));
        let actual = rate_to_json(&r.rate);
        let expected = arrhenius_inline(*a_pre, *ea);
        assert_eq!(actual, expected, "{id} rate mismatch");
    }
}

#[test]
fn rejects_pre_0_4_apply_template() {
    let mutated = FIXTURE.replace(r#""esm": "0.4.0""#, r#""esm": "0.3.0""#);
    assert!(load(&mutated).is_err());
}

fn mutate_first_rate(rate: Value) -> String {
    let mut data: Value = serde_json::from_str(FIXTURE).unwrap();
    data["reaction_systems"]["ToyArrhenius"]["reactions"][0]["rate"] = rate;
    serde_json::to_string(&data).unwrap()
}

#[test]
fn rejects_unknown_template() {
    let s = mutate_first_rate(json!({
        "op": "apply_expression_template",
        "args": [],
        "name": "no_such_template",
        "bindings": {"A_pre": 1.0, "Ea": 1.0},
    }));
    assert!(load(&s).is_err());
}

#[test]
fn rejects_missing_binding() {
    let s = mutate_first_rate(json!({
        "op": "apply_expression_template",
        "args": [],
        "name": "arrhenius",
        "bindings": {"A_pre": 1.0},
    }));
    assert!(load(&s).is_err());
}

#[test]
fn rejects_extra_binding() {
    let s = mutate_first_rate(json!({
        "op": "apply_expression_template",
        "args": [],
        "name": "arrhenius",
        "bindings": {"A_pre": 1.0, "Ea": 1.0, "Junk": 2.0},
    }));
    assert!(load(&s).is_err());
}

#[test]
fn expansion_is_deterministic() {
    let a = load(FIXTURE).unwrap();
    let b = load(FIXTURE).unwrap();
    let ra = &a.reaction_systems.as_ref().unwrap()["ToyArrhenius"].reactions;
    let rb = &b.reaction_systems.as_ref().unwrap()["ToyArrhenius"].reactions;
    for i in 0..ra.len() {
        assert_eq!(rate_to_json(&ra[i].rate), rate_to_json(&rb[i].rate));
    }
}
