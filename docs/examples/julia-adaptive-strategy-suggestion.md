# Adaptive Strategy Suggestion (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_optimization_test.jl`

```julia
strategy = AdaptiveStrategy()
        optimizer = SolverOptimizer(strategy)
        base_solver = Solver("strang_threads", threads=4, stiff_algorithm="QNDF")
        characteristics = ProblemCharacteristics(stiffness_ratio=200.0, problem_size=1000)

        set_problem_characteristics!(optimizer, characteristics)

        # Test suggestion with minimal history
        suggested_config = suggest_next_configuration(optimizer, base_solver)
        @test suggested_config isa SolverConfiguration

        # Add some history
        for i in 1:5
            metrics = PerformanceMetrics(
                1.0 + 0.1*i, 20 + i, 1e-7, 1024*1024, 0.8 - 0.02*i, true
            )
            config = SolverConfiguration(threads=i, timestep=0.01*i)
            record_performance!(optimizer, config, metrics)
```

