use esm_format::{
    Expr, performance::CompactExpr,
};

#[test]
fn test_compact_expression_creation() {
    // Test simple expression: x + 1
    let expr = Expr::Operator(esm_format::ExpressionNode {
        op: "+".to_string(),
        args: vec![
            Expr::Variable("x".to_string()),
            Expr::Number(1.0),
        ],
        wrt: None,
        dim: None,
    });

    let compact = CompactExpr::from_expr(&expr);

    // Should have 3 nodes: Variable(x), Number(1.0), Operator(+)
    assert_eq!(compact.nodes.len(), 3);
    assert_eq!(compact.var_cache.len(), 1);
    assert!(compact.var_cache.contains_key("x"));
}

#[cfg(feature = "parallel")]
#[test]
fn test_compact_expression_evaluation() {
    use esm_format::performance::CompactExpr;

    // Test simple expression: x + 1
    let expr = Expr::Operator(esm_format::ExpressionNode {
        op: "+".to_string(),
        args: vec![
            Expr::Variable("x".to_string()),
            Expr::Number(1.0),
        ],
        wrt: None,
        dim: None,
    });

    let compact = CompactExpr::from_expr(&expr);

    let mut variables = HashMap::new();
    variables.insert("x".to_string(), 5.0);

    let result = compact.evaluate_fast(&variables).unwrap();
    assert_eq!(result, 6.0);
}

#[cfg(feature = "parallel")]
#[test]
fn test_parallel_evaluator_creation() {
    use esm_format::performance::ParallelEvaluator;

    let evaluator = ParallelEvaluator::new(Some(2));
    assert!(evaluator.is_ok());
}

#[cfg(feature = "simd")]
#[test]
fn test_simd_operations() {
    use esm_format::performance::simd_math;

    let a = vec![1.0, 2.0, 3.0, 4.0];
    let b = vec![2.0, 3.0, 4.0, 5.0];
    let mut result = vec![0.0; 4];

    // Test SIMD addition
    simd_math::add_vectors_simd(&a, &b, &mut result).unwrap();
    assert_eq!(result, vec![3.0, 5.0, 7.0, 9.0]);

    // Test SIMD dot product
    let dot = simd_math::dot_product_simd(&a, &b).unwrap();
    assert_eq!(dot, 40.0); // 1*2 + 2*3 + 3*4 + 4*5 = 2 + 6 + 12 + 20 = 40
}

#[cfg(feature = "custom_alloc")]
#[test]
fn test_model_allocator() {
    use esm_format::performance::ModelAllocator;

    let allocator = ModelAllocator::new();
    let slice = allocator.alloc_slice::<f64>(100);
    assert_eq!(slice.len(), 100);

    // All elements should be initialized to default (0.0)
    assert!(slice.iter().all(|&x| x == 0.0));
}

#[cfg(feature = "zero_copy")]
#[test]
fn test_fast_parse() {
    use esm_format::performance::fast_parse;

    let json_data = r#"
    {
        "esm": "0.1.0",
        "metadata": {
            "name": "test"
        }
    }"#;

    let mut json_bytes = json_data.as_bytes().to_vec();
    let result = fast_parse(&mut json_bytes);
    assert!(result.is_ok());

    let esm_file = result.unwrap();
    assert_eq!(esm_file.esm, "0.1.0");
    assert_eq!(esm_file.metadata.name, Some("test".to_string()));
}