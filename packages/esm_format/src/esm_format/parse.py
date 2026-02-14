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

from .types import (
    EsmFile, Metadata, Model, ReactionSystem, ModelVariable, Equation,
    Species, Parameter, Reaction, ExprNode, Expr, AffectEquation,
    ContinuousEvent, DiscreteEvent, DiscreteEventTrigger, FunctionalAffect,
    DataLoader, DataLoaderType, Operator, OperatorType,
    CouplingEntry, CouplingType, Domain, Solver, SolverType,
    Reference
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

    return ContinuousEvent(
        name=name,
        condition=conditions[0],  # For now, take first condition
        affects=affects,
        priority=priority
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


def _parse_esm_data(data: Dict[str, Any]) -> EsmFile:
    """Parse ESM data from validated JSON."""
    # Parse metadata
    metadata = _parse_metadata(data["metadata"])

    # Parse models
    models = []
    if "models" in data:
        for model_name, model_data in data["models"].items():
            model = _parse_model(model_data)
            model.name = model_name
            models.append(model)

    # Parse reaction systems
    reaction_systems = []
    if "reaction_systems" in data:
        for rs_name, rs_data in data["reaction_systems"].items():
            rs = _parse_reaction_system(rs_data)
            rs.name = rs_name
            reaction_systems.append(rs)

    # For now, we'll leave other fields empty as they require more complex parsing
    events = []
    data_loaders = []
    operators = []
    couplings = []
    domains = []
    solvers = []

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