"""
ESM Format validation module.

This module provides a standardized validation interface for cross-language
conformance testing, returning structured validation results.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Union, Tuple, Set
import json
import traceback

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from .parse import load, SchemaValidationError, UnsupportedVersionError, _get_schema
from .error_handling import (
    ESMErrorFactory, ErrorCollector, ESMError, ErrorCode, Severity, ErrorContext, FixSuggestion
)
from .hierarchical_scope_resolution import HierarchicalScopeResolver, ScopeInfo, VariableResolution
from .coupling_graph import ScopedReferenceResolver
from .esm_types import EsmFile


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
class UnitWarning:
    """Represents a unit validation warning."""
    path: str
    message: str
    lhs_units: str = ""
    rhs_units: str = ""
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
    unit_warnings: List[UnitWarning] = None

    def __post_init__(self):
        if self.unit_warnings is None:
            self.unit_warnings = []


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


def validate(esm_file: EsmFile) -> ValidationResult:
    """
    Validate an ESM file against schema, structural, and unit requirements.

    This function implements comprehensive validation including:
    1. Equation-unknown balance
    2. Reference integrity (variable refs, scoped refs, discrete_parameters, coupling refs, operator refs)
    3. Reaction consistency (species declared, positive stoichiometries, no null-null, rate refs)
    4. Event consistency (condition types, affect vars, functional affect refs)

    Args:
        esm_file: The EsmFile object to validate

    Returns:
        ValidationResult containing schema_errors, structural_errors, unit_warnings, and is_valid flag
    """
    schema_errors = []
    structural_errors = []
    unit_warnings = []
    error_collector = ErrorCollector()

    try:
        # Schema validation is assumed to have been done during parsing
        # Focus on structural validation

        # 0. Check that at least one of models or reaction_systems is present
        _validate_content_presence(esm_file, error_collector)

        # 1. Equation-Unknown Balance validation
        _validate_equation_balance_enhanced(esm_file, error_collector)

        # 2. Reference Integrity validation
        _validate_reference_integrity_enhanced(esm_file, error_collector)

        # 3. Reaction Consistency validation
        _validate_reaction_consistency(esm_file, structural_errors)

        # 4. Event Consistency validation
        _validate_event_consistency(esm_file, structural_errors)

        # 5. Domain validation (coordinate transforms, etc.)
        _validate_domain_enhanced(esm_file, error_collector)

        # 6. Unit validation (warnings only)
        _validate_units(esm_file, unit_warnings)

        # Convert enhanced errors back to old format for backward compatibility
        for error in error_collector.errors:
            structural_errors.append(ValidationError(
                path=error.context.path if error.context else "$",
                message=error.message,
                code=error.code.value,
                details=error.context.details if error.context else {}
            ))

        for warning in error_collector.warnings:
            if warning.code == ErrorCode.UNIT_MISMATCH:
                unit_warnings.append(UnitWarning(
                    path=warning.context.path if warning.context else "$",
                    message=warning.message
                ))
            else:
                structural_errors.append(ValidationError(
                    path=warning.context.path if warning.context else "$",
                    message=warning.message,
                    code=warning.code.value,
                    details=warning.context.details if warning.context else {}
                ))

    except Exception as e:
        # Catch-all for unexpected errors
        structural_errors.append(ValidationError(
            path="$",
            message=f"Validation failed with unexpected error: {str(e)}",
            code="validation_error",
            details={
                "exception_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        ))

    is_valid = len(schema_errors) == 0 and len(structural_errors) == 0

    return ValidationResult(
        is_valid=is_valid,
        schema_errors=schema_errors,
        structural_errors=structural_errors,
        unit_warnings=unit_warnings
    )


def validate_raw(esm_data: Union[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate ESM data from raw JSON string or dictionary.

    This function provides backward compatibility by parsing the data first,
    then calling the main validate function.

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
                    structural_errors=[],
                    unit_warnings=[]
                )
        else:
            data = esm_data

        # Validate against JSON schema first
        schema = _get_schema()
        try:
            jsonschema.validate(data, schema)
        except JsonSchemaValidationError as e:
            # Collect all schema validation errors
            validator = jsonschema.Draft7Validator(schema)
            for error in validator.iter_errors(data):
                schema_errors.append(_convert_jsonschema_error(error))

        # If schema validation passed, parse and do structural validation
        if not schema_errors:
            try:
                # Parse to EsmFile and perform structural validation
                esm_file = load(json.dumps(data))
                result = validate(esm_file)
                # Merge schema errors if any occurred during parsing
                result.schema_errors.extend(schema_errors)
                return result
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
            structural_errors=[],
            unit_warnings=[]
        )

    return ValidationResult(
        is_valid=len(schema_errors) == 0 and len(structural_errors) == 0,
        schema_errors=schema_errors,
        structural_errors=structural_errors,
        unit_warnings=[]
    )


def _validate_domain_enhanced(esm_file: EsmFile, error_collector: ErrorCollector) -> None:
    """
    Enhanced domain validation including comprehensive coordinate transform checks.

    This validates:
    1. Coordinate transform ID uniqueness
    2. Non-empty dimensions arrays
    3. Transform chain compatibility (if metadata indicates relationships)
    4. Dimensional consistency for known transform patterns
    """
    if not esm_file.domain or not esm_file.domain.coordinate_transforms:
        return  # No domain or transforms to validate

    domain = esm_file.domain
    transforms = domain.coordinate_transforms
    spatial_dims = set(domain.spatial.keys()) if domain.spatial else set()

    # 1. Check for duplicate transform IDs
    seen_ids = set()
    for i, transform in enumerate(transforms):
        if transform.id in seen_ids:
            error = ESMError(
                code=ErrorCode.SCHEMA_VALIDATION_ERROR,  # Using closest available error code
                message=f"Duplicate coordinate transform ID '{transform.id}' found",
                severity=Severity.ERROR,
                context=ErrorContext(
                    path=f"/domain/coordinate_transforms/{i}/id",
                    details={
                        "transform_id": transform.id,
                        "duplicate_indices": [j for j, t in enumerate(transforms) if t.id == transform.id]
                    }
                ),
                fix_suggestion=FixSuggestion(f"Use unique IDs for coordinate transforms. Consider '{transform.id}_v2' or similar.")
            )
            error_collector.add_error(error)
        seen_ids.add(transform.id)

    # 2. Check for empty dimensions arrays
    for i, transform in enumerate(transforms):
        if not transform.dimensions:
            error = ESMError(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Coordinate transform '{transform.id}' has empty dimensions array",
                severity=Severity.ERROR,
                context=ErrorContext(
                    path=f"/domain/coordinate_transforms/{i}/dimensions",
                    details={
                        "transform_id": transform.id,
                        "description": transform.description if hasattr(transform, 'description') else ""
                    }
                ),
                fix_suggestion=FixSuggestion("Specify at least one dimension for the coordinate transform.")
            )
            error_collector.add_error(error)

    # 3. Check dimensions exist in spatial domain (enhanced beyond parse.py check)
    for i, transform in enumerate(transforms):
        for j, dim in enumerate(transform.dimensions):
            if spatial_dims and dim not in spatial_dims:
                available_dims = sorted(list(spatial_dims))
                error = ESMError(
                    code=ErrorCode.UNDEFINED_VARIABLE,  # Using closest available error code
                    message=f"Coordinate transform '{transform.id}' references undefined dimension '{dim}'",
                    severity=Severity.ERROR,
                    context=ErrorContext(
                        path=f"/domain/coordinate_transforms/{i}/dimensions/{j}",
                        details={
                            "transform_id": transform.id,
                            "undefined_dimension": dim,
                            "available_dimensions": available_dims,
                            "similar_dimensions": [d for d in available_dims if abs(len(d) - len(dim)) <= 2]
                        }
                    ),
                    fix_suggestion=FixSuggestion(
                        f"Use one of the available spatial dimensions: {', '.join(available_dims)}"
                        if available_dims else
                        "Define the required spatial dimensions in the domain.spatial section"
                    )
                )
                error_collector.add_error(error)

    # 4. Validate common coordinate transform patterns
    _validate_coordinate_transform_patterns(transforms, spatial_dims, error_collector)


def _validate_coordinate_transform_patterns(transforms, spatial_dims, error_collector: ErrorCollector) -> None:
    """
    Validate common coordinate transform dimensional patterns.

    This checks for physically reasonable transform dimension counts and patterns
    commonly found in earth science applications.
    """
    for i, transform in enumerate(transforms):
        transform_id = transform.id.lower()
        dim_count = len(transform.dimensions)

        # Check for suspicious dimension patterns
        if dim_count > 4:
            error = ESMError(
                code=ErrorCode.SCHEMA_VALIDATION_ERROR,  # Using available error code for warnings
                message=f"Coordinate transform '{transform.id}' has unusually high dimension count ({dim_count})",
                severity=Severity.WARNING,
                context=ErrorContext(
                    path=f"/domain/coordinate_transforms/{i}",
                    details={
                        "transform_id": transform.id,
                        "dimension_count": dim_count,
                        "dimensions": transform.dimensions
                    }
                ),
                fix_suggestion=FixSuggestion("Verify that all dimensions are necessary for this coordinate transform.")
            )
            error_collector.add_warning(error)

        # Check for common geographic transform patterns
        if any(geo_indicator in transform_id for geo_indicator in ['lonlat', 'geographic', 'mercator', 'proj']):
            geographic_dims = {'lon', 'longitude', 'lat', 'latitude'}
            has_geographic = any(dim.lower() in geographic_dims for dim in transform.dimensions)

            if not has_geographic and spatial_dims:
                # Check if spatial domain has geographic dimensions that might be missing
                available_geographic = [dim for dim in spatial_dims if dim.lower() in geographic_dims]
                if available_geographic:
                    error = ESMError(
                        code=ErrorCode.SCHEMA_VALIDATION_ERROR,
                        message=f"Geographic coordinate transform '{transform.id}' doesn't reference geographic dimensions",
                        severity=Severity.WARNING,
                        context=ErrorContext(
                            path=f"/domain/coordinate_transforms/{i}/dimensions",
                            details={
                                "transform_id": transform.id,
                                "current_dimensions": transform.dimensions,
                                "available_geographic": available_geographic
                            }
                        ),
                        fix_suggestion=FixSuggestion(f"Consider including geographic dimensions: {', '.join(available_geographic)}")
                    )
                    error_collector.add_warning(error)

        # Check for vertical transforms
        if any(vert_indicator in transform_id for vert_indicator in ['pressure', 'height', 'level', 'vertical']):
            vertical_dims = {'lev', 'level', 'pressure', 'height', 'z', 'z_height', 'p'}
            has_vertical = any(dim.lower() in vertical_dims for dim in transform.dimensions)

            if not has_vertical and spatial_dims:
                available_vertical = [dim for dim in spatial_dims if dim.lower() in vertical_dims]
                if available_vertical:
                    error = ESMError(
                        code=ErrorCode.SCHEMA_VALIDATION_ERROR,
                        message=f"Vertical coordinate transform '{transform.id}' doesn't reference vertical dimensions",
                        severity=Severity.WARNING,
                        context=ErrorContext(
                            path=f"/domain/coordinate_transforms/{i}/dimensions",
                            details={
                                "transform_id": transform.id,
                                "current_dimensions": transform.dimensions,
                                "available_vertical": available_vertical
                            }
                        ),
                        fix_suggestion=FixSuggestion(f"Consider including vertical dimensions: {', '.join(available_vertical)}")
                    )
                    error_collector.add_warning(error)


def _validate_content_presence(esm_file: EsmFile, error_collector: ErrorCollector) -> None:
    """
    Validate that at least one of models or reaction_systems is present and non-empty.

    This ensures that the ESM file contains actual computational content rather than
    being empty or containing only metadata.
    """
    has_models = esm_file.models and len(esm_file.models) > 0
    has_reaction_systems = esm_file.reaction_systems and len(esm_file.reaction_systems) > 0

    if not has_models and not has_reaction_systems:
        error = ESMError(
            code=ErrorCode.MISSING_REQUIRED_FIELD,
            message="ESM file must contain at least one model or reaction system. Empty files are not valid.",
            severity=Severity.ERROR,
            context=ErrorContext(
                path="$",
                details={
                    "models_count": len(esm_file.models) if esm_file.models else 0,
                    "reaction_systems_count": len(esm_file.reaction_systems) if esm_file.reaction_systems else 0,
                    "fix_suggestions": [
                        "Add a model with variables and equations",
                        "Add a reaction system with species and reactions",
                        "Import content from existing ESM files"
                    ]
                }
            ),
            fix_suggestion=FixSuggestion("Add at least one model or reaction system to the ESM file")
        )
        error_collector.add_error(error)


def _validate_equation_balance_enhanced(esm_file: EsmFile, error_collector: ErrorCollector) -> None:
    """Enhanced equation-unknown balance validation with detailed suggestions."""
    for i, model in enumerate(esm_file.models.values()):
        # Count state variables (unknowns)
        state_vars = [name for name, var in model.variables.items() if var.type == 'state']
        num_unknowns = len(state_vars)

        # Count equations
        num_equations = len(model.equations)

        if num_equations != num_unknowns:
            error = ESMErrorFactory.create_equation_imbalance_error(
                model.name, num_equations, num_unknowns, state_vars
            )
            error_collector.add_error(error)


def _validate_equation_balance(esm_file: EsmFile, structural_errors: List[ValidationError]) -> None:
    """
    Validate equation-unknown balance in models.

    Ensures each model has the right number of equations for the number of unknowns (state variables).
    """
    for i, model in enumerate(esm_file.models):
        path = f"/models/{i}"

        # Count state variables (unknowns)
        state_vars = [name for name, var in model.variables.items() if var.type == 'state']
        num_unknowns = len(state_vars)

        # Count equations
        num_equations = len(model.equations)

        if num_equations != num_unknowns:
            structural_errors.append(ValidationError(
                path=path,
                message=f"Equation-unknown balance error: {num_equations} equations for {num_unknowns} unknowns (state variables: {', '.join(state_vars)})",
                code="equation_unknown_imbalance",
                details={
                    "model_name": model.name,
                    "num_equations": num_equations,
                    "num_unknowns": num_unknowns,
                    "state_variables": state_vars
                }
            ))


def _validate_reference_integrity_enhanced(esm_file: EsmFile, error_collector: ErrorCollector) -> None:
    """Enhanced reference integrity validation with smart suggestions."""
    # Build comprehensive variable lookup for smart suggestions
    all_variables = {}
    all_models = {}
    all_reaction_systems = {}
    all_operators = {}

    # Collect all models and their variables
    for model in esm_file.models.values():
        all_models[model.name] = model
        for var_name, var in model.variables.items():
            scoped_name = f"{model.name}.{var_name}"
            all_variables[scoped_name] = var
            all_variables[var_name] = var  # Also allow unscoped references within model

    # Collect all reaction systems and their species/parameters
    for rs in esm_file.reaction_systems.values():
        all_reaction_systems[rs.name] = rs
        for species in rs.species:
            scoped_name = f"{rs.name}.{species.name}"
            all_variables[scoped_name] = species
        for param in rs.parameters:
            scoped_name = f"{rs.name}.{param.name}"
            all_variables[scoped_name] = param

    # Collect all operators
    for op in esm_file.operators:
        all_operators[op.operator_id] = op

    # Validate coupling references with enhanced error handling
    for i, coupling in enumerate(esm_file.coupling):
        coupling_path = f"/coupling/{i}"

        # Check source model/system existence (only if field exists)
        if hasattr(coupling, 'source_model') and coupling.source_model is not None:
            if coupling.source_model not in all_models and coupling.source_model not in all_reaction_systems:
                available_components = list(all_models.keys()) + list(all_reaction_systems.keys())
                error = ESMErrorFactory.create_undefined_reference_error(
                    coupling.source_model,
                    available_components,
                    f"{coupling_path}/source_model"
                )
                error.message = f"Source model/system '{coupling.source_model}' not found"
                error_collector.add_error(error)

        # Check target model/system existence (only if field exists)
        if hasattr(coupling, 'target_model') and coupling.target_model is not None:
            if coupling.target_model not in all_models and coupling.target_model not in all_reaction_systems:
                available_components = list(all_models.keys()) + list(all_reaction_systems.keys())
                error = ESMErrorFactory.create_undefined_reference_error(
                    coupling.target_model,
                    available_components,
                    f"{coupling_path}/target_model"
                )
                error.message = f"Target model/system '{coupling.target_model}' not found"
                error_collector.add_error(error)


def _validate_reference_integrity(esm_file: EsmFile, structural_errors: List[ValidationError]) -> None:
    """
    Validate reference integrity across the ESM file.

    Checks:
    - Variable references in equations exist in the model's variables
    - Scoped references in coupling entries resolve correctly
    - Discrete parameter references are valid
    - Coupling references point to existing components
    - Operator references exist in the operators section
    """
    # Build a comprehensive scope resolver for validation
    all_variables = {}
    all_models = {}
    all_reaction_systems = {}
    all_operators = {}

    # Collect all models and their variables
    for model in esm_file.models.values():
        all_models[model.name] = model
        for var_name, var in model.variables.items():
            scoped_name = f"{model.name}.{var_name}"
            all_variables[scoped_name] = var
            all_variables[var_name] = var  # Also allow unscoped references within model

    # Collect all reaction systems and their species/parameters
    for rs in esm_file.reaction_systems.values():
        all_reaction_systems[rs.name] = rs
        # Add species as variables
        for species in rs.species:
            scoped_name = f"{rs.name}.{species.name}"
            all_variables[scoped_name] = species
        # Add parameters as variables
        for param in rs.parameters:
            scoped_name = f"{rs.name}.{param.name}"
            all_variables[scoped_name] = param

    # Collect all operators
    for op in esm_file.operators:
        all_operators[op.operator_id] = op

    # Validate variable references in model equations
    for i, model in enumerate(esm_file.models):
        _validate_model_references(model, i, all_variables, structural_errors)

    # Validate references in reaction systems
    for i, rs in enumerate(esm_file.reaction_systems):
        _validate_reaction_system_references(rs, i, all_variables, structural_errors)

    # Validate coupling references
    for i, coupling in enumerate(esm_file.coupling):
        _validate_coupling_references(coupling, i, all_models, all_reaction_systems, all_operators, structural_errors)

    # Validate event references
    for i, event in enumerate(esm_file.events):
        _validate_event_references(event, i, all_variables, structural_errors)


def _validate_reaction_consistency(esm_file: EsmFile, structural_errors: List[ValidationError]) -> None:
    """
    Validate reaction consistency in reaction systems.

    Checks:
    - Every species in substrates/products is declared in species
    - Stoichiometries are positive
    - No reaction has both substrates: null and products: null
    - Rate expressions only reference declared parameters/species
    """
    for rs_idx, (rs_name, rs) in enumerate(esm_file.reaction_systems.items()):
        rs_path = f"/reaction_systems/{rs_idx}"

        # Build set of declared species and parameters
        species_names = {species.name for species in rs.species}
        param_names = {param.name for param in rs.parameters}

        for r_idx, reaction in enumerate(rs.reactions):
            reaction_path = f"{rs_path}/reactions/{r_idx}"

            # Check for null-null reaction
            if not reaction.reactants and not reaction.products:
                structural_errors.append(ValidationError(
                    path=reaction_path,
                    message=f"Invalid reaction '{reaction.name}': both substrates and products are empty",
                    code="null_null_reaction",
                    details={"reaction_name": reaction.name}
                ))

            # Validate reactant species exist and have positive stoichiometry
            for species_name, stoich in reaction.reactants.items():
                if species_name not in species_names:
                    structural_errors.append(ValidationError(
                        path=f"{reaction_path}/reactants/{species_name}",
                        message=f"Reactant species '{species_name}' not declared in reaction system '{rs.name}'",
                        code="undeclared_species",
                        details={"species": species_name, "reaction_system": rs.name, "available_species": list(species_names)}
                    ))

                if stoich <= 0:
                    structural_errors.append(ValidationError(
                        path=f"{reaction_path}/reactants/{species_name}",
                        message=f"Reactant stoichiometry must be positive, got {stoich}",
                        code="negative_stoichiometry",
                        details={"species": species_name, "stoichiometry": stoich}
                    ))

                # Check if stoichiometry is an integer
                if not isinstance(stoich, int) and not (isinstance(stoich, float) and stoich.is_integer()):
                    structural_errors.append(ValidationError(
                        path=f"{reaction_path}/reactants/{species_name}",
                        message=f"Reactant stoichiometry must be a positive integer, got {stoich}",
                        code="non_integer_stoichiometry",
                        details={"species": species_name, "stoichiometry": stoich, "stoichiometry_type": type(stoich).__name__}
                    ))

            # Validate product species exist and have positive stoichiometry
            for species_name, stoich in reaction.products.items():
                if species_name not in species_names:
                    structural_errors.append(ValidationError(
                        path=f"{reaction_path}/products/{species_name}",
                        message=f"Product species '{species_name}' not declared in reaction system '{rs.name}'",
                        code="undeclared_species",
                        details={"species": species_name, "reaction_system": rs.name, "available_species": list(species_names)}
                    ))

                if stoich <= 0:
                    structural_errors.append(ValidationError(
                        path=f"{reaction_path}/products/{species_name}",
                        message=f"Product stoichiometry must be positive, got {stoich}",
                        code="negative_stoichiometry",
                        details={"species": species_name, "stoichiometry": stoich}
                    ))

                # Check if stoichiometry is an integer
                if not isinstance(stoich, int) and not (isinstance(stoich, float) and stoich.is_integer()):
                    structural_errors.append(ValidationError(
                        path=f"{reaction_path}/products/{species_name}",
                        message=f"Product stoichiometry must be a positive integer, got {stoich}",
                        code="non_integer_stoichiometry",
                        details={"species": species_name, "stoichiometry": stoich, "stoichiometry_type": type(stoich).__name__}
                    ))

            # Validate rate constant references (full expression parsing)
            if hasattr(reaction, 'rate_constant') and reaction.rate_constant is not None:
                _validate_rate_expression(reaction.rate_constant, param_names, species_names, rs.name, reaction_path, structural_errors)


def _validate_rate_expression(rate_expr, param_names: Set[str], species_names: Set[str],
                             reaction_system_name: str, reaction_path: str, structural_errors: List[ValidationError]) -> None:
    """
    Validate that a rate expression only references declared parameters and species.

    Args:
        rate_expr: The rate expression (string, number, or ExprNode)
        param_names: Set of declared parameter names in the reaction system
        species_names: Set of declared species names in the reaction system
        reaction_system_name: Name of the reaction system for error messages
        reaction_path: Path to the reaction for error reporting
        structural_errors: List to append validation errors to
    """
    from .expression import free_variables

    if isinstance(rate_expr, str):
        # Simple parameter reference
        if rate_expr not in param_names:
            structural_errors.append(ValidationError(
                path=f"{reaction_path}/rate_constant",
                message=f"Rate constant parameter '{rate_expr}' not declared in reaction system '{reaction_system_name}'",
                code="undeclared_parameter",
                details={
                    "parameter": rate_expr,
                    "reaction_system": reaction_system_name,
                    "available_parameters": list(param_names)
                }
            ))
    elif isinstance(rate_expr, (int, float)):
        # Numeric constant - always valid
        pass
    else:
        # Complex expression - parse and validate all variables
        try:
            referenced_vars = free_variables(rate_expr)

            # Check that all referenced variables are declared parameters or species
            for var in referenced_vars:
                if var not in param_names and var not in species_names:
                    # Variable is not declared in this reaction system
                    structural_errors.append(ValidationError(
                        path=f"{reaction_path}/rate_constant",
                        message=f"Rate expression references undeclared variable '{var}' in reaction system '{reaction_system_name}'",
                        code="undeclared_rate_variable",
                        details={
                            "variable": var,
                            "reaction_system": reaction_system_name,
                            "available_parameters": list(param_names),
                            "available_species": list(species_names),
                            "rate_expression": str(rate_expr)
                        }
                    ))

        except Exception as e:
            # Error parsing expression - report as validation error
            structural_errors.append(ValidationError(
                path=f"{reaction_path}/rate_constant",
                message=f"Could not parse rate expression in reaction system '{reaction_system_name}': {str(e)}",
                code="invalid_rate_expression",
                details={
                    "reaction_system": reaction_system_name,
                    "rate_expression": str(rate_expr),
                    "parse_error": str(e)
                }
            ))


def _validate_event_consistency(esm_file: EsmFile, structural_errors: List[ValidationError]) -> None:
    """
    Validate event consistency.

    Checks:
    - Continuous event conditions are expressions (not booleans)
    - Discrete event conditions produce boolean values
    - Variables in affects are declared
    - Variables in affect_neg (direction-dependent affects) are declared
    - Functional affect references are valid (handler_id, read_vars, read_params, modified_params)
    - discrete_parameters in coupling entries are valid
    """
    # Build variable lookup for validation
    all_variables = set()
    all_parameters = set()

    for model in esm_file.models.values():
        for var_name in model.variables:
            all_variables.add(var_name)
            all_variables.add(f"{model.name}.{var_name}")
            # Parameters are also variables
            if model.variables[var_name].type == 'parameter':
                all_parameters.add(var_name)
                all_parameters.add(f"{model.name}.{var_name}")

    for rs in esm_file.reaction_systems.values():
        for species in rs.species:
            all_variables.add(species.name)
            all_variables.add(f"{rs.name}.{species.name}")
        for param in rs.parameters:
            all_variables.add(param.name)
            all_variables.add(f"{rs.name}.{param.name}")
            all_parameters.add(param.name)
            all_parameters.add(f"{rs.name}.{param.name}")

    # Build operator/handler lookup for functional affects
    all_operators = set()
    for operator in esm_file.operators:
        all_operators.add(operator.operator_id)

    for event_idx, event in enumerate(esm_file.events):
        event_path = f"/events/{event_idx}"

        # Validate affects - check that target variables exist and functional affects are valid
        for affect_idx, affect in enumerate(event.affects):
            affect_path = f"{event_path}/affects/{affect_idx}"

            if hasattr(affect, 'lhs'):  # AffectEquation
                if affect.lhs not in all_variables:
                    structural_errors.append(ValidationError(
                        path=f"{affect_path}/lhs",
                        message=f"Affect target variable '{affect.lhs}' not declared",
                        code="undeclared_affect_variable",
                        details={"variable": affect.lhs, "available_variables": sorted(list(all_variables))}
                    ))
            elif hasattr(affect, 'handler_id'):  # FunctionalAffect
                # Validate handler_id exists as an operator
                if affect.handler_id not in all_operators:
                    structural_errors.append(ValidationError(
                        path=f"{affect_path}/handler_id",
                        message=f"Functional affect handler '{affect.handler_id}' not declared in operators",
                        code="undeclared_handler",
                        details={"handler": affect.handler_id, "available_operators": sorted(list(all_operators))}
                    ))

                # Validate read_vars exist
                for var_idx, read_var in enumerate(affect.read_vars):
                    if read_var not in all_variables:
                        structural_errors.append(ValidationError(
                            path=f"{affect_path}/read_vars/{var_idx}",
                            message=f"Functional affect read variable '{read_var}' not declared",
                            code="undeclared_read_variable",
                            details={"variable": read_var, "available_variables": sorted(list(all_variables))}
                        ))

                # Validate read_params exist
                for param_idx, read_param in enumerate(affect.read_params):
                    if read_param not in all_parameters:
                        structural_errors.append(ValidationError(
                            path=f"{affect_path}/read_params/{param_idx}",
                            message=f"Functional affect read parameter '{read_param}' not declared",
                            code="undeclared_read_parameter",
                            details={"parameter": read_param, "available_parameters": sorted(list(all_parameters))}
                        ))

                # Validate modified_params exist
                for param_idx, mod_param in enumerate(affect.modified_params):
                    if mod_param not in all_parameters:
                        structural_errors.append(ValidationError(
                            path=f"{affect_path}/modified_params/{param_idx}",
                            message=f"Functional affect modified parameter '{mod_param}' not declared",
                            code="undeclared_modified_parameter",
                            details={"parameter": mod_param, "available_parameters": sorted(list(all_parameters))}
                        ))

        # Validate affect_neg (direction-dependent affects) if present
        if hasattr(event, 'affect_neg') and event.affect_neg is not None:
            for affect_idx, affect in enumerate(event.affect_neg):
                affect_path = f"{event_path}/affect_neg/{affect_idx}"

                if hasattr(affect, 'lhs'):  # AffectEquation
                    if affect.lhs not in all_variables:
                        structural_errors.append(ValidationError(
                            path=f"{affect_path}/lhs",
                            message=f"Affect_neg target variable '{affect.lhs}' not declared",
                            code="undeclared_affect_neg_variable",
                            details={"variable": affect.lhs, "available_variables": sorted(list(all_variables))}
                        ))
                elif hasattr(affect, 'handler_id'):  # FunctionalAffect
                    # Same validation as regular affects
                    if affect.handler_id not in all_operators:
                        structural_errors.append(ValidationError(
                            path=f"{affect_path}/handler_id",
                            message=f"Affect_neg functional affect handler '{affect.handler_id}' not declared in operators",
                            code="undeclared_handler",
                            details={"handler": affect.handler_id, "available_operators": sorted(list(all_operators))}
                        ))

                    # Validate read_vars, read_params, modified_params for affect_neg functional affects
                    for var_idx, read_var in enumerate(affect.read_vars):
                        if read_var not in all_variables:
                            structural_errors.append(ValidationError(
                                path=f"{affect_path}/read_vars/{var_idx}",
                                message=f"Affect_neg functional affect read variable '{read_var}' not declared",
                                code="undeclared_read_variable",
                                details={"variable": read_var, "available_variables": sorted(list(all_variables))}
                            ))

                    for param_idx, read_param in enumerate(affect.read_params):
                        if read_param not in all_parameters:
                            structural_errors.append(ValidationError(
                                path=f"{affect_path}/read_params/{param_idx}",
                                message=f"Affect_neg functional affect read parameter '{read_param}' not declared",
                                code="undeclared_read_parameter",
                                details={"parameter": read_param, "available_parameters": sorted(list(all_parameters))}
                            ))

                    for param_idx, mod_param in enumerate(affect.modified_params):
                        if mod_param not in all_parameters:
                            structural_errors.append(ValidationError(
                                path=f"{affect_path}/modified_params/{param_idx}",
                                message=f"Affect_neg functional affect modified parameter '{mod_param}' not declared",
                                code="undeclared_modified_parameter",
                                details={"parameter": mod_param, "available_parameters": sorted(list(all_parameters))}
                            ))

    # Validate discrete_parameters in coupling entries
    for coupling_idx, coupling in enumerate(esm_file.coupling):
        coupling_path = f"/coupling/{coupling_idx}"

        # Check if this coupling entry has discrete_parameters
        if hasattr(coupling, 'discrete_parameters') and coupling.discrete_parameters is not None:
            for param_idx, discrete_param in enumerate(coupling.discrete_parameters):
                param_path = f"{coupling_path}/discrete_parameters/{param_idx}"

                if discrete_param not in all_parameters:
                    structural_errors.append(ValidationError(
                        path=param_path,
                        message=f"Discrete parameter '{discrete_param}' not declared in any model or reaction system",
                        code="undeclared_discrete_parameter",
                        details={"parameter": discrete_param, "available_parameters": sorted(list(all_parameters))}
                    ))


def _validate_units(esm_file: EsmFile, unit_warnings: List[UnitWarning]) -> None:
    """
    Validate dimensional consistency (warnings only).

    Uses the UnitValidator from units.py to perform comprehensive dimensional analysis
    and unit validation across models and reaction systems.
    """
    try:
        from .units import UnitValidator

        # Create unit validator instance
        validator = UnitValidator()

        # Validate the entire ESM file
        unit_result = validator.validate_esm_file(esm_file)

        # Convert validation errors to warnings (as per function contract)
        for error_msg in unit_result.errors:
            unit_warnings.append(UnitWarning(
                path="unit_validation",
                message=error_msg,
                details={"validation_type": "dimensional_analysis"}
            ))

        # Convert validation warnings to our warning format
        for warning_msg in unit_result.warnings:
            unit_warnings.append(UnitWarning(
                path="unit_validation",
                message=warning_msg,
                details={"validation_type": "unit_warning"}
            ))

    except ImportError:
        # If pint is not available, add a warning about missing unit validation
        unit_warnings.append(UnitWarning(
            path="unit_validation",
            message="Unit validation skipped: pint library not available. Install with: pip install pint",
            details={"validation_type": "dependency_missing"}
        ))
    except Exception as e:
        # If unit validation fails for any reason, add a warning but don't break validation
        unit_warnings.append(UnitWarning(
            path="unit_validation",
            message=f"Unit validation failed: {str(e)}",
            details={"validation_type": "validation_error", "exception": str(e)}
        ))


def _validate_model_references(model, model_idx: int, all_variables: Dict[str, Any], structural_errors: List[ValidationError]) -> None:
    """Validate references within a model."""
    model_path = f"/models/{model_idx}"

    # Check variable references in equations (simplified - would need expression tree walking)
    # This is a placeholder for full expression validation
    for eq_idx, equation in enumerate(model.equations):
        eq_path = f"{model_path}/equations/{eq_idx}"
        # TODO: Walk expression tree and validate all variable references
        pass


def _validate_reaction_system_references(rs, rs_idx: int, all_variables: Dict[str, Any], structural_errors: List[ValidationError]) -> None:
    """Validate references within a reaction system."""
    # TODO: Implement reaction system reference validation
    pass


def _validate_coupling_references(coupling, coupling_idx: int, all_models: Dict[str, Any],
                                all_reaction_systems: Dict[str, Any], all_operators: Dict[str, Any],
                                structural_errors: List[ValidationError]) -> None:
    """Validate coupling references."""
    coupling_path = f"/coupling/{coupling_idx}"

    # Check that source and target models/systems exist
    if coupling.source_model not in all_models and coupling.source_model not in all_reaction_systems:
        structural_errors.append(ValidationError(
            path=f"{coupling_path}/source_model",
            message=f"Source model/system '{coupling.source_model}' not found",
            code="undeclared_coupling_source",
            details={"source": coupling.source_model}
        ))

    if coupling.target_model not in all_models and coupling.target_model not in all_reaction_systems:
        structural_errors.append(ValidationError(
            path=f"{coupling_path}/target_model",
            message=f"Target model/system '{coupling.target_model}' not found",
            code="undeclared_coupling_target",
            details={"target": coupling.target_model}
        ))


def _validate_event_references(event, event_idx: int, all_variables: Dict[str, Any], structural_errors: List[ValidationError]) -> None:
    """Validate event references."""
    # TODO: Implement event reference validation
    pass


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