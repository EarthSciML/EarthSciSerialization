//! Pretty printing utilities for ESM expressions

use crate::Expr;

/// Convert an expression to Unicode mathematical notation
///
/// # Arguments
///
/// * `expr` - The expression to format
///
/// # Returns
///
/// * Unicode string representation
pub fn to_unicode(expr: &Expr) -> String {
    match expr {
        Expr::Number(n) => {
            if n.fract() == 0.0 {
                format!("{}", *n as i64)
            } else {
                format!("{}", n)
            }
        },
        Expr::Variable(name) => {
            // TODO: Handle subscripts, superscripts, Greek letters
            name.clone()
        },
        Expr::Operator(op_node) => {
            format_operator_unicode(&op_node.op, &op_node.args)
        }
    }
}

/// Convert an expression to LaTeX notation
///
/// # Arguments
///
/// * `expr` - The expression to format
///
/// # Returns
///
/// * LaTeX string representation
pub fn to_latex(expr: &Expr) -> String {
    match expr {
        Expr::Number(n) => {
            if n.fract() == 0.0 {
                format!("{}", *n as i64)
            } else {
                format!("{}", n)
            }
        },
        Expr::Variable(name) => {
            // TODO: Handle subscripts, superscripts, Greek letters
            if name.len() > 1 {
                format!("\\mathrm{{{}}}", name)
            } else {
                name.clone()
            }
        },
        Expr::Operator(op_node) => {
            format_operator_latex(&op_node.op, &op_node.args)
        }
    }
}

/// Convert an expression to ASCII representation
///
/// # Arguments
///
/// * `expr` - The expression to format
///
/// # Returns
///
/// * ASCII string representation
pub fn to_ascii(expr: &Expr) -> String {
    match expr {
        Expr::Number(n) => {
            if n.fract() == 0.0 {
                format!("{}", *n as i64)
            } else {
                format!("{}", n)
            }
        },
        Expr::Variable(name) => name.clone(),
        Expr::Operator(op_node) => {
            format_operator_ascii(&op_node.op, &op_node.args)
        }
    }
}

fn format_operator_unicode(op: &str, args: &[Expr]) -> String {
    match op {
        "+" => {
            if args.len() == 2 {
                format!("{} + {}", to_unicode(&args[0]), to_unicode(&args[1]))
            } else {
                format!("+({})", args.iter().map(to_unicode).collect::<Vec<_>>().join(", "))
            }
        },
        "-" => {
            if args.len() == 1 {
                format!("-{}", to_unicode(&args[0]))
            } else if args.len() == 2 {
                format!("{} - {}", to_unicode(&args[0]), to_unicode(&args[1]))
            } else {
                format!("-({})", args.iter().map(to_unicode).collect::<Vec<_>>().join(", "))
            }
        },
        "*" => {
            if args.len() == 2 {
                format!("{} × {}", to_unicode(&args[0]), to_unicode(&args[1]))
            } else {
                format!("×({})", args.iter().map(to_unicode).collect::<Vec<_>>().join(", "))
            }
        },
        "/" => {
            if args.len() == 2 {
                format!("{} ÷ {}", to_unicode(&args[0]), to_unicode(&args[1]))
            } else {
                format!("÷({})", args.iter().map(to_unicode).collect::<Vec<_>>().join(", "))
            }
        },
        "^" => {
            if args.len() == 2 {
                format!("{}^{}", to_unicode(&args[0]), to_unicode(&args[1]))
            } else {
                format!("^({})", args.iter().map(to_unicode).collect::<Vec<_>>().join(", "))
            }
        },
        _ => {
            format!("{}({})", op, args.iter().map(to_unicode).collect::<Vec<_>>().join(", "))
        }
    }
}

fn format_operator_latex(op: &str, args: &[Expr]) -> String {
    match op {
        "+" => {
            if args.len() == 2 {
                format!("{} + {}", to_latex(&args[0]), to_latex(&args[1]))
            } else {
                format!("+({})", args.iter().map(to_latex).collect::<Vec<_>>().join(", "))
            }
        },
        "-" => {
            if args.len() == 1 {
                format!("-{}", to_latex(&args[0]))
            } else if args.len() == 2 {
                format!("{} - {}", to_latex(&args[0]), to_latex(&args[1]))
            } else {
                format!("-({})", args.iter().map(to_latex).collect::<Vec<_>>().join(", "))
            }
        },
        "*" => {
            if args.len() == 2 {
                format!("{} \\cdot {}", to_latex(&args[0]), to_latex(&args[1]))
            } else {
                format!("\\cdot({})", args.iter().map(to_latex).collect::<Vec<_>>().join(", "))
            }
        },
        "/" => {
            if args.len() == 2 {
                format!("\\frac{{{}}}{{{}}}", to_latex(&args[0]), to_latex(&args[1]))
            } else {
                format!("\\div({})", args.iter().map(to_latex).collect::<Vec<_>>().join(", "))
            }
        },
        "^" => {
            if args.len() == 2 {
                format!("{{{}}}^{{{}}}", to_latex(&args[0]), to_latex(&args[1]))
            } else {
                format!("^({})", args.iter().map(to_latex).collect::<Vec<_>>().join(", "))
            }
        },
        "sin" | "cos" | "tan" | "exp" | "log" | "sqrt" => {
            if args.len() == 1 {
                format!("\\{}({})", op, to_latex(&args[0]))
            } else {
                format!("\\{}({})", op, args.iter().map(to_latex).collect::<Vec<_>>().join(", "))
            }
        },
        _ => {
            format!("\\mathrm{{{}}}({})", op, args.iter().map(to_latex).collect::<Vec<_>>().join(", "))
        }
    }
}

fn format_operator_ascii(op: &str, args: &[Expr]) -> String {
    match op {
        "+" => {
            if args.len() == 2 {
                format!("{} + {}", to_ascii(&args[0]), to_ascii(&args[1]))
            } else {
                format!("+({})", args.iter().map(to_ascii).collect::<Vec<_>>().join(", "))
            }
        },
        "-" => {
            if args.len() == 1 {
                format!("-{}", to_ascii(&args[0]))
            } else if args.len() == 2 {
                format!("{} - {}", to_ascii(&args[0]), to_ascii(&args[1]))
            } else {
                format!("-({})", args.iter().map(to_ascii).collect::<Vec<_>>().join(", "))
            }
        },
        "*" => {
            if args.len() == 2 {
                format!("{} * {}", to_ascii(&args[0]), to_ascii(&args[1]))
            } else {
                format!("*({})", args.iter().map(to_ascii).collect::<Vec<_>>().join(", "))
            }
        },
        "/" => {
            if args.len() == 2 {
                format!("{} / {}", to_ascii(&args[0]), to_ascii(&args[1]))
            } else {
                format!("/({})", args.iter().map(to_ascii).collect::<Vec<_>>().join(", "))
            }
        },
        "^" => {
            if args.len() == 2 {
                format!("{}^{}", to_ascii(&args[0]), to_ascii(&args[1]))
            } else {
                format!("^({})", args.iter().map(to_ascii).collect::<Vec<_>>().join(", "))
            }
        },
        _ => {
            format!("{}({})", op, args.iter().map(to_ascii).collect::<Vec<_>>().join(", "))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::ExpressionNode;

    #[test]
    fn test_number_formatting() {
        assert_eq!(to_unicode(&Expr::Number(42.0)), "42");
        assert_eq!(to_latex(&Expr::Number(42.0)), "42");
        assert_eq!(to_ascii(&Expr::Number(42.0)), "42");

        assert_eq!(to_unicode(&Expr::Number(3.14)), "3.14");
        assert_eq!(to_latex(&Expr::Number(3.14)), "3.14");
        assert_eq!(to_ascii(&Expr::Number(3.14)), "3.14");
    }

    #[test]
    fn test_variable_formatting() {
        assert_eq!(to_unicode(&Expr::Variable("x".to_string())), "x");
        assert_eq!(to_latex(&Expr::Variable("x".to_string())), "x");
        assert_eq!(to_ascii(&Expr::Variable("x".to_string())), "x");

        assert_eq!(to_latex(&Expr::Variable("velocity".to_string())), "\\mathrm{velocity}");
    }

    #[test]
    fn test_addition_formatting() {
        let expr = Expr::Operator(ExpressionNode {
                op: "+".to_string(),
                args: vec![
                Expr::Variable("x".to_string()),
                Expr::Number(1.0),
            ],
                wrt: None,
                dim: None,
            });

        assert_eq!(to_unicode(&expr), "x + 1");
        assert_eq!(to_latex(&expr), "x + 1");
        assert_eq!(to_ascii(&expr), "x + 1");
    }

    #[test]
    fn test_multiplication_formatting() {
        let expr = Expr::Operator(ExpressionNode {
                op: "*".to_string(),
                args: vec![
                Expr::Number(2.0),
                Expr::Variable("x".to_string()),
            ],
                wrt: None,
                dim: None,
            });

        assert_eq!(to_unicode(&expr), "2 × x");
        assert_eq!(to_latex(&expr), "2 \\cdot x");
        assert_eq!(to_ascii(&expr), "2 * x");
    }

    #[test]
    fn test_fraction_formatting() {
        let expr = Expr::Operator(ExpressionNode {
                op: "/".to_string(),
                args: vec![
                Expr::Variable("a".to_string()),
                Expr::Variable("b".to_string()),
            ],
                wrt: None,
                dim: None,
            });

        assert_eq!(to_unicode(&expr), "a ÷ b");
        assert_eq!(to_latex(&expr), "\\frac{a}{b}");
        assert_eq!(to_ascii(&expr), "a / b");
    }

    #[test]
    fn test_power_formatting() {
        let expr = Expr::Operator(ExpressionNode {
                op: "^".to_string(),
                args: vec![
                Expr::Variable("x".to_string()),
                Expr::Number(2.0),
            ],
                wrt: None,
                dim: None,
            });

        assert_eq!(to_unicode(&expr), "x^2");
        assert_eq!(to_latex(&expr), "{x}^{2}");
        assert_eq!(to_ascii(&expr), "x^2");
    }
}