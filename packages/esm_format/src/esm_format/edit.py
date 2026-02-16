"""
Editing operations for ESM Format structures.

Provides functions to modify ESM files, models, reaction systems, and their
components in a safe and consistent manner.
"""

from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field, replace
from copy import deepcopy

try:
    from .types import (
        EsmFile, Model, ReactionSystem, ModelVariable, Species, Parameter,
        Reaction, Equation, Expr, ExprNode, AffectEquation
    )
    from .validation import validate, ValidationResult
except ImportError:
    # For direct imports when testing
    from types import (
        EsmFile, Model, ReactionSystem, ModelVariable, Species, Parameter,
        Reaction, Equation, Expr, ExprNode, AffectEquation
    )


@dataclass
class EditOperation:
    """Represents an editing operation that can be applied to an ESM structure."""
    operation_type: str  # 'add', 'remove', 'modify', 'rename'
    target_type: str     # 'model', 'reaction_system', 'variable', 'equation', etc.
    target_id: str       # identifier for the target
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EditResult:
    """Result of an editing operation."""
    success: bool
    modified_object: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None


class ESMEditor:
    """Editor for ESM format structures with validation and safety checks."""

    def __init__(self, validate_after_edit: bool = True):
        """
        Initialize the ESM editor.

        Args:
            validate_after_edit: Whether to validate structures after editing
        """
        self.validate_after_edit = validate_after_edit

    def apply_operation(self, target: Union[EsmFile, Model, ReactionSystem],
                       operation: EditOperation) -> EditResult:
        """
        Apply an editing operation to a target structure.

        Args:
            target: The structure to edit
            operation: The editing operation to apply

        Returns:
            EditResult indicating success/failure and any issues
        """
        try:
            # Make a deep copy to avoid modifying the original
            modified = deepcopy(target)

            if isinstance(target, EsmFile):
                result = self._apply_esm_file_operation(modified, operation)
            elif isinstance(target, Model):
                result = self._apply_model_operation(modified, operation)
            elif isinstance(target, ReactionSystem):
                result = self._apply_reaction_system_operation(modified, operation)
            else:
                return EditResult(
                    success=False,
                    errors=[f"Unsupported target type: {type(target)}"]
                )

            if result.success and self.validate_after_edit:
                try:
                    validation_result = validate(result.modified_object)
                    result.validation_result = validation_result
                    if not validation_result.is_valid:
                        result.warnings.append("Modified structure has validation issues")
                except Exception as e:
                    result.warnings.append(f"Validation failed: {e}")

            return result

        except Exception as e:
            return EditResult(
                success=False,
                errors=[f"Edit operation failed: {e}"]
            )

    def add_model(self, esm_file: EsmFile, model: Model) -> EditResult:
        """Add a model to an ESM file."""
        operation = EditOperation(
            operation_type="add",
            target_type="model",
            target_id=model.name,
            data={"model": model}
        )
        return self.apply_operation(esm_file, operation)

    def remove_model(self, esm_file: EsmFile, model_name: str) -> EditResult:
        """Remove a model from an ESM file."""
        operation = EditOperation(
            operation_type="remove",
            target_type="model",
            target_id=model_name
        )
        return self.apply_operation(esm_file, operation)

    def add_variable(self, model: Model, var_name: str, var_info: ModelVariable) -> EditResult:
        """Add a variable to a model."""
        operation = EditOperation(
            operation_type="add",
            target_type="variable",
            target_id=var_name,
            data={"variable": var_info}
        )
        return self.apply_operation(model, operation)

    def modify_variable(self, model: Model, var_name: str, **updates) -> EditResult:
        """Modify a variable in a model."""
        operation = EditOperation(
            operation_type="modify",
            target_type="variable",
            target_id=var_name,
            data=updates
        )
        return self.apply_operation(model, operation)

    def add_equation(self, model: Model, equation: Equation) -> EditResult:
        """Add an equation to a model."""
        operation = EditOperation(
            operation_type="add",
            target_type="equation",
            target_id=f"eq_{len(model.equations) if model.equations else 0}",
            data={"equation": equation}
        )
        return self.apply_operation(model, operation)

    def add_species(self, reaction_system: ReactionSystem, species: Species) -> EditResult:
        """Add a species to a reaction system."""
        operation = EditOperation(
            operation_type="add",
            target_type="species",
            target_id=species.name,
            data={"species": species}
        )
        return self.apply_operation(reaction_system, operation)

    def add_reaction(self, reaction_system: ReactionSystem, reaction: Reaction) -> EditResult:
        """Add a reaction to a reaction system."""
        operation = EditOperation(
            operation_type="add",
            target_type="reaction",
            target_id=reaction.name,
            data={"reaction": reaction}
        )
        return self.apply_operation(reaction_system, operation)

    def substitute_in_expression(self, expr: Expr, substitutions: Dict[str, Expr]) -> Expr:
        """
        Substitute variables in an expression.

        Args:
            expr: The expression to modify
            substitutions: Dict mapping variable names to replacement expressions

        Returns:
            Modified expression with substitutions applied
        """
        if isinstance(expr, str):
            return substitutions.get(expr, expr)

        elif isinstance(expr, (int, float)):
            return expr

        elif isinstance(expr, ExprNode):
            # Recursively substitute in arguments
            new_args = [self.substitute_in_expression(arg, substitutions) for arg in expr.args]
            return replace(expr, args=new_args)

        return expr

    def rename_variable(self, target: Union[Model, ReactionSystem], old_name: str, new_name: str) -> EditResult:
        """
        Rename a variable throughout a model or reaction system.

        Args:
            target: The model or reaction system to modify
            old_name: Current variable name
            new_name: New variable name

        Returns:
            EditResult with the modified structure
        """
        operation = EditOperation(
            operation_type="rename",
            target_type="variable",
            target_id=old_name,
            data={"new_name": new_name}
        )
        return self.apply_operation(target, operation)

    def _apply_esm_file_operation(self, esm_file: EsmFile, operation: EditOperation) -> EditResult:
        """Apply an operation to an ESM file."""
        if operation.target_type == "model":
            if operation.operation_type == "add":
                model = operation.data.get("model")
                if not model:
                    return EditResult(success=False, errors=["No model data provided"])

                if not esm_file.models:
                    esm_file.models = []

                # Check for duplicate names
                if any(m.name == model.name for m in esm_file.models):
                    return EditResult(success=False, errors=[f"Model '{model.name}' already exists"])

                esm_file.models.append(model)
                return EditResult(success=True, modified_object=esm_file)

            elif operation.operation_type == "remove":
                if not esm_file.models:
                    return EditResult(success=False, errors=["No models to remove"])

                original_count = len(esm_file.models)
                esm_file.models = [m for m in esm_file.models if m.name != operation.target_id]

                if len(esm_file.models) == original_count:
                    return EditResult(success=False, errors=[f"Model '{operation.target_id}' not found"])

                return EditResult(success=True, modified_object=esm_file)

        elif operation.target_type == "reaction_system":
            if operation.operation_type == "add":
                rs = operation.data.get("reaction_system")
                if not rs:
                    return EditResult(success=False, errors=["No reaction system data provided"])

                if not esm_file.reaction_systems:
                    esm_file.reaction_systems = []

                # Check for duplicate names
                if any(r.name == rs.name for r in esm_file.reaction_systems):
                    return EditResult(success=False, errors=[f"Reaction system '{rs.name}' already exists"])

                esm_file.reaction_systems.append(rs)
                return EditResult(success=True, modified_object=esm_file)

            elif operation.operation_type == "remove":
                if not esm_file.reaction_systems:
                    return EditResult(success=False, errors=["No reaction systems to remove"])

                original_count = len(esm_file.reaction_systems)
                esm_file.reaction_systems = [r for r in esm_file.reaction_systems if r.name != operation.target_id]

                if len(esm_file.reaction_systems) == original_count:
                    return EditResult(success=False, errors=[f"Reaction system '{operation.target_id}' not found"])

                return EditResult(success=True, modified_object=esm_file)

        return EditResult(success=False, errors=[f"Unsupported operation: {operation.operation_type} on {operation.target_type}"])

    def _apply_model_operation(self, model: Model, operation: EditOperation) -> EditResult:
        """Apply an operation to a model."""
        if operation.target_type == "variable":
            if operation.operation_type == "add":
                variable = operation.data.get("variable")
                if not variable:
                    return EditResult(success=False, errors=["No variable data provided"])

                if not model.variables:
                    model.variables = {}

                if operation.target_id in model.variables:
                    return EditResult(success=False, errors=[f"Variable '{operation.target_id}' already exists"])

                model.variables[operation.target_id] = variable
                return EditResult(success=True, modified_object=model)

            elif operation.operation_type == "remove":
                if not model.variables or operation.target_id not in model.variables:
                    return EditResult(success=False, errors=[f"Variable '{operation.target_id}' not found"])

                del model.variables[operation.target_id]
                return EditResult(success=True, modified_object=model)

            elif operation.operation_type == "modify":
                if not model.variables or operation.target_id not in model.variables:
                    return EditResult(success=False, errors=[f"Variable '{operation.target_id}' not found"])

                # Apply updates to the variable
                current_var = model.variables[operation.target_id]
                for key, value in operation.data.items():
                    if hasattr(current_var, key):
                        setattr(current_var, key, value)

                return EditResult(success=True, modified_object=model)

            elif operation.operation_type == "rename":
                new_name = operation.data.get("new_name")
                if not new_name:
                    return EditResult(success=False, errors=["No new name provided"])

                if not model.variables or operation.target_id not in model.variables:
                    return EditResult(success=False, errors=[f"Variable '{operation.target_id}' not found"])

                if new_name in model.variables:
                    return EditResult(success=False, errors=[f"Variable '{new_name}' already exists"])

                # Rename the variable
                var_info = model.variables.pop(operation.target_id)
                model.variables[new_name] = var_info

                # Update references in equations
                if model.equations:
                    substitutions = {operation.target_id: new_name}
                    for i, equation in enumerate(model.equations):
                        new_lhs = self.substitute_in_expression(equation.lhs, substitutions)
                        new_rhs = self.substitute_in_expression(equation.rhs, substitutions)
                        model.equations[i] = replace(equation, lhs=new_lhs, rhs=new_rhs)

                return EditResult(success=True, modified_object=model)

        elif operation.target_type == "equation":
            if operation.operation_type == "add":
                equation = operation.data.get("equation")
                if not equation:
                    return EditResult(success=False, errors=["No equation data provided"])

                if not model.equations:
                    model.equations = []

                model.equations.append(equation)
                return EditResult(success=True, modified_object=model)

        return EditResult(success=False, errors=[f"Unsupported operation: {operation.operation_type} on {operation.target_type}"])

    def _apply_reaction_system_operation(self, rs: ReactionSystem, operation: EditOperation) -> EditResult:
        """Apply an operation to a reaction system."""
        if operation.target_type == "species":
            if operation.operation_type == "add":
                species = operation.data.get("species")
                if not species:
                    return EditResult(success=False, errors=["No species data provided"])

                if not rs.species:
                    rs.species = []

                # Check for duplicate names
                if any(s.name == species.name for s in rs.species):
                    return EditResult(success=False, errors=[f"Species '{species.name}' already exists"])

                rs.species.append(species)
                return EditResult(success=True, modified_object=rs)

        elif operation.target_type == "reaction":
            if operation.operation_type == "add":
                reaction = operation.data.get("reaction")
                if not reaction:
                    return EditResult(success=False, errors=["No reaction data provided"])

                if not rs.reactions:
                    rs.reactions = []

                # Check for duplicate names
                if any(r.name == reaction.name for r in rs.reactions):
                    return EditResult(success=False, errors=[f"Reaction '{reaction.name}' already exists"])

                rs.reactions.append(reaction)
                return EditResult(success=True, modified_object=rs)

        elif operation.target_type == "parameter":
            if operation.operation_type == "add":
                parameter = operation.data.get("parameter")
                if not parameter:
                    return EditResult(success=False, errors=["No parameter data provided"])

                if not rs.parameters:
                    rs.parameters = []

                # Check for duplicate names
                if any(p.name == parameter.name for p in rs.parameters):
                    return EditResult(success=False, errors=[f"Parameter '{parameter.name}' already exists"])

                rs.parameters.append(parameter)
                return EditResult(success=True, modified_object=rs)

        return EditResult(success=False, errors=[f"Unsupported operation: {operation.operation_type} on {operation.target_type}"])


# Convenience functions
def add_model_to_file(esm_file: EsmFile, model: Model, validate: bool = True) -> EditResult:
    """Add a model to an ESM file."""
    editor = ESMEditor(validate_after_edit=validate)
    return editor.add_model(esm_file, model)


def add_variable_to_model(model: Model, var_name: str, var_info: ModelVariable, validate: bool = True) -> EditResult:
    """Add a variable to a model."""
    editor = ESMEditor(validate_after_edit=validate)
    return editor.add_variable(model, var_name, var_info)


def rename_variable_in_model(model: Model, old_name: str, new_name: str, validate: bool = True) -> EditResult:
    """Rename a variable in a model."""
    editor = ESMEditor(validate_after_edit=validate)
    return editor.rename_variable(model, old_name, new_name)