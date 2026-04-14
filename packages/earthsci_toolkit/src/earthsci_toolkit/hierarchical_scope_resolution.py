"""
Minimal hierarchical scope resolution for ESM Format.
This provides only the essential scoped reference resolution required by validation.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any, Tuple
from .esm_types import EsmFile, Model, ReactionSystem


@dataclass
class ScopeInfo:
    """Information about a scope."""
    name: str
    parent: Optional[str] = None
    variables: Optional[List[str]] = None


@dataclass
class VariableResolution:
    """Result of variable resolution."""
    variable_name: str
    system_name: str
    found: bool
    full_path: Optional[str] = None


class HierarchicalScopeResolver:
    """Minimal hierarchical scope resolver for scoped references."""

    def __init__(self, esm_file: EsmFile):
        self.esm_file = esm_file

    def resolve_variable(self, reference: str, context_system: Optional[str] = None) -> VariableResolution:
        """Resolve a potentially scoped variable reference."""
        parts = reference.split('.')

        if len(parts) == 1:
            # Unqualified variable - look in context system first
            var_name = parts[0]

            if context_system:
                if self._variable_exists_in_system(var_name, context_system):
                    return VariableResolution(
                        variable_name=var_name,
                        system_name=context_system,
                        found=True,
                        full_path=f"{context_system}.{var_name}"
                    )

            # Look in all systems
            for system_name in self._get_all_system_names():
                if self._variable_exists_in_system(var_name, system_name):
                    return VariableResolution(
                        variable_name=var_name,
                        system_name=system_name,
                        found=True,
                        full_path=f"{system_name}.{var_name}"
                    )

            return VariableResolution(
                variable_name=var_name,
                system_name="",
                found=False
            )

        else:
            # Qualified variable - resolve system path (supports multi-level paths like A.B.C.variable)
            var_name = parts[-1]
            system_path = parts[:-1]  # All parts except the last (variable name)

            # Try to resolve the variable through the subsystem hierarchy
            found, resolved_system = self._resolve_variable_in_hierarchy(system_path, var_name)

            if found:
                return VariableResolution(
                    variable_name=var_name,
                    system_name=resolved_system,
                    found=True,
                    full_path=reference
                )
            else:
                # For backward compatibility, try the old single-level approach
                system_name = parts[0]
                if self._system_exists(system_name) and self._variable_exists_in_system(var_name, system_name):
                    return VariableResolution(
                        variable_name=var_name,
                        system_name=system_name,
                        found=True,
                        full_path=reference
                    )

            return VariableResolution(
                variable_name=var_name,
                system_name=".".join(system_path),
                found=False,
                full_path=reference
            )

    def _get_all_system_names(self) -> List[str]:
        """Get all system names."""
        systems = []
        if self.esm_file.models:
            systems.extend(self.esm_file.models.keys())
        if self.esm_file.reaction_systems:
            systems.extend(self.esm_file.reaction_systems.keys())
        if self.esm_file.data_loaders:
            systems.extend(self.esm_file.data_loaders.keys())
        if self.esm_file.operators:
            systems.extend(self.esm_file.operators.keys())
        return systems

    def _system_exists(self, system_name: str) -> bool:
        """Check if a system exists."""
        return (
            (self.esm_file.models and system_name in self.esm_file.models) or
            (self.esm_file.reaction_systems and system_name in self.esm_file.reaction_systems) or
            (self.esm_file.data_loaders and system_name in self.esm_file.data_loaders) or
            (self.esm_file.operators and system_name in self.esm_file.operators)
        )

    def _variable_exists_in_system(self, var_name: str, system_name: str) -> bool:
        """Check if a variable exists in a system."""
        # Check models
        if self.esm_file.models and system_name in self.esm_file.models:
            model = self.esm_file.models[system_name]
            if model.variables and var_name in model.variables:
                return True

        # Check reaction systems
        if self.esm_file.reaction_systems and system_name in self.esm_file.reaction_systems:
            rsys = self.esm_file.reaction_systems[system_name]
            if rsys.species and var_name in rsys.species:
                return True
            if rsys.parameters and var_name in rsys.parameters:
                return True

        # Check data loaders (variables are in .variables dict)
        if self.esm_file.data_loaders and system_name in self.esm_file.data_loaders:
            loader = self.esm_file.data_loaders[system_name]
            if getattr(loader, 'variables', None) and var_name in loader.variables:
                return True

        return False

    def _resolve_variable_in_hierarchy(self, system_path: List[str], var_name: str) -> Tuple[bool, str]:
        """
        Resolve a variable in a hierarchical system path.

        Args:
            system_path: List of system names forming a path (e.g., ["ParentSystem", "SubsystemA", "DeepSubA"])
            var_name: The variable name to find

        Returns:
            Tuple of (found: bool, resolved_system_name: str)
        """
        if not system_path:
            return False, ""

        root_system_name = system_path[0]

        # Check if root system exists
        if not self._system_exists(root_system_name):
            return False, root_system_name

        # If it's just a single-level reference, use existing logic
        if len(system_path) == 1:
            if self._variable_exists_in_system(var_name, root_system_name):
                return True, root_system_name
            return False, root_system_name

        # Multi-level reference - traverse subsystem hierarchy
        # Start with the root system
        if self.esm_file.models and root_system_name in self.esm_file.models:
            current_system = self.esm_file.models[root_system_name]
            current_path = [root_system_name]

            # Traverse through subsystems
            for subsystem_name in system_path[1:]:
                if not hasattr(current_system, 'subsystems') or not current_system.subsystems:
                    return False, ".".join(current_path)

                if subsystem_name not in current_system.subsystems:
                    return False, ".".join(current_path)

                current_system = current_system.subsystems[subsystem_name]
                current_path.append(subsystem_name)

            # Check if variable exists in the final subsystem
            if current_system.variables and var_name in current_system.variables:
                return True, ".".join(current_path)

            return False, ".".join(current_path)

        # Check reaction systems (they also support subsystems)
        elif self.esm_file.reaction_systems and root_system_name in self.esm_file.reaction_systems:
            current_system = self.esm_file.reaction_systems[root_system_name]
            current_path = [root_system_name]

            # Traverse through subsystems
            for subsystem_name in system_path[1:]:
                if not hasattr(current_system, 'subsystems') or not current_system.subsystems:
                    return False, ".".join(current_path)

                if subsystem_name not in current_system.subsystems:
                    return False, ".".join(current_path)

                current_system = current_system.subsystems[subsystem_name]
                current_path.append(subsystem_name)

            # Check if variable exists in the final subsystem (species or parameters)
            if current_system.species and any(species.name == var_name for species in current_system.species):
                return True, ".".join(current_path)
            if current_system.parameters and any(param.name == var_name for param in current_system.parameters):
                return True, ".".join(current_path)

            return False, ".".join(current_path)

        return False, root_system_name