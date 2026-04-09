//! Expression manipulation utilities

use crate::Expr;
use std::collections::{HashMap, HashSet};

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
        Expr::Number(_) => false,
    }
}

/// Evaluate an expression with given variable values
///
/// # Arguments
///
/// * `expr` - The expression to evaluate
/// * `bindings` - Map from variable names to numeric values
///
/// # Returns
///
/// * `Ok(f64)` if evaluation succeeds
/// * `Err(Vec<String>)` with unbound variable names if evaluation fails
pub fn evaluate(expr: &Expr, bindings: &HashMap<String, f64>) -> Result<f64, Vec<String>> {
    let mut unbound_vars = Vec::new();
    match evaluate_with_unbound_tracking(expr, bindings, &mut unbound_vars) {
        Ok(value) => Ok(value),
        Err(_) => Err(unbound_vars),
    }
}

/// Helper function to evaluate expression while tracking unbound variables
fn evaluate_with_unbound_tracking(
    expr: &Expr,
    bindings: &HashMap<String, f64>,
    unbound_vars: &mut Vec<String>,
) -> Result<f64, ()> {
    match expr {
        Expr::Number(n) => Ok(*n),
        Expr::Variable(name) => {
            if let Some(value) = bindings.get(name) {
                Ok(*value)
            } else {
                unbound_vars.push(name.clone());
                Err(())
            }
        }
        Expr::Operator(op_node) => evaluate_operator_with_unbound_tracking(
            &op_node.op,
            &op_node.args,
            bindings,
            unbound_vars,
        ),
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
        Expr::Number(_) => {
            // Numbers don't contain variables
        }
    }
}

fn evaluate_operator_with_unbound_tracking(
    op: &str,
    args: &[Expr],
    bindings: &HashMap<String, f64>,
    unbound_vars: &mut Vec<String>,
) -> Result<f64, ()> {
    match op {
        // Arithmetic operators
        "+" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(a + b),
                _ => Err(()),
            }
        }
        "-" => {
            if args.len() == 1 {
                let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
                match a_result {
                    Ok(a) => Ok(-a),
                    _ => Err(()),
                }
            } else if args.len() == 2 {
                let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
                let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
                match (a_result, b_result) {
                    (Ok(a), Ok(b)) => Ok(a - b),
                    _ => Err(()),
                }
            } else {
                Err(())
            }
        }
        "*" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(a * b),
                _ => Err(()),
            }
        }
        "/" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => {
                    if b == 0.0 {
                        Err(())
                    } else {
                        Ok(a / b)
                    }
                }
                _ => Err(()),
            }
        }
        "^" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(a.powf(b)),
                _ => Err(()),
            }
        }

        // Mathematical functions
        "exp" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.exp()),
                _ => Err(()),
            }
        }
        "log" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => {
                    if a <= 0.0 {
                        Err(())
                    } else {
                        Ok(a.ln())
                    }
                }
                _ => Err(()),
            }
        }
        "log10" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => {
                    if a <= 0.0 {
                        Err(())
                    } else {
                        Ok(a.log10())
                    }
                }
                _ => Err(()),
            }
        }
        "sqrt" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => {
                    if a < 0.0 {
                        Err(())
                    } else {
                        Ok(a.sqrt())
                    }
                }
                _ => Err(()),
            }
        }
        "abs" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.abs()),
                _ => Err(()),
            }
        }

        // Trigonometric functions
        "sin" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.sin()),
                _ => Err(()),
            }
        }
        "cos" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.cos()),
                _ => Err(()),
            }
        }
        "tan" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.tan()),
                _ => Err(()),
            }
        }
        "asin" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => {
                    if a < -1.0 || a > 1.0 {
                        Err(())
                    } else {
                        Ok(a.asin())
                    }
                }
                _ => Err(()),
            }
        }
        "acos" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => {
                    if a < -1.0 || a > 1.0 {
                        Err(())
                    } else {
                        Ok(a.acos())
                    }
                }
                _ => Err(()),
            }
        }
        "atan" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.atan()),
                _ => Err(()),
            }
        }
        "atan2" => {
            if args.len() != 2 {
                return Err(());
            }
            let y_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let x_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (y_result, x_result) {
                (Ok(y), Ok(x)) => Ok(y.atan2(x)),
                _ => Err(()),
            }
        }

        // Min/max and rounding
        "min" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(a.min(b)),
                _ => Err(()),
            }
        }
        "max" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(a.max(b)),
                _ => Err(()),
            }
        }
        "floor" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.floor()),
                _ => Err(()),
            }
        }
        "ceil" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(a.ceil()),
                _ => Err(()),
            }
        }
        "sign" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(if a > 0.0 {
                    1.0
                } else if a < 0.0 {
                    -1.0
                } else {
                    0.0
                }),
                _ => Err(()),
            }
        }

        // Conditional
        "ifelse" => {
            if args.len() != 3 {
                return Err(());
            }
            let cond_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match cond_result {
                Ok(cond) => {
                    if cond != 0.0 {
                        evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars)
                    } else {
                        evaluate_with_unbound_tracking(&args[2], bindings, unbound_vars)
                    }
                }
                _ => Err(()),
            }
        }

        // Comparison operators (return 1.0 for true, 0.0 for false)
        ">" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if a > b { 1.0 } else { 0.0 }),
                _ => Err(()),
            }
        }
        "<" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if a < b { 1.0 } else { 0.0 }),
                _ => Err(()),
            }
        }
        ">=" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if a >= b { 1.0 } else { 0.0 }),
                _ => Err(()),
            }
        }
        "<=" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if a <= b { 1.0 } else { 0.0 }),
                _ => Err(()),
            }
        }
        "==" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if (a - b).abs() < f64::EPSILON {
                    1.0
                } else {
                    0.0
                }),
                _ => Err(()),
            }
        }
        "!=" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if (a - b).abs() >= f64::EPSILON {
                    1.0
                } else {
                    0.0
                }),
                _ => Err(()),
            }
        }

        // Logical operators (treat non-zero as true)
        "and" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if a != 0.0 && b != 0.0 { 1.0 } else { 0.0 }),
                _ => Err(()),
            }
        }
        "or" => {
            if args.len() != 2 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            let b_result = evaluate_with_unbound_tracking(&args[1], bindings, unbound_vars);
            match (a_result, b_result) {
                (Ok(a), Ok(b)) => Ok(if a != 0.0 || b != 0.0 { 1.0 } else { 0.0 }),
                _ => Err(()),
            }
        }
        "not" => {
            if args.len() != 1 {
                return Err(());
            }
            let a_result = evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars);
            match a_result {
                Ok(a) => Ok(if a == 0.0 { 1.0 } else { 0.0 }),
                _ => Err(()),
            }
        }

        // Differential operators - for now return 0 (these would need special handling)
        "D" | "grad" | "div" | "laplacian" => Ok(0.0),

        // Pre operator - just return the argument for now
        "Pre" => {
            if args.len() != 1 {
                return Err(());
            }
            evaluate_with_unbound_tracking(&args[0], bindings, unbound_vars)
        }

        _ => Err(()),
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
        }
        _ => Expr::Operator(ExpressionNode {
            op: op.to_string(),
            args: args.to_vec(),
            wrt: None,
            dim: None,
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
        });

        assert!(contains(&expr, "x"));
        assert!(!contains(&expr, "y"));
    }

    #[test]
    fn test_evaluate_simple() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![Expr::Variable("x".to_string()), Expr::Number(5.0)],
            wrt: None,
            dim: None,
        });

        let mut bindings = HashMap::new();
        bindings.insert("x".to_string(), 3.0);

        let result = evaluate(&expr, &bindings);
        assert_eq!(result.unwrap(), 8.0);
    }

    #[test]
    fn test_evaluate_undefined_variable() {
        let expr = Expr::Variable("undefined".to_string());
        let bindings = HashMap::new();

        let result = evaluate(&expr, &bindings);
        assert!(result.is_err());
        let unbound_vars = result.unwrap_err();
        assert_eq!(unbound_vars, vec!["undefined"]);
    }

    #[test]
    fn test_simplify_zero_addition() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![Expr::Variable("x".to_string()), Expr::Number(0.0)],
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
            args: vec![Expr::Number(1.0), Expr::Variable("x".to_string())],
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
            args: vec![Expr::Number(0.0), Expr::Variable("x".to_string())],
            wrt: None,
            dim: None,
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

    #[test]
    fn test_evaluate_multiple_unbound_variables() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Variable("y".to_string()),
            ],
            wrt: None,
            dim: None,
        });

        let bindings = HashMap::new();
        let result = evaluate(&expr, &bindings);

        assert!(result.is_err());
        let mut unbound_vars = result.unwrap_err();
        unbound_vars.sort();
        assert_eq!(unbound_vars, vec!["x", "y"]);
    }

    #[test]
    fn test_evaluate_new_operators() {
        let mut bindings = HashMap::new();
        bindings.insert("x".to_string(), 2.0);

        // Test sqrt
        let expr = Expr::Operator(ExpressionNode {
            op: "sqrt".to_string(),
            args: vec![Expr::Number(9.0)],
            wrt: None,
            dim: None,
        });
        assert_eq!(evaluate(&expr, &bindings).unwrap(), 3.0);

        // Test max
        let expr = Expr::Operator(ExpressionNode {
            op: "max".to_string(),
            args: vec![Expr::Variable("x".to_string()), Expr::Number(5.0)],
            wrt: None,
            dim: None,
        });
        assert_eq!(evaluate(&expr, &bindings).unwrap(), 5.0);
    }
}
