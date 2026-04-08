# SolverConfiguration (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_test.jl`

```julia
# Test default construction
        config = SolverConfiguration()
        @test config.threads === nothing
        @test config.timestep === nothing
        @test config.stiff_algorithm === nothing
        @test config.nonstiff_algorithm === nothing
        @test config.map_algorithm === nothing
        @test haskey(config.stiff_kwargs, "abstol")
        @test haskey(config.stiff_kwargs, "reltol")
        @test config.numerical_method === nothing
        @test isempty(config.extra_parameters)

        # Test construction with parameters
        config2 = SolverConfiguration(
            threads=4,
            timestep=0.01,
            stiff_algorithm="QNDF",
            nonstiff_algorithm="Tsit5",
            numerical_method=FiniteDifferenceMethod,
            extra_parameters=Dict("custom_param" => 42)
        )
        @test config2.threads == 4
        @test config2.timestep == 0.01
        @test config2.stiff_algorithm == "QNDF"
        @test config2.nonstiff_algorithm == "Tsit5"
        @test config2.numerical_method == FiniteDifferenceMethod
        @test config2.extra_parameters["custom_param"] == 42
```

