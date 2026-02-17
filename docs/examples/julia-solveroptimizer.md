# SolverOptimizer (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_optimization_test.jl`

```julia
# Test construction
        strategy = AdaptiveStrategy()
        optimizer = SolverOptimizer(strategy)
        @test optimizer.strategy === strategy
        @test isempty(optimizer.history.configurations)
        @test isempty(optimizer.history.metrics)
        @test isempty(optimizer.history.timestamps)
        @test optimizer.current_best === nothing
        @test optimizer.best_performance === nothing
        @test optimizer.problem_characteristics === nothing

        # Test setting problem characteristics
        characteristics = ProblemCharacteristics(stiffness_ratio=100.0, problem_size=1000)
        set_problem_characteristics!(optimizer, characteristics)
        @test optimizer.problem_characteristics === characteristics
```

