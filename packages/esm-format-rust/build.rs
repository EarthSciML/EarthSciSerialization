//! Build script for esm-format
//!
//! This script handles build-time configuration and optionally
//! generates code from the JSON schema.

use std::env;

fn main() {
    // Re-run the build script if Cargo.toml changes
    println!("cargo:rerun-if-changed=Cargo.toml");
    println!("cargo:rerun-if-changed=../../esm-schema.json");

    // Set version info from Cargo
    let version = env!("CARGO_PKG_VERSION");
    println!("cargo:rustc-env=ESM_FORMAT_VERSION={}", version);

    // TODO: In a more complete implementation, we could:
    // - Generate types from the JSON schema automatically
    // - Bundle the schema file as a resource
    // - Set up conditional compilation based on features

    println!("cargo:rustc-cfg=esm_format_built");
}