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

# Enhanced parsing with CSV integration (optional - requires pandas)
try:
    from .parse import load_with_csv_data
    _has_enhanced_loading = True
except (ImportError, ValueError, Exception):
    _has_enhanced_loading = False

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

# Simulation tier - box model simulation (optional - requires scipy)
_has_simulation = False
try:
    from .simulation import (
        simulate,
        simulate_with_discrete_events,
        SimulationResult,
        SimulationError,
    )
    _has_simulation = True
except (ImportError, ValueError, Exception):
    # scipy not available or compatibility issues, skip simulation functionality
    pass

# Display and pretty-printing (Core tier requirement)
from .display import (
    explore,
    ESMExplorer,
    to_unicode,
    to_latex,
    to_ascii,
)

# Code generation (for interoperability)
from .codegen import (
    to_julia_code,
    to_python_code,
)

# Migration functionality
from .migration import (
    migrate,
    can_migrate,
    get_supported_migration_targets,
    MigrationError,
)

# Data loading functionality (optional - requires pandas)
_has_csv_support = False
try:
    from .csv_loader import (
        CSVLoader,
        CSVValidationError,
        load_csv_data,
    )
    _has_csv_support = True
except (ImportError, ValueError, Exception):
    # pandas not available or compatibility issues, skip CSV loader functionality
    pass

# Gridded data loading functionality (optional - requires xarray/netCDF4/h5py)
_has_gridded_support = False
try:
    from .gridded_loader import (
        GriddedDataLoader,
        GriddedValidationError,
        load_gridded_data,
    )
    _has_gridded_support = True
except (ImportError, ValueError, Exception):
    # gridded data libraries not available or compatibility issues
    pass

# Callback data loading functionality (no external dependencies)
_has_callback_support = False
try:
    from .callback_loader import (
        CallbackLoader,
        CallbackValidationError,
        CallbackDataSource,
        load_callback_data,
    )
    _has_callback_support = True
except (ImportError, ValueError, Exception):
    # callback loader functionality failed to load
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


    # Display and pretty-printing
    "explore",
    "ESMExplorer",
    "to_unicode",
    "to_latex",
    "to_ascii",

    # Code generation
    "to_julia_code",
    "to_python_code",

    # Migration functionality
    "migrate",
    "can_migrate",
    "get_supported_migration_targets",
    "MigrationError",
]

# Add CSV data loading components if pandas is available
if _has_csv_support:
    __all__.extend([
        "CSVLoader",
        "CSVValidationError",
        "load_csv_data",
    ])

# Add gridded data loading components if libraries are available
if _has_gridded_support:
    __all__.extend([
        "GriddedDataLoader",
        "GriddedValidationError",
        "load_gridded_data",
    ])

# Add callback data loading components
if _has_callback_support:
    __all__.extend([
        "CallbackLoader",
        "CallbackValidationError",
        "CallbackDataSource",
        "load_callback_data",
    ])

# Add enhanced loading if available
if _has_enhanced_loading:
    __all__.append("load_with_csv_data")

# Add simulation components if scipy is available
if _has_simulation:
    __all__.extend([
        "simulate",
        "simulate_with_discrete_events",
        "SimulationResult",
        "SimulationError",
    ])