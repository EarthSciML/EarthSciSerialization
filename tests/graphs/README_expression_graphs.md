# Expression Graph Test Fixtures

This directory contains test fixtures for expression graphs as specified in ESM Libraries Spec Section 4.8.2.

Expression graphs are variable-level directed graphs where **nodes are variables and parameters** and **edges are mathematical dependencies** extracted from equations and reactions.

## Test Coverage

These test fixtures cover all granularity levels specified in the spec:

### 1. Expression Level (`expression_graph_expression.json`)
- **Input**: Complex rate expression `1.8e-12 * exp(-1370/T) * M`
- **Purpose**: Test parsing of arbitrary expressions into dependency graphs
- **Key Features**: Shows how variables within expressions become nodes and dependency relationships

### 2. Equation Level (`expression_graph_single_equation.json`)
- **Input**: Single ODE equation `D(x)/dt = -x`
- **Purpose**: Test graph generation for individual differential equations
- **Key Features**: Shows LHS variable as target, RHS variables as sources

### 3. Reaction Level (`expression_graph_single_reaction.json`, `expression_graph_simple_photolysis.json`)
- **Input**: Individual reactions (R1: `NO + O3 → NO2`, R2: `NO2 → NO + O3`)
- **Purpose**: Test stoichiometric and rate parameter dependency extraction
- **Key Features**:
  - Stoichiometric edges (substrates → products, self-loss edges)
  - Rate parameter edges (parameters → all affected species)
  - Complex vs simple rate expressions

### 4. System Level (`expression_graph_reaction_system.json`)
- **Input**: Complete SimpleOzone reaction system (2 reactions)
- **Purpose**: Test multi-reaction system graph construction
- **Key Features**: Combined graph showing interactions across reactions

### 5. Model Level (`expression_graph_model.json`)
- **Input**: Advection model with spatial operators
- **Purpose**: Test ODE system graph generation with spatial terms
- **Key Features**: Template variables (`_var`), spatial operators (`grad`), multiplicative dependencies

### 6. File Level (`expression_graph_file_level.json`)
- **Input**: Complete ESM file with coupling
- **Purpose**: Test cross-system edge creation from coupling rules
- **Key Features**:
  - Cross-system edges from `variable_map` coupling
  - Cross-system edges from `operator_compose` coupling
  - Scoped variable names (system prefixes)
  - Integration of all system types (reaction_systems, models, data_loaders)

## Node Data Structure

Each node contains:
- `name`: Variable name (scoped for file-level graphs)
- `kind`: `"state"` | `"parameter"` | `"observed"` | `"species"`
- `units`: Unit string or null
- `system`: Source system name

## Edge Data Structure

Each edge contains:
- `source`: Influencing variable name
- `target`: Influenced variable name
- `relationship`: `"additive"` | `"multiplicative"` | `"rate"` | `"stoichiometric"` | `"variable_map"`
- `equation_index`: Which equation/reaction produced this edge (null for coupling)
- `expression`: Relevant subexpression (optional)
- `label`: Human-readable description

## Export Formats

Each test fixture includes expected outputs in three standard formats:

### DOT (Graphviz)
For piping to layout engines. Includes colors for different edge types:
- Black: Within-system dependencies
- Blue: Variable mapping coupling
- Red: Operator composition coupling

### Mermaid
For embedding in Markdown documentation. Uses different arrow styles:
- `-->`: Standard dependencies
- `-.->`: Variable mapping
- `==>`: Operator composition

### JSON Adjacency List
For programmatic consumption:
```json
{
  "nodes": ["var1", "var2", ...],
  "adjacency": {
    "var1": [{"neighbor": "var2", "edge": {...}}],
    ...
  }
}
```

## Usage in Tests

These fixtures are designed to test:

1. **Parser correctness**: Can libraries extract the correct nodes and edges?
2. **Coupling resolution**: Do file-level graphs properly resolve coupling rules?
3. **Export functionality**: Do libraries generate correct DOT/Mermaid/JSON outputs?
4. **Cross-language consistency**: Do different language implementations produce equivalent graphs?

## Relationship Types

- **stoichiometric**: Species production/consumption in reactions
- **rate**: Parameter influences reaction rates
- **additive**: Variable appears additively in equation RHS
- **multiplicative**: Variable appears multiplicatively in equation RHS
- **variable_map**: Cross-system variable coupling