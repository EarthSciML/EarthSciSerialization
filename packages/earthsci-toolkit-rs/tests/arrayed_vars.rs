//! Arrayed-variable shape/location tests (discretization RFC §10.2).

use earthsci_toolkit::*;
use std::fs;
use std::path::PathBuf;

fn fixture_dir() -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.pop(); // packages/earthsci-toolkit-rs -> packages
    p.pop(); // packages -> repo root
    p.push("tests");
    p.push("fixtures");
    p.push("arrayed_vars");
    p
}

fn load_fixture(name: &str) -> EsmFile {
    let path = fixture_dir().join(name);
    let raw = fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {:?}: {}", path, e));
    load(&raw).unwrap_or_else(|e| panic!("parse {}: {:?}", name, e))
}

fn roundtrip(name: &str) -> (EsmFile, EsmFile) {
    let first = load_fixture(name);
    let serialized = save(&first).expect("serialize");
    let second: EsmFile = load(&serialized).expect("reparse");
    (first, second)
}

fn var<'a>(esm: &'a EsmFile, model: &str, name: &str) -> &'a ModelVariable {
    esm.models
        .as_ref()
        .expect("models map present")
        .get(model)
        .unwrap_or_else(|| panic!("model {} missing", model))
        .variables
        .get(name)
        .unwrap_or_else(|| panic!("variable {} missing", name))
}

#[test]
fn scalar_no_shape_regression() {
    let esm = load_fixture("scalar_no_shape.esm");
    let v = var(&esm, "Scalar0D", "x");
    assert!(v.shape.is_none(), "unset shape should be None");
    assert!(v.location.is_none(), "unset location should be None");
}

#[test]
fn scalar_explicit_empty_shape() {
    let (first, second) = roundtrip("scalar_explicit.esm");
    for esm in [&first, &second] {
        let v = var(esm, "ScalarExplicit", "mass");
        // Empty list and None are both valid "scalar" forms.
        let dims = v.shape.as_ref().map(|s| s.len()).unwrap_or(0);
        assert_eq!(dims, 0, "explicit scalar must parse as zero dimensions");
        assert!(v.location.is_none());
    }
}

#[test]
fn one_d_cell_center() {
    let (first, second) = roundtrip("one_d.esm");
    for esm in [&first, &second] {
        let c = var(esm, "Diffusion1D", "c");
        assert_eq!(c.shape.as_deref(), Some(&["x".to_string()][..]));
        assert_eq!(c.location.as_deref(), Some("cell_center"));
        let d = var(esm, "Diffusion1D", "D");
        assert!(d.shape.is_none());
        assert!(d.location.is_none());
    }
}

#[test]
fn two_d_staggered_faces() {
    let (first, second) = roundtrip("two_d_faces.esm");
    let expected = vec!["x".to_string(), "y".to_string()];
    for esm in [&first, &second] {
        let p = var(esm, "StaggeredFlow2D", "p");
        assert_eq!(p.shape.as_ref(), Some(&expected));
        assert_eq!(p.location.as_deref(), Some("cell_center"));
        let u = var(esm, "StaggeredFlow2D", "u");
        assert_eq!(u.shape.as_ref(), Some(&expected));
        assert_eq!(u.location.as_deref(), Some("x_face"));
    }
}

#[test]
fn vertex_located_roundtrip() {
    let (first, second) = roundtrip("vertex_located.esm");
    let expected = vec!["x".to_string(), "y".to_string()];
    for esm in [&first, &second] {
        let phi = var(esm, "VertexScalar2D", "phi");
        assert_eq!(phi.shape.as_ref(), Some(&expected));
        assert_eq!(phi.location.as_deref(), Some("vertex"));
    }
}
