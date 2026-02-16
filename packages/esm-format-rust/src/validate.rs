//! Structural validation for ESM files

use crate::EsmFile;

/// Result of structural validation
#[derive(Debug, Clone)]
pub struct ValidationResult {
    /// Whether validation passed
    pub valid: bool,
    /// List of validation errors
    pub errors: Vec<ValidationError>,
    /// List of warnings (non-fatal issues)
    pub warnings: Vec<String>,
}

/// A structural validation error
#[derive(Debug, Clone)]
pub struct ValidationError {
    /// Error message
    pub message: String,
    /// Path to the problematic element
    pub path: String,
    /// Error category
    pub category: ValidationErrorCategory,
}

/// Categories of validation errors
#[derive(Debug, Clone)]
pub enum ValidationErrorCategory {
    /// Undefined variable reference
    UndefinedVariable,
    /// Unit inconsistency
    UnitMismatch,
    /// Circular dependency
    CircularDependency,
    /// Mathematical error (division by zero, etc.)
    MathematicalError,
    /// Structural inconsistency
    StructuralError,
}

/// Perform structural validation on an ESM file
///
/// This goes beyond schema validation to check:
/// - All variable references are defined
/// - Unit consistency in equations
/// - No circular dependencies
/// - Mathematical validity of expressions
///
/// # Arguments
///
/// * `esm_file` - The ESM file to validate
///
/// # Returns
///
/// * `ValidationResult` - Detailed validation results
///
/// # Examples
///
/// ```rust
/// use esm_format::{validate, EsmFile, Metadata};
///
/// let esm_file = EsmFile {
///     esm: "0.1.0".to_string(),
///     metadata: Metadata {
///         name: Some("test".to_string()),
///         description: None,
///         authors: None,
///         created: None,
///         modified: None,
///         version: None,
///     },
///     models: None,
///     reaction_systems: None,
///     data_loaders: None,
///     operators: None,
///     coupling: None,
///     domain: None,
///     solver: None,
/// };
///
/// let result = validate(&esm_file);
/// assert!(result.valid);
/// ```
pub fn validate(esm_file: &EsmFile) -> ValidationResult {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();

    // Validate models
    if let Some(ref models) = esm_file.models {
        for (model_name, model) in models {
            validate_model(model_name, model, &mut errors, &mut warnings);
        }
    }

    // Validate reaction systems
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_name, rs) in reaction_systems {
            validate_reaction_system(rs_name, rs, &mut errors, &mut warnings);
        }
    }

    ValidationResult {
        valid: errors.is_empty(),
        errors,
        warnings,
    }
}

fn validate_model(
    model_name: &str,
    model: &crate::Model,
    errors: &mut Vec<ValidationError>,
    _warnings: &mut Vec<String>,
) {
    // Create a map of defined variables
    let mut defined_vars = std::collections::HashSet::new();
    for (var_name, _var) in &model.variables {
        defined_vars.insert(var_name);
    }

    // Check that all equation references are defined
    for (eq_idx, equation) in model.equations.iter().enumerate() {
        let eq_path = format!("models.{}.equations[{}]", model_name, eq_idx);
        validate_expression_references(&equation.lhs, &defined_vars, &eq_path, "lhs", errors);
        validate_expression_references(&equation.rhs, &defined_vars, &eq_path, "rhs", errors);
    }

    // TODO: Add more validation:
    // - Unit consistency
    // - Circular dependencies
    // - Mathematical validity
}

fn validate_reaction_system(
    rs_name: &str,
    rs: &crate::ReactionSystem,
    errors: &mut Vec<ValidationError>,
    _warnings: &mut Vec<String>,
) {
    // Create a map of defined species
    let mut defined_species = std::collections::HashSet::new();
    for species in &rs.species {
        defined_species.insert(&species.name);
    }

    // Check that all reaction references are defined
    for (rxn_idx, reaction) in rs.reactions.iter().enumerate() {
        let rxn_path = format!("reaction_systems.{}.reactions[{}]", rs_name, rxn_idx);

        // Check substrate references
        for (sub_idx, substrate) in reaction.substrates.iter().enumerate() {
            if !defined_species.contains(&substrate.species) {
                errors.push(ValidationError {
                    message: format!("Undefined species '{}' in reaction substrate", substrate.species),
                    path: format!("{}.substrates[{}].species", rxn_path, sub_idx),
                    category: ValidationErrorCategory::UndefinedVariable,
                });
            }
        }

        // Check product references
        for (prod_idx, product) in reaction.products.iter().enumerate() {
            if !defined_species.contains(&product.species) {
                errors.push(ValidationError {
                    message: format!("Undefined species '{}' in reaction product", product.species),
                    path: format!("{}.products[{}].species", rxn_path, prod_idx),
                    category: ValidationErrorCategory::UndefinedVariable,
                });
            }
        }

        // TODO: Validate rate expression references
    }
}

fn validate_expression_references(
    expr: &crate::Expr,
    defined_vars: &std::collections::HashSet<&String>,
    base_path: &str,
    field: &str,
    errors: &mut Vec<ValidationError>,
) {
    match expr {
        crate::Expr::Variable(var_name) => {
            // Skip derivatives and common functions
            if !var_name.starts_with("d(") &&
               !var_name.starts_with("t") &&
               !defined_vars.contains(var_name) {
                errors.push(ValidationError {
                    message: format!("Undefined variable '{}'", var_name),
                    path: format!("{}.{}", base_path, field),
                    category: ValidationErrorCategory::UndefinedVariable,
                });
            }
        },
        crate::Expr::Operator(op_node) => {
            // Recursively validate operands
            for (arg_idx, arg) in op_node.args.iter().enumerate() {
                validate_expression_references(
                    arg,
                    defined_vars,
                    base_path,
                    &format!("{}.args[{}]", field, arg_idx),
                    errors
                );
            }
        },
        crate::Expr::Number(_) => {
            // Numbers are always valid
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Model, Expr};
    use crate::types::{Metadata, ModelVariable, VariableType, Equation};
    use std::collections::HashMap;

    #[test]
    fn test_validate_empty_file() {
        let esm_file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: Metadata {
                name: Some("test".to_string()),
                description: None,
                authors: None,
                created: None,
                modified: None,
                version: None,
            },
            models: None,
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
            solver: None,
        };

        let result = validate(&esm_file);
        assert!(result.valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn test_validate_model_with_undefined_variable() {
        let mut models = HashMap::new();
        let mut variables = HashMap::new();
        variables.insert("x".to_string(), ModelVariable {
            var_type: VariableType::State,
            units: None,
            default: None,
            description: None,
        });

        models.insert("test".to_string(), Model {
            name: Some("Test Model".to_string()),
            variables,
            equations: vec![
                Equation {
                    lhs: Expr::Variable("d(x)/dt".to_string()),
                    rhs: Expr::Variable("undefined_var".to_string()), // This should cause an error
                }
            ],
            events: None,
            description: None,
        });

        let esm_file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: Metadata {
                name: Some("test".to_string()),
                description: None,
                authors: None,
                created: None,
                modified: None,
                version: None,
            },
            models: Some(models),
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
            solver: None,
        };

        let result = validate(&esm_file);
        assert!(!result.valid);
        assert!(!result.errors.is_empty());
        assert!(result.errors[0].message.contains("Undefined variable 'undefined_var'"));
    }
}