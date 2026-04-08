# Comprehensive Graph Generation Test Fixtures

## Overview

This directory contains comprehensive test fixtures for validating graph generation capabilities across all ESM format implementations. These fixtures extend the existing basic graph tests to cover advanced scenarios including coupling resolution, export format validation, edge relationship types, subsystem hierarchy, and cycle detection.

## Test Suite Structure

### 1. Comprehensive Graph Generation Fixtures (`comprehensive_graph_generation_fixtures.json`)

**Purpose**: End-to-end testing of complex graph scenarios with multiple systems and coupling types.

**Test Cases**:
- **`coupling_resolution_complex`**: Multi-system coupling with all relationship types
- **`hierarchical_subsystems`**: Nested subsystem structure with multi-level hierarchy
- **`cycle_detection_comprehensive`**: Multiple cycle types including self-loops and complex cycles
- **`edge_relationship_types_comprehensive`**: All edge relationship types with validation
- **`export_format_validation`**: Format-specific validation requirements

**Key Features Tested**:
- Cross-system variable mapping
- Operator composition coupling
- Temperature-dependent rate parameters
- Feedback loops creating cycles
- Multi-level system hierarchy
- All standard export formats (DOT, Mermaid, GraphML, JSON)

### 2. Cycle Detection Fixtures (`cycle_detection_fixtures.json`)

**Purpose**: Specialized testing of cycle detection algorithms and resolution strategies.

**Test Cases**:
- **`no_cycles_linear_chain`**: Baseline acyclic case for verification
- **`simple_two_node_cycle`**: Basic bidirectional coupling cycle
- **`complex_multi_cycle`**: Multiple overlapping cycles with different lengths
- **`self_reference_cycle`**: Self-referential equations and delay feedback
- **`hierarchical_cycles`**: Cycles at different hierarchical levels

**Validation Requirements**:
- Correct identification of all cycle types
- Strongly connected component analysis
- Execution order determination with cycle resolution
- Performance benchmarks for large graphs

### 3. Subsystem Hierarchy Fixtures (`subsystem_hierarchy_fixtures.json`)

**Purpose**: Testing hierarchical system organization and scoped variable resolution.

**Test Cases**:
- **`nested_three_level_hierarchy`**: Deep nesting with clear dependency structure
- **`mixed_hierarchy_types`**: Models, reaction systems, and operators in hierarchy
- **`dynamic_hierarchy_reconfiguration`**: Time-dependent structural changes

**Validation Requirements**:
- Correct scoped variable name resolution
- Cross-hierarchy dependency tracking
- Dynamic reconfiguration handling
- Type-specific hierarchy rules

## Export Format Specifications

### GraphML Export
- **Schema**: Compliant with GraphML 1.0 specification
- **Required Elements**: `<graphml>`, `<graph>`, `<node>`, `<edge>`, `<key>`
- **Node Attributes**: `name`, `kind`, `units`, `system`, `default_value`
- **Edge Attributes**: `relationship`, `label`, `equation_index`, `expression`, `weight`
- **Validation**: XML well-formedness and XSD schema compliance

### DOT Export
- **Format**: Graphviz DOT language
- **Features**: Subgraphs for system grouping, styled edges by relationship type
- **Node Shapes**: Variables (ellipse), Parameters (box), Species (diamond), Data (house)
- **Edge Colors**: Variable mapping (blue), Operator composition (red), Rate (black)
- **Validation**: Parse successfully with all Graphviz layout engines

### Mermaid Export
- **Format**: Mermaid graph syntax
- **Features**: Subgraphs with icons, relationship-specific arrow styles
- **Styling**: CSS classes for different node and edge types
- **Interactivity**: Click handlers and tooltips where supported
- **Validation**: Render correctly in Mermaid-enabled viewers

## Edge Relationship Types

### Core Relationship Types
1. **`stoichiometric`**: Species production/consumption (quantitative, mass-conserving)
2. **`rate`**: Parameter influences on rates (temperature-dependent)
3. **`additive`**: Linear additive dependencies (superposition applies)
4. **`multiplicative`**: Nonlinear multiplicative coupling (variable coupling strength)
5. **`variable_map`**: Direct variable coupling (instantaneous, unit-consistent)
6. **`operator_compose`**: Processed coupling through operators (may introduce delays)

### Specialized Relationship Types
7. **`spatial_derivative`**: Spatial operators (grad, div, curl)
8. **`temporal_derivative`**: Time derivative dependencies
9. **`feedback`**: Feedback loops (stability-critical, cyclic)
10. **`conditional`**: State-dependent relationships (discontinuous, nonlinear)

## Cycle Detection Requirements

### Cycle Types to Detect
- **Self-loops**: Single-node cycles (e.g., `x' = f(x, ...)`)
- **Simple cycles**: Two-node bidirectional coupling
- **Complex cycles**: Multi-node cycles with varying path lengths
- **Overlapping cycles**: Multiple cycles sharing nodes or edges
- **Hierarchical cycles**: Cycles spanning different system levels

### Analysis Outputs Required
- **Strongly Connected Components**: Tarjan's algorithm implementation
- **Cycle Enumeration**: All fundamental cycles in the graph
- **Execution Strategies**: Solver recommendations for each SCC
- **Dependency Levels**: Topological ordering where possible
- **Critical Coupling Identification**: Edges that break major cycles

## Subsystem Hierarchy Requirements

### Hierarchy Analysis
- **Depth Calculation**: Maximum nesting level
- **Parent-Child Relationships**: Complete hierarchy tree
- **Cross-Level Dependencies**: Dependencies spanning hierarchy levels
- **Scoped Variable Resolution**: Correct prefixing and namespace handling

### Component Type Handling
- **Models**: Differential equation systems with subsystem nesting
- **Reaction Systems**: Chemical networks with subsystem chemistry
- **Operators**: Computational modules with hierarchical composition
- **Data Loaders**: External data sources with structured organization

## Performance Benchmarks

### Graph Size Benchmarks
- **Small**: < 50 nodes, < 100 edges (response time < 100ms)
- **Medium**: 50-500 nodes, 100-1000 edges (response time < 1s)
- **Large**: 500-5000 nodes, 1000-10000 edges (response time < 10s)
- **Extra Large**: > 5000 nodes, > 10000 edges (response time < 60s)

### Memory Usage Limits
- **Graph Storage**: O(V + E) memory complexity
- **Export Generation**: Streaming output for large graphs
- **Cycle Detection**: Efficient SCC algorithms for large graphs

## Validation Test Matrix

| Feature | Basic | Intermediate | Advanced |
|---------|-------|--------------|----------|
| **Variable Dependencies** | ✓ | ✓ | ✓ |
| **Cross-System Coupling** | - | ✓ | ✓ |
| **Cycle Detection** | - | Simple | Complex |
| **Hierarchy Resolution** | - | - | ✓ |
| **Export Formats** | JSON | DOT, Mermaid | GraphML, Custom |
| **Performance** | < 50 nodes | < 500 nodes | < 5000 nodes |

## Implementation Requirements

### For Library Implementers
1. **Parse** all fixture ESM files correctly
2. **Generate** expression and component graphs as specified
3. **Export** graphs in all required formats
4. **Validate** against expected outputs (exact match for deterministic parts)
5. **Performance** test against size benchmarks

### For Test Framework Integration
1. **Automated Validation**: Compare outputs against expected results
2. **Format Compliance**: Validate export formats against schemas
3. **Performance Monitoring**: Track response times and memory usage
4. **Cross-Platform Testing**: Verify consistency across implementations
5. **Regression Testing**: Detect changes in graph generation behavior

## Future Extensions

### Planned Additions
- **Temporal Graphs**: Time-varying graph structures
- **Probabilistic Edges**: Uncertainty quantification in dependencies
- **Interactive Visualization**: Web-based graph exploration tools
- **Graph Analytics**: Centrality measures, community detection
- **Optimization Targets**: Graph-based model optimization

### Compatibility Considerations
- **Version Management**: Fixture versioning for backward compatibility
- **Format Evolution**: Support for new export formats
- **Schema Extensions**: Extensible metadata schemas
- **Tool Integration**: Integration with external graph analysis tools