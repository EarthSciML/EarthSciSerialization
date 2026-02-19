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
    _comment: Optional[str] = None


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
    subsystems: Dict[str, 'Model'] = field(default_factory=dict)


@dataclass
class Species:
    """A chemical species in a reaction system."""
    name: str
    units: Optional[str] = None
    default: Optional[float] = None
    description: Optional[str] = None
    formula: Optional[str] = None  # Chemical formula


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
    constraint_equations: List[Equation] = field(default_factory=list)
    subsystems: Dict[str, 'ReactionSystem'] = field(default_factory=dict)


# ========================================
# 3. Event System
# ========================================

@dataclass
class FunctionalAffect:
    """A functional effect applied during an event."""
    handler_id: str
    read_vars: List[str] = field(default_factory=list)
    read_params: List[str] = field(default_factory=list)
    modified_params: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContinuousEvent:
    """An event that occurs when a condition becomes true during continuous evolution."""
    name: str
    conditions: List[Expr] = field(default_factory=list)  # Changed from single condition to array
    affects: List[Union[AffectEquation, FunctionalAffect]] = field(default_factory=list)
    affect_neg: Optional[List[Union[AffectEquation, FunctionalAffect]]] = None  # Added: affects for negative-going zero crossings
    root_find: Optional[Literal['left', 'right', 'all']] = 'left'  # Added: root-finding direction with default
    reinitialize: bool = False  # Added: whether to reinitialize after event
    priority: int = 0
    description: Optional[str] = None  # Added: optional description


@dataclass
class DiscreteEventTrigger:
    """Trigger condition for a discrete event."""
    type: Literal['condition', 'periodic', 'preset_times']
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
    GRIDDED_DATA = "gridded_data"
    EMISSIONS = "emissions"
    TIMESERIES = "timeseries"
    STATIC = "static"
    CALLBACK = "callback"


@dataclass
class DataLoader:
    """Configuration for loading external data."""
    name: str
    type: DataLoaderType
    source: str  # file path, URL, or connection string
    format_options: Dict[str, Any] = field(default_factory=dict)
    variables: List[str] = field(default_factory=list)
    # Store full metadata for each provided variable (units, description, etc.)
    provides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Operator:
    """A registered runtime operator (e.g., dry deposition, wet scavenging)."""
    operator_id: str
    needed_vars: List[str]
    modifies: Optional[List[str]] = None
    reference: Optional['Reference'] = None
    config: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None


class CouplingType(Enum):
    """Types of coupling between model components matching ESM schema."""
    OPERATOR_COMPOSE = "operator_compose"
    COUPLE2 = "couple2"
    VARIABLE_MAP = "variable_map"
    OPERATOR_APPLY = "operator_apply"
    CALLBACK = "callback"
    EVENT = "event"


@dataclass
class ConnectorEquation:
    """Single equation in a connector system."""
    from_var: str
    to_var: str
    transform: str
    expression: Optional[Expr] = None


@dataclass
class Connector:
    """Connector system with equations."""
    equations: List[ConnectorEquation] = field(default_factory=list)


# Base class for all coupling entries
@dataclass
class BaseCouplingEntry:
    """Base class for all coupling entry types."""
    coupling_type: CouplingType
    description: Optional[str] = None


@dataclass
class OperatorComposeCoupling(BaseCouplingEntry):
    """Coupling entry for operator_compose type."""
    coupling_type: CouplingType = field(default=CouplingType.OPERATOR_COMPOSE, init=False)
    systems: List[str] = field(default_factory=list)
    translate: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Couple2Coupling(BaseCouplingEntry):
    """Coupling entry for couple2 type."""
    coupling_type: CouplingType = field(default=CouplingType.COUPLE2, init=False)
    systems: List[str] = field(default_factory=list)
    coupletype_pair: List[str] = field(default_factory=list)
    connector: Optional[Connector] = None


@dataclass
class VariableMapCoupling(BaseCouplingEntry):
    """Coupling entry for variable_map type."""
    coupling_type: CouplingType = field(default=CouplingType.VARIABLE_MAP, init=False)
    from_var: Optional[str] = None
    to_var: Optional[str] = None
    transform: Optional[str] = None
    factor: Optional[float] = None


@dataclass
class OperatorApplyCoupling(BaseCouplingEntry):
    """Coupling entry for operator_apply type."""
    coupling_type: CouplingType = field(default=CouplingType.OPERATOR_APPLY, init=False)
    operator: Optional[str] = None


@dataclass
class CallbackCoupling(BaseCouplingEntry):
    """Coupling entry for callback type."""
    coupling_type: CouplingType = field(default=CouplingType.CALLBACK, init=False)
    callback_id: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventCoupling(BaseCouplingEntry):
    """Coupling entry for event type."""
    coupling_type: CouplingType = field(default=CouplingType.EVENT, init=False)
    event_type: Optional[str] = None
    conditions: List[Expr] = field(default_factory=list)
    trigger: Optional["DiscreteEventTrigger"] = None
    affects: List["AffectEquation"] = field(default_factory=list)
    affect_neg: List["AffectEquation"] = field(default_factory=list)
    discrete_parameters: List[str] = field(default_factory=list)
    root_find: Optional[str] = None
    reinitialize: Optional[bool] = None


# Discriminated union of all coupling entry types
CouplingEntry = Union[
    OperatorComposeCoupling,
    Couple2Coupling,
    VariableMapCoupling,
    OperatorApplyCoupling,
    CallbackCoupling,
    EventCoupling
]


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
    PER_VARIABLE = "per_variable"
    FUNCTION = "function"
    DATA = "data"


@dataclass
class InitialCondition:
    """Initial condition specification."""
    type: InitialConditionType
    value: Optional[Union[float, Expr]] = None
    values: Optional[Dict[str, float]] = None  # For per_variable type
    function: Optional[str] = None
    data_source: Optional[str] = None


class BoundaryConditionType(Enum):
    """Types of boundary conditions."""
    ZERO_GRADIENT = "zero_gradient"
    CONSTANT = "constant"
    PERIODIC = "periodic"
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"
    ROBIN = "robin"


@dataclass
class BoundaryCondition:
    """Boundary condition specification."""
    type: BoundaryConditionType
    dimensions: List[str]
    value: Optional[Union[float, Expr]] = None
    function: Optional[str] = None
    # Robin boundary condition parameters (αu + β∂u/∂n = γ)
    robin_alpha: Optional[float] = None  # Coefficient for u
    robin_beta: Optional[float] = None   # Coefficient for ∂u/∂n
    robin_gamma: Optional[Union[float, Expr]] = None  # RHS value/expression


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
    models: Dict[str, Model] = field(default_factory=dict)
    reaction_systems: Dict[str, ReactionSystem] = field(default_factory=dict)
    events: List[Union[ContinuousEvent, DiscreteEvent]] = field(default_factory=list)
    data_loaders: List[DataLoader] = field(default_factory=list)
    operators: List[Operator] = field(default_factory=list)
    coupling: List[CouplingEntry] = field(default_factory=list)
    domain: Optional[Domain] = None
    solver: Optional[Solver] = None