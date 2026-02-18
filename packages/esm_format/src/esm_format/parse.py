"""
ESM Format parsing module.

This module provides functions to parse JSON data into ESM format objects,
with schema validation using the bundled esm-schema.json file.
"""

import json
import os
from pathlib import Path
from typing import Union, Dict, Any, List
from dataclasses import fields
from enum import Enum

import jsonschema
from jsonschema import validate

from .esm_types import (
    EsmFile, Metadata, Model, ReactionSystem, ModelVariable, Equation,
    Species, Parameter, Reaction, ExprNode, Expr, AffectEquation,
    ContinuousEvent, DiscreteEvent, DiscreteEventTrigger, FunctionalAffect,
    DataLoader, DataLoaderType, Operator, OperatorType,
    CouplingEntry, CouplingType, ConnectorEquation, Connector, Domain, Solver, SolverType,
    Reference, TemporalDomain, SpatialDimension, CoordinateTransform,
    InitialCondition, InitialConditionType, BoundaryCondition, BoundaryConditionType
)


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails."""
    pass


class UnsupportedVersionError(Exception):
    """Exception raised when ESM version is not supported."""
    pass


def _get_schema() -> Dict[str, Any]:
    """Load the bundled ESM schema."""
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
        return ExprNode(op=op, args=args, wrt=wrt, dim=dim)
    else:
        raise ValueError(f"Invalid expression data: {expr_data}")


def _parse_equation(eq_data: Dict[str, Any]) -> Equation:
    """Parse an equation from JSON data."""
    lhs = _parse_expression(eq_data["lhs"])
    rhs = _parse_expression(eq_data["rhs"])
    return Equation(lhs=lhs, rhs=rhs)


def _parse_affect_equation(affect_data: Dict[str, Any]) -> AffectEquation:
    """Parse an affect equation from JSON data."""
    lhs = affect_data["lhs"]  # string
    rhs = _parse_expression(affect_data["rhs"])
    return AffectEquation(lhs=lhs, rhs=rhs)


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
    affects = [_parse_affect_equation(affect) for affect in event_data["affects"]]
    priority = event_data.get("priority", 0)

    # Parse new fields
    affect_neg = None
    if "affect_neg" in event_data:
        affect_neg = [_parse_affect_equation(affect) for affect in event_data["affect_neg"]]

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
    if "affects" in event_data:
        affects = [_parse_affect_equation(affect) for affect in event_data["affects"]]
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

    # Create model (name is not in the schema, we'll use empty string)
    model = Model(name="", variables=variables, equations=equations)
    return model


def _parse_species(species_data: Dict[str, Any]) -> Species:
    """Parse a species from JSON data."""
    return Species(
        name="",  # Name comes from the key
        formula=None,
        mass=None,
        units=species_data.get("units"),
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

    return ReactionSystem(
        name="",  # Name comes from the key
        species=species,
        parameters=parameters,
        reactions=reactions
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


def _parse_data_loader(loader_data: Dict[str, Any]) -> DataLoader:
    """Parse a data loader from JSON data."""
    name = ""  # Name comes from the key

    # Try to match schema type to our enum, fallback to CSV
    schema_type = loader_data["type"]
    type_mapping = {
        "gridded_data": DataLoaderType.NETCDF,
        "emissions": DataLoaderType.CSV,
        "timeseries": DataLoaderType.CSV,
        "static": DataLoaderType.CSV,
        "callback": DataLoaderType.REMOTE
    }
    loader_type = type_mapping.get(schema_type, DataLoaderType.CSV)

    # Schema uses loader_id, we use source
    source = loader_data.get("loader_id", "")

    # Schema uses config, we use format_options
    format_options = loader_data.get("config", {})

    # Extract variable names from provides
    variables = []
    if "provides" in loader_data:
        variables = list(loader_data["provides"].keys())

    return DataLoader(
        name=name,
        type=loader_type,
        source=source,
        format_options=format_options,
        variables=variables
    )


def _parse_operator(operator_data: Dict[str, Any]) -> Operator:
    """Parse an operator from JSON data."""
    name = ""  # Name comes from the key

    # Schema doesn't have type enum, default to transformation
    operator_type = OperatorType.TRANSFORMATION

    # Schema uses config, we use parameters
    parameters = operator_data.get("config", {})

    # Schema uses needed_vars, we use input_variables
    input_variables = operator_data.get("needed_vars", [])

    # Schema uses modifies, we use output_variables
    output_variables = operator_data.get("modifies", [])

    return Operator(
        name=name,
        type=operator_type,
        parameters=parameters,
        input_variables=input_variables,
        output_variables=output_variables
    )


def _parse_coupling_entry(coupling_data: Dict[str, Any]) -> CouplingEntry:
    """Parse a coupling entry from JSON data."""
    # Get coupling type from schema
    schema_type = coupling_data["type"]

    # Map schema types to our enum
    type_mapping = {
        "operator_compose": CouplingType.OPERATOR_COMPOSE,
        "couple2": CouplingType.COUPLE2,
        "variable_map": CouplingType.VARIABLE_MAP,
        "operator_apply": CouplingType.OPERATOR_APPLY,
        "callback": CouplingType.CALLBACK,
        "event": CouplingType.EVENT,
    }

    if schema_type not in type_mapping:
        raise ValueError(f"Unknown coupling type: {schema_type}")

    coupling_type = type_mapping[schema_type]

    # Create base coupling entry
    entry = CouplingEntry(
        coupling_type=coupling_type,
        description=coupling_data.get("description")
    )

    # Parse type-specific fields
    if coupling_type == CouplingType.OPERATOR_COMPOSE:
        entry.systems = coupling_data.get("systems", [])
        entry.translate = coupling_data.get("translate", {})

    elif coupling_type == CouplingType.COUPLE2:
        entry.systems = coupling_data.get("systems", [])
        entry.coupletype_pair = coupling_data.get("coupletype_pair", [])

        # Parse connector
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
            entry.connector = Connector(equations=equations)

    elif coupling_type == CouplingType.VARIABLE_MAP:
        entry.from_var = coupling_data.get("from")
        entry.to_var = coupling_data.get("to")
        entry.transform = coupling_data.get("transform")
        entry.factor = coupling_data.get("factor")

    elif coupling_type == CouplingType.OPERATOR_APPLY:
        entry.operator = coupling_data.get("operator")

    elif coupling_type == CouplingType.CALLBACK:
        entry.callback_id = coupling_data.get("callback_id")
        entry.config = coupling_data.get("config", {})

    elif coupling_type == CouplingType.EVENT:
        entry.event_type = coupling_data.get("event_type")

        # Parse conditions
        if "conditions" in coupling_data:
            entry.conditions = [_parse_expression(cond) for cond in coupling_data["conditions"]]

        # Parse trigger for discrete events
        if "trigger" in coupling_data:
            entry.trigger = _parse_discrete_event_trigger(coupling_data["trigger"])

        # Parse affects
        if "affects" in coupling_data:
            entry.affects = [_parse_affect_equation(affect) for affect in coupling_data["affects"]]

        # Parse affect_neg
        if "affect_neg" in coupling_data and coupling_data["affect_neg"] is not None:
            entry.affect_neg = [_parse_affect_equation(affect) for affect in coupling_data["affect_neg"]]

        # Parse other fields
        entry.discrete_parameters = coupling_data.get("discrete_parameters", [])
        entry.root_find = coupling_data.get("root_find")
        entry.reinitialize = coupling_data.get("reinitialize")

    return entry


def _parse_solver(solver_data: Dict[str, Any]) -> Solver:
    """Parse a solver from JSON data."""
    name = ""  # Name can be provided or left empty

    # Schema doesn't have type enum, default to ODE
    solver_type = SolverType.ODE

    # Schema uses strategy
    algorithm = solver_data.get("strategy", "")

    # Schema uses config
    parameters = solver_data.get("config", {})

    # Extract tolerances from config if available
    tolerances = {}
    if "config" in solver_data and "stiff_kwargs" in solver_data["config"]:
        stiff_kwargs = solver_data["config"]["stiff_kwargs"]
        if "abstol" in stiff_kwargs:
            tolerances["absolute"] = stiff_kwargs["abstol"]
        if "reltol" in stiff_kwargs:
            tolerances["relative"] = stiff_kwargs["reltol"]

    return Solver(
        name=name,
        type=solver_type,
        algorithm=algorithm,
        parameters=parameters,
        tolerances=tolerances
    )


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
                units=dim_data["units"],
                grid_spacing=dim_data.get("grid_spacing")
            )

    # Parse coordinate transforms
    if "coordinate_transforms" in domain_data:
        for transform_data in domain_data["coordinate_transforms"]:
            transform = CoordinateTransform(
                id=transform_data["id"],
                description=transform_data["description"],
                dimensions=transform_data["dimensions"]
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
            "per_variable": InitialConditionType.CONSTANT,  # Treat as constant for now
            "from_file": InitialConditionType.DATA
        }

        ic_type = type_mapping.get(ic_type_str, InitialConditionType.CONSTANT)

        # Extract appropriate fields based on type
        value = ic_data.get("value")
        function = None
        data_source = ic_data.get("path")  # Schema uses "path" for file source

        domain.initial_conditions = InitialCondition(
            type=ic_type,
            value=value,
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

    # Parse domain if present
    domains = []
    if "domain" in data:
        domain = _parse_domain(data["domain"])
        _validate_domain(domain)
        domains.append(domain)

    # Parse data loaders
    data_loaders = []
    if "data_loaders" in data:
        for loader_name, loader_data in data["data_loaders"].items():
            loader = _parse_data_loader(loader_data)
            loader.name = loader_name
            data_loaders.append(loader)

    # Parse operators
    operators = []
    if "operators" in data:
        for op_name, op_data in data["operators"].items():
            operator = _parse_operator(op_data)
            operator.name = op_name
            operators.append(operator)

    # Parse coupling entries
    couplings = []
    if "coupling" in data:
        for coupling_data in data["coupling"]:
            couplings.append(_parse_coupling_entry(coupling_data))

    # Parse solver
    solvers = []
    if "solver" in data:
        solver = _parse_solver(data["solver"])
        solvers.append(solver)

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
        couplings=couplings,
        domains=domains,
        solvers=solvers
    )


def load(path_or_string: Union[str, Path]) -> EsmFile:
    """
    Load an ESM file from a file path or JSON string.

    Args:
        path_or_string: File path to JSON file or JSON string

    Returns:
        EsmFile object with parsed data

    Raises:
        json.JSONDecodeError: If the JSON is malformed
        jsonschema.ValidationError: If the JSON doesn't match the schema
        FileNotFoundError: If the file path doesn't exist
    """
    # Determine if input is a file path or JSON string
    if isinstance(path_or_string, Path) or (isinstance(path_or_string, str) and os.path.exists(path_or_string)):
        # It's a file path
        with open(path_or_string, 'r') as f:
            data = json.load(f)
    else:
        # It's a JSON string
        data = json.loads(path_or_string)

    # Load and validate against schema
    schema = _get_schema()
    validate(data, schema)

    # Parse into ESM objects
    return _parse_esm_data(data)