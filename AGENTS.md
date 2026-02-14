# Agent Instructions for EarthSciSerialization Project

## Issue Tracking

This project uses **bd (beads)** for issue tracking.
Run `bd prime` for workflow context, or install hooks (`bd hooks install`) for auto-injection.

**Quick reference:**
- `bd ready` - Find unblocked work
- `bd create "Title" --type task --priority 2` - Create issue
- `bd close <id>` - Complete work
- `bd sync` - Sync with git (run at session end)

For full workflow details: `bd prime`

## Project Overview

This project implements the EarthSciML Serialization (ESM) format and supporting libraries for atmospheric chemistry and Earth system modeling. The project consists of:

1. **ESM Format Specification** (`esm-spec.md`) - JSON-based format for model serialization
2. **ESM Libraries Specification** (`esm-libraries-spec.md`) - Requirements for cross-language libraries
3. **Conformance Test Suite** (`tests/`) - Language-independent validation tests
4. **Implementation Libraries** (planned):
   - Julia: `ESMFormat.jl` (Full tier - MTK/Catalyst integration)
   - TypeScript: `esm-format` (Core + Analysis)
   - SolidJS: `esm-editor` (Interactive editing)
   - Python: `esm_format` (Analysis + Simulation)
   - Rust: `esm-format` (Core + CLI)
   - Go: `esm-format` (Core validation)

## Current Status

**Phase**: Test fixture development and specification refinement
**Priority**: Complete comprehensive test coverage before library implementation

## Key Specifications

### ESM Format Features
- JSON-based serialization for Earth system models
- Expression AST with 30+ mathematical operators
- Event system (continuous/discrete) with Pre operator
- 6 coupling mechanisms for system composition
- Support for ODE models and reaction networks
- Language-agnostic design

### Library Capability Tiers
- **Core**: Parse, serialize, validate, pretty-print
- **Analysis**: Unit checking, stoichiometric matrices, graph generation
- **Interactive**: Click-to-edit expressions, structural editing
- **Simulation**: Numerical ODE solving with events
- **Full**: Bidirectional MTK/Catalyst conversion (Julia only)

## Critical Test Coverage Areas

The following areas require comprehensive test fixtures (see beads issues for details):

1. **Event System** - Zero test coverage for continuous/discrete events
2. **Coupling Mechanisms** - Only 2 of 6 coupling types tested
3. **Expression Operators** - Missing 12+ operators including spatial/logical
4. **Cross-Language Conformance** - No automated cross-language validation
5. **Mathematical Verification** - No correctness verification for derived equations
6. **Interactive Editor** - No test fixtures for UI capabilities
7. **Simulation Workflows** - No reference trajectories for validation

## Development Guidelines

### Before Implementing Libraries
1. All test fixtures must be completed first
2. Cross-language conformance framework must be established
3. Mathematical verification tests must pass
4. Specification compliance must be validated

### Testing Requirements
- All valid ESM files must round-trip identically across languages
- All invalid files must produce consistent error codes
- Display formats (Unicode/LaTeX) must be identical across languages
- Graph generation must produce identical structures
- Simulation results must match reference trajectories within tolerance

### Quality Standards
- Schema validation against JSON Schema
- Structural validation with standardized error codes
- Unit/dimensional analysis verification
- Mathematical correctness validation
- Cross-language result consistency

## Dependencies

### External Specifications
- JSON Schema for validation
- ModelingToolkit.jl / Catalyst.jl semantics (Julia)
- SciPy ODE integration patterns (Python)
- SolidJS reactivity patterns (TypeScript editor)

### Test Dependencies
All test fixtures must be authored before library implementation to ensure:
- Specification compliance
- Cross-language consistency
- Mathematical correctness
- User interface functionality

## Contact

For questions about the ESM format or library specifications, refer to the specification documents or create beads issues with appropriate priority and type assignments.