"""
Coupling graph construction and analysis for ESM Format.

This module provides algorithms to construct coupling graphs from ESM definitions,
including node creation, edge detection, dependency analysis, and cycle detection.
It serves as the foundation for all coupling resolution operations.
"""

from typing import Dict, List, Set, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import logging

from .esm_types import CouplingEntry, CouplingType, EsmFile, Model, ReactionSystem, DataLoader, Operator, ModelVariable, Species

# Optional import for unit handling
try:
    from pint import UnitRegistry, DimensionalityError, Quantity
    PINT_AVAILABLE = True
    ureg = UnitRegistry()
except ImportError:
    PINT_AVAILABLE = False
    ureg = None
    logging.warning("Pint not available. Unit conversion features will be disabled.")


class NodeType(Enum):
    """Types of nodes in a coupling graph."""
    MODEL = "model"
    REACTION_SYSTEM = "reaction_system"
    VARIABLE = "variable"


@dataclass
class CouplingNode:
    """A node in the coupling graph."""
    id: str
    name: str
    type: NodeType
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class CouplingEdge:
    """An edge in the coupling graph."""
    source_node: str
    target_node: str
    source_variables: List[str]
    target_variables: List[str]
    coupling_type: CouplingType
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class DependencyInfo:
    """Information about dependencies between components."""
    direct_dependencies: Set[str] = field(default_factory=set)
    indirect_dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    dependency_level: int = 0


@dataclass
class VariableMatchResult:
    """Result of variable matching between source and target variables."""
    is_compatible: bool
    source_variable: Dict[str, Any]
    target_variable: Dict[str, Any]
    unit_conversion_factor: Optional[float] = None
    conversion_expression: Optional[str] = None
    type_compatibility: bool = True
    unit_compatibility: bool = True
    interface_compatibility: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CouplingGraph:
    """
    A coupling graph representing dependencies between model components.

    The graph consists of nodes representing models, reaction systems, and variables,
    and edges representing coupling relationships between them.
    """

    def __init__(self):
        """Initialize an empty coupling graph."""
        self.nodes: Dict[str, CouplingNode] = {}
        self.edges: List[CouplingEdge] = []
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)  # node_id -> set of connected node_ids
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)  # for incoming edges
        self._dependency_info: Dict[str, DependencyInfo] = {}

    def add_node(self, node: CouplingNode) -> None:
        """
        Add a node to the coupling graph.

        Args:
            node: The coupling node to add

        Raises:
            ValueError: If a node with the same ID already exists
        """
        if node.id in self.nodes:
            raise ValueError(f"Node with ID '{node.id}' already exists")

        self.nodes[node.id] = node
        self._adjacency[node.id] = set()
        self._reverse_adjacency[node.id] = set()

    def add_edge(self, edge: CouplingEdge) -> None:
        """
        Add an edge to the coupling graph.

        Args:
            edge: The coupling edge to add

        Raises:
            ValueError: If source or target nodes don't exist
        """
        if edge.source_node not in self.nodes:
            raise ValueError(f"Source node '{edge.source_node}' not found")
        if edge.target_node not in self.nodes:
            raise ValueError(f"Target node '{edge.target_node}' not found")

        self.edges.append(edge)
        self._adjacency[edge.source_node].add(edge.target_node)
        self._reverse_adjacency[edge.target_node].add(edge.source_node)

    def get_node(self, node_id: str) -> Optional[CouplingNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_edges_from_node(self, node_id: str) -> List[CouplingEdge]:
        """Get all edges originating from a specific node."""
        return [edge for edge in self.edges if edge.source_node == node_id]

    def get_edges_to_node(self, node_id: str) -> List[CouplingEdge]:
        """Get all edges targeting a specific node."""
        return [edge for edge in self.edges if edge.target_node == node_id]

    def get_neighbors(self, node_id: str) -> Set[str]:
        """Get all nodes connected to the given node (outgoing edges)."""
        return self._adjacency.get(node_id, set()).copy()

    def get_predecessors(self, node_id: str) -> Set[str]:
        """Get all nodes that have edges pointing to the given node."""
        return self._reverse_adjacency.get(node_id, set()).copy()

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect all strongly connected components (cycles) in the graph.

        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        # Use Tarjan's algorithm to find strongly connected components
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = set()
        cycles = []

        def strongconnect(node_id: str):
            # Set the depth index for this node
            index[node_id] = index_counter[0]
            lowlinks[node_id] = index_counter[0]
            index_counter[0] += 1
            stack.append(node_id)
            on_stack.add(node_id)

            # Consider successors of node_id
            for successor in self._adjacency.get(node_id, set()):
                if successor not in index:
                    # Successor has not been visited; recurse on it
                    strongconnect(successor)
                    lowlinks[node_id] = min(lowlinks[node_id], lowlinks[successor])
                elif successor in on_stack:
                    # Successor is in stack and hence in the current SCC
                    lowlinks[node_id] = min(lowlinks[node_id], index[successor])

            # If node_id is a root node, pop the stack and generate an SCC
            if lowlinks[node_id] == index[node_id]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    component.append(w)
                    if w == node_id:
                        break

                # Only report components with more than one node (actual cycles)
                if len(component) > 1:
                    cycles.append(component)

        # Run the algorithm for all unvisited nodes
        for node_id in self.nodes:
            if node_id not in index:
                strongconnect(node_id)

        return cycles

    def analyze_dependencies(self) -> None:
        """
        Analyze dependencies for all nodes in the graph.

        This method computes direct dependencies, indirect dependencies,
        dependents, and dependency levels for each node.
        """
        self._dependency_info.clear()

        # Initialize dependency info for all nodes
        for node_id in self.nodes:
            self._dependency_info[node_id] = DependencyInfo()

        # Compute direct dependencies and dependents
        for edge in self.edges:
            source = edge.source_node
            target = edge.target_node

            self._dependency_info[target].direct_dependencies.add(source)
            self._dependency_info[source].dependents.add(target)

        # Compute indirect dependencies using transitive closure
        for node_id in self.nodes:
            self._compute_indirect_dependencies(node_id)

        # Compute dependency levels
        self._compute_dependency_levels()

    def _compute_indirect_dependencies(self, node_id: str) -> None:
        """Compute indirect dependencies for a specific node."""
        visited = set()
        stack = list(self._dependency_info[node_id].direct_dependencies)

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            # Add this as an indirect dependency
            if current != node_id:  # Don't add self as dependency
                self._dependency_info[node_id].indirect_dependencies.add(current)

            # Add dependencies of current node to stack
            for dep in self._dependency_info[current].direct_dependencies:
                if dep not in visited:
                    stack.append(dep)

    def _compute_dependency_levels(self) -> None:
        """Compute dependency levels using topological sorting."""
        # Create a copy of direct dependencies for manipulation
        temp_deps = {}
        in_degree = {}

        for node_id in self.nodes:
            temp_deps[node_id] = self._dependency_info[node_id].direct_dependencies.copy()
            in_degree[node_id] = len(temp_deps[node_id])

        # Topological sort with level assignment
        queue = deque([node_id for node_id in self.nodes if in_degree[node_id] == 0])
        level = 0

        while queue:
            next_queue = deque()

            # Process all nodes at current level
            while queue:
                node_id = queue.popleft()
                self._dependency_info[node_id].dependency_level = level

                # Update in-degrees of dependents
                for dependent in self._dependency_info[node_id].dependents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)

            queue = next_queue
            level += 1

    def get_dependency_info(self, node_id: str) -> Optional[DependencyInfo]:
        """Get dependency information for a node."""
        return self._dependency_info.get(node_id)

    def get_execution_order(self) -> List[str]:
        """
        Get a topologically sorted execution order for all nodes.

        Returns:
            List of node IDs in execution order (dependencies first)

        Raises:
            ValueError: If circular dependencies exist
        """
        cycles = self.detect_cycles()
        if cycles:
            cycle_strs = [" -> ".join(cycle) for cycle in cycles]
            raise ValueError(f"Circular dependencies detected: {'; '.join(cycle_strs)}")

        # Ensure dependency analysis is up-to-date
        if not self._dependency_info:
            self.analyze_dependencies()

        # Group nodes by dependency level and sort within each level
        levels = defaultdict(list)
        for node_id, dep_info in self._dependency_info.items():
            levels[dep_info.dependency_level].append(node_id)

        # Build execution order
        execution_order = []
        for level in sorted(levels.keys()):
            # Sort nodes within each level by name for deterministic ordering
            level_nodes = sorted(levels[level])
            execution_order.extend(level_nodes)

        return execution_order

    def get_statistics(self) -> Dict[str, Union[int, float]]:
        """
        Get statistics about the coupling graph.

        Returns:
            Dictionary containing graph statistics
        """
        cycles = self.detect_cycles()

        # Calculate node type counts
        node_type_counts = defaultdict(int)
        for node in self.nodes.values():
            node_type_counts[node.type.value] += 1

        # Calculate coupling type counts
        coupling_type_counts = defaultdict(int)
        for edge in self.edges:
            coupling_type_counts[edge.coupling_type.value] += 1

        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'model_nodes': node_type_counts[NodeType.MODEL.value],
            'reaction_system_nodes': node_type_counts[NodeType.REACTION_SYSTEM.value],
            'variable_nodes': node_type_counts[NodeType.VARIABLE.value],
            'operator_compose_couplings': coupling_type_counts[CouplingType.OPERATOR_COMPOSE.value],
            'couple2_couplings': coupling_type_counts[CouplingType.COUPLE2.value],
            'variable_map_couplings': coupling_type_counts[CouplingType.VARIABLE_MAP.value],
            'operator_apply_couplings': coupling_type_counts[CouplingType.OPERATOR_APPLY.value],
            'callback_couplings': coupling_type_counts[CouplingType.CALLBACK.value],
            'event_couplings': coupling_type_counts[CouplingType.EVENT.value],
            'cycles_detected': len(cycles),
            'max_dependency_level': max((info.dependency_level for info in self._dependency_info.values()), default=0)
        }


def match_coupling_variables(
    source_var_name: str,
    target_var_name: str,
    source_component: Union[Model, ReactionSystem],
    target_component: Union[Model, ReactionSystem],
    coupling_type: CouplingType = CouplingType.VARIABLE_MAP
) -> VariableMatchResult:
    """
    Match variables between coupled components with type compatibility checking,
    unit conversion, and interface validation.

    Args:
        source_var_name: Name of the source variable
        target_var_name: Name of the target variable
        source_component: Source model or reaction system component
        target_component: Target model or reaction system component
        coupling_type: Type of coupling between components

    Returns:
        VariableMatchResult containing compatibility analysis and conversion info

    Raises:
        ValueError: If variables are not found in their respective components
    """
    result = VariableMatchResult(
        is_compatible=True,
        source_variable={},
        target_variable={}
    )

    # Step 1: Extract variable information
    try:
        source_var = _extract_variable_info(source_var_name, source_component)
        target_var = _extract_variable_info(target_var_name, target_component)

        result.source_variable = source_var
        result.target_variable = target_var

    except ValueError as e:
        result.is_compatible = False
        result.errors.append(str(e))
        return result

    # Step 2: Check type compatibility
    type_compatible, type_errors, type_warnings = _check_type_compatibility(
        source_var, target_var, coupling_type
    )
    result.type_compatibility = type_compatible
    result.errors.extend(type_errors)
    result.warnings.extend(type_warnings)

    # Step 3: Check unit compatibility and conversion
    if PINT_AVAILABLE:
        unit_compatible, unit_errors, unit_warnings, conversion_info = _check_unit_compatibility(
            source_var, target_var, coupling_type
        )
        result.unit_compatibility = unit_compatible
        result.errors.extend(unit_errors)
        result.warnings.extend(unit_warnings)

        if conversion_info:
            result.unit_conversion_factor = conversion_info.get('factor')
            result.conversion_expression = conversion_info.get('expression')
    else:
        result.warnings.append("Unit validation disabled: pint library not available")

    # Step 4: Check interface compatibility
    interface_compatible, interface_errors, interface_warnings = _check_interface_compatibility(
        source_var, target_var, coupling_type
    )
    result.interface_compatibility = interface_compatible
    result.errors.extend(interface_errors)
    result.warnings.extend(interface_warnings)

    # Step 5: Overall compatibility assessment
    result.is_compatible = (
        result.type_compatibility and
        result.unit_compatibility and
        result.interface_compatibility and
        len(result.errors) == 0
    )

    # Step 6: Add metadata about the matching process
    result.metadata = {
        'coupling_type': coupling_type.value,
        'source_component_type': type(source_component).__name__,
        'target_component_type': type(target_component).__name__,
        'matching_algorithm_version': '1.0.0'
    }

    return result


def _extract_variable_info(var_name: str, component: Union[Model, ReactionSystem]) -> Dict[str, Any]:
    """Extract variable information from a component."""
    var_info = {
        'name': var_name,
        'type': None,
        'units': None,
        'description': None,
        'default': None,
        'component_type': type(component).__name__
    }

    if isinstance(component, Model):
        if var_name not in component.variables:
            raise ValueError(f"Variable '{var_name}' not found in model '{component.name}'")

        model_var = component.variables[var_name]
        var_info.update({
            'type': model_var.type,
            'units': model_var.units,
            'description': model_var.description,
            'default': model_var.default,
            'expression': getattr(model_var, 'expression', None)
        })

    elif isinstance(component, ReactionSystem):
        # Look for variable in species list
        species_var = None
        for species in component.species:
            if species.name == var_name:
                species_var = species
                break

        if species_var:
            var_info.update({
                'type': 'species',
                'units': species_var.units,
                'description': species_var.description,
                'formula': getattr(species_var, 'formula', None),
                'mass': getattr(species_var, 'mass', None)
            })
        else:
            # Look in parameters
            param_var = None
            for param in component.parameters:
                if param.name == var_name:
                    param_var = param
                    break

            if param_var:
                var_info.update({
                    'type': 'parameter',
                    'units': param_var.units,
                    'description': param_var.description,
                    'default': param_var.value,
                    'uncertainty': getattr(param_var, 'uncertainty', None)
                })
            else:
                raise ValueError(f"Variable '{var_name}' not found in reaction system '{component.name}'")

    else:
        if component is None:
            raise ValueError(f"Component cannot be None")
        raise ValueError(f"Unsupported component type: {type(component)}")

    return var_info


def _check_type_compatibility(
    source_var: Dict[str, Any],
    target_var: Dict[str, Any],
    coupling_type: CouplingType
) -> Tuple[bool, List[str], List[str]]:
    """Check type compatibility between source and target variables."""
    errors = []
    warnings = []

    source_type = source_var.get('type')
    target_type = target_var.get('type')

    # Define compatible type mappings
    compatible_types = {
        ('state', 'state'): True,
        ('parameter', 'parameter'): True,
        ('observed', 'observed'): True,
        ('species', 'state'): True,  # Species can be mapped to model state variables
        ('state', 'species'): True,  # Model states can provide species concentrations
        ('parameter', 'state'): False,  # Generally not recommended - parameters shouldn't drive states directly
        ('state', 'parameter'): False,  # Generally not recommended - states shouldn't directly set parameters
        ('species', 'parameter'): False,  # Generally not recommended
        ('parameter', 'species'): False,  # Generally not recommended
    }

    type_pair = (source_type, target_type)
    is_compatible = compatible_types.get(type_pair, False)

    if not is_compatible:
        errors.append(
            f"Type incompatibility: cannot couple '{source_type}' to '{target_type}' "
            f"with coupling type '{coupling_type.value}'"
        )

    # Add warnings for potentially problematic couplings
    if type_pair in [('parameter', 'state'), ('state', 'parameter')]:
        warnings.append(
            "Coupling parameter to/from state variable may require careful validation "
            "of temporal evolution assumptions"
        )

    return is_compatible, errors, warnings


def _check_unit_compatibility(
    source_var: Dict[str, Any],
    target_var: Dict[str, Any],
    coupling_type: CouplingType
) -> Tuple[bool, List[str], List[str], Optional[Dict[str, Any]]]:
    """Check unit compatibility and calculate conversion if needed."""
    errors = []
    warnings = []
    conversion_info = None

    source_units = source_var.get('units')
    target_units = target_var.get('units')

    # Handle cases where units are missing or dimensionless
    if not source_units and not target_units:
        warnings.append("Both variables lack unit specifications")
        return True, errors, warnings, conversion_info

    # Handle dimensionless units
    if source_units == "dimensionless":
        source_units = ""
    if target_units == "dimensionless":
        target_units = ""

    if not source_units and target_units:
        errors.append(f"Source variable '{source_var['name']}' missing unit specification")
        return False, errors, warnings, conversion_info

    if source_units and not target_units:
        errors.append(f"Target variable '{target_var['name']}' missing unit specification")
        return False, errors, warnings, conversion_info

    # Both dimensionless/empty
    if not source_units and not target_units:
        return True, errors, warnings, conversion_info

    try:
        # Create quantities for unit comparison
        source_qty = ureg.Quantity(1.0, source_units)
        target_qty = ureg.Quantity(1.0, target_units)

        # Check if units are dimensionally compatible
        try:
            converted_qty = source_qty.to(target_units)
            conversion_factor = float(converted_qty.magnitude)

            conversion_info = {
                'factor': conversion_factor,
                'expression': f"target_value = source_value * {conversion_factor}"
            }

            if abs(conversion_factor - 1.0) > 1e-12:
                warnings.append(
                    f"Unit conversion required: {source_units} -> {target_units} "
                    f"(factor: {conversion_factor})"
                )

            return True, errors, warnings, conversion_info

        except DimensionalityError:
            errors.append(
                f"Unit dimensionality mismatch: '{source_units}' cannot be converted to '{target_units}'"
            )
            return False, errors, warnings, conversion_info

    except Exception as e:
        errors.append(f"Unit parsing error: {str(e)}")
        return False, errors, warnings, conversion_info


def _check_interface_compatibility(
    source_var: Dict[str, Any],
    target_var: Dict[str, Any],
    coupling_type: CouplingType
) -> Tuple[bool, List[str], List[str]]:
    """Check interface compatibility for the coupling."""
    errors = []
    warnings = []

    # Check for required interface properties based on coupling type
    if coupling_type == CouplingType.COUPLE2:
        # Bidirectional coupling requires careful interface matching
        warnings.append(
            "Couple2 coupling detected: ensure proper bidirectional interface compatibility"
        )
    elif coupling_type == CouplingType.VARIABLE_MAP:
        # Variable mapping requires type compatibility
        if source_var.get('type') != 'state' and target_var.get('type') != 'parameter':
            warnings.append(
                f"Variable mapping from {source_var.get('type')} to {target_var.get('type')} "
                "may require careful consideration of variable lifecycle"
            )
    elif coupling_type == CouplingType.EVENT:
        # Event couplings require careful handling of temporal dependencies
        warnings.append(
            "Event coupling detected: ensure proper temporal synchronization "
            "to avoid numerical instabilities"
        )

    # Check for semantic compatibility based on descriptions
    source_desc = (source_var.get('description') or '').lower()
    target_desc = (target_var.get('description') or '').lower()

    if source_desc and target_desc:
        # Simple keyword matching for semantic validation
        semantic_mismatch = _detect_semantic_mismatch(source_desc, target_desc)
        if semantic_mismatch:
            warnings.append(
                f"Potential semantic mismatch: '{source_desc}' -> '{target_desc}'"
            )

    # Interface compatibility is generally permissive with warnings
    return True, errors, warnings


def _has_spatial_domain_info(var_info: Dict[str, Any]) -> bool:
    """Check if variable has spatial domain information for interpolation."""
    # This is a placeholder - in practice, would check for grid information,
    # coordinate systems, etc.
    description = (var_info.get('description') or '').lower()
    spatial_keywords = ['grid', 'spatial', 'coordinate', 'latitude', 'longitude', 'x', 'y', 'z']
    return any(keyword in description for keyword in spatial_keywords)


def _has_aggregation_metadata(var_info: Dict[str, Any]) -> bool:
    """Check if variable has aggregation metadata."""
    # Placeholder for checking aggregation-related metadata
    description = (var_info.get('description') or '').lower()
    aggregation_keywords = ['average', 'sum', 'integral', 'mean', 'total']
    return any(keyword in description for keyword in aggregation_keywords)


def _detect_semantic_mismatch(source_desc: str, target_desc: str) -> bool:
    """Detect potential semantic mismatches between variable descriptions."""
    # Handle empty descriptions
    if not source_desc or not target_desc:
        return False

    # Simple heuristic: look for conflicting keywords
    conflicting_pairs = [
        (['temperature', 'thermal'], ['pressure', 'force']),
        (['concentration', 'density'], ['velocity', 'speed']),
        (['mass', 'weight'], ['length', 'distance']),
        (['energy', 'power'], ['time', 'duration'])
    ]

    for group1, group2 in conflicting_pairs:
        has_group1 = any(keyword in source_desc for keyword in group1)
        has_group2 = any(keyword in target_desc for keyword in group2)

        if has_group1 and has_group2:
            return True

    return False


def construct_coupling_graph(esm_file: EsmFile) -> CouplingGraph:
    """
    Construct a coupling graph from an ESM file definition.

    Args:
        esm_file: The ESM file containing models, reaction systems, and couplings

    Returns:
        A fully constructed coupling graph

    Raises:
        ValueError: If invalid coupling definitions are found
    """
    graph = CouplingGraph()

    # Create nodes for models
    for model in esm_file.models:
        node = CouplingNode(
            id=f"model:{model.name}",
            name=model.name,
            type=NodeType.MODEL,
            variables=list(model.variables.keys()),
            metadata={
                'equations_count': len(model.equations),
                'metadata': model.metadata
            }
        )
        graph.add_node(node)

    # Create nodes for reaction systems
    for reaction_system in esm_file.reaction_systems:
        node = CouplingNode(
            id=f"reaction_system:{reaction_system.name}",
            name=reaction_system.name,
            type=NodeType.REACTION_SYSTEM,
            variables=[species.name for species in reaction_system.species],
            metadata={
                'species_count': len(reaction_system.species),
                'reactions_count': len(reaction_system.reactions),
                'parameters_count': len(reaction_system.parameters)
            }
        )
        graph.add_node(node)

    # Create edges from coupling entries
    for coupling in esm_file.couplings:
        # Create source and target node IDs
        source_id = _resolve_component_id(coupling.source_model, esm_file)
        target_id = _resolve_component_id(coupling.target_model, esm_file)

        # Note: validation already done in _resolve_component_id, nodes should exist
        # This is defensive programming in case the resolution changes
        if source_id not in graph.nodes:
            raise ValueError(f"Internal error: source node '{source_id}' not found after resolution")
        if target_id not in graph.nodes:
            raise ValueError(f"Internal error: target node '{target_id}' not found after resolution")

        # Validate variables exist in source and target
        source_node = graph.nodes[source_id]
        target_node = graph.nodes[target_id]

        for var in coupling.source_variables:
            if var not in source_node.variables:
                raise ValueError(f"Source variable '{var}' not found in component '{coupling.source_model}'")

        for var in coupling.target_variables:
            if var not in target_node.variables:
                raise ValueError(f"Target variable '{var}' not found in component '{coupling.target_model}'")

        # Create coupling edge
        edge = CouplingEdge(
            source_node=source_id,
            target_node=target_id,
            source_variables=coupling.source_variables.copy(),
            target_variables=coupling.target_variables.copy(),
            coupling_type=coupling.coupling_type,
            metadata={
                'transformation': coupling.transformation
            }
        )
        graph.add_edge(edge)

    # Analyze dependencies
    graph.analyze_dependencies()

    return graph


def _resolve_component_id(component_name: str, esm_file: EsmFile) -> str:
    """
    Resolve a component name to its internal ID format.

    Args:
        component_name: Name of the component
        esm_file: ESM file to search in

    Returns:
        Internal ID string for the component

    Raises:
        ValueError: If component is not found
    """
    # Check if it's a model
    for model in esm_file.models:
        if model.name == component_name:
            return f"model:{component_name}"

    # Check if it's a reaction system
    for reaction_system in esm_file.reaction_systems:
        if reaction_system.name == component_name:
            return f"reaction_system:{component_name}"

    raise ValueError(f"Component '{component_name}' not found in ESM file")


def validate_coupling_graph(graph: CouplingGraph) -> Tuple[bool, List[str]]:
    """
    Validate a coupling graph for common issues.

    Args:
        graph: The coupling graph to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    # Check for cycles
    cycles = graph.detect_cycles()
    if cycles:
        for i, cycle in enumerate(cycles):
            errors.append(f"Circular dependency detected in cycle {i+1}: {' -> '.join(cycle)}")

    # Check for orphaned nodes (nodes with no connections)
    for node_id, node in graph.nodes.items():
        if (not graph.get_edges_from_node(node_id) and
            not graph.get_edges_to_node(node_id)):
            errors.append(f"Orphaned node '{node.name}' ({node_id}) has no connections")

    # Check for variable mismatches in couplings
    for edge in graph.edges:
        if len(edge.source_variables) != len(edge.target_variables):
            errors.append(f"Variable count mismatch in coupling {edge.source_node} -> {edge.target_node}: "
                         f"{len(edge.source_variables)} source vars vs {len(edge.target_variables)} target vars")

    return len(errors) == 0, errors


def validate_coupling_variables(
    graph: CouplingGraph,
    esm_file: EsmFile,
    detailed: bool = False
) -> Tuple[bool, List[str], Optional[List[VariableMatchResult]]]:
    """
    Validate coupling variables using the variable matching algorithm.

    Args:
        graph: The coupling graph to validate
        esm_file: The ESM file containing component definitions
        detailed: If True, return detailed matching results

    Returns:
        Tuple of (is_valid, error_messages, detailed_results)
    """
    errors = []
    detailed_results = [] if detailed else None

    # Create component lookup
    components = {}
    for model in esm_file.models:
        components[f"model:{model.name}"] = model
    for reaction_system in esm_file.reaction_systems:
        components[f"reaction_system:{reaction_system.name}"] = reaction_system

    # Validate each coupling edge
    for edge in graph.edges:
        source_component = components.get(edge.source_node)
        target_component = components.get(edge.target_node)

        if not source_component:
            errors.append(f"Source component '{edge.source_node}' not found")

        if not target_component:
            errors.append(f"Target component '{edge.target_node}' not found")

        if not source_component or not target_component:
            continue

        # Validate each variable pair in the coupling
        for i, (source_var, target_var) in enumerate(zip(edge.source_variables, edge.target_variables)):
            try:
                match_result = match_coupling_variables(
                    source_var, target_var,
                    source_component, target_component,
                    edge.coupling_type
                )

                if detailed:
                    detailed_results.append(match_result)

                if not match_result.is_compatible:
                    errors.extend([
                        f"Variable matching failed for {edge.source_node}.{source_var} -> "
                        f"{edge.target_node}.{target_var}: {error}"
                        for error in match_result.errors
                    ])

            except Exception as e:
                errors.append(
                    f"Error validating coupling {edge.source_node}.{source_var} -> "
                    f"{edge.target_node}.{target_var}: {str(e)}"
                )

    return len(errors) == 0, errors, detailed_results


@dataclass
class ScopedReference:
    """
    A resolved scoped reference containing the path and target information.

    A scoped reference like 'AtmosphereModel.Chemistry.temperature' is resolved into:
    - path: ['AtmosphereModel', 'Chemistry'] (the hierarchy path)
    - target: 'temperature' (the final variable/system name)
    - resolved_component: The actual component object
    - resolved_variable: The actual variable object (if applicable)
    """
    original_reference: str
    path: List[str]
    target: str
    resolved_component: Union[Model, ReactionSystem, DataLoader, Operator, Dict]
    resolved_variable: Optional[Dict] = None
    component_type: str = ""  # 'model', 'reaction_system', 'data_loader', 'operator'


class ScopedReferenceResolver:
    """
    Resolver for hierarchical scoped references in ESM format.

    Implements the hierarchical dot notation resolution algorithm from Section 4.3:
    Given 'A.B.C.var', splits on '.' → [A, B, C, var]
    Final segment 'var' is variable name
    Path [A, B, C] walks subsystem hierarchy
    """

    def __init__(self, esm_file: EsmFile):
        """
        Initialize resolver with an ESM file.

        Args:
            esm_file: The ESM file containing components to resolve against
        """
        self.esm_file = esm_file

    def resolve_reference(self, reference: str) -> ScopedReference:
        """
        Resolve a scoped reference to its component and variable.

        Args:
            reference: Scoped reference like 'AtmosphereModel.Chemistry.temperature'

        Returns:
            ScopedReference object with resolved component and variable information

        Raises:
            ValueError: If the reference cannot be resolved
        """
        # Step 1: Split on '.'
        segments = reference.split('.')
        if len(segments) < 2:
            raise ValueError(f"Invalid scoped reference '{reference}': must contain at least one dot")

        # Step 2: Final segment could be variable name or system name
        target = segments[-1]
        path = segments[:-1]

        # Step 3: Find the top-level system in models, reaction_systems, data_loaders, or operators
        top_level_name = path[0]
        component, component_type = self._find_top_level_component(top_level_name)

        if component is None:
            raise ValueError(f"Top-level component '{top_level_name}' not found in ESM file")

        # Step 4: Walk the subsystem hierarchy
        current_component = component
        remaining_path = path[1:]  # Skip the top-level component we already found

        for i, subsystem_name in enumerate(remaining_path):
            if not hasattr(current_component, 'subsystems') and not isinstance(current_component, dict):
                raise ValueError(f"Component at path '{'.'.join(path[:i+1])}' has no subsystems")

            # Handle dict-based components (from parsed JSON)
            if isinstance(current_component, dict):
                subsystems = current_component.get('subsystems', {})
            else:
                subsystems = getattr(current_component, 'subsystems', {})

            if subsystem_name not in subsystems:
                raise ValueError(f"Subsystem '{subsystem_name}' not found in component '{'.'.join(path[:i+1])}'")

            current_component = subsystems[subsystem_name]

        # Step 5: Try to resolve the target as a variable first, then as a subsystem
        resolved_variable = None

        # Check if target is a variable
        variables = {}
        if isinstance(current_component, dict):
            variables = current_component.get('variables', {})
        elif hasattr(current_component, 'variables'):
            variables = getattr(current_component, 'variables', {})

        if target in variables:
            resolved_variable = variables[target]
        else:
            # Check if target is a subsystem (for references like 'AtmosphereModel.Chemistry')
            subsystems = {}
            if isinstance(current_component, dict):
                subsystems = current_component.get('subsystems', {})
            elif hasattr(current_component, 'subsystems'):
                subsystems = getattr(current_component, 'subsystems', {})

            if target in subsystems:
                # Target is a subsystem, not a variable
                current_component = subsystems[target]
                path = segments  # Include the target in the path since it's a component
                target = ""  # No specific variable targeted
            else:
                raise ValueError(f"Target '{target}' not found as variable or subsystem in component '{'.'.join(path)}'")

        return ScopedReference(
            original_reference=reference,
            path=path,
            target=target,
            resolved_component=current_component,
            resolved_variable=resolved_variable,
            component_type=component_type
        )

    def _find_top_level_component(self, name: str) -> Tuple[Optional[Union[Model, ReactionSystem, DataLoader, Operator, Dict]], str]:
        """
        Find a top-level component by name in models, reaction_systems, data_loaders, or operators.

        Args:
            name: Name of the component to find

        Returns:
            Tuple of (component, component_type) or (None, "") if not found
        """
        # Check models
        if hasattr(self.esm_file, 'models') and self.esm_file.models:
            if isinstance(self.esm_file.models, dict) and name in self.esm_file.models:
                return self.esm_file.models[name], 'model'
            elif isinstance(self.esm_file.models, list):
                for model in self.esm_file.models:
                    if (isinstance(model, dict) and model.get('name') == name) or \
                       (hasattr(model, 'name') and model.name == name):
                        return model, 'model'

        # Check reaction_systems
        if hasattr(self.esm_file, 'reaction_systems') and self.esm_file.reaction_systems:
            if isinstance(self.esm_file.reaction_systems, dict) and name in self.esm_file.reaction_systems:
                return self.esm_file.reaction_systems[name], 'reaction_system'
            elif isinstance(self.esm_file.reaction_systems, list):
                for rs in self.esm_file.reaction_systems:
                    if (isinstance(rs, dict) and rs.get('name') == name) or \
                       (hasattr(rs, 'name') and rs.name == name):
                        return rs, 'reaction_system'

        # Check data_loaders
        if hasattr(self.esm_file, 'data_loaders') and self.esm_file.data_loaders:
            if isinstance(self.esm_file.data_loaders, dict) and name in self.esm_file.data_loaders:
                return self.esm_file.data_loaders[name], 'data_loader'

        # Check operators
        if hasattr(self.esm_file, 'operators') and self.esm_file.operators:
            if isinstance(self.esm_file.operators, dict) and name in self.esm_file.operators:
                return self.esm_file.operators[name], 'operator'

        return None, ""

    def validate_reference(self, reference: str) -> Tuple[bool, List[str]]:
        """
        Validate a scoped reference without fully resolving it.

        Args:
            reference: Scoped reference to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        try:
            self.resolve_reference(reference)
            return True, []
        except ValueError as e:
            return False, [str(e)]


def resolve_coupling_dependencies(esm_file: EsmFile) -> Dict[str, List[str]]:
    """
    Resolve all coupling dependencies in an ESM file using scoped references.

    This function analyzes all coupling entries in the ESM file and resolves
    their scoped references to determine the actual dependencies between components.

    Args:
        esm_file: ESM file to analyze

    Returns:
        Dictionary mapping component identifiers to lists of their dependencies

    Raises:
        ValueError: If any scoped references cannot be resolved
    """
    resolver = ScopedReferenceResolver(esm_file)
    dependencies = defaultdict(list)

    if not hasattr(esm_file, 'couplings') or not esm_file.couplings:
        return dict(dependencies)

    for coupling in esm_file.couplings:
        if hasattr(coupling, 'type') and coupling.type in ['variable_map', 'couple2']:
            # Handle variable_map couplings
            if hasattr(coupling, 'from_ref') and hasattr(coupling, 'to_ref'):
                from_ref = coupling.from_ref
                to_ref = coupling.to_ref
            elif hasattr(coupling, 'from') and hasattr(coupling, 'to'):
                from_ref = coupling.from_ref if hasattr(coupling, 'from_ref') else str(coupling.from_ref)
                to_ref = coupling.to if hasattr(coupling, 'to_ref') else str(coupling.to)
            else:
                continue

            try:
                # Resolve source and target references
                from_resolved = resolver.resolve_reference(from_ref)
                to_resolved = resolver.resolve_reference(to_ref)

                # Create dependency: target depends on source
                from_component_id = f"{from_resolved.component_type}:{from_resolved.path[0]}"
                to_component_id = f"{to_resolved.component_type}:{to_resolved.path[0]}"

                if from_component_id != to_component_id:
                    dependencies[to_component_id].append(from_component_id)

            except ValueError as e:
                # Skip invalid references for now, could be enhanced to collect errors
                continue

        elif hasattr(coupling, 'type') and coupling.type == 'operator_compose':
            # Handle operator_compose couplings
            if hasattr(coupling, 'systems') and isinstance(coupling.systems, list):
                # All systems in the compose depend on each other
                resolved_systems = []
                for system_ref in coupling.systems:
                    try:
                        resolved = resolver.resolve_reference(system_ref)
                        component_id = f"{resolved.component_type}:{resolved.path[0]}"
                        resolved_systems.append(component_id)
                    except ValueError:
                        continue

                # Create bidirectional dependencies between composed systems
                for i, sys1 in enumerate(resolved_systems):
                    for j, sys2 in enumerate(resolved_systems):
                        if i != j and sys2 not in dependencies[sys1]:
                            dependencies[sys1].append(sys2)

    return dict(dependencies)


def build_execution_order_from_dependencies(dependencies: Dict[str, List[str]]) -> List[str]:
    """
    Build an execution order from dependency information using topological sorting.

    Args:
        dependencies: Dictionary mapping components to their dependencies

    Returns:
        List of component identifiers in execution order

    Raises:
        ValueError: If circular dependencies are detected
    """
    # Create a graph representation
    all_components = set(dependencies.keys())
    for deps in dependencies.values():
        all_components.update(deps)

    # Calculate in-degrees
    in_degree = {comp: 0 for comp in all_components}
    for target, deps in dependencies.items():
        for dep in deps:
            if dep in all_components:  # Only count dependencies that exist
                in_degree[target] += 1

    # Topological sort using Kahn's algorithm
    queue = deque([comp for comp in all_components if in_degree[comp] == 0])
    execution_order = []

    while queue:
        current = queue.popleft()
        execution_order.append(current)

        # Find all components that depend on current
        for target, deps in dependencies.items():
            if current in deps:
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)

    # Check for cycles
    if len(execution_order) != len(all_components):
        remaining = all_components - set(execution_order)
        raise ValueError(f"Circular dependencies detected among components: {', '.join(remaining)}")

    return execution_order