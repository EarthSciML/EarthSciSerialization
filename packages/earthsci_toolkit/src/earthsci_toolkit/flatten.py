"""
Coupled system flattening for ESM Format.

This module flattens a coupled multi-system ESM file into a single unified
system with dot-namespaced variables. The flattening process:

1. Iterates over all models and reaction_systems
2. Namespaces all variables (prefix with "SystemName.")
3. Processes coupling entries to record variable mappings and composition rules
4. Returns a unified FlattenedSystem
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .esm_types import (
    EsmFile, Model, ReactionSystem, Equation, ExprNode, Expr,
    CouplingEntry, CouplingType,
    OperatorComposeCoupling, CouplingCouple, VariableMapCoupling,
    OperatorApplyCoupling, CallbackCoupling, EventCoupling,
)


@dataclass
class FlattenedEquation:
    """An equation in the flattened system with namespaced variables."""
    lhs: str  # dot-namespaced variable name
    rhs: str  # expression string with namespaced references
    source_system: str  # which system this came from


@dataclass
class FlattenMetadata:
    """Metadata about which systems were flattened and how."""
    source_systems: List[str] = field(default_factory=list)
    coupling_rules: List[str] = field(default_factory=list)


@dataclass
class FlattenedSystem:
    """A coupled system flattened to a single system with dot-namespaced variables."""
    state_variables: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    equations: List[FlattenedEquation] = field(default_factory=list)
    metadata: FlattenMetadata = field(default_factory=FlattenMetadata)


def _expr_to_string(expr: Expr) -> str:
    """Convert an ESM expression tree to a human-readable string."""
    if isinstance(expr, (int, float)):
        return str(expr)
    elif isinstance(expr, str):
        return expr
    elif isinstance(expr, ExprNode):
        args_str = [_expr_to_string(arg) for arg in expr.args]

        # Infix operators
        if expr.op in ("+", "-", "*", "/", "^", "**"):
            if expr.op == "-" and len(args_str) == 1:
                return f"(-{args_str[0]})"
            return f"({' '.join(a + ' ' + expr.op if i < len(args_str) - 1 else a for i, a in enumerate(args_str))})"

        # Derivative operator
        if expr.op == "D" and expr.wrt:
            return f"D({args_str[0]}, {expr.wrt})"

        # Gradient operator
        if expr.op == "grad" and expr.dim:
            return f"grad({args_str[0]}, {expr.dim})"

        # Function-style operators
        return f"{expr.op}({', '.join(args_str)})"
    else:
        return str(expr)


def _namespace_expr(expr: Expr, system_name: str) -> Expr:
    """Recursively prefix all string variable references in an expression with the system name."""
    if isinstance(expr, (int, float)):
        return expr
    elif isinstance(expr, str):
        return f"{system_name}.{expr}"
    elif isinstance(expr, ExprNode):
        namespaced_args = [_namespace_expr(arg, system_name) for arg in expr.args]
        return ExprNode(
            op=expr.op,
            args=namespaced_args,
            wrt=f"{system_name}.{expr.wrt}" if expr.wrt else None,
            dim=expr.dim,
        )
    else:
        return expr


def _flatten_model(model: Model, system_name: str, result: FlattenedSystem) -> None:
    """Flatten a single model into the result, namespacing all variables."""
    for var_name, var in model.variables.items():
        namespaced = f"{system_name}.{var_name}"
        if var.type == "state":
            result.state_variables.append(namespaced)
        elif var.type == "parameter":
            result.parameters.append(namespaced)

        # Record variable description/type in the variables dict
        description = var.description or var.type
        result.variables[namespaced] = description

    for eq in model.equations:
        namespaced_lhs = _namespace_expr(eq.lhs, system_name)
        namespaced_rhs = _namespace_expr(eq.rhs, system_name)
        result.equations.append(FlattenedEquation(
            lhs=_expr_to_string(namespaced_lhs),
            rhs=_expr_to_string(namespaced_rhs),
            source_system=system_name,
        ))

    # Recursively flatten subsystems
    for sub_name, sub_model in model.subsystems.items():
        nested_name = f"{system_name}.{sub_name}"
        _flatten_model(sub_model, nested_name, result)


def _flatten_reaction_system(rs: ReactionSystem, system_name: str, result: FlattenedSystem) -> None:
    """Flatten a single reaction system into the result, namespacing all species and parameters."""
    for species in rs.species:
        namespaced = f"{system_name}.{species.name}"
        result.state_variables.append(namespaced)
        description = species.description or "species"
        result.variables[namespaced] = description

    for param in rs.parameters:
        namespaced = f"{system_name}.{param.name}"
        result.parameters.append(namespaced)
        description = param.description or "parameter"
        result.variables[namespaced] = description

    for eq in rs.constraint_equations:
        namespaced_lhs = _namespace_expr(eq.lhs, system_name)
        namespaced_rhs = _namespace_expr(eq.rhs, system_name)
        result.equations.append(FlattenedEquation(
            lhs=_expr_to_string(namespaced_lhs),
            rhs=_expr_to_string(namespaced_rhs),
            source_system=system_name,
        ))

    # Recursively flatten subsystems
    for sub_name, sub_rs in rs.subsystems.items():
        nested_name = f"{system_name}.{sub_name}"
        _flatten_reaction_system(sub_rs, nested_name, result)


def _process_coupling(coupling_entries: List[CouplingEntry], metadata: FlattenMetadata) -> None:
    """Process coupling entries and record rules in the metadata."""
    for entry in coupling_entries:
        if isinstance(entry, OperatorComposeCoupling):
            systems_str = " -> ".join(entry.systems)
            rule = f"operator_compose: {systems_str}"
            if entry.translate:
                translations = ", ".join(
                    f"{k}={v}" for k, v in entry.translate.items()
                )
                rule += f" [translate: {translations}]"
            metadata.coupling_rules.append(rule)

        elif isinstance(entry, CouplingCouple):
            systems_str = " <-> ".join(entry.systems)
            rule = f"couple: {systems_str}"
            if entry.connector and entry.connector.equations:
                eq_strs = []
                for ceq in entry.connector.equations:
                    eq_strs.append(f"{ceq.from_var}->{ceq.to_var}({ceq.transform})")
                rule += f" [connector: {'; '.join(eq_strs)}]"
            metadata.coupling_rules.append(rule)

        elif isinstance(entry, VariableMapCoupling):
            from_var = entry.from_var or "?"
            to_var = entry.to_var or "?"
            transform = entry.transform or "identity"
            rule = f"variable_map: {from_var} -> {to_var} ({transform})"
            if entry.factor is not None:
                rule += f" * {entry.factor}"
            metadata.coupling_rules.append(rule)

        elif isinstance(entry, OperatorApplyCoupling):
            operator = entry.operator or "?"
            rule = f"operator_apply: {operator}"
            metadata.coupling_rules.append(rule)

        elif isinstance(entry, CallbackCoupling):
            callback_id = entry.callback_id or "?"
            rule = f"callback: {callback_id}"
            metadata.coupling_rules.append(rule)

        elif isinstance(entry, EventCoupling):
            event_type = entry.event_type or "?"
            rule = f"event: {event_type}"
            if entry.conditions:
                rule += f" [{len(entry.conditions)} condition(s)]"
            metadata.coupling_rules.append(rule)

        else:
            desc = getattr(entry, "description", None) or str(type(entry).__name__)
            metadata.coupling_rules.append(f"unknown: {desc}")


def flatten(esm_file: EsmFile) -> FlattenedSystem:
    """
    Flatten a coupled multi-system ESM file into a single unified system.

    The flattening process:
    1. Iterates over all models and reaction_systems in the ESM file
    2. Namespaces all variables with their system name (e.g., "ModelA.x")
    3. Processes coupling entries into human-readable rule descriptions
    4. Returns a FlattenedSystem with all variables, equations, and metadata

    Args:
        esm_file: The parsed ESM file containing models, reaction systems, and coupling

    Returns:
        A FlattenedSystem with dot-namespaced variables and unified equations

    Raises:
        ValueError: If the ESM file has no models or reaction systems to flatten
    """
    if not esm_file.models and not esm_file.reaction_systems:
        raise ValueError(
            "Cannot flatten an ESM file with no models or reaction systems"
        )

    result = FlattenedSystem()

    # Collect source system names
    for name in esm_file.models:
        result.metadata.source_systems.append(name)
    for name in esm_file.reaction_systems:
        result.metadata.source_systems.append(name)

    # Flatten models
    for name, model in esm_file.models.items():
        _flatten_model(model, name, result)

    # Flatten reaction systems
    for name, rs in esm_file.reaction_systems.items():
        _flatten_reaction_system(rs, name, result)

    # Process coupling
    if esm_file.coupling:
        _process_coupling(esm_file.coupling, result.metadata)

    return result
