# ESM Format - Python Package

A Python package for handling Earth System Model serialization and mathematical expressions.

## Installation

```bash
pip install -e .
```

## Features

- Type definitions for mathematical expressions and equations
- Model variable and equation representations
- Chemical species and reaction system modeling
- Event system for continuous and discrete events
- Data loading and mathematical operators
- Coupling between model components
- Computational domain and solver specifications
- Comprehensive metadata support

## Usage

```python
from esm_format import Expr, Model, Species, Reaction

# Create mathematical expressions
expr = ExprNode(op="+", args=[1, 2])

# Define model variables
var = ModelVariable(type="state", units="kg/m^3", description="Concentration")

# Build models
model = Model(name="MyModel")
```

## Development

Install development dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```