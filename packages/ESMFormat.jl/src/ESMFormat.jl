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
include("parse.jl")
include("serialize.jl")
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
    # System types
    Domain, Solver, Reference, Metadata, EsmFile,
    # JSON functionality
    load, save, ParseError, SchemaValidationError,
    # MTK/Catalyst conversion functions
    to_mtk_system, to_catalyst_system, from_mtk_system, from_catalyst_system,
    # Mock system types
    MockMTKSystem, MockCatalystSystem,
    # Expression conversion utilities
    esm_to_mock_symbolic, mock_symbolic_to_esm

end # module ESMFormat