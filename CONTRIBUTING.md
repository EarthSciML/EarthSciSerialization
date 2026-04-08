# Contributing to EarthSciSerialization

Thank you for your interest in contributing to EarthSciSerialization! This guide covers everything you need to know to get started with development, testing, and submitting contributions to this multi-language earth science serialization project.

## Table of Contents

- [Overview](#overview)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Contribution Workflow](#contribution-workflow)
- [Language-Specific Guidelines](#language-specific-guidelines)
- [Documentation](#documentation)
- [Issue Tracking](#issue-tracking)
- [Release Process](#release-process)
- [Getting Help](#getting-help)

## Overview

EarthSciSerialization is a language-agnostic JSON-based format for earth science model components with implementations across multiple programming languages:

- **Julia** (ESMFormat.jl) - Complete MTK/Catalyst integration
- **TypeScript** (esm-format) - Web/Node.js types and utilities
- **Python** (esm_format) - Scientific Python integration
- **Rust** (esm-format-rust) - High-performance implementation
- **Go** (esm-format-go) - Lightweight Go implementation
- **SolidJS** (esm-editor) - Interactive web-based editor

All implementations must maintain conformance across languages through our comprehensive test suite.

## Development Setup

### Prerequisites

Ensure you have the following installed:

- **Julia** 1.9+ (for Julia package development and testing)
- **Node.js** 18+ and npm (for TypeScript/JavaScript packages)
- **Python** 3.8+ and pip (for Python package development)
- **Rust** 1.75.0+ and Cargo (for Rust package development)
- **Go** 1.19+ (for Go package development)
- **Git** (for version control)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/EarthSciML/EarthSciSerialization.git
   cd EarthSciSerialization
   ```

2. **Install dependencies for all packages:**
   ```bash
   # Use the unified dependency manager
   ./scripts/deps install
   ```

3. **Run the setup verification:**
   ```bash
   # Check all dependencies are correctly installed
   ./scripts/deps check
   ```

4. **Run the full test suite:**
   ```bash
   # Julia tests (primary testing framework)
   julia --project=. -e 'using Pkg; Pkg.test()'

   # Cross-language conformance tests
   ./scripts/test-conformance.sh
   ```

### Environment Configuration

The project includes environment management scripts:

```bash
# Manage development environments
./scripts/env-manager.sh create-dev-env
./scripts/env-manager.sh activate julia  # or python, node, rust, go
```

## Project Structure

```
EarthSciSerialization/
├── packages/                 # Language-specific implementations
│   ├── ESMFormat.jl/        # Julia implementation
│   ├── esm-format/          # TypeScript implementation
│   ├── esm_format/          # Python implementation
│   ├── esm-format-rust/     # Rust implementation
│   ├── esm-format-go/       # Go implementation
│   └── esm-editor/          # SolidJS web editor
├── tests/                   # Cross-language conformance tests
│   ├── valid/              # Valid ESM files for testing
│   ├── invalid/            # Invalid ESM files for validation testing
│   ├── conformance/        # Cross-language test fixtures
│   └── README.md           # Detailed testing documentation
├── scripts/                # Development and build scripts
├── docs/                   # Documentation and specifications
├── .github/workflows/      # CI/CD workflows
├── esm-spec.md            # Format specification
├── esm-libraries-spec.md  # Library implementation requirements
└── esm-schema.json        # Authoritative JSON schema
```

## Coding Standards

### General Principles

1. **Consistency First**: All language implementations must produce identical results for the same inputs
2. **Schema Compliance**: All changes must maintain compatibility with `esm-schema.json`
3. **Test-Driven Development**: Write tests before implementation
4. **Documentation**: All public APIs must be documented
5. **Error Handling**: Provide clear, actionable error messages

### Language-Specific Standards

Each language implementation should follow its ecosystem's conventions:

- **Julia**: Follow [Julia Style Guide](https://docs.julialang.org/en/v1/manual/style-guide/)
- **TypeScript**: Use ESLint + Prettier, follow strict type checking
- **Python**: Follow PEP 8, use type hints, run black formatter
- **Rust**: Follow `rustfmt` and `clippy` recommendations
- **Go**: Follow `gofmt` and standard Go conventions

### Code Quality Requirements

All code contributions must:

- Pass language-specific linters and formatters
- Maintain 90%+ test coverage for new functionality
- Include appropriate error handling and validation
- Follow semantic versioning for breaking changes
- Be compatible with specified minimum language versions

## Testing Requirements

### Test Categories

1. **Unit Tests**: Language-specific functionality testing
2. **Conformance Tests**: Cross-language consistency validation
3. **Integration Tests**: End-to-end workflow testing
4. **Performance Tests**: Benchmarking and scalability validation

### Running Tests

#### Full Test Suite
```bash
# Complete test suite (all languages)
./scripts/test-conformance.sh

# Individual language testing
julia --project=. -e 'using Pkg; Pkg.test()'                    # Julia
cd packages/esm-format && npm test                              # TypeScript
cd packages/esm_format && python -m pytest                     # Python
cd packages/esm-format-rust && cargo test                      # Rust
cd packages/esm-format-go && go test ./...                     # Go
```

#### Conformance Testing
```bash
# Run cross-language conformance tests
./scripts/run-julia-conformance.jl
./scripts/run-typescript-conformance.js
./scripts/run-python-conformance.py

# Generate conformance report
./scripts/generate-conformance-report.py
```

#### Test Requirements for Contributions

- **All tests must pass** before code submission
- **New features** require corresponding conformance tests
- **Bug fixes** must include regression tests
- **Breaking changes** require migration guides and deprecation notices

### Conformance Requirements

All language implementations must:

1. Parse all files in `tests/valid/` successfully
2. Reject all files in `tests/invalid/` with expected error codes
3. Produce identical outputs for display formatting tests
4. Generate consistent graph representations
5. Handle all mathematical expression types correctly

## Contribution Workflow

### Issue Tracking

We use **[Beads](https://github.com/beadshq/beads)** for project management and issue tracking:

```bash
# Find available work
bd ready

# View issue details
bd show <issue-id>

# Claim an issue
bd update <issue-id> --status=in_progress

# Close completed work
bd close <issue-id>
```

### Development Process

1. **Find or Create an Issue:**
   ```bash
   # Find ready work
   bd ready

   # Or create new issue
   bd create --title="Add feature X" --type=feature --priority=2
   ```

2. **Create a Branch:**
   ```bash
   git checkout -b feature/issue-description
   ```

3. **Make Changes:**
   - Write tests first (TDD approach)
   - Implement functionality
   - Run tests frequently: `julia --project=. -e 'using Pkg; Pkg.test()'`
   - Commit small, focused changes

4. **Test Everything:**
   ```bash
   # Run full test suite
   julia --project=. -e 'using Pkg; Pkg.test()'
   ./scripts/test-conformance.sh

   # Check dependencies
   ./scripts/deps check
   ```

5. **Submit Pull Request:**
   - Ensure all tests pass
   - Update documentation as needed
   - Reference the issue being addressed
   - Include clear description of changes

### Commit Guidelines

Follow conventional commit format:

```
type(scope): description

Examples:
feat(julia): add expression evaluation support
fix(typescript): resolve schema validation edge case
docs(spec): update coupling section examples
test(conformance): add mathematical correctness fixtures
```

## Language-Specific Guidelines

### Julia (ESMFormat.jl)

- **Primary Implementation**: Julia is the reference implementation
- **Testing**: All changes must pass Julia test suite
- **Dependencies**: Use Project.toml for dependency management
- **Integration**: Maintain ModelingToolkit.jl and Catalyst.jl compatibility
- **Performance**: Profile performance-critical code paths

```bash
# Julia development workflow
cd packages/ESMFormat.jl
julia --project=. -e 'using Pkg; Pkg.activate("."); Pkg.test()'
```

### TypeScript (esm-format)

- **Standards**: Strict TypeScript, ESLint + Prettier
- **Testing**: Jest for unit tests, cross-browser compatibility
- **Build**: Support both Node.js and browser environments
- **Types**: Maintain comprehensive type definitions

```bash
# TypeScript development workflow
cd packages/esm-format
npm install
npm run lint
npm test
npm run build
```

### Python (esm_format)

- **Standards**: PEP 8, type hints, Black formatting
- **Testing**: pytest for unit tests, mypy for type checking
- **Packaging**: Use pyproject.toml, support Python 3.8+
- **Dependencies**: Scientific Python ecosystem (NumPy, pandas)

```bash
# Python development workflow
cd packages/esm_format
pip install -e .[dev]
python -m pytest
python -m mypy esm_format/
python -m black esm_format/
```

### Rust (esm-format-rust)

- **Standards**: rustfmt, clippy, comprehensive error handling
- **Testing**: Standard Rust testing with cargo test
- **Performance**: Focus on high-performance parsing/serialization
- **Safety**: No unsafe code without thorough justification

```bash
# Rust development workflow
cd packages/esm-format-rust
cargo fmt
cargo clippy -- -D warnings
cargo test
cargo bench  # for performance testing
```

### Go (esm-format-go)

- **Standards**: gofmt, go vet, standard Go conventions
- **Testing**: Go standard testing package
- **Simplicity**: Maintain lightweight, dependency-minimal design
- **Performance**: Focus on fast parsing and low memory usage

```bash
# Go development workflow
cd packages/esm-format-go
go fmt ./...
go vet ./...
go test ./...
```

## Documentation

### Documentation Requirements

All contributions must include appropriate documentation:

- **API Documentation**: All public functions/types/methods
- **Usage Examples**: Demonstrating new functionality
- **Format Specification Updates**: For changes affecting the ESM format
- **Migration Guides**: For breaking changes

### Building Documentation

```bash
# Generate documentation for all packages
./scripts/generate_docs.py

# Validate documentation
./scripts/validate_docs.py

# Deploy documentation (maintainers only)
./scripts/deploy_docs.py
```

## Issue Tracking

We use Beads for comprehensive project management:

### Creating Issues

```bash
# Create different types of issues
bd create --title="Bug: parsing fails on complex expressions" --type=bug --priority=1
bd create --title="Feature: add GraphQL operator support" --type=feature --priority=2
bd create --title="Docs: improve Python API examples" --type=task --priority=3
```

### Issue Labels and Priorities

- **Priority Levels**: P0 (critical) to P4 (backlog)
- **Types**: bug, feature, task, epic, documentation
- **Languages**: julia, typescript, python, rust, go
- **Areas**: parser, schema, validation, performance, conformance

### Dependencies and Blocking

```bash
# Add dependencies between issues
bd dep add <dependent-issue> <blocking-issue>

# View blocked issues
bd blocked
```

## Release Process

### Version Management

All packages follow semantic versioning:

- **Major** (X.0.0): Breaking changes to ESM format or public APIs
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes, backward compatible

### Release Workflow

1. **Version Coordination**: All language packages maintain synchronized versions
2. **Testing**: Full conformance test suite must pass
3. **Documentation**: Update all relevant documentation
4. **Security**: Run security scans and address vulnerabilities
5. **Changelog**: Generate comprehensive changelog

```bash
# Automated release process (maintainers only)
./scripts/release-coordinator.sh --version=minor
```

## Getting Help

### Communication Channels

- **Issues**: Use Beads issue tracker for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and broader topics
- **Security**: See SECURITY.md for security-related concerns

### Common Development Tasks

**Adding a new operator:**
1. Update `esm-schema.json` with operator definition
2. Add conformance tests in `tests/expressions/`
3. Implement in each language package
4. Update format specification (`esm-spec.md`)

**Adding a new validation rule:**
1. Add invalid test cases to `tests/invalid/`
2. Update `expected_errors.json` with error codes
3. Implement validation in each language
4. Document in library specification

**Performance optimization:**
1. Add benchmarks in `tests/performance/`
2. Profile and optimize implementation
3. Verify conformance is maintained
4. Document performance characteristics

### Development Environment Issues

**Dependency conflicts:**
```bash
./scripts/deps check        # Diagnose issues
./scripts/deps report       # Generate detailed report
```

**Test failures:**
```bash
./scripts/test-conformance-minimal.sh  # Quick conformance check
./scripts/enhanced-conformance-analyzer.py  # Detailed analysis
```

**Documentation builds:**
```bash
./scripts/docs_maintenance.py --check  # Validate documentation
./scripts/docs_maintenance.py --fix    # Auto-fix common issues
```

Thank you for contributing to EarthSciSerialization! Your contributions help advance earth science modeling capabilities across programming languages.