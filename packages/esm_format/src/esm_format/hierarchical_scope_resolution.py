"""
Enhanced hierarchical scope resolution algorithm for ESM Format.

This module implements comprehensive hierarchical scope resolution with:
1. Scope chain traversal - walking up and down the hierarchy
2. Variable shadowing rules - inner scopes shadow outer scopes
3. Scope inheritance - inner scopes can access parent scope variables

The algorithm follows these resolution rules:
- Direct resolution: Try to find the variable at the exact scope requested
- Inheritance resolution: If not found, walk up the scope chain to parent scopes
- Shadowing enforcement: When multiple scopes have the same variable, use the most specific (inner) one
"""

from typing import Dict, List, Set, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from .esm_types import CouplingEntry, CouplingType, EsmFile, Model, ReactionSystem, DataLoader, Operator, ModelVariable, Species
from .coupling_graph import ScopedReference


@dataclass
class ScopeInfo:
    """Information about a scope in the hierarchy."""
    name: str
    full_path: List[str]  # Full path from root to this scope
    parent: Optional['ScopeInfo'] = None
    children: Dict[str, 'ScopeInfo'] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    component_data: Any = None  # The actual component object/dict
    component_type: str = ""


@dataclass
class VariableResolution:
    """Result of variable resolution with scope information."""
    variable_name: str
    resolved_value: Any
    resolved_scope: ScopeInfo
    resolution_type: str  # "direct", "inherited", "shadowed"
    shadow_chain: List[ScopeInfo] = field(default_factory=list)  # Scopes that were shadowed
    available_scopes: List[ScopeInfo] = field(default_factory=list)  # All scopes checked


class HierarchicalScopeResolver:
    """
    Enhanced hierarchical scope resolver with shadowing and inheritance.

    This resolver builds a complete scope hierarchy tree and implements
    sophisticated variable resolution with proper shadowing semantics.
    """

    def __init__(self, esm_file: EsmFile):
        """
        Initialize the hierarchical scope resolver.

        Args:
            esm_file: The ESM file containing components to resolve against
        """
        self.esm_file = esm_file
        self.scope_tree: Dict[str, ScopeInfo] = {}
        self.logger = logging.getLogger(__name__)

        # Build the scope hierarchy tree
        self._build_scope_tree()

    def _build_scope_tree(self):
        """Build the complete scope hierarchy tree from the ESM file."""
        self.scope_tree.clear()

        # Process models
        if hasattr(self.esm_file, 'models') and self.esm_file.models:
            self._build_tree_from_components(self.esm_file.models, 'model')

        # Process reaction systems
        if hasattr(self.esm_file, 'reaction_systems') and self.esm_file.reaction_systems:
            self._build_tree_from_components(self.esm_file.reaction_systems, 'reaction_system')

        # Process data loaders
        if hasattr(self.esm_file, 'data_loaders') and self.esm_file.data_loaders:
            self._build_tree_from_components(self.esm_file.data_loaders, 'data_loader')

        # Process operators
        if hasattr(self.esm_file, 'operators') and self.esm_file.operators:
            self._build_tree_from_components(self.esm_file.operators, 'operator')

    def _build_tree_from_components(self, components: Union[Dict, List], component_type: str):
        """Build scope tree from a collection of components."""
        if isinstance(components, dict):
            for name, component in components.items():
                self._build_scope_subtree(component, [name], component_type)
        elif isinstance(components, list):
            for component in components:
                if isinstance(component, dict) and 'name' in component:
                    name = component['name']
                elif hasattr(component, 'name'):
                    name = component.name
                else:
                    continue
                self._build_scope_subtree(component, [name], component_type)

    def _build_scope_subtree(self, component: Any, path: List[str], component_type: str, parent: Optional[ScopeInfo] = None):
        """Recursively build scope subtree for a component and its subsystems."""
        # Create scope info for this component
        scope_name = path[-1]
        scope_info = ScopeInfo(
            name=scope_name,
            full_path=path.copy(),
            parent=parent,
            component_data=component,
            component_type=component_type
        )

        # Extract variables from the component
        scope_info.variables = self._extract_variables_from_component(component)

        # Store in the tree
        scope_key = '.'.join(path)
        self.scope_tree[scope_key] = scope_info

        # Link to parent
        if parent:
            parent.children[scope_name] = scope_info

        # Recursively process subsystems
        subsystems = {}
        if isinstance(component, dict):
            subsystems = component.get('subsystems', {})
        elif hasattr(component, 'subsystems'):
            subsystems = getattr(component, 'subsystems', {})

        for subsystem_name, subsystem_data in subsystems.items():
            child_path = path + [subsystem_name]
            self._build_scope_subtree(subsystem_data, child_path, component_type, scope_info)

    def _extract_variables_from_component(self, component: Any) -> Dict[str, Any]:
        """Extract all variables from a component."""
        variables = {}

        # Handle dict-based components
        if isinstance(component, dict):
            variables.update(component.get('variables', {}))
            # Also check for provides (for data loaders)
            variables.update(component.get('provides', {}))
        else:
            # Handle object-based components
            if hasattr(component, 'variables'):
                if isinstance(component.variables, dict):
                    variables.update(component.variables)

            # Handle Model objects specifically
            if hasattr(component, '__class__') and component.__class__.__name__ == 'Model':
                for var_name, var_obj in getattr(component, 'variables', {}).items():
                    if hasattr(var_obj, '__dict__'):
                        variables[var_name] = var_obj.__dict__
                    else:
                        variables[var_name] = var_obj

            # Handle ReactionSystem objects
            elif hasattr(component, '__class__') and component.__class__.__name__ == 'ReactionSystem':
                # Add species as variables
                for species in getattr(component, 'species', []):
                    if hasattr(species, 'name'):
                        variables[species.name] = {
                            'type': 'species',
                            'units': getattr(species, 'units', None),
                            'description': getattr(species, 'description', None)
                        }

                # Add parameters as variables
                for param in getattr(component, 'parameters', []):
                    if hasattr(param, 'name'):
                        variables[param.name] = {
                            'type': 'parameter',
                            'units': getattr(param, 'units', None),
                            'value': getattr(param, 'value', None),
                            'description': getattr(param, 'description', None)
                        }

        return variables

    def resolve_variable(self, reference: str) -> VariableResolution:
        """
        Resolve a scoped variable reference with full shadowing and inheritance.

        Args:
            reference: Scoped reference like 'AtmosphereModel.Chemistry.temperature'

        Returns:
            VariableResolution with complete resolution information

        Raises:
            ValueError: If the reference cannot be resolved
        """
        # Parse the reference
        segments = reference.split('.')
        if len(segments) < 2:
            raise ValueError(f"Invalid scoped reference '{reference}': must contain at least one dot")

        variable_name = segments[-1]
        scope_path = segments[:-1]

        # Find the target scope
        scope_key = '.'.join(scope_path)
        if scope_key not in self.scope_tree:
            raise ValueError(f"Scope '{scope_key}' not found in hierarchy")

        target_scope = self.scope_tree[scope_key]

        # Try direct resolution first
        if variable_name in target_scope.variables:
            return VariableResolution(
                variable_name=variable_name,
                resolved_value=target_scope.variables[variable_name],
                resolved_scope=target_scope,
                resolution_type="direct",
                available_scopes=[target_scope]
            )

        # Try inheritance resolution (walk up the scope chain)
        current_scope = target_scope
        shadow_chain = []
        available_scopes = [target_scope]

        while current_scope.parent:
            current_scope = current_scope.parent
            available_scopes.append(current_scope)

            if variable_name in current_scope.variables:
                return VariableResolution(
                    variable_name=variable_name,
                    resolved_value=current_scope.variables[variable_name],
                    resolved_scope=current_scope,
                    resolution_type="inherited",
                    shadow_chain=shadow_chain,
                    available_scopes=available_scopes
                )

        # Variable not found in any parent scope
        all_available = self._get_all_available_variables_in_scope_chain(target_scope)
        raise ValueError(
            f"Variable '{variable_name}' not found in scope '{scope_key}' or any parent scope. "
            f"Available variables: {list(all_available.keys())}"
        )

    def _get_all_available_variables_in_scope_chain(self, scope: ScopeInfo) -> Dict[str, ScopeInfo]:
        """Get all variables available in a scope chain (including parents)."""
        available = {}
        current = scope

        while current:
            for var_name in current.variables:
                if var_name not in available:  # Respect shadowing - first one found wins
                    available[var_name] = current
            current = current.parent

        return available

    def find_variable_shadows(self, variable_name: str, scope_path: List[str]) -> List[Tuple[ScopeInfo, Any]]:
        """
        Find all instances of a variable in the scope hierarchy (for shadowing analysis).

        Args:
            variable_name: Name of the variable to search for
            scope_path: Path to start the search from

        Returns:
            List of (scope, variable_value) tuples where the variable exists
        """
        shadows = []

        # Start from the specified scope and walk up
        scope_key = '.'.join(scope_path)
        if scope_key not in self.scope_tree:
            return shadows

        current_scope = self.scope_tree[scope_key]

        while current_scope:
            if variable_name in current_scope.variables:
                shadows.append((current_scope, current_scope.variables[variable_name]))
            current_scope = current_scope.parent

        return shadows

    def resolve_with_shadowing_info(self, reference: str) -> VariableResolution:
        """
        Resolve a variable with complete shadowing information.

        This method provides detailed information about which variables were
        shadowed during the resolution process.
        """
        segments = reference.split('.')
        if len(segments) < 2:
            raise ValueError(f"Invalid scoped reference '{reference}': must contain at least one dot")

        variable_name = segments[-1]
        scope_path = segments[:-1]

        # Find all shadows of this variable
        shadows = self.find_variable_shadows(variable_name, scope_path)

        if not shadows:
            scope_key = '.'.join(scope_path)
            if scope_key in self.scope_tree:
                available = self._get_all_available_variables_in_scope_chain(self.scope_tree[scope_key])
                raise ValueError(
                    f"Variable '{variable_name}' not found in scope '{scope_key}' or any parent scope. "
                    f"Available variables: {list(available.keys())}"
                )
            else:
                raise ValueError(f"Scope '{scope_key}' not found in hierarchy")

        # The first shadow is the resolved variable (most specific scope)
        resolved_scope, resolved_value = shadows[0]

        # Determine resolution type
        scope_key = '.'.join(scope_path)
        if resolved_scope.full_path == scope_path:
            resolution_type = "direct"
            shadow_chain = [scope for scope, _ in shadows[1:]]  # All others were shadowed
        else:
            resolution_type = "inherited"
            shadow_chain = [scope for scope, _ in shadows[1:]]  # All others were shadowed

        return VariableResolution(
            variable_name=variable_name,
            resolved_value=resolved_value,
            resolved_scope=resolved_scope,
            resolution_type=resolution_type,
            shadow_chain=shadow_chain,
            available_scopes=[scope for scope, _ in shadows]
        )

    def validate_scope_hierarchy(self) -> Tuple[bool, List[str]]:
        """
        Validate the scope hierarchy for common issues.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []

        # Check for orphaned scopes
        for scope_key, scope_info in self.scope_tree.items():
            if len(scope_info.full_path) > 1 and scope_info.parent is None:
                errors.append(f"Orphaned scope '{scope_key}': has path depth > 1 but no parent")

        # Check for circular parent relationships (shouldn't happen, but defensive)
        for scope_key, scope_info in self.scope_tree.items():
            visited = set()
            current = scope_info
            while current:
                if id(current) in visited:
                    errors.append(f"Circular parent relationship detected in scope '{scope_key}'")
                    break
                visited.add(id(current))
                current = current.parent

        # Check for inconsistent children relationships
        for scope_key, scope_info in self.scope_tree.items():
            for child_name, child_scope in scope_info.children.items():
                if child_scope.parent is not scope_info:
                    errors.append(f"Inconsistent parent-child relationship: '{scope_key}'.'{child_name}'")

        return len(errors) == 0, errors

    def get_scope_statistics(self) -> Dict[str, Any]:
        """Get statistics about the scope hierarchy."""
        stats = {
            'total_scopes': len(self.scope_tree),
            'max_depth': 0,
            'scopes_by_type': defaultdict(int),
            'variables_by_scope': {},
            'total_variables': 0
        }

        for scope_key, scope_info in self.scope_tree.items():
            # Track max depth
            depth = len(scope_info.full_path)
            stats['max_depth'] = max(stats['max_depth'], depth)

            # Track scopes by type
            stats['scopes_by_type'][scope_info.component_type] += 1

            # Track variables
            var_count = len(scope_info.variables)
            stats['variables_by_scope'][scope_key] = var_count
            stats['total_variables'] += var_count

        return dict(stats)


def create_enhanced_scoped_reference(
    resolver: HierarchicalScopeResolver,
    reference: str
) -> ScopedReference:
    """
    Create an enhanced ScopedReference using the hierarchical resolver.

    This function bridges the old ScopedReference interface with the new
    hierarchical resolution capabilities.
    """
    resolution = resolver.resolve_with_shadowing_info(reference)

    segments = reference.split('.')
    path = segments[:-1] if len(segments) > 1 else []
    target = segments[-1] if len(segments) > 1 else ""

    return ScopedReference(
        original_reference=reference,
        path=path,
        target=target,
        resolved_component=resolution.resolved_scope.component_data,
        resolved_variable=resolution.resolved_value,
        component_type=resolution.resolved_scope.component_type
    )