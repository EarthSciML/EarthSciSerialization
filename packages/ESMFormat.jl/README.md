# ESMFormat.jl

[![Build Status](https://github.com/EarthSciML/EarthSciSerialization/workflows/CI/badge.svg)](https://github.com/EarthSciML/EarthSciSerialization/actions)
[![Docs](https://img.shields.io/badge/docs-stable-blue.svg)](https://earthsciml.github.io/EarthSciSerialization/packages/ESMFormat.jl/stable)
[![Docs](https://img.shields.io/badge/docs-dev-blue.svg)](https://earthsciml.github.io/EarthSciSerialization/packages/ESMFormat.jl/dev)

EarthSciML Serialization Format Julia library.

ESMFormat.jl provides Julia types and functions for working with ESM format files,
which are JSON-based serialization format for EarthSciML model components,
their composition, and runtime configuration.

## Features

- **Complete Type System**: Rich type hierarchy for earth science models
- **JSON Serialization**: Parse and serialize ESM format files
- **Expression Support**: Mathematical expressions with variables and operators
- **Model Composition**: Coupling multiple earth science model components
- **Schema Validation**: Built-in JSON schema validation
- **MTK Integration**: Convert to/from ModelingToolkit.jl systems
- **Catalyst Integration**: Support for reaction network models
- **Unit Validation**: Dimensional analysis and unit checking
- **Graph Analysis**: Dependency and coupling graph generation

## Installation

```julia
using Pkg
Pkg.add("ESMFormat")
```

## Quick Start

```julia
using ESMFormat

# Load an ESM format file
esm_file = load("model.esm")

# Access model components
model = esm_file.models["atmosphere"]
println("Model has $(length(model.variables)) variables")

# Convert to ModelingToolkit (if available)
mtk_system = to_mtk_system(model, "AtmosphereModel")

# Validate the model
result = validate(esm_file)
if result.valid
    println("Model is valid!")
else
    println("Validation errors: ", result.errors)
end
```

## Documentation

For detailed documentation, examples, and API reference, see:
- [Stable Documentation](https://earthsciml.github.io/EarthSciSerialization/packages/ESMFormat.jl/stable)
- [Development Documentation](https://earthsciml.github.io/EarthSciSerialization/packages/ESMFormat.jl/dev)

## Contributing

Contributions are welcome! Please see the [contributing guide](../../CONTRIBUTING.md) for details.

## License

This package is part of the EarthSciSerialization project and is licensed under the MIT License.