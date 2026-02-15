//! ESM Format CLI Tool
//!
//! Command-line interface for working with ESM files

#[cfg(feature = "cli")]
use clap::{Parser, Subcommand};
#[cfg(feature = "cli")]
use esm_format::{load, save, validate};
#[cfg(feature = "cli")]
use std::fs;
#[cfg(feature = "cli")]
use std::path::PathBuf;

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
    /// Pretty-print expressions in an ESM file
    PrettyPrint {
        /// Path to the ESM file
        #[arg(value_name = "FILE")]
        file: PathBuf,
        /// Output format (unicode, latex, ascii)
        #[arg(short, long, default_value = "unicode")]
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

                    if validation_result.valid {
                        println!("✓ Structural validation passed");
                        if verbose && !validation_result.warnings.is_empty() {
                            println!("Warnings:");
                            for warning in validation_result.warnings {
                                println!("  ⚠ {}", warning);
                            }
                        }
                    } else {
                        println!("✗ Structural validation failed");
                        for error in validation_result.errors {
                            println!("  ✗ {}: {}", error.path, error.message);
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
        Commands::Convert { input, output, format } => {
            let content = fs::read_to_string(&input)?;
            let esm_file = load(&content)?;

            let output_content = match format.as_str() {
                "json" => save(&esm_file)?,
                "compact-json" => esm_format::serialize::save_compact(&esm_file)?,
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
        Commands::PrettyPrint { file, format } => {
            let content = fs::read_to_string(&file)?;
            let esm_file = load(&content)?;

            println!("Pretty-printing expressions in {}:", file.display());

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