"""
Dynamic scope resolution for runtime contexts in ESM Format.

This module extends the hierarchical scope resolution system to support:
1. Runtime parameter injection - dynamically inject parameters into scopes
2. Context switching - switch between different runtime contexts
3. Dynamic scope creation - create new scopes at runtime
4. Runtime variable overrides - temporarily override variable values
5. Context isolation - maintain separate runtime contexts that don't interfere

The dynamic system builds on top of the static hierarchical scope resolution
but allows for runtime modifications without altering the original ESM structure.
"""

from typing import Dict, List, Set, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, ChainMap
import logging
import copy
import uuid
from contextlib import contextmanager

from .esm_types import EsmFile, ModelVariable
from .hierarchical_scope_resolution import HierarchicalScopeResolver, ScopeInfo, VariableResolution


@dataclass
class RuntimeVariable:
    """A variable with runtime context information."""
    name: str
    value: Any
    units: Optional[str] = None
    description: Optional[str] = None
    injected_at: Optional[str] = None  # ISO datetime when injected
    injector_id: Optional[str] = None  # ID of who/what injected this
    expiry_time: Optional[str] = None  # Optional expiry time
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeContext:
    """A runtime execution context with injected parameters and overrides."""
    context_id: str
    name: str
    parent_context_id: Optional[str] = None
    created_at: Optional[str] = None
    description: Optional[str] = None

    # Runtime variable overrides and injections
    injected_variables: Dict[str, Dict[str, RuntimeVariable]] = field(default_factory=dict)  # scope_path -> var_name -> RuntimeVariable
    variable_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # scope_path -> var_name -> override_value

    # Dynamic scopes created at runtime
    dynamic_scopes: Dict[str, ScopeInfo] = field(default_factory=dict)  # scope_path -> ScopeInfo

    # Context-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class ContextSwitchResult:
    """Result of a context switch operation."""
    from_context_id: Optional[str]
    to_context_id: str
    switch_successful: bool
    affected_scopes: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class DynamicScopeResolver:
    """
    Dynamic scope resolver with runtime context support.

    This resolver extends HierarchicalScopeResolver to support runtime
    modifications including parameter injection, context switching,
    and dynamic scope creation.
    """

    def __init__(self, esm_file: EsmFile):
        """
        Initialize the dynamic scope resolver.

        Args:
            esm_file: The ESM file containing the base component structure
        """
        self.esm_file = esm_file
        self.base_resolver = HierarchicalScopeResolver(esm_file)
        self.logger = logging.getLogger(__name__)

        # Runtime context management
        self.contexts: Dict[str, RuntimeContext] = {}
        self.current_context_id: Optional[str] = None
        self.default_context_id = "default"

        # Create default context
        self._create_default_context()

        # Variable change listeners
        self.variable_change_listeners: List[Callable] = []

    def _create_default_context(self):
        """Create the default runtime context."""
        default_context = RuntimeContext(
            context_id=self.default_context_id,
            name="Default Context",
            created_at="initialization",
            description="Default runtime context created at resolver initialization"
        )
        self.contexts[self.default_context_id] = default_context
        self.current_context_id = self.default_context_id

    def create_runtime_context(self,
                             name: str,
                             parent_context_id: Optional[str] = None,
                             description: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new runtime context.

        Args:
            name: Human-readable name for the context
            parent_context_id: Optional parent context ID for inheritance
            description: Optional description of the context
            metadata: Optional metadata dictionary

        Returns:
            The new context ID

        Raises:
            ValueError: If parent_context_id doesn't exist
        """
        context_id = f"ctx_{uuid.uuid4().hex[:8]}"

        if parent_context_id and parent_context_id not in self.contexts:
            raise ValueError(f"Parent context '{parent_context_id}' does not exist")

        context = RuntimeContext(
            context_id=context_id,
            name=name,
            parent_context_id=parent_context_id,
            description=description,
            metadata=metadata or {}
        )

        # If there's a parent context, inherit its injections and overrides
        if parent_context_id:
            parent = self.contexts[parent_context_id]
            context.injected_variables = copy.deepcopy(parent.injected_variables)
            context.variable_overrides = copy.deepcopy(parent.variable_overrides)
            context.dynamic_scopes = copy.deepcopy(parent.dynamic_scopes)

        self.contexts[context_id] = context
        self.logger.info(f"Created runtime context '{name}' with ID '{context_id}'")

        return context_id

    def switch_context(self, context_id: str) -> ContextSwitchResult:
        """
        Switch to a different runtime context.

        Args:
            context_id: ID of the context to switch to

        Returns:
            ContextSwitchResult with switch details
        """
        if context_id not in self.contexts:
            return ContextSwitchResult(
                from_context_id=self.current_context_id,
                to_context_id=context_id,
                switch_successful=False,
                error_message=f"Context '{context_id}' does not exist"
            )

        if not self.contexts[context_id].is_active:
            return ContextSwitchResult(
                from_context_id=self.current_context_id,
                to_context_id=context_id,
                switch_successful=False,
                error_message=f"Context '{context_id}' is not active"
            )

        old_context_id = self.current_context_id
        self.current_context_id = context_id

        # Calculate affected scopes
        affected_scopes = []
        if old_context_id:
            old_context = self.contexts[old_context_id]
            new_context = self.contexts[context_id]

            all_scopes = set(old_context.injected_variables.keys()) | set(old_context.variable_overrides.keys())
            all_scopes |= set(new_context.injected_variables.keys()) | set(new_context.variable_overrides.keys())
            affected_scopes = list(all_scopes)

        self.logger.info(f"Switched context from '{old_context_id}' to '{context_id}'")

        return ContextSwitchResult(
            from_context_id=old_context_id,
            to_context_id=context_id,
            switch_successful=True,
            affected_scopes=affected_scopes
        )

    @contextmanager
    def temporary_context(self, context_id: str):
        """
        Context manager for temporarily switching contexts.

        Args:
            context_id: ID of the context to switch to temporarily

        Yields:
            The temporary context

        Example:
            with resolver.temporary_context("simulation_ctx") as ctx:
                result = resolver.resolve_variable_dynamic("model.temperature")
        """
        old_context_id = self.current_context_id
        switch_result = self.switch_context(context_id)

        if not switch_result.switch_successful:
            raise ValueError(switch_result.error_message)

        try:
            yield self.contexts[context_id]
        finally:
            if old_context_id:
                self.switch_context(old_context_id)

    def inject_parameter(self,
                        scope_path: str,
                        variable_name: str,
                        value: Any,
                        units: Optional[str] = None,
                        description: Optional[str] = None,
                        context_id: Optional[str] = None,
                        injector_id: Optional[str] = None,
                        expiry_time: Optional[str] = None) -> bool:
        """
        Inject a parameter into a scope within a runtime context.

        Args:
            scope_path: Dot-separated path to the scope (e.g., "AtmosphereModel.Chemistry")
            variable_name: Name of the variable to inject
            value: Value to inject
            units: Optional units for the variable
            description: Optional description
            context_id: Context to inject into (uses current if None)
            injector_id: ID of who/what is injecting this parameter
            expiry_time: Optional expiry time for the injection

        Returns:
            True if injection successful, False otherwise
        """
        if not context_id:
            context_id = self.current_context_id

        if not context_id or context_id not in self.contexts:
            self.logger.error(f"Cannot inject parameter: invalid context '{context_id}'")
            return False

        context = self.contexts[context_id]

        # Create the runtime variable
        runtime_var = RuntimeVariable(
            name=variable_name,
            value=value,
            units=units,
            description=description,
            injector_id=injector_id,
            expiry_time=expiry_time
        )

        # Add to context's injected variables
        if scope_path not in context.injected_variables:
            context.injected_variables[scope_path] = {}

        context.injected_variables[scope_path][variable_name] = runtime_var

        self.logger.info(f"Injected parameter '{variable_name}' into scope '{scope_path}' in context '{context_id}'")

        # Notify listeners
        self._notify_variable_change("parameter_injected", scope_path, variable_name, value, context_id)

        return True

    def override_variable(self,
                         scope_path: str,
                         variable_name: str,
                         override_value: Any,
                         context_id: Optional[str] = None) -> bool:
        """
        Override an existing variable's value in a runtime context.

        Args:
            scope_path: Dot-separated path to the scope
            variable_name: Name of the variable to override
            override_value: New value for the variable
            context_id: Context to apply override in (uses current if None)

        Returns:
            True if override successful, False otherwise
        """
        if not context_id:
            context_id = self.current_context_id

        if not context_id or context_id not in self.contexts:
            self.logger.error(f"Cannot override variable: invalid context '{context_id}'")
            return False

        # Check if the base variable exists
        try:
            self.base_resolver.resolve_variable(f"{scope_path}.{variable_name}")
        except ValueError:
            self.logger.error(f"Cannot override non-existent variable '{scope_path}.{variable_name}'")
            return False

        context = self.contexts[context_id]

        if scope_path not in context.variable_overrides:
            context.variable_overrides[scope_path] = {}

        context.variable_overrides[scope_path][variable_name] = override_value

        self.logger.info(f"Override variable '{variable_name}' in scope '{scope_path}' in context '{context_id}'")

        # Notify listeners
        self._notify_variable_change("variable_overridden", scope_path, variable_name, override_value, context_id)

        return True

    def create_dynamic_scope(self,
                           scope_path: str,
                           scope_name: str,
                           variables: Optional[Dict[str, Any]] = None,
                           component_type: str = "dynamic",
                           context_id: Optional[str] = None) -> bool:
        """
        Create a new dynamic scope at runtime.

        Args:
            scope_path: Parent scope path (e.g., "AtmosphereModel")
            scope_name: Name of the new scope
            variables: Optional initial variables for the scope
            component_type: Type of component being created
            context_id: Context to create scope in (uses current if None)

        Returns:
            True if scope creation successful, False otherwise
        """
        if not context_id:
            context_id = self.current_context_id

        if not context_id or context_id not in self.contexts:
            self.logger.error(f"Cannot create dynamic scope: invalid context '{context_id}'")
            return False

        context = self.contexts[context_id]

        # Build full scope path
        full_scope_path = f"{scope_path}.{scope_name}" if scope_path else scope_name

        # Check if scope already exists
        if full_scope_path in self.base_resolver.scope_tree or full_scope_path in context.dynamic_scopes:
            self.logger.error(f"Scope '{full_scope_path}' already exists")
            return False

        # Find parent scope
        parent_scope = None
        if scope_path:
            if scope_path in self.base_resolver.scope_tree:
                parent_scope = self.base_resolver.scope_tree[scope_path]
            elif scope_path in context.dynamic_scopes:
                parent_scope = context.dynamic_scopes[scope_path]
            else:
                self.logger.error(f"Parent scope '{scope_path}' not found")
                return False

        # Create the dynamic scope
        dynamic_scope = ScopeInfo(
            name=scope_name,
            full_path=full_scope_path.split('.'),
            parent=parent_scope,
            variables=variables or {},
            component_data={'name': scope_name, 'variables': variables or {}},
            component_type=component_type
        )

        # Add to parent's children if there is a parent
        if parent_scope:
            parent_scope.children[scope_name] = dynamic_scope

        context.dynamic_scopes[full_scope_path] = dynamic_scope

        self.logger.info(f"Created dynamic scope '{full_scope_path}' in context '{context_id}'")

        return True

    def resolve_variable_dynamic(self, reference: str, context_id: Optional[str] = None) -> VariableResolution:
        """
        Resolve a variable with dynamic runtime context support.

        This method extends the base resolution to include:
        1. Variable overrides from the current context
        2. Injected parameters
        3. Dynamic scopes

        Args:
            reference: Scoped reference like 'AtmosphereModel.Chemistry.temperature'
            context_id: Context to resolve in (uses current if None)

        Returns:
            VariableResolution with runtime context information

        Raises:
            ValueError: If the reference cannot be resolved
        """
        if not context_id:
            context_id = self.current_context_id

        if not context_id or context_id not in self.contexts:
            raise ValueError(f"Invalid context '{context_id}'")

        context = self.contexts[context_id]
        segments = reference.split('.')

        if len(segments) < 2:
            raise ValueError(f"Invalid scoped reference '{reference}': must contain at least one dot")

        variable_name = segments[-1]
        scope_path = '.'.join(segments[:-1])

        # First, check for variable overrides in current context
        if scope_path in context.variable_overrides and variable_name in context.variable_overrides[scope_path]:
            override_value = context.variable_overrides[scope_path][variable_name]

            # Try to get the original scope for context
            try:
                original_resolution = self.base_resolver.resolve_variable(reference)
                return VariableResolution(
                    variable_name=variable_name,
                    resolved_value=override_value,
                    resolved_scope=original_resolution.resolved_scope,
                    resolution_type="overridden",
                    available_scopes=original_resolution.available_scopes
                )
            except ValueError:
                # If original doesn't exist, treat as error
                raise ValueError(f"Cannot override non-existent variable '{reference}'")

        # Second, check for injected parameters
        if scope_path in context.injected_variables and variable_name in context.injected_variables[scope_path]:
            runtime_var = context.injected_variables[scope_path][variable_name]

            # Create a synthetic scope info for injected variables
            synthetic_scope = ScopeInfo(
                name=segments[-2] if len(segments) > 1 else "root",
                full_path=segments[:-1],
                variables={variable_name: runtime_var.value}
            )

            return VariableResolution(
                variable_name=variable_name,
                resolved_value=runtime_var.value,
                resolved_scope=synthetic_scope,
                resolution_type="injected",
                available_scopes=[synthetic_scope]
            )

        # Third, check dynamic scopes
        if scope_path in context.dynamic_scopes:
            dynamic_scope = context.dynamic_scopes[scope_path]
            if variable_name in dynamic_scope.variables:
                return VariableResolution(
                    variable_name=variable_name,
                    resolved_value=dynamic_scope.variables[variable_name],
                    resolved_scope=dynamic_scope,
                    resolution_type="dynamic",
                    available_scopes=[dynamic_scope]
                )

        # Finally, fall back to base hierarchical resolution
        try:
            return self.base_resolver.resolve_variable(reference)
        except ValueError:
            # Enhance error message with context info
            available_injected = []
            available_overridden = []
            available_dynamic = []

            if scope_path in context.injected_variables:
                available_injected = list(context.injected_variables[scope_path].keys())
            if scope_path in context.variable_overrides:
                available_overridden = list(context.variable_overrides[scope_path].keys())
            if scope_path in context.dynamic_scopes:
                available_dynamic = list(context.dynamic_scopes[scope_path].variables.keys())

            error_parts = [f"Variable '{variable_name}' not found in scope '{scope_path}' (context: {context_id})"]

            if available_injected:
                error_parts.append(f"Injected variables: {available_injected}")
            if available_overridden:
                error_parts.append(f"Overridden variables: {available_overridden}")
            if available_dynamic:
                error_parts.append(f"Dynamic scope variables: {available_dynamic}")

            raise ValueError(". ".join(error_parts))

    def get_context_info(self, context_id: Optional[str] = None) -> RuntimeContext:
        """
        Get information about a runtime context.

        Args:
            context_id: Context to get info for (uses current if None)

        Returns:
            RuntimeContext object

        Raises:
            ValueError: If context doesn't exist
        """
        if not context_id:
            context_id = self.current_context_id

        if not context_id or context_id not in self.contexts:
            raise ValueError(f"Context '{context_id}' does not exist")

        return self.contexts[context_id]

    def list_contexts(self) -> List[Tuple[str, str, bool]]:
        """
        List all available contexts.

        Returns:
            List of (context_id, name, is_current) tuples
        """
        return [
            (ctx_id, ctx.name, ctx_id == self.current_context_id)
            for ctx_id, ctx in self.contexts.items()
        ]

    def clear_context_injections(self,
                                scope_path: Optional[str] = None,
                                context_id: Optional[str] = None) -> int:
        """
        Clear injected parameters from a context.

        Args:
            scope_path: Specific scope to clear (clears all if None)
            context_id: Context to clear from (uses current if None)

        Returns:
            Number of injections cleared
        """
        if not context_id:
            context_id = self.current_context_id

        if not context_id or context_id not in self.contexts:
            return 0

        context = self.contexts[context_id]
        cleared_count = 0

        if scope_path:
            # Clear specific scope
            if scope_path in context.injected_variables:
                cleared_count = len(context.injected_variables[scope_path])
                del context.injected_variables[scope_path]
        else:
            # Clear all scopes
            for scope_vars in context.injected_variables.values():
                cleared_count += len(scope_vars)
            context.injected_variables.clear()

        self.logger.info(f"Cleared {cleared_count} injections from context '{context_id}'")
        return cleared_count

    def add_variable_change_listener(self, listener: Callable):
        """Add a listener for variable change events."""
        self.variable_change_listeners.append(listener)

    def remove_variable_change_listener(self, listener: Callable):
        """Remove a variable change listener."""
        if listener in self.variable_change_listeners:
            self.variable_change_listeners.remove(listener)

    def _notify_variable_change(self,
                              change_type: str,
                              scope_path: str,
                              variable_name: str,
                              new_value: Any,
                              context_id: str):
        """Notify listeners of variable changes."""
        for listener in self.variable_change_listeners:
            try:
                listener(change_type, scope_path, variable_name, new_value, context_id)
            except Exception as e:
                self.logger.warning(f"Variable change listener failed: {e}")

    def get_runtime_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the runtime context system.

        Returns:
            Dictionary with runtime statistics
        """
        stats = {
            'total_contexts': len(self.contexts),
            'current_context_id': self.current_context_id,
            'contexts_info': {},
            'total_injections': 0,
            'total_overrides': 0,
            'total_dynamic_scopes': 0
        }

        for ctx_id, ctx in self.contexts.items():
            injection_count = sum(len(scope_vars) for scope_vars in ctx.injected_variables.values())
            override_count = sum(len(scope_vars) for scope_vars in ctx.variable_overrides.values())
            dynamic_scope_count = len(ctx.dynamic_scopes)

            stats['contexts_info'][ctx_id] = {
                'name': ctx.name,
                'is_active': ctx.is_active,
                'injection_count': injection_count,
                'override_count': override_count,
                'dynamic_scope_count': dynamic_scope_count,
                'has_parent': ctx.parent_context_id is not None
            }

            stats['total_injections'] += injection_count
            stats['total_overrides'] += override_count
            stats['total_dynamic_scopes'] += dynamic_scope_count

        return stats