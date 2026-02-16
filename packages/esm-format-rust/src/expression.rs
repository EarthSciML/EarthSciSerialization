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
        Expr::Operator(op_node) => {
            op_node.args.iter().any(|arg| contains(arg, var_name))
        },
        Expr::Number(_) => false,
    }
}

/// Evaluate an expression with given variable values
///
/// # Arguments
///
/// * `expr` - The expression to evaluate
/// * `values` - Map from variable names to numeric values
///
/// # Returns
///
/// * `Ok(f64)` if evaluation succeeds
/// * `Err(String)` if evaluation fails (undefined variable, math error, etc.)
pub fn evaluate(expr: &Expr, values: &std::collections::HashMap<String, f64>) -> Result<f64, String> {
    match expr {
        Expr::Number(n) => Ok(*n),
        Expr::Variable(name) => {
            values.get(name)
                .copied()
                .ok_or_else(|| format!("Undefined variable: {}", name))
        },
        Expr::Operator(op_node) => {
            evaluate_operator(&op_node.op, &op_node.args, values)
        }
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
        Expr::Variable(name) => Expr::Variable(name.clone()),
        Expr::Operator(op_node) => {
            let simplified_args: Vec<Expr> = op_node.args.iter()
                .map(simplify)
                .collect();

            simplify_operator(&op_node.op, &simplified_args)
        }
    }
}

fn collect_variables(expr: &Expr, vars: &mut HashSet<String>) {
    match expr {
        Expr::Variable(name) => {
            vars.insert(name.clone());
        },
        Expr::Operator(op_node) => {
            for arg in &op_node.args {
                collect_variables(arg, vars);
            }
        },
        Expr::Number(_) => {
            // Numbers don't contain variables
        }
    }
}

fn evaluate_operator(
    op: &str,
    args: &[Expr],
    values: &std::collections::HashMap<String, f64>
) -> Result<f64, String> {
    match op {
        "+" => {
            if args.len() != 2 {
                return Err(format!("Addition requires exactly 2 arguments, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            let b = evaluate(&args[1], values)?;
            Ok(a + b)
        },
        "-" => {
            if args.len() == 1 {
                let a = evaluate(&args[0], values)?;
                Ok(-a)
            } else if args.len() == 2 {
                let a = evaluate(&args[0], values)?;
                let b = evaluate(&args[1], values)?;
                Ok(a - b)
            } else {
                Err(format!("Subtraction requires 1 or 2 arguments, got {}", args.len()))
            }
        },
        "*" => {
            if args.len() != 2 {
                return Err(format!("Multiplication requires exactly 2 arguments, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            let b = evaluate(&args[1], values)?;
            Ok(a * b)
        },
        "/" => {
            if args.len() != 2 {
                return Err(format!("Division requires exactly 2 arguments, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            let b = evaluate(&args[1], values)?;
            if b == 0.0 {
                return Err("Division by zero".to_string());
            }
            Ok(a / b)
        },
        "^" => {
            if args.len() != 2 {
                return Err(format!("Power requires exactly 2 arguments, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            let b = evaluate(&args[1], values)?;
            Ok(a.powf(b))
        },
        "sin" => {
            if args.len() != 1 {
                return Err(format!("sin requires exactly 1 argument, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            Ok(a.sin())
        },
        "cos" => {
            if args.len() != 1 {
                return Err(format!("cos requires exactly 1 argument, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            Ok(a.cos())
        },
        "exp" => {
            if args.len() != 1 {
                return Err(format!("exp requires exactly 1 argument, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            Ok(a.exp())
        },
        "log" => {
            if args.len() != 1 {
                return Err(format!("log requires exactly 1 argument, got {}", args.len()));
            }
            let a = evaluate(&args[0], values)?;
            if a <= 0.0 {
                return Err("log of non-positive number".to_string());
            }
            Ok(a.ln())
        },
        _ => {
            Err(format!("Unknown operator: {}", op))
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
            }),
                }
            } else {
                Expr::Operator(ExpressionNode {
                op: op.to_string(),
                args: args.to_vec(),
                wrt: None,
                dim: None,
            })
            }
        },
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
            }),
                }
            } else {
                Expr::Operator(ExpressionNode {
                op: op.to_string(),
                args: args.to_vec(),
                wrt: None,
                dim: None,
            })
            }
        },
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
            }),
                }
            } else {
                Expr::Operator(ExpressionNode {
                op: op.to_string(),
                args: args.to_vec(),
                wrt: None,
                dim: None,
            })
            }
        },
        _ => {
            Expr::Operator(ExpressionNode {
                op: op.to_string(),
                args: args.to_vec(),
                wrt: None,
                dim: None,
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
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
                args: vec![
                Expr::Number(2.0),
                Expr::Variable("x".to_string()),
            ],
                wrt: None,
                dim: None,
            });

        assert!(contains(&expr, "x"));
        assert!(!contains(&expr, "y"));
    }

    #[test]
    fn test_evaluate_simple() {
        let expr = Expr::Operator(ExpressionNode {
                op: "+".to_string(),
                args: vec![
                Expr::Variable("x".to_string()),
                Expr::Number(5.0),
            ],
                wrt: None,
                dim: None,
            });

        let mut values = HashMap::new();
        values.insert("x".to_string(), 3.0);

        let result = evaluate(&expr, &values);
        assert_eq!(result.unwrap(), 8.0);
    }

    #[test]
    fn test_evaluate_undefined_variable() {
        let expr = Expr::Variable("undefined".to_string());
        let values = HashMap::new();

        let result = evaluate(&expr, &values);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Undefined variable"));
    }

    #[test]
    fn test_simplify_zero_addition() {
        let expr = Expr::Operator(ExpressionNode {
                op: "+".to_string(),
                args: vec![
                Expr::Variable("x".to_string()),
                Expr::Number(0.0),
            ],
                wrt: None,
                dim: None,
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
                args: vec![
                Expr::Number(1.0),
                Expr::Variable("x".to_string()),
            ],
                wrt: None,
                dim: None,
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
                args: vec![
                Expr::Number(0.0),
                Expr::Variable("x".to_string()),
            ],
                wrt: None,
                dim: None,
            });

        let simplified = simplify(&expr);
        match simplified {
            Expr::Number(n) => assert_eq!(n, 0.0),
            _ => panic!("Expected number 0"),
        }
    }
}