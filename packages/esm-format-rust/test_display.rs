use esm_format::*;
use esm_format::types::*;
use std::collections::HashMap;

fn main() {
    println!("Testing display functionality...");

    // Test chemical subscripts
    println!("\n=== Chemical Subscripts ===");
    let tests = vec![
        "O3", "NO2", "CH4", "C2H6", "H2O2", "CO2", "NH3", "SO4",
        "Ca2", "k_NO_O3", "jNO2", "C6H12O6", "Fe2O3", "NaCl", "Al2O3"
    ];

    for test in tests {
        let var = Expr::Variable(test.to_string());
        println!("{:<10} -> Unicode: {:<15} LaTeX: {:<25} ASCII: {}",
            test,
            to_unicode(&var),
            to_latex(&var),
            to_ascii(&var)
        );
    }

    // Test numbers
    println!("\n=== Number Formatting ===");
    let numbers = vec![42.0, 3.14, 1.8e-12, 2.46e19, 0.0001, 9999.0, 10000.0];

    for num in numbers {
        let expr = Expr::Number(num);
        println!("{:<12} -> Unicode: {:<15} LaTeX: {:<15} ASCII: {}",
            format!("{:e}", num),
            to_unicode(&expr),
            to_latex(&expr),
            to_ascii(&expr)
        );
    }

    // Test operators
    println!("\n=== Operator Formatting ===");

    // Test derivative: ∂O₃/∂t
    let derivative = Expr::Operator(ExpressionNode {
        op: "D".to_string(),
        args: vec![Expr::Variable("O3".to_string())],
        wrt: Some("t".to_string()),
        dim: None,
    });

    println!("D(O3)/Dt -> Unicode: {:<20} LaTeX: {:<30} ASCII: {}",
        to_unicode(&derivative),
        to_latex(&derivative),
        to_ascii(&derivative)
    );

    // Test power: x²
    let power = Expr::Operator(ExpressionNode {
        op: "^".to_string(),
        args: vec![Expr::Variable("x".to_string()), Expr::Number(2.0)],
        wrt: None,
        dim: None,
    });

    println!("x^2 -> Unicode: {:<20} LaTeX: {:<30} ASCII: {}",
        to_unicode(&power),
        to_latex(&power),
        to_ascii(&power)
    );

    // Test complex expression: 1.8×10⁻¹²·O₃·NO·M
    let complex_expr = Expr::Operator(ExpressionNode {
        op: "*".to_string(),
        args: vec![
            Expr::Operator(ExpressionNode {
                op: "*".to_string(),
                args: vec![
                    Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![
                            Expr::Number(1.8e-12),
                            Expr::Variable("O3".to_string()),
                        ],
                        wrt: None,
                        dim: None,
                    }),
                    Expr::Variable("NO".to_string()),
                ],
                wrt: None,
                dim: None,
            }),
            Expr::Variable("M".to_string()),
        ],
        wrt: None,
        dim: None,
    });

    println!("Complex expr -> Unicode: {:<25} LaTeX: {:<40} ASCII: {}",
        to_unicode(&complex_expr),
        to_latex(&complex_expr),
        to_ascii(&complex_expr)
    );

    // Test Model Display
    println!("\n=== Model Display ===");
    let mut variables = HashMap::new();
    variables.insert("u_wind".to_string(), ModelVariable {
        var_type: VariableType::Parameter,
        units: Some("m/s".to_string()),
        default: None,
        description: Some("Wind speed in x direction".to_string()),
        expression: None,
    });
    variables.insert("v_wind".to_string(), ModelVariable {
        var_type: VariableType::Parameter,
        units: Some("m/s".to_string()),
        default: None,
        description: Some("Wind speed in y direction".to_string()),
        expression: None,
    });

    let equation = Equation {
        lhs: Expr::Operator(ExpressionNode {
            op: "D".to_string(),
            args: vec![Expr::Variable("_var".to_string())],
            wrt: Some("t".to_string()),
            dim: None,
        }),
        rhs: Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![
                Expr::Operator(ExpressionNode {
                    op: "-".to_string(),
                    args: vec![
                        Expr::Operator(ExpressionNode {
                            op: "*".to_string(),
                            args: vec![
                                Expr::Variable("u_wind".to_string()),
                                Expr::Operator(ExpressionNode {
                                    op: "D".to_string(),
                                    args: vec![Expr::Variable("_var".to_string())],
                                    wrt: Some("x".to_string()),
                                    dim: None,
                                }),
                            ],
                            wrt: None,
                            dim: None,
                        })
                    ],
                    wrt: None,
                    dim: None,
                }),
                Expr::Operator(ExpressionNode {
                    op: "-".to_string(),
                    args: vec![
                        Expr::Operator(ExpressionNode {
                            op: "*".to_string(),
                            args: vec![
                                Expr::Variable("v_wind".to_string()),
                                Expr::Operator(ExpressionNode {
                                    op: "D".to_string(),
                                    args: vec![Expr::Variable("_var".to_string())],
                                    wrt: Some("y".to_string()),
                                    dim: None,
                                }),
                            ],
                            wrt: None,
                            dim: None,
                        })
                    ],
                    wrt: None,
                    dim: None,
                }),
            ],
            wrt: None,
            dim: None,
        }),
    };

    let model = Model {
        name: Some("Advection".to_string()),
        variables,
        equations: vec![equation],
        events: None,
        description: Some("Simple advection model".to_string()),
    };

    println!("{}", model);
}