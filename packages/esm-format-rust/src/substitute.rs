//! Expression substitution utilities

use crate::{Expr, Model, ReactionSystem, EsmFile};
use crate::types::{ExpressionNode, Equation, Reaction};
use std::collections::HashMap;

/// Substitute variables in an expression
///
/// # Arguments
///
/// * `expr` - The expression to modify
/// * `substitutions` - Map from variable names to replacement expressions
///
/// # Returns
///
/// * New expression with substitutions applied
pub fn substitute(expr: &Expr, substitutions: &std::collections::HashMap<String, Expr>) -> Expr {
    match expr {
        Expr::Number(n) => Expr::Number(*n),
        Expr::Variable(var_name) => {
            if let Some(replacement) = substitutions.get(var_name) {
                replacement.clone()
            } else {
                Expr::Variable(var_name.clone())
            }
        },
        Expr::Operator(op_node) => {
            let new_args: Vec<Expr> = op_node.args.iter()
                .map(|arg| substitute(arg, substitutions))
                .collect();

            Expr::Operator(ExpressionNode {
                op: op_node.op.clone(),
                args: new_args,
                wrt: op_node.wrt.clone(),
                dim: op_node.dim.clone(),
            })
        }
    }
}

/// Substitute variables in all expressions within a model
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `substitutions` - Map from variable names to replacement expressions
///
/// # Returns
///
/// * New model with substitutions applied
pub fn substitute_in_model(
    model: &Model,
    substitutions: &std::collections::HashMap<String, Expr>
) -> Model {
    let new_equations = model.equations.iter()
        .map(|eq| Equation {
            lhs: substitute(&eq.lhs, substitutions),
            rhs: substitute(&eq.rhs, substitutions),
        })
        .collect();

    Model {
        name: model.name.clone(),
        variables: model.variables.clone(),
        equations: new_equations,
        discrete_events: model.discrete_events.clone(), // TODO: Substitute in discrete events too
        continuous_events: model.continuous_events.clone(), // TODO: Substitute in continuous events too
        description: model.description.clone(),
    }
}

/// Substitute variables in all expressions within a reaction system
///
/// # Arguments
///
/// * `reaction_system` - The reaction system to modify
/// * `substitutions` - Map from variable names to replacement expressions
///
/// # Returns
///
/// * New reaction system with substitutions applied
pub fn substitute_in_reaction_system(
    reaction_system: &ReactionSystem,
    substitutions: &std::collections::HashMap<String, Expr>
) -> ReactionSystem {
    let new_reactions = reaction_system.reactions.iter()
        .map(|rxn| Reaction {
            name: rxn.name.clone(),
            substrates: rxn.substrates.clone(),
            products: rxn.products.clone(),
            rate: substitute(&rxn.rate, substitutions),
            description: rxn.description.clone(),
        })
        .collect();

    ReactionSystem {
        name: reaction_system.name.clone(),
        species: reaction_system.species.clone(),
        parameters: reaction_system.parameters.clone(),
        reactions: new_reactions,
        description: reaction_system.description.clone(),
    }
}

/// Context for hierarchical scoped reference resolution
#[derive(Debug, Clone)]
pub struct ScopedContext {
    /// Available models in the ESM file
    pub models: HashMap<String, Model>,
    /// Available reaction systems in the ESM file
    pub reaction_systems: HashMap<String, ReactionSystem>,
    /// Current scope path (e.g., ["Model", "Subsystem"])
    pub current_scope: Vec<String>,
}

impl ScopedContext {
    /// Create a new scoped context from an ESM file
    pub fn from_esm_file(esm_file: &EsmFile) -> Self {
        let models = esm_file.models.clone().unwrap_or_default();
        let reaction_systems = esm_file.reaction_systems.clone().unwrap_or_default();

        ScopedContext {
            models,
            reaction_systems,
            current_scope: vec![],
        }
    }

    /// Create a scoped context with specific current scope
    pub fn with_scope(mut self, scope: Vec<String>) -> Self {
        self.current_scope = scope;
        self
    }

    /// Resolve a scoped reference to its full path
    /// Handles hierarchical resolution according to ESM Spec Section 2.3.3
    pub fn resolve_scoped_reference(&self, scoped_ref: &str) -> Option<String> {
        let components: Vec<&str> = scoped_ref.split('.').collect();

        // If it's already a fully qualified name with at least 2 components, try direct lookup
        if components.len() >= 2 {
            if self.can_resolve_full_path(&components) {
                return Some(scoped_ref.to_string());
            }
        }

        // Try resolving relative to current scope
        if !self.current_scope.is_empty() {
            let mut full_path = self.current_scope.clone();
            full_path.extend(components.iter().map(|s| s.to_string()));
            let full_path_str = full_path.join(".");

            if self.can_resolve_full_path(&full_path.iter().map(|s| s.as_str()).collect::<Vec<_>>()) {
                return Some(full_path_str);
            }
        }

        // If direct resolution fails, try to find it in any available model/system
        self.search_in_available_contexts(&components)
    }

    /// Check if a full path can be resolved in the current context
    fn can_resolve_full_path(&self, components: &[&str]) -> bool {
        if components.is_empty() {
            return false;
        }

        // Check if it starts with a known model
        if let Some(model) = self.models.get(components[0]) {
            return self.resolve_in_model(model, &components[1..]);
        }

        // Check if it starts with a known reaction system
        if let Some(rs) = self.reaction_systems.get(components[0]) {
            return self.resolve_in_reaction_system(rs, &components[1..]);
        }

        false
    }

    /// Resolve remaining components within a model
    fn resolve_in_model(&self, model: &Model, remaining: &[&str]) -> bool {
        if remaining.is_empty() {
            return false; // Need at least a variable name
        }

        if remaining.len() == 1 {
            // Direct variable lookup
            return model.variables.contains_key(remaining[0]);
        }

        // For nested subsystems, we'd need more complex resolution logic
        // For now, we treat the full remaining path as a single variable name
        // This is a simplification but covers the main use cases
        let full_var_name = remaining.join(".");
        model.variables.contains_key(&full_var_name)
    }

    /// Resolve remaining components within a reaction system
    fn resolve_in_reaction_system(&self, rs: &ReactionSystem, remaining: &[&str]) -> bool {
        if remaining.is_empty() {
            return false;
        }

        if remaining.len() == 1 {
            // Check species
            if rs.species.iter().any(|s| s.name == remaining[0]) {
                return true;
            }
            // Check parameters
            if rs.parameters.contains_key(remaining[0]) {
                return true;
            }
        }

        // For nested paths in reaction systems
        let full_name = remaining.join(".");
        rs.parameters.contains_key(&full_name)
    }

    /// Search for the reference in all available contexts
    fn search_in_available_contexts(&self, components: &[&str]) -> Option<String> {
        // Search in models
        for (model_name, model) in &self.models {
            if components.len() == 1 && model.variables.contains_key(components[0]) {
                return Some(format!("{}.{}", model_name, components[0]));
            }

            // Check for nested variable names
            let nested_name = components.join(".");
            if model.variables.contains_key(&nested_name) {
                return Some(format!("{}.{}", model_name, nested_name));
            }
        }

        // Search in reaction systems
        for (rs_name, rs) in &self.reaction_systems {
            if components.len() == 1 {
                if rs.species.iter().any(|s| s.name == components[0]) {
                    return Some(format!("{}.{}", rs_name, components[0]));
                }
                if rs.parameters.contains_key(components[0]) {
                    return Some(format!("{}.{}", rs_name, components[0]));
                }
            }
        }

        None
    }
}

/// Substitute variables in an expression with scoped reference resolution
///
/// # Arguments
///
/// * `expr` - The expression to modify
/// * `substitutions` - Map from variable names to replacement expressions
/// * `context` - Scoped context for hierarchical resolution
///
/// # Returns
///
/// * New expression with substitutions applied using scoped resolution
pub fn substitute_with_context(
    expr: &Expr,
    substitutions: &std::collections::HashMap<String, Expr>,
    context: &ScopedContext
) -> Expr {
    match expr {
        Expr::Number(n) => Expr::Number(*n),
        Expr::Variable(var_name) => {
            // First try direct substitution
            if let Some(replacement) = substitutions.get(var_name) {
                return replacement.clone();
            }

            // If not found, try scoped resolution
            if let Some(resolved_name) = context.resolve_scoped_reference(var_name) {
                if let Some(replacement) = substitutions.get(&resolved_name) {
                    return replacement.clone();
                }
                // Return the resolved name if no substitution found
                return Expr::Variable(resolved_name);
            }

            // Return original if no resolution possible
            Expr::Variable(var_name.clone())
        },
        Expr::Operator(op_node) => {
            let new_args: Vec<Expr> = op_node.args.iter()
                .map(|arg| substitute_with_context(arg, substitutions, context))
                .collect();

            Expr::Operator(ExpressionNode {
                op: op_node.op.clone(),
                args: new_args,
                wrt: op_node.wrt.clone(),
                dim: op_node.dim.clone(),
            })
        }
    }
}

/// Substitute variables in all expressions within a model using scoped reference resolution
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `substitutions` - Map from variable names to replacement expressions
/// * `context` - Scoped context for hierarchical resolution
///
/// # Returns
///
/// * New model with substitutions applied using scoped resolution
pub fn substitute_in_model_with_context(
    model: &Model,
    substitutions: &std::collections::HashMap<String, Expr>,
    context: &ScopedContext
) -> Model {
    let new_equations = model.equations.iter()
        .map(|eq| Equation {
            lhs: substitute_with_context(&eq.lhs, substitutions, context),
            rhs: substitute_with_context(&eq.rhs, substitutions, context),
        })
        .collect();

    Model {
        name: model.name.clone(),
        variables: model.variables.clone(),
        equations: new_equations,
        discrete_events: model.discrete_events.clone(), // TODO: Substitute in discrete events too
        continuous_events: model.continuous_events.clone(), // TODO: Substitute in continuous events too
        description: model.description.clone(),
    }
}

/// Substitute variables in all expressions within a reaction system using scoped reference resolution
///
/// # Arguments
///
/// * `reaction_system` - The reaction system to modify
/// * `substitutions` - Map from variable names to replacement expressions
/// * `context` - Scoped context for hierarchical resolution
///
/// # Returns
///
/// * New reaction system with substitutions applied using scoped resolution
pub fn substitute_in_reaction_system_with_context(
    reaction_system: &ReactionSystem,
    substitutions: &std::collections::HashMap<String, Expr>,
    context: &ScopedContext
) -> ReactionSystem {
    let new_reactions = reaction_system.reactions.iter()
        .map(|rxn| Reaction {
            name: rxn.name.clone(),
            substrates: rxn.substrates.clone(),
            products: rxn.products.clone(),
            rate: substitute_with_context(&rxn.rate, substitutions, context),
            description: rxn.description.clone(),
        })
        .collect();

    ReactionSystem {
        name: reaction_system.name.clone(),
        species: reaction_system.species.clone(),
        parameters: reaction_system.parameters.clone(),
        reactions: new_reactions,
        description: reaction_system.description.clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ModelVariable;
    use std::collections::HashMap;

    #[test]
    fn test_substitute_variable() {
        let mut subs = HashMap::new();
        subs.insert("x".to_string(), Expr::Number(42.0));

        let expr = Expr::Variable("x".to_string());
        let result = substitute(&expr, &subs);

        match result {
            Expr::Number(n) => assert_eq!(n, 42.0),
            _ => panic!("Expected number"),
        }
    }

    #[test]
    fn test_substitute_no_match() {
        let subs = HashMap::new();
        let expr = Expr::Variable("y".to_string());
        let result = substitute(&expr, &subs);

        match result {
            Expr::Variable(name) => assert_eq!(name, "y"),
            _ => panic!("Expected variable"),
        }
    }

    #[test]
    fn test_substitute_in_operator() {
        let mut subs = HashMap::new();
        subs.insert("x".to_string(), Expr::Number(2.0));
        subs.insert("y".to_string(), Expr::Number(3.0));

        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Variable("y".to_string()),
            ],
            wrt: None,
            dim: None,
        });

        let result = substitute(&expr, &subs);

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
            },
            _ => panic!("Expected operator"),
        }
    }

    #[test]
    fn test_scoped_context_creation() {
        use crate::{EsmFile, Metadata, VariableType};

        let mut models = HashMap::new();
        let mut model_variables = HashMap::new();
        model_variables.insert("temperature".to_string(), ModelVariable {
            var_type: VariableType::State,
            units: Some("K".to_string()),
            default: Some(298.15),
            description: None,
            expression: None,
        });

        models.insert("Atmosphere".to_string(), Model {
            name: Some("Atmosphere".to_string()),
            variables: model_variables,
            equations: vec![],
            discrete_events: None,
            continuous_events: None,
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

        let context = ScopedContext::from_esm_file(&esm_file);
        assert!(context.models.contains_key("Atmosphere"));
        assert!(context.models.get("Atmosphere").unwrap().variables.contains_key("temperature"));
    }

    #[test]
    fn test_scoped_reference_resolution() {
        use crate::{EsmFile, Metadata, VariableType};

        let mut models = HashMap::new();
        let mut model_variables = HashMap::new();
        model_variables.insert("temperature".to_string(), ModelVariable {
            var_type: VariableType::State,
            units: Some("K".to_string()),
            default: Some(298.15),
            description: None,
            expression: None,
        });

        models.insert("Atmosphere".to_string(), Model {
            name: Some("Atmosphere".to_string()),
            variables: model_variables,
            equations: vec![],
            discrete_events: None,
            continuous_events: None,
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

        let context = ScopedContext::from_esm_file(&esm_file);

        // Test fully qualified reference
        let resolved = context.resolve_scoped_reference("Atmosphere.temperature");
        assert_eq!(resolved, Some("Atmosphere.temperature".to_string()));

        // Test partial reference - should find it in available models
        let resolved_partial = context.resolve_scoped_reference("temperature");
        assert_eq!(resolved_partial, Some("Atmosphere.temperature".to_string()));

        // Test non-existent reference
        let resolved_none = context.resolve_scoped_reference("NonExistent.var");
        assert_eq!(resolved_none, None);
    }

    #[test]
    fn test_substitute_with_scoped_context() {
        use crate::{EsmFile, Metadata, VariableType};

        let mut models = HashMap::new();
        let mut model_variables = HashMap::new();
        model_variables.insert("temperature".to_string(), ModelVariable {
            var_type: VariableType::State,
            units: Some("K".to_string()),
            default: Some(298.15),
            description: None,
            expression: None,
        });

        models.insert("Atmosphere".to_string(), Model {
            name: Some("Atmosphere".to_string()),
            variables: model_variables,
            equations: vec![],
            discrete_events: None,
            continuous_events: None,
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

        let context = ScopedContext::from_esm_file(&esm_file);

        // Test substitution with scoped reference
        let expr = Expr::Variable("Atmosphere.temperature".to_string());
        let mut substitutions = HashMap::new();
        substitutions.insert("Atmosphere.temperature".to_string(), Expr::Number(273.15));

        let result = substitute_with_context(&expr, &substitutions, &context);
        match result {
            Expr::Number(n) => assert_eq!(n, 273.15),
            _ => panic!("Expected number after substitution"),
        }
    }

    #[test]
    fn test_hierarchical_scoped_substitution() {
        use crate::{EsmFile, Metadata, VariableType};

        // Create a more complex model with hierarchical scoped references
        let mut models = HashMap::new();
        let mut model_variables = HashMap::new();
        model_variables.insert("Chemistry.FastChem.O3".to_string(), ModelVariable {
            var_type: VariableType::State,
            units: Some("mol/L".to_string()),
            default: Some(40e-9),
            description: None,
            expression: None,
        });
        model_variables.insert("Chemistry.FastChem.k_rate".to_string(), ModelVariable {
            var_type: VariableType::Parameter,
            units: Some("s-1".to_string()),
            default: Some(1.8e-12),
            description: None,
            expression: None,
        });

        models.insert("Atmosphere".to_string(), Model {
            name: Some("Atmosphere".to_string()),
            variables: model_variables,
            equations: vec![],
            discrete_events: None,
            continuous_events: None,
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

        let context = ScopedContext::from_esm_file(&esm_file);

        // Test complex expression with multiple scoped references
        let complex_expr = Expr::Operator(ExpressionNode {
            op: "*".to_string(),
            args: vec![
                Expr::Variable("Atmosphere.Chemistry.FastChem.k_rate".to_string()),
                Expr::Variable("Atmosphere.Chemistry.FastChem.O3".to_string()),
            ],
            wrt: None,
            dim: None,
        });

        let mut substitutions = HashMap::new();
        substitutions.insert("Atmosphere.Chemistry.FastChem.k_rate".to_string(), Expr::Number(2.0e-12));
        substitutions.insert("Atmosphere.Chemistry.FastChem.O3".to_string(), Expr::Variable("local_O3".to_string()));

        let result = substitute_with_context(&complex_expr, &substitutions, &context);

        // Verify the result structure
        match result {
            Expr::Operator(op_node) => {
                assert_eq!(op_node.op, "*");
                assert_eq!(op_node.args.len(), 2);
                // First arg should be substituted with number
                match &op_node.args[0] {
                    Expr::Number(n) => assert_eq!(*n, 2.0e-12),
                    _ => panic!("Expected number for first arg"),
                }
                // Second arg should be substituted with variable
                match &op_node.args[1] {
                    Expr::Variable(name) => assert_eq!(name, "local_O3"),
                    _ => panic!("Expected variable for second arg"),
                }
            },
            _ => panic!("Expected operator expression"),
        }
    }
}