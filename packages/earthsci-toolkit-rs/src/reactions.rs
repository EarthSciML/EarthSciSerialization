//! Reaction system analysis and ODE generation

use crate::{
    Equation, Expr, ExpressionNode, Model, ModelVariable, ReactionSystem, Species, VariableType,
};
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

/// Lower a reaction network to an ODE equation list.
///
/// Produces one `D(species, t) = Σ(net_stoichiometry · rate)` equation per species
/// per spec §4.7.5 step 1. Reusable from both [`derive_odes`] and
/// [`crate::flatten::flatten`] so the reaction-to-equation core lives in one place.
///
/// Each reaction's base rate is enhanced with mass-action concentration factors
/// (unless the rate expression already references substrate names). Net
/// stoichiometry combines substrate and product contributions for each species.
pub fn lower_reactions_to_equations(
    reactions: &[crate::Reaction],
    species: &HashMap<String, Species>,
) -> Result<Vec<Equation>, DeriveError> {
    // Validate system has species if there are reactions
    if species.is_empty() && !reactions.is_empty() {
        return Err(DeriveError::InvalidStoichiometry(
            "Reaction system has reactions but no species defined".to_string(),
        ));
    }

    // Validate reactions and their stoichiometry (u32 can't be negative,
    // so there's no negative-coefficient check anymore).
    for (reaction_idx, reaction) in reactions.iter().enumerate() {
        for substrate in reaction.substrates.iter().flatten() {
            if !species.contains_key(&substrate.species) {
                return Err(DeriveError::InvalidStoichiometry(format!(
                    "Unknown substrate species '{}' in reaction {}",
                    substrate.species, reaction_idx
                )));
            }
        }

        for product in reaction.products.iter().flatten() {
            if !species.contains_key(&product.species) {
                return Err(DeriveError::InvalidStoichiometry(format!(
                    "Unknown product species '{}' in reaction {}",
                    product.species, reaction_idx
                )));
            }
        }

        let no_substrates = reaction.substrates.as_ref().is_none_or(|v| v.is_empty());
        let no_products = reaction.products.as_ref().is_none_or(|v| v.is_empty());
        if no_substrates && no_products {
            return Err(DeriveError::InvalidStoichiometry(format!(
                "Reaction {} has no substrates or products",
                reaction_idx
            )));
        }
    }

    let mut equations = Vec::with_capacity(species.len());

    let mut species_names: Vec<&String> = species.keys().collect();
    species_names.sort();
    for sp_name in species_names {
        let mut rate_terms = Vec::new();

        for reaction in reactions {
            let mut net_stoichiometry: i64 = 0;

            for substrate in reaction.substrates.iter().flatten() {
                if &substrate.species == sp_name {
                    net_stoichiometry -= substrate.coefficient as i64;
                }
            }
            for product in reaction.products.iter().flatten() {
                if &product.species == sp_name {
                    net_stoichiometry += product.coefficient as i64;
                }
            }

            if net_stoichiometry != 0 {
                let enhanced_rate = enhance_rate_with_mass_action(
                    &reaction.rate,
                    reaction.substrates.as_deref().unwrap_or(&[]),
                )?;

                if net_stoichiometry == 1 {
                    rate_terms.push(enhanced_rate);
                } else if net_stoichiometry == -1 {
                    rate_terms.push(Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![Expr::Number(-1.0), enhanced_rate],
                        wrt: None,
                        dim: None,
                        ..Default::default()
                    }));
                } else {
                    rate_terms.push(Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![Expr::Number(net_stoichiometry as f64), enhanced_rate],
                        wrt: None,
                        dim: None,
                        ..Default::default()
                    }));
                }
            }
        }

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
                ..Default::default()
            })
        };

        let lhs = Expr::Operator(ExpressionNode {
            op: "D".to_string(),
            args: vec![Expr::Variable(sp_name.clone())],
            wrt: Some("t".to_string()),
            dim: None,
            ..Default::default()
        });

        equations.push(Equation { lhs, rhs });
    }

    Ok(equations)
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

    for (species_name, species) in &system.species {
        variables.insert(
            species_name.clone(),
            ModelVariable {
                var_type: VariableType::State,
                units: species.units.clone(),
                default: species.default,
                description: species.description.clone(),
                expression: None,
                shape: None,
                location: None,
            noise_kind: None,
            correlation_group: None,
            },
        );
    }

    let equations = lower_reactions_to_equations(&system.reactions, &system.species)?;

    Ok(Model {
        name: None,
        domain: system.domain.clone(),
        coupletype: system.coupletype.clone(),
        reference: system.reference.clone(),
        variables,
        equations,
        discrete_events: system.discrete_events.clone(),
        continuous_events: system.continuous_events.clone(),
        subsystems: None,
        description: None,
        tolerance: None,
        tests: None,
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
    let rate_contains_substrates = substrates
        .iter()
        .any(|s| contains_variable(rate, &s.species));

    // If rate already contains substrate concentrations, use as-is
    if rate_contains_substrates {
        return Ok(rate.clone());
    }

    // Otherwise, enhance with mass action kinetics.
    // Stoichiometric coefficients are integers ≥ 1 per schema.
    let mut concentration_factors = Vec::new();

    for substrate in substrates {
        let coeff = substrate.coefficient;
        let species_var = Expr::Variable(substrate.species.clone());

        if coeff == 1 {
            concentration_factors.push(species_var);
        } else {
            let mut power_terms = Vec::new();
            for _ in 0..coeff {
                power_terms.push(species_var.clone());
            }
            concentration_factors.push(Expr::Operator(ExpressionNode {
                op: "*".to_string(),
                args: power_terms,
                wrt: None,
                dim: None,
                ..Default::default()
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
            ..Default::default()
        }))
    }
}

/// Check if an expression contains a specific variable
fn contains_variable(expr: &Expr, var_name: &str) -> bool {
    match expr {
        Expr::Variable(name) => name == var_name,
        Expr::Number(_) => false,
        Expr::Operator(node) => node.args.iter().any(|arg| contains_variable(arg, var_name)),
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

    // Build a stable species ordering (sorted by name) so indices are reproducible
    // across runs and match the ordering used by derive_odes / lower_reactions_to_equations.
    let mut sorted_species_names: Vec<&String> = system.species.keys().collect();
    sorted_species_names.sort();
    let species_index: HashMap<String, usize> = sorted_species_names
        .iter()
        .enumerate()
        .map(|(idx, name)| ((*name).clone(), idx))
        .collect();

    // Fill in the matrix
    for (reaction_idx, reaction) in system.reactions.iter().enumerate() {
        // Process substrates (negative coefficients)
        for substrate in reaction.substrates.iter().flatten() {
            if let Some(&species_idx) = species_index.get(&substrate.species) {
                matrix[species_idx][reaction_idx] -= substrate.coefficient as f64;
            }
        }

        // Process products (positive coefficients)
        for product in reaction.products.iter().flatten() {
            if let Some(&species_idx) = species_index.get(&product.species) {
                matrix[species_idx][reaction_idx] += product.coefficient as f64;
            }
        }
    }

    matrix
}

/// Generate a stoichiometric matrix from a reaction system using parallel computation
///
/// This function provides parallel computation for generating stoichiometric matrices,
/// which can significantly improve performance for large reaction systems.
///
/// # Arguments
///
/// * `system` - The reaction system to analyze
///
/// # Returns
///
/// * `Result<Vec<Vec<f64>>, crate::performance::PerformanceError>` - Matrix with species as rows and reactions as columns
///
/// # Features
///
/// This function requires the `parallel` feature to be enabled.
///
/// # Example
///
/// ```rust
/// # #[cfg(feature = "parallel")]
/// # {
/// use earthsci_toolkit::{ReactionSystem, stoichiometric_matrix_parallel};
///
/// // Assuming you have a reaction system
/// let reaction_system = ReactionSystem {
///     name: Some("Test System".to_string()),
///     species: vec![],
///     parameters: std::collections::HashMap::new(),
///     reactions: vec![],
///     description: None,
/// };
///
/// let matrix = stoichiometric_matrix_parallel(&reaction_system).unwrap();
/// # }
/// ```
#[cfg(feature = "parallel")]
pub fn stoichiometric_matrix_parallel(
    system: &ReactionSystem,
) -> Result<Vec<Vec<f64>>, crate::performance::PerformanceError> {
    use crate::performance::ParallelEvaluator;

    let evaluator = ParallelEvaluator::new(None)?;
    evaluator.compute_stoichiometric_matrix_parallel(system)
}

/// Conservation law violations in a reaction system
#[derive(Debug, Clone, PartialEq)]
pub struct ConservationViolation {
    /// Type of conservation law violated
    pub violation_type: ConservationLawType,
    /// Reaction index where violation occurs (if applicable)
    pub reaction_index: Option<usize>,
    /// Species involved in the violation
    pub species: Vec<String>,
    /// Quantitative measure of the violation
    pub magnitude: f64,
    /// Human-readable description
    pub description: String,
}

/// Types of conservation laws that can be detected
#[derive(Debug, Clone, PartialEq)]
pub enum ConservationLawType {
    /// Mass balance violation within a single reaction
    MassBalance,
    /// System-wide linear invariant violation
    LinearInvariant,
    /// Unexpected degrees of freedom in the stoichiometric matrix
    StoichiometricRank,
}

/// Results of conservation law analysis
#[derive(Debug, Clone)]
pub struct ConservationAnalysis {
    /// Violations found in the system
    pub violations: Vec<ConservationViolation>,
    /// Linear invariants found (combinations of species that should be conserved)
    pub linear_invariants: Vec<LinearInvariant>,
    /// Rank of the stoichiometric matrix
    pub stoichiometric_rank: usize,
    /// Number of independent conservation laws
    pub conservation_laws_count: usize,
}

/// A linear invariant representing a conservation law
#[derive(Debug, Clone)]
pub struct LinearInvariant {
    /// Coefficients for each species (same order as in the reaction system)
    pub coefficients: Vec<f64>,
    /// Names of species with non-zero coefficients
    pub species_names: Vec<String>,
    /// Description of what this invariant represents
    pub description: String,
}

/// Detect conservation law violations in a reaction system
///
/// Analyzes the reaction system for various types of conservation law violations
/// including mass balance within reactions and system-wide linear invariants.
///
/// # Arguments
///
/// * `system` - The reaction system to analyze
///
/// # Returns
///
/// * `ConservationAnalysis` - Detailed analysis of conservation laws and violations
///
/// # Examples
///
/// ```rust
/// use earthsci_toolkit::{ReactionSystem, detect_conservation_violations};
/// use std::collections::HashMap;
///
/// // Create an empty reaction system
/// let system = ReactionSystem {
///     domain: None,
///     coupletype: None,
///     reference: None,
///     species: HashMap::new(),
///     parameters: HashMap::new(),
///     reactions: vec![],
///     constraint_equations: None,
///     discrete_events: None,
///     continuous_events: None,
///     subsystems: None,
/// };
///
/// let analysis = detect_conservation_violations(&system);
/// println!("Found {} violations", analysis.violations.len());
/// ```
pub fn detect_conservation_violations(system: &ReactionSystem) -> ConservationAnalysis {
    let mut violations = Vec::new();

    // Check mass balance for each reaction
    violations.extend(detect_mass_balance_violations(system));

    // Build a stable, sorted list of species names so indices match
    // `stoichiometric_matrix` and downstream invariant analysis.
    let mut sorted_species_names: Vec<String> = system.species.keys().cloned().collect();
    sorted_species_names.sort();

    // Analyze stoichiometric matrix for linear invariants
    let matrix = stoichiometric_matrix(system);
    let linear_invariants = find_linear_invariants(&matrix, &sorted_species_names);
    let stoichiometric_rank = calculate_matrix_rank(&matrix);
    let conservation_laws_count = system.species.len().saturating_sub(stoichiometric_rank);

    // Check for unexpected rank (this could indicate missing conservation laws)
    if conservation_laws_count == 0 && !system.species.is_empty() && !system.reactions.is_empty() {
        violations.push(ConservationViolation {
            violation_type: ConservationLawType::StoichiometricRank,
            reaction_index: None,
            species: sorted_species_names.clone(),
            magnitude: stoichiometric_rank as f64,
            description: "System has full rank stoichiometric matrix with no conservation laws, which may indicate missing constraints".to_string(),
        });
    }

    ConservationAnalysis {
        violations,
        linear_invariants,
        stoichiometric_rank,
        conservation_laws_count,
    }
}

/// Detect mass balance violations in individual reactions
fn detect_mass_balance_violations(system: &ReactionSystem) -> Vec<ConservationViolation> {
    let mut violations = Vec::new();

    for (reaction_idx, reaction) in system.reactions.iter().enumerate() {
        // Skip source reactions (no substrates) and sink reactions (no products)
        // These represent exchange with environment and don't need to be mass balanced.
        let no_substrates = reaction.substrates.as_ref().is_none_or(|v| v.is_empty());
        let no_products = reaction.products.as_ref().is_none_or(|v| v.is_empty());
        if no_substrates || no_products {
            continue;
        }

        // Calculate total substrate and product coefficients
        let substrate_sum: f64 = reaction
            .substrates
            .iter()
            .flatten()
            .map(|s| s.coefficient as f64)
            .sum();

        let product_sum: f64 = reaction
            .products
            .iter()
            .flatten()
            .map(|p| p.coefficient as f64)
            .sum();

        // Check if mass is conserved (allowing for small numerical errors)
        const BALANCE_TOLERANCE: f64 = 1e-10;
        let imbalance = (substrate_sum - product_sum).abs();

        if imbalance > BALANCE_TOLERANCE {
            let mut species_involved = Vec::new();
            species_involved.extend(
                reaction
                    .substrates
                    .iter()
                    .flatten()
                    .map(|s| s.species.clone()),
            );
            species_involved.extend(
                reaction
                    .products
                    .iter()
                    .flatten()
                    .map(|p| p.species.clone()),
            );

            violations.push(ConservationViolation {
                violation_type: ConservationLawType::MassBalance,
                reaction_index: Some(reaction_idx),
                species: species_involved,
                magnitude: imbalance,
                description: format!(
                    "Reaction {} has mass imbalance: {:.6} substrates → {:.6} products (difference: {:.6})",
                    reaction_idx, substrate_sum, product_sum, imbalance
                ),
            });
        }
    }

    violations
}

/// Find linear invariants (conservation laws) from the stoichiometric matrix.
///
/// `species_names` must be in the same order as rows of `matrix` (sorted alphabetically,
/// matching what `stoichiometric_matrix` produces).
fn find_linear_invariants(matrix: &[Vec<f64>], species_names: &[String]) -> Vec<LinearInvariant> {
    if matrix.is_empty() || species_names.is_empty() {
        return Vec::new();
    }

    let num_species = matrix.len();
    let num_reactions = matrix[0].len();

    if num_reactions == 0 {
        // No reactions means all species are conserved individually
        return species_names
            .iter()
            .enumerate()
            .map(|(i, name)| {
                let mut coefficients = vec![0.0; num_species];
                coefficients[i] = 1.0;
                LinearInvariant {
                    coefficients,
                    species_names: vec![name.clone()],
                    description: format!("Conservation of {}", name),
                }
            })
            .collect();
    }

    // Find the null space of the transpose of the stoichiometric matrix
    // This gives us the linear invariants
    let invariants = find_null_space_transpose(matrix);

    // Convert to LinearInvariant structs with descriptions
    invariants
        .into_iter()
        .map(|coeffs| {
            let names: Vec<String> = coeffs
                .iter()
                .enumerate()
                .filter_map(|(i, &coeff)| {
                    if coeff.abs() > 1e-10 {
                        Some(species_names[i].clone())
                    } else {
                        None
                    }
                })
                .collect();

            let description = if names.len() <= 3 {
                format!(
                    "Linear combination: {}",
                    coeffs
                        .iter()
                        .enumerate()
                        .filter(|(_, coeff)| coeff.abs() > 1e-10)
                        .map(|(i, coeff)| format!("{:.3}*{}", coeff, species_names[i]))
                        .collect::<Vec<_>>()
                        .join(" + ")
                )
            } else {
                format!("Linear invariant involving {} species", names.len())
            };

            LinearInvariant {
                coefficients: coeffs,
                species_names: names,
                description,
            }
        })
        .collect()
}

/// Find the null space of the transpose of a matrix (simplified implementation)
fn find_null_space_transpose(matrix: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let num_species = matrix.len();
    let num_reactions = if matrix.is_empty() {
        0
    } else {
        matrix[0].len()
    };

    if num_reactions == 0 {
        // All species are independent invariants
        return (0..num_species)
            .map(|i| {
                let mut inv = vec![0.0; num_species];
                inv[i] = 1.0;
                inv
            })
            .collect();
    }

    // For the transpose null space, we need to find vectors v such that:
    // matrix^T * v = 0, which means v^T * matrix = 0
    // This is equivalent to finding the left null space of the stoichiometric matrix

    // Use a simplified approach based on the rank deficiency
    let rank = calculate_matrix_rank(matrix);
    let null_space_dim = num_species.saturating_sub(rank);

    if null_space_dim == 0 {
        return Vec::new();
    }

    let mut invariants = Vec::new();

    // Check if total mass is conserved (sum of all species)
    let mut total_conserved = true;
    for reaction_col in 0..num_reactions {
        let column_sum: f64 = matrix.iter().map(|row| row[reaction_col]).sum();
        if column_sum.abs() > 1e-10 {
            total_conserved = false;
            break;
        }
    }

    if total_conserved {
        invariants.push(vec![1.0; num_species]);
    }

    // For reversible A <-> B systems, check for simple conservation patterns
    if num_species == 2 && num_reactions == 2 && invariants.is_empty() {
        // Check if the two reactions are opposite of each other (reversible system)
        let mut is_reversible = true;
        for row in matrix.iter().take(num_species) {
            let coeff_sum: f64 = row.iter().sum();
            if coeff_sum.abs() > 1e-10 {
                is_reversible = false;
                break;
            }
        }

        if is_reversible {
            // A <-> B system: A + B is conserved
            invariants.push(vec![1.0; num_species]);
        }
    }

    // For systems with rank deficiency, try to find additional patterns
    if invariants.len() < null_space_dim {
        // Try combinations that sum to zero for each reaction
        // This is a heuristic approach for common chemical systems
        for species_idx in 0..num_species {
            let mut candidate = vec![0.0; num_species];
            candidate[species_idx] = 1.0;

            // Check if this species by itself forms a conservation law
            let mut is_conserved = true;
            for val in matrix[species_idx].iter().take(num_reactions) {
                if val.abs() > 1e-10 {
                    is_conserved = false;
                    break;
                }
            }

            if is_conserved && !invariants.iter().any(|inv| inv[species_idx] > 0.5) {
                invariants.push(candidate);
            }
        }
    }

    invariants
}

/// Calculate the rank of a matrix using Gaussian elimination
fn calculate_matrix_rank(matrix: &[Vec<f64>]) -> usize {
    if matrix.is_empty() {
        return 0;
    }

    let rows = matrix.len();
    let cols = matrix[0].len();

    if cols == 0 {
        return 0;
    }

    // Create a mutable copy for Gaussian elimination
    let mut mat = matrix.to_vec();

    let mut rank = 0;
    let mut col = 0;

    for row in 0..rows {
        if col >= cols {
            break;
        }

        // Find pivot
        let mut pivot_row = row;
        for i in (row + 1)..rows {
            if mat[i][col].abs() > mat[pivot_row][col].abs() {
                pivot_row = i;
            }
        }

        // If pivot is too small, try next column
        if mat[pivot_row][col].abs() < 1e-10 {
            col += 1;
            continue;
        }

        // Swap rows if needed
        if pivot_row != row {
            mat.swap(pivot_row, row);
        }

        // Eliminate below pivot
        for i in (row + 1)..rows {
            if mat[i][col].abs() > 1e-10 {
                let factor = mat[i][col] / mat[row][col];
                #[allow(clippy::needless_range_loop)]
                for j in col..cols {
                    mat[i][j] -= factor * mat[row][j];
                }
            }
        }

        rank += 1;
        col += 1;
    }

    rank
}

/// SIMD-optimized computation of conservation weights for batch analysis
///
/// This function demonstrates the use of SIMD operations for accelerated
/// computation of conservation weights across multiple species concentrations.
/// It uses the existing SIMD functions from the performance module.
///
/// # Arguments
///
/// * `species_concentrations` - Current concentrations of all species
/// * `conservation_coefficients` - Linear combination coefficients for conservation laws
///
/// # Returns
///
/// * `Result<Vec<f64>, crate::PerformanceError>` - Conservation weights for each invariant
///
/// # Example
///
/// ```rust
/// # #[cfg(feature = "simd")]
/// # {
/// use earthsci_toolkit::compute_conservation_weights_simd;
///
/// let concentrations = vec![1.0, 2.0, 3.0, 4.0];
/// let coefficients = vec![1.0, 1.0, -1.0, -1.0]; // Mass balance: A + B - C - D = 0
/// let weights = compute_conservation_weights_simd(&concentrations, &coefficients).unwrap();
/// # }
/// ```
#[cfg(feature = "simd")]
pub fn compute_conservation_weights_simd(
    species_concentrations: &[f64],
    conservation_coefficients: &[f64],
) -> Result<f64, crate::PerformanceError> {
    if species_concentrations.len() != conservation_coefficients.len() {
        return Err(crate::PerformanceError::SimdError(
            "Concentration and coefficient arrays must have the same length".to_string(),
        ));
    }

    // Use SIMD dot product to compute the conservation weight
    // This represents how well a conservation law is satisfied
    crate::performance::simd_math::dot_product_simd(
        species_concentrations,
        conservation_coefficients,
    )
}

/// Batch computation of multiple conservation weights using SIMD
///
/// Computes conservation weights for multiple invariants simultaneously,
/// leveraging SIMD operations for improved performance with large datasets.
///
/// # Arguments
///
/// * `species_concentrations` - Current concentrations of all species
/// * `conservation_matrix` - Matrix where each row represents conservation coefficients
///
/// # Returns
///
/// * `Result<Vec<f64>, crate::PerformanceError>` - Conservation weights for each invariant
#[cfg(feature = "simd")]
pub fn compute_batch_conservation_weights_simd(
    species_concentrations: &[f64],
    conservation_matrix: &[Vec<f64>],
) -> Result<Vec<f64>, crate::PerformanceError> {
    let mut weights = Vec::with_capacity(conservation_matrix.len());

    for coefficients in conservation_matrix {
        let weight = compute_conservation_weights_simd(species_concentrations, coefficients)?;
        weights.push(weight);
    }

    Ok(weights)
}

/// SIMD-accelerated analysis of conservation law violations
///
/// Uses SIMD operations to efficiently compute conservation violations across
/// multiple chemical species, which is useful for validating reaction mechanisms.
///
/// # Arguments
///
/// * `current_concentrations` - Species concentrations at current time
/// * `previous_concentrations` - Species concentrations at previous time
/// * `conservation_coefficients` - Linear combination coefficients
///
/// # Returns
///
/// * `Result<f64, crate::PerformanceError>` - Magnitude of conservation violation
#[cfg(feature = "simd")]
pub fn analyze_conservation_violation_simd(
    current_concentrations: &[f64],
    previous_concentrations: &[f64],
    conservation_coefficients: &[f64],
) -> Result<f64, crate::PerformanceError> {
    if current_concentrations.len() != previous_concentrations.len()
        || current_concentrations.len() != conservation_coefficients.len()
    {
        return Err(crate::PerformanceError::SimdError(
            "All arrays must have the same length".to_string(),
        ));
    }

    // Compute change in concentrations using SIMD subtraction
    let mut concentration_changes = vec![0.0; current_concentrations.len()];
    let negated_previous: Vec<f64> = previous_concentrations.iter().map(|x| -x).collect();

    crate::performance::simd_math::add_vectors_simd(
        current_concentrations,
        &negated_previous,
        &mut concentration_changes,
    )?;

    // Compute conservation violation using SIMD dot product
    crate::performance::simd_math::dot_product_simd(
        &concentration_changes,
        conservation_coefficients,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Reaction, Species, StoichiometricEntry};

    fn create_test_species(name: &str) -> (String, Species) {
        (
            name.to_string(),
            Species {
                units: Some("mol/L".to_string()),
                default: Some(0.0),
                description: None,
            },
        )
    }

    fn create_test_reaction(
        substrates: Vec<(&str, u32)>,
        products: Vec<(&str, u32)>,
        rate: Expr,
    ) -> Reaction {
        Reaction {
            id: None,
            name: None,
            substrates: Some(
                substrates
                    .into_iter()
                    .map(|(species, coeff)| StoichiometricEntry {
                        species: species.to_string(),
                        coefficient: coeff,
                    })
                    .collect(),
            ),
            products: Some(
                products
                    .into_iter()
                    .map(|(species, coeff)| StoichiometricEntry {
                        species: species.to_string(),
                        coefficient: coeff,
                    })
                    .collect(),
            ),
            rate,
            reference: None,
        }
    }

    #[test]
    fn test_derive_odes_simple() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A"), create_test_species("B")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // A -> B with rate k1 * A
                create_test_reaction(
                    vec![("A", 1)],
                    vec![("B", 1)],
                    Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![
                            Expr::Variable("k1".to_string()),
                            Expr::Variable("A".to_string()),
                        ],
                        wrt: None,
                        dim: None,
                        ..Default::default()
                    }),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let model = derive_odes(&system).expect("Should derive ODEs successfully");

        assert_eq!(model.variables.len(), 2);
        assert!(model.variables.contains_key("A"));
        assert!(model.variables.contains_key("B"));

        assert_eq!(model.equations.len(), 2);

        // Both species should have ODE equations
        let var_names: Vec<String> = model
            .equations
            .iter()
            .map(|eq| match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => match &node.args[0] {
                    Expr::Variable(name) => name.clone(),
                    _ => "unknown".to_string(),
                },
                _ => "unknown".to_string(),
            })
            .collect();

        assert!(var_names.contains(&"A".to_string()));
        assert!(var_names.contains(&"B".to_string()));
    }

    #[test]
    fn test_stoichiometric_matrix() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
            ]
            .into_iter()
            .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // Reaction 1: A -> B
                create_test_reaction(
                    vec![("A", 1)],
                    vec![("B", 1)],
                    Expr::Variable("k1".to_string()),
                ),
                // Reaction 2: B -> C
                create_test_reaction(
                    vec![("B", 1)],
                    vec![("C", 1)],
                    Expr::Variable("k2".to_string()),
                ),
                // Reaction 3: 2A -> C
                create_test_reaction(
                    vec![("A", 2)],
                    vec![("C", 1)],
                    Expr::Variable("k3".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
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
            domain: None,
            coupletype: None,
            reference: None,
            species: std::collections::HashMap::new(),
            parameters: HashMap::new(),
            reactions: vec![],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let matrix = stoichiometric_matrix(&system);
        assert_eq!(matrix.len(), 0);
    }

    #[test]
    fn test_derive_odes_empty_system() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: std::collections::HashMap::new(),
            parameters: HashMap::new(),
            reactions: vec![],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let model = derive_odes(&system).expect("Should handle empty system");
        assert_eq!(model.variables.len(), 0);
        assert_eq!(model.equations.len(), 0);
    }

    #[test]
    fn test_derive_odes_unknown_species_error() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![create_test_reaction(
                vec![("B", 1)], // B is not defined in species
                vec![("A", 1)],
                Expr::Variable("k1".to_string()),
            )],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
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
    fn test_derive_odes_mass_action_kinetics() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
            ]
            .into_iter()
            .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // A + B -> C with rate coefficient k1 (should become k1*A*B)
                create_test_reaction(
                    vec![("A", 1), ("B", 1)],
                    vec![("C", 1)],
                    Expr::Variable("k1".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let model = derive_odes(&system).expect("Should derive ODEs successfully");
        assert_eq!(model.variables.len(), 3);
        assert_eq!(model.equations.len(), 3);

        // Check that the rate law includes mass action terms
        // For species C: d[C]/dt = k1 * A * B
        let c_equation = model
            .equations
            .iter()
            .find(|eq| match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => match &node.args[0] {
                    Expr::Variable(name) => name == "C",
                    _ => false,
                },
                _ => false,
            })
            .expect("Should find C equation");

        // The RHS should be a multiplication involving k1, A, and B
        match &c_equation.rhs {
            Expr::Operator(node) if node.op == "*" => {
                assert!(node.args.len() >= 2);
                // Should contain k1, A, and B in some form
            }
            _ => panic!("Expected multiplication for mass action kinetics"),
        }
    }

    #[test]
    fn test_derive_odes_source_reaction() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // Source reaction: -> A with rate k0 (no substrates)
                create_test_reaction(vec![], vec![("A", 1)], Expr::Variable("k0".to_string())),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
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
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // Sink reaction: A -> with rate k_deg (no products)
                create_test_reaction(vec![("A", 1)], vec![], Expr::Variable("k_deg".to_string())),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
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
            }
            _ => panic!(
                "Expected multiplication for sink reaction kinetics, got: {:?}",
                a_equation.rhs
            ),
        }
    }

    #[test]
    fn test_derive_odes_higher_order_reaction() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A"), create_test_species("B")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // 2A -> B with rate k1 (second order in A)
                create_test_reaction(
                    vec![("A", 2)],
                    vec![("B", 1)],
                    Expr::Variable("k1".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let model = derive_odes(&system).expect("Should handle higher order reactions");
        assert_eq!(model.variables.len(), 2);
        assert_eq!(model.equations.len(), 2);

        // Check that the rate law includes A^2 term (or A*A)
        let b_equation = model
            .equations
            .iter()
            .find(|eq| match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => match &node.args[0] {
                    Expr::Variable(name) => name == "B",
                    _ => false,
                },
                _ => false,
            })
            .expect("Should find B equation");

        // The RHS should involve k1 and A squared
        match &b_equation.rhs {
            Expr::Operator(node) if node.op == "*" => {
                assert!(node.args.len() >= 2);
                // Should contain k1 and either A*A or pow(A, 2)
            }
            _ => panic!("Expected multiplication for higher order kinetics"),
        }
    }

    #[test]
    fn test_derive_odes_reactions_with_no_substrates_and_products() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![create_test_reaction(
                vec![], // No substrates
                vec![], // No products
                Expr::Variable("k1".to_string()),
            )],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
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
    fn test_derive_odes_complex_reaction_network() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
                create_test_species("D"),
            ]
            .into_iter()
            .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // A + B -> C + D (rate k1)
                create_test_reaction(
                    vec![("A", 1), ("B", 1)],
                    vec![("C", 1), ("D", 1)],
                    Expr::Variable("k1".to_string()),
                ),
                // C -> A (rate k2)
                create_test_reaction(
                    vec![("C", 1)],
                    vec![("A", 1)],
                    Expr::Variable("k2".to_string()),
                ),
                // D -> B (rate k3)
                create_test_reaction(
                    vec![("D", 1)],
                    vec![("B", 1)],
                    Expr::Variable("k3".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let model = derive_odes(&system).expect("Should handle complex networks");
        assert_eq!(model.variables.len(), 4);
        assert_eq!(model.equations.len(), 4);

        // Each species should have an equation
        for species_name in &["A", "B", "C", "D"] {
            let found = model.equations.iter().any(|eq| match &eq.lhs {
                Expr::Operator(node) if node.op == "D" => match &node.args[0] {
                    Expr::Variable(name) => name == species_name,
                    _ => false,
                },
                _ => false,
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
            ..Default::default()
        });
        assert!(contains_variable(&expr3, "A"));
        assert!(contains_variable(&expr3, "k"));
        assert!(!contains_variable(&expr3, "B"));
    }

    #[test]
    #[cfg(feature = "parallel")]
    fn test_stoichiometric_matrix_parallel() {
        use std::collections::HashMap;

        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
            ]
            .into_iter()
            .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // A -> B
                create_test_reaction(
                    vec![("A", 1)],
                    vec![("B", 1)],
                    Expr::Variable("k1".to_string()),
                ),
                // B -> C
                create_test_reaction(
                    vec![("B", 1)],
                    vec![("C", 1)],
                    Expr::Variable("k2".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        // Test the parallel version
        let parallel_matrix = crate::reactions::stoichiometric_matrix_parallel(&system)
            .expect("Parallel stoichiometric matrix should work");

        // Test the sequential version for comparison
        let sequential_matrix = stoichiometric_matrix(&system);

        // Both should produce the same result
        assert_eq!(parallel_matrix.len(), sequential_matrix.len());
        assert_eq!(parallel_matrix[0].len(), sequential_matrix[0].len());

        for (i, row) in parallel_matrix.iter().enumerate() {
            for (j, &val) in row.iter().enumerate() {
                assert_eq!(
                    val, sequential_matrix[i][j],
                    "Parallel and sequential results should match at position [{}, {}]",
                    i, j
                );
            }
        }

        // Verify specific values
        assert_eq!(parallel_matrix[0][0], -1.0, "A consumed in reaction 1");
        assert_eq!(parallel_matrix[1][0], 1.0, "B produced in reaction 1");
        assert_eq!(parallel_matrix[1][1], -1.0, "B consumed in reaction 2");
        assert_eq!(parallel_matrix[2][1], 1.0, "C produced in reaction 2");
    }

    #[test]
    fn test_conservation_detection_balanced_system() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A"), create_test_species("B")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // A <-> B (reversible)
                create_test_reaction(
                    vec![("A", 1)],
                    vec![("B", 1)],
                    Expr::Variable("kf".to_string()),
                ),
                create_test_reaction(
                    vec![("B", 1)],
                    vec![("A", 1)],
                    Expr::Variable("kr".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let analysis = detect_conservation_violations(&system);

        // Should have no mass balance violations
        let mass_violations: Vec<_> = analysis
            .violations
            .iter()
            .filter(|v| v.violation_type == ConservationLawType::MassBalance)
            .collect();
        assert_eq!(
            mass_violations.len(),
            0,
            "Balanced system should have no mass violations"
        );

        // Should detect total mass conservation (A + B = constant)
        assert!(
            !analysis.linear_invariants.is_empty(),
            "Should detect conservation laws"
        );
        assert_eq!(
            analysis.conservation_laws_count, 1,
            "Should have one conservation law"
        );
    }

    #[test]
    fn test_conservation_detection_unbalanced_reaction() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A"), create_test_species("B")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // Unbalanced: 2A -> B (mass not conserved)
                create_test_reaction(
                    vec![("A", 2)],
                    vec![("B", 1)],
                    Expr::Variable("k".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let analysis = detect_conservation_violations(&system);

        // Should detect mass balance violation
        let mass_violations: Vec<_> = analysis
            .violations
            .iter()
            .filter(|v| v.violation_type == ConservationLawType::MassBalance)
            .collect();
        assert_eq!(
            mass_violations.len(),
            1,
            "Should detect one mass balance violation"
        );

        let violation = &mass_violations[0];
        assert_eq!(violation.reaction_index, Some(0));
        assert_eq!(violation.magnitude, 1.0); // |2.0 - 1.0| = 1.0
        assert!(violation.species.contains(&"A".to_string()));
        assert!(violation.species.contains(&"B".to_string()));
    }

    #[test]
    fn test_conservation_detection_complex_network() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [
                create_test_species("A"),
                create_test_species("B"),
                create_test_species("C"),
            ]
            .into_iter()
            .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // 2A -> B + C (total mass conserved)
                create_test_reaction(
                    vec![("A", 2)],
                    vec![("B", 1), ("C", 1)],
                    Expr::Variable("k1".to_string()),
                ),
                // B -> A (mass conserved)
                create_test_reaction(
                    vec![("B", 1)],
                    vec![("A", 1)],
                    Expr::Variable("k2".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let analysis = detect_conservation_violations(&system);

        // All reactions should be mass balanced
        let mass_violations: Vec<_> = analysis
            .violations
            .iter()
            .filter(|v| v.violation_type == ConservationLawType::MassBalance)
            .collect();
        assert_eq!(
            mass_violations.len(),
            0,
            "All reactions should be mass balanced"
        );

        // Should have conservation laws
        assert!(
            analysis.conservation_laws_count > 0,
            "Should have conservation laws"
        );
    }

    #[test]
    fn test_conservation_detection_empty_system() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: std::collections::HashMap::new(),
            parameters: HashMap::new(),
            reactions: vec![],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let analysis = detect_conservation_violations(&system);

        assert_eq!(
            analysis.violations.len(),
            0,
            "Empty system should have no violations"
        );
        assert_eq!(
            analysis.linear_invariants.len(),
            0,
            "Empty system should have no invariants"
        );
        assert_eq!(
            analysis.stoichiometric_rank, 0,
            "Empty system should have rank 0"
        );
        assert_eq!(
            analysis.conservation_laws_count, 0,
            "Empty system should have no conservation laws"
        );
    }

    #[test]
    fn test_conservation_detection_source_sink() {
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // Source: -> A
                create_test_reaction(
                    vec![],
                    vec![("A", 1)],
                    Expr::Variable("k_source".to_string()),
                ),
                // Sink: A ->
                create_test_reaction(vec![("A", 1)], vec![], Expr::Variable("k_sink".to_string())),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let analysis = detect_conservation_violations(&system);

        // Source and sink reactions should not be flagged as mass balance violations
        // (they represent exchange with environment)
        let mass_violations: Vec<_> = analysis
            .violations
            .iter()
            .filter(|v| v.violation_type == ConservationLawType::MassBalance)
            .collect();
        assert_eq!(
            mass_violations.len(),
            0,
            "Source/sink reactions should not be flagged"
        );
    }

    #[test]
    fn test_linear_invariant_calculation() {
        // Test system where A + B = constant
        let system = ReactionSystem {
            domain: None,
            coupletype: None,
            reference: None,
            species: [create_test_species("A"), create_test_species("B")]
                .into_iter()
                .collect::<std::collections::HashMap<_, _>>(),
            parameters: HashMap::new(),
            reactions: vec![
                // A <-> B
                create_test_reaction(
                    vec![("A", 1)],
                    vec![("B", 1)],
                    Expr::Variable("k".to_string()),
                ),
            ],
            constraint_equations: None,
            discrete_events: None,
            continuous_events: None,
            subsystems: None,
        };

        let matrix = stoichiometric_matrix(&system);
        let mut sorted_names: Vec<String> = system.species.keys().cloned().collect();
        sorted_names.sort();
        let invariants = find_linear_invariants(&matrix, &sorted_names);

        // Should find that total mass (A + B) is conserved
        assert!(!invariants.is_empty(), "Should find linear invariants");

        // Check that we found the A + B conservation
        let total_mass_invariant = invariants.iter().find(|inv| {
            inv.coefficients.len() == 2
                && (inv.coefficients[0] - inv.coefficients[1]).abs() < 1e-10
                && inv.coefficients[0].abs() > 0.5
        });
        assert!(
            total_mass_invariant.is_some(),
            "Should find A + B conservation law"
        );
    }

    #[test]
    fn test_matrix_rank_calculation() {
        // Test rank calculation with known matrices

        // Full rank 2x2 matrix
        let full_rank_matrix = vec![vec![1.0, 0.0], vec![0.0, 1.0]];
        assert_eq!(
            calculate_matrix_rank(&full_rank_matrix),
            2,
            "Identity matrix should have full rank"
        );

        // Rank 1 matrix
        let rank_1_matrix = vec![vec![1.0, 2.0], vec![2.0, 4.0]];
        assert_eq!(
            calculate_matrix_rank(&rank_1_matrix),
            1,
            "Dependent rows should give rank 1"
        );

        // Zero matrix
        let zero_matrix = vec![vec![0.0, 0.0], vec![0.0, 0.0]];
        assert_eq!(
            calculate_matrix_rank(&zero_matrix),
            0,
            "Zero matrix should have rank 0"
        );

        // Empty matrix
        let empty_matrix: Vec<Vec<f64>> = vec![];
        assert_eq!(
            calculate_matrix_rank(&empty_matrix),
            0,
            "Empty matrix should have rank 0"
        );
    }

    #[test]
    fn test_conservation_violation_types() {
        // Test that different violation types are properly categorized
        let violation = ConservationViolation {
            violation_type: ConservationLawType::MassBalance,
            reaction_index: Some(0),
            species: vec!["A".to_string(), "B".to_string()],
            magnitude: 1.5,
            description: "Test violation".to_string(),
        };

        assert_eq!(violation.violation_type, ConservationLawType::MassBalance);
        assert_eq!(violation.reaction_index, Some(0));
        assert_eq!(violation.magnitude, 1.5);
        assert_eq!(violation.species.len(), 2);
    }

    #[cfg(feature = "simd")]
    #[test]
    fn test_conservation_weights_simd() {
        // Test SIMD computation of conservation weights
        let concentrations = vec![2.0, 3.0, 4.0, 5.0];
        let coefficients = vec![1.0, 1.0, -1.0, -1.0]; // A + B - C - D

        let weight = compute_conservation_weights_simd(&concentrations, &coefficients).unwrap();

        // Expected: 2*1 + 3*1 + 4*(-1) + 5*(-1) = 2 + 3 - 4 - 5 = -4
        assert_eq!(weight, -4.0);
    }

    #[cfg(feature = "simd")]
    #[test]
    fn test_batch_conservation_weights_simd() {
        // Test batch computation
        let concentrations = vec![1.0, 2.0, 3.0, 4.0];
        let matrix = vec![
            vec![1.0, 1.0, 0.0, 0.0],   // First invariant: A + B
            vec![0.0, 0.0, 1.0, 1.0],   // Second invariant: C + D
            vec![1.0, -1.0, 1.0, -1.0], // Third invariant: A - B + C - D
        ];

        let weights = compute_batch_conservation_weights_simd(&concentrations, &matrix).unwrap();

        assert_eq!(weights.len(), 3);
        assert_eq!(weights[0], 3.0); // 1*1 + 2*1 = 3
        assert_eq!(weights[1], 7.0); // 3*1 + 4*1 = 7
        assert_eq!(weights[2], -2.0); // 1*1 + (-1)*2 + 1*3 + (-1)*4 = 1 - 2 + 3 - 4 = -2
    }

    #[cfg(feature = "simd")]
    #[test]
    fn test_conservation_violation_simd() {
        // Test SIMD analysis of conservation violations
        let current = vec![5.0, 3.0, 2.0, 4.0];
        let previous = vec![4.0, 2.0, 1.0, 3.0];
        let coefficients = vec![1.0, 1.0, -1.0, -1.0]; // Conservation law: A + B - C - D = 0

        let violation =
            analyze_conservation_violation_simd(&current, &previous, &coefficients).unwrap();

        // Changes: [1.0, 1.0, 1.0, 1.0] (all increased by 1)
        // Violation: 1*1 + 1*1 + (-1)*1 + (-1)*1 = 1 + 1 - 1 - 1 = 0
        assert_eq!(violation, 0.0);
    }

    #[cfg(feature = "simd")]
    #[test]
    fn test_conservation_weights_simd_error_cases() {
        // Test error handling
        let concentrations = vec![1.0, 2.0];
        let coefficients = vec![1.0, 1.0, 1.0]; // Wrong length

        let result = compute_conservation_weights_simd(&concentrations, &coefficients);
        assert!(result.is_err());
    }
}
