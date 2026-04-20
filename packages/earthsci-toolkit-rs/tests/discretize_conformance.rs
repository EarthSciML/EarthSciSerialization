//! Manifest-driven cross-binding discretize-conformance harness
//! (RFC §11, gt-l3dg, gt-59sj).
//!
//! Every binding that implements `discretize()` MUST run its output through
//! this harness and emit canonical JSON that is byte-identical to the
//! committed golden files under `tests/conformance/discretize/golden/`.
//! See `tests/conformance/discretize/README.md` for the full contract.
//!
//! The Rust adapter: parse each manifest fixture, call
//! `discretize::discretize` with the manifest defaults, emit via
//! `canonical_doc_json`, compare byte-for-byte with the golden, and assert
//! within-binding determinism across two calls.

use std::path::{Path, PathBuf};

use earthsci_toolkit::{DiscretizeOptions, canonical_doc_json, discretize};

fn repo_root() -> PathBuf {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    PathBuf::from(manifest_dir)
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

fn conf_dir() -> PathBuf {
    repo_root()
        .join("tests")
        .join("conformance")
        .join("discretize")
}

fn read_json(p: &Path) -> serde_json::Value {
    let bytes = std::fs::read(p).unwrap_or_else(|e| panic!("read {}: {e}", p.display()));
    serde_json::from_slice(&bytes).unwrap_or_else(|e| panic!("parse {}: {e}", p.display()))
}

fn options_from(manifest: &serde_json::Value) -> DiscretizeOptions {
    let mut opts = DiscretizeOptions::default();
    if let Some(o) = manifest.get("options") {
        if let Some(mp) = o.get("max_passes").and_then(|v| v.as_u64()) {
            opts.max_passes = mp as usize;
        }
        if let Some(s) = o.get("strict_unrewritten").and_then(|v| v.as_bool()) {
            opts.strict_unrewritten = s;
        }
    }
    opts
}

#[test]
fn discretize_conformance_manifest() {
    let dir = conf_dir();
    let manifest_path = dir.join("manifest.json");
    let manifest = read_json(&manifest_path);
    assert_eq!(manifest["category"], "discretize");

    let fixtures = manifest["fixtures"]
        .as_array()
        .expect("fixtures must be an array");
    assert!(!fixtures.is_empty(), "manifest has no fixtures");

    let opts = options_from(&manifest);

    for f in fixtures {
        let id = f["id"].as_str().unwrap();
        let input_path = dir.join(f["input"].as_str().unwrap());
        let golden_path = dir.join(f["golden"].as_str().unwrap());
        let tags: Vec<String> = f
            .get("tags")
            .and_then(|v| v.as_array())
            .map(|a| {
                a.iter()
                    .filter_map(|x| x.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();

        assert!(
            input_path.exists(),
            "fixture {id}: input missing at {}",
            input_path.display()
        );
        assert!(
            golden_path.exists(),
            "fixture {id}: golden missing at {}",
            golden_path.display()
        );

        let input = read_json(&input_path);

        let first = discretize(&input, &opts)
            .unwrap_or_else(|e| panic!("fixture {id} (tags={tags:?}): discretize failed: {e}"));
        let first_bytes = canonical_doc_json(&first);

        // Determinism: a second call on the same input must emit identical bytes.
        let second = discretize(&input, &opts).unwrap();
        let second_bytes = canonical_doc_json(&second);
        assert_eq!(
            first_bytes, second_bytes,
            "fixture {id}: within-binding determinism violation"
        );

        // Byte-identity against the committed golden (strip one trailing '\n'
        // if present — the contract allows either side to own the newline).
        let golden = std::fs::read_to_string(&golden_path).unwrap();
        let golden_bytes = golden.strip_suffix('\n').unwrap_or(&golden);
        assert_eq!(
            first_bytes, golden_bytes,
            "fixture {id}: canonical output does not match golden"
        );
    }
}
