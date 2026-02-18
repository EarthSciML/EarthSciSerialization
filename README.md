# EarthSciSerialization

[![Build Status](https://github.com/EarthSciML/EarthSciSerialization/workflows/CI/badge.svg)](https://github.com/EarthSciML/EarthSciSerialization/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**EarthSciML Serialization Format** — A language-agnostic JSON-based format for earth science model components, their composition, and runtime configuration.

## Overview

The ESM (`.esm`) format enables persistence, interchange, and version control for earth science models across multiple programming languages. Every model is fully self-describing: all equations, variables, parameters, species, and reactions are specified in the format itself, allowing conforming parsers in any language to reconstruct the complete mathematical system.

**Key Features:**
- 🌍 **Language-agnostic** — Works with Julia, TypeScript, Python, Rust, and Go
- 📄 **Human-readable** — JSON-based format that's diff-friendly for version control
- 🔗 **Composable** — Define coupling between model components
- ✅ **Validated** — Built-in schema validation and consistency checks
- 🧮 **Mathematical** — Rich expression system with operators and units

## Quick Start

### Loading an ESM Model

**Julia:**
```julia
using ESMFormat
esm_file = load("model.esm")
println("Model has $(length(esm_file.models)) components")
```

**TypeScript/Node.js:**
```typescript
import { load, validate } from 'esm-format';
const esmFile = load('model.esm');
const result = validate(esmFile);
```

**Python:**
```python
import esm_format
esm_file = esm_format.load("model.esm")
print(f"Model has {len(esm_file.models)} components")
```

## Packages

This repository contains multiple language implementations of the ESM format:

| Package | Language | Description | Directory |
|---------|----------|-------------|-----------|
| **ESMFormat.jl** | Julia | Complete MTK/Catalyst integration | [`packages/ESMFormat.jl/`](packages/ESMFormat.jl/) |
| **esm-format** | TypeScript | Web/Node.js types and utilities | [`packages/esm-format/`](packages/esm-format/) |
| **esm_format** | Python | Scientific Python integration | [`packages/esm_format/`](packages/esm_format/) |
| **esm-format-rust** | Rust | High-performance implementation | [`packages/esm-format-rust/`](packages/esm-format-rust/) |
| **esm-format-go** | Go | Lightweight Go implementation | [`packages/esm-format-go/`](packages/esm-format-go/) |
| **esm-editor** | SolidJS | Interactive web-based editor | [`packages/esm-editor/`](packages/esm-editor/) |

## Installation

### Julia
```julia
using Pkg
Pkg.add("ESMFormat")
```

### TypeScript/Node.js
```bash
npm install esm-format
```

### Python
```bash
pip install esm-format
```

### Rust
```toml
[dependencies]
esm-format = "0.1.0"
```

### Go
```bash
go get github.com/EarthSciML/EarthSciSerialization/packages/esm-format-go
```

## Format Specification

The ESM format supports:

- **Models**: ODE-based model components with variables, parameters, and equations
- **Reaction Systems**: Chemical reaction networks with species and reactions
- **Coupling**: Rules for composing multiple model components
- **Domain**: Spatial and temporal domain specifications
- **Operators**: Registered mathematical operators and data loaders
- **Metadata**: Authorship, provenance, and documentation

### Example ESM File

```json
{
  "esm": "0.1.0",
  "metadata": {
    "name": "SimpleChemistry",
    "description": "Basic atmospheric chemistry model",
    "authors": ["Chris Tessum"]
  },
  "models": {
    "chemistry": {
      "variables": [
        {
          "name": "O3",
          "description": "Ozone concentration",
          "units": "molec/cm^3",
          "initial": 1e12
        }
      ],
      "equations": [
        {
          "lhs": {
            "op": "D",
            "args": ["O3", "t"]
          },
          "rhs": {
            "op": "-",
            "args": [
              {
                "op": "*",
                "args": ["k1", "O3"]
              }
            ]
          }
        }
      ]
    }
  }
}
```

## Documentation

- **[Format Specification](esm-spec.md)** — Complete ESM format documentation
- **[Library Specification](esm-libraries-spec.md)** — Requirements for ESM library implementations
- **[Schema Reference](esm-schema.json)** — Authoritative JSON schema
- **[Conformance Testing](CONFORMANCE_TESTING.md)** — Cross-language test suite
- **[Validation Matrix](ESM_COMPLIANCE_VALIDATION_MATRIX.md)** — Implementation compliance tracking

## Contributing

We welcome contributions! This project uses:

- **[Beads](https://github.com/beadshq/beads)** for issue tracking and project management
- **Julia** testing with `julia --project=. -e 'using Pkg; Pkg.test()'`
- **Cross-language conformance tests** to ensure implementation consistency

See individual package directories for language-specific development guides.

## License

This project is licensed under the [MIT License](LICENSE).

## Citation

If you use EarthSciSerialization in your research, please cite:

```bibtex
@software{earthsciserialization,
  title = {EarthSciSerialization: Language-agnostic serialization for earth science models},
  author = {Chris Tessum and contributors},
  year = {2026},
  url = {https://github.com/EarthSciML/EarthSciSerialization}
}
```