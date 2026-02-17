//! Graph utilities for analyzing model structure and coupling

use crate::{EsmFile, CouplingEntry};

/// Component graph representing model structure
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ComponentGraph {
    /// Nodes in the graph (models, reaction systems, etc.)
    pub nodes: Vec<ComponentNode>,
    /// Edges representing coupling relationships
    pub edges: Vec<CouplingEdge>,
}

/// Node in the component graph
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ComponentNode {
    /// Unique node identifier
    pub id: String,
    /// Type of component
    pub component_type: ComponentType,
    /// Human-readable name
    pub name: Option<String>,
}

/// Type of component in the graph
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
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
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
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

/// Expression graph representing variable dependencies within expressions
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ExpressionGraph {
    /// Nodes representing variables and operators
    pub nodes: Vec<ExpressionNode>,
    /// Edges representing dependencies
    pub edges: Vec<DependencyEdge>,
}

/// Node in an expression graph
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ExpressionNode {
    /// Unique node identifier
    pub id: String,
    /// Type of expression node
    pub node_type: ExpressionNodeType,
    /// Optional value for constants
    pub value: Option<f64>,
}

/// Type of node in an expression graph
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum ExpressionNodeType {
    /// Variable reference
    Variable,
    /// Numeric constant
    Constant,
    /// Operator
    Operator(String),
}

/// Edge representing dependencies in an expression graph
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DependencyEdge {
    /// Source node ID
    pub from: String,
    /// Target node ID
    pub to: String,
    /// Edge type (e.g., "operand")
    pub edge_type: String,
}

/// Build an expression graph from various ESM components
///
/// # Arguments
///
/// * `input` - Can be an ESM file, model, reaction system, equation, reaction, or expression
///
/// # Returns
///
/// * `ExpressionGraph` - Graph showing variable dependencies
pub fn expression_graph<T>(input: &T) -> ExpressionGraph
where
    T: ExpressionGraphInput,
{
    input.build_expression_graph()
}

/// Trait for types that can build expression graphs
pub trait ExpressionGraphInput {
    fn build_expression_graph(&self) -> ExpressionGraph;
}

impl ExpressionGraphInput for crate::EsmFile {
    fn build_expression_graph(&self) -> ExpressionGraph {
        let mut nodes = Vec::new();
        let mut edges = Vec::new();
        let mut node_counter = 0;

        // Process all models
        if let Some(ref models) = self.models {
            for (_, model) in models {
                let (model_nodes, model_edges) = extract_from_model(model, &mut node_counter);
                nodes.extend(model_nodes);
                edges.extend(model_edges);
            }
        }

        // Process all reaction systems
        if let Some(ref reaction_systems) = self.reaction_systems {
            for (_, rs) in reaction_systems {
                let (rs_nodes, rs_edges) = extract_from_reaction_system(rs, &mut node_counter);
                nodes.extend(rs_nodes);
                edges.extend(rs_edges);
            }
        }

        ExpressionGraph { nodes, edges }
    }
}

impl ExpressionGraphInput for crate::Model {
    fn build_expression_graph(&self) -> ExpressionGraph {
        let mut node_counter = 0;
        let (nodes, edges) = extract_from_model(self, &mut node_counter);
        ExpressionGraph { nodes, edges }
    }
}

impl ExpressionGraphInput for crate::ReactionSystem {
    fn build_expression_graph(&self) -> ExpressionGraph {
        let mut node_counter = 0;
        let (nodes, edges) = extract_from_reaction_system(self, &mut node_counter);
        ExpressionGraph { nodes, edges }
    }
}

impl ExpressionGraphInput for crate::Equation {
    fn build_expression_graph(&self) -> ExpressionGraph {
        let mut node_counter = 0;
        let mut nodes = Vec::new();
        let mut edges = Vec::new();

        extract_from_expr(&self.lhs, &mut nodes, &mut edges, &mut node_counter);
        extract_from_expr(&self.rhs, &mut nodes, &mut edges, &mut node_counter);

        ExpressionGraph { nodes, edges }
    }
}

impl ExpressionGraphInput for crate::Reaction {
    fn build_expression_graph(&self) -> ExpressionGraph {
        let mut node_counter = 0;
        let mut nodes = Vec::new();
        let mut edges = Vec::new();

        extract_from_expr(&self.rate, &mut nodes, &mut edges, &mut node_counter);

        ExpressionGraph { nodes, edges }
    }
}

impl ExpressionGraphInput for crate::Expr {
    fn build_expression_graph(&self) -> ExpressionGraph {
        let mut node_counter = 0;
        let mut nodes = Vec::new();
        let mut edges = Vec::new();

        extract_from_expr(self, &mut nodes, &mut edges, &mut node_counter);

        ExpressionGraph { nodes, edges }
    }
}

/// Helper function to extract nodes and edges from a model
fn extract_from_model(model: &crate::Model, node_counter: &mut usize) -> (Vec<ExpressionNode>, Vec<DependencyEdge>) {
    let mut nodes = Vec::new();
    let mut edges = Vec::new();

    for equation in &model.equations {
        extract_from_expr(&equation.lhs, &mut nodes, &mut edges, node_counter);
        extract_from_expr(&equation.rhs, &mut nodes, &mut edges, node_counter);
    }

    (nodes, edges)
}

/// Helper function to extract nodes and edges from a reaction system
fn extract_from_reaction_system(rs: &crate::ReactionSystem, node_counter: &mut usize) -> (Vec<ExpressionNode>, Vec<DependencyEdge>) {
    let mut nodes = Vec::new();
    let mut edges = Vec::new();

    for reaction in &rs.reactions {
        extract_from_expr(&reaction.rate, &mut nodes, &mut edges, node_counter);
    }

    (nodes, edges)
}

/// Helper function to extract nodes and edges from an expression
fn extract_from_expr(
    expr: &crate::Expr,
    nodes: &mut Vec<ExpressionNode>,
    edges: &mut Vec<DependencyEdge>,
    node_counter: &mut usize,
) -> String {
    match expr {
        crate::Expr::Number(n) => {
            let node_id = format!("const_{}", node_counter);
            *node_counter += 1;

            nodes.push(ExpressionNode {
                id: node_id.clone(),
                node_type: ExpressionNodeType::Constant,
                value: Some(*n),
            });

            node_id
        }
        crate::Expr::Variable(var) => {
            let node_id = var.clone();

            // Only add node if not already present
            if !nodes.iter().any(|n| n.id == node_id) {
                nodes.push(ExpressionNode {
                    id: node_id.clone(),
                    node_type: ExpressionNodeType::Variable,
                    value: None,
                });
            }

            node_id
        }
        crate::Expr::Operator(op_node) => {
            let node_id = format!("op_{}_{}", op_node.op, node_counter);
            *node_counter += 1;

            nodes.push(ExpressionNode {
                id: node_id.clone(),
                node_type: ExpressionNodeType::Operator(op_node.op.clone()),
                value: None,
            });

            // Process operands and create edges
            for (i, arg) in op_node.args.iter().enumerate() {
                let arg_id = extract_from_expr(arg, nodes, edges, node_counter);
                edges.push(DependencyEdge {
                    from: arg_id,
                    to: node_id.clone(),
                    edge_type: format!("operand_{}", i),
                });
            }

            node_id
        }
    }
}

impl ComponentGraph {
    /// Export graph to DOT format for Graphviz
    ///
    /// # Returns
    ///
    /// * `String` - DOT representation of the graph
    pub fn to_dot(&self) -> String {
        let mut dot = String::from("digraph ComponentGraph {\n");
        dot.push_str("  rankdir=LR;\n");
        dot.push_str("  node [shape=box];\n\n");

        // Add nodes
        for node in &self.nodes {
            let shape = match node.component_type {
                ComponentType::Model => "ellipse",
                ComponentType::ReactionSystem => "box",
                ComponentType::DataLoader => "diamond",
                ComponentType::Operator => "hexagon",
            };

            let label = node.name.as_ref().unwrap_or(&node.id);
            dot.push_str(&format!("  \"{}\" [label=\"{}\" shape={}];\n",
                node.id, label, shape));
        }

        dot.push_str("\n");

        // Add edges
        for edge in &self.edges {
            dot.push_str(&format!("  \"{}\" -> \"{}\" [label=\"{}\"];\n",
                edge.from, edge.to, edge.coupling_type));
        }

        dot.push_str("}\n");
        dot
    }

    /// Export graph to Mermaid format
    ///
    /// # Returns
    ///
    /// * `String` - Mermaid representation of the graph
    pub fn to_mermaid(&self) -> String {
        let mut mermaid = String::from("graph LR\n");

        // Add nodes with types
        for node in &self.nodes {
            let shape = match node.component_type {
                ComponentType::Model => ("(", ")"),
                ComponentType::ReactionSystem => ("[", "]"),
                ComponentType::DataLoader => ("{", "}"),
                ComponentType::Operator => ("((", "))"),
            };

            let label = node.name.as_ref().unwrap_or(&node.id);
            mermaid.push_str(&format!("  {}{}{}{}\n",
                node.id, shape.0, label, shape.1));
        }

        // Add edges
        for edge in &self.edges {
            mermaid.push_str(&format!("  {} -->|{}| {}\n",
                edge.from, edge.coupling_type, edge.to));
        }

        mermaid
    }

    /// Export graph to JSON format
    ///
    /// # Returns
    ///
    /// * `String` - JSON representation of the graph
    pub fn to_json_graph(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_else(|_| "{}".to_string())
    }
}

impl ExpressionGraph {
    /// Export graph to DOT format for Graphviz
    ///
    /// # Returns
    ///
    /// * `String` - DOT representation of the expression graph
    pub fn to_dot(&self) -> String {
        let mut dot = String::from("digraph ExpressionGraph {\n");
        dot.push_str("  rankdir=TB;\n");
        dot.push_str("  node [shape=circle];\n\n");

        // Add nodes
        for node in &self.nodes {
            let (shape, label) = match &node.node_type {
                ExpressionNodeType::Variable => ("ellipse", node.id.clone()),
                ExpressionNodeType::Constant => ("box", format!("{}", node.value.unwrap_or(0.0))),
                ExpressionNodeType::Operator(op) => ("diamond", op.clone()),
            };

            dot.push_str(&format!("  \"{}\" [label=\"{}\" shape={}];\n",
                node.id, label, shape));
        }

        dot.push_str("\n");

        // Add edges
        for edge in &self.edges {
            dot.push_str(&format!("  \"{}\" -> \"{}\";\n",
                edge.from, edge.to));
        }

        dot.push_str("}\n");
        dot
    }

    /// Export graph to Mermaid format
    ///
    /// # Returns
    ///
    /// * `String` - Mermaid representation of the expression graph
    pub fn to_mermaid(&self) -> String {
        let mut mermaid = String::from("graph TD\n");

        // Add nodes with appropriate shapes
        for node in &self.nodes {
            let (shape_start, shape_end, label) = match &node.node_type {
                ExpressionNodeType::Variable => ("(", ")", format!("{}", node.id)),
                ExpressionNodeType::Constant => ("[", "]", format!("{}", node.value.unwrap_or(0.0))),
                ExpressionNodeType::Operator(op) => ("{", "}", format!("{}", op)),
            };

            mermaid.push_str(&format!("  {}{}{}{}\n", node.id, shape_start, label, shape_end));
        }

        // Add edges
        for edge in &self.edges {
            mermaid.push_str(&format!("  {} --> {}\n", edge.from, edge.to));
        }

        mermaid
    }

    /// Export graph to JSON format
    ///
    /// # Returns
    ///
    /// * `String` - JSON representation of the graph
    pub fn to_json_graph(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_else(|_| "{}".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Model, ReactionSystem, Expr, ExpressionNode as ExprNode};
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
            variables: HashMap::new(),
            equations: vec![],
            events: None,
            description: None,
        });
        models.insert("model2".to_string(), Model {
            name: Some("Test Model 2".to_string()),
            variables: HashMap::new(),
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
            variables: HashMap::new(),
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
            variables: HashMap::new(),
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

    #[test]
    fn test_expression_graph() {
        let expr = Expr::Operator(ExprNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Number(1.0),
            ],
            wrt: None,
            dim: None,
        });

        let graph = expression_graph(&expr);
        assert_eq!(graph.nodes.len(), 3); // x, 1.0, +
        assert_eq!(graph.edges.len(), 2); // x -> +, 1.0 -> +
    }

    #[test]
    fn test_component_graph_to_dot() {
        let graph = ComponentGraph {
            nodes: vec![
                ComponentNode {
                    id: "model1".to_string(),
                    component_type: ComponentType::Model,
                    name: Some("Test Model".to_string()),
                },
            ],
            edges: vec![],
        };

        let dot = graph.to_dot();
        assert!(dot.contains("digraph ComponentGraph"));
        assert!(dot.contains("model1"));
        assert!(dot.contains("Test Model"));
    }

    #[test]
    fn test_component_graph_to_mermaid() {
        let graph = ComponentGraph {
            nodes: vec![
                ComponentNode {
                    id: "model1".to_string(),
                    component_type: ComponentType::Model,
                    name: Some("Test Model".to_string()),
                },
            ],
            edges: vec![],
        };

        let mermaid = graph.to_mermaid();
        assert!(mermaid.contains("graph LR"));
        assert!(mermaid.contains("model1(Test Model)"));
    }

    #[test]
    fn test_expression_graph_to_mermaid() {
        let expr = Expr::Operator(ExprNode {
            op: "+".to_string(),
            args: vec![
                Expr::Variable("x".to_string()),
                Expr::Number(1.0),
            ],
            wrt: None,
            dim: None,
        });

        let graph = expression_graph(&expr);
        let mermaid = graph.to_mermaid();

        assert!(mermaid.contains("graph TD"));
        assert!(mermaid.contains("x(x)"));  // Variable node
        assert!(mermaid.contains("const_"));  // Constant node
        assert!(mermaid.contains("{+}"));    // Operator node
        assert!(mermaid.contains("-->"));    // Edge
    }
}