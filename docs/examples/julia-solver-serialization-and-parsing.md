# Solver Serialization and Parsing (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_test.jl`

```julia
# Test new format serialization
        solver = Solver("strang_threads",
                       threads=4,
                       stiff_algorithm="QNDF",
                       nonstiff_algorithm="Tsit5",
                       timestep=0.01,
                       numerical_method=FiniteDifferenceMethod)

        serialized = serialize_solver(solver)
        @test serialized["strategy"] == "strang_threads"
        @test serialized["config"]["threads"] == 4
        @test serialized["config"]["stiff_algorithm"] == "QNDF"
        @test serialized["config"]["nonstiff_algorithm"] == "Tsit5"
        @test serialized["config"]["timestep"] == 0.01
        @test serialized["config"]["numerical_method"] == "fdm"

        # Test parsing new format - convert string keys to symbols for coerce_solver
        serialized_with_symbols = Dict(Symbol(k) => v for (k, v) in serialized)
        # Also convert nested config
        if haskey(serialized_with_symbols, :config)
            serialized_with_symbols[:config] = Dict(Symbol(k) => v for (k, v) in serialized_with_symbols[:config])
```

