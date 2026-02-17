"""
ESM Format serialization module.

This module provides functions to serialize ESM format objects to JSON,
with optional file writing capability.
"""

import json
from pathlib import Path
from typing import Union, Dict, Any, Optional

from .esm_types import (
    EsmFile, Metadata, Model, ReactionSystem, ModelVariable, Equation,
    Species, Parameter, Reaction, ExprNode, Expr, AffectEquation,
    ContinuousEvent, DiscreteEvent, DiscreteEventTrigger, FunctionalAffect,
    DataLoader, DataLoaderType, Operator, OperatorType,
    CouplingEntry, CouplingType, Domain, Solver, SolverType,
    Reference, TemporalDomain, SpatialDimension, CoordinateTransform,
    InitialCondition, BoundaryCondition
)


def _serialize_expression(expr: Expr) -> Union[int, float, str, Dict[str, Any]]:
    """Serialize an expression to JSON-compatible format."""
    if isinstance(expr, (int, float, str)):
        return expr
    elif isinstance(expr, ExprNode):
        result = {
            "op": expr.op,
            "args": [_serialize_expression(arg) for arg in expr.args]
        }
        if expr.wrt is not None:
            result["wrt"] = expr.wrt
        if expr.dim is not None:
            result["dim"] = expr.dim
        return result
    else:
        raise ValueError(f"Invalid expression type: {type(expr)}")


def _serialize_equation(equation: Equation) -> Dict[str, Any]:
    """Serialize an equation to JSON-compatible format."""
    return {
        "lhs": _serialize_expression(equation.lhs),
        "rhs": _serialize_expression(equation.rhs)
    }


def _serialize_affect_equation(affect: AffectEquation) -> Dict[str, Any]:
    """Serialize an affect equation to JSON-compatible format."""
    return {
        "lhs": affect.lhs,
        "rhs": _serialize_expression(affect.rhs)
    }


def _serialize_model_variable(variable: ModelVariable) -> Dict[str, Any]:
    """Serialize a model variable to JSON-compatible format."""
    result = {
        "type": variable.type
    }
    if variable.units is not None:
        result["units"] = variable.units
    if variable.default is not None:
        result["default"] = variable.default
    if variable.description is not None:
        result["description"] = variable.description
    if variable.expression is not None:
        result["expression"] = _serialize_expression(variable.expression)
    return result


def _serialize_discrete_event_trigger(trigger: DiscreteEventTrigger) -> Dict[str, Any]:
    """Serialize a discrete event trigger to JSON-compatible format."""
    result = {"type": trigger.type}

    if trigger.type == "condition":
        result["expression"] = _serialize_expression(trigger.value)
    elif trigger.type == "periodic":
        result["interval"] = trigger.value
    elif trigger.type == "preset_times":
        result["times"] = trigger.value

    return result


def _serialize_continuous_event(event: ContinuousEvent) -> Dict[str, Any]:
    """Serialize a continuous event to JSON-compatible format."""
    result = {
        "conditions": [_serialize_expression(event.condition)],
        "affects": [_serialize_affect_equation(affect) for affect in event.affects]
    }
    if event.name:
        result["name"] = event.name
    if event.priority != 0:
        result["priority"] = event.priority

    return result


def _serialize_discrete_event(event: DiscreteEvent) -> Dict[str, Any]:
    """Serialize a discrete event to JSON-compatible format."""
    result = {
        "trigger": _serialize_discrete_event_trigger(event.trigger),
        "affects": [_serialize_affect_equation(affect) for affect in event.affects]
    }
    if event.name:
        result["name"] = event.name
    if event.priority != 0:
        result["priority"] = event.priority

    return result


def _serialize_model(model: Model) -> Dict[str, Any]:
    """Serialize a model to JSON-compatible format."""
    result = {}

    # Serialize variables
    if model.variables:
        result["variables"] = {
            name: _serialize_model_variable(var)
            for name, var in model.variables.items()
        }

    # Serialize equations
    if model.equations:
        result["equations"] = [_serialize_equation(eq) for eq in model.equations]

    return result


def _serialize_species(species: Species) -> Dict[str, Any]:
    """Serialize a species to JSON-compatible format."""
    result = {}
    if species.units is not None:
        result["units"] = species.units
    if species.description is not None:
        result["description"] = species.description
    return result


def _serialize_parameter(parameter: Parameter) -> Dict[str, Any]:
    """Serialize a parameter to JSON-compatible format."""
    result = {}
    if parameter.units is not None:
        result["units"] = parameter.units
    if parameter.description is not None:
        result["description"] = parameter.description
    if isinstance(parameter.value, (int, float)):
        result["default"] = parameter.value
    return result


def _serialize_reaction(reaction: Reaction) -> Dict[str, Any]:
    """Serialize a reaction to JSON-compatible format."""
    result = {
        "id": reaction.name
    }

    if reaction.name:
        result["name"] = reaction.name

    # Serialize substrates (reactants)
    if reaction.reactants:
        result["substrates"] = [
            {"species": species, "stoichiometry": int(coeff)}
            for species, coeff in reaction.reactants.items()
        ]
    else:
        result["substrates"] = None

    # Serialize products
    if reaction.products:
        result["products"] = [
            {"species": species, "stoichiometry": int(coeff)}
            for species, coeff in reaction.products.items()
        ]
    else:
        result["products"] = None

    # Serialize rate
    if reaction.rate_constant is not None:
        result["rate"] = _serialize_expression(reaction.rate_constant)

    return result


def _serialize_reaction_system(rs: ReactionSystem) -> Dict[str, Any]:
    """Serialize a reaction system to JSON-compatible format."""
    result = {}

    # Serialize species
    if rs.species:
        result["species"] = {
            sp.name: _serialize_species(sp)
            for sp in rs.species
        }
    else:
        result["species"] = {}

    # Serialize parameters
    if rs.parameters:
        result["parameters"] = {
            param.name: _serialize_parameter(param)
            for param in rs.parameters
        }
    else:
        result["parameters"] = {}

    # Serialize reactions
    if rs.reactions:
        result["reactions"] = [_serialize_reaction(reaction) for reaction in rs.reactions]
    else:
        result["reactions"] = []

    return result


def _serialize_reference(reference: Reference) -> Dict[str, Any]:
    """Serialize a reference to JSON-compatible format."""
    result = {}
    if reference.title:
        result["citation"] = reference.title
    if reference.doi is not None:
        result["doi"] = reference.doi
    if reference.url is not None:
        result["url"] = reference.url
    return result


def _serialize_metadata(metadata: Metadata) -> Dict[str, Any]:
    """Serialize metadata to JSON-compatible format."""
    result = {
        "name": metadata.title
    }

    if metadata.description is not None:
        result["description"] = metadata.description
    if metadata.authors:
        result["authors"] = metadata.authors
    if metadata.created is not None:
        result["created"] = metadata.created
    if metadata.modified is not None:
        result["modified"] = metadata.modified
    if metadata.keywords:
        result["tags"] = metadata.keywords
    if metadata.references:
        result["references"] = [_serialize_reference(ref) for ref in metadata.references]

    return result


def _serialize_domain(domain: Domain) -> Dict[str, Any]:
    """Serialize a domain to JSON-compatible format."""
    result = {}

    if domain.independent_variable:
        result["independent_variable"] = domain.independent_variable

    # Serialize temporal domain
    if domain.temporal:
        temporal_data = {
            "start": domain.temporal.start,
            "end": domain.temporal.end
        }
        if domain.temporal.reference_time:
            temporal_data["reference_time"] = domain.temporal.reference_time
        result["temporal"] = temporal_data

    # Serialize spatial domain
    if domain.spatial:
        spatial_data = {}
        for dim_name, dim_spec in domain.spatial.items():
            dim_data = {
                "min": dim_spec.min,
                "max": dim_spec.max,
                "units": dim_spec.units
            }
            if dim_spec.grid_spacing is not None:
                dim_data["grid_spacing"] = dim_spec.grid_spacing
            spatial_data[dim_name] = dim_data
        result["spatial"] = spatial_data

    # Serialize coordinate transforms
    if domain.coordinate_transforms:
        result["coordinate_transforms"] = [
            {
                "id": transform.id,
                "description": transform.description,
                "dimensions": transform.dimensions
            }
            for transform in domain.coordinate_transforms
        ]

    # Serialize spatial reference
    if domain.spatial_ref:
        result["spatial_ref"] = domain.spatial_ref

    # Serialize initial conditions
    if domain.initial_conditions:
        ic = domain.initial_conditions
        ic_data = {"type": ic.type.value}

        if ic.value is not None:
            ic_data["value"] = ic.value
        if ic.function is not None:
            ic_data["function"] = ic.function
        if ic.data_source is not None:
            ic_data["path"] = ic.data_source  # Schema uses "path" for data source

        result["initial_conditions"] = ic_data

    # Serialize boundary conditions
    if domain.boundary_conditions:
        bc_data = []
        for bc in domain.boundary_conditions:
            bc_dict = {
                "type": bc.type.value,
                "dimensions": bc.dimensions
            }
            if bc.value is not None:
                bc_dict["value"] = bc.value
            if bc.function is not None:
                bc_dict["function"] = bc.function
            bc_data.append(bc_dict)
        result["boundary_conditions"] = bc_data

    return result


def _serialize_data_loader(loader: DataLoader) -> Dict[str, Any]:
    """Serialize a data loader to JSON-compatible format."""
    result = {}

    # Map our enum to schema types
    type_mapping = {
        DataLoaderType.NETCDF: "gridded_data",
        DataLoaderType.CSV: "emissions",  # Default to emissions for CSV
        DataLoaderType.REMOTE: "callback"
    }
    result["type"] = type_mapping.get(loader.type, "emissions")

    # Schema uses loader_id for source
    if loader.source:
        result["loader_id"] = loader.source

    # Schema uses config for format_options
    if loader.format_options:
        result["config"] = loader.format_options

    # Schema uses provides for variables
    if loader.variables:
        result["provides"] = {var: {} for var in loader.variables}

    return result


def _serialize_operator(operator: Operator) -> Dict[str, Any]:
    """Serialize an operator to JSON-compatible format."""
    result = {}

    # Schema requires operator_id
    result["operator_id"] = operator.name or "default_operator"

    # Schema uses config for parameters
    if operator.parameters:
        result["config"] = operator.parameters

    # Schema uses needed_vars for input_variables
    if operator.input_variables:
        result["needed_vars"] = operator.input_variables

    # Schema uses modifies for output_variables
    if operator.output_variables:
        result["modifies"] = operator.output_variables

    return result


def _serialize_coupling_entry(coupling: CouplingEntry) -> Dict[str, Any]:
    """Serialize a coupling entry to JSON-compatible format."""
    result = {}

    # Map our enum to schema types (using variable_map as default)
    result["type"] = "variable_map"

    # Create from/to strings from model and variable names
    if coupling.source_variables and coupling.target_variables:
        result["from"] = f"{coupling.source_model}.{coupling.source_variables[0]}"
        result["to"] = f"{coupling.target_model}.{coupling.target_variables[0]}"

    return result


def _serialize_solver(solver: Solver) -> Dict[str, Any]:
    """Serialize a solver to JSON-compatible format."""
    result = {}

    # Schema uses strategy for algorithm
    if solver.algorithm:
        result["strategy"] = solver.algorithm

    # Schema uses config for parameters
    config = {}
    if solver.parameters:
        config.update(solver.parameters)

    # Add tolerances to config
    if solver.tolerances:
        stiff_kwargs = {}
        if "absolute" in solver.tolerances:
            stiff_kwargs["abstol"] = solver.tolerances["absolute"]
        if "relative" in solver.tolerances:
            stiff_kwargs["reltol"] = solver.tolerances["relative"]
        if stiff_kwargs:
            config["stiff_kwargs"] = stiff_kwargs

    if config:
        result["config"] = config

    return result


def _serialize_esm_file(esm_file: EsmFile) -> Dict[str, Any]:
    """Serialize an ESM file to JSON-compatible format."""
    result = {
        "esm": esm_file.version,
        "metadata": _serialize_metadata(esm_file.metadata)
    }

    # Serialize models
    if esm_file.models:
        result["models"] = {
            model.name: _serialize_model(model)
            for model in esm_file.models
        }

    # Serialize reaction systems
    if esm_file.reaction_systems:
        result["reaction_systems"] = {
            rs.name: _serialize_reaction_system(rs)
            for rs in esm_file.reaction_systems
        }

    # Serialize domain (only first domain for now, as schema expects single domain)
    if esm_file.domains:
        result["domain"] = _serialize_domain(esm_file.domains[0])

    # Serialize data loaders
    if esm_file.data_loaders:
        result["data_loaders"] = {
            loader.name: _serialize_data_loader(loader)
            for loader in esm_file.data_loaders
        }

    # Serialize operators
    if esm_file.operators:
        result["operators"] = {
            operator.name: _serialize_operator(operator)
            for operator in esm_file.operators
        }

    # Serialize couplings
    if esm_file.couplings:
        result["coupling"] = [
            _serialize_coupling_entry(coupling)
            for coupling in esm_file.couplings
        ]

    # Serialize solver (only first solver for now, as schema expects single solver)
    if esm_file.solvers:
        result["solver"] = _serialize_solver(esm_file.solvers[0])

    # Serialize events
    if esm_file.events:
        # For now, serialize events as a simple list at top level
        # TODO: Properly distribute events back to their parent models/reaction_systems
        continuous_events = []
        discrete_events = []

        for event in esm_file.events:
            if isinstance(event, ContinuousEvent):
                continuous_events.append(_serialize_continuous_event(event))
            elif isinstance(event, DiscreteEvent):
                discrete_events.append(_serialize_discrete_event(event))

        if continuous_events:
            result["continuous_events"] = continuous_events
        if discrete_events:
            result["discrete_events"] = discrete_events

    return result


def save(esm_file: EsmFile, path: Optional[Union[str, Path]] = None) -> str:
    """
    Serialize an ESM file to JSON string, optionally writing to file.

    Args:
        esm_file: The EsmFile object to serialize
        path: Optional file path to write the JSON to

    Returns:
        JSON string representation of the ESM file

    Raises:
        IOError: If writing to file fails
    """
    # Serialize to dictionary
    data = _serialize_esm_file(esm_file)

    # Convert to JSON string with nice formatting
    json_str = json.dumps(data, indent=2, ensure_ascii=False)

    # Write to file if path provided
    if path is not None:
        with open(path, 'w') as f:
            f.write(json_str)

    return json_str