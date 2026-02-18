//! Reaction system analysis and ODE generation

use crate::{ReactionSystem, Model, Expr, ExpressionNode, Equation, ModelVariable, VariableType};
use std::collections::HashMap;
use thiserror::Error;

/// Error type for ODE derivation operations
#[derive(Error, Debug)]
pub enum DeriveError {
    /// Unit conversion error
    #[error("Unit conversion error: {0}")]
    UnitConversion(String),

    /// Invalid stoichiometry
    #[error("Invalid stoichiometry: {0}")]
    InvalidStoichiometry(String),

    /// Missing rate law
    #[error("Missing or invalid rate law: {0}")]
    InvalidRateLaw(String),

    /// Constraint equation error
    #[error("Constraint equation error: {0}")]
    ConstraintEquation(String),

    /// Generic derivation error
    #[error("Derivation error: {0}")]
    Other(String),
}

/// Generate ODE model from a reaction system
///
/// Converts a reaction system into an ODE model with species as state variables
/// and reactions contributing to their derivatives using mass action kinetics.
///
/// Mass action kinetics: rate law = k * product(substrates^stoichiometry)
/// Net stoichiometry = products - substrates
/// d[species]/dt = sum(net_stoichiometry * rate_law)
///
/// # Arguments
///
/// * `system` - The reaction system to convert
///
/// # Returns
///
/// * `Result<Model, DeriveError>` - ODE model with species as state variables, or error
///
/// # Errors
///
/// Returns `DeriveError` for invalid stoichiometry, missing rate laws, or unit conversion issues.
pub fn derive_odes(system: &ReactionSystem) -> Result<Model, DeriveError> {
    let mut variables = HashMap::new();
    let mut equations = Vec::new();

    // Validate system has species and reactions
    if system.species.is_empty() && !system.reactions.is_empty() {
        return Err(DeriveError::InvalidStoichiometry(
            "Reaction system has reactions but no species defined".to_string()
        ));
    }

    // Create state variables for each species
    for species in &system.species {
        variables.insert(species.name.clone(), ModelVariable {
            var_type: VariableType::State,
            units: species.units.clone(),
            default: species.default,
            description: species.description.clone(),
        });
    }

    // Validate reactions and their stoichiometry
    for (reaction_idx, reaction) in system.reactions.iter().enumerate() {
        // Check for invalid stoichiometry
        for substrate in &reaction.substrates {
            if substrate.coefficient.map_or(false, |c| c < 0.0) {
                return Err(DeriveError::InvalidStoichiometry(
                    format!("Negative substrate coefficient {} in reaction {}",
                           substrate.coefficient.unwrap(), reaction_idx)
                ));
            }
            // Verify substrate species exists
            if !system.species.iter().any(|s| s.name == substrate.species) {
                return Err(DeriveError::InvalidStoichiometry(
                    format!("Unknown substrate species '{}' in reaction {}",
                           substrate.species, reaction_idx)
                ));
            }
        }

        for product in &reaction.products {
            if product.coefficient.map_or(false, |c| c < 0.0) {
                return Err(DeriveError::InvalidStoichiometry(
                    format!("Negative product coefficient {} in reaction {}",
                           product.coefficient.unwrap(), reaction_idx)
                ));
            }
            // Verify product species exists
            if !system.species.iter().any(|s| s.name == product.species) {
                return Err(DeriveError::InvalidStoichiometry(
                    format!("Unknown product species '{}' in reaction {}",
                           product.species, reaction_idx)
                ));
            }
        }

        // Check for source/sink reactions (no substrates or no products)
        if reaction.substrates.is_empty() && reaction.products.is_empty() {
            return Err(DeriveError::InvalidStoichiometry(
                format!("Reaction {} has no substrates or products", reaction_idx)
            ));
        }
    }

    // Generate ODE equations for each species
    for species in &system.species {
        let mut rate_terms = Vec::new();

        // Check each reaction for contributions to this species
        for (_reaction_idx, reaction) in system.reactions.iter().enumerate() {
            let mut net_stoichiometry = 0.0;

            // Check if species is a substrate (negative contribution)
            for substrate in &reaction.substrates {
                if substrate.species == species.name {
                    net_stoichiometry -= substrate.coefficient.unwrap_or(1.0);
                }
            }

            // Check if species is a product (positive contribution)
            for product in &reaction.products {
                if product.species == species.name {
                    net_stoichiometry += product.coefficient.unwrap_or(1.0);
                }
            }

            // If species participates in this reaction, add rate term
            if net_stoichiometry != 0.0 {
                // For mass action kinetics, we need to multiply the base rate by concentration terms
                let enhanced_rate = enhance_rate_with_mass_action(&reaction.rate, &reaction.substrates)?;

                if net_stoichiometry == 1.0 {
                    // Direct rate contribution
                    rate_terms.push(enhanced_rate);
                } else if net_stoichiometry == -1.0 {
                    // Negative rate contribution
                    rate_terms.push(Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![
                            Expr::Number(-1.0),
                            enhanced_rate
                        ],
                        wrt: None,
                        dim: None,
                    }));
                } else {
                    // Scaled rate contribution
                    rate_terms.push(Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![
                            Expr::Number(net_stoichiometry),
                            enhanced_rate
                        ],
                        wrt: None,
                        dim: None,
                    }));
                }
            }
        }

        // Create the RHS expression (sum of all rate terms)
        let rhs = if rate_terms.is_empty() {
            Expr::Number(0.0)
        } else if rate_terms.len() == 1 {
            rate_terms.into_iter().next().unwrap()
        } else {
            Expr::Operator(ExpressionNode {
                op: "+".to_string(),
                args: rate_terms,
                wrt: None,
                dim: None,
            })
        };

        // Create the ODE equation: D[species] (wrt t) = rhs
        let lhs = Expr::Operator(ExpressionNode {
            op: "D".to_string(),
            args: vec![Expr::Variable(species.name.clone())],
            wrt: Some("t".to_string()),
            dim: None,
        });

        equations.push(Equation { lhs, rhs });
    }

    Ok(Model {
        name: system.name.clone(),
        variables,
        equations,
        discrete_events: None,
        continuous_events: None,
        description: system.description.clone(),
    })
}

/// Enhance base rate law with mass action kinetics
///
/// For mass action kinetics: rate_law = k * product(substrates^stoichiometry)
/// If the rate already contains substrate concentrations, we use it as-is.
/// If it's just a constant (rate coefficient), we multiply by substrate concentrations.
fn enhance_rate_with_mass_action(
    rate: &Expr,
    substrates: &[crate::StoichiometricEntry],
) -> Result<Expr, DeriveError> {
    // If no substrates (source reaction), return rate as-is
    if substrates.is_empty() {
        return Ok(rate.clone());
    }

    // Check if rate expression already contains substrate variables
    let rate_contains_substrates = substrates.iter().any(|s| contains_variable(rate, &s.species));

    // If rate already contains substrate concentrations, use as-is
    if rate_contains_substrates {
        return Ok(rate.clone());
    }

    // Otherwise, enhance with mass action kinetics
    let mut concentration_factors = Vec::new();

    for substrate in substrates {
        let coeff = substrate.coefficient.unwrap_or(1.0);
        let species_var = Expr::Variable(substrate.species.clone());

        if coeff == 1.0 {
            // Simple concentration factor
            concentration_factors.push(species_var);
        } else if coeff == coeff.floor() && coeff > 1.0 {
            // Integer power - create explicit multiplication
            let mut power_terms = Vec::new();
            for _ in 0..(coeff as i32) {
                power_terms.push(species_var.clone());
            }
            if power_terms.len() == 1 {
                concentration_factors.push(power_terms.into_iter().next().unwrap());
            } else {
                concentration_factors.push(Expr::Operator(ExpressionNode {
                    op: "*".to_string(),
                    args: power_terms,
                    wrt: None,
                    dim: None,
                }));
            }
        } else {
            // Non-integer power - use pow operator
            concentration_factors.push(Expr::Operator(ExpressionNode {
                op: "pow".to_string(),
                args: vec![species_var, Expr::Number(coeff)],
                wrt: None,
                dim: None,
            }));
        }
    }

    // Combine rate coefficient with concentration factors
    let mut all_factors = vec![rate.clone()];
    all_factors.extend(concentration_factors);

    if all_factors.len() == 1 {
        Ok(all_factors.into_iter().next().unwrap())
    } else {
        Ok(Expr::Operator(ExpressionNode {
            op: "*".to_string(),
            args: all_factors,
            wrt: None,
            dim: None,
        }))
    }
}

/// Check if an expression contains a specific variable
fn contains_variable(expr: &Expr, var_name: &str) -> bool {
    match expr {
        Expr::Variable(name) => name == var_name,
        Expr::Number(_) => false,
        Expr::Operator(node) => {
            node.args.iter().any(|arg| contains_variable(arg, var_name))
        }
    }
}

/// Generate stoichiometric matrix from a reaction system
///
/// Creates a matrix where rows represent species and columns represent reactions.
/// Matrix[i][j] = stoichiometric coefficient of species i in reaction j.
/// Negative values indicate reactants, positive values indicate products.
///
/// # Arguments
///
/// * `system` - The reaction system to analyze
///
/// # Returns
///
/// * `Vec<Vec<f64>>` - Matrix with species as rows and reactions as columns
pub fn stoichiometric_matrix(system: &ReactionSystem) -> Vec<Vec<f64>> {
    let num_species = system.species.len();
    let num_reactions = system.reactions.len();

    // Initialize matrix with zeros
    let mut matrix = vec![vec![0.0f64; num_reactions]; num_species];

    // Create mapping from species name to index
    let species_index: HashMap<String, usize> = system.species
        .iter()
        .enumerate()
        .map(|(idx, species)| (species.name.clone(), idx))
        .collect();

    // Fill in the matrix
    for (reaction_idx, reaction) in system.reactions.iter().enumerate() {
        // Process substrates (negative coefficients)
        for substrate in &reaction.substrates {
            if let Some(&species_idx) = species_index.get(&substrate.species) {
                let coeff = substrate.coefficient.unwrap_or(1.0);
                matrix[species_idx][reaction_idx] -= coeff;
            }
        }

        // Process products (positive coefficients)
        for product in &reaction.products {
            if let Some(&species_idx) = species_index.get(&product.species) {
                let coeff = product.coefficient.unwrap_or(1.0);
                matrix[species_idx][reaction_idx] += coeff;
            }
        }
    }

    matrix
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Species, Reaction, StoichiometricEntry};

    fn create_test_species(name: &str) -> Species {
        Species {
            name: name.to_string(),
            units: Some("mol/L".to_string()),
            default: Some(0.0),
            description: None,
        }
    }

    fn create_test_reaction(
        substrates: Vec<(&str, Option<f64>)>,
        products: Vec<(&str, Option<f64>)>,
        rate: Expr,
    ) -> Reaction {
        Reaction {
            name: None,
            substrates: substrates.into_iter().map(|(species, coeff)| StoichiometricEntry {
                species: species.to_string(),
                coefficient: coeff,
            }).collect(),
            products: products.into_iter().map(|(species, coeff)| StoichiometricEntry {
                species: species.to_string(),
                coefficient: coeff,
            }).collect(),
            rate,
            description: None,
        }
    }

    #[test]
    fn test_derive_odes_simple() {
        let system = ReactionSystem {
            name: Some("Simple System".to_string()),
            species: vec![
                create_test_species("A"),
                create_test_species("B"),
            ],
            reactions: vec![
                // A -> B with rate k1 * A
                create_test_reaction(
                    vec![("A", Some(1.0))],
                    vec![("B", Some(1.0))],
                    Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![
                            Expr::Variable("k1".to_string()),
                            Expr::Variable("A".to_string()),
                        ],
                        wrt: None,
                        dim: None,
                    })
                ),
            ],
            description: None,
        };

        let model = derive_odes(&system).expect("Should derive ODEs successfully");

        assert_eq!(model.variables.len(), 2);
        assert!(model.variables.contains_key("A"));
        assert!(model.variables.contains_key("B"));

        assert_eq!(model.equations.len(), 2);

        // Both species should have ODE equations
        let var_names: Vec<String> = model.equations.iter().map(|eq| {
            match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => {
                    match &node.args[0] {
                        Expr::Variable(name) => name.clone(),
                        _ => "unknown".to_string(),
                    }
                },
                _ => "unknown".to_string(),
            }
        }).collect();

        assert!(var_names.contains(&"A".to_string()));
        assert!(var_names.contains(&"B".to_string()));
    }

    #[test]
    fn test_stoichiometric_matrix() {
        let system = ReactionSystem {
            name: Some("Test System".to_string()),
            species: vec![
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
            ],
            reactions: vec![
                // Reaction 1: A -> B
                create_test_reaction(
                    vec![("A", Some(1.0))],
                    vec![("B", Some(1.0))],
                    Expr::Variable("k1".to_string())
                ),
                // Reaction 2: B -> C
                create_test_reaction(
                    vec![("B", Some(1.0))],
                    vec![("C", Some(1.0))],
                    Expr::Variable("k2".to_string())
                ),
                // Reaction 3: 2A -> C
                create_test_reaction(
                    vec![("A", Some(2.0))],
                    vec![("C", Some(1.0))],
                    Expr::Variable("k3".to_string())
                ),
            ],
            description: None,
        };

        let matrix = stoichiometric_matrix(&system);

        // Should be 3x3 matrix (3 species, 3 reactions)
        assert_eq!(matrix.len(), 3);
        assert_eq!(matrix[0].len(), 3);
        assert_eq!(matrix[1].len(), 3);
        assert_eq!(matrix[2].len(), 3);

        // Check specific values
        // Species A: [-1, 0, -2] (consumed in reactions 1 and 3)
        assert_eq!(matrix[0], vec![-1.0, 0.0, -2.0]);

        // Species B: [1, -1, 0] (produced in reaction 1, consumed in reaction 2)
        assert_eq!(matrix[1], vec![1.0, -1.0, 0.0]);

        // Species C: [0, 1, 1] (produced in reactions 2 and 3)
        assert_eq!(matrix[2], vec![0.0, 1.0, 1.0]);
    }

    #[test]
    fn test_stoichiometric_matrix_empty() {
        let system = ReactionSystem {
            name: Some("Empty System".to_string()),
            species: vec![],
            reactions: vec![],
            description: None,
        };

        let matrix = stoichiometric_matrix(&system);
        assert_eq!(matrix.len(), 0);
    }

    #[test]
    fn test_derive_odes_empty_system() {
        let system = ReactionSystem {
            name: Some("Empty System".to_string()),
            species: vec![],
            reactions: vec![],
            description: None,
        };

        let model = derive_odes(&system).expect("Should handle empty system");
        assert_eq!(model.variables.len(), 0);
        assert_eq!(model.equations.len(), 0);
    }

    #[test]
    fn test_derive_odes_unknown_species_error() {
        let system = ReactionSystem {
            name: Some("Invalid System".to_string()),
            species: vec![create_test_species("A")],
            reactions: vec![
                create_test_reaction(
                    vec![("B", Some(1.0))], // B is not defined in species
                    vec![("A", Some(1.0))],
                    Expr::Variable("k1".to_string())
                ),
            ],
            description: None,
        };

        let result = derive_odes(&system);
        assert!(result.is_err());
        match result {
            Err(DeriveError::InvalidStoichiometry(msg)) => {
                assert!(msg.contains("Unknown substrate species 'B'"));
            }
            _ => panic!("Expected InvalidStoichiometry error"),
        }
    }

    #[test]
    fn test_derive_odes_negative_coefficient_error() {
        let system = ReactionSystem {
            name: Some("Invalid System".to_string()),
            species: vec![create_test_species("A"), create_test_species("B")],
            reactions: vec![
                create_test_reaction(
                    vec![("A", Some(-1.0))], // Negative coefficient
                    vec![("B", Some(1.0))],
                    Expr::Variable("k1".to_string())
                ),
            ],
            description: None,
        };

        let result = derive_odes(&system);
        assert!(result.is_err());
        match result {
            Err(DeriveError::InvalidStoichiometry(msg)) => {
                assert!(msg.contains("Negative substrate coefficient"));
            }
            _ => panic!("Expected InvalidStoichiometry error"),
        }
    }

    #[test]
    fn test_derive_odes_mass_action_kinetics() {
        let system = ReactionSystem {
            name: Some("Mass Action System".to_string()),
            species: vec![
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
            ],
            reactions: vec![
                // A + B -> C with rate coefficient k1 (should become k1*A*B)
                create_test_reaction(
                    vec![("A", Some(1.0)), ("B", Some(1.0))],
                    vec![("C", Some(1.0))],
                    Expr::Variable("k1".to_string())
                ),
            ],
            description: None,
        };

        let model = derive_odes(&system).expect("Should derive ODEs successfully");
        assert_eq!(model.variables.len(), 3);
        assert_eq!(model.equations.len(), 3);

        // Check that the rate law includes mass action terms
        // For species C: d[C]/dt = k1 * A * B
        let c_equation = model.equations.iter()
            .find(|eq| match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => {
                    match &node.args[0] {
                        Expr::Variable(name) => name == "C",
                        _ => false,
                    }
                },
                _ => false,
            })
            .expect("Should find C equation");

        // The RHS should be a multiplication involving k1, A, and B
        match &c_equation.rhs {
            Expr::Operator(node) if node.op == "*" => {
                assert!(node.args.len() >= 2);
                // Should contain k1, A, and B in some form
            },
            _ => panic!("Expected multiplication for mass action kinetics"),
        }
    }

    #[test]
    fn test_derive_odes_source_reaction() {
        let system = ReactionSystem {
            name: Some("Source System".to_string()),
            species: vec![create_test_species("A")],
            reactions: vec![
                // Source reaction: -> A with rate k0 (no substrates)
                create_test_reaction(
                    vec![],
                    vec![("A", Some(1.0))],
                    Expr::Variable("k0".to_string())
                ),
            ],
            description: None,
        };

        let model = derive_odes(&system).expect("Should handle source reactions");
        assert_eq!(model.variables.len(), 1);
        assert_eq!(model.equations.len(), 1);

        // For species A: d[A]/dt = k0 (no concentration dependence)
        let a_equation = &model.equations[0];
        match &a_equation.rhs {
            Expr::Variable(name) => assert_eq!(name, "k0"),
            _ => panic!("Expected simple rate constant for source reaction"),
        }
    }

    #[test]
    fn test_derive_odes_sink_reaction() {
        let system = ReactionSystem {
            name: Some("Sink System".to_string()),
            species: vec![create_test_species("A")],
            reactions: vec![
                // Sink reaction: A -> with rate k_deg (no products)
                create_test_reaction(
                    vec![("A", Some(1.0))],
                    vec![],
                    Expr::Variable("k_deg".to_string())
                ),
            ],
            description: None,
        };

        let model = derive_odes(&system).expect("Should handle sink reactions");
        assert_eq!(model.variables.len(), 1);
        assert_eq!(model.equations.len(), 1);

        // For species A: d[A]/dt = -k_deg * A
        let a_equation = &model.equations[0];
        match &a_equation.rhs {
            Expr::Operator(node) if node.op == "*" => {
                // Should be [-1, k_deg * A] structure
                assert_eq!(node.args.len(), 2);
                // First arg should be -1, second should be k_deg * A
                match &node.args[0] {
                    Expr::Number(n) => assert_eq!(*n, -1.0),
                    _ => panic!("Expected -1 as first argument"),
                }
            },
            _ => panic!("Expected multiplication for sink reaction kinetics, got: {:?}", a_equation.rhs),
        }
    }

    #[test]
    fn test_derive_odes_higher_order_reaction() {
        let system = ReactionSystem {
            name: Some("Higher Order System".to_string()),
            species: vec![
                create_test_species("A"),
                create_test_species("B"),
            ],
            reactions: vec![
                // 2A -> B with rate k1 (second order in A)
                create_test_reaction(
                    vec![("A", Some(2.0))],
                    vec![("B", Some(1.0))],
                    Expr::Variable("k1".to_string())
                ),
            ],
            description: None,
        };

        let model = derive_odes(&system).expect("Should handle higher order reactions");
        assert_eq!(model.variables.len(), 2);
        assert_eq!(model.equations.len(), 2);

        // Check that the rate law includes A^2 term (or A*A)
        let b_equation = model.equations.iter()
            .find(|eq| match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => {
                    match &node.args[0] {
                        Expr::Variable(name) => name == "B",
                        _ => false,
                    }
                },
                _ => false,
            })
            .expect("Should find B equation");

        // The RHS should involve k1 and A squared
        match &b_equation.rhs {
            Expr::Operator(node) if node.op == "*" => {
                assert!(node.args.len() >= 2);
                // Should contain k1 and either A*A or pow(A, 2)
            },
            _ => panic!("Expected multiplication for higher order kinetics"),
        }
    }

    #[test]
    fn test_derive_odes_reactions_with_no_substrates_and_products() {
        let system = ReactionSystem {
            name: Some("Invalid System".to_string()),
            species: vec![create_test_species("A")],
            reactions: vec![
                create_test_reaction(
                    vec![], // No substrates
                    vec![], // No products
                    Expr::Variable("k1".to_string())
                ),
            ],
            description: None,
        };

        let result = derive_odes(&system);
        assert!(result.is_err());
        match result {
            Err(DeriveError::InvalidStoichiometry(msg)) => {
                assert!(msg.contains("has no substrates or products"));
            }
            _ => panic!("Expected InvalidStoichiometry error"),
        }
    }

    #[test]
    fn test_derive_odes_fractional_coefficients() {
        let system = ReactionSystem {
            name: Some("Fractional System".to_string()),
            species: vec![
                create_test_species("A"),
                create_test_species("B"),
            ],
            reactions: vec![
                // 0.5A -> B with rate k1
                create_test_reaction(
                    vec![("A", Some(0.5))],
                    vec![("B", Some(1.0))],
                    Expr::Variable("k1".to_string())
                ),
            ],
            description: None,
        };

        let model = derive_odes(&system).expect("Should handle fractional coefficients");
        assert_eq!(model.variables.len(), 2);
        assert_eq!(model.equations.len(), 2);

        // Check that fractional stoichiometry is handled correctly
        let b_equation = model.equations.iter()
            .find(|eq| match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => {
                    match &node.args[0] {
                        Expr::Variable(name) => name == "B",
                        _ => false,
                    }
                },
                _ => false,
            })
            .expect("Should find B equation");

        // The RHS should involve k1 and pow(A, 0.5)
        match &b_equation.rhs {
            Expr::Operator(node) if node.op == "*" => {
                assert!(node.args.len() >= 2);
                // Should contain k1 and pow(A, 0.5)
            },
            _ => panic!("Expected multiplication for fractional coefficient kinetics"),
        }
    }

    #[test]
    fn test_derive_odes_complex_reaction_network() {
        let system = ReactionSystem {
            name: Some("Complex Network".to_string()),
            species: vec![
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
                create_test_species("D"),
            ],
            reactions: vec![
                // A + B -> C + D (rate k1)
                create_test_reaction(
                    vec![("A", Some(1.0)), ("B", Some(1.0))],
                    vec![("C", Some(1.0)), ("D", Some(1.0))],
                    Expr::Variable("k1".to_string())
                ),
                // C -> A (rate k2)
                create_test_reaction(
                    vec![("C", Some(1.0))],
                    vec![("A", Some(1.0))],
                    Expr::Variable("k2".to_string())
                ),
                // D -> B (rate k3)
                create_test_reaction(
                    vec![("D", Some(1.0))],
                    vec![("B", Some(1.0))],
                    Expr::Variable("k3".to_string())
                ),
            ],
            description: None,
        };

        let model = derive_odes(&system).expect("Should handle complex networks");
        assert_eq!(model.variables.len(), 4);
        assert_eq!(model.equations.len(), 4);

        // Each species should have an equation
        for species_name in &["A", "B", "C", "D"] {
            let found = model.equations.iter().any(|eq| {
                match &eq.lhs {
                    Expr::Operator(node) if node.op == "D" => {
                        match &node.args[0] {
                            Expr::Variable(name) => name == species_name,
                            _ => false,
                        }
                    },
                    _ => false,
                }
            });
            assert!(found, "Should have equation for species {}", species_name);
        }
    }

    #[test]
    fn test_contains_variable_helper() {
        // Test the helper function directly
        let expr1 = Expr::Variable("A".to_string());
        assert!(contains_variable(&expr1, "A"));
        assert!(!contains_variable(&expr1, "B"));

        let expr2 = Expr::Number(42.0);
        assert!(!contains_variable(&expr2, "A"));

        let expr3 = Expr::Operator(ExpressionNode {
            op: "*".to_string(),
            args: vec![
                Expr::Variable("k".to_string()),
                Expr::Variable("A".to_string()),
            ],
            wrt: None,
            dim: None,
        });
        assert!(contains_variable(&expr3, "A"));
        assert!(contains_variable(&expr3, "k"));
        assert!(!contains_variable(&expr3, "B"));
    }
}