"""
Validation system for custom operator registration in ESM Format.

This module provides comprehensive validation for operator implementations including:
- Signature validation to ensure operators implement required methods
- Documentation requirements validation
- Runtime type checking for inputs and outputs
- Metadata validation
"""

import inspect
import warnings
from typing import Type, Dict, Any, List, Optional, Callable, Union, get_type_hints
from dataclasses import dataclass
from enum import Enum

from .esm_types import Operator, OperatorType


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # Fail registration on any validation error
    WARNING = "warning"    # Issue warnings but allow registration
    PERMISSIVE = "permissive"  # Minimal validation only


@dataclass
class ValidationResult:
    """Result of operator validation."""
    passed: bool
    errors: List[str]
    warnings: List[str]
    info: Dict[str, Any]


@dataclass
class OperatorRequirements:
    """Requirements for operator implementations."""
    required_methods: List[str]
    required_docstring: bool = True
    required_metadata: Optional[Dict[str, Any]] = None
    type_checking: bool = True
    signature_validation: bool = True


class OperatorValidator:
    """
    Validator for operator implementations.

    Validates that custom operators meet interface requirements,
    have proper documentation, and support runtime type checking.
    """

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.WARNING):
        """
        Initialize the validator.

        Args:
            validation_level: Level of validation strictness to apply
        """
        self.validation_level = validation_level

        # Define requirements for different operator types
        self._type_requirements = {
            OperatorType.ARITHMETIC: OperatorRequirements(
                required_methods=["evaluate"],
                required_docstring=True,
                type_checking=True
            ),
            OperatorType.LOGICAL: OperatorRequirements(
                required_methods=["evaluate"],
                required_docstring=True,
                type_checking=True
            ),
            OperatorType.INTERPOLATION: OperatorRequirements(
                required_methods=["interpolate", "__init__"],
                required_docstring=True,
                type_checking=True
            ),
            OperatorType.DIFFERENTIATION: OperatorRequirements(
                required_methods=["differentiate", "__init__"],
                required_docstring=True,
                type_checking=True
            ),
            OperatorType.INTEGRATION: OperatorRequirements(
                required_methods=["integrate", "__init__"],
                required_docstring=True,
                type_checking=True
            ),
            OperatorType.STATISTICAL: OperatorRequirements(
                required_methods=["compute", "__init__"],
                required_docstring=True,
                type_checking=True
            ),
            OperatorType.FILTERING: OperatorRequirements(
                required_methods=["filter", "__init__"],
                required_docstring=True,
                type_checking=True
            ),
            OperatorType.TRANSFORMATION: OperatorRequirements(
                required_methods=["transform", "__init__"],
                required_docstring=True,
                type_checking=True
            ),
        }

    def validate_operator(
        self,
        operator_class: Type,
        operator_type: OperatorType,
        name: str
    ) -> ValidationResult:
        """
        Validate an operator implementation.

        Args:
            operator_class: The operator class to validate
            operator_type: Expected operator type
            name: Name of the operator

        Returns:
            ValidationResult with detailed validation information
        """
        errors = []
        warnings = []
        info = {}

        requirements = self._type_requirements.get(operator_type)
        if not requirements:
            errors.append(f"Unknown operator type: {operator_type}")
            return ValidationResult(False, errors, warnings, info)

        # 1. Signature validation
        signature_result = self._validate_signature(operator_class, requirements, name)
        errors.extend(signature_result.errors)
        warnings.extend(signature_result.warnings)
        info.update(signature_result.info)

        # 2. Documentation validation
        doc_result = self._validate_documentation(operator_class, requirements, name)
        errors.extend(doc_result.errors)
        warnings.extend(doc_result.warnings)
        info.update(doc_result.info)

        # 3. Constructor validation
        init_result = self._validate_constructor(operator_class, name)
        errors.extend(init_result.errors)
        warnings.extend(init_result.warnings)
        info.update(init_result.info)

        # 4. Type annotation validation
        if requirements.type_checking:
            type_result = self._validate_type_annotations(operator_class, requirements, name)
            errors.extend(type_result.errors)
            warnings.extend(type_result.warnings)
            info.update(type_result.info)

        passed = len(errors) == 0
        return ValidationResult(passed, errors, warnings, info)

    def _validate_signature(
        self,
        operator_class: Type,
        requirements: OperatorRequirements,
        name: str
    ) -> ValidationResult:
        """Validate operator method signatures."""
        errors = []
        warnings = []
        info = {}

        if not requirements.signature_validation:
            return ValidationResult(True, errors, warnings, info)

        # Check required methods exist
        missing_methods = []
        method_signatures = {}

        for method_name in requirements.required_methods:
            if not hasattr(operator_class, method_name):
                missing_methods.append(method_name)
            else:
                method = getattr(operator_class, method_name)
                if callable(method):
                    try:
                        sig = inspect.signature(method)
                        method_signatures[method_name] = sig
                        info[f"{method_name}_signature"] = str(sig)
                    except (ValueError, TypeError) as e:
                        warnings.append(f"Cannot inspect signature of {method_name}: {e}")

        if missing_methods:
            errors.append(f"Operator {name} missing required methods: {missing_methods}")

        # Validate __init__ signature if present
        if "__init__" in method_signatures:
            init_sig = method_signatures["__init__"]
            params = list(init_sig.parameters.keys())

            if len(params) < 2:  # self + config
                errors.append(f"Operator {name} __init__ must accept at least 'self' and 'config' parameters")
            elif params[1] != "config":
                warnings.append(f"Operator {name} __init__ second parameter should be named 'config', got '{params[1]}'")

            # Check for type annotations on config parameter
            if "config" in init_sig.parameters:
                config_param = init_sig.parameters["config"]
                if config_param.annotation == inspect.Parameter.empty:
                    warnings.append(f"Operator {name} __init__ 'config' parameter should have type annotation")

        info["method_signatures"] = method_signatures

        passed = len(errors) == 0
        return ValidationResult(passed, errors, warnings, info)

    def _validate_documentation(
        self,
        operator_class: Type,
        requirements: OperatorRequirements,
        name: str
    ) -> ValidationResult:
        """Validate operator documentation."""
        errors = []
        warnings = []
        info = {}

        if not requirements.required_docstring:
            return ValidationResult(True, errors, warnings, info)

        # Check class docstring
        class_doc = inspect.getdoc(operator_class)
        if not class_doc:
            errors.append(f"Operator {name} class must have a docstring")
        else:
            info["class_docstring"] = class_doc

            # Check docstring quality
            if len(class_doc.strip()) < 20:
                warnings.append(f"Operator {name} docstring is very short, consider adding more detail")

            # Check for common docstring sections
            doc_lower = class_doc.lower()
            expected_sections = ["args", "returns", "raises"]
            missing_sections = [s for s in expected_sections if s not in doc_lower]
            if missing_sections:
                warnings.append(f"Operator {name} docstring missing recommended sections: {missing_sections}")

        # Check method docstrings
        method_docs = {}
        for method_name in requirements.required_methods:
            if hasattr(operator_class, method_name):
                method = getattr(operator_class, method_name)
                method_doc = inspect.getdoc(method)
                method_docs[method_name] = method_doc

                if not method_doc:
                    warnings.append(f"Operator {name} method '{method_name}' should have a docstring")

        info["method_docstrings"] = method_docs

        passed = len(errors) == 0
        return ValidationResult(passed, errors, warnings, info)

    def _validate_constructor(
        self,
        operator_class: Type,
        name: str
    ) -> ValidationResult:
        """Validate operator constructor."""
        errors = []
        warnings = []
        info = {}

        # Try to inspect the constructor
        try:
            init_method = getattr(operator_class, "__init__")
            sig = inspect.signature(init_method)

            # Check if it can be called with an Operator config
            params = list(sig.parameters.keys())
            if len(params) < 2:
                errors.append(f"Operator {name} constructor must accept a config parameter")
            else:
                # Test parameter types
                config_param = sig.parameters.get("config") or sig.parameters.get(params[1])
                if config_param and config_param.annotation != inspect.Parameter.empty:
                    info["config_param_annotation"] = config_param.annotation

        except Exception as e:
            warnings.append(f"Cannot inspect constructor for {name}: {e}")

        passed = len(errors) == 0
        return ValidationResult(passed, errors, warnings, info)

    def _validate_type_annotations(
        self,
        operator_class: Type,
        requirements: OperatorRequirements,
        name: str
    ) -> ValidationResult:
        """Validate type annotations on operator methods."""
        errors = []
        warnings = []
        info = {}

        try:
            # Get type hints for the class
            type_hints = get_type_hints(operator_class)
            info["class_type_hints"] = {k: str(v) for k, v in type_hints.items()}
        except Exception as e:
            warnings.append(f"Cannot get type hints for {name}: {e}")

        # Check type annotations on methods
        method_annotations = {}
        for method_name in requirements.required_methods:
            if hasattr(operator_class, method_name):
                method = getattr(operator_class, method_name)
                try:
                    method_hints = get_type_hints(method)
                    method_annotations[method_name] = {k: str(v) for k, v in method_hints.items()}

                    if not method_hints:
                        warnings.append(f"Method {name}.{method_name} has no type annotations")
                except Exception as e:
                    warnings.append(f"Cannot get type hints for {name}.{method_name}: {e}")

        info["method_type_annotations"] = method_annotations

        passed = len(errors) == 0
        return ValidationResult(passed, errors, warnings, info)

    def validate_runtime_types(
        self,
        operator_instance: Any,
        method_name: str,
        args: tuple,
        kwargs: dict,
        expected_input_types: Optional[List[type]] = None,
        expected_output_type: Optional[type] = None
    ) -> ValidationResult:
        """
        Validate types at runtime for operator method calls.

        Args:
            operator_instance: Instance of the operator
            method_name: Name of the method being called
            args: Positional arguments passed to method
            kwargs: Keyword arguments passed to method
            expected_input_types: Expected types for input arguments
            expected_output_type: Expected type for return value

        Returns:
            ValidationResult with runtime type validation info
        """
        errors = []
        warnings = []
        info = {}

        # Validate input types
        if expected_input_types:
            for i, (arg, expected_type) in enumerate(zip(args, expected_input_types)):
                if not isinstance(arg, expected_type):
                    errors.append(
                        f"Argument {i} to {method_name}: expected {expected_type.__name__}, "
                        f"got {type(arg).__name__}"
                    )

        # Get method for validation
        if not hasattr(operator_instance, method_name):
            errors.append(f"Operator does not have method {method_name}")
            return ValidationResult(False, errors, warnings, info)

        method = getattr(operator_instance, method_name)

        # Try to call the method and validate output type
        try:
            result = method(*args, **kwargs)

            if expected_output_type and not isinstance(result, expected_output_type):
                warnings.append(
                    f"Return value from {method_name}: expected {expected_output_type.__name__}, "
                    f"got {type(result).__name__}"
                )

            info["return_type"] = type(result).__name__
            info["return_value_sample"] = str(result)[:100] if result is not None else "None"

        except Exception as e:
            errors.append(f"Runtime error calling {method_name}: {e}")

        passed = len(errors) == 0
        return ValidationResult(passed, errors, warnings, info)

    def should_allow_registration(self, validation_result: ValidationResult) -> bool:
        """
        Determine if operator should be allowed to register based on validation result.

        Args:
            validation_result: Result from validate_operator

        Returns:
            True if registration should be allowed
        """
        if self.validation_level == ValidationLevel.PERMISSIVE:
            return True
        elif self.validation_level == ValidationLevel.STRICT:
            return validation_result.passed
        else:  # WARNING
            # Allow registration but issue warnings
            for warning in validation_result.warnings:
                warnings.warn(f"Operator validation warning: {warning}", UserWarning)
            return len(validation_result.errors) == 0


# Global validator instance
_global_validator = OperatorValidator()


def get_validator() -> OperatorValidator:
    """Get the global operator validator instance."""
    return _global_validator


def set_validation_level(level: ValidationLevel) -> None:
    """
    Set the global validation level.

    Args:
        level: Validation level to set
    """
    global _global_validator
    _global_validator.validation_level = level


def validate_operator(
    operator_class: Type,
    operator_type: OperatorType,
    name: str
) -> ValidationResult:
    """
    Validate an operator using the global validator.

    Args:
        operator_class: The operator class to validate
        operator_type: Expected operator type
        name: Name of the operator

    Returns:
        ValidationResult with detailed validation information
    """
    return _global_validator.validate_operator(operator_class, operator_type, name)


def validate_runtime_types(
    operator_instance: Any,
    method_name: str,
    args: tuple,
    kwargs: dict,
    expected_input_types: Optional[List[type]] = None,
    expected_output_type: Optional[type] = None
) -> ValidationResult:
    """
    Validate types at runtime using the global validator.

    Args:
        operator_instance: Instance of the operator
        method_name: Name of the method being called
        args: Positional arguments passed to method
        kwargs: Keyword arguments passed to method
        expected_input_types: Expected types for input arguments
        expected_output_type: Expected type for return value

    Returns:
        ValidationResult with runtime type validation info
    """
    return _global_validator.validate_runtime_types(
        operator_instance, method_name, args, kwargs,
        expected_input_types, expected_output_type
    )