//! ESM Format CLI Tool
//!
//! Command-line interface for working with ESM files

#[cfg(feature = "cli")]
use clap::{Parser, Subcommand};
#[cfg(feature = "cli")]
use esm_format::{load, save, save_compact, validate, validate_complete, component_graph, component_exists};
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
    /// Pretty-print mathematical expressions in an ESM file
    Pretty {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Output format (unicode, latex, ascii)
        #[arg(short, long, default_value = "unicode")]
        format: String,
    },
    /// Display expressions in an ESM file with pretty-printing (alias for pretty)
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
        /// Target format (json, compact-json, julia, python)
        #[arg(long, default_value = "json")]
        to: String,
    },
    /// Analyze system properties and metrics
    Analyze {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Analysis type (all, structure, complexity, coupling)
        #[arg(long, default_value = "all")]
        analysis_type: String,
    },
    /// Run basic simulations
    Simulate {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Simulation duration
        #[arg(long, default_value = "10.0")]
        time: f64,
        /// Output file for results
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    /// Show information about an ESM file
    Info {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
    },

    // ANALYSIS COMMANDS
    /// Verify conservation laws
    CheckConservation {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Conservation type (mass, energy, species)
        #[arg(long, default_value = "all")]
        conservation_type: String,
    },
    /// Dimensional analysis report
    Units {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Check dimensional consistency
        #[arg(long)]
        check: bool,
    },
    /// Coupling dependency analysis
    CouplingAnalysis {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Analysis depth (shallow, deep)
        #[arg(long, default_value = "shallow")]
        depth: String,
    },
    /// Memory/time analysis
    PerformanceProfile {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Profiling type (memory, time, both)
        #[arg(long, default_value = "both")]
        profile_type: String,
    },
    /// Model difference report
    Compare {
        /// First ESM file
        #[arg(value_name = "FILE1")]
        file1: PathBuf,
        /// Second ESM file
        #[arg(value_name = "FILE2")]
        file2: PathBuf,
        /// Comparison type (semantic, structural, numerical)
        #[arg(long, default_value = "semantic")]
        comparison_type: String,
    },
    /// Expression optimization suggestions
    Optimize {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Optimization type (expression, structure, performance)
        #[arg(long, default_value = "expression")]
        opt_type: String,
    },

    // DEVELOPMENT COMMANDS
    /// Create new ESM project template
    Init {
        /// Project name
        #[arg(value_name = "NAME")]
        name: String,
        /// Template type (minimal, atmospheric, ecosystem, coupling)
        #[arg(long, default_value = "minimal")]
        template: String,
    },
    /// Batch validation for test suites
    ValidateFixtures {
        /// Directory containing ESM files
        #[arg(value_name = "DIRECTORY")]
        directory: PathBuf,
        /// Recursive directory traversal
        #[arg(short, long)]
        recursive: bool,
    },
    /// Performance benchmarking
    Benchmark {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Benchmark type (parse, validate, simulate)
        #[arg(long, default_value = "all")]
        bench_type: String,
        /// Number of iterations
        #[arg(long, default_value = "100")]
        iterations: usize,
    },
    /// JSON schema compliance
    SchemaCheck {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Schema version to check against
        #[arg(long)]
        schema_version: Option<String>,
    },
    /// Test load/save fidelity
    RoundTrip {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Number of round trips
        #[arg(long, default_value = "1")]
        rounds: usize,
    },
    /// REPL for expression evaluation
    Interactive {
        /// Load ESM file into REPL context
        #[arg(value_name = "FILE")]
        file: Option<PathBuf>,
    },
}

#[cfg(feature = "cli")]
fn check_mass_conservation(esm_file: &esm_format::EsmFile) {
    println!("Mass Conservation Analysis:");

    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            println!("  Reaction System: {}", rs_id);

            let mut mass_balanced = true;
            let mut mass_issues = Vec::new();

            for (i, reaction) in rs.reactions.iter().enumerate() {
                // Check if mass is conserved in each reaction
                let mut substrate_mass = 0.0;
                let mut product_mass = 0.0;

                // For simplicity, assume all species have unit atomic mass
                // In a real implementation, this would use actual atomic masses
                for substrate in &reaction.substrates {
                    substrate_mass += substrate.coefficient.unwrap_or(1.0);
                }

                for product in &reaction.products {
                    product_mass += product.coefficient.unwrap_or(1.0);
                }

                if (substrate_mass - product_mass).abs() > 1e-6 {
                    mass_balanced = false;
                    mass_issues.push(format!(
                        "Reaction {}: mass imbalance ({:.3} -> {:.3})",
                        i + 1, substrate_mass, product_mass
                    ));
                } else {
                    println!("    Reaction {}: ✓ mass conserved", i + 1);
                }
            }

            if mass_balanced {
                println!("    ✓ All reactions are mass-balanced");
            } else {
                println!("    ⚠ Mass conservation issues found:");
                for issue in &mass_issues {
                    println!("      {}", issue);
                }
            }
        }
    } else {
        println!("  No reaction systems found - mass conservation check not applicable");
    }
}

#[cfg(feature = "cli")]
fn check_energy_conservation(esm_file: &esm_format::EsmFile) {
    println!("Energy Conservation Analysis:");

    // Check for energy-related variables and equations
    let mut energy_vars = Vec::new();
    let mut energy_equations = Vec::new();

    if let Some(ref models) = esm_file.models {
        for (model_id, model) in models {
            println!("  Model: {}", model_id);

            // Look for energy-related variables
            for (var_name, var) in &model.variables {
                if var_name.to_lowercase().contains("energy") ||
                   var_name.to_lowercase().contains("temperature") ||
                   var_name.to_lowercase().contains("heat") {
                    energy_vars.push((model_id, var_name));
                }
            }

            // Look for energy-related equations
            for (i, equation) in model.equations.iter().enumerate() {
                if contains_energy_terms(&equation.lhs) || contains_energy_terms(&equation.rhs) {
                    energy_equations.push((model_id, i + 1));
                }
            }
        }
    }

    if energy_vars.is_empty() {
        println!("  No energy variables detected");
    } else {
        println!("  Energy variables found:");
        for (model_id, var_name) in energy_vars {
            println!("    {}.{}", model_id, var_name);
        }
    }

    if energy_equations.is_empty() {
        println!("  No energy equations detected");
    } else {
        println!("  Energy equations found:");
        for (model_id, eq_num) in energy_equations {
            println!("    {}: equation {}", model_id, eq_num);
        }
    }

    // Note: A full energy conservation check would require:
    // 1. Identifying all energy sources and sinks
    // 2. Checking that d(total_energy)/dt = energy_input - energy_output
    // 3. Verifying thermodynamic consistency
    println!("  Note: Full energy conservation analysis requires domain-specific knowledge");
}

#[cfg(feature = "cli")]
fn check_species_conservation(esm_file: &esm_format::EsmFile) {
    println!("Species Conservation Analysis:");

    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            println!("  Reaction System: {}", rs_id);

            // Check species mass balance for each reaction
            for (i, reaction) in rs.reactions.iter().enumerate() {
                let mut atom_balance = std::collections::HashMap::new();

                // For each substrate, add atoms consumed
                for substrate in &reaction.substrates {
                    // Simplified: assume species name indicates element
                    // Real implementation would parse chemical formulas
                    let coeff = substrate.coefficient.unwrap_or(1.0);
                    *atom_balance.entry(&substrate.species).or_insert(0.0) -= coeff;
                }

                // For each product, add atoms produced
                for product in &reaction.products {
                    let coeff = product.coefficient.unwrap_or(1.0);
                    *atom_balance.entry(&product.species).or_insert(0.0) += coeff;
                }

                // Check if atom counts balance
                let mut balanced = true;
                for (species, balance) in &atom_balance {
                    if balance.abs() > 1e-6 {
                        balanced = false;
                        break;
                    }
                }

                if balanced {
                    println!("    Reaction {}: ✓ species conserved", i + 1);
                } else {
                    println!("    Reaction {}: ⚠ species imbalance", i + 1);
                    for (species, balance) in &atom_balance {
                        if balance.abs() > 1e-6 {
                            println!("      {} imbalance: {:.3}", species, balance);
                        }
                    }
                }
            }
        }
    } else {
        println!("  No reaction systems found - species conservation check not applicable");
    }
}

#[cfg(feature = "cli")]
fn analyze_model_units(esm_file: &esm_format::EsmFile) {
    if let Some(ref models) = esm_file.models {
        for (model_id, model) in models {
            println!("Model: {}", model_id);

            // Analyze variable units
            let mut unit_count = 0;
            for (var_name, var) in &model.variables {
                if let Some(ref units) = var.units {
                    println!("  Variable {}: {} [{}]", var_name, var_name, units);
                    unit_count += 1;
                } else {
                    println!("  Variable {}: {} [no units specified]", var_name, var_name);
                }
            }

            println!("  {} out of {} variables have units specified",
                unit_count, model.variables.len());

            // Check for dimensional consistency in equations
            for (i, equation) in model.equations.iter().enumerate() {
                println!("  Equation {}: dimensional analysis needed", i + 1);
                // Note: Full dimensional analysis would require evaluating expression units
            }
        }
    }
}

#[cfg(feature = "cli")]
fn analyze_reaction_system_units(esm_file: &esm_format::EsmFile) {
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            println!("Reaction System: {}", rs_id);

            // Analyze species units
            let mut species_with_units = 0;
            for species in &rs.species {
                if let Some(ref units) = species.units {
                    println!("  Species {}: [{}]", species.name, units);
                    species_with_units += 1;
                } else {
                    println!("  Species {}: [no units]", species.name);
                }
            }

            println!("  {} out of {} species have units specified",
                species_with_units, rs.species.len());

            // Check rate expression units
            for (i, reaction) in rs.reactions.iter().enumerate() {
                println!("  Reaction {} rate: dimensional analysis needed", i + 1);
                // Rate expressions should have units consistent with d[species]/dt
            }
        }
    }
}

#[cfg(feature = "cli")]
fn generate_julia_code(esm_file: &esm_format::EsmFile) -> String {
    let mut code = String::new();

    code.push_str("# Generated Julia code from ESM file\n");
    code.push_str("# WARNING: This is a basic code generation - review before use\n\n");
    code.push_str("using DifferentialEquations, ModelingToolkit\n\n");

    if let Some(ref name) = esm_file.metadata.name {
        code.push_str(&format!("# Model: {}\n", name));
    }
    if let Some(ref description) = esm_file.metadata.description {
        code.push_str(&format!("# {}\n", description));
    }
    code.push('\n');

    // Generate variables and equations for each model
    if let Some(ref models) = esm_file.models {
        for (model_id, model) in models {
            code.push_str(&format!("# Model: {}\n", model_id));
            code.push_str(&format!("function {}!(du, u, p, t)\n", model_id));

            // Variable mapping
            for (i, (var_name, _var)) in model.variables.iter().enumerate() {
                code.push_str(&format!("    {} = u[{}]  # {}\n", var_name, i + 1, var_name));
            }
            code.push('\n');

            // Equations
            for (i, equation) in model.equations.iter().enumerate() {
                let lhs = expr_to_julia(&equation.lhs);
                let rhs = expr_to_julia(&equation.rhs);

                // Check if it's a derivative equation
                if let esm_format::Expr::Operator(node) = &equation.lhs {
                    if node.op == "d" && node.args.len() >= 1 {
                        if let esm_format::Expr::Variable(var_name) = &node.args[0] {
                            // Find variable index
                            if let Some(var_idx) = model.variables.keys().position(|v| v == var_name) {
                                code.push_str(&format!("    du[{}] = {}  # d{}/dt\n", var_idx + 1, rhs, var_name));
                            } else {
                                code.push_str(&format!("    # Unknown variable in derivative: d{}/dt = {}\n", var_name, rhs));
                            }
                        }
                    } else {
                        code.push_str(&format!("    # Algebraic equation {}: {} = {}\n", i + 1, lhs, rhs));
                    }
                } else {
                    code.push_str(&format!("    # Algebraic equation {}: {} = {}\n", i + 1, lhs, rhs));
                }
            }

            code.push_str("end\n\n");

            // Initial conditions
            if !model.variables.is_empty() {
                code.push_str(&format!("# Initial conditions for {}\n", model_id));
                code.push_str("u0 = [\n");
                for (var_name, var) in &model.variables {
                    let init_val = var.default.unwrap_or(0.0);
                    code.push_str(&format!("    {},  # {}\n", init_val, var_name));
                }
                code.push_str("]\n\n");
            }
        }
    }

    // Generate reaction system code
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            code.push_str(&format!("# Reaction System: {}\n", rs_id));
            code.push_str(&format!("function {}!(du, u, p, t)\n", rs_id));

            // Species mapping
            for (i, species) in rs.species.iter().enumerate() {
                code.push_str(&format!("    {} = u[{}]  # {}\n", species.name, i + 1, species.name));
            }
            code.push('\n');

            // Reaction rates
            for (i, reaction) in rs.reactions.iter().enumerate() {
                let rate = expr_to_julia(&reaction.rate);
                code.push_str(&format!("    rate_{} = {}\n", i + 1, rate));
            }
            code.push('\n');

            // Species rate equations
            for (i, species) in rs.species.iter().enumerate() {
                code.push_str(&format!("    du[{}] = 0.0  # d[{}]/dt\n", i + 1, species.name));

                for (j, reaction) in rs.reactions.iter().enumerate() {
                    // Check if species is a substrate
                    for substrate in &reaction.substrates {
                        if substrate.species == species.name {
                            let coeff = substrate.coefficient.unwrap_or(1.0);
                            code.push_str(&format!("    du[{}] -= {} * rate_{}  # substrate\n", i + 1, coeff, j + 1));
                        }
                    }

                    // Check if species is a product
                    for product in &reaction.products {
                        if product.species == species.name {
                            let coeff = product.coefficient.unwrap_or(1.0);
                            code.push_str(&format!("    du[{}] += {} * rate_{}  # product\n", i + 1, coeff, j + 1));
                        }
                    }
                }
            }

            code.push_str("end\n\n");
        }
    }

    // Basic solver setup
    code.push_str("# Example solver setup\n");
    code.push_str("# tspan = (0.0, 10.0)\n");
    code.push_str("# prob = ODEProblem(model_function!, u0, tspan)\n");
    code.push_str("# sol = solve(prob)\n");

    code
}

#[cfg(feature = "cli")]
fn generate_python_code(esm_file: &esm_format::EsmFile) -> String {
    let mut code = String::new();

    code.push_str("# Generated Python code from ESM file\n");
    code.push_str("# WARNING: This is a basic code generation - review before use\n\n");
    code.push_str("import numpy as np\n");
    code.push_str("from scipy.integrate import solve_ivp\n");
    code.push_str("import matplotlib.pyplot as plt\n\n");

    if let Some(ref name) = esm_file.metadata.name {
        code.push_str(&format!("# Model: {}\n", name));
    }
    if let Some(ref description) = esm_file.metadata.description {
        code.push_str(&format!("# {}\n", description));
    }
    code.push('\n');

    // Generate functions for each model
    if let Some(ref models) = esm_file.models {
        for (model_id, model) in models {
            code.push_str(&format!("def {}(t, y):\n", model_id));
            code.push_str("    \"\"\"\n");
            code.push_str(&format!("    Model: {}\n", model.name.as_deref().unwrap_or("Unnamed")));
            code.push_str("    \"\"\"\n");

            // Variable unpacking
            for (i, (var_name, _var)) in model.variables.iter().enumerate() {
                code.push_str(&format!("    {} = y[{}]  # {}\n", var_name, i, var_name));
            }
            code.push('\n');

            code.push_str(&format!("    dydt = np.zeros({})\n", model.variables.len()));
            code.push('\n');

            // Equations
            for (i, equation) in model.equations.iter().enumerate() {
                let lhs = expr_to_python(&equation.lhs);
                let rhs = expr_to_python(&equation.rhs);

                // Check if it's a derivative equation
                if let esm_format::Expr::Operator(node) = &equation.lhs {
                    if node.op == "d" && node.args.len() >= 1 {
                        if let esm_format::Expr::Variable(var_name) = &node.args[0] {
                            // Find variable index
                            if let Some(var_idx) = model.variables.keys().position(|v| v == var_name) {
                                code.push_str(&format!("    dydt[{}] = {}  # d{}/dt\n", var_idx, rhs, var_name));
                            } else {
                                code.push_str(&format!("    # Unknown variable: d{}/dt = {}\n", var_name, rhs));
                            }
                        }
                    } else {
                        code.push_str(&format!("    # Algebraic equation {}: {} = {}\n", i + 1, lhs, rhs));
                    }
                } else {
                    code.push_str(&format!("    # Algebraic equation {}: {} = {}\n", i + 1, lhs, rhs));
                }
            }

            code.push_str("\n    return dydt\n\n");

            // Initial conditions
            if !model.variables.is_empty() {
                code.push_str(&format!("# Initial conditions for {}\n", model_id));
                code.push_str(&format!("{}_y0 = np.array([\n", model_id));
                for (var_name, var) in &model.variables {
                    let init_val = var.default.unwrap_or(0.0);
                    code.push_str(&format!("    {},  # {}\n", init_val, var_name));
                }
                code.push_str("])\n\n");
            }
        }
    }

    // Generate reaction system functions
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            code.push_str(&format!("def {}(t, y):\n", rs_id));
            code.push_str("    \"\"\"\n");
            code.push_str(&format!("    Reaction System: {}\n", rs.name.as_deref().unwrap_or("Unnamed")));
            code.push_str("    \"\"\"\n");

            // Species unpacking
            for (i, species) in rs.species.iter().enumerate() {
                code.push_str(&format!("    {} = y[{}]  # {}\n", species.name, i, species.name));
            }
            code.push('\n');

            // Reaction rates
            for (i, reaction) in rs.reactions.iter().enumerate() {
                let rate = expr_to_python(&reaction.rate);
                code.push_str(&format!("    rate_{} = {}\n", i + 1, rate));
            }
            code.push('\n');

            code.push_str(&format!("    dydt = np.zeros({})\n", rs.species.len()));

            // Species rate equations
            for (i, species) in rs.species.iter().enumerate() {
                code.push_str(&format!("    # d[{}]/dt\n", species.name));

                for (j, reaction) in rs.reactions.iter().enumerate() {
                    // Check if species is a substrate
                    for substrate in &reaction.substrates {
                        if substrate.species == species.name {
                            let coeff = substrate.coefficient.unwrap_or(1.0);
                            code.push_str(&format!("    dydt[{}] -= {} * rate_{}\n", i, coeff, j + 1));
                        }
                    }

                    // Check if species is a product
                    for product in &reaction.products {
                        if product.species == species.name {
                            let coeff = product.coefficient.unwrap_or(1.0);
                            code.push_str(&format!("    dydt[{}] += {} * rate_{}\n", i, coeff, j + 1));
                        }
                    }
                }
            }

            code.push_str("\n    return dydt\n\n");
        }
    }

    // Example solver setup
    code.push_str("# Example solver setup\n");
    code.push_str("if __name__ == '__main__':\n");
    code.push_str("    # Time span\n");
    code.push_str("    t_span = (0, 10)\n");
    code.push_str("    t_eval = np.linspace(0, 10, 100)\n\n");
    code.push_str("    # Solve ODE (uncomment and modify as needed)\n");
    code.push_str("    # sol = solve_ivp(model_function, t_span, y0, t_eval=t_eval)\n");
    code.push_str("    # plt.plot(sol.t, sol.y.T)\n");
    code.push_str("    # plt.show()\n");

    code
}

#[cfg(feature = "cli")]
fn expr_to_julia(expr: &esm_format::Expr) -> String {
    match expr {
        esm_format::Expr::Number(n) => n.to_string(),
        esm_format::Expr::Variable(name) => name.clone(),
        esm_format::Expr::Operator(node) => {
            match node.op.as_str() {
                "+" | "-" | "*" | "/" => {
                    if node.args.len() >= 2 {
                        let args: Vec<String> = node.args.iter().map(expr_to_julia).collect();
                        format!("({} {} {})", args[0], node.op, args[1])
                    } else {
                        format!("{}({})", node.op, node.args.iter().map(expr_to_julia).collect::<Vec<_>>().join(", "))
                    }
                }
                "^" | "**" => {
                    if node.args.len() >= 2 {
                        let base = expr_to_julia(&node.args[0]);
                        let exp = expr_to_julia(&node.args[1]);
                        format!("{}^{}", base, exp)
                    } else {
                        "1.0".to_string()
                    }
                }
                "exp" | "log" | "sin" | "cos" | "tan" => {
                    if !node.args.is_empty() {
                        let arg = expr_to_julia(&node.args[0]);
                        format!("{}({})", node.op, arg)
                    } else {
                        node.op.clone()
                    }
                }
                "d" => {
                    // Derivative - just return the variable name for now
                    if !node.args.is_empty() {
                        expr_to_julia(&node.args[0])
                    } else {
                        "unknown_derivative".to_string()
                    }
                }
                _ => {
                    let args: Vec<String> = node.args.iter().map(expr_to_julia).collect();
                    format!("{}({})", node.op, args.join(", "))
                }
            }
        }
    }
}

#[cfg(feature = "cli")]
fn expr_to_python(expr: &esm_format::Expr) -> String {
    match expr {
        esm_format::Expr::Number(n) => n.to_string(),
        esm_format::Expr::Variable(name) => name.clone(),
        esm_format::Expr::Operator(node) => {
            match node.op.as_str() {
                "+" | "-" | "*" | "/" => {
                    if node.args.len() >= 2 {
                        let args: Vec<String> = node.args.iter().map(expr_to_python).collect();
                        format!("({} {} {})", args[0], node.op, args[1])
                    } else {
                        format!("{}({})", node.op, node.args.iter().map(expr_to_python).collect::<Vec<_>>().join(", "))
                    }
                }
                "^" | "**" => {
                    if node.args.len() >= 2 {
                        let base = expr_to_python(&node.args[0]);
                        let exp = expr_to_python(&node.args[1]);
                        format!("{}**{}", base, exp)
                    } else {
                        "1.0".to_string()
                    }
                }
                "exp" => {
                    if !node.args.is_empty() {
                        let arg = expr_to_python(&node.args[0]);
                        format!("np.exp({})", arg)
                    } else {
                        "np.exp".to_string()
                    }
                }
                "log" => {
                    if !node.args.is_empty() {
                        let arg = expr_to_python(&node.args[0]);
                        format!("np.log({})", arg)
                    } else {
                        "np.log".to_string()
                    }
                }
                "sin" | "cos" | "tan" => {
                    if !node.args.is_empty() {
                        let arg = expr_to_python(&node.args[0]);
                        format!("np.{}({})", node.op, arg)
                    } else {
                        format!("np.{}", node.op)
                    }
                }
                "d" => {
                    // Derivative - just return the variable name for now
                    if !node.args.is_empty() {
                        expr_to_python(&node.args[0])
                    } else {
                        "unknown_derivative".to_string()
                    }
                }
                _ => {
                    let args: Vec<String> = node.args.iter().map(expr_to_python).collect();
                    format!("{}({})", node.op, args.join(", "))
                }
            }
        }
    }
}

#[cfg(feature = "cli")]
fn collect_unit_types(esm_file: &esm_format::EsmFile) -> Vec<String> {
    let mut units = std::collections::HashSet::new();

    if let Some(ref models) = esm_file.models {
        for (_, model) in models {
            for (_, var) in &model.variables {
                if let Some(ref unit_str) = var.units {
                    units.insert(unit_str.clone());
                }
            }
        }
    }

    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (_, rs) in reaction_systems {
            for species in &rs.species {
                if let Some(ref unit_str) = species.units {
                    units.insert(unit_str.clone());
                }
            }
        }
    }

    let mut unit_list: Vec<String> = units.into_iter().collect();
    unit_list.sort();
    unit_list
}

#[cfg(feature = "cli")]
fn contains_energy_terms(expr: &esm_format::Expr) -> bool {
    match expr {
        esm_format::Expr::Variable(name) => {
            name.to_lowercase().contains("energy") ||
            name.to_lowercase().contains("temperature") ||
            name.to_lowercase().contains("heat") ||
            name.to_lowercase().contains("enthalpy")
        }
        esm_format::Expr::Operator(node) => {
            node.args.iter().any(contains_energy_terms)
        }
        esm_format::Expr::Number(_) => false,
    }
}

#[cfg(feature = "cli")]
fn expression_depth(expr: &esm_format::Expr) -> usize {
    match expr {
        esm_format::Expr::Number(_) | esm_format::Expr::Variable(_) => 1,
        esm_format::Expr::Operator(node) => {
            1 + node.args.iter().map(expression_depth).max().unwrap_or(0)
        }
    }
}

#[cfg(feature = "cli")]
fn count_expression_nodes(expr: &esm_format::Expr) -> usize {
    match expr {
        esm_format::Expr::Number(_) | esm_format::Expr::Variable(_) => 1,
        esm_format::Expr::Operator(node) => {
            1 + node.args.iter().map(count_expression_nodes).sum::<usize>()
        }
    }
}

#[cfg(feature = "cli")]
fn analyze_expression_optimization(esm_file: &esm_format::EsmFile) {
    println!("\n=== EXPRESSION OPTIMIZATION ANALYSIS ===");

    let mut suggestions: Vec<String> = Vec::new();
    let mut complex_expressions = 0;
    let mut redundant_operations = 0;

    // Analyze model expressions
    if let Some(ref models) = esm_file.models {
        for (model_id, model) in models {
            println!("Model: {}", model_id);

            for (i, equation) in model.equations.iter().enumerate() {
                // Check expression complexity
                let lhs_depth = expression_depth(&equation.lhs);
                let rhs_depth = expression_depth(&equation.rhs);
                let max_depth = lhs_depth.max(rhs_depth);

                if max_depth > 5 {
                    complex_expressions += 1;
                    suggestions.push(format!("  Eq {}: High complexity (depth {}), consider factoring", i + 1, max_depth));
                }

                // Check for redundant operations
                if contains_redundant_operations(&equation.rhs) {
                    redundant_operations += 1;
                    suggestions.push(format!("  Eq {}: Contains redundant operations", i + 1));
                }

                // Check for common subexpressions
                if contains_common_subexpressions(&equation.lhs, &equation.rhs) {
                    suggestions.push(format!("  Eq {}: Common subexpressions found", i + 1));
                }
            }
        }
    }

    // Analyze reaction expressions
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            println!("Reaction System: {}", rs_id);

            for (i, reaction) in rs.reactions.iter().enumerate() {
                let rate_depth = expression_depth(&reaction.rate);

                if rate_depth > 4 {
                    complex_expressions += 1;
                    suggestions.push(format!("  Reaction {}: Complex rate expression (depth {})", i + 1, rate_depth));
                }

                if contains_redundant_operations(&reaction.rate) {
                    redundant_operations += 1;
                    suggestions.push(format!("  Reaction {}: Rate contains redundant operations", i + 1));
                }
            }
        }
    }

    // Summary
    println!("\n=== OPTIMIZATION SUGGESTIONS ===");
    if suggestions.is_empty() {
        println!("✓ No obvious expression optimizations needed");
    } else {
        println!("Found {} complex expressions, {} redundant operations", complex_expressions, redundant_operations);
        for suggestion in suggestions {
            println!("{}", suggestion);
        }
    }

    // General recommendations
    println!("\n=== GENERAL RECOMMENDATIONS ===");
    println!("- Factor out common subexpressions into intermediate variables");
    println!("- Use pre-computed constants where possible");
    println!("- Consider using operator precedence to reduce parentheses");
}

#[cfg(feature = "cli")]
fn analyze_structure_optimization(esm_file: &esm_format::EsmFile) {
    println!("\n=== STRUCTURE OPTIMIZATION ANALYSIS ===");

    // Component count analysis
    let model_count = esm_file.models.as_ref().map(|m| m.len()).unwrap_or(0);
    let rs_count = esm_file.reaction_systems.as_ref().map(|rs| rs.len()).unwrap_or(0);
    let coupling_count = esm_file.coupling.as_ref().map(|c| c.len()).unwrap_or(0);

    println!("Structure: {} models, {} reaction systems, {} coupling rules",
        model_count, rs_count, coupling_count);

    let mut suggestions: Vec<String> = Vec::new();

    // Analyze coupling complexity
    if coupling_count > 10 {
        suggestions.push("High coupling complexity - consider grouping related couplings".to_string());
    }

    // Analyze model sizes
    if let Some(ref models) = esm_file.models {
        for (model_id, model) in models {
            let var_count = model.variables.len();
            let eq_count = model.equations.len();

            if var_count > 50 {
                suggestions.push(format!("Model '{}' has {} variables - consider splitting into smaller components", model_id, var_count));
            }

            if eq_count > 30 {
                suggestions.push(format!("Model '{}' has {} equations - consider modular decomposition", model_id, eq_count));
            }

            // Check for unused variables
            let mut used_vars = std::collections::HashSet::new();
            for equation in &model.equations {
                collect_variables(&equation.lhs, &mut used_vars);
                collect_variables(&equation.rhs, &mut used_vars);
            }

            let unused_count = model.variables.keys().filter(|&v| !used_vars.contains(v)).count();
            if unused_count > 0 {
                suggestions.push(format!("Model '{}' has {} potentially unused variables", model_id, unused_count));
            }
        }
    }

    // Analyze reaction system sizes
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            if rs.species.len() > 100 {
                suggestions.push(format!("Reaction system '{}' has {} species - consider chemical family grouping", rs_id, rs.species.len()));
            }

            if rs.reactions.len() > 200 {
                suggestions.push(format!("Reaction system '{}' has {} reactions - consider mechanism reduction", rs_id, rs.reactions.len()));
            }
        }
    }

    // Output recommendations
    if suggestions.is_empty() {
        println!("✓ Structure appears well-organized");
    } else {
        println!("\n=== OPTIMIZATION SUGGESTIONS ===");
        for suggestion in suggestions {
            println!("  - {}", suggestion);
        }
    }

    println!("\n=== GENERAL RECOMMENDATIONS ===");
    println!("- Keep models focused on single domains/processes");
    println!("- Use hierarchical naming for related variables");
    println!("- Group related coupling operations together");
}

#[cfg(feature = "cli")]
fn analyze_performance_optimization(esm_file: &esm_format::EsmFile) {
    println!("\n=== PERFORMANCE OPTIMIZATION ANALYSIS ===");

    // Computational complexity estimation
    let mut total_ops = 0;
    let mut expensive_ops = 0;

    if let Some(ref models) = esm_file.models {
        for (model_id, model) in models {
            println!("Model: {}", model_id);
            let mut model_ops = 0;

            for equation in &model.equations {
                let lhs_ops = count_operations(&equation.lhs);
                let rhs_ops = count_operations(&equation.rhs);
                model_ops += lhs_ops + rhs_ops;

                // Check for expensive operations
                if contains_expensive_operations(&equation.rhs) {
                    expensive_ops += 1;
                }
            }

            total_ops += model_ops;
            println!("  Operations per timestep: ~{}", model_ops);
        }
    }

    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (rs_id, rs) in reaction_systems {
            println!("Reaction System: {}", rs_id);
            let mut rs_ops = 0;

            for reaction in &rs.reactions {
                let rate_ops = count_operations(&reaction.rate);
                rs_ops += rate_ops;

                if contains_expensive_operations(&reaction.rate) {
                    expensive_ops += 1;
                }
            }

            // Add stoichiometric operations
            rs_ops += rs.reactions.len() * rs.species.len(); // Approximate stoichiometric matrix operations

            total_ops += rs_ops;
            println!("  Operations per timestep: ~{}", rs_ops);
        }
    }

    println!("\nTotal operations per timestep: ~{}", total_ops);
    println!("Expensive operations found: {}", expensive_ops);

    // Performance suggestions
    println!("\n=== OPTIMIZATION SUGGESTIONS ===");
    if total_ops > 10000 {
        println!("  - High computational load - consider numerical method optimization");
    }
    if expensive_ops > 5 {
        println!("  - {} expensive operations found - consider lookup tables or approximations", expensive_ops);
    }

    // Memory usage estimation
    let var_count = esm_file.models.as_ref().map(|models| {
        models.values().map(|m| m.variables.len()).sum::<usize>()
    }).unwrap_or(0);

    let species_count = esm_file.reaction_systems.as_ref().map(|rs_map| {
        rs_map.values().map(|rs| rs.species.len()).sum::<usize>()
    }).unwrap_or(0);

    let total_state_vars = var_count + species_count;
    println!("State variables: {} (estimated memory: {} KB)",
        total_state_vars, total_state_vars * 8 / 1024); // 8 bytes per double

    println!("\n=== GENERAL RECOMMENDATIONS ===");
    println!("- Use fast numerical integrators for stiff systems");
    println!("- Cache frequently computed expressions");
    println!("- Consider sparse matrix representations for large systems");
    println!("- Profile actual runtime to identify bottlenecks");
}

#[cfg(feature = "cli")]
fn contains_redundant_operations(expr: &esm_format::Expr) -> bool {
    match expr {
        esm_format::Expr::Operator(node) => {
            // Check for operations like x + 0, x * 1, x^1, etc.
            match node.op.as_str() {
                "+" | "-" => {
                    node.args.iter().any(|arg| {
                        if let esm_format::Expr::Number(n) = arg {
                            *n == 0.0
                        } else {
                            false
                        }
                    })
                },
                "*" | "/" => {
                    node.args.iter().any(|arg| {
                        if let esm_format::Expr::Number(n) = arg {
                            *n == 1.0
                        } else {
                            false
                        }
                    })
                },
                "^" => {
                    if node.args.len() >= 2 {
                        if let esm_format::Expr::Number(n) = &node.args[1] {
                            *n == 1.0
                        } else {
                            false
                        }
                    } else {
                        false
                    }
                },
                _ => node.args.iter().any(contains_redundant_operations)
            }
        }
        _ => false
    }
}

#[cfg(feature = "cli")]
fn contains_common_subexpressions(lhs: &esm_format::Expr, rhs: &esm_format::Expr) -> bool {
    let mut lhs_subexprs = Vec::new();
    let mut rhs_subexprs = Vec::new();

    collect_subexpressions(lhs, &mut lhs_subexprs);
    collect_subexpressions(rhs, &mut rhs_subexprs);

    // Simple heuristic: check if any complex subexpressions appear in both sides
    lhs_subexprs.iter().any(|lhs_expr| {
        if expression_depth(lhs_expr) > 2 {
            rhs_subexprs.iter().any(|rhs_expr| expressions_equal(lhs_expr, rhs_expr))
        } else {
            false
        }
    })
}

#[cfg(feature = "cli")]
fn collect_subexpressions(expr: &esm_format::Expr, subexprs: &mut Vec<esm_format::Expr>) {
    subexprs.push(expr.clone());
    if let esm_format::Expr::Operator(node) = expr {
        for arg in &node.args {
            collect_subexpressions(arg, subexprs);
        }
    }
}

#[cfg(feature = "cli")]
fn expressions_equal(expr1: &esm_format::Expr, expr2: &esm_format::Expr) -> bool {
    // Simple structural equality check
    match (expr1, expr2) {
        (esm_format::Expr::Number(n1), esm_format::Expr::Number(n2)) => (n1 - n2).abs() < 1e-10,
        (esm_format::Expr::Variable(v1), esm_format::Expr::Variable(v2)) => v1 == v2,
        (esm_format::Expr::Operator(op1), esm_format::Expr::Operator(op2)) => {
            op1.op == op2.op && op1.args.len() == op2.args.len() &&
            op1.args.iter().zip(op2.args.iter()).all(|(a1, a2)| expressions_equal(a1, a2))
        },
        _ => false
    }
}

#[cfg(feature = "cli")]
fn collect_variables(expr: &esm_format::Expr, vars: &mut std::collections::HashSet<String>) {
    match expr {
        esm_format::Expr::Variable(name) => {
            vars.insert(name.clone());
        }
        esm_format::Expr::Operator(node) => {
            for arg in &node.args {
                collect_variables(arg, vars);
            }
        }
        esm_format::Expr::Number(_) => {}
    }
}

#[cfg(feature = "cli")]
fn count_operations(expr: &esm_format::Expr) -> usize {
    match expr {
        esm_format::Expr::Number(_) | esm_format::Expr::Variable(_) => 0,
        esm_format::Expr::Operator(node) => {
            1 + node.args.iter().map(count_operations).sum::<usize>()
        }
    }
}

#[cfg(feature = "cli")]
fn contains_expensive_operations(expr: &esm_format::Expr) -> bool {
    match expr {
        esm_format::Expr::Operator(node) => {
            match node.op.as_str() {
                "exp" | "log" | "sin" | "cos" | "tan" | "sqrt" | "^" => true,
                _ => node.args.iter().any(contains_expensive_operations)
            }
        }
        _ => false
    }
}

#[cfg(feature = "cli")]
fn perform_structural_comparison(esm_file1: &esm_format::EsmFile, esm_file2: &esm_format::EsmFile) {
    println!("\n=== STRUCTURAL COMPARISON ===");

    let mut differences = Vec::new();

    // Compare basic structure
    if esm_file1.esm != esm_file2.esm {
        differences.push(format!("ESM version: {} vs {}", esm_file1.esm, esm_file2.esm));
    }

    // Compare component counts
    let models1_count = esm_file1.models.as_ref().map(|m| m.len()).unwrap_or(0);
    let models2_count = esm_file2.models.as_ref().map(|m| m.len()).unwrap_or(0);
    if models1_count != models2_count {
        differences.push(format!("Model count: {} vs {}", models1_count, models2_count));
    }

    let rs1_count = esm_file1.reaction_systems.as_ref().map(|rs| rs.len()).unwrap_or(0);
    let rs2_count = esm_file2.reaction_systems.as_ref().map(|rs| rs.len()).unwrap_or(0);
    if rs1_count != rs2_count {
        differences.push(format!("Reaction system count: {} vs {}", rs1_count, rs2_count));
    }

    let coupling1_count = esm_file1.coupling.as_ref().map(|c| c.len()).unwrap_or(0);
    let coupling2_count = esm_file2.coupling.as_ref().map(|c| c.len()).unwrap_or(0);
    if coupling1_count != coupling2_count {
        differences.push(format!("Coupling rule count: {} vs {}", coupling1_count, coupling2_count));
    }

    // Compare model structures
    match (&esm_file1.models, &esm_file2.models) {
        (Some(models1), Some(models2)) => {
            let keys1: std::collections::HashSet<_> = models1.keys().collect();
            let keys2: std::collections::HashSet<_> = models2.keys().collect();

            let only_in_1: Vec<_> = keys1.difference(&keys2).collect();
            let only_in_2: Vec<_> = keys2.difference(&keys1).collect();

            if !only_in_1.is_empty() {
                differences.push(format!("Models only in file1: {:?}", only_in_1));
            }
            if !only_in_2.is_empty() {
                differences.push(format!("Models only in file2: {:?}", only_in_2));
            }

            // Compare common models
            for model_id in keys1.intersection(&keys2) {
                let model1 = &models1[*model_id];
                let model2 = &models2[*model_id];

                if model1.variables.len() != model2.variables.len() {
                    differences.push(format!("Model {}: variable count {} vs {}",
                        model_id, model1.variables.len(), model2.variables.len()));
                }

                if model1.equations.len() != model2.equations.len() {
                    differences.push(format!("Model {}: equation count {} vs {}",
                        model_id, model1.equations.len(), model2.equations.len()));
                }

                // Compare variable names
                let vars1: std::collections::HashSet<_> = model1.variables.keys().collect();
                let vars2: std::collections::HashSet<_> = model2.variables.keys().collect();
                if vars1 != vars2 {
                    differences.push(format!("Model {}: different variable sets", model_id));
                }
            }
        }
        (Some(_), None) => differences.push("File1 has models, file2 does not".to_string()),
        (None, Some(_)) => differences.push("File2 has models, file1 does not".to_string()),
        (None, None) => {}
    }

    // Compare reaction system structures
    match (&esm_file1.reaction_systems, &esm_file2.reaction_systems) {
        (Some(rs1), Some(rs2)) => {
            let keys1: std::collections::HashSet<_> = rs1.keys().collect();
            let keys2: std::collections::HashSet<_> = rs2.keys().collect();

            let only_in_1: Vec<_> = keys1.difference(&keys2).collect();
            let only_in_2: Vec<_> = keys2.difference(&keys1).collect();

            if !only_in_1.is_empty() {
                differences.push(format!("Reaction systems only in file1: {:?}", only_in_1));
            }
            if !only_in_2.is_empty() {
                differences.push(format!("Reaction systems only in file2: {:?}", only_in_2));
            }

            // Compare common reaction systems
            for rs_id in keys1.intersection(&keys2) {
                let system1 = &rs1[*rs_id];
                let system2 = &rs2[*rs_id];

                if system1.species.len() != system2.species.len() {
                    differences.push(format!("Reaction system {}: species count {} vs {}",
                        rs_id, system1.species.len(), system2.species.len()));
                }

                if system1.reactions.len() != system2.reactions.len() {
                    differences.push(format!("Reaction system {}: reaction count {} vs {}",
                        rs_id, system1.reactions.len(), system2.reactions.len()));
                }
            }
        }
        (Some(_), None) => differences.push("File1 has reaction systems, file2 does not".to_string()),
        (None, Some(_)) => differences.push("File2 has reaction systems, file1 does not".to_string()),
        (None, None) => {}
    }

    // Output results
    if differences.is_empty() {
        println!("✓ Files have identical structure");
    } else {
        println!("✗ Structural differences found:");
        for diff in differences {
            println!("  - {}", diff);
        }
    }
}

#[cfg(feature = "cli")]
fn perform_numerical_comparison(esm_file1: &esm_format::EsmFile, esm_file2: &esm_format::EsmFile) {
    println!("\n=== NUMERICAL COMPARISON ===");

    let tolerance = 1e-10;
    let mut differences = Vec::new();

    // Compare numerical values in models
    if let (Some(models1), Some(models2)) = (&esm_file1.models, &esm_file2.models) {
        for model_id in models1.keys() {
            if let Some(model2) = models2.get(model_id) {
                let model1 = &models1[model_id];

                // Compare variable default values
                for (var_name, var1) in &model1.variables {
                    if let Some(var2) = model2.variables.get(var_name) {
                        if let (Some(default1), Some(default2)) = (var1.default, var2.default) {
                            if (default1 - default2).abs() > tolerance {
                                differences.push(format!("Model {}, variable {}: default {} vs {}",
                                    model_id, var_name, default1, default2));
                            }
                        }
                    }
                }

                // Compare equation expressions numerically
                if model1.equations.len() == model2.equations.len() {
                    for (i, (eq1, eq2)) in model1.equations.iter().zip(model2.equations.iter()).enumerate() {
                        if !expressions_numerically_equal(&eq1.lhs, &eq2.lhs, tolerance) {
                            differences.push(format!("Model {}, equation {} LHS: numerical difference", model_id, i + 1));
                        }
                        if !expressions_numerically_equal(&eq1.rhs, &eq2.rhs, tolerance) {
                            differences.push(format!("Model {}, equation {} RHS: numerical difference", model_id, i + 1));
                        }
                    }
                }
            }
        }
    }

    // Compare reaction system coefficients
    if let (Some(rs1), Some(rs2)) = (&esm_file1.reaction_systems, &esm_file2.reaction_systems) {
        for rs_id in rs1.keys() {
            if let Some(system2) = rs2.get(rs_id) {
                let system1 = &rs1[rs_id];

                if system1.reactions.len() == system2.reactions.len() {
                    for (i, (reaction1, reaction2)) in system1.reactions.iter().zip(system2.reactions.iter()).enumerate() {
                        // Compare substrate coefficients
                        if reaction1.substrates.len() == reaction2.substrates.len() {
                            for (sub1, sub2) in reaction1.substrates.iter().zip(reaction2.substrates.iter()) {
                                let coeff1 = sub1.coefficient.unwrap_or(1.0);
                                let coeff2 = sub2.coefficient.unwrap_or(1.0);
                                if (coeff1 - coeff2).abs() > tolerance {
                                    differences.push(format!("Reaction system {}, reaction {}: substrate coefficient {} vs {}",
                                        rs_id, i + 1, coeff1, coeff2));
                                }
                            }
                        }

                        // Compare product coefficients
                        if reaction1.products.len() == reaction2.products.len() {
                            for (prod1, prod2) in reaction1.products.iter().zip(reaction2.products.iter()) {
                                let coeff1 = prod1.coefficient.unwrap_or(1.0);
                                let coeff2 = prod2.coefficient.unwrap_or(1.0);
                                if (coeff1 - coeff2).abs() > tolerance {
                                    differences.push(format!("Reaction system {}, reaction {}: product coefficient {} vs {}",
                                        rs_id, i + 1, coeff1, coeff2));
                                }
                            }
                        }

                        // Compare rate expressions
                        if !expressions_numerically_equal(&reaction1.rate, &reaction2.rate, tolerance) {
                            differences.push(format!("Reaction system {}, reaction {}: rate expression numerical difference",
                                rs_id, i + 1));
                        }
                    }
                }
            }
        }
    }

    // Output results
    if differences.is_empty() {
        println!("✓ Files are numerically equivalent (tolerance: {})", tolerance);
    } else {
        println!("✗ Numerical differences found (tolerance: {}):", tolerance);
        for diff in differences {
            println!("  - {}", diff);
        }
    }

    // Summary statistics
    let mut total_numbers1 = 0;
    let mut total_numbers2 = 0;
    count_numerical_values(&esm_file1, &mut total_numbers1);
    count_numerical_values(&esm_file2, &mut total_numbers2);

    println!("\nNumerical values compared: {} vs {}", total_numbers1, total_numbers2);
}

#[cfg(feature = "cli")]
fn expressions_numerically_equal(expr1: &esm_format::Expr, expr2: &esm_format::Expr, tolerance: f64) -> bool {
    match (expr1, expr2) {
        (esm_format::Expr::Number(n1), esm_format::Expr::Number(n2)) => {
            (n1 - n2).abs() <= tolerance
        }
        (esm_format::Expr::Variable(v1), esm_format::Expr::Variable(v2)) => v1 == v2,
        (esm_format::Expr::Operator(op1), esm_format::Expr::Operator(op2)) => {
            op1.op == op2.op && op1.args.len() == op2.args.len() &&
            op1.args.iter().zip(op2.args.iter()).all(|(a1, a2)| expressions_numerically_equal(a1, a2, tolerance))
        }
        _ => false
    }
}

#[cfg(feature = "cli")]
fn count_numerical_values(esm_file: &esm_format::EsmFile, count: &mut usize) {
    if let Some(ref models) = esm_file.models {
        for (_, model) in models {
            // Count variable defaults
            for (_, var) in &model.variables {
                if var.default.is_some() {
                    *count += 1;
                }
            }

            // Count numbers in expressions
            for equation in &model.equations {
                count_numbers_in_expression(&equation.lhs, count);
                count_numbers_in_expression(&equation.rhs, count);
            }
        }
    }

    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        for (_, rs) in reaction_systems {
            for reaction in &rs.reactions {
                // Count coefficients
                for substrate in &reaction.substrates {
                    if substrate.coefficient.is_some() {
                        *count += 1;
                    }
                }
                for product in &reaction.products {
                    if product.coefficient.is_some() {
                        *count += 1;
                    }
                }

                // Count numbers in rate expressions
                count_numbers_in_expression(&reaction.rate, count);
            }
        }
    }
}

#[cfg(feature = "cli")]
fn count_numbers_in_expression(expr: &esm_format::Expr, count: &mut usize) {
    match expr {
        esm_format::Expr::Number(_) => *count += 1,
        esm_format::Expr::Operator(node) => {
            for arg in &node.args {
                count_numbers_in_expression(arg, count);
            }
        }
        esm_format::Expr::Variable(_) => {}
    }
}

#[cfg(feature = "cli")]
fn perform_deep_coupling_analysis(esm_file: &esm_format::EsmFile) {
    println!("\n=== DEEP COUPLING DEPENDENCY ANALYSIS ===");

    let graph = component_graph(&esm_file);
    println!("Analyzing {} components with {} coupling relationships",
        graph.nodes.len(), graph.edges.len());

    // Build dependency maps
    let mut dependencies = std::collections::HashMap::new();
    let mut dependents = std::collections::HashMap::new();

    for edge in &graph.edges {
        dependencies.entry(edge.to.clone()).or_insert_with(Vec::new).push(edge.from.clone());
        dependents.entry(edge.from.clone()).or_insert_with(Vec::new).push(edge.to.clone());
    }

    // Analyze coupling patterns
    analyze_coupling_patterns(&graph);

    // Find strongly connected components (circular dependencies)
    let scc = find_strongly_connected_components(&graph);
    if scc.len() < graph.nodes.len() {
        println!("\n=== CIRCULAR DEPENDENCIES FOUND ===");
        for (i, component) in scc.iter().enumerate() {
            if component.len() > 1 {
                println!("Circular dependency group {}: {:?}", i + 1, component);
            }
        }
    } else {
        println!("\n✓ No circular dependencies found");
    }

    // Analyze coupling strength
    analyze_coupling_strength(&graph, &esm_file);

    // Detect coupling anti-patterns
    detect_coupling_antipatterns(&graph, &esm_file);

    // Generate coupling recommendations
    println!("\n=== COUPLING RECOMMENDATIONS ===");
    if graph.edges.len() > graph.nodes.len() * 2 {
        println!("- High coupling density ({} edges, {} nodes) - consider reducing interdependencies",
            graph.edges.len(), graph.nodes.len());
    }

    // Check for hub components (components with many connections)
    let mut connection_counts = std::collections::HashMap::new();
    for edge in &graph.edges {
        *connection_counts.entry(&edge.from).or_insert(0) += 1;
        *connection_counts.entry(&edge.to).or_insert(0) += 1;
    }

    let max_connections = connection_counts.values().max().unwrap_or(&0);
    if *max_connections > 5 {
        println!("- Hub components detected (max {} connections) - consider architectural refactoring",
            max_connections);
        for (component, count) in &connection_counts {
            if *count > 5 {
                println!("  High connectivity: {} ({} connections)", component, count);
            }
        }
    }

    // Analyze coupling by type
    let mut coupling_types = std::collections::HashMap::new();
    for edge in &graph.edges {
        *coupling_types.entry(&edge.coupling_type).or_insert(0) += 1;
    }

    println!("\n=== COUPLING TYPE ANALYSIS ===");
    for (coupling_type, count) in coupling_types {
        println!("  {}: {} occurrences", coupling_type, count);
    }

    // Calculate coupling metrics
    let coupling_density = graph.edges.len() as f64 / (graph.nodes.len() as f64 * (graph.nodes.len() - 1) as f64);
    println!("\nCoupling density: {:.3} (0=no coupling, 1=fully coupled)", coupling_density);

    if coupling_density > 0.5 {
        println!("⚠ Very high coupling density - system may be difficult to maintain");
    } else if coupling_density > 0.2 {
        println!("- Moderate coupling density - monitor for growth");
    } else {
        println!("✓ Low coupling density - good architectural separation");
    }
}

#[cfg(feature = "cli")]
fn analyze_coupling_patterns(graph: &esm_format::graph::ComponentGraph) {
    println!("\n=== COUPLING PATTERNS ===");

    // Pattern 1: Fan-out (one component affects many others)
    let mut out_degree = std::collections::HashMap::new();
    let mut in_degree = std::collections::HashMap::new();

    for edge in &graph.edges {
        *out_degree.entry(&edge.from).or_insert(0) += 1;
        *in_degree.entry(&edge.to).or_insert(0) += 1;
    }

    let mut fan_out_components = Vec::new();
    let mut fan_in_components = Vec::new();

    for (component, degree) in &out_degree {
        if *degree > 3 {
            fan_out_components.push((component, degree));
        }
    }

    for (component, degree) in &in_degree {
        if *degree > 3 {
            fan_in_components.push((component, degree));
        }
    }

    if !fan_out_components.is_empty() {
        println!("Fan-out patterns (components affecting many others):");
        for (component, degree) in fan_out_components {
            println!("  {} -> {} components", component, degree);
        }
    }

    if !fan_in_components.is_empty() {
        println!("Fan-in patterns (components affected by many others):");
        for (component, degree) in fan_in_components {
            println!("  {} <- {} components", component, degree);
        }
    }

    // Pattern 2: Chains (A->B->C->D)
    let chain_length = find_longest_dependency_chain(graph);
    if chain_length > 4 {
        println!("Long dependency chain detected: {} components", chain_length);
        println!("  Consider reducing chain length for better parallelization");
    }
}

#[cfg(feature = "cli")]
fn find_strongly_connected_components(graph: &esm_format::graph::ComponentGraph) -> Vec<Vec<String>> {
    // Simple SCC detection using DFS
    let mut visited = std::collections::HashSet::new();
    let mut components = Vec::new();

    for node in &graph.nodes {
        if !visited.contains(&node.id) {
            let mut component = Vec::new();
            dfs_scc(&graph, &node.id, &mut visited, &mut component);
            if !component.is_empty() {
                components.push(component);
            }
        }
    }

    components
}

#[cfg(feature = "cli")]
fn dfs_scc(graph: &esm_format::graph::ComponentGraph, node_id: &str, visited: &mut std::collections::HashSet<String>, component: &mut Vec<String>) {
    visited.insert(node_id.to_string());
    component.push(node_id.to_string());

    // Find all nodes reachable from this node
    for edge in &graph.edges {
        if edge.from == node_id && !visited.contains(&edge.to) {
            dfs_scc(graph, &edge.to, visited, component);
        }
    }
}

#[cfg(feature = "cli")]
fn analyze_coupling_strength(graph: &esm_format::graph::ComponentGraph, esm_file: &esm_format::EsmFile) {
    println!("\n=== COUPLING STRENGTH ANALYSIS ===");

    // Analyze based on coupling rules
    if let Some(ref coupling) = esm_file.coupling {
        let mut strong_couplings = 0;
        let mut weak_couplings = 0;

        for rule in coupling {
            match rule {
                esm_format::CouplingEntry::Couple2 { systems, .. } => {
                    // Bidirectional coupling is stronger
                    strong_couplings += 1;
                    if systems.len() >= 2 {
                        println!("  Strong coupling: {} <-> {} (bidirectional)", systems[0], systems[1]);
                    }
                }
                esm_format::CouplingEntry::OperatorCompose { systems, .. } => {
                    // Composition is medium strength
                    if systems.len() >= 2 {
                        println!("  Medium coupling: {} -> {} (composition)", systems[0], systems[1]);
                    }
                }
                esm_format::CouplingEntry::VariableMap { from, to, .. } => {
                    // Variable mapping is weaker
                    weak_couplings += 1;
                    println!("  Weak coupling: {} -> {} (variable mapping)", from, to);
                }
                esm_format::CouplingEntry::OperatorApply { operator, .. } => {
                    println!("  Medium coupling: {} (operator application)", operator);
                }
                esm_format::CouplingEntry::Callback { callback_id, .. } => {
                    println!("  Dynamic coupling: {} (callback)", callback_id);
                }
                esm_format::CouplingEntry::Event { name, affects, .. } => {
                    let event_name = name.as_deref().unwrap_or("unnamed");
                    let affected_count = affects.as_ref().map(|a| a.len()).unwrap_or(0);
                    println!("  Event coupling: {} affects {} components", event_name, affected_count);
                }
            }
        }

        println!("\nCoupling strength distribution:");
        println!("  Strong (bidirectional): {}", strong_couplings);
        println!("  Medium (composition/operators): {}", coupling.len() - strong_couplings - weak_couplings);
        println!("  Weak (variable mapping): {}", weak_couplings);

        if strong_couplings > weak_couplings {
            println!("⚠ Many strong couplings - consider loosening dependencies");
        }
    }
}

#[cfg(feature = "cli")]
fn detect_coupling_antipatterns(graph: &esm_format::graph::ComponentGraph, esm_file: &esm_format::EsmFile) {
    println!("\n=== COUPLING ANTI-PATTERNS ===");

    let mut antipatterns_found = Vec::new();

    // Anti-pattern 1: God component (connected to everything)
    let mut connection_counts = std::collections::HashMap::new();
    for edge in &graph.edges {
        *connection_counts.entry(&edge.from).or_insert(0) += 1;
        *connection_counts.entry(&edge.to).or_insert(0) += 1;
    }

    for (component, count) in &connection_counts {
        if *count > graph.nodes.len() / 2 {
            antipatterns_found.push(format!("God component: {} connected to {}/{} components",
                component, count, graph.nodes.len()));
        }
    }

    // Anti-pattern 2: Inappropriate intimacy (too many coupling types between same components)
    let mut component_pairs = std::collections::HashMap::new();
    for edge in &graph.edges {
        let key = if edge.from < edge.to {
            format!("{}->{}", edge.from, edge.to)
        } else {
            format!("{}->{}", edge.to, edge.from)
        };
        *component_pairs.entry(key).or_insert(0) += 1;
    }

    for (pair, count) in &component_pairs {
        if *count > 2 {
            antipatterns_found.push(format!("Inappropriate intimacy: {} ({} coupling types)",
                pair, count));
        }
    }

    // Anti-pattern 3: Circular dependencies (already detected in SCC analysis)

    if antipatterns_found.is_empty() {
        println!("✓ No major coupling anti-patterns detected");
    } else {
        for antipattern in antipatterns_found {
            println!("  ⚠ {}", antipattern);
        }
    }
}

#[cfg(feature = "cli")]
fn find_longest_dependency_chain(graph: &esm_format::graph::ComponentGraph) -> usize {
    let mut max_length = 0;

    // For each node, find the longest path starting from it
    for node in &graph.nodes {
        let mut visited = std::collections::HashSet::new();
        let length = dfs_longest_path(graph, &node.id, &mut visited);
        max_length = max_length.max(length);
    }

    max_length
}

#[cfg(feature = "cli")]
fn dfs_longest_path(graph: &esm_format::graph::ComponentGraph, node_id: &str, visited: &mut std::collections::HashSet<String>) -> usize {
    if visited.contains(node_id) {
        return 0; // Avoid cycles
    }

    visited.insert(node_id.to_string());
    let mut max_path = 1;

    // Find all outgoing edges
    for edge in &graph.edges {
        if edge.from == node_id {
            let path_length = 1 + dfs_longest_path(graph, &edge.to, visited);
            max_path = max_path.max(path_length);
        }
    }

    visited.remove(node_id);
    max_path
}

#[cfg(feature = "cli")]
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Validate { file, verbose } => {
            let content = fs::read_to_string(&file)?;

            // Perform complete validation (schema + structural)
            let validation_result = validate_complete(&content);

            if validation_result.is_valid {
                println!("✓ Validation passed");
                if verbose && !validation_result.unit_warnings.is_empty() {
                    println!("Warnings:");
                    for warning in validation_result.unit_warnings {
                        println!("  ⚠ {}", warning);
                    }
                }
            } else {
                println!("✗ Validation failed");

                if !validation_result.schema_errors.is_empty() {
                    println!("Schema errors:");
                    for error in &validation_result.schema_errors {
                        println!("  ✗ {}: {}", error.path, error.message);
                    }
                }

                if !validation_result.structural_errors.is_empty() {
                    println!("Structural errors:");
                    for error in &validation_result.structural_errors {
                        if verbose {
                            println!("  ✗ {} ({}): {}", error.path, error.code, error.message);
                            if !error.details.is_null() {
                                println!("    Details: {}", error.details);
                            }
                        } else {
                            println!("  ✗ {}: {}", error.path, error.message);
                        }
                    }
                }
                std::process::exit(1);
            }
        },
        Commands::Pretty { file, format } | Commands::Display { file, format } => {
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
        Commands::Convert { input, output, to } => {
            let content = fs::read_to_string(&input)?;
            let esm_file = load(&content)?;

            let output_content = match to.as_str() {
                "json" => save(&esm_file)?,
                "compact-json" => save_compact(&esm_file)?,
                "julia" => {
                    generate_julia_code(&esm_file)
                },
                "python" => {
                    generate_python_code(&esm_file)
                },
                _ => {
                    eprintln!("Unsupported format: {}. Use json, compact-json, julia, or python.", to);
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
        Commands::Analyze { file, analysis_type } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("System Analysis for: {}", file.display());
            println!("Analysis Type: {}", analysis_type);

            match analysis_type.as_str() {
                "all" | "structure" => {
                    println!("\n=== STRUCTURAL ANALYSIS ===");

                    // Component count analysis
                    let model_count = esm_file.models.as_ref().map(|m| m.len()).unwrap_or(0);
                    let rs_count = esm_file.reaction_systems.as_ref().map(|rs| rs.len()).unwrap_or(0);
                    let dl_count = esm_file.data_loaders.as_ref().map(|dl| dl.len()).unwrap_or(0);
                    let op_count = esm_file.operators.as_ref().map(|op| op.len()).unwrap_or(0);

                    println!("Components: {} models, {} reaction systems, {} data loaders, {} operators",
                        model_count, rs_count, dl_count, op_count);

                    // Equation and variable analysis
                    let mut total_vars = 0;
                    let mut total_eqs = 0;
                    if let Some(ref models) = esm_file.models {
                        for (model_id, model) in models {
                            total_vars += model.variables.len();
                            total_eqs += model.equations.len();
                            println!("  Model {}: {} variables, {} equations",
                                model_id, model.variables.len(), model.equations.len());
                        }
                    }

                    // Species and reaction analysis
                    let mut total_species = 0;
                    let mut total_reactions = 0;
                    if let Some(ref reaction_systems) = esm_file.reaction_systems {
                        for (rs_id, rs) in reaction_systems {
                            total_species += rs.species.len();
                            total_reactions += rs.reactions.len();
                            println!("  Reaction System {}: {} species, {} reactions",
                                rs_id, rs.species.len(), rs.reactions.len());
                        }
                    }

                    println!("Total: {} variables, {} equations, {} species, {} reactions",
                        total_vars, total_eqs, total_species, total_reactions);
                }
                "complexity" => {
                    println!("\n=== COMPLEXITY ANALYSIS ===");
                    // TODO: Implement complexity metrics
                    println!("Complexity analysis not yet implemented");
                }
                "coupling" => {
                    println!("\n=== COUPLING ANALYSIS ===");
                    if let Some(ref coupling) = esm_file.coupling {
                        println!("Coupling rules: {}", coupling.len());
                        for (i, rule) in coupling.iter().enumerate() {
                            match rule {
                                esm_format::CouplingEntry::OperatorCompose { systems, .. } => {
                                    if systems.len() >= 2 {
                                        println!("  Rule {}: {} -> {} (OperatorCompose)", i+1, systems[0], systems[1]);
                                    }
                                }
                                esm_format::CouplingEntry::Couple2 { systems, .. } => {
                                    if systems.len() >= 2 {
                                        println!("  Rule {}: {} <-> {} (Couple2)", i+1, systems[0], systems[1]);
                                    }
                                }
                                esm_format::CouplingEntry::VariableMap { from, to, .. } => {
                                    println!("  Rule {}: {} -> {} (VariableMap)", i+1, from, to);
                                }
                                esm_format::CouplingEntry::OperatorApply { operator, .. } => {
                                    println!("  Rule {}: {} (OperatorApply)", i+1, operator);
                                }
                                esm_format::CouplingEntry::Callback { callback_id, .. } => {
                                    println!("  Rule {}: {} (Callback)", i+1, callback_id);
                                }
                                esm_format::CouplingEntry::Event { name, affects, .. } => {
                                    let event_name = name.as_deref().unwrap_or("unnamed_event");
                                    let systems: Vec<String> = affects.as_ref().map(|affects| {
                                        affects.iter().filter_map(|affect| {
                                            if affect.lhs.contains('.') {
                                                Some(affect.lhs.split('.').next().unwrap_or("").to_string())
                                            } else {
                                                None
                                            }
                                        }).collect()
                                    }).unwrap_or_default();
                                    println!("  Rule {}: {} -> {:?} (Event)", i+1, event_name, systems);
                                }
                            }
                        }
                    } else {
                        println!("No coupling rules defined");
                    }
                }
                _ => {
                    eprintln!("Unsupported analysis type: {}. Use all, structure, complexity, or coupling.", analysis_type);
                    std::process::exit(1);
                }
            }
        },
        Commands::Simulate { file, time, output } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Running simulation for: {}", file.display());
            println!("Simulation time: {}", time);

            // TODO: Implement basic simulation
            // For now, just validate the file and show what would be simulated
            let validation_result = validate(&esm_file);
            if !validation_result.is_valid {
                eprintln!("Cannot simulate: validation failed");
                std::process::exit(1);
            }

            println!("Basic simulation not yet implemented");
            println!("Would simulate for {} time units", time);

            if let Some(output_path) = output {
                println!("Results would be written to: {}", output_path.display());
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

        // ANALYSIS COMMANDS
        Commands::CheckConservation { file, conservation_type } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Conservation Analysis for: {}", file.display());
            println!("Type: {}", conservation_type);

            match conservation_type.as_str() {
                "mass" => {
                    println!("\n=== MASS CONSERVATION ANALYSIS ===");
                    check_mass_conservation(&esm_file);
                }
                "energy" => {
                    println!("\n=== ENERGY CONSERVATION ANALYSIS ===");
                    check_energy_conservation(&esm_file);
                }
                "species" => {
                    println!("\n=== SPECIES CONSERVATION ANALYSIS ===");
                    check_species_conservation(&esm_file);
                }
                "all" => {
                    println!("\n=== COMPREHENSIVE CONSERVATION ANALYSIS ===");
                    check_mass_conservation(&esm_file);
                    println!();
                    check_energy_conservation(&esm_file);
                    println!();
                    check_species_conservation(&esm_file);
                }
                _ => {
                    eprintln!("Unsupported conservation type: {}. Use all, mass, energy, or species.", conservation_type);
                    std::process::exit(1);
                }
            }
        },

        Commands::Units { file, check } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Units Analysis for: {}", file.display());

            if check {
                println!("\n=== DIMENSIONAL CONSISTENCY CHECK ===");
                // Use existing validation for unit checking
                let validation_result = validate(&esm_file);

                if !validation_result.unit_warnings.is_empty() {
                    println!("Unit warnings:");
                    for warning in &validation_result.unit_warnings {
                        println!("  ⚠ {}", warning);
                    }
                } else {
                    println!("✓ All units are dimensionally consistent");
                }
            } else {
                println!("\n=== COMPREHENSIVE UNIT ANALYSIS ===");

                // Analyze units in all components
                analyze_model_units(&esm_file);
                analyze_reaction_system_units(&esm_file);

                // Unit system summary
                println!("\n=== UNIT SYSTEM SUMMARY ===");
                let unit_summary = collect_unit_types(&esm_file);

                if unit_summary.is_empty() {
                    println!("No units specified in the model");
                } else {
                    println!("Unit types found:");
                    for unit_type in &unit_summary {
                        println!("  - {}", unit_type);
                    }

                    // Unit system recommendations
                    println!("\n=== RECOMMENDATIONS ===");
                    if unit_summary.contains(&"m".to_string()) && unit_summary.contains(&"cm".to_string()) {
                        println!("⚠ Mixed length units detected (m, cm) - consider standardizing");
                    }
                    if unit_summary.contains(&"s".to_string()) && unit_summary.contains(&"min".to_string()) {
                        println!("⚠ Mixed time units detected (s, min) - consider standardizing");
                    }

                    // Check for SI compliance
                    let si_base_units = ["m", "kg", "s", "A", "K", "mol", "cd"];
                    let using_si = unit_summary.iter().any(|u| si_base_units.contains(&u.as_str()));
                    if using_si {
                        println!("✓ SI base units detected - good for scientific consistency");
                    } else {
                        println!("ℹ Consider using SI base units for scientific consistency");
                    }
                }
            }
        },

        Commands::CouplingAnalysis { file, depth } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Coupling Dependency Analysis for: {}", file.display());
            println!("Depth: {}", depth);

            let graph = component_graph(&esm_file);
            println!("Found {} components with {} coupling relationships",
                graph.nodes.len(), graph.edges.len());

            for edge in &graph.edges {
                println!("  {} --[{}]--> {}", edge.from, edge.coupling_type, edge.to);
            }

            match depth.as_str() {
                "shallow" => {
                    println!("Shallow analysis complete");
                }
                "deep" => {
                    perform_deep_coupling_analysis(&esm_file);
                }
                _ => {
                    eprintln!("Unsupported depth: {}. Use shallow or deep.", depth);
                    std::process::exit(1);
                }
            }
        },

        Commands::PerformanceProfile { file, profile_type } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Performance Profile for: {}", file.display());
            println!("Profile type: {}", profile_type);

            match profile_type.as_str() {
                "memory" => {
                    println!("\n=== MEMORY ANALYSIS ===");

                    // File size analysis
                    let file_size = content.len();
                    println!("File size: {} bytes ({:.2} KB)", file_size, file_size as f64 / 1024.0);

                    // Component memory estimation
                    let model_count = esm_file.models.as_ref().map(|m| m.len()).unwrap_or(0);
                    let rs_count = esm_file.reaction_systems.as_ref().map(|rs| rs.len()).unwrap_or(0);
                    let dl_count = esm_file.data_loaders.as_ref().map(|dl| dl.len()).unwrap_or(0);
                    let op_count = esm_file.operators.as_ref().map(|op| op.len()).unwrap_or(0);

                    // Estimate memory usage
                    let mut estimated_memory = file_size; // Base JSON representation

                    if let Some(ref models) = esm_file.models {
                        for (model_id, model) in models {
                            let vars_mem = model.variables.len() * 64; // ~64 bytes per variable
                            let eqs_mem = model.equations.len() * 128; // ~128 bytes per equation
                            estimated_memory += vars_mem + eqs_mem;
                            println!("  Model {}: ~{} bytes ({} vars, {} eqs)",
                                model_id, vars_mem + eqs_mem, model.variables.len(), model.equations.len());
                        }
                    }

                    if let Some(ref reaction_systems) = esm_file.reaction_systems {
                        for (rs_id, rs) in reaction_systems {
                            let species_mem = rs.species.len() * 32; // ~32 bytes per species
                            let reactions_mem = rs.reactions.len() * 256; // ~256 bytes per reaction
                            estimated_memory += species_mem + reactions_mem;
                            println!("  Reaction System {}: ~{} bytes ({} species, {} reactions)",
                                rs_id, species_mem + reactions_mem, rs.species.len(), rs.reactions.len());
                        }
                    }

                    println!("Total estimated memory: {} bytes ({:.2} KB)",
                        estimated_memory, estimated_memory as f64 / 1024.0);

                    // Memory optimization suggestions
                    if file_size > 10000 { // > 10KB
                        println!("\n=== MEMORY OPTIMIZATION SUGGESTIONS ===");
                        println!("- Consider using compact JSON format for smaller file sizes");
                        println!("- Use references instead of duplicating common expressions");
                    }
                }
                "time" => {
                    println!("\n=== TIME ANALYSIS ===");

                    // Parsing benchmark
                    let iterations = 100;
                    let start = std::time::Instant::now();
                    for _ in 0..iterations {
                        let _ = load(&content)?;
                    }
                    let parse_duration = start.elapsed();
                    println!("Parse time: {} iterations in {:?} ({:?}/iter)",
                        iterations, parse_duration, parse_duration / iterations as u32);

                    // Validation benchmark
                    let start = std::time::Instant::now();
                    for _ in 0..iterations {
                        let _ = validate(&esm_file);
                    }
                    let validate_duration = start.elapsed();
                    println!("Validate time: {} iterations in {:?} ({:?}/iter)",
                        iterations, validate_duration, validate_duration / iterations as u32);

                    // Expression complexity analysis
                    if let Some(ref models) = esm_file.models {
                        println!("\n=== EXPRESSION COMPLEXITY ===");
                        for (model_id, model) in models {
                            let mut max_depth = 0;
                            let mut total_nodes = 0;

                            for equation in &model.equations {
                                let lhs_depth = expression_depth(&equation.lhs);
                                let rhs_depth = expression_depth(&equation.rhs);
                                max_depth = max_depth.max(lhs_depth).max(rhs_depth);

                                total_nodes += count_expression_nodes(&equation.lhs);
                                total_nodes += count_expression_nodes(&equation.rhs);
                            }

                            println!("  Model {}: max depth = {}, total nodes = {}",
                                model_id, max_depth, total_nodes);
                        }
                    }

                    // Performance suggestions
                    println!("\n=== PERFORMANCE SUGGESTIONS ===");
                    if parse_duration.as_millis() > 100 {
                        println!("- Parse time is high; consider SIMD JSON parsing for large files");
                    }
                    if validate_duration.as_millis() > 50 {
                        println!("- Validation time is high; consider caching validation results");
                    }
                }
                "both" => {
                    // Run both memory and time analysis
                    println!("=== COMBINED PERFORMANCE ANALYSIS ===");
                    // Reuse the above logic for both types

                    // Memory analysis (simplified)
                    let file_size = content.len();
                    println!("File size: {} bytes ({:.2} KB)", file_size, file_size as f64 / 1024.0);

                    // Time analysis (simplified)
                    let iterations = 50;
                    let start = std::time::Instant::now();
                    for _ in 0..iterations {
                        let _ = load(&content)?;
                    }
                    let parse_duration = start.elapsed();
                    println!("Parse time: {:?}/iter", parse_duration / iterations as u32);

                    // Overall assessment
                    println!("\n=== OVERALL ASSESSMENT ===");
                    if file_size < 1000 {
                        println!("✓ Small file size - good performance expected");
                    } else if file_size < 10000 {
                        println!("- Medium file size - acceptable performance");
                    } else {
                        println!("⚠ Large file size - consider optimization");
                    }
                }
                _ => {
                    eprintln!("Unsupported profile type: {}. Use memory, time, or both.", profile_type);
                    std::process::exit(1);
                }
            }
        },

        Commands::Compare { file1, file2, comparison_type } => {
            let content1 = fs::read_to_string(&file1)?;
            let content2 = fs::read_to_string(&file2)?;
            let esm_file1 = load(&content1)?;
            let esm_file2 = load(&content2)?;

            println!("Comparing {} and {}:", file1.display(), file2.display());
            println!("Comparison type: {}", comparison_type);

            match comparison_type.as_str() {
                "semantic" => {
                    // Use existing diff logic
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
                    }
                }
                "structural" => {
                    perform_structural_comparison(&esm_file1, &esm_file2);
                }
                "numerical" => {
                    perform_numerical_comparison(&esm_file1, &esm_file2);
                }
                _ => {
                    eprintln!("Unsupported comparison type: {}. Use semantic, structural, or numerical.", comparison_type);
                    std::process::exit(1);
                }
            }
        },

        Commands::Optimize { file, opt_type } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Optimization Analysis for: {}", file.display());
            println!("Optimization type: {}", opt_type);

            match opt_type.as_str() {
                "expression" => {
                    analyze_expression_optimization(&esm_file);
                }
                "structure" => {
                    analyze_structure_optimization(&esm_file);
                }
                "performance" => {
                    analyze_performance_optimization(&esm_file);
                }
                _ => {
                    eprintln!("Unsupported optimization type: {}. Use expression, structure, or performance.", opt_type);
                    std::process::exit(1);
                }
            }
        },

        // DEVELOPMENT COMMANDS
        Commands::Init { name, template } => {
            println!("Creating new ESM project: {}", name);
            println!("Template: {}", template);

            let project_dir = PathBuf::from(&name);

            if project_dir.exists() {
                eprintln!("Directory '{}' already exists", name);
                std::process::exit(1);
            }

            fs::create_dir(&project_dir)?;

            // Create basic ESM template
            let template_content = match template.as_str() {
                "minimal" => {
                    r#"{
  "esm": "0.1.0",
  "metadata": {
    "name": "{name}",
    "description": "A minimal ESM model",
    "authors": ["Generated by esm-format CLI"],
    "created": "{timestamp}"
  }
}"#
                },
                "atmospheric" => {
                    r#"{
  "esm": "0.1.0",
  "metadata": {
    "name": "{name}",
    "description": "An atmospheric chemistry model",
    "authors": ["Generated by esm-format CLI"],
    "created": "{timestamp}"
  },
  "reaction_systems": {
    "atmospheric_chemistry": {
      "name": "Atmospheric Chemistry",
      "species": [
        {"name": "O2", "units": "molec/cm3"},
        {"name": "O3", "units": "molec/cm3"}
      ],
      "reactions": [
        {
          "substrates": [{"species": "O2", "coefficient": 1.0}],
          "products": [{"species": "O3", "coefficient": 1.0}],
          "rate": {"op": "*", "args": [{"op": "k", "args": []}, "O2"]}
        }
      ]
    }
  }
}"#
                },
                "ecosystem" => {
                    r#"{
  "esm": "0.1.0",
  "metadata": {
    "name": "{name}",
    "description": "An ecosystem model",
    "authors": ["Generated by esm-format CLI"],
    "created": "{timestamp}"
  },
  "models": {
    "ecosystem": {
      "name": "Simple Ecosystem",
      "variables": [
        {"name": "biomass", "units": "kg/m2", "initial_value": 1.0}
      ],
      "equations": [
        {
          "lhs": {"op": "d", "args": ["biomass"], "wrt": "t"},
          "rhs": {"op": "*", "args": [0.1, "biomass"]}
        }
      ]
    }
  }
}"#
                },
                "coupling" => {
                    r#"{
  "esm": "0.1.0",
  "metadata": {
    "name": "{name}",
    "description": "A coupled system model",
    "authors": ["Generated by esm-format CLI"],
    "created": "{timestamp}"
  },
  "models": {
    "atmosphere": {
      "name": "Atmospheric Model",
      "variables": [{"name": "temperature", "units": "K"}],
      "equations": [
        {
          "lhs": {"op": "d", "args": ["temperature"], "wrt": "t"},
          "rhs": {"op": "+", "args": ["heating", "cooling"]}
        }
      ]
    },
    "ocean": {
      "name": "Ocean Model",
      "variables": [{"name": "sea_temp", "units": "K"}],
      "equations": [
        {
          "lhs": {"op": "d", "args": ["sea_temp"], "wrt": "t"},
          "rhs": {"op": "*", "args": [0.5, "heat_flux"]}
        }
      ]
    }
  },
  "coupling": [
    {
      "from": "atmosphere.temperature",
      "to": "ocean.heat_flux",
      "transform": {"op": "*", "args": ["temperature", 0.1]}
    }
  ]
}"#
                },
                _ => {
                    eprintln!("Unsupported template: {}. Use minimal, atmospheric, ecosystem, or coupling.", template);
                    std::process::exit(1);
                }
            };

            // Replace placeholders
            let timestamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs();
            let final_content = template_content
                .replace("{name}", &name)
                .replace("{timestamp}", &format!("{}", timestamp));

            let esm_file = project_dir.join(format!("{}.esm", name));
            fs::write(&esm_file, final_content)?;

            println!("Created project '{}' with template '{}'", name, template);
            println!("Main file: {}", esm_file.display());
        },

        Commands::ValidateFixtures { directory, recursive } => {
            println!("Validating fixtures in: {}", directory.display());
            println!("Recursive: {}", recursive);

            if !directory.exists() {
                eprintln!("Directory does not exist: {}", directory.display());
                std::process::exit(1);
            }

            let pattern = if recursive { "**/*.esm" } else { "*.esm" };

            // TODO: Use glob to find files and validate them
            println!("Batch validation not yet fully implemented");
            println!("Would process files matching: {}", pattern);
        },

        Commands::Benchmark { file, bench_type, iterations } => {
            let content = fs::read_to_string(&file)?;

            println!("Benchmarking: {}", file.display());
            println!("Type: {}, Iterations: {}", bench_type, iterations);

            match bench_type.as_str() {
                "all" | "parse" => {
                    let start = std::time::Instant::now();
                    for _ in 0..iterations {
                        let _ = load(&content)?;
                    }
                    let duration = start.elapsed();
                    println!("Parse: {} iterations in {:?} ({:?}/iter)",
                        iterations, duration, duration / (iterations as u32));
                }
                "validate" => {
                    let esm_file = load(&content)?;
                    let start = std::time::Instant::now();
                    for _ in 0..iterations {
                        let _ = validate(&esm_file);
                    }
                    let duration = start.elapsed();
                    println!("Validate: {} iterations in {:?} ({:?}/iter)",
                        iterations, duration, duration / (iterations as u32));
                }
                "simulate" => {
                    println!("Simulation benchmarking not yet implemented");
                }
                _ => {
                    eprintln!("Unsupported benchmark type: {}. Use all, parse, validate, or simulate.", bench_type);
                    std::process::exit(1);
                }
            }
        },

        Commands::SchemaCheck { file, schema_version } => {
            let content = fs::read_to_string(&file)?;

            println!("Schema check for: {}", file.display());
            if let Some(ref version) = schema_version {
                println!("Target schema version: {}", version);
            }

            // Load performs schema validation
            match load(&content) {
                Ok(_) => println!("✓ Schema validation passed"),
                Err(e) => {
                    println!("✗ Schema validation failed: {}", e);
                    std::process::exit(1);
                }
            }
        },

        Commands::RoundTrip { file, rounds } => {
            println!("Round-trip test for: {} ({} rounds)", file.display(), rounds);

            let original_content = fs::read_to_string(&file)?;
            let mut content = original_content.clone();

            for round in 1..=rounds {
                // Load
                let esm_file = match load(&content) {
                    Ok(file) => file,
                    Err(e) => {
                        eprintln!("Round {}: Load failed: {}", round, e);
                        std::process::exit(1);
                    }
                };

                // Save
                content = match save(&esm_file) {
                    Ok(content) => content,
                    Err(e) => {
                        eprintln!("Round {}: Save failed: {}", round, e);
                        std::process::exit(1);
                    }
                };

                println!("Round {}: OK", round);
            }

            // Check if final content matches original (semantically)
            let original_esm = load(&original_content)?;
            let final_esm = load(&content)?;

            let original_json = serde_json::to_value(&original_esm)?;
            let final_json = serde_json::to_value(&final_esm)?;

            if original_json == final_json {
                println!("✓ Round-trip fidelity maintained");
            } else {
                println!("✗ Round-trip fidelity lost");
                std::process::exit(1);
            }
        },

        Commands::Interactive { file } => {
            println!("ESM Interactive REPL");

            if let Some(file_path) = file {
                println!("Loading context from: {}", file_path.display());
                let content = fs::read_to_string(&file_path)?;
                let _esm_file = load(&content)?;
                println!("File loaded successfully");
            }

            println!("Interactive REPL not yet implemented");
            println!("Type 'exit' to quit (if it were implemented)");
        },
    }

    Ok(())
}

#[cfg(not(feature = "cli"))]
fn main() {
    eprintln!("CLI feature not enabled. Please compile with --features cli");
    std::process::exit(1);
}