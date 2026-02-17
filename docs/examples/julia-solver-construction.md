# Solver Construction (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_test.jl`

```julia
# Test construction with enum strategy
        config = SolverConfiguration(threads=2, stiff_algorithm="QNDF")
        solver = Solver(StrangThreads, config)
        @test solver.strategy == StrangThreads
        @test solver.config.threads == 2
        @test solver.config.stiff_algorithm == "QNDF"

        # Test construction with string strategy
        solver2 = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.001)
        @test solver2.strategy == IMEX
        @test solver2.config.stiff_algorithm == "KenCarp4"
        @test solver2.config.timestep == 0.001

        # Test invalid string strategy throws error
        @test_throws ArgumentError Solver("invalid_strategy")
```

