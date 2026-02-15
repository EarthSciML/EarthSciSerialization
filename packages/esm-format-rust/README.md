# ESM Format - Rust Implementation

Rust implementation of the EarthSciML Serialization Format (ESM).

## Features

- **Core**: Parse, serialize, pretty-print, substitute, validate schema
- **Analysis**: Unit checking, equation counting, structural validation
- **CLI Tool**: Command-line interface for validation and conversion
- **WASM**: WebAssembly compilation for web use

## Installation

### As a Library

Add this to your `Cargo.toml`:

```toml
[dependencies]
esm-format = "0.1.0"
```

### As a CLI Tool

```bash
cargo install esm-format --features cli
```

### For WASM

```bash
wasm-pack build --target web --features wasm
```

## Usage

### Library

```rust
use esm_format::{load, save, validate};

// Load an ESM file
let content = std::fs::read_to_string("model.esm")?;
let esm_file = load(&content)?;

// Validate it
let validation_result = validate(&esm_file);
if !validation_result.valid {
    for error in validation_result.errors {
        println!("Error: {}", error.message);
    }
}

// Save it back
let json = save(&esm_file)?;
```

### CLI

```bash
# Validate an ESM file
esm validate model.esm

# Convert to compact JSON
esm convert model.esm -o model_compact.json -f compact-json

# Pretty print expressions
esm pretty-print model.esm -f latex

# Show file information
esm info model.esm
```

## Building

### Library and CLI

```bash
cargo build --release
```

### WASM

```bash
wasm-pack build --target web --features wasm
```

### Cross-compilation

The crate supports cross-compilation to various targets:

```bash
# For Linux ARM64
cargo build --target aarch64-unknown-linux-gnu

# For Windows
cargo build --target x86_64-pc-windows-gnu

# For macOS ARM64
cargo build --target aarch64-apple-darwin
```

## Development

Run tests:

```bash
cargo test
```

Run tests with all features:

```bash
cargo test --all-features
```

Format code:

```bash
cargo fmt
```

Lint:

```bash
cargo clippy
```

## Features

- `default`: Includes CLI functionality
- `cli`: Command-line interface (requires clap)
- `wasm`: WebAssembly bindings (requires wasm-bindgen)

## License

MIT

## Contributing

Please see the main repository for contribution guidelines.