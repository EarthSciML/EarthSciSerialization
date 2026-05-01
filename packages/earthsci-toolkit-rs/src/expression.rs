//! Expression manipulation utilities

use crate::Expr;
use std::collections::HashSet;

/// Extract all free variables from an expression
///
/// # Arguments
///
/// * `expr` - The expression to analyze
///
/// # Returns
///
/// * Set of variable names referenced in the expression
pub fn free_variables(expr: &Expr) -> HashSet<String> {
    let mut vars = HashSet::new();
    collect_variables(expr, &mut vars);
    vars
}

/// Extract all free parameters from an expression
///
/// This is currently the same as free_variables since we don't distinguish
/// parameters from variables at the expression level.
///
/// # Arguments
///
/// * `expr` - The expression to analyze
///
/// # Returns
///
/// * Set of parameter names referenced in the expression
pub fn free_parameters(expr: &Expr) -> HashSet<String> {
    free_variables(expr)
}

/// Check if an expression contains a specific variable
///
/// # Arguments
///
/// * `expr` - The expression to search
/// * `var_name` - The variable name to look for
///
/// # Returns
///
/// * `true` if the variable is found, `false` otherwise
pub fn contains(expr: &Expr, var_name: &str) -> bool {
    match expr {
        Expr::Variable(name) => name == var_name,
        Expr::Operator(op_node) => op_node.args.iter().any(|arg| contains(arg, var_name)),
        Expr::Number(_) | Expr::Integer(_) => false,
    }
}

/// Simplify an expression (basic symbolic simplification)
///
/// # Arguments
///
/// * `expr` - The expression to simplify
///
/// # Returns
///
/// * Simplified expression
pub fn simplify(expr: &Expr) -> Expr {
    match expr {
        Expr::Number(n) => Expr::Number(*n),
        Expr::Integer(n) => Expr::Integer(*n),
        Expr::Variable(name) => Expr::Variable(name.clone()),
        Expr::Operator(op_node) => {
            let simplified_args: Vec<Expr> = op_node.args.iter().map(simplify).collect();

            simplify_operator(&op_node.op, &simplified_args)
        }
    }
}

fn collect_variables(expr: &Expr, vars: &mut HashSet<String>) {
    match expr {
        Expr::Variable(name) => {
            vars.insert(name.clone());
        }
        Expr::Operator(op_node) => {
            for arg in &op_node.args {
                collect_variables(arg, vars);
            }
        }
        Expr::Number(_) | Expr::Integer(_) => {
            // Numbers don't contain variables
        }
    }
}

fn simplify_operator(op: &str, args: &[Expr]) -> Expr {
    use crate::types::ExpressionNode;

    match op {
        "+" => {
            if args.len() == 2 {
                match (&args[0], &args[1]) {
                    // 0 + x = x
                    (Expr::Number(0.0), x) => x.clone(),
                    // x + 0 = x
                    (x, Expr::Number(0.0)) => x.clone(),
                    // a + b = (a + b) for numbers
                    (Expr::Number(a), Expr::Number(b)) => Expr::Number(a + b),
                    _ => Expr::Operator(ExpressionNode {
                        op: op.to_string(),
                        args: args.to_vec(),
                        wrt: None,
                        dim: None,
                        ..Default::default()
                    }),
                }
            } else {
                Expr::Operator(ExpressionNode {
                    op: op.to_string(),
                    args: args.to_vec(),
                    wrt: None,
                    dim: None,
                    ..Default::default()
                })
            }
        }
        "*" => {
            if args.len() == 2 {
                match (&args[0], &args[1]) {
                    // 0 * x = 0
                    (Expr::Number(0.0), _) => Expr::Number(0.0),
                    // x * 0 = 0
                    (_, Expr::Number(0.0)) => Expr::Number(0.0),
                    // 1 * x = x
                    (Expr::Number(1.0), x) => x.clone(),
                    // x * 1 = x
                    (x, Expr::Number(1.0)) => x.clone(),
                    // a * b = (a * b) for numbers
                    (Expr::Number(a), Expr::Number(b)) => Expr::Number(a * b),
                    _ => Expr::Operator(ExpressionNode {
                        op: op.to_string(),
                        args: args.to_vec(),
                        wrt: None,
                        dim: None,
                        ..Default::default()
                    }),
                }
            } else {
                Expr::Operator(ExpressionNode {
                    op: op.to_string(),
                    args: args.to_vec(),
                    wrt: None,
                    dim: None,
                    ..Default::default()
                })
            }
        }
        "^" => {
            if args.len() == 2 {
                match (&args[0], &args[1]) {
                    // x^0 = 1
                    (_, Expr::Number(0.0)) => Expr::Number(1.0),
                    // x^1 = x
                    (x, Expr::Number(1.0)) => x.clone(),
                    // a^b = (a^b) for numbers
                    (Expr::Number(a), Expr::Number(b)) => Expr::Number(a.powf(*b)),
                    _ => Expr::Operator(ExpressionNode {
                        op: op.to_string(),
                        args: args.to_vec(),
                        wrt: None,
                        dim: None,
                        ..Default::default()
                    }),
                }
            } else {
                Expr::Operator(ExpressionNode {
                    op: op.to_string(),
                    args: args.to_vec(),
                    wrt: None,
                    dim: None,
                    ..Default::default()
                })
            }
        }
        _ => Expr::Operator(ExpressionNode {
            op: op.to_string(),
            args: args.to_vec(),
            wrt: None,
            dim: None,
            ..Default::default()
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::substitute::substitute;
    use crate::types::ExpressionNode;
    use std::collections::HashMap;

    #[test]
    fn test_free_variables() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Variable("y".to_string()),
            ],
            wrt: None,
            dim: None,
            ..Default::default()
        });

        let vars = free_variables(&expr);
        assert_eq!(vars.len(), 2);
        assert!(vars.contains("x"));
        assert!(vars.contains("y"));
    }

    #[test]
    fn test_contains() {
        let expr = Expr::Operator(ExpressionNode {
            op: "*".to_string(),
            args: vec![Expr::Number(2.0), Expr::Variable("x".to_string())],
            wrt: None,
            dim: None,
            ..Default::default()
        });

        assert!(contains(&expr, "x"));
        assert!(!contains(&expr, "y"));
    }

    #[test]
    fn test_simplify_zero_addition() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![Expr::Variable("x".to_string()), Expr::Number(0.0)],
            wrt: None,
            dim: None,
            ..Default::default()
        });

        let simplified = simplify(&expr);
        match simplified {
            Expr::Variable(name) => assert_eq!(name, "x"),
            _ => panic!("Expected variable 'x'"),
        }
    }

    #[test]
    fn test_simplify_one_multiplication() {
        let expr = Expr::Operator(ExpressionNode {
            op: "*".to_string(),
            args: vec![Expr::Number(1.0), Expr::Variable("x".to_string())],
            wrt: None,
            dim: None,
            ..Default::default()
        });

        let simplified = simplify(&expr);
        match simplified {
            Expr::Variable(name) => assert_eq!(name, "x"),
            _ => panic!("Expected variable 'x'"),
        }
    }

    #[test]
    fn test_simplify_zero_multiplication() {
        let expr = Expr::Operator(ExpressionNode {
            op: "*".to_string(),
            args: vec![Expr::Number(0.0), Expr::Variable("x".to_string())],
            wrt: None,
            dim: None,
            ..Default::default()
        });

        let simplified = simplify(&expr);
        match simplified {
            Expr::Number(n) => assert_eq!(n, 0.0),
            _ => panic!("Expected number 0"),
        }
    }

    #[test]
    fn test_substitute_variable() {
        let mut bindings = HashMap::new();
        bindings.insert("x".to_string(), Expr::Number(42.0));

        let expr = Expr::Variable("x".to_string());
        let result = substitute(&expr, &bindings);

        match result {
            Expr::Number(n) => assert_eq!(n, 42.0),
            _ => panic!("Expected number"),
        }
    }

    #[test]
    fn test_substitute_no_match() {
        let bindings = HashMap::new();
        let expr = Expr::Variable("y".to_string());
        let result = substitute(&expr, &bindings);

        match result {
            Expr::Variable(name) => assert_eq!(name, "y"),
            _ => panic!("Expected variable"),
        }
    }

    #[test]
    fn test_substitute_in_operator() {
        let mut bindings = HashMap::new();
        bindings.insert("x".to_string(), Expr::Number(2.0));
        bindings.insert("y".to_string(), Expr::Number(3.0));

        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Variable("y".to_string()),
            ],
            wrt: None,
            dim: None,
            ..Default::default()
        });

        let result = substitute(&expr, &bindings);

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
            }
            _ => panic!("Expected operator"),
        }
    }
}
