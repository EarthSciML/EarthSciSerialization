"""
ESM Format validation module.

This module provides a standardized validation interface for cross-language
conformance testing, returning structured validation results.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Union
import json
import traceback

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from .parse import load, SchemaValidationError, UnsupportedVersionError, _get_schema


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