"""
Type definitions for ESM Format using dataclasses.
"""

from dataclasses import dataclass, field
from typing import Union, List, Dict, Any, Optional, Literal, Tuple
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

    # Array-op extensions (schema §ExpressionNode). None unless the op uses them.
    # arrayop:
    output_idx: Optional[List[Union[str, int]]] = None
    expr: Optional['Expr'] = None
    reduce: Optional[str] = None  # default "+"
    ranges: Optional[Dict[str, List[int]]] = None
    # makearray:
    regions: Optional[List[List[List[int]]]] = None
    values: Optional[List['Expr']] = None
    # reshape:
    shape: Optional[List[Union[int, str]]] = None
    # transpose:
    perm: Optional[List[int]] = None
    # concat:
    axis: Optional[int] = None
    # broadcast:
    fn: Optional[str] = None
    # call (registered function invocation, see esm-spec §4.4 / §9.2):
    handler_id: Optional[str] = None


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
    """A variable in a mathematical model.

    The "brownian" type denotes a stochastic noise source (Wiener process); the
    presence of any brownian variable promotes the enclosing model from an ODE
    system to an SDE system. The optional ``noise_kind`` and
    ``correlation_group`` fields apply only to brownian variables.
    """
    type: Literal['state', 'parameter', 'observed', 'brownian']
    units: Optional[str] = None
    default: Optional[Any] = None
    default_units: Optional[str] = None
    description: Optional[str] = None
    expression: Optional[Expr] = None
    # Arrayed-variable shape: ordered dimension names from the enclosing
    # model's domain.spatial. None means scalar. See discretization RFC §10.2.
    shape: Optional[List[str]] = None
    # Staggered-grid location tag (e.g. "cell_center", "edge_normal",
    # "vertex"). None means no explicit staggering. See RFC §10.2.
    location: Optional[str] = None
    # Brownian-only: kind of stochastic process. Currently only "wiener".
    noise_kind: Optional[str] = None
    # Brownian-only: opaque tag grouping correlated noise sources.
    correlation_group: Optional[str] = None


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
    default_units: Optional[str] = None
    description: Optional[str] = None
    formula: Optional[str] = None  # Chemical formula


@dataclass
class Parameter:
    """A parameter for reaction systems."""
    name: str
    value: Union[float, Expr]
    units: Optional[str] = None
    default_units: Optional[str] = None
    description: Optional[str] = None
    uncertainty: Optional[float] = None


@dataclass
class Reaction:
    """A chemical reaction."""
    name: str
    id: Optional[str] = None
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

class DataLoaderKind(Enum):
    """Structural kind of an external data source."""
    GRID = "grid"
    POINTS = "points"
    STATIC = "static"


@dataclass
class DataLoaderSource:
    """File discovery configuration for a data loader."""
    url_template: str
    mirrors: List[str] = field(default_factory=list)


@dataclass
class DataLoaderTemporal:
    """Temporal coverage and record layout for a data source."""
    start: Optional[str] = None
    end: Optional[str] = None
    file_period: Optional[str] = None
    frequency: Optional[str] = None
    records_per_file: Optional[Union[int, str]] = None
    time_variable: Optional[str] = None


@dataclass
class DataLoaderSpatial:
    """Spatial grid description for a data source."""
    crs: str
    grid_type: str
    staggering: Dict[str, str] = field(default_factory=dict)
    resolution: Dict[str, float] = field(default_factory=dict)
    extent: Dict[str, List[float]] = field(default_factory=dict)


@dataclass
class DataLoaderVariable:
    """A variable exposed by a data loader, mapped from a source-file variable."""
    file_variable: str
    units: str
    unit_conversion: Optional[Union[float, int, 'Expr']] = None
    description: Optional[str] = None
    reference: Optional['Reference'] = None


@dataclass
class DataLoaderRegridding:
    """Structural regridding configuration for a data loader."""
    fill_value: Optional[float] = None
    extrapolation: Optional[str] = None  # "clamp", "nan", "periodic"


@dataclass
class DataLoader:
    """
    Generic, runtime-agnostic description of an external data source.

    Carries enough structural information to locate files, map timestamps
    to files, describe spatial/variable semantics, and regrid — rather than
    pointing at a runtime handler.
    """
    name: str
    kind: DataLoaderKind
    source: DataLoaderSource
    variables: Dict[str, DataLoaderVariable] = field(default_factory=dict)
    temporal: Optional[DataLoaderTemporal] = None
    spatial: Optional[DataLoaderSpatial] = None
    regridding: Optional[DataLoaderRegridding] = None
    reference: Optional['Reference'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Operator:
    """A registered runtime operator (e.g., dry deposition, wet scavenging)."""
    operator_id: str
    needed_vars: List[str]
    modifies: Optional[List[str]] = None
    reference: Optional['Reference'] = None
    config: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None


@dataclass
class RegisteredFunctionSignature:
    """Calling convention for a RegisteredFunction (see esm-spec §9.2)."""
    arg_count: int
    arg_types: Optional[List[str]] = None
    return_type: Optional[str] = None


@dataclass
class RegisteredFunction:
    """A named pure function invoked inside expressions via the 'call' op."""
    id: str
    signature: RegisteredFunctionSignature
    units: Optional[str] = None
    arg_units: Optional[List[Optional[str]]] = None
    description: Optional[str] = None
    references: List['Reference'] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class CouplingType(Enum):
    """Types of coupling between model components matching ESM schema."""
    OPERATOR_COMPOSE = "operator_compose"
    COUPLE = "couple"
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
class CouplingCouple(BaseCouplingEntry):
    """Coupling entry for couple type."""
    coupling_type: CouplingType = field(default=CouplingType.COUPLE, init=False)
    systems: List[str] = field(default_factory=list)
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
    CouplingCouple,
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
    start: Optional[str] = None  # ISO datetime string
    end: Optional[str] = None    # ISO datetime string
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

    @property
    def name(self) -> str:
        """Alias for title field (matches JSON 'name' key)."""
        return self.title


@dataclass
class EsmFile:
    """Root container for an ESM format file."""
    version: str
    metadata: Metadata
    models: Dict[str, Model] = field(default_factory=dict)
    reaction_systems: Dict[str, ReactionSystem] = field(default_factory=dict)
    events: List[Union[ContinuousEvent, DiscreteEvent]] = field(default_factory=list)
    data_loaders: Dict[str, DataLoader] = field(default_factory=dict)
    operators: List[Operator] = field(default_factory=list)
    registered_functions: Dict[str, RegisteredFunction] = field(default_factory=dict)
    coupling: List[CouplingEntry] = field(default_factory=list)
    domains: Dict[str, Domain] = field(default_factory=dict)

    @property
    def esm(self) -> str:
        """Alias for version field (matches JSON 'esm' key)."""
        return self.version