# Auto-tuning Convenience Functions (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_optimization_test.jl`

```julia
# Test create_auto_tuning_optimizer
        adaptive_optimizer = create_auto_tuning_optimizer(strategy="adaptive")
        @test adaptive_optimizer.strategy isa AdaptiveStrategy

        grid_optimizer = create_auto_tuning_optimizer(strategy="grid_search", max_evaluations=100)
        @test grid_optimizer.strategy isa GridSearchStrategy
        @test grid_optimizer.strategy.max_evaluations == 100

        # Test invalid strategy
        @test_throws ErrorException create_auto_tuning_optimizer(strategy="invalid")

        # Test auto_tune_solver
        base_solver = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.01)
        characteristics = ProblemCharacteristics(
            stiffness_ratio=500.0,
            problem_size=2000,
            temporal_scale=1e-5
        )

        tuned_solver = auto_tune_solver(base_solver, characteristics, max_iterations=10)
        @test tuned_solver isa Solver
        @test tuned_solver.strategy == base_solver.strategy
        # Configuration should be adapted based on characteristics
        @test tuned_solver.config !== base_solver.config
```

