"""
ESM Format - Earth System Model Serialization Format

A Python package for handling Earth System Model serialization and mathematical expressions.
This is the core implementation following the ESM Library Specification v0.1.0.
"""

# Core data types
from .esm_types import (
    Expr,
    ExprNode,
    Equation,
    AffectEquation,
    ModelVariable,
    Model,
    Species,
    Parameter,
    Reaction,
    ReactionSystem,
    ContinuousEvent,
    DiscreteEvent,
    FunctionalAffect,
    DiscreteEventTrigger,
    DataLoader,
    DataLoaderType,
    Operator,
    OperatorType,
    CouplingEntry,
    Domain,
    TemporalDomain,
    SpatialDimension,
    CoordinateTransform,
    InitialCondition,
    InitialConditionType,
    BoundaryCondition,
    BoundaryConditionType,
    Solver,
    Reference,
    Metadata,
    EsmFile,
)

# Core parsing and serialization
from .parse import load, SchemaValidationError, UnsupportedVersionError
from .serialize import save

# Validation (Core tier requirement)
from .validation import validate, ValidationResult, ValidationError

# Expression engine (Core tier requirement)
from .expression import (
    free_variables,
    free_parameters,
    contains,
    evaluate,
    simplify,
    to_sympy,
    from_sympy,
    symbolic_jacobian as jacobian
)

# Substitution (Core tier requirement)
from .substitute import substitute, substitute_in_model, substitute_in_reaction_system

# Analysis tier - reaction system analysis
from .reactions import (
    derive_odes,
    stoichiometric_matrix,
    substrate_matrix,
    product_matrix,
)

# Analysis tier - graph representations
from .graph import (
    component_graph,
    expression_graph,
    to_dot,
    to_mermaid,
    to_json_graph,
    Graph,
    GraphNode,
    GraphEdge,
    ComponentNode,
    VariableNode,
    CouplingEdge,
    DependencyEdge,
)

# Analysis tier - unit validation
from .units import (
    validate_units,
    convert_units,
    UnitValidator,
    UnitValidationResult,
    UnitConversionResult,
)

# Core editing operations
from .edit import (
    ESMEditor,
    EditOperation,
    EditResult,
    add_model_to_file,
    add_variable_to_model,
    rename_variable_in_model,
    remove_variable_from_model,
    add_equation_to_model,
    remove_equation_from_model,
    add_reaction_to_system,
    remove_reaction_from_system,
    add_species_to_system,
    remove_species_from_system,
    add_continuous_event_to_model,
    add_discrete_event_to_model,
    remove_event_from_model,
    add_coupling_to_file,
    remove_coupling_from_file,
    compose_systems,
    map_variable_in_file,
    merge_esm_files,
    extract_component_from_file,
)

# Simulation tier - box model simulation
from .simulation import (
    simulate,
    simulate_with_discrete_events,
    SimulationResult,
    SimulationError,
)

# Display and pretty-printing (Core tier requirement)
from .display import (
    explore,
    ESMExplorer,
    to_unicode,
    to_latex,
)

# Code generation (for interoperability)
from .codegen import (
    to_julia_code,
    to_python_code,
)

# Data loading functionality (optional - requires pandas)
try:
    from .csv_loader import (
        CSVLoader,
        CSVValidationError,
        load_csv_data,
    )
except ImportError:
    # pandas not available, skip CSV loader functionality
    pass

__version__ = "0.1.0"

# Streamlined public API - only Core + Analysis + Simulation tier functionality
__all__ = [
    # Core data types
    "Expr",
    "ExprNode",
    "Equation",
    "AffectEquation",
    "ModelVariable",
    "Model",
    "Species",
    "Parameter",
    "Reaction",
    "ReactionSystem",
    "ContinuousEvent",
    "DiscreteEvent",
    "FunctionalAffect",
    "DiscreteEventTrigger",
    "DataLoader",
    "DataLoaderType",
    "Operator",
    "OperatorType",
    "CouplingEntry",
    "Domain",
    "TemporalDomain",
    "SpatialDimension",
    "CoordinateTransform",
    "InitialCondition",
    "InitialConditionType",
    "BoundaryCondition",
    "BoundaryConditionType",
    "Solver",
    "Reference",
    "Metadata",
    "EsmFile",

    # Core parsing and serialization
    "load",
    "save",

    # Validation
    "validate",
    "ValidationResult",
    "ValidationError",
    "SchemaValidationError",
    "UnsupportedVersionError",

    # Expression engine
    "free_variables",
    "free_parameters",
    "contains",
    "evaluate",
    "simplify",
    "to_sympy",
    "from_sympy",
    "jacobian",

    # Substitution
    "substitute",
    "substitute_in_model",
    "substitute_in_reaction_system",

    # Reaction system analysis
    "derive_odes",
    "stoichiometric_matrix",
    "substrate_matrix",
    "product_matrix",

    # Graph representations
    "component_graph",
    "expression_graph",
    "to_dot",
    "to_mermaid",
    "to_json_graph",
    "Graph",
    "GraphNode",
    "GraphEdge",
    "ComponentNode",
    "VariableNode",
    "CouplingEdge",
    "DependencyEdge",

    # Unit validation
    "validate_units",
    "convert_units",
    "UnitValidator",
    "UnitValidationResult",
    "UnitConversionResult",

    # Editing operations
    "ESMEditor",
    "EditOperation",
    "EditResult",
    "add_model_to_file",
    "add_variable_to_model",
    "rename_variable_in_model",
    "remove_variable_from_model",
    "add_equation_to_model",
    "remove_equation_from_model",
    "add_reaction_to_system",
    "remove_reaction_from_system",
    "add_species_to_system",
    "remove_species_from_system",
    "add_continuous_event_to_model",
    "add_discrete_event_to_model",
    "remove_event_from_model",
    "add_coupling_to_file",
    "remove_coupling_from_file",
    "compose_systems",
    "map_variable_in_file",
    "merge_esm_files",
    "extract_component_from_file",

    # Simulation
    "simulate",
    "simulate_with_discrete_events",
    "SimulationResult",
    "SimulationError",

    # Display and pretty-printing
    "explore",
    "ESMExplorer",
    "to_unicode",
    "to_latex",

    # Code generation
    "to_julia_code",
    "to_python_code",

    # Data loading
    "CSVLoader",
    "CSVValidationError",
    "load_csv_data",
]