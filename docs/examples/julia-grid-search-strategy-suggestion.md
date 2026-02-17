# Grid Search Strategy Suggestion (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_optimization_test.jl`

```julia
param_ranges = Dict{String,Vector{Any}}(
            "abstol" => [1e-6, 1e-8, 1e-10],
            "timestep" => [1e-3, 1e-2, 1e-1]
        )
        strategy = GridSearchStrategy(param_ranges, max_evaluations=10)
        optimizer = SolverOptimizer(strategy)
        base_solver = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.01)

        # Test suggestion with empty history
        suggested_config = suggest_next_configuration(optimizer, base_solver)
        @test suggested_config isa SolverConfiguration

        # Test suggestion with some history
        metrics = PerformanceMetrics(1.0, 20, 1e-7, 1024*1024, 0.8, true)
        record_performance!(optimizer, suggested_config, metrics)

        suggested_config2 = suggest_next_configuration(optimizer, base_solver)
        @test suggested_config2 isa SolverConfiguration
```

