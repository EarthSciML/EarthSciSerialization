//! Expression substitution utilities

use crate::{Expr, Model, ReactionSystem};
use crate::types::{ExpressionNode, Equation, Reaction};

/// Substitute variables in an expression
///
/// # Arguments
///
/// * `expr` - The expression to modify
/// * `substitutions` - Map from variable names to replacement expressions
///
/// # Returns
///
/// * New expression with substitutions applied
pub fn substitute(expr: &Expr, substitutions: &std::collections::HashMap<String, Expr>) -> Expr {
    match expr {
        Expr::Number(n) => Expr::Number(*n),
        Expr::Variable(var_name) => {
            if let Some(replacement) = substitutions.get(var_name) {
                replacement.clone()
            } else {
                Expr::Variable(var_name.clone())
            }
        },
        Expr::Operator(op_node) => {
            let new_args: Vec<Expr> = op_node.args.iter()
                .map(|arg| substitute(arg, substitutions))
                .collect();

            Expr::Operator(ExpressionNode {
                op: op_node.op.clone(),
                args: new_args,
                wrt: op_node.wrt.clone(),
                dim: op_node.dim.clone(),
            })
        }
    }
}

/// Substitute variables in all expressions within a model
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `substitutions` - Map from variable names to replacement expressions
///
/// # Returns
///
/// * New model with substitutions applied
pub fn substitute_in_model(
    model: &Model,
    substitutions: &std::collections::HashMap<String, Expr>
) -> Model {
    let new_equations = model.equations.iter()
        .map(|eq| Equation {
            lhs: substitute(&eq.lhs, substitutions),
            rhs: substitute(&eq.rhs, substitutions),
        })
        .collect();

    Model {
        name: model.name.clone(),
        variables: model.variables.clone(),
        equations: new_equations,
        discrete_events: model.discrete_events.clone(), // TODO: Substitute in discrete events too
        continuous_events: model.continuous_events.clone(), // TODO: Substitute in continuous events too
        description: model.description.clone(),
    }
}

/// Substitute variables in all expressions within a reaction system
///
/// # Arguments
///
/// * `reaction_system` - The reaction system to modify
/// * `substitutions` - Map from variable names to replacement expressions
///
/// # Returns
///
/// * New reaction system with substitutions applied
pub fn substitute_in_reaction_system(
    reaction_system: &ReactionSystem,
    substitutions: &std::collections::HashMap<String, Expr>
) -> ReactionSystem {
    let new_reactions = reaction_system.reactions.iter()
        .map(|rxn| Reaction {
            name: rxn.name.clone(),
            substrates: rxn.substrates.clone(),
            products: rxn.products.clone(),
            rate: substitute(&rxn.rate, substitutions),
            description: rxn.description.clone(),
        })
        .collect();

    ReactionSystem {
        name: reaction_system.name.clone(),
        species: reaction_system.species.clone(),
        reactions: new_reactions,
        description: reaction_system.description.clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn test_substitute_variable() {
        let mut subs = HashMap::new();
        subs.insert("x".to_string(), Expr::Number(42.0));

        let expr = Expr::Variable("x".to_string());
        let result = substitute(&expr, &subs);

        match result {
            Expr::Number(n) => assert_eq!(n, 42.0),
            _ => panic!("Expected number"),
        }
    }

    #[test]
    fn test_substitute_no_match() {
        let subs = HashMap::new();
        let expr = Expr::Variable("y".to_string());
        let result = substitute(&expr, &subs);

        match result {
            Expr::Variable(name) => assert_eq!(name, "y"),
            _ => panic!("Expected variable"),
        }
    }

    #[test]
    fn test_substitute_in_operator() {
        let mut subs = HashMap::new();
        subs.insert("x".to_string(), Expr::Number(2.0));
        subs.insert("y".to_string(), Expr::Number(3.0));

        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Variable("y".to_string()),
            ],
            wrt: None,
            dim: None,
        });

        let result = substitute(&expr, &subs);

        match result {
            Expr::Operator(op_node) => {
                assert_eq!(op_node.op, "+");
                assert_eq!(op_node.args.len(), 2);
                match &op_node.args[0] {
                    Expr::Number(n) => assert_eq!(*n, 2.0),
                    _ => panic!("Expected number"),
                }
                match &op_node.args[1] {
                    Expr::Number(n) => assert_eq!(*n, 3.0),
                    _ => panic!("Expected number"),
                }
            },
            _ => panic!("Expected operator"),
        }
    }
}