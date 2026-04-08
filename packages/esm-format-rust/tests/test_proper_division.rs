//! Test proper division formatting to verify the LaTeX frac functionality

use esm_format::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_division_latex_frac() {
        // Test simple binary division: a / b should render as \frac{a}{b}
        let division_expr = Expr::Operator(ExpressionNode {
            op: "/".to_string(),
            args: vec![
                Expr::Variable("a".to_string()),
                Expr::Variable("b".to_string()),
            ],
            wrt: None,
            dim: None,
        });

        let latex_result = to_latex(&division_expr);
        assert_eq!(latex_result, "\\frac{a}{b}", "Simple division should render as \\frac{{}}{{}}");

        // Test with numbers: 1 / 2
        let number_division = Expr::Operator(ExpressionNode {
            op: "/".to_string(),
            args: vec![
                Expr::Number(1.0),
                Expr::Number(2.0),
            ],
            wrt: None,
            dim: None,
        });

        let latex_result = to_latex(&number_division);
        assert_eq!(latex_result, "\\frac{1}{2}", "Number division should render as \\frac{{}}{{}}");

        // Test nested expressions in division: (x + y) / (z - w)
        let nested_division = Expr::Operator(ExpressionNode {
            op: "/".to_string(),
            args: vec![
                Expr::Operator(ExpressionNode {
                    op: "+".to_string(),
                    args: vec![
                        Expr::Variable("x".to_string()),
                        Expr::Variable("y".to_string()),
                    ],
                    wrt: None,
                    dim: None,
                }),
                Expr::Operator(ExpressionNode {
                    op: "-".to_string(),
                    args: vec![
                        Expr::Variable("z".to_string()),
                        Expr::Variable("w".to_string()),
                    ],
                    wrt: None,
                    dim: None,
                }),
            ],
            wrt: None,
            dim: None,
        });

        let latex_result = to_latex(&nested_division);
        assert_eq!(latex_result, "\\frac{x + y}{z - w}", "Nested division should render as \\frac{{}}{{}}");

        // Test single argument division (edge case) - should use fallback
        let single_arg_division = Expr::Operator(ExpressionNode {
            op: "/".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
            ],
            wrt: None,
            dim: None,
        });

        let latex_result = to_latex(&single_arg_division);
        assert_eq!(latex_result, "\\div(x)", "Single argument division should use \\div fallback");

        // Test empty argument division (edge case)
        let empty_division = Expr::Operator(ExpressionNode {
            op: "/".to_string(),
            args: vec![],
            wrt: None,
            dim: None,
        });

        let latex_result = to_latex(&empty_division);
        assert_eq!(latex_result, "\\div()", "Empty division should use \\div fallback");
    }

    #[test]
    fn test_division_in_complex_expressions() {
        // Test division within multiplication: a * (b / c)
        let complex_expr = Expr::Operator(ExpressionNode {
            op: "*".to_string(),
            args: vec![
                Expr::Variable("a".to_string()),
                Expr::Operator(ExpressionNode {
                    op: "/".to_string(),
                    args: vec![
                        Expr::Variable("b".to_string()),
                        Expr::Variable("c".to_string()),
                    ],
                    wrt: None,
                    dim: None,
                }),
            ],
            wrt: None,
            dim: None,
        });

        let latex_result = to_latex(&complex_expr);
        assert_eq!(latex_result, "a \\cdot \\frac{b}{c}", "Division in multiplication should render correctly");

        // Test nested divisions: (a / b) / c = \frac{a/b}{c} = \frac{\frac{a}{b}}{c}
        let nested_divisions = Expr::Operator(ExpressionNode {
            op: "/".to_string(),
            args: vec![
                Expr::Operator(ExpressionNode {
                    op: "/".to_string(),
                    args: vec![
                        Expr::Variable("a".to_string()),
                        Expr::Variable("b".to_string()),
                    ],
                    wrt: None,
                    dim: None,
                }),
                Expr::Variable("c".to_string()),
            ],
            wrt: None,
            dim: None,
        });

        let latex_result = to_latex(&nested_divisions);
        assert_eq!(latex_result, "\\frac{\\frac{a}{b}}{c}", "Nested divisions should render correctly");
    }
}

