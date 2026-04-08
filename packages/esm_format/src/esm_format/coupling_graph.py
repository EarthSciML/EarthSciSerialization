"""
Minimal coupling graph functionality for ESM Format.
This provides only the essential coupling functionality required by the core modules.
"""

from typing import Dict, List, Any, Optional, Set, Union, Tuple
from dataclasses import dataclass
from .esm_types import EsmFile, Model, ReactionSystem, CouplingEntry, ContinuousEvent, DiscreteEvent


@dataclass
class CouplingEdge:
    """Represents a labeled edge in the coupling graph."""
    from_node: str
    to_node: str
    label: str
    coupling_type: str
    metadata: Dict[str, Any]

    def as_tuple(self) -> Tuple[str, str]:
        """Return edge as simple tuple for backward compatibility."""
        return (self.from_node, self.to_node)


@dataclass
class CouplingGraph:
    """Coupling graph with labeled edges and cross-system event support."""
    nodes: List[str]
    labeled_edges: List[CouplingEdge]

    def get_nodes(self) -> List[str]:
        return self.nodes

    def get_edges(self) -> List[Tuple[str, str]]:
        """Return edges as simple tuples for backward compatibility."""
        return [edge.as_tuple() for edge in self.labeled_edges]

    def get_labeled_edges(self) -> List[CouplingEdge]:
        """Return edges with full label information."""
        return self.labeled_edges

    def get_edges_by_type(self, coupling_type: str) -> List[CouplingEdge]:
        """Return edges filtered by coupling type."""
        return [edge for edge in self.labeled_edges if edge.coupling_type == coupling_type]

    def get_cross_system_edges(self) -> List[CouplingEdge]:
        """Return edges that represent cross-system interactions."""
        return [edge for edge in self.labeled_edges
                if edge.coupling_type in ['variable_map', 'operator_compose', 'couple2', 'event']]


def construct_coupling_graph(esm_file: EsmFile) -> CouplingGraph:
    """Construct a coupling graph with labeled edges from an ESM file."""
    nodes = []
    labeled_edges = []

    # Add model nodes
    if esm_file.models:
        nodes.extend(esm_file.models.keys())

    # Add reaction system nodes
    if esm_file.reaction_systems:
        nodes.extend(esm_file.reaction_systems.keys())

    # Add data loader nodes
    if esm_file.data_loaders:
        nodes.extend([loader.name for loader in esm_file.data_loaders if hasattr(loader, 'name')])
        # Fallback if loaders don't have names
        for i, loader in enumerate(esm_file.data_loaders):
            if not hasattr(loader, 'name'):
                nodes.append(f"loader_{i}")

    # Add operator nodes
    if esm_file.operators:
        nodes.extend([op.name for op in esm_file.operators if hasattr(op, 'name')])
        # Fallback if operators don't have names
        for i, op in enumerate(esm_file.operators):
            if not hasattr(op, 'name'):
                nodes.append(f"operator_{i}")

    # Add labeled edges from coupling entries
    if esm_file.coupling:
        for entry in esm_file.coupling:
            coupling_type_str = entry.coupling_type.value if hasattr(entry.coupling_type, 'value') else str(entry.coupling_type)

            if hasattr(entry, 'systems') and entry.systems:
                # operator_compose, couple2
                if len(entry.systems) >= 2:
                    for i in range(len(entry.systems) - 1):
                        from_system = entry.systems[i]
                        to_system = entry.systems[i + 1]
                        label = f"{coupling_type_str}: {from_system} → {to_system}"
                        metadata = {'description': entry.description} if entry.description else {}

                        # Add specific metadata based on coupling type
                        if hasattr(entry, 'translate') and entry.translate:
                            metadata['translate'] = entry.translate
                        if hasattr(entry, 'connector') and entry.connector:
                            metadata['connector'] = True
                        if hasattr(entry, 'coupletype_pair') and entry.coupletype_pair:
                            metadata['coupletype_pair'] = entry.coupletype_pair

                        labeled_edges.append(CouplingEdge(
                            from_node=from_system,
                            to_node=to_system,
                            label=label,
                            coupling_type=coupling_type_str,
                            metadata=metadata
                        ))

            elif hasattr(entry, 'from_var') and hasattr(entry, 'to_var'):
                # variable_map
                from_parts = entry.from_var.split('.')
                to_parts = entry.to_var.split('.')
                if len(from_parts) > 1 and len(to_parts) > 1:
                    from_system = from_parts[0]
                    to_system = to_parts[0]
                    from_var = '.'.join(from_parts[1:])
                    to_var = '.'.join(to_parts[1:])

                    label = f"{coupling_type_str}: {entry.from_var} → {entry.to_var}"
                    metadata = {
                        'from_var': from_var,
                        'to_var': to_var,
                        'transform': entry.transform if hasattr(entry, 'transform') and entry.transform else 'identity',
                        'factor': entry.factor if hasattr(entry, 'factor') and entry.factor else 1.0
                    }
                    if entry.description:
                        metadata['description'] = entry.description

                    labeled_edges.append(CouplingEdge(
                        from_node=from_system,
                        to_node=to_system,
                        label=label,
                        coupling_type=coupling_type_str,
                        metadata=metadata
                    ))

            elif hasattr(entry, 'operator') and entry.operator:
                # operator_apply - adds an edge from operator to relevant systems
                operator_name = entry.operator
                label = f"{coupling_type_str}: apply {operator_name}"
                metadata = {'operator': operator_name}
                if entry.description:
                    metadata['description'] = entry.description

                # For operator_apply, we create edges from the operator to all affected systems
                # This is a simplified approach; more sophisticated logic could determine specific targets
                for node in nodes:
                    if node != operator_name and not node.startswith('operator_') and not node.startswith('loader_'):
                        labeled_edges.append(CouplingEdge(
                            from_node=operator_name,
                            to_node=node,
                            label=label,
                            coupling_type=coupling_type_str,
                            metadata=metadata
                        ))

    # Add edges for cross-system events
    if esm_file.events:
        labeled_edges.extend(_extract_cross_system_event_edges(esm_file.events, nodes))

    return CouplingGraph(nodes=nodes, labeled_edges=labeled_edges)


def _extract_cross_system_event_edges(events: List[Union[ContinuousEvent, DiscreteEvent]],
                                     nodes: List[str]) -> List[CouplingEdge]:
    """Extract edges representing cross-system events."""
    edges = []

    for event in events:
        # Check if the event affects variables from multiple systems
        affected_systems = set()

        # For continuous events (note: field is 'affects', not 'affect')
        if hasattr(event, 'affects') and event.affects:
            for affect_eq in event.affects:
                if hasattr(affect_eq, 'lhs'):
                    var_parts = affect_eq.lhs.split('.')
                    if len(var_parts) > 1:
                        system_name = var_parts[0]
                        if system_name in nodes:
                            affected_systems.add(system_name)

        # For discrete events
        if hasattr(event, 'discrete_affects') and event.discrete_affects:
            for affect_eq in event.discrete_affects:
                if hasattr(affect_eq, 'lhs'):
                    var_parts = affect_eq.lhs.split('.')
                    if len(var_parts) > 1:
                        system_name = var_parts[0]
                        if system_name in nodes:
                            affected_systems.add(system_name)

        # Check condition variables for additional systems involved (note: field is 'conditions', not 'condition')
        if hasattr(event, 'conditions') and event.conditions:
            for condition in event.conditions:
                condition_systems = _extract_systems_from_expression(condition, nodes)
                affected_systems.update(condition_systems)

        # If event affects multiple systems, create cross-system edges
        if len(affected_systems) > 1:
            affected_list = list(affected_systems)
            event_name = getattr(event, 'name', f'event_{hash(str(event)) % 10000}')

            for i in range(len(affected_list)):
                for j in range(i + 1, len(affected_list)):
                    label = f"event: {event_name} ({affected_list[i]} ↔ {affected_list[j]})"
                    metadata = {
                        'event_name': event_name,
                        'event_type': 'continuous' if hasattr(event, 'affects') else 'discrete',
                        'cross_system': True
                    }

                    # Bi-directional edges for cross-system events
                    edges.append(CouplingEdge(
                        from_node=affected_list[i],
                        to_node=affected_list[j],
                        label=label,
                        coupling_type='event',
                        metadata=metadata
                    ))
                    edges.append(CouplingEdge(
                        from_node=affected_list[j],
                        to_node=affected_list[i],
                        label=label,
                        coupling_type='event',
                        metadata=metadata
                    ))

    return edges


def _extract_systems_from_expression(expr, nodes: List[str]) -> Set[str]:
    """Extract system names from an expression tree."""
    systems = set()

    if isinstance(expr, str):
        # Simple variable reference
        parts = expr.split('.')
        if len(parts) > 1 and parts[0] in nodes:
            systems.add(parts[0])
    elif hasattr(expr, 'op') and hasattr(expr, 'args'):
        # Expression node - recursively check arguments
        for arg in expr.args:
            systems.update(_extract_systems_from_expression(arg, nodes))
    elif hasattr(expr, '__iter__') and not isinstance(expr, str):
        # List or tuple of expressions
        for item in expr:
            systems.update(_extract_systems_from_expression(item, nodes))

    return systems


class ScopedReferenceResolver:
    """Enhanced scoped reference resolver with cross-system validation."""

    def __init__(self, esm_file: EsmFile):
        self.esm_file = esm_file
        self._system_cache = self._build_system_cache()
        self._variable_cache = self._build_variable_cache()

    def _build_system_cache(self) -> Dict[str, str]:
        """Build cache of system names to their types for fast lookup."""
        cache = {}
        if self.esm_file.models:
            for name in self.esm_file.models:
                cache[name] = 'model'
        if self.esm_file.reaction_systems:
            for name in self.esm_file.reaction_systems:
                cache[name] = 'reaction_system'
        if self.esm_file.data_loaders:
            for i, loader in enumerate(self.esm_file.data_loaders):
                name = getattr(loader, 'name', f'loader_{i}')
                cache[name] = 'data_loader'
        if self.esm_file.operators:
            for i, op in enumerate(self.esm_file.operators):
                name = getattr(op, 'name', f'operator_{i}')
                cache[name] = 'operator'
        return cache

    def _build_variable_cache(self) -> Dict[str, Set[str]]:
        """Build cache of variables available in each system."""
        cache = {}

        # Model variables
        if self.esm_file.models:
            for name, model in self.esm_file.models.items():
                variables = set()
                if hasattr(model, 'variables') and model.variables:
                    variables.update(model.variables.keys())
                cache[name] = variables

        # Reaction system species and parameters
        if self.esm_file.reaction_systems:
            for name, rs in self.esm_file.reaction_systems.items():
                variables = set()
                if hasattr(rs, 'species') and rs.species:
                    variables.update([s.name for s in rs.species if hasattr(s, 'name')])
                if hasattr(rs, 'parameters') and rs.parameters:
                    variables.update([p.name for p in rs.parameters if hasattr(p, 'name')])
                cache[name] = variables

        # Data loader provides
        if self.esm_file.data_loaders:
            for i, loader in enumerate(self.esm_file.data_loaders):
                name = getattr(loader, 'name', f'loader_{i}')
                variables = set()
                if hasattr(loader, 'provides') and loader.provides:
                    variables.update(loader.provides.keys())
                cache[name] = variables

        return cache

    def resolve(self, reference: str) -> Optional[str]:
        """Resolve a scoped reference to its system."""
        parts = reference.split('.')
        if len(parts) > 1:
            system_name = parts[0]
            return system_name if system_name in self._system_cache else None
        return None

    def get_system_type(self, system_name: str) -> Optional[str]:
        """Get the type of a system (model, reaction_system, data_loader, operator)."""
        return self._system_cache.get(system_name)

    def get_variable_name(self, reference: str) -> str:
        """Get the variable name from a scoped reference."""
        parts = reference.split('.')
        return parts[-1]  # Last part is always the variable name

    def get_full_path(self, reference: str) -> List[str]:
        """Get the full path components of a scoped reference."""
        return reference.split('.')

    def validate_reference(self, reference: str) -> bool:
        """Validate that a scoped reference points to an existing variable."""
        parts = reference.split('.')
        if len(parts) < 2:
            return False

        system_name = parts[0]
        if system_name not in self._system_cache:
            return False

        # For nested references (e.g., model.subsystem.var), we only check the first level
        variable_name = parts[-1]
        system_variables = self._variable_cache.get(system_name, set())
        return variable_name in system_variables if system_variables else True  # Allow unknown variables for now

    def get_cross_system_references(self, expr) -> List[Tuple[str, str]]:
        """Extract all cross-system references from an expression.

        Returns list of tuples (system_name, variable_path).
        """
        references = []
        self._collect_references_recursive(expr, references)

        # Filter to only cross-system references (those with dots)
        cross_refs = []
        for ref_str in references:
            parts = ref_str.split('.')
            if len(parts) > 1 and parts[0] in self._system_cache:
                cross_refs.append((parts[0], '.'.join(parts[1:])))

        return cross_refs

    def _collect_references_recursive(self, expr, references: List[str]):
        """Recursively collect variable references from expression."""
        if isinstance(expr, str):
            # Check if it looks like a scoped reference
            if '.' in expr:
                references.append(expr)
        elif hasattr(expr, 'op') and hasattr(expr, 'args'):
            # Expression node - recursively check arguments
            for arg in expr.args:
                self._collect_references_recursive(arg, references)
        elif hasattr(expr, '__iter__') and not isinstance(expr, str):
            # List or tuple of expressions
            for item in expr:
                self._collect_references_recursive(item, references)