//! Coupled system flattening
//!
//! This module implements an algorithm to flatten a coupled system of models
//! and reaction systems into a single unified system with dot-namespaced
//! variables.

use crate::types::{CouplingEntry, EsmFile, Expr, ExpressionNode, Model, ReactionSystem};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A coupled system flattened into a single system with dot-namespaced variables
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlattenedSystem {
    /// All state variables (dot-namespaced)
    pub state_variables: Vec<String>,
    /// All parameters (dot-namespaced)
    pub parameters: Vec<String>,
    /// Map from namespaced variable name to its description/unit info
    pub variables: HashMap<String, String>,
    /// Flattened equations from all source systems
    pub equations: Vec<FlattenedEquation>,
    /// Metadata about the flattening operation
    pub metadata: FlattenMetadata,
}

/// A single equation in the flattened system, tracking its origin
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlattenedEquation {
    /// Left-hand side expression (serialized)
    pub lhs: String,
    /// Right-hand side expression (serialized)
    pub rhs: String,
    /// Which system this equation originated from
    pub source_system: String,
}

/// Metadata about the flattening process
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlattenMetadata {
    /// Names of all source systems that were flattened
    pub source_systems: Vec<String>,
    /// Human-readable descriptions of coupling rules that were applied
    pub coupling_rules: Vec<String>,
}

/// Flatten a coupled ESM file into a single unified system.
///
/// The algorithm:
/// 1. Iterates over all models and reaction systems in the file
/// 2. Namespaces all variables with a "SystemName." prefix
/// 3. Processes coupling entries to produce mapping/merge descriptions
/// 4. Returns a unified flattened system
///
/// # Arguments
///
/// * `file` - The ESM file containing models, reaction systems, and coupling
///
/// # Returns
///
/// * `Ok(FlattenedSystem)` on success
/// * `Err(String)` if the file has no models or reaction systems to flatten
///
/// # Examples
///
/// ```rust
/// use earthsci_toolkit::types::{EsmFile, Metadata, Model, ModelVariable, VariableType, Equation, Expr};
/// use earthsci_toolkit::flatten::flatten;
/// use std::collections::HashMap;
///
/// let mut models = HashMap::new();
/// let mut vars = HashMap::new();
/// vars.insert("x".to_string(), ModelVariable {
///     var_type: VariableType::State,
///     units: Some("m".to_string()),
///     default: Some(0.0),
///     description: None,
///     expression: None,
/// });
/// models.insert("sys".to_string(), Model {
///     name: Some("System".to_string()),
///     reference: None,
///     variables: vars,
///     equations: vec![Equation {
///         lhs: Expr::Variable("d(x)/dt".to_string()),
///         rhs: Expr::Number(1.0),
///     }],
///     discrete_events: None,
///     continuous_events: None,
///     description: None,
/// });
///
/// let file = EsmFile {
///     esm: "0.1.0".to_string(),
///     metadata: Metadata {
///         name: Some("test".to_string()),
///         description: None,
///         authors: None,
///         license: None,
///         created: None,
///         modified: None,
///         tags: None,
///         references: None,
///     },
///     models: Some(models),
///     reaction_systems: None,
///     data_loaders: None,
///     operators: None,
///     coupling: None,
///     domain: None,
/// };
///
/// let flat = flatten(&file).unwrap();
/// assert_eq!(flat.state_variables, vec!["sys.x"]);
/// ```
pub fn flatten(file: &EsmFile) -> Result<FlattenedSystem, String> {
    let has_models = file.models.as_ref().is_some_and(|m| !m.is_empty());
    let has_rs = file
        .reaction_systems
        .as_ref()
        .is_some_and(|rs| !rs.is_empty());

    if !has_models && !has_rs {
        return Err("No models or reaction systems to flatten".to_string());
    }

    let mut state_variables = Vec::new();
    let mut parameters = Vec::new();
    let mut variables: HashMap<String, String> = HashMap::new();
    let mut equations = Vec::new();
    let mut source_systems = Vec::new();

    // Process models
    if let Some(ref models) = file.models {
        let mut sorted_keys: Vec<&String> = models.keys().collect();
        sorted_keys.sort();
        for system_name in sorted_keys {
            let model = &models[system_name];
            source_systems.push(system_name.clone());
            flatten_model(
                system_name,
                model,
                &mut state_variables,
                &mut parameters,
                &mut variables,
                &mut equations,
            );
        }
    }

    // Process reaction systems
    if let Some(ref reaction_systems) = file.reaction_systems {
        let mut sorted_keys: Vec<&String> = reaction_systems.keys().collect();
        sorted_keys.sort();
        for system_name in sorted_keys {
            let rs = &reaction_systems[system_name];
            source_systems.push(system_name.clone());
            flatten_reaction_system(
                system_name,
                rs,
                &mut state_variables,
                &mut parameters,
                &mut variables,
                &mut equations,
            );
        }
    }

    // Process coupling entries
    let coupling_rules = process_coupling(file, &mut equations, &variables);

    Ok(FlattenedSystem {
        state_variables,
        parameters,
        variables,
        equations,
        metadata: FlattenMetadata {
            source_systems,
            coupling_rules,
        },
    })
}

/// Flatten a single model, adding its namespaced variables and equations
fn flatten_model(
    system_name: &str,
    model: &Model,
    state_variables: &mut Vec<String>,
    parameters: &mut Vec<String>,
    variables: &mut HashMap<String, String>,
    equations: &mut Vec<FlattenedEquation>,
) {
    use crate::types::VariableType;

    // Collect and sort variable names for deterministic output
    let mut var_names: Vec<&String> = model.variables.keys().collect();
    var_names.sort();

    for var_name in var_names {
        let var = &model.variables[var_name];
        let namespaced = format!("{}.{}", system_name, var_name);

        let description = var.description.clone().unwrap_or_default();
        let units = var.units.as_deref().unwrap_or("dimensionless");
        let info = format!("{} [{}]", description, units).trim().to_string();
        variables.insert(namespaced.clone(), info);

        match var.var_type {
            VariableType::State => state_variables.push(namespaced),
            VariableType::Parameter => parameters.push(namespaced),
            VariableType::Observed => {
                // Observed variables are neither state nor parameter but still tracked
            }
        }
    }

    // Namespace equations
    for eq in &model.equations {
        let lhs = namespace_expr(&eq.lhs, system_name);
        let rhs = namespace_expr(&eq.rhs, system_name);
        equations.push(FlattenedEquation {
            lhs: expr_to_string(&lhs),
            rhs: expr_to_string(&rhs),
            source_system: system_name.to_string(),
        });
    }
}

/// Flatten a single reaction system, adding its namespaced species and reactions
fn flatten_reaction_system(
    system_name: &str,
    rs: &ReactionSystem,
    state_variables: &mut Vec<String>,
    parameters: &mut Vec<String>,
    variables: &mut HashMap<String, String>,
    equations: &mut Vec<FlattenedEquation>,
) {
    // Species become state variables
    for species in &rs.species {
        let namespaced = format!("{}.{}", system_name, species.name);
        let description = species.description.clone().unwrap_or_default();
        let units = species.units.as_deref().unwrap_or("dimensionless");
        let info = format!("{} [{}]", description, units).trim().to_string();
        variables.insert(namespaced.clone(), info);
        state_variables.push(namespaced);
    }

    // Parameters
    let mut param_names: Vec<&String> = rs.parameters.keys().collect();
    param_names.sort();
    for param_name in param_names {
        let param = &rs.parameters[param_name];
        let namespaced = format!("{}.{}", system_name, param_name);
        let description = param.description.clone().unwrap_or_default();
        let units = param.units.as_deref().unwrap_or("dimensionless");
        let info = format!("{} [{}]", description, units).trim().to_string();
        variables.insert(namespaced.clone(), info);
        parameters.push(namespaced);
    }

    // Convert reactions to equations: for each reaction produce a rate equation
    for reaction in &rs.reactions {
        let rate_str = expr_to_string(&namespace_expr(&reaction.rate, system_name));
        let reaction_name = reaction.name.as_deref().unwrap_or("unnamed_reaction");

        // Build a description of the reaction as an equation
        let substrates: Vec<String> = reaction
            .substrates
            .iter()
            .map(|s| {
                let coeff = s.coefficient.unwrap_or(1.0);
                if (coeff - 1.0).abs() < f64::EPSILON {
                    format!("{}.{}", system_name, s.species)
                } else {
                    format!("{}*{}.{}", coeff, system_name, s.species)
                }
            })
            .collect();
        let products: Vec<String> = reaction
            .products
            .iter()
            .map(|p| {
                let coeff = p.coefficient.unwrap_or(1.0);
                if (coeff - 1.0).abs() < f64::EPSILON {
                    format!("{}.{}", system_name, p.species)
                } else {
                    format!("{}*{}.{}", coeff, system_name, p.species)
                }
            })
            .collect();

        let lhs_str = format!(
            "{}: {} -> {}",
            reaction_name,
            substrates.join(" + "),
            products.join(" + ")
        );

        equations.push(FlattenedEquation {
            lhs: lhs_str,
            rhs: rate_str,
            source_system: system_name.to_string(),
        });
    }
}

/// Apply dot-namespacing to an expression tree, prefixing all variable
/// references with the given system name.
fn namespace_expr(expr: &Expr, system_name: &str) -> Expr {
    match expr {
        Expr::Number(n) => Expr::Number(*n),
        Expr::Variable(name) => {
            // Don't double-namespace if already contains a dot
            if name.contains('.') {
                Expr::Variable(name.clone())
            } else {
                Expr::Variable(format!("{}.{}", system_name, name))
            }
        }
        Expr::Operator(op_node) => {
            let namespaced_args: Vec<Expr> = op_node
                .args
                .iter()
                .map(|a| namespace_expr(a, system_name))
                .collect();
            Expr::Operator(ExpressionNode {
                op: op_node.op.clone(),
                args: namespaced_args,
                wrt: op_node.wrt.as_ref().map(|w| {
                    if w.contains('.') {
                        w.clone()
                    } else {
                        format!("{}.{}", system_name, w)
                    }
                }),
                dim: op_node.dim.clone(),
            })
        }
    }
}

/// Serialize an Expr to a human-readable string representation
fn expr_to_string(expr: &Expr) -> String {
    match expr {
        Expr::Number(n) => {
            if *n == (*n as i64) as f64 {
                format!("{}", *n as i64)
            } else {
                format!("{}", n)
            }
        }
        Expr::Variable(name) => name.clone(),
        Expr::Operator(op_node) => {
            let args_str: Vec<String> = op_node.args.iter().map(expr_to_string).collect();
            match op_node.op.as_str() {
                "+" | "-" | "*" | "/" | "^" => {
                    if args_str.len() == 2 {
                        format!("({} {} {})", args_str[0], op_node.op, args_str[1])
                    } else if args_str.len() == 1 && op_node.op == "-" {
                        format!("(-{})", args_str[0])
                    } else {
                        format!("{}({})", op_node.op, args_str.join(", "))
                    }
                }
                "D" => {
                    if let Some(ref wrt) = op_node.wrt {
                        format!("d({})/d{}", args_str.join(", "), wrt)
                    } else {
                        format!("D({})", args_str.join(", "))
                    }
                }
                _ => format!("{}({})", op_node.op, args_str.join(", ")),
            }
        }
    }
}

/// Process coupling entries and apply their effects to the flattened equations.
///
/// Returns a list of human-readable coupling rule descriptions.
fn process_coupling(
    file: &EsmFile,
    equations: &mut Vec<FlattenedEquation>,
    _variables: &HashMap<String, String>,
) -> Vec<String> {
    let mut rules = Vec::new();

    let coupling = match file.coupling {
        Some(ref c) => c,
        None => return rules,
    };

    for entry in coupling {
        match entry {
            CouplingEntry::OperatorCompose {
                systems,
                description,
                ..
            } => {
                let desc = description
                    .clone()
                    .unwrap_or_else(|| format!("Operator compose: {}", systems.join(" + ")));
                rules.push(desc);
            }
            CouplingEntry::Couple {
                systems,
                connector,
                description,
                ..
            } => {
                let desc = description
                    .clone()
                    .unwrap_or_else(|| format!("Couple: {}", systems.join(" <-> ")));
                rules.push(desc.clone());

                // If the connector has equations, add them to the flattened system
                if let Some(eqs) = connector.get("equations").and_then(|e| e.as_array()) {
                    for eq_val in eqs {
                        if let (Some(lhs), Some(rhs)) = (eq_val.get("lhs"), eq_val.get("rhs")) {
                            equations.push(FlattenedEquation {
                                lhs: serde_json::to_string(lhs).unwrap_or_default(),
                                rhs: serde_json::to_string(rhs).unwrap_or_default(),
                                source_system: format!("coupling({})", systems.join(",")),
                            });
                        }
                    }
                }
            }
            CouplingEntry::VariableMap {
                from,
                to,
                transform,
                factor,
                description,
                ..
            } => {
                let desc = description.clone().unwrap_or_else(|| {
                    let factor_str = factor
                        .map(|f| format!(" (factor={})", f))
                        .unwrap_or_default();
                    format!(
                        "VariableMap: {} -> {} [{}]{}",
                        from, to, transform, factor_str
                    )
                });
                rules.push(desc);

                // Generate a mapping equation
                let rhs = match (transform.as_str(), factor) {
                    ("conversion_factor", Some(f)) => format!("({} * {})", from, f),
                    _ => from.clone(),
                };
                equations.push(FlattenedEquation {
                    lhs: to.clone(),
                    rhs,
                    source_system: "coupling(variable_map)".to_string(),
                });
            }
            CouplingEntry::OperatorApply {
                operator,
                description,
                ..
            } => {
                let desc = description
                    .clone()
                    .unwrap_or_else(|| format!("OperatorApply: {}", operator));
                rules.push(desc);
            }
            CouplingEntry::Callback {
                callback_id,
                description,
                ..
            } => {
                let desc = description
                    .clone()
                    .unwrap_or_else(|| format!("Callback: {}", callback_id));
                rules.push(desc);
            }
            CouplingEntry::Event {
                event_type,
                name,
                description,
                ..
            } => {
                let desc = description.clone().unwrap_or_else(|| {
                    format!(
                        "Event({}): {}",
                        event_type,
                        name.as_deref().unwrap_or("unnamed")
                    )
                });
                rules.push(desc);
            }
        }
    }

    rules
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{
        Equation, Metadata, Model, ModelVariable, Parameter, Reaction, ReactionSystem, Species,
        StoichiometricEntry, VariableType,
    };

    fn make_metadata() -> Metadata {
        Metadata {
            name: Some("test".to_string()),
            description: None,
            authors: None,
            license: None,
            created: None,
            modified: None,
            tags: None,
            references: None,
        }
    }

    #[test]
    fn test_flatten_single_model() {
        let mut vars = HashMap::new();
        vars.insert(
            "x".to_string(),
            ModelVariable {
                var_type: VariableType::State,
                units: Some("m".to_string()),
                default: Some(0.0),
                description: None,
                expression: None,
            },
        );
        vars.insert(
            "k".to_string(),
            ModelVariable {
                var_type: VariableType::Parameter,
                units: None,
                default: Some(1.0),
                description: None,
                expression: None,
            },
        );

        let mut models = HashMap::new();
        models.insert(
            "sys".to_string(),
            Model {
                name: Some("System".to_string()),
                reference: None,
                variables: vars,
                equations: vec![Equation {
                    lhs: Expr::Variable("d(x)/dt".to_string()),
                    rhs: Expr::Variable("k".to_string()),
                }],
                discrete_events: None,
                continuous_events: None,
                description: None,
            },
        );

        let file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: make_metadata(),
            models: Some(models),
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
        };

        let flat = flatten(&file).unwrap();
        assert_eq!(flat.state_variables, vec!["sys.x"]);
        assert_eq!(flat.parameters, vec!["sys.k"]);
        assert_eq!(flat.equations.len(), 1);
        assert_eq!(flat.equations[0].source_system, "sys");
        assert_eq!(flat.equations[0].lhs, "sys.d(x)/dt");
        assert_eq!(flat.equations[0].rhs, "sys.k");
        assert_eq!(flat.metadata.source_systems, vec!["sys"]);
    }

    #[test]
    fn test_flatten_empty_file() {
        let file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: make_metadata(),
            models: None,
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
        };

        let result = flatten(&file);
        assert!(result.is_err());
        assert_eq!(
            result.unwrap_err(),
            "No models or reaction systems to flatten"
        );
    }

    #[test]
    fn test_flatten_reaction_system() {
        let mut params = HashMap::new();
        params.insert(
            "k1".to_string(),
            Parameter {
                units: Some("1/s".to_string()),
                default: Some(0.1),
                description: None,
            },
        );

        let mut reaction_systems = HashMap::new();
        reaction_systems.insert(
            "chem".to_string(),
            ReactionSystem {
                name: Some("Chemistry".to_string()),
                species: vec![
                    Species {
                        name: "A".to_string(),
                        units: Some("mol/L".to_string()),
                        default: Some(1.0),
                        description: None,
                    },
                    Species {
                        name: "B".to_string(),
                        units: Some("mol/L".to_string()),
                        default: Some(0.0),
                        description: None,
                    },
                ],
                parameters: params,
                reactions: vec![Reaction {
                    name: Some("r1".to_string()),
                    substrates: vec![StoichiometricEntry {
                        species: "A".to_string(),
                        coefficient: Some(1.0),
                    }],
                    products: vec![StoichiometricEntry {
                        species: "B".to_string(),
                        coefficient: Some(1.0),
                    }],
                    rate: Expr::Operator(ExpressionNode {
                        op: "*".to_string(),
                        args: vec![
                            Expr::Variable("k1".to_string()),
                            Expr::Variable("A".to_string()),
                        ],
                        wrt: None,
                        dim: None,
                    }),
                    description: None,
                }],
                description: None,
            },
        );

        let file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: make_metadata(),
            models: None,
            reaction_systems: Some(reaction_systems),
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
        };

        let flat = flatten(&file).unwrap();
        assert_eq!(flat.state_variables, vec!["chem.A", "chem.B"]);
        assert_eq!(flat.parameters, vec!["chem.k1"]);
        assert_eq!(flat.equations.len(), 1);
        assert_eq!(flat.equations[0].source_system, "chem");
        assert!(flat.equations[0].rhs.contains("chem.k1"));
        assert!(flat.equations[0].rhs.contains("chem.A"));
    }

    #[test]
    fn test_flatten_with_coupling() {
        let mut models = HashMap::new();
        let mut vars_a = HashMap::new();
        vars_a.insert(
            "x".to_string(),
            ModelVariable {
                var_type: VariableType::State,
                units: None,
                default: None,
                description: None,
                expression: None,
            },
        );
        models.insert(
            "A".to_string(),
            Model {
                name: None,
                reference: None,
                variables: vars_a,
                equations: vec![],
                discrete_events: None,
                continuous_events: None,
                description: None,
            },
        );

        let mut vars_b = HashMap::new();
        vars_b.insert(
            "y".to_string(),
            ModelVariable {
                var_type: VariableType::Parameter,
                units: None,
                default: None,
                description: None,
                expression: None,
            },
        );
        models.insert(
            "B".to_string(),
            Model {
                name: None,
                reference: None,
                variables: vars_b,
                equations: vec![],
                discrete_events: None,
                continuous_events: None,
                description: None,
            },
        );

        let coupling = vec![CouplingEntry::VariableMap {
            from: "A.x".to_string(),
            to: "B.y".to_string(),
            transform: "identity".to_string(),
            factor: None,
            description: None,
        }];

        let file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: make_metadata(),
            models: Some(models),
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: Some(coupling),
            domain: None,
        };

        let flat = flatten(&file).unwrap();
        assert!(flat.metadata.coupling_rules.len() == 1);
        assert!(flat.metadata.coupling_rules[0].contains("VariableMap"));
        // Should have an extra equation from the coupling
        assert!(
            flat.equations
                .iter()
                .any(|e| e.source_system == "coupling(variable_map)")
        );
    }

    #[test]
    fn test_namespace_expr() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![Expr::Variable("x".to_string()), Expr::Number(1.0)],
            wrt: None,
            dim: None,
        });

        let namespaced = namespace_expr(&expr, "sys");
        match &namespaced {
            Expr::Operator(op) => {
                assert_eq!(op.args[0], Expr::Variable("sys.x".to_string()));
                assert_eq!(op.args[1], Expr::Number(1.0));
            }
            _ => panic!("Expected Operator"),
        }
    }

    #[test]
    fn test_namespace_expr_no_double_namespace() {
        let expr = Expr::Variable("other.x".to_string());
        let namespaced = namespace_expr(&expr, "sys");
        assert_eq!(namespaced, Expr::Variable("other.x".to_string()));
    }

    #[test]
    fn test_expr_to_string() {
        let expr = Expr::Operator(ExpressionNode {
            op: "+".to_string(),
            args: vec![Expr::Variable("x".to_string()), Expr::Number(1.0)],
            wrt: None,
            dim: None,
        });
        assert_eq!(expr_to_string(&expr), "(x + 1)");

        let expr2 = Expr::Operator(ExpressionNode {
            op: "sin".to_string(),
            args: vec![Expr::Variable("x".to_string())],
            wrt: None,
            dim: None,
        });
        assert_eq!(expr_to_string(&expr2), "sin(x)");
    }
}
