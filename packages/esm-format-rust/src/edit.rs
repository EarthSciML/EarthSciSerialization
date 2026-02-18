//! Immutable editing operations for ESM models

use crate::{EsmFile, Model, ReactionSystem, Expr, ExpressionNode, Equation, Species, Reaction, ModelVariable};
use std::collections::HashMap;

/// Result type for editing operations
pub type EditResult<T> = Result<T, EditError>;

/// Errors that can occur during editing operations
#[derive(Debug, Clone, PartialEq)]
pub enum EditError {
    /// Component not found
    ComponentNotFound(String),
    /// Invalid operation
    InvalidOperation(String),
    /// Variable already exists
    VariableExists(String),
    /// Equation index out of bounds
    EquationIndexError(usize),
    /// Species not found
    SpeciesNotFound(String),
    /// Reaction not found
    ReactionNotFound(String),
}

impl std::fmt::Display for EditError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EditError::ComponentNotFound(name) => write!(f, "Component not found: {}", name),
            EditError::InvalidOperation(msg) => write!(f, "Invalid operation: {}", msg),
            EditError::VariableExists(name) => write!(f, "Variable already exists: {}", name),
            EditError::EquationIndexError(idx) => write!(f, "Equation index out of bounds: {}", idx),
            EditError::SpeciesNotFound(name) => write!(f, "Species not found: {}", name),
            EditError::ReactionNotFound(name) => write!(f, "Reaction not found: {}", name),
        }
    }
}

impl std::error::Error for EditError {}

/// Add a new model to an ESM file
///
/// # Arguments
///
/// * `esm_file` - The ESM file to modify
/// * `model_id` - Unique identifier for the new model
/// * `model` - The model to add
///
/// # Returns
///
/// * `EditResult<EsmFile>` - New ESM file with the added model
pub fn add_model(esm_file: &EsmFile, model_id: &str, model: Model) -> EditResult<EsmFile> {
    let mut new_file = esm_file.clone();

    // Initialize models map if it doesn't exist
    if new_file.models.is_none() {
        new_file.models = Some(HashMap::new());
    }

    // Check if model already exists
    if new_file.models.as_ref().unwrap().contains_key(model_id) {
        return Err(EditError::InvalidOperation(
            format!("Model '{}' already exists", model_id)
        ));
    }

    // Add the new model
    new_file.models.as_mut().unwrap().insert(model_id.to_string(), model);

    Ok(new_file)
}

/// Remove a model from an ESM file
///
/// # Arguments
///
/// * `esm_file` - The ESM file to modify
/// * `model_id` - Identifier of the model to remove
///
/// # Returns
///
/// * `EditResult<EsmFile>` - New ESM file without the model
pub fn remove_model(esm_file: &EsmFile, model_id: &str) -> EditResult<EsmFile> {
    let mut new_file = esm_file.clone();

    if let Some(ref mut models) = new_file.models {
        if models.remove(model_id).is_none() {
            return Err(EditError::ComponentNotFound(model_id.to_string()));
        }
    } else {
        return Err(EditError::ComponentNotFound(model_id.to_string()));
    }

    Ok(new_file)
}

/// Add a variable to a model
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `var_name` - Name of the new variable
/// * `variable` - The variable to add
///
/// # Returns
///
/// * `EditResult<Model>` - New model with the added variable
pub fn add_variable(model: &Model, var_name: &str, variable: ModelVariable) -> EditResult<Model> {
    let mut new_model = model.clone();

    if new_model.variables.contains_key(var_name) {
        return Err(EditError::VariableExists(var_name.to_string()));
    }

    new_model.variables.insert(var_name.to_string(), variable);
    Ok(new_model)
}

/// Remove a variable from a model
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `var_name` - Name of the variable to remove
///
/// # Returns
///
/// * `EditResult<Model>` - New model without the variable
pub fn remove_variable(model: &Model, var_name: &str) -> EditResult<Model> {
    let mut new_model = model.clone();

    if new_model.variables.remove(var_name).is_none() {
        return Err(EditError::ComponentNotFound(var_name.to_string()));
    }

    Ok(new_model)
}

/// Add an equation to a model
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `equation` - The equation to add
///
/// # Returns
///
/// * `EditResult<Model>` - New model with the added equation
pub fn add_equation(model: &Model, equation: Equation) -> EditResult<Model> {
    let mut new_model = model.clone();
    new_model.equations.push(equation);
    Ok(new_model)
}

/// Remove an equation from a model by index
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `index` - Index of the equation to remove
///
/// # Returns
///
/// * `EditResult<Model>` - New model without the equation
pub fn remove_equation(model: &Model, index: usize) -> EditResult<Model> {
    if index >= model.equations.len() {
        return Err(EditError::EquationIndexError(index));
    }

    let mut new_model = model.clone();
    new_model.equations.remove(index);
    Ok(new_model)
}

/// Replace an equation in a model
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `index` - Index of the equation to replace
/// * `equation` - The new equation
///
/// # Returns
///
/// * `EditResult<Model>` - New model with the replaced equation
pub fn replace_equation(model: &Model, index: usize, equation: Equation) -> EditResult<Model> {
    if index >= model.equations.len() {
        return Err(EditError::EquationIndexError(index));
    }

    let mut new_model = model.clone();
    new_model.equations[index] = equation;
    Ok(new_model)
}

/// Add a reaction system to an ESM file
///
/// # Arguments
///
/// * `esm_file` - The ESM file to modify
/// * `system_id` - Unique identifier for the new reaction system
/// * `system` - The reaction system to add
///
/// # Returns
///
/// * `EditResult<EsmFile>` - New ESM file with the added reaction system
pub fn add_reaction_system(esm_file: &EsmFile, system_id: &str, system: ReactionSystem) -> EditResult<EsmFile> {
    let mut new_file = esm_file.clone();

    // Initialize reaction_systems map if it doesn't exist
    if new_file.reaction_systems.is_none() {
        new_file.reaction_systems = Some(HashMap::new());
    }

    // Check if reaction system already exists
    if new_file.reaction_systems.as_ref().unwrap().contains_key(system_id) {
        return Err(EditError::InvalidOperation(
            format!("Reaction system '{}' already exists", system_id)
        ));
    }

    // Add the new reaction system
    new_file.reaction_systems.as_mut().unwrap().insert(system_id.to_string(), system);

    Ok(new_file)
}

/// Add a species to a reaction system
///
/// # Arguments
///
/// * `system` - The reaction system to modify
/// * `species` - The species to add
///
/// # Returns
///
/// * `EditResult<ReactionSystem>` - New reaction system with the added species
pub fn add_species(system: &ReactionSystem, species: Species) -> EditResult<ReactionSystem> {
    let mut new_system = system.clone();

    // Check if species already exists
    if new_system.species.iter().any(|s| s.name == species.name) {
        return Err(EditError::InvalidOperation(
            format!("Species '{}' already exists", species.name)
        ));
    }

    new_system.species.push(species);
    Ok(new_system)
}

/// Remove a species from a reaction system
///
/// # Arguments
///
/// * `system` - The reaction system to modify
/// * `species_name` - Name of the species to remove
///
/// # Returns
///
/// * `EditResult<ReactionSystem>` - New reaction system without the species
pub fn remove_species(system: &ReactionSystem, species_name: &str) -> EditResult<ReactionSystem> {
    let mut new_system = system.clone();

    let initial_len = new_system.species.len();
    new_system.species.retain(|s| s.name != species_name);

    if new_system.species.len() == initial_len {
        return Err(EditError::SpeciesNotFound(species_name.to_string()));
    }

    Ok(new_system)
}

/// Add a reaction to a reaction system
///
/// # Arguments
///
/// * `system` - The reaction system to modify
/// * `reaction` - The reaction to add
///
/// # Returns
///
/// * `EditResult<ReactionSystem>` - New reaction system with the added reaction
pub fn add_reaction(system: &ReactionSystem, reaction: Reaction) -> EditResult<ReactionSystem> {
    let mut new_system = system.clone();
    new_system.reactions.push(reaction);
    Ok(new_system)
}

/// Remove a reaction from a reaction system by index
///
/// # Arguments
///
/// * `system` - The reaction system to modify
/// * `index` - Index of the reaction to remove
///
/// # Returns
///
/// * `EditResult<ReactionSystem>` - New reaction system without the reaction
pub fn remove_reaction(system: &ReactionSystem, index: usize) -> EditResult<ReactionSystem> {
    if index >= system.reactions.len() {
        return Err(EditError::InvalidOperation(
            format!("Reaction index {} out of bounds", index)
        ));
    }

    let mut new_system = system.clone();
    new_system.reactions.remove(index);
    Ok(new_system)
}

/// Update model metadata
///
/// # Arguments
///
/// * `model` - The model to modify
/// * `name` - New name (None to keep current)
/// * `description` - New description (None to keep current)
///
/// # Returns
///
/// * `EditResult<Model>` - New model with updated metadata
pub fn update_model_metadata(model: &Model, name: Option<String>, description: Option<String>) -> EditResult<Model> {
    let mut new_model = model.clone();

    if let Some(new_name) = name {
        new_model.name = Some(new_name);
    }

    if let Some(new_desc) = description {
        new_model.description = Some(new_desc);
    }

    Ok(new_model)
}

/// Create a copy of an expression with variable substitution
///
/// # Arguments
///
/// * `expr` - The expression to modify
/// * `substitutions` - Map of variable names to replacement expressions
///
/// # Returns
///
/// * `Expr` - New expression with substitutions applied
pub fn substitute_in_expression(expr: &Expr, substitutions: &HashMap<String, Expr>) -> Expr {
    match expr {
        Expr::Number(n) => Expr::Number(*n),
        Expr::Variable(var) => {
            if let Some(replacement) = substitutions.get(var) {
                replacement.clone()
            } else {
                Expr::Variable(var.clone())
            }
        }
        Expr::Operator(node) => {
            let new_args = node.args
                .iter()
                .map(|arg| substitute_in_expression(arg, substitutions))
                .collect();

            Expr::Operator(ExpressionNode {
                op: node.op.clone(),
                args: new_args,
                wrt: node.wrt.clone(),
                dim: node.dim.clone(),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Metadata, VariableType};
    use std::collections::HashMap;

    fn create_empty_esm_file() -> EsmFile {
        EsmFile {
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
        }
    }

    fn create_simple_model() -> Model {
        Model {
            name: Some("Test Model".to_string()),
            variables: HashMap::new(),
            equations: vec![],
            discrete_events: None,
            continuous_events: None,
            description: None,
        }
    }

    #[test]
    fn test_add_model() {
        let esm_file = create_empty_esm_file();
        let model = create_simple_model();

        let result = add_model(&esm_file, "test_model", model);
        assert!(result.is_ok());

        let new_file = result.unwrap();
        assert!(new_file.models.is_some());
        assert!(new_file.models.as_ref().unwrap().contains_key("test_model"));
    }

    #[test]
    fn test_add_duplicate_model() {
        let esm_file = create_empty_esm_file();
        let model = create_simple_model();

        let result1 = add_model(&esm_file, "test_model", model.clone());
        assert!(result1.is_ok());

        let new_file = result1.unwrap();
        let result2 = add_model(&new_file, "test_model", model);
        assert!(result2.is_err());
        assert!(matches!(result2.unwrap_err(), EditError::InvalidOperation(_)));
    }

    #[test]
    fn test_add_variable() {
        let model = create_simple_model();
        let variable = ModelVariable {
            var_type: VariableType::Parameter,
            units: Some("mol/L".to_string()),
            default: Some(1.0),
            description: None,
            expression: None,
        };

        let result = add_variable(&model, "test_var", variable);
        assert!(result.is_ok());

        let new_model = result.unwrap();
        assert!(new_model.variables.contains_key("test_var"));
    }

    #[test]
    fn test_add_duplicate_variable() {
        let mut model = create_simple_model();
        model.variables.insert("existing_var".to_string(), ModelVariable {
            var_type: VariableType::Parameter,
            units: None,
            default: None,
            description: None,
            expression: None,
        });

        let variable = ModelVariable {
            var_type: VariableType::State,
            units: Some("mol/L".to_string()),
            default: Some(1.0),
            description: None,
            expression: None,
        };

        let result = add_variable(&model, "existing_var", variable);
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), EditError::VariableExists(_)));
    }

    #[test]
    fn test_add_equation() {
        let model = create_simple_model();
        let equation = Equation {
            lhs: Expr::Variable("x".to_string()),
            rhs: Expr::Number(1.0),
        };

        let result = add_equation(&model, equation);
        assert!(result.is_ok());

        let new_model = result.unwrap();
        assert_eq!(new_model.equations.len(), 1);
    }

    #[test]
    fn test_remove_equation() {
        let mut model = create_simple_model();
        model.equations.push(Equation {
            lhs: Expr::Variable("x".to_string()),
            rhs: Expr::Number(1.0),
        });

        let result = remove_equation(&model, 0);
        assert!(result.is_ok());

        let new_model = result.unwrap();
        assert_eq!(new_model.equations.len(), 0);

        // Test out of bounds
        let result = remove_equation(&model, 1);
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), EditError::EquationIndexError(_)));
    }

    #[test]
    fn test_substitute_in_expression() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Number(1.0),
            ],
            wrt: None,
            dim: None,
        });

        let mut substitutions = HashMap::new();
        substitutions.insert("x".to_string(), Expr::Number(5.0));

        let result = substitute_in_expression(&expr, &substitutions);

        if let Expr::Operator(node) = result {
            assert_eq!(node.op, "+");
            assert_eq!(node.args.len(), 2);
            assert!(matches!(node.args[0], Expr::Number(5.0)));
            assert!(matches!(node.args[1], Expr::Number(1.0)));
        } else {
            panic!("Expected operator expression");
        }
    }
}