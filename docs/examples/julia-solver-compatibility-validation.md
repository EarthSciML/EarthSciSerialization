# Solver Compatibility Validation (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_test.jl`

```julia
# Test valid Strang threads configuration
        solver1 = Solver("strang_threads",
                        threads=4,
                        stiff_algorithm="QNDF",
                        nonstiff_algorithm="Tsit5")
        @test validate_solver_compatibility(solver1) == true

        # Test invalid Strang threads (no thread count)
        solver2 = Solver("strang_threads", stiff_algorithm="QNDF")
        @test validate_solver_compatibility(solver2) == false

        # Test valid Strang serial configuration
        solver3 = Solver("strang_serial",
                        stiff_algorithm="QNDF",
                        nonstiff_algorithm="Tsit5")
        @test validate_solver_compatibility(solver3) == true

        # Test invalid Strang serial (too many threads)
        solver4 = Solver("strang_serial",
                        threads=4,
                        stiff_algorithm="QNDF",
                        nonstiff_algorithm="Tsit5")
        @test validate_solver_compatibility(solver4) == false

        # Test valid IMEX configuration
        solver5 = Solver("imex", stiff_algorithm="KenCarp4")
        @test validate_solver_compatibility(solver5) == true

        # Test invalid timestep
        solver6 = Solver("imex", stiff_algorithm="KenCarp4", timestep=-0.1)
        @test validate_solver_compatibility(solver6) == false

        # Test invalid tolerance
        solver7 = Solver("imex", stiff_algorithm="KenCarp4")
        solver7.config.stiff_kwargs["abstol"] = -1e-8
        @test validate_solver_compatibility(solver7) == false
```

