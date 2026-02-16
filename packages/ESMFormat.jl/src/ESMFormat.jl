"""
    ESMFormat

EarthSciML Serialization Format Julia library.

This module provides Julia types and functions for working with ESM format files,
which are JSON-based serialization format for EarthSciML model components,
their composition, and runtime configuration.
"""
module ESMFormat

# Import required dependencies
using JSON3
using JSONSchema

# Include type definitions and functionality
include("types.jl")
include("error_handling.jl")
include("validate.jl")
include("coupled.jl")  # Include before parse.jl and serialize.jl since they use coupling types
include("parse.jl")
include("serialize.jl")
include("expression.jl")
include("display.jl")
include("reactions.jl")
include("catalyst.jl")
# MTK modules - conditionally loaded to avoid precompilation issues
include("mtk.jl")
include("mtk_catalyst.jl")

# Export main types
export
    # Expression types
    Expr, NumExpr, VarExpr, OpExpr,
    # Equation types
    Equation, AffectEquation,
    # Model component types
    ModelVariableType, StateVariable, ParameterVariable, ObservedVariable,
    ModelVariable, Model, Species, Parameter, Reaction, ReactionSystem,
    # Event types
    EventType, ContinuousEvent, DiscreteEvent, FunctionalAffect, DiscreteEventTrigger,
    ConditionTrigger, PeriodicTrigger, PresetTimesTrigger,
    # Data and operator types
    DataLoader, Operator, CouplingEntry,
    # Concrete coupling types
    CouplingOperatorCompose, CouplingCouple2, CouplingVariableMap,
    CouplingOperatorApply, CouplingCallback, CouplingEvent,
    # Coupled system
    MockCoupledSystem,
    # System types
    Domain, Solver, Reference, Metadata, EsmFile,
    # Solver types and enums
    SolverStrategy, StrangThreads, StrangSerial, IMEX,
    NumericalMethod, FiniteDifferenceMethod, FiniteElementMethod, FiniteVolumeMethod,
    SolverConfiguration,
    # Solver utility functions
    parse_solver_strategy, solver_strategy_to_string,
    parse_numerical_method, numerical_method_to_string,
    validate_solver_compatibility, get_recommended_algorithms, create_solver_with_method,
    # Serialization functions for solver (internal)
    serialize_solver, serialize_solver_configuration, coerce_solver, coerce_solver_configuration,
    # JSON functionality
    load, save, ParseError, SchemaValidationError, SchemaError, validate_schema,
    # Coupling serialization functions
    serialize_coupling_entry, coerce_coupling_entry,
    # Structural validation
    StructuralError, ValidationResult, validate_structural, validate,
    # Expression operations
    substitute, free_variables, contains, evaluate, simplify, UnboundVariableError,
    # Qualified reference resolution
    resolve_qualified_reference, QualifiedReferenceError, ReferenceResolution,
    validate_reference_syntax, is_valid_identifier,
    # Reaction system ODE derivation
    derive_odes, stoichiometric_matrix, mass_action_rate,
    # Catalyst conversion functions
    to_catalyst_system, MockCatalystSystem
    # MTK conversion functions
    to_mtk_system, from_mtk_system, from_catalyst_system,
    to_coupled_system,
    # Expression conversion utilities
    esm_to_symbolic, symbolic_to_esm,
    # Legacy compatibility aliases (for tests)
    MockMTKSystem,
    esm_to_mock_symbolic, mock_symbolic_to_esm

end # module ESMFormat