"""
Type definitions for ESM Format using dataclasses.
"""

from dataclasses import dataclass, field
from typing import Union, List, Dict, Any, Optional, Literal
from enum import Enum


# ========================================
# 1. Expression Types
# ========================================

@dataclass
class ExprNode:
    """A node in an expression tree."""
    op: str
    args: List['Expr'] = field(default_factory=list)
    wrt: Optional[str] = None  # with respect to (for derivatives)
    dim: Optional[str] = None  # dimension information


# Recursive type definition for expressions
Expr = Union[int, float, str, ExprNode]


@dataclass
class Equation:
    """Mathematical equation with left and right hand sides."""
    lhs: Expr
    rhs: Expr


@dataclass
class AffectEquation:
    """Equation that affects a variable (assignment-like)."""
    lhs: str  # variable name being affected
    rhs: Expr  # expression to compute


# ========================================
# 2. Model Components
# ========================================

@dataclass
class ModelVariable:
    """A variable in a mathematical model."""
    type: Literal['state', 'parameter', 'observed']
    units: Optional[str] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    expression: Optional[Expr] = None


@dataclass
class Model:
    """A mathematical model containing variables and equations."""
    name: str
    variables: Dict[str, ModelVariable] = field(default_factory=dict)
    equations: List[Equation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Species:
    """A chemical species in a reaction system."""
    name: str
    formula: Optional[str] = None
    mass: Optional[float] = None
    units: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Parameter:
    """A parameter for reaction systems."""
    name: str
    value: Union[float, Expr]
    units: Optional[str] = None
    description: Optional[str] = None
    uncertainty: Optional[float] = None


@dataclass
class Reaction:
    """A chemical reaction."""
    name: str
    reactants: Dict[str, float] = field(default_factory=dict)  # species -> coefficient
    products: Dict[str, float] = field(default_factory=dict)   # species -> coefficient
    rate_constant: Optional[Union[float, Expr]] = None
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReactionSystem:
    """A system of chemical reactions."""
    name: str
    species: List[Species] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    reactions: List[Reaction] = field(default_factory=list)


# ========================================
# 3. Event System
# ========================================

@dataclass
class FunctionalAffect:
    """A functional effect applied during an event."""
    target: str
    function: str
    arguments: List[Any] = field(default_factory=list)


@dataclass
class ContinuousEvent:
    """An event that occurs when a condition becomes true during continuous evolution."""
    name: str
    condition: Expr
    affects: List[Union[AffectEquation, FunctionalAffect]] = field(default_factory=list)
    priority: int = 0


@dataclass
class DiscreteEventTrigger:
    """Trigger condition for a discrete event."""
    type: Literal['time', 'condition', 'external']
    value: Union[float, Expr, str]  # time value, condition expression, or external identifier


@dataclass
class DiscreteEvent:
    """An event that occurs at discrete time points."""
    name: str
    trigger: DiscreteEventTrigger
    affects: List[Union[AffectEquation, FunctionalAffect]] = field(default_factory=list)
    priority: int = 0


# ========================================
# 4. Data Loading and Operations
# ========================================

class DataLoaderType(Enum):
    """Types of data loaders."""
    CSV = "csv"
    JSON = "json"
    NETCDF = "netcdf"
    HDF5 = "hdf5"
    BINARY = "binary"
    DATABASE = "database"


@dataclass
class DataLoader:
    """Configuration for loading external data."""
    name: str
    type: DataLoaderType
    source: str  # file path, URL, or connection string
    format_options: Dict[str, Any] = field(default_factory=dict)
    variables: List[str] = field(default_factory=list)


class OperatorType(Enum):
    """Types of mathematical operators."""
    INTERPOLATION = "interpolation"
    INTEGRATION = "integration"
    DIFFERENTIATION = "differentiation"
    FILTERING = "filtering"
    TRANSFORMATION = "transformation"
    ARITHMETIC = "arithmetic"
    LOGICAL = "logical"


@dataclass
class Operator:
    """Mathematical operator applied to data or expressions."""
    name: str
    type: OperatorType
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_variables: List[str] = field(default_factory=list)
    output_variables: List[str] = field(default_factory=list)


class CouplingType(Enum):
    """Types of coupling between model components."""
    DIRECT = "direct"
    INTERPOLATED = "interpolated"
    AGGREGATED = "aggregated"
    FEEDBACK = "feedback"


@dataclass
class CouplingEntry:
    """Entry describing how model components are coupled."""
    source_model: str
    target_model: str
    source_variables: List[str]
    target_variables: List[str]
    coupling_type: CouplingType
    transformation: Optional[Operator] = None


# ========================================
# 5. Computational Domain and Solving
# ========================================

@dataclass
class TemporalDomain:
    """Temporal domain specification."""
    start: str  # ISO datetime string
    end: str    # ISO datetime string
    reference_time: Optional[str] = None  # ISO datetime string


@dataclass
class SpatialDimension:
    """Spatial dimension specification."""
    min: float
    max: float
    units: str
    grid_spacing: Optional[float] = None


@dataclass
class CoordinateTransform:
    """Coordinate transformation specification."""
    id: str
    description: str
    dimensions: List[str]


class InitialConditionType(Enum):
    """Types of initial conditions."""
    CONSTANT = "constant"
    FUNCTION = "function"
    DATA = "data"


@dataclass
class InitialCondition:
    """Initial condition specification."""
    type: InitialConditionType
    value: Optional[Union[float, Expr]] = None
    function: Optional[str] = None
    data_source: Optional[str] = None


class BoundaryConditionType(Enum):
    """Types of boundary conditions."""
    ZERO_GRADIENT = "zero_gradient"
    CONSTANT = "constant"
    PERIODIC = "periodic"
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


@dataclass
class BoundaryCondition:
    """Boundary condition specification."""
    type: BoundaryConditionType
    dimensions: List[str]
    value: Optional[Union[float, Expr]] = None
    function: Optional[str] = None


@dataclass
class Domain:
    """Comprehensive computational domain specification."""
    name: Optional[str] = None
    independent_variable: Optional[str] = None
    temporal: Optional[TemporalDomain] = None
    spatial: Optional[Dict[str, SpatialDimension]] = None
    coordinate_transforms: List[CoordinateTransform] = field(default_factory=list)
    spatial_ref: Optional[str] = None
    initial_conditions: Optional[InitialCondition] = None
    boundary_conditions: List[BoundaryCondition] = field(default_factory=list)

    # Legacy support for backwards compatibility
    dimensions: Optional[Dict[str, Any]] = None
    coordinates: Dict[str, List[float]] = field(default_factory=dict)
    boundaries: Dict[str, Any] = field(default_factory=dict)


class SolverType(Enum):
    """Types of numerical solvers."""
    ODE = "ode"
    PDE = "pde"
    ALGEBRAIC = "algebraic"
    STOCHASTIC = "stochastic"
    HYBRID = "hybrid"


@dataclass
class Solver:
    """Numerical solver configuration."""
    name: str
    type: SolverType
    algorithm: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    tolerances: Dict[str, float] = field(default_factory=dict)


# ========================================
# 6. Metadata and File Structure
# ========================================

@dataclass
class Reference:
    """Bibliographic reference."""
    title: str
    authors: List[str] = field(default_factory=list)
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None


@dataclass
class Metadata:
    """Metadata about the model or dataset."""
    title: str
    description: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    created: Optional[str] = None  # ISO datetime string
    modified: Optional[str] = None  # ISO datetime string
    version: str = "1.0"
    references: List[Reference] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EsmFile:
    """Root container for an ESM format file."""
    version: str
    metadata: Metadata
    models: List[Model] = field(default_factory=list)
    reaction_systems: List[ReactionSystem] = field(default_factory=list)
    events: List[Union[ContinuousEvent, DiscreteEvent]] = field(default_factory=list)
    data_loaders: List[DataLoader] = field(default_factory=list)
    operators: List[Operator] = field(default_factory=list)
    couplings: List[CouplingEntry] = field(default_factory=list)
    domains: List[Domain] = field(default_factory=list)
    solvers: List[Solver] = field(default_factory=list)