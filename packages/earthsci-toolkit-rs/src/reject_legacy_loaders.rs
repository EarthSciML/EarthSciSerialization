//! Load-time rejection of legacy (pre-0.7.0) pure-I/O data-loader shapes.
//!
//! esm-spec.md §8, RFC pure-io-data-loaders §4.1, ess-v9a.7.
//!
//! The v0.7.0 pure-I/O hard break reduced `DataLoader` to pure I/O and removed
//! two loader-level blocks:
//!   - `DataLoader.regridding` — regridding is now a per-variable model concern
//!     (see `Model.regrid`).
//!   - `DataLoader.spatial` — the native grid is now a GDD `Grid` under `grid`.
//!
//! A file declaring `esm` < 0.7.0 that still carries one of those removed
//! blocks is rejected at load time with a named, version-keyed diagnostic —
//! mirroring [`reject_expression_templates_pre_v04`] so the user sees a stable
//! migration hint instead of a generic schema "additionalProperties" error.
//! Mirrors the equivalent TS / Python / Julia / Go checks for
//! cross-binding-uniform diagnostics.
//!
//! Operates on the pre-deserialization `serde_json::Value` view; in `load` /
//! `load_path` it runs right after `reject_expression_templates_pre_v04` and
//! before schema validation.
//!
//! [`reject_expression_templates_pre_v04`]: crate::lower_expression_templates::reject_expression_templates_pre_v04

use serde_json::Value;

/// Stable diagnostic codes raised by the legacy data-loader rejection pass.
/// Mirrors the codes emitted by the TS / Python / Julia / Go bindings
/// (`data_loader_regridding_removed`, `data_loader_spatial_removed`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyDataLoaderError {
    pub code: &'static str,
    pub message: String,
}

impl std::fmt::Display for LegacyDataLoaderError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[{}] {}", self.code, self.message)
    }
}

impl std::error::Error for LegacyDataLoaderError {}

fn err(code: &'static str, message: impl Into<String>) -> LegacyDataLoaderError {
    LegacyDataLoaderError {
        code,
        message: message.into(),
    }
}

/// Reject `DataLoader.regridding` / `DataLoader.spatial` blocks in files
/// declaring `esm` < 0.7.0, with the named diagnostics
/// `data_loader_regridding_removed` / `data_loader_spatial_removed`
/// (esm-spec.md §8, RFC pure-io-data-loaders §4.1).
pub fn reject_legacy_data_loader_shapes(view: &Value) -> Result<(), LegacyDataLoaderError> {
    let Some(obj) = view.as_object() else {
        return Ok(());
    };
    let Some(esm) = obj.get("esm").and_then(|v| v.as_str()) else {
        return Ok(());
    };
    let parts: Vec<&str> = esm.split('.').collect();
    if parts.len() != 3 {
        return Ok(());
    }
    let major: u32 = match parts[0].parse() {
        Ok(v) => v,
        Err(_) => return Ok(()),
    };
    let minor: u32 = match parts[1].parse() {
        Ok(v) => v,
        Err(_) => return Ok(()),
    };
    // Version gate: only pre-0.7.0 files can still carry the removed blocks.
    if !(major == 0 && minor < 7) {
        return Ok(());
    }

    let Some(loaders) = obj.get("data_loaders").and_then(|v| v.as_object()) else {
        return Ok(());
    };

    let mut regridding_paths: Vec<String> = Vec::new();
    let mut spatial_paths: Vec<String> = Vec::new();
    for (name, loader) in loaders {
        let Some(loader_obj) = loader.as_object() else {
            continue;
        };
        if loader_obj.contains_key("regridding") {
            regridding_paths.push(format!("/data_loaders/{name}/regridding"));
        }
        if loader_obj.contains_key("spatial") {
            spatial_paths.push(format!("/data_loaders/{name}/spatial"));
        }
    }

    if !regridding_paths.is_empty() {
        return Err(err(
            "data_loader_regridding_removed",
            format!(
                "DataLoader `regridding` was removed in esm 0.7.0 (regridding is now a \
                 per-variable model concern — see `Model.regrid`; RFC pure-io-data-loaders \
                 §4.1); file declares {esm}. Migrate by deleting the block and moving the \
                 per-variable regridding choice to the owning model. Offending paths: {}",
                regridding_paths.join(", ")
            ),
        ));
    }
    if !spatial_paths.is_empty() {
        return Err(err(
            "data_loader_spatial_removed",
            format!(
                "DataLoader `spatial` was removed in esm 0.7.0 (the native grid is now a \
                 GDD `Grid` under `grid`; RFC pure-io-data-loaders §4.1); file declares \
                 {esm}. Migrate by replacing the block with a `grid` GDD Grid. Offending \
                 paths: {}",
                spatial_paths.join(", ")
            ),
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const REGRIDDING_FIXTURE: &str =
        include_str!("../../../tests/conformance/migration/0_6_to_0_7/loader_regridding_removed.esm");
    const SPATIAL_FIXTURE: &str =
        include_str!("../../../tests/conformance/migration/0_6_to_0_7/loader_spatial_removed.esm");
    const MIGRATED_FIXTURE: &str =
        include_str!("../../../tests/conformance/migration/0_6_to_0_7/loader_migrated.esm");

    #[test]
    fn rejects_legacy_regridding_block() {
        let view: Value = serde_json::from_str(REGRIDDING_FIXTURE).expect("parse fixture");
        let e = reject_legacy_data_loader_shapes(&view).expect_err("should reject regridding");
        assert_eq!(e.code, "data_loader_regridding_removed");
    }

    #[test]
    fn rejects_legacy_spatial_block() {
        let view: Value = serde_json::from_str(SPATIAL_FIXTURE).expect("parse fixture");
        let e = reject_legacy_data_loader_shapes(&view).expect_err("should reject spatial");
        assert_eq!(e.code, "data_loader_spatial_removed");
    }

    #[test]
    fn accepts_migrated_loader() {
        let view: Value = serde_json::from_str(MIGRATED_FIXTURE).expect("parse fixture");
        reject_legacy_data_loader_shapes(&view).expect("migrated 0.7.0 fixture must pass");
        // The migrated 0.7.0 shape must also load cleanly through the full pipeline.
        crate::parse::load(MIGRATED_FIXTURE).expect("migrated fixture must load");
    }

    #[test]
    fn version_gate_skips_070_files() {
        // A 0.7.0 file is past the gate, so a stray `regridding` key is a no-op
        // here — it is the schema's additionalProperties:false that rejects it.
        let view = json!({"esm": "0.7.0", "data_loaders": {"w": {"regridding": {}}}});
        reject_legacy_data_loader_shapes(&view).expect("0.7.0 is version-gated to a no-op");
    }
}
