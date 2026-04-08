# ESM Format - Rust Implementation

Rust implementation of the EarthSciML Serialization Format (ESM).

## Features

- **Core**: Parse, serialize, pretty-print, substitute, validate schema
- **Analysis**: Unit checking, equation counting, structural validation
- **CLI Tool**: Command-line interface for validation and conversion
- **WASM**: WebAssembly compilation for web use
- **High Performance**: Zero-copy parsing, parallel evaluation, SIMD optimization
- **Memory Efficient**: Custom allocators and compact expression trees
- **Benchmarking**: Comprehensive performance analysis with criterion.rs

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

### High-Performance Build

For maximum performance, enable all optimization features:

```bash
cargo build --release --features performance
```

Available performance features:
- `parallel`: Multi-threaded evaluation with rayon
- `simd`: SIMD-optimized mathematical operations
- `zero_copy`: Fast JSON parsing with simd-json
- `custom_alloc`: Custom memory allocators for large models
- `performance`: Enables all performance features

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

### High-Performance Usage

For performance-critical applications:

```rust
use esm_format::{
    performance::{CompactExpr, ParallelEvaluator, simd_math},
    load, stoichiometric_matrix
};
use std::collections::HashMap;

// Fast parsing with zero-copy SIMD JSON
#[cfg(feature = "zero_copy")]
{
    let mut json_bytes = content.into_bytes();
    let esm_file = esm_format::performance::fast_parse(&mut json_bytes)?;
}

// Compact expression evaluation
let expr = load_expression_from_file("complex_expr.json")?;
let compact = CompactExpr::from_expr(&expr);
let variables = HashMap::from([("x".to_string(), 1.5), ("k".to_string(), 0.1)]);

// Fast stack-based evaluation
let result = compact.evaluate_fast(&variables)?;

// Parallel expression batch evaluation
#[cfg(feature = "parallel")]
{
    let evaluator = ParallelEvaluator::new(Some(4))?; // Use 4 threads
    let expressions = load_many_expressions()?;
    let results = evaluator.evaluate_batch(&expressions, &variables)?;
}

// SIMD-optimized vector operations
#[cfg(feature = "simd")]
{
    let a = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
    let b = vec![2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0];
    let mut result = vec![0.0; 8];

    // SIMD vector addition (4x faster than scalar)
    simd_math::add_vectors_simd(&a, &b, &mut result)?;

    // SIMD dot product
    let dot_product = simd_math::dot_product_simd(&a, &b)?;
}

// Parallel stoichiometric matrix computation
#[cfg(feature = "parallel")]
{
    let reaction_system = load_reaction_system()?;
    let matrix = evaluator.compute_stoichiometric_matrix_parallel(&reaction_system)?;
}

// Custom memory allocation for large models
#[cfg(feature = "custom_alloc")]
{
    use esm_format::performance::ModelAllocator;

    let mut allocator = ModelAllocator::with_capacity(1_000_000);
    let large_array = allocator.alloc_slice::<f64>(10000);
    // Process large model...
    allocator.reset(); // Reuse memory
}
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