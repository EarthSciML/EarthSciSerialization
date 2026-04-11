"""
Coupled system flattening for ESM Format (spec §4.7.5 + §4.7.6).

The flattened representation is the canonical intermediate form between an
EsmFile and any downstream consumer (simulation, graph construction, validation,
solver export). All variables are dot-namespaced by their owning system, and
coupling rules have been resolved into the equation set itself.

This module is the Python equivalent of EarthSciSerialization.jl/src/flatten.jl.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .esm_types import (
    AffectEquation,
    CallbackCoupling,
    ContinuousEvent,
    CouplingCouple,
    CouplingEntry,
    DiscreteEvent,
    Domain,
    EsmFile,
    Expr,
    ExprNode,
    Model,
    OperatorApplyCoupling,
    OperatorComposeCoupling,
    ReactionSystem,
    VariableMapCoupling,
)
from .reactions import derive_odes
from .substitute import has_var_placeholder, substitute


# ============================================================================
# Errors (spec §4.7.6 — to be expanded as the dimension-promotion rules land)
# ============================================================================


class FlattenError(Exception):
    """Base class for errors raised during flatten()."""


class ConflictingDerivativeError(FlattenError):
    """Two systems define non-additive equations for the same dependent variable."""


class UnmappedDomainError(FlattenError):
    """A coupling references a variable whose domain has no mapping rule."""


class SliceOutOfDomainError(FlattenError):
    """A slice mapping reaches outside the source variable's domain."""


class UnsupportedMappingError(FlattenError):
    """A dimension-promotion mapping is not supported by this implementation tier."""


class UnsupportedDimensionalityError(FlattenError):
    """The flattened system has a dimensionality the simulator cannot handle.

    Raised by simulate() (and any ODE-only backend) when the flattened system
    contains spatial independent variables — see spec §4.7.6.12.
    """


# ============================================================================
# Data classes
# ============================================================================


@dataclass
class FlattenedVariable:
    """A single variable in the flattened system."""
    name: str  # dot-namespaced
    type: str  # "state" | "parameter" | "observed" | "species"
    units: Optional[str] = None
    default: Any = None
    description: Optional[str] = None
    source_system: Optional[str] = None


@dataclass
class FlattenedEquation:
    """An equation in the flattened system, with namespaced Expr trees.

    Backwards-compatibility note: ``lhs`` and ``rhs`` are stored as Expr trees
    (the canonical form), and ``lhs_str`` / ``rhs_str`` provide pretty-printed
    versions for tests and display.
    """
    lhs: Expr
    rhs: Expr
    source_system: str
    lhs_str: str = ""
    rhs_str: str = ""

    def __post_init__(self) -> None:
        if not self.lhs_str:
            self.lhs_str = _expr_to_string(self.lhs)
        if not self.rhs_str:
            self.rhs_str = _expr_to_string(self.rhs)


@dataclass
class FlattenMetadata:
    """Provenance metadata for a FlattenedSystem."""
    source_systems: List[str] = field(default_factory=list)
    coupling_rules: List[str] = field(default_factory=list)
    operator_applies: List[str] = field(default_factory=list)
    callbacks: List[str] = field(default_factory=list)


@dataclass
class FlattenedSystem:
    """The result of flattening an EsmFile per spec §4.7.5.

    Fields
    ------
    independent_variables:
        Independent variables of the flattened system. Always contains ``"t"``
        for temporal evolution; spatial independent variables (``"x"``, ``"y"``,
        ``"z"``) appear only when the equations contain spatial derivative
        operators (``grad``, ``div``, ``laplacian``).
    state_variables:
        Dot-namespaced state variables, keyed by their namespaced name.
    parameters:
        Dot-namespaced parameters, keyed by their namespaced name.
        Parameters promoted to variables by ``variable_map`` are removed.
    observed_variables:
        Dot-namespaced observed (algebraic / dependent) variables.
    equations:
        Flattened equations as Expr trees.
    continuous_events:
        Continuous events, with variable references rewritten to dot-namespaced
        form.
    discrete_events:
        Discrete events, similarly namespaced.
    domain:
        The file's ``domain`` section, if any (passed through unchanged).
    metadata:
        Provenance about which systems were flattened and which rules applied.

    Backwards-compatibility helpers (``variables`` dict and string-keyed
    helpers) are exposed via properties so existing call sites continue to work.
    """
    independent_variables: List[str] = field(default_factory=lambda: ["t"])
    state_variables: "OrderedDict[str, FlattenedVariable]" = field(default_factory=OrderedDict)
    parameters: "OrderedDict[str, FlattenedVariable]" = field(default_factory=OrderedDict)
    observed_variables: "OrderedDict[str, FlattenedVariable]" = field(default_factory=OrderedDict)
    equations: List[FlattenedEquation] = field(default_factory=list)
    continuous_events: List[ContinuousEvent] = field(default_factory=list)
    discrete_events: List[DiscreteEvent] = field(default_factory=list)
    domain: Optional[Domain] = None
    metadata: FlattenMetadata = field(default_factory=FlattenMetadata)

    @property
    def variables(self) -> Dict[str, str]:
        """Type label by namespaced name (compat with the old FlattenedSystem)."""
        out: Dict[str, str] = {}
        for name, var in self.state_variables.items():
            out[name] = var.type
        for name, var in self.parameters.items():
            out[name] = var.type
        for name, var in self.observed_variables.items():
            out[name] = var.type
        return out


# ============================================================================
# Expression helpers
# ============================================================================


_SPATIAL_OPS = {"grad", "div", "laplacian", "curl"}


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _expr_to_string(expr: Expr) -> str:
    """Pretty-print an Expr tree to a single-line human-readable string."""
    if expr is None:
        return ""
    if _is_number(expr):
        return str(expr)
    if isinstance(expr, str):
        return expr
    if isinstance(expr, ExprNode):
        op = expr.op
        args = [_expr_to_string(a) for a in expr.args]

        if op == "D" and expr.wrt:
            inner = args[0] if args else ""
            return f"D({inner}, {expr.wrt})"

        if op in _SPATIAL_OPS:
            inner = args[0] if args else ""
            dim = expr.dim or ""
            return f"{op}({inner}, {dim})" if dim else f"{op}({inner})"

        if op in ("+", "-", "*", "/", "^", "**"):
            if op == "-" and len(args) == 1:
                return f"(-{args[0]})"
            return "(" + f" {op} ".join(args) + ")"

        return f"{op}({', '.join(args)})"
    return str(expr)


def _namespace_expr(expr: Expr, prefix: str, leave_alone: Optional[Set[str]] = None) -> Expr:
    """Recursively prefix every variable reference in ``expr`` with ``prefix.``.

    A reference is left alone if it already contains a dot (already namespaced)
    or appears in ``leave_alone`` (e.g. independent variables like ``t``, ``x``).
    """
    leave_alone = leave_alone or set()
    if expr is None or _is_number(expr):
        return expr
    if isinstance(expr, str):
        if expr in leave_alone or "." in expr:
            return expr
        return f"{prefix}.{expr}"
    if isinstance(expr, ExprNode):
        new_args = [_namespace_expr(a, prefix, leave_alone) for a in expr.args]
        new_wrt = expr.wrt
        if new_wrt and new_wrt not in leave_alone and "." not in new_wrt:
            # The "wrt" of D() is an independent variable like t — leave it.
            # We only namespace if it looks like a state variable reference (rare).
            pass
        return ExprNode(op=expr.op, args=new_args, wrt=expr.wrt, dim=expr.dim)
    return expr


def _lhs_dependent_var(lhs: Expr) -> Optional[str]:
    """Return the dependent variable name from an LHS expression.

    For ``D(var, t)`` returns ``var``. For a bare variable name returns it.
    Returns None if the LHS is something we cannot identify (e.g. an algebraic
    constraint with a complex LHS).
    """
    if isinstance(lhs, str):
        return lhs
    if isinstance(lhs, ExprNode):
        if lhs.op == "D" and lhs.args:
            inner = lhs.args[0]
            if isinstance(inner, str):
                return inner
            if isinstance(inner, ExprNode) and inner.op == "D" and inner.args:
                return _lhs_dependent_var(inner)
        # Algebraic equation: LHS is a complex expression — not a single var.
        return None
    return None


def _has_spatial_operator(expr: Expr) -> bool:
    """Return True if ``expr`` contains a spatial derivative operator."""
    if _is_number(expr) or isinstance(expr, str) or expr is None:
        return False
    if isinstance(expr, ExprNode):
        if expr.op in _SPATIAL_OPS:
            return True
        return any(_has_spatial_operator(a) for a in expr.args)
    return False


def _spatial_dims_in_expr(expr: Expr) -> Set[str]:
    """Return the set of spatial dimension labels referenced by spatial ops."""
    out: Set[str] = set()
    if isinstance(expr, ExprNode):
        if expr.op in _SPATIAL_OPS and expr.dim:
            out.add(expr.dim)
        for arg in expr.args:
            out.update(_spatial_dims_in_expr(arg))
    return out


# ============================================================================
# Coupling rule descriptions (kept compatible with the previous module)
# ============================================================================


def _describe_coupling(entry: CouplingEntry) -> str:
    if isinstance(entry, OperatorComposeCoupling):
        systems = " + ".join(entry.systems)
        rule = f"operator_compose({systems})"
        if entry.translate:
            rule += " [translate: " + ", ".join(f"{k}->{v}" for k, v in entry.translate.items()) + "]"
        return rule
    if isinstance(entry, CouplingCouple):
        systems = " <-> ".join(entry.systems)
        return f"couple({systems})"
    if isinstance(entry, VariableMapCoupling):
        rule = f"variable_map({entry.from_var} -> {entry.to_var}, transform={entry.transform})"
        if entry.factor is not None:
            rule += f" [factor={entry.factor}]"
        return rule
    if isinstance(entry, OperatorApplyCoupling):
        return f"operator_apply({entry.operator})"
    if isinstance(entry, CallbackCoupling):
        return f"callback({entry.callback_id})"
    return f"unknown({type(entry).__name__})"


# ============================================================================
# Per-system collection (model + reaction systems lowered to ODEs)
# ============================================================================


@dataclass
class _ComponentSystem:
    """Internal representation of one system before merging."""
    name: str
    state_vars: "OrderedDict[str, FlattenedVariable]" = field(default_factory=OrderedDict)
    parameters: "OrderedDict[str, FlattenedVariable]" = field(default_factory=OrderedDict)
    observed: "OrderedDict[str, FlattenedVariable]" = field(default_factory=OrderedDict)
    equations: List[FlattenedEquation] = field(default_factory=list)


def _collect_model(name: str, model: Model, prefix: Optional[str] = None) -> _ComponentSystem:
    """Collect a Model (recursively, including subsystems) into a _ComponentSystem."""
    full_prefix = prefix or name
    component = _ComponentSystem(name=full_prefix)

    for var_name, var in model.variables.items():
        namespaced = f"{full_prefix}.{var_name}"
        flat_var = FlattenedVariable(
            name=namespaced,
            type=var.type,
            units=var.units,
            default=var.default,
            description=var.description,
            source_system=full_prefix,
        )
        if var.type == "state":
            component.state_vars[namespaced] = flat_var
        elif var.type == "parameter":
            component.parameters[namespaced] = flat_var
        elif var.type == "observed":
            component.observed[namespaced] = flat_var

    # _var is a placeholder used by operator_compose; never namespace it.
    leave_alone = {"t", "_var"}
    for eq in model.equations:
        ns_lhs = _namespace_expr(eq.lhs, full_prefix, leave_alone=leave_alone)
        ns_rhs = _namespace_expr(eq.rhs, full_prefix, leave_alone=leave_alone)
        component.equations.append(FlattenedEquation(
            lhs=ns_lhs, rhs=ns_rhs, source_system=full_prefix,
        ))

    for sub_name, sub_model in model.subsystems.items():
        sub_prefix = f"{full_prefix}.{sub_name}"
        sub_component = _collect_model(sub_name, sub_model, sub_prefix)
        component.state_vars.update(sub_component.state_vars)
        component.parameters.update(sub_component.parameters)
        component.observed.update(sub_component.observed)
        component.equations.extend(sub_component.equations)

    return component


def _collect_reaction_system(name: str, rs: ReactionSystem, prefix: Optional[str] = None) -> _ComponentSystem:
    """Collect a ReactionSystem (lowered through derive_odes) into a _ComponentSystem.

    Species become state variables; reaction parameters become parameters;
    rate laws are converted to dN_i/dt equations via mass-action kinetics.
    Constraint equations are passed through.
    """
    full_prefix = prefix or name
    component = _ComponentSystem(name=full_prefix)

    has_reactions = bool(rs.reactions)
    derived: Optional[Model] = None
    if has_reactions:
        derived = derive_odes(rs)

    leave_alone = {"t", "_var"}

    for species in rs.species:
        namespaced = f"{full_prefix}.{species.name}"
        component.state_vars[namespaced] = FlattenedVariable(
            name=namespaced,
            type="species",
            units=species.units,
            default=species.default,
            description=species.description,
            source_system=full_prefix,
        )

    for param in rs.parameters:
        namespaced = f"{full_prefix}.{param.name}"
        default_value: Any = None
        if isinstance(param.value, (int, float)):
            default_value = param.value
        component.parameters[namespaced] = FlattenedVariable(
            name=namespaced,
            type="parameter",
            units=param.units,
            default=default_value,
            description=param.description,
            source_system=full_prefix,
        )

    if derived is not None:
        for eq in derived.equations:
            ns_lhs = _namespace_expr(eq.lhs, full_prefix, leave_alone=leave_alone)
            ns_rhs = _namespace_expr(eq.rhs, full_prefix, leave_alone=leave_alone)
            component.equations.append(FlattenedEquation(
                lhs=ns_lhs, rhs=ns_rhs, source_system=full_prefix,
            ))

    for eq in rs.constraint_equations:
        ns_lhs = _namespace_expr(eq.lhs, full_prefix, leave_alone=leave_alone)
        ns_rhs = _namespace_expr(eq.rhs, full_prefix, leave_alone=leave_alone)
        component.equations.append(FlattenedEquation(
            lhs=ns_lhs, rhs=ns_rhs, source_system=full_prefix,
        ))

    for sub_name, sub_rs in rs.subsystems.items():
        sub_prefix = f"{full_prefix}.{sub_name}"
        sub_component = _collect_reaction_system(sub_name, sub_rs, sub_prefix)
        component.state_vars.update(sub_component.state_vars)
        component.parameters.update(sub_component.parameters)
        component.observed.update(sub_component.observed)
        component.equations.extend(sub_component.equations)

    return component


# ============================================================================
# Coupling resolution
# ============================================================================


def _build_translate_map(entry: OperatorComposeCoupling) -> Dict[str, Tuple[str, float]]:
    """Normalize the operator_compose ``translate`` dict.

    Each entry maps a scoped reference in system A to a scoped reference in
    system B (or vice versa), optionally with a conversion factor.
    """
    out: Dict[str, Tuple[str, float]] = {}
    if not entry.translate:
        return out
    for k, v in entry.translate.items():
        if isinstance(v, dict):
            target = v.get("to") or v.get("target") or v.get("var")
            factor = float(v.get("factor", 1.0))
            if target:
                out[k] = (target, factor)
        elif isinstance(v, str):
            out[k] = (v, 1.0)
    return out


def _apply_operator_compose(
    components: "OrderedDict[str, _ComponentSystem]",
    entry: OperatorComposeCoupling,
) -> None:
    """Merge B's equations into A by matching dependent variables.

    Per spec §4.7.1: for each B equation with LHS ``D(x, t)``, find A's
    equation with LHS ``D(x, t)`` (translation-aware) and sum their RHS into
    a single equation. Unmatched B equations are appended unchanged.
    """
    if not entry.systems or len(entry.systems) < 2:
        return
    a_name, b_name = entry.systems[0], entry.systems[1]
    if a_name not in components or b_name not in components:
        return
    a = components[a_name]
    b = components[b_name]

    translate = _build_translate_map(entry)

    # Index A's equations by namespaced dependent variable.
    a_index: Dict[str, int] = {}
    for i, eq in enumerate(a.equations):
        dep = _lhs_dependent_var(eq.lhs)
        if dep is not None:
            a_index[dep] = i

    surviving_b: List[FlattenedEquation] = []

    for b_eq in b.equations:
        b_dep = _lhs_dependent_var(b_eq.lhs)
        if b_dep is None:
            surviving_b.append(b_eq)
            continue

        # Determine the A target for this dependent variable.
        target_dep = b_dep
        factor = 1.0
        if b_dep in translate:
            t, factor = translate[b_dep]
            target_dep = t
        else:
            # Try mapping bare names from B back to A's equivalent.
            short = b_dep.split(".", 1)[1] if "." in b_dep else b_dep
            for ad in a_index:
                if ad.endswith("." + short):
                    target_dep = ad
                    break

        if target_dep in a_index:
            i = a_index[target_dep]
            a_eq = a.equations[i]
            substituted_rhs = substitute(b_eq.rhs, {b_dep: target_dep})
            if factor != 1.0:
                substituted_rhs = ExprNode(op="*", args=[factor, substituted_rhs])
            new_rhs = _add_exprs(a_eq.rhs, substituted_rhs)
            a.equations[i] = FlattenedEquation(
                lhs=a_eq.lhs,
                rhs=new_rhs,
                source_system=a_eq.source_system,
            )
        else:
            surviving_b.append(b_eq)

    b.equations = surviving_b


def _add_exprs(left: Expr, right: Expr) -> Expr:
    """Sum two expressions, normalizing trivial cases."""
    if _is_number(left) and left == 0:
        return right
    if _is_number(right) and right == 0:
        return left
    return ExprNode(op="+", args=[left, right])


def _multiply_exprs(left: Expr, right: Expr) -> Expr:
    if _is_number(left) and left == 1:
        return right
    if _is_number(right) and right == 1:
        return left
    if (_is_number(left) and left == 0) or (_is_number(right) and right == 0):
        return 0
    return ExprNode(op="*", args=[left, right])


def _apply_couple(
    components: "OrderedDict[str, _ComponentSystem]",
    entry: CouplingCouple,
) -> None:
    """Resolve a ``couple`` connector by injecting source/sink terms.

    Each connector equation maps ``from_var`` (already a scoped reference like
    ``A.x``) to ``to_var`` with one of three transforms (``additive``,
    ``multiplicative``, ``replacement``). The expression is appended to (or
    multiplied with, or replaces) the target variable's equation.
    """
    if not entry.connector or not entry.connector.equations:
        return

    # Build a global index of equations for fast LHS lookup.
    eq_index: Dict[str, Tuple[str, int]] = {}
    for sys_name, comp in components.items():
        for i, eq in enumerate(comp.equations):
            dep = _lhs_dependent_var(eq.lhs)
            if dep is not None:
                eq_index[dep] = (sys_name, i)

    for ceq in entry.connector.equations:
        target = ceq.to_var
        if not target:
            continue
        if target not in eq_index:
            continue
        sys_name, i = eq_index[target]
        comp = components[sys_name]
        existing = comp.equations[i]
        expression: Expr = ceq.expression if ceq.expression is not None else ceq.from_var

        if ceq.transform == "additive":
            new_rhs = _add_exprs(existing.rhs, expression)
        elif ceq.transform == "multiplicative":
            new_rhs = _multiply_exprs(existing.rhs, expression)
        elif ceq.transform == "replacement":
            new_rhs = expression
        else:
            new_rhs = _add_exprs(existing.rhs, expression)

        comp.equations[i] = FlattenedEquation(
            lhs=existing.lhs,
            rhs=new_rhs,
            source_system=existing.source_system,
        )


def _apply_variable_map(
    components: "OrderedDict[str, _ComponentSystem]",
    entry: VariableMapCoupling,
) -> None:
    """Substitute the target parameter with the source variable.

    For ``param_to_var``, the target parameter is removed from the parameter
    list (it becomes a shared variable). For other transforms (``identity``,
    ``additive``, ``multiplicative``, ``conversion_factor``) we still substitute
    so the equation set references the canonical name.
    """
    if not entry.from_var or not entry.to_var:
        return
    factor = entry.factor or 1.0
    src: Expr = entry.from_var
    if factor != 1.0:
        src = ExprNode(op="*", args=[factor, entry.from_var])

    bindings = {entry.to_var: src}
    for comp in components.values():
        new_eqs: List[FlattenedEquation] = []
        for eq in comp.equations:
            new_eqs.append(FlattenedEquation(
                lhs=substitute(eq.lhs, bindings),
                rhs=substitute(eq.rhs, bindings),
                source_system=eq.source_system,
            ))
        comp.equations = new_eqs

    transform = (entry.transform or "").lower()
    promoted = transform in ("param_to_var", "conversion_factor", "")
    if promoted:
        for comp in components.values():
            comp.parameters.pop(entry.to_var, None)


# ============================================================================
# Event namespacing
# ============================================================================


def _namespace_event_affects(
    affects: List, system_var_names: Dict[str, str]
) -> List:
    """Rewrite AffectEquation.lhs/rhs to dot-namespaced form when possible."""
    out = []
    for affect in affects:
        if isinstance(affect, AffectEquation):
            ns_lhs = system_var_names.get(affect.lhs, affect.lhs)
            ns_rhs = affect.rhs
            if isinstance(ns_rhs, str):
                ns_rhs = system_var_names.get(ns_rhs, ns_rhs)
            elif isinstance(ns_rhs, ExprNode):
                ns_rhs = _namespace_event_expr(ns_rhs, system_var_names)
            out.append(AffectEquation(lhs=ns_lhs, rhs=ns_rhs))
        else:
            out.append(affect)
    return out


def _namespace_event_expr(expr: Expr, system_var_names: Dict[str, str]) -> Expr:
    if _is_number(expr) or expr is None:
        return expr
    if isinstance(expr, str):
        return system_var_names.get(expr, expr)
    if isinstance(expr, ExprNode):
        new_args = [_namespace_event_expr(a, system_var_names) for a in expr.args]
        return ExprNode(op=expr.op, args=new_args, wrt=expr.wrt, dim=expr.dim)
    return expr


# ============================================================================
# Public API
# ============================================================================


def flatten(esm_file: EsmFile) -> FlattenedSystem:
    """Flatten a coupled multi-system EsmFile per spec §4.7.5.

    The result is the canonical intermediate representation: dot-namespaced
    variables, equations as Expr trees, coupling rules resolved into the
    equation set, and metadata recording what happened.

    Raises
    ------
    ValueError
        If the file has no models, no reaction systems, and nothing to flatten.
    ConflictingDerivativeError
        If two source systems define non-additive equations for the same
        dependent variable.
    """
    if not esm_file.models and not esm_file.reaction_systems:
        raise ValueError(
            "Cannot flatten an EsmFile with no models or reaction systems"
        )

    # Step 1: collect every component system into a per-system bag of variables
    # and (already-namespaced) equations.
    components: "OrderedDict[str, _ComponentSystem]" = OrderedDict()
    source_systems: List[str] = []
    for name, model in esm_file.models.items():
        components[name] = _collect_model(name, model)
        source_systems.append(name)
    for name, rs in esm_file.reaction_systems.items():
        components[name] = _collect_reaction_system(name, rs)
        source_systems.append(name)

    metadata = FlattenMetadata(source_systems=list(source_systems))

    # Step 2: walk coupling entries in array order. operator_compose runs first
    # so its placeholder-expansion / merge happens before any variable_map
    # substitution rewrites the dependent variable names out from under us.
    operator_compose_entries: List[OperatorComposeCoupling] = []
    couple_entries: List[CouplingCouple] = []
    var_map_entries: List[VariableMapCoupling] = []
    for entry in esm_file.coupling:
        if isinstance(entry, OperatorComposeCoupling):
            operator_compose_entries.append(entry)
        elif isinstance(entry, CouplingCouple):
            couple_entries.append(entry)
        elif isinstance(entry, VariableMapCoupling):
            var_map_entries.append(entry)
        elif isinstance(entry, OperatorApplyCoupling):
            metadata.operator_applies.append(entry.operator or "?")
        elif isinstance(entry, CallbackCoupling):
            metadata.callbacks.append(entry.callback_id or "?")
        metadata.coupling_rules.append(_describe_coupling(entry))

    for oc in operator_compose_entries:
        _expand_operator_compose_placeholders(components, oc)
        _apply_operator_compose(components, oc)

    for cp in couple_entries:
        _apply_couple(components, cp)

    for vm in var_map_entries:
        _apply_variable_map(components, vm)

    # Step 3: assemble the final FlattenedSystem from the per-component pieces.
    flat = FlattenedSystem(metadata=metadata)
    seen_lhs: Dict[str, FlattenedEquation] = {}
    for comp in components.values():
        for name, var in comp.state_vars.items():
            flat.state_variables[name] = var
        for name, var in comp.parameters.items():
            flat.parameters[name] = var
        for name, var in comp.observed.items():
            flat.observed_variables[name] = var
        for eq in comp.equations:
            dep = _lhs_dependent_var(eq.lhs)
            if dep is not None:
                if dep in seen_lhs:
                    existing = seen_lhs[dep]
                    if _expr_to_string(existing.rhs) != _expr_to_string(eq.rhs):
                        raise ConflictingDerivativeError(
                            f"Two systems define non-additive equations for "
                            f"variable {dep!r}: "
                            f"{existing.source_system} vs {eq.source_system}"
                        )
                    continue
                seen_lhs[dep] = eq
            flat.equations.append(eq)

    # Step 4: events. We just collect them — namespacing per-system is hard
    # because the file's events list isn't tagged with a source system. We
    # rewrite affect-equation LHS names where they unambiguously match a
    # known state variable.
    var_to_namespaced: Dict[str, str] = {}
    for name in list(flat.state_variables) + list(flat.parameters):
        bare = name.rsplit(".", 1)[-1]
        var_to_namespaced.setdefault(bare, name)

    for event in esm_file.events:
        if isinstance(event, ContinuousEvent):
            new_conditions = [_namespace_event_expr(c, var_to_namespaced) for c in event.conditions]
            new_affects = _namespace_event_affects(event.affects, var_to_namespaced)
            new_affect_neg = (
                _namespace_event_affects(event.affect_neg, var_to_namespaced)
                if event.affect_neg is not None else None
            )
            flat.continuous_events.append(ContinuousEvent(
                name=event.name,
                conditions=new_conditions,
                affects=new_affects,
                affect_neg=new_affect_neg,
                root_find=event.root_find,
                reinitialize=event.reinitialize,
                priority=event.priority,
                description=event.description,
            ))
        elif isinstance(event, DiscreteEvent):
            new_affects = _namespace_event_affects(event.affects, var_to_namespaced)
            flat.discrete_events.append(DiscreteEvent(
                name=event.name,
                trigger=event.trigger,
                affects=new_affects,
                priority=event.priority,
            ))

    # Step 5: domain pass-through. The Python tier does not currently apply
    # dimension-promotion rules from §4.7.6 — only the spatial-rejection check
    # in simulate() distinguishes ODE-only flattened systems from PDE inputs.
    if esm_file.domains:
        # Use the first domain (the spec doesn't yet say how to merge multiple).
        flat.domain = next(iter(esm_file.domains.values()))

    # Step 6: derive independent variables from the equation set. Time is
    # always present; spatial dimensions are added when grad/div/laplacian
    # operators reference them.
    independent: List[str] = ["t"]
    spatial_dims: Set[str] = set()
    for eq in flat.equations:
        spatial_dims.update(_spatial_dims_in_expr(eq.lhs))
        spatial_dims.update(_spatial_dims_in_expr(eq.rhs))
    for dim in sorted(spatial_dims):
        independent.append(dim)
    flat.independent_variables = independent

    return flat


def _expand_operator_compose_placeholders(
    components: "OrderedDict[str, _ComponentSystem]",
    entry: OperatorComposeCoupling,
) -> None:
    """Expand ``_var`` placeholders in B's equations against A's state variables.

    Spec §4.7.1 placeholder expansion: an equation like ``D(_var, t) =
    -u·grad(_var, x)`` in system B is cloned once per state variable in system
    A, with ``_var`` substituted for the actual (namespaced) variable name.
    """
    if not entry.systems or len(entry.systems) < 2:
        return
    a_name, b_name = entry.systems[0], entry.systems[1]
    if a_name not in components or b_name not in components:
        return
    a = components[a_name]
    b = components[b_name]

    a_state_names = list(a.state_vars.keys())
    if not a_state_names:
        return

    new_equations: List[FlattenedEquation] = []
    for eq in b.equations:
        if has_var_placeholder(eq.lhs) or has_var_placeholder(eq.rhs):
            for var_name in a_state_names:
                bindings = {"_var": var_name}
                new_equations.append(FlattenedEquation(
                    lhs=substitute(eq.lhs, bindings),
                    rhs=substitute(eq.rhs, bindings),
                    source_system=eq.source_system,
                ))
        else:
            new_equations.append(eq)
    b.equations = new_equations
