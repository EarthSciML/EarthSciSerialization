"""
Expression substitution and variable replacement functions.
"""

from typing import Dict, Union
from .esm_types import Expr, ExprNode, Model, ReactionSystem, ModelVariable, Equation, AffectEquation, Parameter, Reaction


def substitute(expr: Expr, bindings: Dict[str, Expr]) -> Expr:
    """
    Recursively substitute variables in an expression with their bindings.

    Args:
        expr: Expression to perform substitutions on
        bindings: Dictionary mapping variable names to replacement expressions

    Returns:
        Expression with variables substituted
    """
    if isinstance(expr, str):
        # String is a variable name - substitute if binding exists
        return bindings.get(expr, expr)
    elif isinstance(expr, (int, float)):
        # Numbers are unchanged
        return expr
    elif isinstance(expr, ExprNode):
        # Recursively substitute in all arguments
        substituted_args = [substitute(arg, bindings) for arg in expr.args]
        return ExprNode(
            op=expr.op,
            args=substituted_args,
            wrt=expr.wrt,
            dim=expr.dim
        )
    else:
        # Unknown type, return unchanged
        return expr


def substitute_in_model(model: Model, bindings: Dict[str, Expr]) -> Model:
    """
    Apply substitutions to all expressions in a model.

    Args:
        model: Model to perform substitutions on
        bindings: Dictionary mapping variable names to replacement expressions

    Returns:
        New model with substitutions applied
    """
    # Substitute in model variables
    new_variables = {}
    for name, var in model.variables.items():
        new_expression = None
        if var.expression is not None:
            new_expression = substitute(var.expression, bindings)

        # Create new variable with substituted expression
        new_var = ModelVariable(
            type=var.type,
            units=var.units,
            default=var.default,
            description=var.description,
            expression=new_expression
        )
        new_variables[name] = new_var

    # Substitute in equations
    new_equations = []
    for eq in model.equations:
        new_lhs = substitute(eq.lhs, bindings)
        new_rhs = substitute(eq.rhs, bindings)
        new_equations.append(Equation(lhs=new_lhs, rhs=new_rhs))

    return Model(
        name=model.name,
        variables=new_variables,
        equations=new_equations,
        metadata=model.metadata.copy()  # Shallow copy metadata
    )


def substitute_in_reaction_system(system: ReactionSystem, bindings: Dict[str, Expr]) -> ReactionSystem:
    """
    Apply substitutions to all expressions in a reaction system.

    Args:
        system: Reaction system to perform substitutions on
        bindings: Dictionary mapping variable names to replacement expressions

    Returns:
        New reaction system with substitutions applied
    """
    # Substitute in parameters
    new_parameters = []
    for param in system.parameters:
        new_value = param.value
        if not isinstance(param.value, (int, float)):
            # Parameter value is an expression
            new_value = substitute(param.value, bindings)

        new_param = Parameter(
            name=param.name,
            value=new_value,
            units=param.units,
            description=param.description,
            uncertainty=param.uncertainty
        )
        new_parameters.append(new_param)

    # Substitute in reactions
    new_reactions = []
    for reaction in system.reactions:
        new_rate_constant = reaction.rate_constant
        if reaction.rate_constant is not None and not isinstance(reaction.rate_constant, (int, float)):
            # Rate constant is an expression
            new_rate_constant = substitute(reaction.rate_constant, bindings)

        new_reaction = Reaction(
            name=reaction.name,
            reactants=reaction.reactants.copy(),
            products=reaction.products.copy(),
            rate_constant=new_rate_constant,
            conditions=reaction.conditions.copy()
        )
        new_reactions.append(new_reaction)

    return ReactionSystem(
        name=system.name,
        species=system.species.copy(),  # Species don't contain expressions typically
        parameters=new_parameters,
        reactions=new_reactions
    )