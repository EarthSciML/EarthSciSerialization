# create_solver_with_method (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_test.jl`

```julia
# Test creation with method and strategy
        solver = create_solver_with_method("strang_threads", "fdm", threads=4)
        @test solver.strategy == StrangThreads
        @test solver.config.numerical_method == FiniteDifferenceMethod
        @test solver.config.stiff_algorithm == "QNDF"
        @test solver.config.nonstiff_algorithm == "Tsit5"
        @test solver.config.threads == 4
        @test validate_solver_compatibility(solver) == true

        # Test IMEX + FEM combination
        solver2 = create_solver_with_method("imex", "fem", timestep=0.01)
        @test solver2.strategy == IMEX
        @test solver2.config.numerical_method == FiniteElementMethod
        @test solver2.config.stiff_algorithm == "ARKODE"
        @test solver2.config.timestep == 0.01
        @test validate_solver_compatibility(solver2) == true
```

