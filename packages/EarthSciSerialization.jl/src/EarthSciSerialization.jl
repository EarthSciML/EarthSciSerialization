"""
    EarthSciSerialization

EarthSciML Serialization Format Julia library.

This module provides Julia types and functions for working with ESM format files,
which are JSON-based serialization format for EarthSciML model components,
their composition, and runtime configuration.

Deep ModelingToolkit/Catalyst integration is provided by package extensions
(`EarthSciSerializationMTKExt`, `EarthSciSerializationCatalystExt`) that load
automatically when the user imports `ModelingToolkit` or `Catalyst`. Without
those packages loaded, `MockMTKSystem`, `MockPDESystem`, and `MockCatalystSystem`
give plain-Julia snapshots of the flattened system with the same ODE/PDE split.
"""
module EarthSciSerialization

using Dates
using JSON3
using JSONSchema

include("types.jl")
include("error_handling.jl")
include("validate.jl")
include("reactions.jl")
include("flatten.jl")
include("mock_systems.jl")
include("parse.jl")
include("serialize.jl")
include("expression.jl")
include("display.jl")
include("graph.jl")
include("units.jl")
include("edit.jl")
include("codegen.jl")
include("canonicalize.jl")

export
    # Expression types
    Expr, NumExpr, IntExpr, VarExpr, OpExpr,
    # Literal predicates (RFC §5.4.1 int/float distinction)
    is_literal, literal_value,
    # Equation types
    Equation, AffectEquation,
    # Model component types
    ModelVariableType, StateVariable, ParameterVariable, ObservedVariable, BrownianVariable,
    ModelVariable, Model, Species, Parameter, Reaction, ReactionSystem,
    # Event types
    EventType, ContinuousEvent, DiscreteEvent, FunctionalAffect, DiscreteEventTrigger,
    ConditionTrigger, PeriodicTrigger, PresetTimesTrigger,
    # Data and operator types
    DataLoader, DataLoaderSource, DataLoaderTemporal, DataLoaderSpatial,
    DataLoaderVariable, DataLoaderRegridding,
    Operator, RegisteredFunction, RegisteredFunctionSignature, CouplingEntry,
    # Concrete coupling types
    CouplingOperatorCompose, CouplingCouple, CouplingVariableMap,
    CouplingOperatorApply, CouplingCallback, CouplingEvent,
    # Flattened system (§4.7.5 / §4.7.6)
    FlattenMetadata, FlattenedSystem, flatten, lower_reactions_to_equations,
    infer_array_shapes,
    # Flatten error taxonomy (spec §4.7.6.10, 8 types for cross-language parity)
    ConflictingDerivativeError, DimensionPromotionError, UnmappedDomainError,
    UnsupportedMappingError, DomainUnitMismatchError,
    DomainExtentMismatchError, SliceOutOfDomainError, CyclicPromotionError,
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
    validate_reaction_rate_units, validate_model_gradient_units,
    # Expression operations
    substitute, free_variables, contains, evaluate, simplify, UnboundVariableError,
    # Qualified reference resolution
    resolve_qualified_reference, QualifiedReferenceError, ReferenceResolution,
    validate_reference_syntax, is_valid_identifier,
    # Reaction system ODE derivation
    derive_odes, stoichiometric_matrix, mass_action_rate,
    # Mock systems (no-MTK / no-Catalyst fallbacks)
    MockMTKSystem, MockPDESystem, MockCatalystSystem,
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
    # Code generation
    to_julia_code, to_python_code,
    # ASCII display format
    to_ascii, format_expression_ascii,
    # Canonical AST form (RFC §5.4)
    canonicalize, canonical_json, format_canonical_float, CanonicalizeError

end # module EarthSciSerialization
