//! Graph utilities for analyzing model structure and coupling

use crate::{EsmFile, CouplingEntry};

/// Component graph representing model structure
#[derive(Debug, Clone)]
pub struct ComponentGraph {
    /// Nodes in the graph (models, reaction systems, etc.)
    pub nodes: Vec<ComponentNode>,
    /// Edges representing coupling relationships
    pub edges: Vec<CouplingEdge>,
}

/// Node in the component graph
#[derive(Debug, Clone)]
pub struct ComponentNode {
    /// Unique node identifier
    pub id: String,
    /// Type of component
    pub component_type: ComponentType,
    /// Human-readable name
    pub name: Option<String>,
}

/// Type of component in the graph
#[derive(Debug, Clone, PartialEq)]
pub enum ComponentType {
    /// ODE model
    Model,
    /// Reaction system
    ReactionSystem,
    /// Data loader
    DataLoader,
    /// Operator
    Operator,
}

/// Edge in the component graph
#[derive(Debug, Clone)]
pub struct CouplingEdge {
    /// Source component ID
    pub from: String,
    /// Target component ID
    pub to: String,
    /// Type of coupling
    pub coupling_type: String,
    /// Additional coupling data
    pub data: serde_json::Value,
}

/// Build a component graph from an ESM file
///
/// # Arguments
///
/// * `esm_file` - The ESM file to analyze
///
/// # Returns
///
/// * Component graph showing structure and coupling
pub fn component_graph(esm_file: &EsmFile) -> ComponentGraph {
    let mut nodes = Vec::new();
    let mut edges = Vec::new();

    // Add model nodes
    if let Some(ref models) = esm_file.models {
        for (id, model) in models {
            nodes.push(ComponentNode {
                id: id.clone(),
                component_type: ComponentType::Model,
                name: model.name.clone(),
            });
        }
    }

    // Add reaction system nodes
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (id, rs) in reaction_systems {
            nodes.push(ComponentNode {
                id: id.clone(),
                component_type: ComponentType::ReactionSystem,
                name: rs.name.clone(),
            });
        }
    }

    // Add data loader nodes
    if let Some(ref data_loaders) = esm_file.data_loaders {
        for (id, _dl) in data_loaders {
            nodes.push(ComponentNode {
                id: id.clone(),
                component_type: ComponentType::DataLoader,
                name: None, // Data loaders typically don't have human names
            });
        }
    }

    // Add operator nodes
    if let Some(ref operators) = esm_file.operators {
        for (id, _op) in operators {
            nodes.push(ComponentNode {
                id: id.clone(),
                component_type: ComponentType::Operator,
                name: None, // Operators typically don't have human names
            });
        }
    }

    // Add coupling edges
    if let Some(ref coupling_entries) = esm_file.coupling {
        for entry in coupling_entries {
            // Extract coupling relationships based on the coupling type
            let (from, to, coupling_type_str) = match entry {
                CouplingEntry::OperatorCompose { source, target, .. } =>
                    (source.clone(), target.clone(), "operator_compose".to_string()),
                CouplingEntry::Couple2 { system1, system2, .. } =>
                    (system1.clone(), system2.clone(), "couple2".to_string()),
                CouplingEntry::VariableMap { source, target, .. } =>
                    (source.clone(), target.clone(), "variable_map".to_string()),
                CouplingEntry::OperatorApply { operator, target, .. } =>
                    (operator.clone(), target.clone(), "operator_apply".to_string()),
                CouplingEntry::Callback { source, target, .. } =>
                    (source.clone(), target.clone(), "callback".to_string()),
                CouplingEntry::Event { event, systems, .. } => {
                    if systems.len() >= 2 {
                        (systems[0].clone(), systems[1].clone(), "event".to_string())
                    } else if systems.len() == 1 {
                        (event.clone(), systems[0].clone(), "event".to_string())
                    } else {
                        (event.clone(), "unknown".to_string(), "event".to_string())
                    }
                }
            };

            edges.push(CouplingEdge {
                from,
                to,
                coupling_type: coupling_type_str,
                data: serde_json::Value::Null, // Simplified for now
            });
        }
    }

    ComponentGraph { nodes, edges }
}

/// Check if a component exists in the ESM file
///
/// # Arguments
///
/// * `esm_file` - The ESM file to check
/// * `component_id` - The component ID to look for
///
/// # Returns
///
/// * `true` if the component exists, `false` otherwise
pub fn component_exists(esm_file: &EsmFile, component_id: &str) -> bool {
    // Check models
    if let Some(ref models) = esm_file.models {
        if models.contains_key(component_id) {
            return true;
        }
    }

    // Check reaction systems
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        if reaction_systems.contains_key(component_id) {
            return true;
        }
    }

    // Check data loaders
    if let Some(ref data_loaders) = esm_file.data_loaders {
        if data_loaders.contains_key(component_id) {
            return true;
        }
    }

    // Check operators
    if let Some(ref operators) = esm_file.operators {
        if operators.contains_key(component_id) {
            return true;
        }
    }

    false
}

/// Get the type of a component
///
/// # Arguments
///
/// * `esm_file` - The ESM file to check
/// * `component_id` - The component ID to look for
///
/// # Returns
///
/// * `Some(ComponentType)` if the component exists
/// * `None` if the component doesn't exist
pub fn get_component_type(esm_file: &EsmFile, component_id: &str) -> Option<ComponentType> {
    // Check models
    if let Some(ref models) = esm_file.models {
        if models.contains_key(component_id) {
            return Some(ComponentType::Model);
        }
    }

    // Check reaction systems
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        if reaction_systems.contains_key(component_id) {
            return Some(ComponentType::ReactionSystem);
        }
    }

    // Check data loaders
    if let Some(ref data_loaders) = esm_file.data_loaders {
        if data_loaders.contains_key(component_id) {
            return Some(ComponentType::DataLoader);
        }
    }

    // Check operators
    if let Some(ref operators) = esm_file.operators {
        if operators.contains_key(component_id) {
            return Some(ComponentType::Operator);
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Model, ReactionSystem};
    use crate::types::Metadata;
    use std::collections::HashMap;

    #[test]
    fn test_component_graph_empty() {
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

        let graph = component_graph(&esm_file);
        assert_eq!(graph.nodes.len(), 0);
        assert_eq!(graph.edges.len(), 0);
    }

    #[test]
    fn test_component_graph_with_models() {
        let mut models = HashMap::new();
        models.insert("model1".to_string(), Model {
            name: Some("Test Model 1".to_string()),
            variables: vec![],
            equations: vec![],
            events: None,
            description: None,
        });
        models.insert("model2".to_string(), Model {
            name: Some("Test Model 2".to_string()),
            variables: vec![],
            equations: vec![],
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

        let graph = component_graph(&esm_file);
        assert_eq!(graph.nodes.len(), 2);

        let node1 = graph.nodes.iter().find(|n| n.id == "model1").unwrap();
        assert_eq!(node1.component_type, ComponentType::Model);
        assert_eq!(node1.name, Some("Test Model 1".to_string()));

        let node2 = graph.nodes.iter().find(|n| n.id == "model2").unwrap();
        assert_eq!(node2.component_type, ComponentType::Model);
        assert_eq!(node2.name, Some("Test Model 2".to_string()));
    }

    #[test]
    fn test_component_exists() {
        let mut models = HashMap::new();
        models.insert("test_model".to_string(), Model {
            name: Some("Test Model".to_string()),
            variables: vec![],
            equations: vec![],
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

        assert!(component_exists(&esm_file, "test_model"));
        assert!(!component_exists(&esm_file, "nonexistent"));
    }

    #[test]
    fn test_get_component_type() {
        let mut models = HashMap::new();
        models.insert("test_model".to_string(), Model {
            name: Some("Test Model".to_string()),
            variables: vec![],
            equations: vec![],
            events: None,
            description: None,
        });

        let mut reaction_systems = HashMap::new();
        reaction_systems.insert("test_rs".to_string(), ReactionSystem {
            name: Some("Test RS".to_string()),
            species: vec![],
            reactions: vec![],
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
            reaction_systems: Some(reaction_systems),
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
            solver: None,
        };

        assert_eq!(get_component_type(&esm_file, "test_model"), Some(ComponentType::Model));
        assert_eq!(get_component_type(&esm_file, "test_rs"), Some(ComponentType::ReactionSystem));
        assert_eq!(get_component_type(&esm_file, "nonexistent"), None);
    }
}