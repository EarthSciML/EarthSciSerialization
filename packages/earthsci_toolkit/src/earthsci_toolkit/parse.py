"""
ESM Format parsing module.

This module provides functions to parse JSON data into ESM format objects,
with schema validation using the bundled esm-schema.json file.
"""

import json
import os
from pathlib import Path
from typing import Union, Dict, Any, List, TYPE_CHECKING
from dataclasses import fields
from enum import Enum
try:
    # Python 3.9+
    from importlib.resources import files
    _RESOURCES_AVAILABLE = True
except ImportError:
    try:
        # Python 3.7-3.8 fallback
        from importlib_resources import files
        _RESOURCES_AVAILABLE = True
    except ImportError:
        # No importlib resources available, will use fallback
        _RESOURCES_AVAILABLE = False
        files = None

if TYPE_CHECKING:
    from .esm_types import DataLoader

import jsonschema
from jsonschema import validate

from .esm_types import (
    EsmFile, Metadata, Model, ReactionSystem, ModelVariable, Equation,
    Species, Parameter, Reaction, ExprNode, Expr, AffectEquation,
    ContinuousEvent, DiscreteEvent, DiscreteEventTrigger, FunctionalAffect,
    DataLoader, DataLoaderKind, DataLoaderSource, DataLoaderTemporal,
    DataLoaderSpatial, DataLoaderVariable, DataLoaderRegridding, Operator,
    CouplingEntry, CouplingType, ConnectorEquation, Connector, Domain,
    OperatorComposeCoupling, CouplingCouple, VariableMapCoupling,
    OperatorApplyCoupling, CallbackCoupling, EventCoupling,
    Reference, TemporalDomain, SpatialDimension, CoordinateTransform,
    InitialCondition, InitialConditionType, BoundaryCondition, BoundaryConditionType
)


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails."""
    pass


class UnsupportedVersionError(Exception):
    """Exception raised when ESM version is not supported."""
    pass


class CircularReferenceError(Exception):
    """Exception raised when circular subsystem references are detected."""
    pass


class SubsystemRefError(Exception):
    """Exception raised when a subsystem reference cannot be resolved."""
    pass


# Current library version for compatibility checking
_CURRENT_VERSION = (0, 1, 0)


def _check_version_compatibility(version_string: str) -> None:
    """Check ESM version compatibility, raising errors or warnings as appropriate."""
    import re
    import warnings

    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_string)
    if not match:
        return  # Schema validation should catch invalid formats

    major = int(match.group(1))
    minor = int(match.group(2))

    # Reject unsupported major versions
    if major != _CURRENT_VERSION[0]:
        raise UnsupportedVersionError(
            f"Unsupported major version {major}. "
            f"This library supports major version {_CURRENT_VERSION[0]}."
        )

    # Warn about newer minor versions
    if minor > _CURRENT_VERSION[1]:
        warnings.warn(
            f"{version_string} is newer than the current library version "
            f"{'.'.join(str(v) for v in _CURRENT_VERSION)}. "
            f"Some features may not be supported.",
            UserWarning,
            stacklevel=3
        )


def _get_schema() -> Dict[str, Any]:
    """Load the bundled ESM schema."""
    if _RESOURCES_AVAILABLE:
        try:
            # Use importlib.resources to locate the schema file within the package
            schema_files = files("earthsci_toolkit") / "data"
            schema_path = schema_files / "esm-schema.json"

            # Read the schema content using the modern resource API
            with schema_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, AttributeError, TypeError) as e:
            # Fall through to the legacy path approach
            pass

    # Fallback to the original method if resources approach fails or is unavailable
    schema_path = Path(__file__).parent / "data" / "esm-schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"ESM schema not found at {schema_path}")

    with open(schema_path, 'r') as f:
        return json.load(f)


def _parse_expression(expr_data: Union[int, float, str, Dict[str, Any]]) -> Expr:
    """Parse an expression from JSON data."""
    if isinstance(expr_data, (int, float, str)):
        return expr_data
    elif isinstance(expr_data, dict):
        # Parse ExprNode
        op = expr_data["op"]
        args = [_parse_expression(arg) for arg in expr_data["args"]]
        wrt = expr_data.get("wrt")
        dim = expr_data.get("dim")

        # Validate operator-specific field requirements
        if op == "D" and wrt is None:
            raise ValueError(f"Operator 'D' requires 'wrt' field to be specified")
        if op == "grad" and dim is None:
            raise ValueError(f"Operator 'grad' requires 'dim' field to be specified")

        return ExprNode(op=op, args=args, wrt=wrt, dim=dim)
    else:
        raise ValueError(f"Invalid expression data: {expr_data}")


def _parse_equation(eq_data: Dict[str, Any]) -> Equation:
    """Parse an equation from JSON data."""
    lhs = _parse_expression(eq_data["lhs"])
    rhs = _parse_expression(eq_data["rhs"])
    comment = eq_data.get("_comment")
    return Equation(lhs=lhs, rhs=rhs, _comment=comment)


def _parse_affect_equation(affect_data: Dict[str, Any]) -> AffectEquation:
    """Parse an affect equation from JSON data."""
    lhs = affect_data["lhs"]  # string
    rhs = _parse_expression(affect_data["rhs"])
    return AffectEquation(lhs=lhs, rhs=rhs)


def _parse_functional_affect(functional_affect_data: Dict[str, Any]) -> FunctionalAffect:
    """Parse a functional affect from JSON data."""
    handler_id = functional_affect_data["handler_id"]
    read_vars = functional_affect_data.get("read_vars", [])
    read_params = functional_affect_data.get("read_params", [])
    modified_params = functional_affect_data.get("modified_params", [])
    config = functional_affect_data.get("config", {})

    return FunctionalAffect(
        handler_id=handler_id,
        read_vars=read_vars,
        read_params=read_params,
        modified_params=modified_params,
        config=config
    )


def _parse_model_variable(var_data: Dict[str, Any]) -> ModelVariable:
    """Parse a model variable from JSON data."""
    var_type = var_data["type"]
    units = var_data.get("units")
    default = var_data.get("default")
    description = var_data.get("description")
    expression = None
    if "expression" in var_data:
        expression = _parse_expression(var_data["expression"])

    return ModelVariable(
        type=var_type,
        units=units,
        default=default,
        description=description,
        expression=expression
    )


def _parse_discrete_event_trigger(trigger_data: Dict[str, Any]) -> DiscreteEventTrigger:
    """Parse a discrete event trigger from JSON data."""
    trigger_type = trigger_data["type"]

    if trigger_type == "condition":
        expression = _parse_expression(trigger_data["expression"])
        return DiscreteEventTrigger(type=trigger_type, value=expression)
    elif trigger_type == "periodic":
        interval = trigger_data["interval"]
        return DiscreteEventTrigger(type=trigger_type, value=interval)
    elif trigger_type == "preset_times":
        times = trigger_data["times"]
        return DiscreteEventTrigger(type=trigger_type, value=times)
    else:
        raise ValueError(f"Unknown trigger type: {trigger_type}")


def _parse_continuous_event(event_data: Dict[str, Any]) -> ContinuousEvent:
    """Parse a continuous event from JSON data."""
    name = event_data.get("name", "")
    conditions = [_parse_expression(cond) for cond in event_data["conditions"]]
    affects = []

    # Parse affects: distinguish AffectEquation from FunctionalAffect
    if "affects" in event_data:
        for affect in event_data["affects"]:
            if isinstance(affect, dict) and "handler_id" in affect:
                affects.append(_parse_functional_affect(affect))
            else:
                affects.append(_parse_affect_equation(affect))

    # Parse functional_affect (FunctionalAffect object)
    if "functional_affect" in event_data:
        functional_affect = _parse_functional_affect(event_data["functional_affect"])
        affects.append(functional_affect)

    priority = event_data.get("priority", 0)

    # Parse new fields
    affect_neg = None
    if "affect_neg" in event_data:
        affect_neg_list = []
        for affect in event_data["affect_neg"]:
            if isinstance(affect, dict) and "handler_id" in affect:
                # This is a functional affect
                affect_neg_list.append(_parse_functional_affect(affect))
            else:
                # This is a regular affect equation
                affect_neg_list.append(_parse_affect_equation(affect))
        affect_neg = affect_neg_list

    root_find = event_data.get("root_find", "left")
    reinitialize = event_data.get("reinitialize", False)
    description = event_data.get("description")

    return ContinuousEvent(
        name=name,
        conditions=conditions,  # Fixed: use plural conditions
        affects=affects,
        affect_neg=affect_neg,
        root_find=root_find,
        reinitialize=reinitialize,
        priority=priority,
        description=description
    )


def _parse_discrete_event(event_data: Dict[str, Any]) -> DiscreteEvent:
    """Parse a discrete event from JSON data."""
    name = event_data.get("name", "")
    trigger = _parse_discrete_event_trigger(event_data["trigger"])
    affects = []

    # Parse affects: distinguish AffectEquation from FunctionalAffect
    if "affects" in event_data:
        for affect in event_data["affects"]:
            if isinstance(affect, dict) and "handler_id" in affect:
                affects.append(_parse_functional_affect(affect))
            else:
                affects.append(_parse_affect_equation(affect))

    # Parse functional_affect (FunctionalAffect object)
    if "functional_affect" in event_data:
        functional_affect = _parse_functional_affect(event_data["functional_affect"])
        affects.append(functional_affect)

    priority = event_data.get("priority", 0)

    return DiscreteEvent(
        name=name,
        trigger=trigger,
        affects=affects,
        priority=priority
    )


def _parse_model(model_data: Dict[str, Any]) -> Model:
    """Parse a model from JSON data."""
    # Extract variables
    variables = {}
    if "variables" in model_data:
        for var_name, var_data in model_data["variables"].items():
            variables[var_name] = _parse_model_variable(var_data)

    # Extract equations
    equations = []
    if "equations" in model_data:
        for eq_data in model_data["equations"]:
            equations.append(_parse_equation(eq_data))

    # Extract subsystems. Each entry is either a parsed Model or a raw dict
    # carrying a "ref" field to be resolved later by resolve_subsystem_refs.
    subsystems: Dict[str, Any] = {}
    if "subsystems" in model_data:
        for sub_name, sub_data in model_data["subsystems"].items():
            if isinstance(sub_data, dict) and "ref" in sub_data:
                subsystems[sub_name] = sub_data
            else:
                sub_model = _parse_model(sub_data)
                sub_model.name = sub_name
                subsystems[sub_name] = sub_model

    model = Model(name="", variables=variables, equations=equations,
                  subsystems=subsystems)
    return model


def _parse_species(species_data: Dict[str, Any]) -> Species:
    """Parse a species from JSON data."""
    return Species(
        name="",  # Name comes from the key
        units=species_data.get("units"),
        default=species_data.get("default"),
        description=species_data.get("description")
    )


def _parse_parameter(param_data: Dict[str, Any]) -> Parameter:
    """Parse a parameter from JSON data."""
    # For now, assume value is numeric (can be extended for expressions)
    value = param_data.get("default", 0.0)
    return Parameter(
        name="",  # Name comes from the key
        value=value,
        units=param_data.get("units"),
        description=param_data.get("description")
    )


def _parse_reaction(reaction_data: Dict[str, Any]) -> Reaction:
    """Parse a reaction from JSON data."""
    name = reaction_data.get("name", reaction_data["id"])

    # Parse reactants (substrates in schema)
    reactants = {}
    if reaction_data.get("substrates"):
        for substrate in reaction_data["substrates"]:
            species = substrate["species"]
            stoichiometry = substrate["stoichiometry"]
            reactants[species] = float(stoichiometry)

    # Parse products
    products = {}
    if reaction_data.get("products"):
        for product in reaction_data["products"]:
            species = product["species"]
            stoichiometry = product["stoichiometry"]
            products[species] = float(stoichiometry)

    # Parse rate
    rate_constant = None
    if "rate" in reaction_data:
        rate_constant = _parse_expression(reaction_data["rate"])

    return Reaction(
        name=name,
        reactants=reactants,
        products=products,
        rate_constant=rate_constant
    )


def _parse_reaction_system(rs_data: Dict[str, Any]) -> ReactionSystem:
    """Parse a reaction system from JSON data."""
    # Parse species
    species = []
    if "species" in rs_data:
        for species_name, species_data in rs_data["species"].items():
            sp = _parse_species(species_data)
            sp.name = species_name
            species.append(sp)

    # Parse parameters
    parameters = []
    if "parameters" in rs_data:
        for param_name, param_data in rs_data["parameters"].items():
            param = _parse_parameter(param_data)
            param.name = param_name
            parameters.append(param)

    # Parse reactions
    reactions = []
    if "reactions" in rs_data:
        for reaction_data in rs_data["reactions"]:
            reactions.append(_parse_reaction(reaction_data))

    # Parse constraint equations
    constraint_equations = []
    if "constraint_equations" in rs_data:
        for eq_data in rs_data["constraint_equations"]:
            constraint_equations.append(_parse_equation(eq_data))

    # Extract subsystems. Each entry is either a parsed ReactionSystem or a raw
    # dict with a "ref" field to be resolved later by resolve_subsystem_refs.
    subsystems: Dict[str, Any] = {}
    if "subsystems" in rs_data:
        for sub_name, sub_data in rs_data["subsystems"].items():
            if isinstance(sub_data, dict) and "ref" in sub_data:
                subsystems[sub_name] = sub_data
            else:
                sub_rs = _parse_reaction_system(sub_data)
                sub_rs.name = sub_name
                subsystems[sub_name] = sub_rs

    return ReactionSystem(
        name="",  # Name comes from the key
        species=species,
        parameters=parameters,
        reactions=reactions,
        constraint_equations=constraint_equations,
        subsystems=subsystems,
    )


def _parse_reference(ref_data: Dict[str, Any]) -> Reference:
    """Parse a reference from JSON data."""
    return Reference(
        title=ref_data.get("citation", ""),
        authors=[],  # Schema doesn't have authors field
        journal=None,
        year=None,
        doi=ref_data.get("doi"),
        url=ref_data.get("url")
    )


def _parse_metadata(metadata_data: Dict[str, Any]) -> Metadata:
    """Parse metadata from JSON data."""
    references = []
    if "references" in metadata_data:
        for ref_data in metadata_data["references"]:
            references.append(_parse_reference(ref_data))

    return Metadata(
        title=metadata_data["name"],  # Schema uses "name" not "title"
        description=metadata_data.get("description"),
        authors=metadata_data.get("authors", []),
        created=metadata_data.get("created"),
        modified=metadata_data.get("modified"),
        version="1.0",  # Default version
        references=references,
        keywords=metadata_data.get("tags", [])  # Schema uses "tags" not "keywords"
    )


def _parse_data_loader_source(src_data: Dict[str, Any]) -> DataLoaderSource:
    return DataLoaderSource(
        url_template=src_data["url_template"],
        mirrors=list(src_data.get("mirrors", [])),
    )


def _parse_data_loader_temporal(tmp_data: Dict[str, Any]) -> DataLoaderTemporal:
    return DataLoaderTemporal(
        start=tmp_data.get("start"),
        end=tmp_data.get("end"),
        file_period=tmp_data.get("file_period"),
        frequency=tmp_data.get("frequency"),
        records_per_file=tmp_data.get("records_per_file"),
        time_variable=tmp_data.get("time_variable"),
    )


def _parse_data_loader_spatial(sp_data: Dict[str, Any]) -> DataLoaderSpatial:
    return DataLoaderSpatial(
        crs=sp_data["crs"],
        grid_type=sp_data["grid_type"],
        staggering=dict(sp_data.get("staggering", {})),
        resolution=dict(sp_data.get("resolution", {})),
        extent={k: list(v) for k, v in sp_data.get("extent", {}).items()},
    )


def _parse_data_loader_variable(var_data: Dict[str, Any]) -> DataLoaderVariable:
    unit_conversion = var_data.get("unit_conversion")
    if isinstance(unit_conversion, dict):
        unit_conversion = _parse_expression(unit_conversion)
    reference = None
    if "reference" in var_data:
        reference = _parse_reference(var_data["reference"])
    return DataLoaderVariable(
        file_variable=var_data["file_variable"],
        units=var_data["units"],
        unit_conversion=unit_conversion,
        description=var_data.get("description"),
        reference=reference,
    )


def _parse_data_loader_regridding(rg_data: Dict[str, Any]) -> DataLoaderRegridding:
    return DataLoaderRegridding(
        fill_value=rg_data.get("fill_value"),
        extrapolation=rg_data.get("extrapolation"),
    )


def _parse_data_loader(loader_data: Dict[str, Any]) -> DataLoader:
    """Parse a data loader from JSON data."""
    kind = DataLoaderKind(loader_data["kind"])
    source = _parse_data_loader_source(loader_data["source"])

    variables = {
        vname: _parse_data_loader_variable(vdef)
        for vname, vdef in loader_data["variables"].items()
    }

    temporal = None
    if "temporal" in loader_data:
        temporal = _parse_data_loader_temporal(loader_data["temporal"])

    spatial = None
    if "spatial" in loader_data:
        spatial = _parse_data_loader_spatial(loader_data["spatial"])

    regridding = None
    if "regridding" in loader_data:
        regridding = _parse_data_loader_regridding(loader_data["regridding"])

    reference = None
    if "reference" in loader_data:
        reference = _parse_reference(loader_data["reference"])

    metadata = dict(loader_data.get("metadata", {}))

    return DataLoader(
        name="",  # Name comes from the key
        kind=kind,
        source=source,
        variables=variables,
        temporal=temporal,
        spatial=spatial,
        regridding=regridding,
        reference=reference,
        metadata=metadata,
    )


def _parse_operator(operator_data: Dict[str, Any]) -> Operator:
    """Parse an operator from JSON data."""
    # Use schema fields directly
    operator_id = operator_data.get("operator_id", "")
    needed_vars = operator_data.get("needed_vars", [])
    modifies = operator_data.get("modifies")
    config = operator_data.get("config", {})
    description = operator_data.get("description")
    reference = None
    if "reference" in operator_data:
        reference = _parse_reference(operator_data["reference"])

    return Operator(
        operator_id=operator_id,
        needed_vars=needed_vars,
        modifies=modifies,
        reference=reference,
        config=config,
        description=description
    )


def _parse_coupling_entry(coupling_data: Dict[str, Any]) -> CouplingEntry:
    """Parse a coupling entry from JSON data."""
    # Get coupling type from schema
    schema_type = coupling_data["type"]

    # Map schema types to our enum
    type_mapping = {
        "operator_compose": CouplingType.OPERATOR_COMPOSE,
        "couple": CouplingType.COUPLE,
        "variable_map": CouplingType.VARIABLE_MAP,
        "operator_apply": CouplingType.OPERATOR_APPLY,
        "callback": CouplingType.CALLBACK,
        "event": CouplingType.EVENT,
    }

    if schema_type not in type_mapping:
        raise ValueError(f"Unknown coupling type: {schema_type}")

    coupling_type = type_mapping[schema_type]
    description = coupling_data.get("description")

    # Create appropriate coupling entry based on type
    if coupling_type == CouplingType.OPERATOR_COMPOSE:
        return OperatorComposeCoupling(
            description=description,
            systems=coupling_data.get("systems", []),
            translate=coupling_data.get("translate", {})
        )

    elif coupling_type == CouplingType.COUPLE:
        # Parse connector if present
        connector = None
        if "connector" in coupling_data:
            connector_data = coupling_data["connector"]
            equations = []
            for eq_data in connector_data.get("equations", []):
                equation = ConnectorEquation(
                    from_var=eq_data["from"],
                    to_var=eq_data["to"],
                    transform=eq_data["transform"],
                    expression=_parse_expression(eq_data["expression"]) if "expression" in eq_data else None
                )
                equations.append(equation)
            connector = Connector(equations=equations)

        return CouplingCouple(
            description=description,
            systems=coupling_data.get("systems", []),
            connector=connector
        )

    elif coupling_type == CouplingType.VARIABLE_MAP:
        return VariableMapCoupling(
            description=description,
            from_var=coupling_data.get("from"),
            to_var=coupling_data.get("to"),
            transform=coupling_data.get("transform"),
            factor=coupling_data.get("factor")
        )

    elif coupling_type == CouplingType.OPERATOR_APPLY:
        return OperatorApplyCoupling(
            description=description,
            operator=coupling_data.get("operator")
        )

    elif coupling_type == CouplingType.CALLBACK:
        return CallbackCoupling(
            description=description,
            callback_id=coupling_data.get("callback_id"),
            config=coupling_data.get("config", {})
        )

    elif coupling_type == CouplingType.EVENT:
        # Parse conditions
        conditions = []
        if "conditions" in coupling_data:
            conditions = [_parse_expression(cond) for cond in coupling_data["conditions"]]

        # Parse trigger for discrete events
        trigger = None
        if "trigger" in coupling_data:
            trigger = _parse_discrete_event_trigger(coupling_data["trigger"])

        # Parse affects
        affects = []
        if "affects" in coupling_data:
            affects = [_parse_affect_equation(affect) for affect in coupling_data["affects"]]

        # Parse functional_affect (FunctionalAffect object)
        if "functional_affect" in coupling_data:
            functional_affect = _parse_functional_affect(coupling_data["functional_affect"])
            affects.append(functional_affect)

        # Parse affect_neg
        affect_neg = []
        if "affect_neg" in coupling_data and coupling_data["affect_neg"] is not None:
            for affect in coupling_data["affect_neg"]:
                if isinstance(affect, dict) and "handler_id" in affect:
                    # This is a functional affect
                    affect_neg.append(_parse_functional_affect(affect))
                else:
                    # This is a regular affect equation
                    affect_neg.append(_parse_affect_equation(affect))

        return EventCoupling(
            description=description,
            event_type=coupling_data.get("event_type"),
            conditions=conditions,
            trigger=trigger,
            affects=affects,
            affect_neg=affect_neg,
            discrete_parameters=coupling_data.get("discrete_parameters", []),
            root_find=coupling_data.get("root_find"),
            reinitialize=coupling_data.get("reinitialize")
        )

    else:
        raise ValueError(f"Unknown coupling type: {coupling_type}")


def _parse_domain(domain_data: Dict[str, Any]) -> Domain:
    """Parse domain configuration from JSON data."""
    domain = Domain()

    if "independent_variable" in domain_data:
        domain.independent_variable = domain_data["independent_variable"]

    # Parse temporal domain
    if "temporal" in domain_data:
        temporal_data = domain_data["temporal"]
        domain.temporal = TemporalDomain(
            start=temporal_data["start"],
            end=temporal_data["end"],
            reference_time=temporal_data.get("reference_time")
        )

    # Parse spatial domain
    if "spatial" in domain_data:
        spatial_data = domain_data["spatial"]
        domain.spatial = {}
        for dim_name, dim_data in spatial_data.items():
            domain.spatial[dim_name] = SpatialDimension(
                min=dim_data["min"],
                max=dim_data["max"],
                units=dim_data.get("units"),
                grid_spacing=dim_data.get("grid_spacing")
            )

    # Parse coordinate transforms
    if "coordinate_transforms" in domain_data:
        for transform_data in domain_data["coordinate_transforms"]:
            transform = CoordinateTransform(
                id=transform_data["id"],
                description=transform_data.get("description", ""),
                dimensions=transform_data.get("dimensions", [])
            )
            domain.coordinate_transforms.append(transform)

    # Parse spatial reference
    if "spatial_ref" in domain_data:
        domain.spatial_ref = domain_data["spatial_ref"]

    # Parse initial conditions
    if "initial_conditions" in domain_data:
        ic_data = domain_data["initial_conditions"]
        ic_type_str = ic_data["type"]

        # Map schema types to our enum types
        type_mapping = {
            "constant": InitialConditionType.CONSTANT,
            "per_variable": InitialConditionType.PER_VARIABLE,
            "from_file": InitialConditionType.DATA
        }

        ic_type = type_mapping.get(ic_type_str, InitialConditionType.CONSTANT)

        # Extract appropriate fields based on type
        value = ic_data.get("value")
        values = ic_data.get("values")  # For per_variable type
        function = None
        data_source = ic_data.get("path")  # Schema uses "path" for file source

        domain.initial_conditions = InitialCondition(
            type=ic_type,
            value=value,
            values=values,
            function=function,
            data_source=data_source
        )

    # Parse boundary conditions
    if "boundary_conditions" in domain_data:
        for bc_data in domain_data["boundary_conditions"]:
            bc_type = BoundaryConditionType(bc_data["type"])
            bc = BoundaryCondition(
                type=bc_type,
                dimensions=bc_data["dimensions"],
                value=bc_data.get("value"),
                function=bc_data.get("function"),
                robin_alpha=bc_data.get("robin_alpha"),
                robin_beta=bc_data.get("robin_beta"),
                robin_gamma=bc_data.get("robin_gamma")
            )
            domain.boundary_conditions.append(bc)

    return domain


def _validate_domain(domain: Domain) -> None:
    """Validate domain configuration for consistency and semantic correctness."""
    errors = []

    # Validate temporal domain
    if domain.temporal:
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(domain.temporal.start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(domain.temporal.end.replace('Z', '+00:00'))

            if start_dt >= end_dt:
                errors.append("Temporal domain: start time must be before end time")

            if domain.temporal.reference_time:
                ref_dt = datetime.fromisoformat(domain.temporal.reference_time.replace('Z', '+00:00'))
                if ref_dt < start_dt or ref_dt > end_dt:
                    errors.append("Temporal domain: reference time must be within start and end times")
        except ValueError as e:
            errors.append(f"Temporal domain: invalid datetime format - {e}")

    # Validate spatial dimensions
    if domain.spatial:
        for dim_name, dim_spec in domain.spatial.items():
            if dim_spec.min >= dim_spec.max:
                errors.append(f"Spatial dimension '{dim_name}': min value must be less than max value")

            if dim_spec.grid_spacing is not None and dim_spec.grid_spacing <= 0:
                errors.append(f"Spatial dimension '{dim_name}': grid spacing must be positive")

            # Check reasonable coordinate ranges
            if dim_name in ['lon', 'longitude']:
                if dim_spec.min < -180 or dim_spec.max > 180:
                    errors.append(f"Longitude dimension: values should be between -180 and 180 degrees")
            elif dim_name in ['lat', 'latitude']:
                if dim_spec.min < -90 or dim_spec.max > 90:
                    errors.append(f"Latitude dimension: values should be between -90 and 90 degrees")

    # Validate coordinate transforms reference valid dimensions
    if domain.coordinate_transforms and domain.spatial:
        for transform in domain.coordinate_transforms:
            for dim in transform.dimensions:
                if dim not in domain.spatial:
                    errors.append(f"Coordinate transform '{transform.id}': references undefined dimension '{dim}'")

    # Validate boundary conditions reference valid dimensions
    if domain.boundary_conditions and domain.spatial:
        for bc in domain.boundary_conditions:
            for dim in bc.dimensions:
                if dim not in domain.spatial:
                    errors.append(f"Boundary condition: references undefined dimension '{dim}'")

    # Validate initial conditions have required fields
    if domain.initial_conditions:
        ic = domain.initial_conditions
        if ic.type == InitialConditionType.CONSTANT and ic.value is None:
            errors.append("Initial condition type 'constant' requires a value")
        elif ic.type == InitialConditionType.FUNCTION and ic.function is None:
            errors.append("Initial condition type 'function' requires a function specification")
        elif ic.type == InitialConditionType.DATA and ic.data_source is None:
            errors.append("Initial condition type 'data' requires a data source")

    # Validate boundary conditions have required fields
    for i, bc in enumerate(domain.boundary_conditions):
        if bc.type in [BoundaryConditionType.CONSTANT, BoundaryConditionType.DIRICHLET] and bc.value is None:
            errors.append(f"Boundary condition {i+1}: type '{bc.type.value}' requires a value")
        elif bc.type == BoundaryConditionType.ROBIN:
            if bc.robin_alpha is None or bc.robin_beta is None:
                errors.append(f"Boundary condition {i+1}: Robin boundary condition requires robin_alpha and robin_beta coefficients")
            if bc.robin_gamma is None:
                errors.append(f"Boundary condition {i+1}: Robin boundary condition requires robin_gamma value")

    if errors:
        raise ValueError("Domain validation failed:\n" + "\n".join(f"  - {error}" for error in errors))


def _parse_esm_data(data: Dict[str, Any]) -> EsmFile:
    """Parse ESM data from validated JSON."""
    # Parse metadata
    metadata = _parse_metadata(data["metadata"])

    # Parse models
    models = {}
    if "models" in data:
        for model_name, model_data in data["models"].items():
            model = _parse_model(model_data)
            model.name = model_name
            models[model_name] = model

    # Parse reaction systems
    reaction_systems = {}
    if "reaction_systems" in data:
        for rs_name, rs_data in data["reaction_systems"].items():
            rs = _parse_reaction_system(rs_data)
            rs.name = rs_name
            reaction_systems[rs_name] = rs

    # Parse domains if present
    domains = {}
    if "domains" in data:
        for domain_name, domain_data in data["domains"].items():
            d = _parse_domain(domain_data)
            _validate_domain(d)
            domains[domain_name] = d

    # Parse data loaders
    data_loaders: Dict[str, DataLoader] = {}
    if "data_loaders" in data:
        for loader_name, loader_data in data["data_loaders"].items():
            loader = _parse_data_loader(loader_data)
            loader.name = loader_name
            data_loaders[loader_name] = loader

    # Parse operators
    operators = []
    if "operators" in data:
        for op_name, op_data in data["operators"].items():
            operator = _parse_operator(op_data)
            operator.name = op_name
            operators.append(operator)

    # Parse coupling entries
    coupling = []
    if "coupling" in data:
        for coupling_data in data["coupling"]:
            coupling.append(_parse_coupling_entry(coupling_data))

    # Collect events from models and reaction systems
    events = []

    # Collect events from models
    if "models" in data:
        for model_name, model_data in data["models"].items():
            if "discrete_events" in model_data:
                for event_data in model_data["discrete_events"]:
                    events.append(_parse_discrete_event(event_data))
            if "continuous_events" in model_data:
                for event_data in model_data["continuous_events"]:
                    events.append(_parse_continuous_event(event_data))

    # Collect events from reaction systems
    if "reaction_systems" in data:
        for rs_name, rs_data in data["reaction_systems"].items():
            if "discrete_events" in rs_data:
                for event_data in rs_data["discrete_events"]:
                    events.append(_parse_discrete_event(event_data))
            if "continuous_events" in rs_data:
                for event_data in rs_data["continuous_events"]:
                    events.append(_parse_continuous_event(event_data))

    return EsmFile(
        version=data["esm"],
        metadata=metadata,
        models=models,
        reaction_systems=reaction_systems,
        events=events,
        data_loaders=data_loaders,
        operators=operators,
        coupling=coupling,
        domains=domains,
    )


def _fetch_ref_content(ref: str, base_path: str) -> str:
    """Fetch content from a subsystem ref (URL or file path).

    Args:
        ref: The reference string (URL or relative file path)
        base_path: The base directory for resolving relative paths

    Returns:
        The file content as a string

    Raises:
        SubsystemRefError: If the reference cannot be fetched or read
    """
    if ref.startswith("http://") or ref.startswith("https://"):
        import urllib.request
        import urllib.error
        try:
            with urllib.request.urlopen(ref) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            raise SubsystemRefError(
                f"Failed to fetch subsystem ref URL '{ref}': {e}"
            )
    else:
        resolved = os.path.normpath(os.path.join(base_path, ref))
        if not os.path.exists(resolved):
            raise SubsystemRefError(
                f"Subsystem ref file not found: '{resolved}' "
                f"(resolved from '{ref}' relative to '{base_path}')"
            )
        with open(resolved, "r") as f:
            return f.read()


def _resolve_model_subsystems(
    model: Model,
    base_path: str,
    seen_refs: set,
) -> None:
    """Recursively resolve subsystem refs within a Model.

    Args:
        model: The model whose subsystems should be resolved
        base_path: The base directory for resolving relative paths
        seen_refs: Set of already-seen ref strings for circular detection
    """
    if not model.subsystems:
        return

    resolved_subsystems: Dict[str, Any] = {}
    for sub_name, sub_value in model.subsystems.items():
        # During parsing, a ref object comes through as a dict with a "ref" key
        # before being coerced to a Model.
        if isinstance(sub_value, dict) and "ref" in sub_value:
            ref_str = sub_value["ref"]

            # Circular reference detection
            canonical = os.path.normpath(os.path.join(base_path, ref_str)) \
                if not ref_str.startswith("http") else ref_str
            if canonical in seen_refs:
                raise CircularReferenceError(
                    f"Circular subsystem reference detected: '{ref_str}' "
                    f"(chain: {' -> '.join(seen_refs)} -> {canonical})"
                )
            new_seen = seen_refs | {canonical}

            content = _fetch_ref_content(ref_str, base_path)
            ref_data = json.loads(content)

            # Determine the new base_path for nested refs
            if ref_str.startswith("http://") or ref_str.startswith("https://"):
                # For URLs, use the URL directory as base
                new_base = ref_str.rsplit("/", 1)[0] if "/" in ref_str else base_path
            else:
                resolved_path = os.path.normpath(os.path.join(base_path, ref_str))
                new_base = os.path.dirname(resolved_path)

            # Validate and parse the referenced file
            schema = _get_schema()
            try:
                validate(ref_data, schema)
            except jsonschema.ValidationError as e:
                raise SubsystemRefError(
                    f"Schema validation failed for subsystem ref '{ref_str}': {e.message}"
                )

            parsed = _parse_esm_data(ref_data)

            # Extract the single top-level model
            if parsed.models:
                # Take the first (and expected-only) model
                sub_model = next(iter(parsed.models.values()))
                sub_model.name = sub_name
                # Recursively resolve nested subsystem refs
                _resolve_model_subsystems(sub_model, new_base, new_seen)
                resolved_subsystems[sub_name] = sub_model
            else:
                raise SubsystemRefError(
                    f"Subsystem ref '{ref_str}' does not contain a model"
                )
        else:
            # Already a Model object, just recurse into it
            if isinstance(sub_value, Model):
                _resolve_model_subsystems(sub_value, base_path, seen_refs)
            resolved_subsystems[sub_name] = sub_value

    model.subsystems = resolved_subsystems


def _resolve_reaction_system_subsystems(
    rs: ReactionSystem,
    base_path: str,
    seen_refs: set,
) -> None:
    """Recursively resolve subsystem refs within a ReactionSystem.

    Args:
        rs: The reaction system whose subsystems should be resolved
        base_path: The base directory for resolving relative paths
        seen_refs: Set of already-seen ref strings for circular detection
    """
    if not rs.subsystems:
        return

    resolved_subsystems: Dict[str, Any] = {}
    for sub_name, sub_value in rs.subsystems.items():
        if isinstance(sub_value, dict) and "ref" in sub_value:
            ref_str = sub_value["ref"]

            canonical = os.path.normpath(os.path.join(base_path, ref_str)) \
                if not ref_str.startswith("http") else ref_str
            if canonical in seen_refs:
                raise CircularReferenceError(
                    f"Circular subsystem reference detected: '{ref_str}' "
                    f"(chain: {' -> '.join(seen_refs)} -> {canonical})"
                )
            new_seen = seen_refs | {canonical}

            content = _fetch_ref_content(ref_str, base_path)
            ref_data = json.loads(content)

            if ref_str.startswith("http://") or ref_str.startswith("https://"):
                new_base = ref_str.rsplit("/", 1)[0] if "/" in ref_str else base_path
            else:
                resolved_path = os.path.normpath(os.path.join(base_path, ref_str))
                new_base = os.path.dirname(resolved_path)

            schema = _get_schema()
            try:
                validate(ref_data, schema)
            except jsonschema.ValidationError as e:
                raise SubsystemRefError(
                    f"Schema validation failed for subsystem ref '{ref_str}': {e.message}"
                )

            parsed = _parse_esm_data(ref_data)

            # Extract the single top-level reaction system
            if parsed.reaction_systems:
                sub_rs = next(iter(parsed.reaction_systems.values()))
                sub_rs.name = sub_name
                _resolve_reaction_system_subsystems(sub_rs, new_base, new_seen)
                resolved_subsystems[sub_name] = sub_rs
            else:
                raise SubsystemRefError(
                    f"Subsystem ref '{ref_str}' does not contain a reaction system"
                )
        else:
            if isinstance(sub_value, ReactionSystem):
                _resolve_reaction_system_subsystems(sub_value, base_path, seen_refs)
            resolved_subsystems[sub_name] = sub_value

    rs.subsystems = resolved_subsystems


def resolve_subsystem_refs(esm_file: EsmFile, base_path: str) -> None:
    """Resolve all subsystem references in an ESM file.

    Walks all subsystems in models and reaction_systems. For each subsystem
    value with a ``ref`` field:

    - If the ref starts with ``http://`` or ``https://``, the content is
      fetched via urllib.
    - Otherwise the ref is resolved relative to *base_path* and read from
      the filesystem.

    The referenced file is parsed, the single top-level model or reaction
    system is extracted, and the reference is replaced with the resolved
    content. Resolution is recursive, and circular references are detected.

    Args:
        esm_file: The parsed ESM file to resolve references in (modified in place)
        base_path: The base directory for resolving relative file paths

    Raises:
        CircularReferenceError: If circular subsystem references are detected
        SubsystemRefError: If a reference cannot be resolved or is invalid
    """
    seen: set = set()

    for model in esm_file.models.values():
        _resolve_model_subsystems(model, base_path, seen)

    for rs in esm_file.reaction_systems.values():
        _resolve_reaction_system_subsystems(rs, base_path, seen)


# Operator arity requirements: (min_args, max_args). None = unlimited.
_OPERATOR_ARITY = {
    "+": (2, None), "-": (1, None), "*": (2, None), "/": (2, 2),
    "^": (2, 2), "D": (1, 1), "grad": (1, 1), "div": (1, 1),
    "laplacian": (1, 1), "exp": (1, 1), "log": (1, 1), "log10": (1, 1),
    "sqrt": (1, 1), "abs": (1, 1), "sin": (1, 1), "cos": (1, 1),
    "tan": (1, 1), "asin": (1, 1), "acos": (1, 1), "atan": (1, 1),
    "atan2": (2, 2), "min": (2, None), "max": (2, None),
    "floor": (1, 1), "ceil": (1, 1), "ifelse": (3, 3),
    ">": (2, 2), "<": (2, 2), ">=": (2, 2), "<=": (2, 2),
    "==": (2, 2), "!=": (2, 2), "and": (2, None), "or": (2, None),
    "not": (1, 1), "Pre": (1, 1), "sign": (1, 1),
}

# Built-in symbols always available in expressions
_BUILTIN_SYMBOLS = frozenset({
    "t", "pi", "e", "true", "false",
    "x", "y", "z", "lon", "lat", "lev", "longitude", "latitude", "level",
})

# Pint-compatible unit aliases for normalizing
_UNIT_ALIASES = {
    "1": "dimensionless", "": "dimensionless", "dimensionless": "dimensionless",
}


def _walk_expression_strings(expr) -> List[str]:
    """Recursively collect string args from inside op-expression nodes only."""
    result = []
    if isinstance(expr, dict) and "op" in expr and "args" in expr:
        for arg in expr["args"]:
            if isinstance(arg, str):
                result.append(arg)
            elif isinstance(arg, dict):
                result.extend(_walk_expression_strings(arg))
    return result


def _check_expression_arity(expr, errors: List[str], path: str) -> None:
    """Walk an expression tree and check operator arity."""
    if isinstance(expr, dict) and "op" in expr and "args" in expr:
        op = expr["op"]
        args = expr["args"]
        if op in _OPERATOR_ARITY:
            min_args, max_args = _OPERATOR_ARITY[op]
            n = len(args)
            if n < min_args:
                errors.append(
                    f"{path}: operator '{op}' requires at least {min_args} args, got {n}"
                )
            elif max_args is not None and n > max_args:
                errors.append(
                    f"{path}: operator '{op}' accepts at most {max_args} args, got {n}"
                )
        for i, arg in enumerate(args):
            _check_expression_arity(arg, errors, f"{path}/args[{i}]")


def _normalize_unit(unit: str) -> str:
    """Normalize a unit string for compatibility comparison."""
    if unit is None:
        return "dimensionless"
    return _UNIT_ALIASES.get(unit.strip(), unit.strip())


def _units_compatible(u1: str, u2: str) -> bool:
    """Check if two unit strings represent compatible (same dimension) quantities."""
    n1 = _normalize_unit(u1)
    n2 = _normalize_unit(u2)
    if n1 == n2:
        return True
    try:
        import pint
        ureg = pint.UnitRegistry()
        q1 = ureg(n1) if n1 != "dimensionless" else ureg("dimensionless")
        q2 = ureg(n2) if n2 != "dimensionless" else ureg("dimensionless")
        return q1.dimensionality == q2.dimensionality
    except Exception:
        return n1 == n2


def _build_symbol_tables(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build symbol tables for all systems and global symbols in the file."""
    models = {}
    for mname, m in data.get("models", {}).items():
        var_info = {}
        for vname, vdef in m.get("variables", {}).items():
            var_info[vname] = vdef
        models[mname] = var_info

    reaction_systems = {}
    for rsname, rs in data.get("reaction_systems", {}).items():
        sym_info = {}
        for sname, sdef in rs.get("species", {}).items():
            sym_info[sname] = {"type": "species", **sdef}
        for pname, pdef in rs.get("parameters", {}).items():
            sym_info[pname] = {"type": "parameter", **pdef}
        reaction_systems[rsname] = sym_info

    data_loaders = {}
    for dname, d in data.get("data_loaders", {}).items():
        loader_info = {}
        for vname, vdef in d.get("variables", {}).items():
            loader_info[vname] = vdef
        data_loaders[dname] = loader_info

    # Global symbol set: all variable/species/parameter names anywhere
    global_symbols = set(_BUILTIN_SYMBOLS)
    for m in models.values():
        global_symbols.update(m.keys())
    for rs in reaction_systems.values():
        global_symbols.update(rs.keys())
    for d in data_loaders.values():
        global_symbols.update(d.keys())
    # Add spatial dim names from domains
    for dom in data.get("domains", {}).values():
        global_symbols.update(dom.get("spatial", {}).keys())

    return {
        "models": models,
        "reaction_systems": reaction_systems,
        "data_loaders": data_loaders,
        "global_symbols": global_symbols,
        "all_systems": set(models.keys()) | set(reaction_systems.keys()) | set(data_loaders.keys()),
    }


def _resolve_scoped_ref(ref: str, tables: Dict[str, Any]) -> tuple:
    """
    Try to resolve a 'System.var' style reference.
    Returns (system_name, var_name, status) where status is one of:
    - 'ok': resolved successfully
    - 'no_system': system not found
    - 'no_var': system found but variable not in it
    - 'not_scoped': ref doesn't have a dot
    """
    if "." not in ref:
        return (None, None, "not_scoped")
    parts = ref.split(".")
    system = parts[0]
    var = parts[-1]
    if system not in tables["all_systems"]:
        return (system, var, "no_system")
    # Check if var exists in that system
    if system in tables["models"]:
        if var in tables["models"][system]:
            return (system, var, "ok")
    if system in tables["reaction_systems"]:
        if var in tables["reaction_systems"][system]:
            return (system, var, "ok")
    if system in tables["data_loaders"]:
        if var in tables["data_loaders"][system]:
            return (system, var, "ok")
    return (system, var, "no_var")


def _check_variable_references(data: Dict[str, Any], tables: Dict[str, Any], errors: List[str]) -> None:
    """
    Check variable references in equations.

    Two flavors of check:
    1. Scoped refs (Model.var): system must exist; for 2-part refs the var must exist
       in the named system.
    2. Bare-string refs in the RHS of D() (derivative) equations: every ref must
       resolve to a symbol declared somewhere in the file. Plain assignment-style
       equations are not checked because they often use coupled-in vars.
    """
    global_symbols = tables["global_symbols"]
    for mname, m in data.get("models", {}).items():
        for i, eq in enumerate(m.get("equations", [])):
            lhs_is_derivative = (
                isinstance(eq.get("lhs"), dict) and eq["lhs"].get("op") == "D"
            )
            for side in ("lhs", "rhs"):
                if side not in eq:
                    continue
                refs = _walk_expression_strings(eq[side])
                for ref in refs:
                    if "." in ref:
                        # 3+ part refs may use subsystem nesting; only check top-level system
                        if ref.count(".") > 1:
                            top_system = ref.split(".")[0]
                            if top_system not in tables["all_systems"]:
                                errors.append(
                                    f"models/{mname}/equations[{i}]: reference '{ref}' to undefined system '{top_system}'"
                                )
                            continue
                        system, var, status = _resolve_scoped_ref(ref, tables)
                        if status == "no_system":
                            errors.append(
                                f"models/{mname}/equations[{i}]: reference '{ref}' to undefined system '{system}'"
                            )
                        elif status == "no_var":
                            errors.append(
                                f"models/{mname}/equations[{i}]: reference '{ref}' — variable '{var}' not found in system '{system}'"
                            )
                    else:
                        # Bare-string refs only checked inside derivative equations
                        if lhs_is_derivative and side == "rhs":
                            if ref not in global_symbols:
                                errors.append(
                                    f"models/{mname}/equations[{i}]: undefined variable reference '{ref}'"
                                )


def _check_coupling_references(data: Dict[str, Any], tables: Dict[str, Any], errors: List[str]) -> None:
    """Check that coupling 'from' references resolve to valid scoped refs.
    'to' is intentionally lenient since variable_map can introduce new target vars."""
    for i, c in enumerate(data.get("coupling", [])):
        ref = c.get("from")
        if not isinstance(ref, str) or "." not in ref:
            continue
        # For 3+ part refs (subsystem nesting), only verify the top-level system exists
        if ref.count(".") > 1:
            top_system = ref.split(".")[0]
            if top_system not in tables["all_systems"]:
                errors.append(
                    f"coupling[{i}]/from: reference '{ref}' to undefined system '{top_system}'"
                )
            continue
        system, var, status = _resolve_scoped_ref(ref, tables)
        if status == "no_system":
            errors.append(
                f"coupling[{i}]/from: reference '{ref}' to undefined system '{system}'"
            )
        elif status == "no_var":
            errors.append(
                f"coupling[{i}]/from: reference '{ref}' — variable '{var}' not provided by '{system}'"
            )


def _check_circular_references(data: Dict[str, Any], tables: Dict[str, Any], errors: List[str]) -> None:
    """Detect cycles in cross-system dependencies introduced by equation references."""
    # Build system -> set of systems it depends on
    deps = {name: set() for name in data.get("models", {})}
    for mname, m in data.get("models", {}).items():
        for eq in m.get("equations", []):
            for side in ("lhs", "rhs"):
                if side not in eq:
                    continue
                for ref in _walk_expression_strings(eq[side]):
                    if "." in ref:
                        target_system = ref.split(".")[0]
                        if target_system != mname and target_system in deps:
                            deps[mname].add(target_system)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in deps}

    def dfs(node, path):
        color[node] = GRAY
        for nxt in deps.get(node, ()):
            if color.get(nxt) == GRAY:
                cycle_start = path.index(nxt) if nxt in path else 0
                cycle = path[cycle_start:] + [nxt]
                errors.append(f"circular reference (cycle) detected: {' -> '.join(cycle)}")
                return True
            elif color.get(nxt) == WHITE:
                if dfs(nxt, path + [nxt]):
                    return True
        color[node] = BLACK
        return False

    for n in deps:
        if color[n] == WHITE:
            if dfs(n, [n]):
                break


def _check_data_loader_variables(data: Dict[str, Any], errors: List[str]) -> None:
    """Each variable in data_loader.variables must declare file_variable and units."""
    for dname, d in data.get("data_loaders", {}).items():
        variables = d.get("variables", {})
        if not variables:
            errors.append(f"data_loaders/{dname}/variables: must declare at least one variable")
        for vname, vdef in variables.items():
            if not isinstance(vdef, dict):
                continue
            if "file_variable" not in vdef:
                errors.append(
                    f"data_loaders/{dname}/variables/{vname}: missing required 'file_variable' field"
                )
            if "units" not in vdef:
                errors.append(
                    f"data_loaders/{dname}/variables/{vname}: missing required 'units' field"
                )


def _check_discrete_parameters(data: Dict[str, Any], errors: List[str]) -> None:
    """discrete_parameters list must reference variables of type 'parameter'."""
    for mname, m in data.get("models", {}).items():
        var_types = {n: v.get("type") for n, v in m.get("variables", {}).items()}
        for ei, event in enumerate(m.get("discrete_events", [])):
            for dp in event.get("discrete_parameters", []) or []:
                if dp not in var_types:
                    errors.append(
                        f"models/{mname}/discrete_events[{ei}]: discrete_parameter '{dp}' not declared in model"
                    )
                elif var_types[dp] != "parameter":
                    errors.append(
                        f"models/{mname}/discrete_events[{ei}]: discrete_parameter '{dp}' references variable of type '{var_types[dp]}', expected 'parameter'"
                    )


_DATE_RE = __import__("re").compile(
    r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$'
)
_URL_RE = __import__("re").compile(r'^https?://[^\s/$.?#].[^\s]*$')
_DOI_RE = __import__("re").compile(r'^10\.\d{4,9}/[^\s]+$')
_DURATION_RE = __import__("re").compile(
    r'^P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$'
)


def _check_metadata_formats(data: Dict[str, Any], errors: List[str]) -> None:
    """Validate ISO 8601 dates, URLs, and DOIs in metadata."""
    md = data.get("metadata", {})
    for field in ("created", "modified"):
        val = md.get(field)
        if isinstance(val, str) and not _DATE_RE.match(val):
            errors.append(f"metadata/{field}: '{val}' is not a valid ISO 8601 date")
    for ri, ref in enumerate(md.get("references", []) or []):
        url = ref.get("url")
        if isinstance(url, str) and not _URL_RE.match(url):
            errors.append(f"metadata/references[{ri}]/url: '{url}' is not a valid URL")
        doi = ref.get("doi")
        if isinstance(doi, str) and not _DOI_RE.match(doi):
            errors.append(f"metadata/references[{ri}]/doi: '{doi}' is not a valid DOI format")


def _check_temporal_resolution(data: Dict[str, Any], errors: List[str]) -> None:
    """Validate ISO 8601 duration strings in data_loader.temporal fields."""
    for dname, d in data.get("data_loaders", {}).items():
        temporal = d.get("temporal", {})
        if not isinstance(temporal, dict):
            continue
        for field_name in ("file_period", "frequency"):
            res = temporal.get(field_name)
            if isinstance(res, str) and res and not _DURATION_RE.match(res):
                errors.append(
                    f"data_loaders/{dname}/temporal/{field_name}: '{res}' is not a valid ISO 8601 duration"
                )


def _check_subsystem_refs(data: Dict[str, Any], errors: List[str], file_path) -> None:
    """Check that subsystem ref points to an existing file with a single top-level system."""
    base_dirs = []
    if file_path is not None:
        base = Path(file_path).parent if not isinstance(file_path, Path) else file_path.parent
        base_dirs.append(base)
    # Always include CWD as a fallback
    base_dirs.append(Path.cwd())

    def check_subsystems(parent_path, subsystems):
        for sname, sub in subsystems.items():
            ref = sub.get("ref") if isinstance(sub, dict) else None
            if not ref:
                continue
            # Try to resolve against any base dir
            target = None
            for bd in base_dirs:
                candidate = (bd / ref).resolve()
                if candidate.exists():
                    target = candidate
                    break
            if target is None:
                errors.append(
                    f"{parent_path}/subsystems/{sname}: ref '{ref}' file not found"
                )
                continue
            try:
                with open(target) as f:
                    sub_data = json.load(f)
            except Exception as e:
                errors.append(f"{parent_path}/subsystems/{sname}: cannot parse ref '{ref}': {e}")
                continue
            top_systems = list(sub_data.get("models", {}).keys()) + list(
                sub_data.get("reaction_systems", {}).keys()
            )
            if len(top_systems) != 1:
                errors.append(
                    f"{parent_path}/subsystems/{sname}: ref '{ref}' is ambiguous — expected exactly one top-level system, found {len(top_systems)}"
                )

    for mname, m in data.get("models", {}).items():
        if "subsystems" in m:
            check_subsystems(f"models/{mname}", m["subsystems"])
    for rsname, rs in data.get("reaction_systems", {}).items():
        if "subsystems" in rs:
            check_subsystems(f"reaction_systems/{rsname}", rs["subsystems"])


def _collect_var_units(tables: Dict[str, Any]) -> Dict[str, str]:
    """Build {var_name: units} map for plain (unscoped) variable refs."""
    var_units = {}
    for m in tables["models"].values():
        for vname, vdef in m.items():
            if vdef.get("units") is not None:
                var_units[vname] = vdef["units"]
    for rs in tables["reaction_systems"].values():
        for vname, vdef in rs.items():
            if vdef.get("units") is not None:
                var_units[vname] = vdef["units"]
    for d in tables["data_loaders"].values():
        for vname, vdef in d.items():
            if vdef.get("units") is not None:
                var_units[vname] = vdef["units"]
    return var_units


def _infer_expression_units(expr, var_units: Dict[str, str]):
    """
    Best-effort inference of expression units. Returns the unit string,
    None if can't infer, or special tag '<incompatible>' if a unit conflict was found inside.
    """
    if isinstance(expr, (int, float)):
        return "dimensionless"
    if isinstance(expr, str):
        return var_units.get(expr)
    if not isinstance(expr, dict):
        return None
    op = expr.get("op")
    args = expr.get("args", [])
    if op in ("+", "-"):
        # All args must share units
        sub_units = [_infer_expression_units(a, var_units) for a in args]
        non_none = [u for u in sub_units if u is not None]
        if len(non_none) >= 2:
            ref = non_none[0]
            for u in non_none[1:]:
                if not _units_compatible(ref, u):
                    return "<incompatible>"
        return non_none[0] if non_none else None
    if op == "*":
        return None  # multiplication can have varied units
    return None


def _is_derivative_compatible(lhs_var_units: str, rhs_units: str) -> bool:
    """
    Check whether rhs_units could be the time derivative of lhs_var_units.
    True if (rhs * second) is dimensionally equal to lhs_var.
    Also accepts the case where both are dimensionless (decay-style equations).
    """
    n_lhs = _normalize_unit(lhs_var_units)
    n_rhs = _normalize_unit(rhs_units)
    if n_lhs == "dimensionless" and n_rhs == "dimensionless":
        return True
    try:
        import pint
        ureg = pint.UnitRegistry()
        lhs_q = ureg(n_lhs)
        rhs_q = ureg(n_rhs)
        ratio = (rhs_q * ureg("second")) / lhs_q
        return ratio.dimensionless
    except Exception:
        return True  # If pint can't parse, don't flag


def _check_unit_consistency(data: Dict[str, Any], tables: Dict[str, Any], errors: List[str]) -> None:
    """
    Check unit compatibility in equations.

    Conservative: only flags
    1. Equations of the form D(x)/dt = bare_var where bare_var has dimensions
       clearly incompatible with x/time (e.g., velocity-rate set to mass).
    2. Observed variable expressions whose top-level + or - has incompatible operands.
    """
    var_units = _collect_var_units(tables)

    for mname, m in data.get("models", {}).items():
        # Observed variables: check direct addition/subtraction operand compatibility
        for vname, vdef in m.get("variables", {}).items():
            if vdef.get("type") == "observed" and "expression" in vdef:
                expr = vdef["expression"]
                if isinstance(expr, dict) and expr.get("op") in ("+", "-"):
                    sub_units = []
                    for arg in expr.get("args", []):
                        if isinstance(arg, str):
                            sub_units.append(var_units.get(arg))
                    non_none = [u for u in sub_units if u is not None]
                    if len(non_none) >= 2:
                        ref = non_none[0]
                        for u in non_none[1:]:
                            if not _units_compatible(ref, u):
                                errors.append(
                                    f"models/{mname}/variables/{vname}: expression has incompatible units in addition/subtraction"
                                )
                                break

        # Equations: only check D(x)/dt = bare_var case
        for i, eq in enumerate(m.get("equations", [])):
            lhs = eq.get("lhs")
            rhs = eq.get("rhs")
            if not (isinstance(lhs, dict) and lhs.get("op") == "D"):
                continue
            inner = lhs.get("args", [None])[0]
            if not isinstance(inner, str):
                continue
            lhs_var_units = var_units.get(inner)
            if not lhs_var_units:
                continue
            if not isinstance(rhs, str):
                continue
            rhs_units = var_units.get(rhs)
            if not rhs_units:
                continue
            if not _is_derivative_compatible(lhs_var_units, rhs_units):
                errors.append(
                    f"models/{mname}/equations[{i}]: rhs '{rhs}' units '{rhs_units}' incompatible with time derivative of '{lhs_var_units}'"
                )


def _check_equation_balance(data: Dict[str, Any], errors: List[str]) -> None:
    """
    Check for clearly broken equation/state-variable patterns.

    Flags only the unambiguous cases (no operators/coupling/data_loaders to disambiguate):
    1. Model has state variables but zero equations.
    2. Total equations < state variables AND no observed variables provide algebraic
       relations (under-determined with no compensating relations).
    3. ODE equations > state variables (over-determined).
    """
    has_operators = bool(data.get("operators"))
    has_coupling = bool(data.get("coupling"))
    has_loaders = bool(data.get("data_loaders"))
    has_external = has_operators or has_coupling or has_loaders

    for mname, m in data.get("models", {}).items():
        state_vars = {n for n, v in m.get("variables", {}).items() if v.get("type") == "state"}
        observed_vars = {n for n, v in m.get("variables", {}).items() if v.get("type") == "observed"}
        eqs = m.get("equations", [])
        ode_lhs_vars = []
        for eq in eqs:
            lhs = eq.get("lhs")
            if isinstance(lhs, dict) and lhs.get("op") == "D":
                args = lhs.get("args", [])
                if args and isinstance(args[0], str):
                    ode_lhs_vars.append(args[0])

        if has_external:
            continue

        # Case 1: state vars but zero equations
        if state_vars and not eqs:
            errors.append(
                f"models/{mname}: has {len(state_vars)} state variables but no equations"
            )
            continue

        # Case 2: more ODE equations than state variables (over-determined)
        if len(ode_lhs_vars) > len(state_vars):
            errors.append(
                f"models/{mname}: equation count mismatch — {len(ode_lhs_vars)} ODE equations for {len(state_vars)} state variables (over-determined)"
            )
            continue

        # Case 3: total equations less than state variables AND no observed vars
        # to provide algebraic relations
        if len(eqs) < len(state_vars) and not observed_vars:
            errors.append(
                f"models/{mname}: equation count mismatch — {len(eqs)} equations for {len(state_vars)} state variables (under-determined, no algebraic relations)"
            )


def _check_operator_state_coverage(data: Dict[str, Any], errors: List[str]) -> None:
    """
    When a file declares operators, every state variable in each model must be
    covered by either an equation (ODE or assignment) or an operator's modifies list.
    """
    if not data.get("operators"):
        return
    op_modifies = set()
    for op in data.get("operators", {}).values():
        op_modifies.update(op.get("modifies", []) or [])
    for mname, m in data.get("models", {}).items():
        state_vars = [n for n, v in m.get("variables", {}).items() if v.get("type") == "state"]
        eq_lhs_vars = set()
        for eq in m.get("equations", []):
            lhs = eq.get("lhs")
            if isinstance(lhs, dict) and lhs.get("op") == "D":
                args = lhs.get("args", [])
                if args and isinstance(args[0], str):
                    eq_lhs_vars.add(args[0])
            elif isinstance(lhs, str):
                eq_lhs_vars.add(lhs)
        uncovered = [s for s in state_vars if s not in eq_lhs_vars and s not in op_modifies]
        if uncovered:
            errors.append(
                f"models/{mname}: state variables {uncovered} are not covered by any equation or operator's modifies list"
            )


def _check_reaction_systems(data: Dict[str, Any], errors: List[str]) -> None:
    """Validate reaction system: substrates/products are declared species, rate refs valid."""
    for rsname, rs in data.get("reaction_systems", {}).items():
        species = set(rs.get("species", {}).keys())
        params = set(rs.get("parameters", {}).keys())
        valid_rate_syms = species | params | _BUILTIN_SYMBOLS
        for ri, reaction in enumerate(rs.get("reactions", [])):
            substrates = reaction.get("substrates")
            products = reaction.get("products")
            # Reaction has both substrates and products explicitly null is invalid
            if "substrates" in reaction and "products" in reaction \
                    and substrates is None and products is None:
                errors.append(
                    f"reaction_systems/{rsname}/reactions[{ri}]: reaction has both substrates and products as null"
                )
                continue
            # Check substrate/product species are declared
            for s in substrates or []:
                if isinstance(s, dict):
                    sp = s.get("species")
                    if sp and sp not in species:
                        errors.append(
                            f"reaction_systems/{rsname}/reactions[{ri}]: substrate species '{sp}' not declared"
                        )
            for p in products or []:
                if isinstance(p, dict):
                    sp = p.get("species")
                    if sp and sp not in species:
                        errors.append(
                            f"reaction_systems/{rsname}/reactions[{ri}]: product species '{sp}' not declared"
                        )
            # Check rate expression references valid symbols
            rate = reaction.get("rate")
            if rate is not None:
                refs = []
                if isinstance(rate, str):
                    refs = [rate]
                elif isinstance(rate, dict):
                    refs = _walk_expression_strings(rate)
                for ref in refs:
                    if "." in ref:
                        continue  # Scoped refs handled elsewhere
                    if ref not in valid_rate_syms:
                        errors.append(
                            f"reaction_systems/{rsname}/reactions[{ri}]/rate: undefined reference '{ref}'"
                        )


def _check_event_references(data: Dict[str, Any], tables: Dict[str, Any], errors: List[str]) -> None:
    """Check that event affects/conditions reference declared variables."""
    for mname, m in data.get("models", {}).items():
        local_vars = set(m.get("variables", {}).keys())
        for ei, event in enumerate(m.get("discrete_events", []) + m.get("continuous_events", [])):
            for ai, affect in enumerate(event.get("affects", []) or []):
                if isinstance(affect, dict) and "lhs" in affect and isinstance(affect["lhs"], str):
                    name = affect["lhs"]
                    # Underscore-prefixed names are conventional placeholders
                    if name.startswith("_"):
                        continue
                    if name not in local_vars and name not in tables["global_symbols"]:
                        errors.append(
                            f"models/{mname}/events[{ei}]/affects[{ai}]: undefined variable '{name}'"
                        )


def _validate_structural(data: Dict[str, Any], file_path=None) -> None:
    """
    Perform post-schema structural validation.

    Raises SchemaValidationError if any structural problems are found.
    """
    errors: List[str] = []

    # Operator arity check (walk all expressions)
    def walk_for_arity(obj, path):
        if isinstance(obj, dict):
            if "op" in obj and "args" in obj:
                _check_expression_arity(obj, errors, path)
                return
            for k, v in obj.items():
                walk_for_arity(v, f"{path}/{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk_for_arity(v, f"{path}[{i}]")

    walk_for_arity(data, "")

    tables = _build_symbol_tables(data)

    _check_variable_references(data, tables, errors)
    _check_coupling_references(data, tables, errors)
    _check_circular_references(data, tables, errors)
    _check_data_loader_variables(data, errors)
    _check_discrete_parameters(data, errors)
    _check_metadata_formats(data, errors)
    _check_temporal_resolution(data, errors)
    # Subsystem ref existence/parse is checked by resolve_subsystem_refs after
    # structural validation, which raises SubsystemRefError with richer context.
    _check_unit_consistency(data, tables, errors)
    _check_event_references(data, tables, errors)
    _check_equation_balance(data, errors)
    _check_operator_state_coverage(data, errors)
    _check_reaction_systems(data, errors)

    if errors:
        raise SchemaValidationError(
            "Structural validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )


def load(path_or_string: Union[str, Path, dict]) -> EsmFile:
    """
    Load an ESM file from a file path, JSON string, or dict.

    Args:
        path_or_string: File path to JSON file, JSON string, or parsed dict

    Returns:
        EsmFile object with parsed data

    Raises:
        json.JSONDecodeError: If the JSON is malformed
        jsonschema.ValidationError: If the JSON doesn't match the schema
        FileNotFoundError: If the file path doesn't exist
    """
    # Handle dict input directly
    base_path = os.getcwd()
    file_path = None
    if isinstance(path_or_string, dict):
        data = path_or_string
    elif isinstance(path_or_string, Path) or (isinstance(path_or_string, str) and os.path.exists(path_or_string)):
        # It's a file path
        file_path = Path(path_or_string)
        base_path = str(file_path.parent.resolve())
        with open(path_or_string, 'r') as f:
            data = json.load(f)
    else:
        # It's a JSON string
        data = json.loads(path_or_string)

    # Strip top-level events (not allowed by schema, but accepted for tooling roundtrip)
    top_continuous_events = data.pop("continuous_events", None) if isinstance(data, dict) else None
    top_discrete_events = data.pop("discrete_events", None) if isinstance(data, dict) else None

    # Load and validate against schema
    schema = _get_schema()
    try:
        validate(data, schema)
    except jsonschema.ValidationError as e:
        raise SchemaValidationError(str(e)) from e

    # Check version compatibility
    _check_version_compatibility(data.get("esm", ""))

    # Structural validation
    _validate_structural(data, file_path=file_path)

    # Parse into ESM objects
    esm_file = _parse_esm_data(data)

    # Resolve subsystem references
    resolve_subsystem_refs(esm_file, base_path)

    # Append top-level events that were stripped earlier
    if top_continuous_events:
        for ev in top_continuous_events:
            esm_file.events.append(_parse_continuous_event(ev))
    if top_discrete_events:
        for ev in top_discrete_events:
            esm_file.events.append(_parse_discrete_event(ev))

    return esm_file


