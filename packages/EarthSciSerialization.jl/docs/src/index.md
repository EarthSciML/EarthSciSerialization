```@meta
CurrentModule = EarthSciSerialization
```

# EarthSciSerialization.jl

Documentation for [EarthSciSerialization.jl](https://github.com/EarthSciML/EarthSciSerialization).

EarthSciSerialization.jl is a Julia library for working with the EarthSciML Serialization Format (ESM format),
a JSON-based serialization format for earth science model components, their composition, and runtime configuration.

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

```@index
```

```@autodocs
Modules = [EarthSciSerialization]
```