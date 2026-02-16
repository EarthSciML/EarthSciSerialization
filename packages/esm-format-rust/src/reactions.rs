//! Reaction system analysis and ODE generation

use crate::{ReactionSystem, Model, Expr, ExpressionNode, Equation, ModelVariable, VariableType};
use std::collections::HashMap;

/// Generate ODE model from a reaction system
///
/// Converts a reaction system into an ODE model with species as state variables
/// and reactions contributing to their derivatives.
///
/// # Arguments
///
/// * `system` - The reaction system to convert
///
/// # Returns
///
/// * `Model` - ODE model with species as state variables
pub fn derive_odes(system: &ReactionSystem) -> Model {
    let mut variables = HashMap::new();
    let mut equations = Vec::new();

    // Create state variables for each species
    for species in &system.species {
        variables.insert(species.name.clone(), ModelVariable {
            var_type: VariableType::State,
            units: species.units.clone(),
            default: species.default,
            description: species.description.clone(),
        });
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
                if net_stoichiometry == 1.0 {
                    // Direct rate contribution
                    rate_terms.push(reaction.rate.clone());
                } else if net_stoichiometry == -1.0 {
                    // Negative rate contribution
                    rate_terms.push(Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![
                            Expr::Number(-1.0),
                            reaction.rate.clone()
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
                            reaction.rate.clone()
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

        // Create the ODE equation: d[species]/dt = rhs
        let lhs = Expr::Operator(ExpressionNode {
            op: "d/dt".to_string(),
            args: vec![Expr::Variable(species.name.clone())],
            wrt: Some("t".to_string()),
            dim: None,
        });

        equations.push(Equation { lhs, rhs });
    }

    Model {
        name: system.name.clone(),
        variables,
        equations,
        events: None,
        description: system.description.clone(),
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
/// * `Vec<Vec<i32>>` - Matrix with species as rows and reactions as columns
pub fn stoichiometric_matrix(system: &ReactionSystem) -> Vec<Vec<i32>> {
    let num_species = system.species.len();
    let num_reactions = system.reactions.len();

    // Initialize matrix with zeros
    let mut matrix = vec![vec![0i32; num_reactions]; num_species];

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
                let coeff = substrate.coefficient.unwrap_or(1.0) as i32;
                matrix[species_idx][reaction_idx] -= coeff;
            }
        }

        // Process products (positive coefficients)
        for product in &reaction.products {
            if let Some(&species_idx) = species_index.get(&product.species) {
                let coeff = product.coefficient.unwrap_or(1.0) as i32;
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

        let model = derive_odes(&system);

        assert_eq!(model.variables.len(), 2);
        assert!(model.variables.contains_key("A"));
        assert!(model.variables.contains_key("B"));

        assert_eq!(model.equations.len(), 2);

        // Both species should have ODE equations
        let var_names: Vec<String> = model.equations.iter().map(|eq| {
            match &eq.lhs {
                Expr::Operator(node) if node.op == "d/dt" => {
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
        assert_eq!(matrix[0], vec![-1, 0, -2]);

        // Species B: [1, -1, 0] (produced in reaction 1, consumed in reaction 2)
        assert_eq!(matrix[1], vec![1, -1, 0]);

        // Species C: [0, 1, 1] (produced in reactions 2 and 3)
        assert_eq!(matrix[2], vec![0, 1, 1]);
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
}