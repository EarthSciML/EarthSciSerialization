use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use esm_format::{
    EsmFile, Metadata, load, save, validate,
    performance::{CompactExpr, PerformanceError},
    Expr, Model, ReactionSystem, Species, Reaction, StoichiometricEntry,
    stoichiometric_matrix,
};
use std::collections::HashMap;

#[cfg(feature = "parallel")]
use esm_format::performance::ParallelEvaluator;

#[cfg(feature = "simd")]
use esm_format::performance::simd_math;

/// Create a test ESM file with varying complexity
fn create_test_esm(num_models: usize, equations_per_model: usize) -> EsmFile {
    let mut models = HashMap::new();

    for i in 0..num_models {
        let mut variables = HashMap::new();
        let mut equations = Vec::new();

        // Create variables
        for j in 0..equations_per_model {
            let var_name = format!("x{}_{}", i, j);
            variables.insert(var_name.clone(), esm_format::ModelVariable {
                name: Some(var_name.clone()),
                var_type: esm_format::VariableType::StateVariable,
                units: Some("m/s".to_string()),
                description: None,
                initial_condition: Some(Expr::Number(1.0)),
                bounds: None,
        expression: None,
            });
        }

        // Create equations
        for j in 0..equations_per_model {
            let var_name = format!("x{}_{}", i, j);
            equations.push(esm_format::Equation {
                lhs: Expr::Variable(var_name),
                rhs: Expr::BinaryOp {
                    op: "*".to_string(),
                    left: Box::new(Expr::Variable("k".to_string())),
                    right: Box::new(Expr::Variable(format!("x{}_{}", i, (j + 1) % equations_per_model))),
                },
            });
        }

        let model = Model {
            name: Some(format!("model_{}", i)),
            variables,
            equations,
            description: None,
            discrete_events: None,
        };

        models.insert(format!("model_{}", i), model);
    }

    EsmFile {
        esm: "0.1.0".to_string(),
        metadata: Metadata {
            name: Some("benchmark_test".to_string()),
            description: Some("Benchmark test file".to_string()),
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
    }
}

/// Create a test reaction system with varying complexity
fn create_test_reaction_system(num_species: usize, num_reactions: usize) -> ReactionSystem {
    let mut species = Vec::new();
    let mut reactions = Vec::new();

    // Create species
    for i in 0..num_species {
        species.push(Species {
            name: format!("S{}", i),
            formula: None,
            charge: None,
            phase: None,
        });
    }

    // Create reactions
    for i in 0..num_reactions {
        let substrate_idx = i % num_species;
        let product_idx = (i + 1) % num_species;

        reactions.push(Reaction {
            name: Some(format!("R{}", i)),
            substrates: vec![StoichiometricEntry {
                species: format!("S{}", substrate_idx),
                coefficient: Some(1.0),
            }],
            products: vec![StoichiometricEntry {
                species: format!("S{}", product_idx),
                coefficient: Some(1.0),
            }],
            rate_law: Some(Expr::BinaryOp {
                op: "*".to_string(),
                left: Box::new(Expr::Number(0.1)),
                right: Box::new(Expr::Variable(format!("S{}", substrate_idx))),
            }),
            description: None,
        });
    }

    ReactionSystem {
        name: Some("benchmark_system".to_string()),
        species,
        reactions,
        description: None,
    }
}

fn benchmark_parsing(c: &mut Criterion) {
    let mut group = c.benchmark_group("parsing");

    for size in [10, 50, 100].iter() {
        let esm_file = create_test_esm(*size, 10);
        let json_str = save(&esm_file).unwrap();

        group.bench_with_input(BenchmarkId::new("standard_parse", size), &json_str, |b, json| {
            b.iter(|| load(black_box(json)).unwrap())
        });

        #[cfg(feature = "zero_copy")]
        {
            let mut json_bytes = json_str.clone().into_bytes();
            group.bench_with_input(BenchmarkId::new("simd_parse", size), &json_bytes, |b, bytes| {
                b.iter(|| {
                    let mut data = bytes.clone();
                    esm_format::performance::fast_parse(black_box(&mut data)).unwrap()
                })
            });
        }
    }

    group.finish();
}

fn benchmark_validation(c: &mut Criterion) {
    let mut group = c.benchmark_group("validation");

    for size in [10, 50, 100].iter() {
        let esm_file = create_test_esm(*size, 10);

        group.bench_with_input(BenchmarkId::new("validate", size), &esm_file, |b, esm| {
            b.iter(|| validate(black_box(esm)))
        });
    }

    group.finish();
}

fn benchmark_stoichiometric_matrix(c: &mut Criterion) {
    let mut group = c.benchmark_group("stoichiometric_matrix");

    for (species, reactions) in [(10, 20), (50, 100), (100, 200)].iter() {
        let system = create_test_reaction_system(*species, *reactions);

        group.bench_with_input(
            BenchmarkId::new("sequential", format!("{}x{}", species, reactions)),
            &system,
            |b, sys| {
                b.iter(|| stoichiometric_matrix(black_box(sys)))
            }
        );

        #[cfg(feature = "parallel")]
        {
            let evaluator = ParallelEvaluator::new(None).unwrap();
            group.bench_with_input(
                BenchmarkId::new("parallel", format!("{}x{}", species, reactions)),
                &system,
                |b, sys| {
                    b.iter(|| evaluator.compute_stoichiometric_matrix_parallel(black_box(sys)).unwrap())
                }
            );
        }
    }

    group.finish();
}

fn benchmark_expression_evaluation(c: &mut Criterion) {
    let mut group = c.benchmark_group("expression_evaluation");

    // Create test expressions of varying complexity
    let simple_expr = Expr::BinaryOp {
        op: "+".to_string(),
        left: Box::new(Expr::Variable("x".to_string())),
        right: Box::new(Expr::Number(1.0)),
    };

    let complex_expr = Expr::BinaryOp {
        op: "+".to_string(),
        left: Box::new(Expr::BinaryOp {
            op: "*".to_string(),
            left: Box::new(Expr::FunctionCall {
                name: "sin".to_string(),
                args: vec![Expr::Variable("x".to_string())],
            }),
            right: Box::new(Expr::Variable("k".to_string())),
        }),
        right: Box::new(Expr::FunctionCall {
            name: "exp".to_string(),
            args: vec![Expr::BinaryOp {
                op: "/".to_string(),
                left: Box::new(Expr::Variable("y".to_string())),
                right: Box::new(Expr::Number(2.0)),
            }],
        }),
    };

    let mut variables = HashMap::new();
    variables.insert("x".to_string(), 1.5);
    variables.insert("y".to_string(), 2.5);
    variables.insert("k".to_string(), 0.1);

    group.bench_function("simple_standard", |b| {
        b.iter(|| esm_format::expression::evaluate(black_box(&simple_expr), black_box(&variables)).unwrap())
    });

    group.bench_function("complex_standard", |b| {
        b.iter(|| esm_format::expression::evaluate(black_box(&complex_expr), black_box(&variables)).unwrap())
    });

    // Compact expression benchmarks
    let compact_simple = CompactExpr::from_expr(&simple_expr);
    let compact_complex = CompactExpr::from_expr(&complex_expr);

    #[cfg(feature = "parallel")]
    {
        group.bench_function("simple_compact", |b| {
            b.iter(|| compact_simple.evaluate_fast(black_box(&variables)).unwrap())
        });

        group.bench_function("complex_compact", |b| {
            b.iter(|| compact_complex.evaluate_fast(black_box(&variables)).unwrap())
        });
    }

    // Parallel evaluation benchmark
    #[cfg(feature = "parallel")]
    {
        let expressions = vec![simple_expr.clone(); 1000];
        let evaluator = ParallelEvaluator::new(None).unwrap();

        group.bench_function("batch_parallel", |b| {
            b.iter(|| evaluator.evaluate_batch(black_box(&expressions), black_box(&variables)).unwrap())
        });
    }

    group.finish();
}

#[cfg(feature = "simd")]
fn benchmark_simd_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("simd_operations");

    for size in [100, 1000, 10000].iter() {
        let a: Vec<f64> = (0..*size).map(|i| i as f64).collect();
        let b: Vec<f64> = (0..*size).map(|i| (i + 1) as f64).collect();
        let mut result = vec![0.0; *size];

        group.bench_with_input(BenchmarkId::new("add_scalar", size), &(*size, &a, &b), |bench, (_, a, b)| {
            bench.iter(|| {
                for i in 0..a.len() {
                    result[i] = a[i] + b[i];
                }
                black_box(&result);
            })
        });

        group.bench_with_input(BenchmarkId::new("add_simd", size), &(*size, &a, &b), |bench, (_, a, b)| {
            bench.iter(|| {
                simd_math::add_vectors_simd(black_box(a), black_box(b), black_box(&mut result)).unwrap();
                black_box(&result);
            })
        });

        group.bench_with_input(BenchmarkId::new("multiply_scalar", size), &(*size, &a, &b), |bench, (_, a, b)| {
            bench.iter(|| {
                for i in 0..a.len() {
                    result[i] = a[i] * b[i];
                }
                black_box(&result);
            })
        });

        group.bench_with_input(BenchmarkId::new("multiply_simd", size), &(*size, &a, &b), |bench, (_, a, b)| {
            bench.iter(|| {
                simd_math::multiply_vectors_simd(black_box(a), black_box(b), black_box(&mut result)).unwrap();
                black_box(&result);
            })
        });

        group.bench_with_input(BenchmarkId::new("dot_scalar", size), &(*size, &a, &b), |bench, (_, a, b)| {
            bench.iter(|| {
                let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
                black_box(dot);
            })
        });

        group.bench_with_input(BenchmarkId::new("dot_simd", size), &(*size, &a, &b), |bench, (_, a, b)| {
            bench.iter(|| {
                let dot = simd_math::dot_product_simd(black_box(a), black_box(b)).unwrap();
                black_box(dot);
            })
        });
    }

    group.finish();
}

#[cfg(feature = "custom_alloc")]
fn benchmark_memory_allocation(c: &mut Criterion) {
    let mut group = c.benchmark_group("memory_allocation");

    for size in [1000, 10000, 100000].iter() {
        group.bench_with_input(BenchmarkId::new("standard_alloc", size), size, |b, &size| {
            b.iter(|| {
                let _data: Vec<f64> = vec![0.0; size];
                black_box(&_data);
            })
        });

        group.bench_with_input(BenchmarkId::new("bump_alloc", size), size, |b, &size| {
            b.iter(|| {
                let allocator = esm_format::performance::ModelAllocator::new();
                let _data = allocator.alloc_slice::<f64>(size);
                black_box(&_data);
            })
        });
    }

    group.finish();
}

// Define benchmark groups
criterion_group!(
    benches,
    benchmark_parsing,
    benchmark_validation,
    benchmark_stoichiometric_matrix,
    benchmark_expression_evaluation,
    #[cfg(feature = "simd")]
    benchmark_simd_operations,
    #[cfg(feature = "custom_alloc")]
    benchmark_memory_allocation
);

criterion_main!(benches);