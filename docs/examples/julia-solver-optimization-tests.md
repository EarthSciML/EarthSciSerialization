# Solver Optimization Tests (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_optimization_test.jl`

```julia
@testset "PerformanceMetrics" begin
        # Test construction
        metrics = PerformanceMetrics(1.5, 25, 1e-6, 1024*1024, 0.85, true)
        @test metrics.execution_time == 1.5
        @test metrics.convergence_iterations == 25
        @test metrics.error_norm == 1e-6
        @test metrics.memory_usage == 1024*1024
        @test metrics.stability_indicator == 0.85
        @test metrics.success == true

        # Test performance scoring
        score = ESMFormat.calculate_performance_score(metrics)
        @test score > 0.0
        @test score <= 1.0

        # Test failed run scoring
        failed_metrics = PerformanceMetrics(1.0, 100, 1e-3, 1024*1024, 0.1, false)
        @test ESMFormat.calculate_performance_score(failed_metrics) == 0.0
```

