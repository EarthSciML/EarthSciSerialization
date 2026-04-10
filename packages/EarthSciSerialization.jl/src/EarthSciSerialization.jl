"""
    EarthSciSerialization

EarthSciML Serialization Format Julia library.

This module provides Julia types and functions for working with ESM format files,
which are JSON-based serialization format for EarthSciML model components,
their composition, and runtime configuration.
"""
module EarthSciSerialization

# Disable precompilation to avoid method overwriting errors with dependencies
__precompile__(false)

# Import required dependencies
using JSON3
using JSONSchema

# Include type definitions and functionality
include("availability.jl")  # Include before other modules that need availability checking
include("types.jl")
include("error_handling.jl")
include("validate.jl")
include("reactions.jl")
# MTK and Catalyst modules - need to be loaded before coupled.jl since it uses their mock systems
include("mtk.jl")
include("catalyst.jl")
include("mtk_catalyst.jl")
include("coupled.jl")  # Include after mtk.jl and catalyst.jl since it uses MockMTKSystem and MockCatalystSystem
include("flatten.jl")  # Include after coupled.jl since it uses CouplingEntry types
include("parse.jl")
include("serialize.jl")
include("expression.jl")
include("display.jl")
# Analysis features
include("graph.jl")
include("units.jl")
include("edit.jl")
# Code generation
include("codegen.jl")

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
    CouplingOperatorCompose, CouplingCouple, CouplingVariableMap,
    CouplingOperatorApply, CouplingCallback, CouplingEvent,
    # Coupled system
    MockCoupledSystem,
    # Flattened system
    FlattenedEquation, FlattenMetadata, FlattenedSystem, flatten,
    # System types
    Domain, Interface, Reference, Metadata, EsmFile,
    # JSON functionality
    load, save, ParseError, SchemaValidationError, SchemaError, validate_schema,
    # Subsystem reference resolution
    resolve_subsystem_refs!, SubsystemRefError,
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
    to_catalyst_system, MockCatalystSystem,
    # MTK conversion functions
    to_mtk_system, from_mtk_system, from_catalyst_system,
    to_coupled_system,
    # Expression conversion utilities
    esm_to_symbolic, symbolic_to_esm,
    # Graph analysis (Section 4.8)
    Graph, ComponentNode, CouplingEdge, VariableNode, DependencyEdge,
    component_graph, expression_graph, adjacency, predecessors, successors,
    to_dot, to_mermaid, to_json,
    # Chemical subscript rendering
    render_chemical_formula, format_node_label,
    # Unit validation
    parse_units, get_expression_dimensions, validate_equation_dimensions,
    validate_model_dimensions, validate_reaction_system_dimensions, validate_file_dimensions,
    infer_variable_units,
    # Editing operations (Section 4)
    add_variable, remove_variable, rename_variable,
    add_equation, remove_equation, substitute_in_equations,
    add_reaction, remove_reaction, add_species, remove_species,
    add_continuous_event, add_discrete_event, remove_event,
    add_coupling, remove_coupling, compose, map_variable,
    merge, extract,
    # Legacy compatibility aliases (for tests)
    MockMTKSystem,
    esm_to_mock_symbolic, mock_symbolic_to_esm,
    # Availability checking functions
    check_mtk_availability, check_catalyst_availability, check_mtk_catalyst_availability,
    # Code generation
    to_julia_code, to_python_code,
    # ASCII display format
    to_ascii, format_expression_ascii

end # module EarthSciSerialization