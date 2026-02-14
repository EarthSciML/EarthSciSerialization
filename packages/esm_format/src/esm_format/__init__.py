"""
ESM Format - Earth System Model Serialization Format

A Python package for handling Earth System Model serialization and mathematical expressions.
"""

from .types import (
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
    Solver,
    Reference,
    Metadata,
    EsmFile,
)
from .parse import load, SchemaValidationError, UnsupportedVersionError
from .serialize import save
from .validation import validate, ValidationResult, ValidationError
from .verification import (
    MathematicalVerifier,
    VerificationResult,
    VerificationReport,
    VerificationStatus,
    verify_reaction_system,
    verify_model,
    compute_stoichiometric_matrix,
)
from .simulation import (
    simulate,
    simulate_with_discrete_events,
    SimulationResult,
    SimulationError,
)
from .data_loaders import (
    NetCDFLoader,
    create_data_loader,
)

__version__ = "0.1.0"
__all__ = [
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
    "Solver",
    "Reference",
    "Metadata",
    "EsmFile",
    "load",
    "save",
    "validate",
    "ValidationResult",
    "ValidationError",
    "SchemaValidationError",
    "UnsupportedVersionError",
    "MathematicalVerifier",
    "VerificationResult",
    "VerificationReport",
    "VerificationStatus",
    "verify_reaction_system",
    "verify_model",
    "compute_stoichiometric_matrix",
    "simulate",
    "simulate_with_discrete_events",
    "SimulationResult",
    "SimulationError",
    "NetCDFLoader",
    "create_data_loader",
]