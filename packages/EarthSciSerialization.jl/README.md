# EarthSciSerialization.jl

[![Cross-Language Conformance Testing](https://github.com/EarthSciML/EarthSciSerialization/actions/workflows/conformance-testing.yml/badge.svg)](https://github.com/EarthSciML/EarthSciSerialization/actions/workflows/conformance-testing.yml)
[![Docs](https://img.shields.io/badge/docs-stable-blue.svg)](https://earthsciml.github.io/EarthSciSerialization/packages/EarthSciSerialization.jl/stable)
[![Docs](https://img.shields.io/badge/docs-dev-blue.svg)](https://earthsciml.github.io/EarthSciSerialization/packages/EarthSciSerialization.jl/dev)

EarthSciML Serialization Format Julia library.

EarthSciSerialization.jl provides Julia types and functions for working with ESM format files,
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
Pkg.add("EarthSciSerialization")
```

## Quick Start

```julia
using EarthSciSerialization

# Load an ESM format file
esm_file = load("model.esm")

# Access model components
model = esm_file.models["atmosphere"]
println("Model has $(length(model.variables)) variables")

# Convert to ModelingToolkit (extension loads automatically when MTK is imported)
using ModelingToolkit
sys = ModelingToolkit.System(model; name=:AtmosphereModel)
# Or, for models with spatial independent variables:
# pde = ModelingToolkit.PDESystem(model; name=:AtmosphereModel)

# Without ModelingToolkit loaded, the same pattern works via mock fallbacks:
mock_sys = MockMTKSystem(model; name=:AtmosphereModel)

# Validate the model
result = validate(esm_file)
if result.is_valid
    println("Model is valid!")
else
    println("Validation errors: ", result.structural_errors)
end
```

## Public API: constructor dispatch

EarthSciSerialization uses Julia package extensions (1.9+) for deep
ModelingToolkit and Catalyst integration. The public API is constructor
dispatch on the foreign types:

```julia
# Flatten first, then build a live symbolic system
flat = flatten(esm_file)
sys  = ModelingToolkit.System(flat; name=:Atmosphere)    # pure ODE
pde  = ModelingToolkit.PDESystem(flat; name=:Atmosphere) # with spatial IVs
rxn  = Catalyst.ReactionSystem(esm_file.reaction_systems["Chem"]; name=:Chem)

# Reverse direction: live system → ESM Model
recovered = EarthSciSerialization.Model(sys)
```

The `MockMTKSystem`, `MockPDESystem`, and `MockCatalystSystem` types provide
pure-Julia fallbacks when ModelingToolkit and Catalyst are not loaded, with
the same ODE-vs-PDE dispatch semantics as the real constructors.

## Documentation

For detailed documentation, examples, and API reference, see:
- [Stable Documentation](https://earthsciml.github.io/EarthSciSerialization/packages/EarthSciSerialization.jl/stable)
- [Development Documentation](https://earthsciml.github.io/EarthSciSerialization/packages/EarthSciSerialization.jl/dev)

## Contributing

Contributions are welcome! Please see the [contributing guide](../../CONTRIBUTING.md) for details.

## License

This package is part of the EarthSciSerialization project and is licensed under the MIT License.