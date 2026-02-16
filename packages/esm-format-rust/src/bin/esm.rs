//! ESM Format CLI Tool
//!
//! Command-line interface for working with ESM files

#[cfg(feature = "cli")]
use clap::{Parser, Subcommand};
#[cfg(feature = "cli")]
use esm_format::{load, save, save_compact, validate, component_graph, component_exists};
#[cfg(feature = "cli")]
use std::fs;
#[cfg(feature = "cli")]
use std::path::PathBuf;
#[cfg(feature = "cli")]
use std::collections::HashMap;

#[cfg(feature = "cli")]
#[derive(Parser)]
#[command(name = "esm")]
#[command(about = "A CLI tool for EarthSciML Serialization Format")]
#[command(version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[cfg(feature = "cli")]
#[derive(Subcommand)]
enum Commands {
    /// Validate an ESM file
    Validate {
        /// Path to the ESM file to validate
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Show detailed validation output
        #[arg(long)]
        verbose: bool,
    },
    /// Display expressions in an ESM file with pretty-printing
    Display {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Output format (unicode, latex, ascii)
        #[arg(short, long, default_value = "unicode")]
        format: String,
    },
    /// Extract a single component from an ESM file
    Extract {
        /// Input ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Component ID to extract
        #[arg(long)]
        component: String,
        /// Output file (or stdout if not specified)
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    /// Compare two ESM files semantically
    Diff {
        /// First ESM file
        #[arg(value_name = "FILE1")]
        file1: PathBuf,
        /// Second ESM file
        #[arg(value_name = "FILE2")]
        file2: PathBuf,
    },
    /// Generate stoichiometric matrix for a reaction system
    Stoich {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Reaction system ID
        #[arg(long)]
        system: String,
    },
    /// Generate system or expression graphs
    Graph {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Graph level (component or expression)
        #[arg(long, default_value = "component")]
        level: String,
        /// Output format (dot, mermaid, json)
        #[arg(short, long, default_value = "dot")]
        format: String,
        /// System ID (for expression-level graphs)
        #[arg(long)]
        system: Option<String>,
    },
    /// Convert an ESM file to a different format
    Convert {
        /// Input ESM file
        #[arg(value_name = "INPUT")]
        input: PathBuf,
        /// Output file (or stdout if not specified)
        #[arg(short, long, value_name = "OUTPUT")]
        output: Option<PathBuf>,
        /// Output format (json, compact-json)
        #[arg(short, long, default_value = "json")]
        format: String,
    },
    /// Show information about an ESM file
    Info {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
    },
}

#[cfg(feature = "cli")]
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Validate { file, verbose } => {
            let content = fs::read_to_string(&file)?;

            // First try to load and parse
            match load(&content) {
                Ok(esm_file) => {
                    println!("✓ JSON parsing and schema validation passed");

                    // Perform structural validation
                    let validation_result = validate(&esm_file);

                    if validation_result.is_valid {
                        println!("✓ Structural validation passed");
                        if verbose && !validation_result.unit_warnings.is_empty() {
                            println!("Warnings:");
                            for warning in validation_result.unit_warnings {
                                println!("  ⚠ {}", warning);
                            }
                        }
                    } else {
                        println!("✗ Structural validation failed");

                        if !validation_result.schema_errors.is_empty() {
                            println!("Schema errors:");
                            for error in &validation_result.schema_errors {
                                println!("  ✗ {}: {}", error.path, error.message);
                            }
                        }

                        if !validation_result.structural_errors.is_empty() {
                            println!("Structural errors:");
                            for error in &validation_result.structural_errors {
                                println!("  ✗ {}: {}", error.path, error.message);
                            }
                        }

                        std::process::exit(1);
                    }
                },
                Err(e) => {
                    println!("✗ Validation failed: {}", e);
                    std::process::exit(1);
                }
            }
        },
        Commands::Display { file, format } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Displaying expressions in {}:", file.display());

            // Print model equations
            if let Some(ref models) = esm_file.models {
                for (model_id, model) in models {
                    println!("\nModel: {} ({})", model_id, model.name.as_deref().unwrap_or("unnamed"));
                    for (i, equation) in model.equations.iter().enumerate() {
                        let lhs = match format.as_str() {
                            "unicode" => esm_format::to_unicode(&equation.lhs),
                            "latex" => esm_format::to_latex(&equation.lhs),
                            "ascii" => esm_format::to_ascii(&equation.lhs),
                            _ => {
                                eprintln!("Unsupported format: {}", format);
                                std::process::exit(1);
                            }
                        };
                        let rhs = match format.as_str() {
                            "unicode" => esm_format::to_unicode(&equation.rhs),
                            "latex" => esm_format::to_latex(&equation.rhs),
                            "ascii" => esm_format::to_ascii(&equation.rhs),
                            _ => unreachable!(),
                        };
                        println!("  Eq {}: {} = {}", i + 1, lhs, rhs);
                    }
                }
            }

            // Print reaction rates
            if let Some(ref reaction_systems) = esm_file.reaction_systems {
                for (rs_id, rs) in reaction_systems {
                    println!("\nReaction System: {} ({})", rs_id, rs.name.as_deref().unwrap_or("unnamed"));
                    for (i, reaction) in rs.reactions.iter().enumerate() {
                        let rate = match format.as_str() {
                            "unicode" => esm_format::to_unicode(&reaction.rate),
                            "latex" => esm_format::to_latex(&reaction.rate),
                            "ascii" => esm_format::to_ascii(&reaction.rate),
                            _ => unreachable!(),
                        };
                        println!("  Reaction {}: rate = {}", i + 1, rate);
                    }
                }
            }
        },
        Commands::Extract { file, component, output } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            // Check if component exists
            if !component_exists(&esm_file, &component) {
                eprintln!("Component '{}' not found in the ESM file", component);
                std::process::exit(1);
            }

            // Create a new ESM file with just the requested component
            let mut extracted_esm = esm_format::EsmFile {
                esm: esm_file.esm.clone(),
                metadata: esm_file.metadata.clone(),
                models: None,
                reaction_systems: None,
                data_loaders: None,
                operators: None,
                coupling: None,
                domain: esm_file.domain.clone(),
                solver: esm_file.solver.clone(),
            };

            // Extract the specific component
            if let Some(ref models) = esm_file.models {
                if let Some(model) = models.get(&component) {
                    let mut extracted_models = HashMap::new();
                    extracted_models.insert(component.clone(), model.clone());
                    extracted_esm.models = Some(extracted_models);
                }
            }

            if let Some(ref reaction_systems) = esm_file.reaction_systems {
                if let Some(rs) = reaction_systems.get(&component) {
                    let mut extracted_rs = HashMap::new();
                    extracted_rs.insert(component.clone(), rs.clone());
                    extracted_esm.reaction_systems = Some(extracted_rs);
                }
            }

            if let Some(ref data_loaders) = esm_file.data_loaders {
                if let Some(dl) = data_loaders.get(&component) {
                    let mut extracted_dl = HashMap::new();
                    extracted_dl.insert(component.clone(), dl.clone());
                    extracted_esm.data_loaders = Some(extracted_dl);
                }
            }

            if let Some(ref operators) = esm_file.operators {
                if let Some(op) = operators.get(&component) {
                    let mut extracted_op = HashMap::new();
                    extracted_op.insert(component.clone(), op.clone());
                    extracted_esm.operators = Some(extracted_op);
                }
            }

            let output_content = save(&extracted_esm)?;

            if let Some(output_path) = output {
                fs::write(&output_path, output_content)?;
                println!("Extracted component '{}' to {}", component, output_path.display());
            } else {
                print!("{}", output_content);
            }
        },
        Commands::Diff { file1, file2 } => {
            let content1 = fs::read_to_string(&file1)?;
            let content2 = fs::read_to_string(&file2)?;
            let esm_file1 = load(&content1)?;
            let esm_file2 = load(&content2)?;

            println!("Comparing {} and {}:", file1.display(), file2.display());

            // Simple semantic comparison - we could make this more sophisticated
            let json1 = serde_json::to_value(&esm_file1)?;
            let json2 = serde_json::to_value(&esm_file2)?;

            if json1 == json2 {
                println!("✓ Files are semantically identical");
            } else {
                println!("✗ Files differ semantically");

                // Basic structural comparison
                if esm_file1.esm != esm_file2.esm {
                    println!("  ESM version: {} vs {}", esm_file1.esm, esm_file2.esm);
                }

                let models1_count = esm_file1.models.as_ref().map(|m| m.len()).unwrap_or(0);
                let models2_count = esm_file2.models.as_ref().map(|m| m.len()).unwrap_or(0);
                if models1_count != models2_count {
                    println!("  Model count: {} vs {}", models1_count, models2_count);
                }

                let rs1_count = esm_file1.reaction_systems.as_ref().map(|rs| rs.len()).unwrap_or(0);
                let rs2_count = esm_file2.reaction_systems.as_ref().map(|rs| rs.len()).unwrap_or(0);
                if rs1_count != rs2_count {
                    println!("  Reaction system count: {} vs {}", rs1_count, rs2_count);
                }

                std::process::exit(1);
            }
        },
        Commands::Stoich { file, system } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            if let Some(ref reaction_systems) = esm_file.reaction_systems {
                if let Some(rs) = reaction_systems.get(&system) {
                    println!("Stoichiometric matrix for reaction system '{}':", system);

                    // Create species index map
                    let mut species_index = HashMap::new();
                    for (i, species) in rs.species.iter().enumerate() {
                        species_index.insert(species.name.clone(), i);
                    }

                    // Print species header
                    print!("{:>15}", "");
                    for species in &rs.species {
                        print!("{:>10}", species.name);
                    }
                    println!();

                    // Print reaction stoichiometry
                    for (reaction_idx, reaction) in rs.reactions.iter().enumerate() {
                        print!("Reaction {:>3}:", reaction_idx + 1);

                        let mut coeffs = vec![0.0; rs.species.len()];

                        // Substrates (negative coefficients)
                        for substrate in &reaction.substrates {
                            if let Some(&idx) = species_index.get(&substrate.species) {
                                coeffs[idx] -= substrate.coefficient.unwrap_or(1.0);
                            }
                        }

                        // Products (positive coefficients)
                        for product in &reaction.products {
                            if let Some(&idx) = species_index.get(&product.species) {
                                coeffs[idx] += product.coefficient.unwrap_or(1.0);
                            }
                        }

                        for coeff in coeffs {
                            print!("{:>10.1}", coeff);
                        }
                        println!();
                    }
                } else {
                    eprintln!("Reaction system '{}' not found", system);
                    std::process::exit(1);
                }
            } else {
                eprintln!("No reaction systems found in the file");
                std::process::exit(1);
            }
        },
        Commands::Graph { file, level, format, system } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            match level.as_str() {
                "component" => {
                    let graph = component_graph(&esm_file);

                    match format.as_str() {
                        "dot" => {
                            println!("digraph ESMComponents {{");
                            println!("  rankdir=LR;");
                            println!("  node [shape=box];");
                            println!();

                            // Nodes
                            for node in &graph.nodes {
                                let label = node.name.as_deref().unwrap_or(&node.id);
                                let shape = match node.component_type {
                                    esm_format::graph::ComponentType::Model => "ellipse",
                                    esm_format::graph::ComponentType::ReactionSystem => "box",
                                    esm_format::graph::ComponentType::DataLoader => "diamond",
                                    esm_format::graph::ComponentType::Operator => "hexagon",
                                };
                                println!("  \"{}\" [label=\"{}\", shape={}];", node.id, label, shape);
                            }

                            println!();

                            // Edges
                            for edge in &graph.edges {
                                println!("  \"{}\" -> \"{}\" [label=\"{}\"];", edge.from, edge.to, edge.coupling_type);
                            }

                            println!("}}");
                        },
                        "mermaid" => {
                            println!("graph LR");

                            for node in &graph.nodes {
                                let label = node.name.as_deref().unwrap_or(&node.id);
                                let shape_open = match node.component_type {
                                    esm_format::graph::ComponentType::Model => "(",
                                    esm_format::graph::ComponentType::ReactionSystem => "[",
                                    esm_format::graph::ComponentType::DataLoader => "{",
                                    esm_format::graph::ComponentType::Operator => "{{",
                                };
                                let shape_close = match node.component_type {
                                    esm_format::graph::ComponentType::Model => ")",
                                    esm_format::graph::ComponentType::ReactionSystem => "]",
                                    esm_format::graph::ComponentType::DataLoader => "}",
                                    esm_format::graph::ComponentType::Operator => "}}",
                                };
                                println!("  {}{}{}{}", node.id, shape_open, label, shape_close);
                            }

                            for edge in &graph.edges {
                                println!("  {} -->|{}| {}", edge.from, edge.coupling_type, edge.to);
                            }
                        },
                        "json" => {
                            let json_graph = serde_json::json!({
                                "nodes": graph.nodes.iter().map(|n| serde_json::json!({
                                    "id": n.id,
                                    "type": match n.component_type {
                                        esm_format::graph::ComponentType::Model => "model",
                                        esm_format::graph::ComponentType::ReactionSystem => "reaction_system",
                                        esm_format::graph::ComponentType::DataLoader => "data_loader",
                                        esm_format::graph::ComponentType::Operator => "operator",
                                    },
                                    "name": n.name
                                })).collect::<Vec<_>>(),
                                "edges": graph.edges.iter().map(|e| serde_json::json!({
                                    "from": e.from,
                                    "to": e.to,
                                    "type": e.coupling_type
                                })).collect::<Vec<_>>()
                            });
                            println!("{}", serde_json::to_string_pretty(&json_graph)?);
                        },
                        _ => {
                            eprintln!("Unsupported graph format: {}. Use dot, mermaid, or json.", format);
                            std::process::exit(1);
                        }
                    }
                },
                "expression" => {
                    // Expression-level graphs not yet implemented
                    if let Some(ref _sys) = system {
                        eprintln!("Expression-level graphs for system '{}' not yet implemented", _sys);
                    } else {
                        eprintln!("Expression-level graphs not yet implemented");
                    }
                    std::process::exit(1);
                },
                _ => {
                    eprintln!("Unsupported graph level: {}. Use component or expression.", level);
                    std::process::exit(1);
                }
            }
        },
        Commands::Convert { input, output, format } => {
            let content = fs::read_to_string(&input)?;
            let esm_file = load(&content)?;

            let output_content = match format.as_str() {
                "json" => save(&esm_file)?,
                "compact-json" => save_compact(&esm_file)?,
                _ => {
                    eprintln!("Unsupported format: {}", format);
                    std::process::exit(1);
                }
            };

            if let Some(output_path) = output {
                fs::write(&output_path, output_content)?;
                println!("Converted {} to {}", input.display(), output_path.display());
            } else {
                print!("{}", output_content);
            }
        },
        Commands::Info { file } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("ESM File Information for: {}", file.display());
            println!("ESM Version: {}", esm_file.esm);

            if let Some(ref name) = esm_file.metadata.name {
                println!("Model Name: {}", name);
            }
            if let Some(ref description) = esm_file.metadata.description {
                println!("Description: {}", description);
            }
            if let Some(ref authors) = esm_file.metadata.authors {
                println!("Authors: {}", authors.join(", "));
            }

            if let Some(ref models) = esm_file.models {
                println!("Models: {} component(s)", models.len());
                for (id, model) in models {
                    println!("  - {} ({} vars, {} eqs)",
                        id,
                        model.variables.len(),
                        model.equations.len()
                    );
                }
            }

            if let Some(ref reaction_systems) = esm_file.reaction_systems {
                println!("Reaction Systems: {} component(s)", reaction_systems.len());
                for (id, rs) in reaction_systems {
                    println!("  - {} ({} species, {} reactions)",
                        id,
                        rs.species.len(),
                        rs.reactions.len()
                    );
                }
            }

            if let Some(ref data_loaders) = esm_file.data_loaders {
                println!("Data Loaders: {} component(s)", data_loaders.len());
            }

            if let Some(ref operators) = esm_file.operators {
                println!("Operators: {} component(s)", operators.len());
            }

            if let Some(ref coupling) = esm_file.coupling {
                println!("Coupling Rules: {} rule(s)", coupling.len());
            }
        }
    }

    Ok(())
}

#[cfg(not(feature = "cli"))]
fn main() {
    eprintln!("CLI feature not enabled. Please compile with --features cli");
    std::process::exit(1);
}