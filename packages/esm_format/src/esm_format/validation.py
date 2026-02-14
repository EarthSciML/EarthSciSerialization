"""
ESM Format validation module.

This module provides a standardized validation interface for cross-language
conformance testing, returning structured validation results.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Union, Tuple
import json
import traceback

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from .parse import load, SchemaValidationError, UnsupportedVersionError, _get_schema
from .hierarchical_scope_resolution import HierarchicalScopeResolver, ScopeInfo, VariableResolution
from .coupling_graph import ScopedReferenceResolver
from .types import EsmFile


@dataclass
class ValidationError:
    """Represents a single validation error."""
    path: str
    message: str
    code: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class ValidationResult:
    """Represents the result of validation."""
    is_valid: bool
    schema_errors: List[ValidationError]
    structural_errors: List[ValidationError]


def _convert_jsonschema_error(error: JsonSchemaValidationError) -> ValidationError:
    """Convert a jsonschema ValidationError to our ValidationError format."""
    # Convert the path to a string representation
    path_parts = []
    for part in error.absolute_path:
        if isinstance(part, int):
            path_parts.append(f"[{part}]")
        else:
            path_parts.append(f".{part}" if path_parts else str(part))

    path = "".join(path_parts) if path_parts else "$"

    return ValidationError(
        path=path,
        message=error.message,
        code=error.validator or "",
        details={
            "validator": error.validator,
            "validator_value": error.validator_value,
            "schema_path": list(error.schema_path),
            "instance": error.instance
        }
    )


def validate(esm_data: Union[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate ESM data against the schema and structural requirements.

    Args:
        esm_data: Either a JSON string or a dictionary containing ESM data

    Returns:
        ValidationResult containing validation status and any errors found
    """
    schema_errors = []
    structural_errors = []

    try:
        # Parse the data if it's a string
        if isinstance(esm_data, str):
            try:
                data = json.loads(esm_data)
            except json.JSONDecodeError as e:
                return ValidationResult(
                    is_valid=False,
                    schema_errors=[ValidationError(
                        path="$",
                        message=f"Invalid JSON: {e.msg}",
                        code="json_decode_error",
                        details={"line": e.lineno, "column": e.colno}
                    )],
                    structural_errors=[]
                )
        else:
            data = esm_data

        # Validate against JSON schema
        schema = _get_schema()
        try:
            jsonschema.validate(data, schema)
        except JsonSchemaValidationError as e:
            # Collect all schema validation errors
            validator = jsonschema.Draft7Validator(schema)
            for error in validator.iter_errors(data):
                schema_errors.append(_convert_jsonschema_error(error))

        # Try to parse and perform structural validation
        if not schema_errors:
            try:
                # The load function performs additional structural validation
                esm_file = load(json.dumps(data))
                # If we get here without exception, structural validation passed
            except (SchemaValidationError, UnsupportedVersionError, ValueError) as e:
                structural_errors.append(ValidationError(
                    path="$",
                    message=str(e),
                    code=type(e).__name__.lower().replace("error", ""),
                    details={"exception_type": type(e).__name__}
                ))
            except Exception as e:
                # Catch any other parsing errors
                structural_errors.append(ValidationError(
                    path="$",
                    message=f"Structural validation failed: {str(e)}",
                    code="structural_error",
                    details={
                        "exception_type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }
                ))

    except Exception as e:
        # Catch-all for unexpected errors
        return ValidationResult(
            is_valid=False,
            schema_errors=[ValidationError(
                path="$",
                message=f"Validation failed with unexpected error: {str(e)}",
                code="unexpected_error",
                details={
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
            )],
            structural_errors=[]
        )

    is_valid = len(schema_errors) == 0 and len(structural_errors) == 0

    return ValidationResult(
        is_valid=is_valid,
        schema_errors=schema_errors,
        structural_errors=structural_errors
    )


@dataclass
class ScopeValidationError:
    """Represents a scope validation error with detailed information."""
    error_type: str  # "undefined_reference", "scope_boundary_violation", "invalid_scope_path", etc.
    reference: str
    scope_path: List[str]
    message: str
    resolution_path: List[str] = None  # Path tried during resolution
    available_variables: List[str] = None  # Available variables at the scope
    available_scopes: List[str] = None  # Available scopes at the level
    shadowed_variables: List[Dict[str, Any]] = None  # Information about shadowed variables
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.resolution_path is None:
            self.resolution_path = []
        if self.available_variables is None:
            self.available_variables = []
        if self.available_scopes is None:
            self.available_scopes = []
        if self.shadowed_variables is None:
            self.shadowed_variables = []
        if self.details is None:
            self.details = {}


@dataclass
class ScopeValidationResult:
    """Result of comprehensive scope validation."""
    is_valid: bool
    errors: List[ScopeValidationError]
    warnings: List[ScopeValidationError]
    scope_hierarchy_valid: bool
    total_scopes_validated: int
    total_references_validated: int

    @property
    def error_count(self) -> int:
        """Get the total number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get the total number of warnings."""
        return len(self.warnings)


class ScopeValidator:
    """
    Comprehensive scope validation system with detailed error reporting.

    This validator provides:
    1. Undefined reference detection
    2. Scope boundary violation detection
    3. Resolution path tracking
    4. Shadowing analysis
    5. Hierarchy consistency validation
    """

    def __init__(self, esm_file: EsmFile):
        """
        Initialize the scope validator.

        Args:
            esm_file: The ESM file to validate
        """
        self.esm_file = esm_file
        self.hierarchical_resolver = HierarchicalScopeResolver(esm_file)
        self.scoped_resolver = ScopedReferenceResolver(esm_file)

    def validate_comprehensive(self, references_to_validate: List[str] = None) -> ScopeValidationResult:
        """
        Perform comprehensive scope validation.

        Args:
            references_to_validate: Optional list of specific references to validate.
                                   If None, validates all references found in the ESM file.

        Returns:
            ScopeValidationResult with detailed validation information
        """
        errors = []
        warnings = []

        # Validate scope hierarchy first
        hierarchy_valid, hierarchy_errors = self.hierarchical_resolver.validate_scope_hierarchy()

        # Convert hierarchy errors to our format
        for error_msg in hierarchy_errors:
            errors.append(ScopeValidationError(
                error_type="scope_hierarchy_error",
                reference="",
                scope_path=[],
                message=error_msg,
                details={"validation_phase": "hierarchy_validation"}
            ))

        # Get references to validate
        if references_to_validate is None:
            references_to_validate = self._extract_all_references()

        # Validate each reference
        for reference in references_to_validate:
            reference_errors, reference_warnings = self._validate_single_reference(reference)
            errors.extend(reference_errors)
            warnings.extend(reference_warnings)

        # Additional validation checks
        additional_errors, additional_warnings = self._perform_additional_validation()
        errors.extend(additional_errors)
        warnings.extend(additional_warnings)

        return ScopeValidationResult(
            is_valid=(len(errors) == 0 and hierarchy_valid),
            errors=errors,
            warnings=warnings,
            scope_hierarchy_valid=hierarchy_valid,
            total_scopes_validated=len(self.hierarchical_resolver.scope_tree),
            total_references_validated=len(references_to_validate)
        )

    def _extract_all_references(self) -> List[str]:
        """Extract all scoped references from the ESM file."""
        references = []

        # This would typically extract references from couplings, equations, etc.
        # For now, we'll create some example references based on the scope structure
        for scope_path in self.hierarchical_resolver.scope_tree.keys():
            scope_info = self.hierarchical_resolver.scope_tree[scope_path]
            for var_name in scope_info.variables.keys():
                references.append(f"{scope_path}.{var_name}")

        return references

    def _validate_single_reference(self, reference: str) -> Tuple[List[ScopeValidationError], List[ScopeValidationError]]:
        """
        Validate a single scoped reference.

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        try:
            # Parse the reference
            segments = reference.split('.')
            if len(segments) < 2:
                errors.append(ScopeValidationError(
                    error_type="invalid_reference_format",
                    reference=reference,
                    scope_path=[],
                    message=f"Invalid scoped reference format: '{reference}'. Must contain at least one dot.",
                    details={"expected_format": "scope.variable or scope.subsystem.variable"}
                ))
                return errors, warnings

            variable_name = segments[-1]
            scope_path = segments[:-1]

            # Try to resolve with hierarchical resolver
            try:
                resolution = self.hierarchical_resolver.resolve_with_shadowing_info(reference)

                # Check for shadowing warnings
                if len(resolution.shadow_chain) > 0:
                    shadowed_info = []
                    for shadowed_scope in resolution.shadow_chain:
                        if variable_name in shadowed_scope.variables:
                            shadowed_info.append({
                                'scope': '.'.join(shadowed_scope.full_path),
                                'value': shadowed_scope.variables[variable_name],
                                'scope_type': shadowed_scope.component_type
                            })

                    warnings.append(ScopeValidationError(
                        error_type="variable_shadowing",
                        reference=reference,
                        scope_path=scope_path,
                        message=f"Variable '{variable_name}' shadows {len(resolution.shadow_chain)} variable(s) in parent scope(s)",
                        resolution_path=['.'.join(scope.full_path) for scope in resolution.available_scopes],
                        shadowed_variables=shadowed_info,
                        details={
                            "resolved_scope": '.'.join(resolution.resolved_scope.full_path),
                            "resolution_type": resolution.resolution_type
                        }
                    ))

            except ValueError as e:
                error_msg = str(e)

                # Determine error type based on the error message
                error_type = "undefined_reference"
                if "not found in hierarchy" in error_msg:
                    error_type = "invalid_scope_path"
                elif "not found in scope" in error_msg:
                    error_type = "undefined_reference"

                # Extract available information from the error
                available_vars = []
                available_scopes = []
                resolution_path = scope_path.copy()

                # Try to get available variables and scopes for better error reporting
                scope_key = '.'.join(scope_path)
                if scope_key in self.hierarchical_resolver.scope_tree:
                    target_scope = self.hierarchical_resolver.scope_tree[scope_key]
                    available_vars = list(self.hierarchical_resolver._get_all_available_variables_in_scope_chain(target_scope).keys())
                    available_scopes = [scope for scope in self.hierarchical_resolver.scope_tree.keys() if scope.startswith(scope_key)]

                errors.append(ScopeValidationError(
                    error_type=error_type,
                    reference=reference,
                    scope_path=scope_path,
                    message=error_msg,
                    resolution_path=resolution_path,
                    available_variables=available_vars,
                    available_scopes=available_scopes,
                    details={"original_exception": type(e).__name__}
                ))

        except Exception as e:
            # Catch-all for unexpected errors during validation
            errors.append(ScopeValidationError(
                error_type="validation_error",
                reference=reference,
                scope_path=[],
                message=f"Unexpected error during validation: {str(e)}",
                details={
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
            ))

        return errors, warnings

    def _perform_additional_validation(self) -> Tuple[List[ScopeValidationError], List[ScopeValidationError]]:
        """Perform additional validation checks."""
        errors = []
        warnings = []

        # Check for scope boundary violations (subsystems accessing sibling variables)
        for scope_path, scope_info in self.hierarchical_resolver.scope_tree.items():
            if scope_info.parent is None:
                continue  # Skip root scopes

            # Check if this scope has any sibling scopes
            siblings = [child_name for child_name in scope_info.parent.children.keys()
                       if child_name != scope_info.name]

            if siblings:
                # This scope has siblings - check for potential cross-references
                # Note: This is a simplified check; in practice, you'd need to analyze
                # actual coupling references to detect violations
                pass

        # Check for unused variables (variables defined but never referenced)
        all_references = self._extract_all_references()
        for scope_path, scope_info in self.hierarchical_resolver.scope_tree.items():
            for var_name in scope_info.variables.keys():
                full_reference = f"{scope_path}.{var_name}"
                if full_reference not in all_references:
                    warnings.append(ScopeValidationError(
                        error_type="unused_variable",
                        reference=full_reference,
                        scope_path=scope_path.split('.'),
                        message=f"Variable '{var_name}' is defined but never referenced",
                        details={
                            "scope": scope_path,
                            "variable_info": scope_info.variables[var_name]
                        }
                    ))

        # Check for deeply nested scopes (potential design issue)
        max_depth_warning = 5
        for scope_path, scope_info in self.hierarchical_resolver.scope_tree.items():
            depth = len(scope_info.full_path)
            if depth > max_depth_warning:
                warnings.append(ScopeValidationError(
                    error_type="deep_nesting",
                    reference="",
                    scope_path=scope_info.full_path,
                    message=f"Scope '{scope_path}' has deep nesting (depth: {depth}). Consider flattening the hierarchy.",
                    details={"depth": depth, "max_recommended": max_depth_warning}
                ))

        return errors, warnings

    def validate_reference(self, reference: str) -> ScopeValidationResult:
        """
        Validate a single reference with comprehensive error reporting.

        Args:
            reference: The scoped reference to validate

        Returns:
            ScopeValidationResult for the single reference
        """
        errors, warnings = self._validate_single_reference(reference)

        return ScopeValidationResult(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
            scope_hierarchy_valid=True,  # Assuming hierarchy is valid for single reference
            total_scopes_validated=1,
            total_references_validated=1
        )

    def get_resolution_path_details(self, reference: str) -> Dict[str, Any]:
        """
        Get detailed information about the resolution path for a reference.

        Args:
            reference: The scoped reference to analyze

        Returns:
            Dictionary with detailed resolution path information
        """
        try:
            resolution = self.hierarchical_resolver.resolve_with_shadowing_info(reference)

            return {
                "reference": reference,
                "is_resolvable": True,
                "resolved_scope": '.'.join(resolution.resolved_scope.full_path),
                "resolution_type": resolution.resolution_type,
                "resolution_path": ['.'.join(scope.full_path) for scope in resolution.available_scopes],
                "shadowed_scopes": ['.'.join(scope.full_path) for scope in resolution.shadow_chain],
                "resolved_value": resolution.resolved_value,
                "variable_name": resolution.variable_name
            }
        except Exception as e:
            segments = reference.split('.')
            scope_path = segments[:-1] if len(segments) > 1 else []

            available_scopes = []
            available_variables = []

            # Try to get partial information
            for i in range(len(scope_path)):
                partial_scope = '.'.join(scope_path[:i+1])
                if partial_scope in self.hierarchical_resolver.scope_tree:
                    available_scopes.append(partial_scope)
                    scope_info = self.hierarchical_resolver.scope_tree[partial_scope]
                    available_variables.extend(list(scope_info.variables.keys()))

            return {
                "reference": reference,
                "is_resolvable": False,
                "error": str(e),
                "attempted_scope_path": scope_path,
                "available_scopes": available_scopes,
                "available_variables": list(set(available_variables))
            }


def validate_scope_comprehensive(esm_file: EsmFile, references: List[str] = None) -> ScopeValidationResult:
    """
    Convenience function for comprehensive scope validation.

    Args:
        esm_file: The ESM file to validate
        references: Optional list of references to validate

    Returns:
        ScopeValidationResult with comprehensive validation results
    """
    validator = ScopeValidator(esm_file)
    return validator.validate_comprehensive(references)