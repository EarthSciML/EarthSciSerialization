# Solver System Tests (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_test.jl`

```julia
@testset "Solver Strategy Enum" begin
        # Test enum values exist
        @test StrangThreads isa SolverStrategy
        @test StrangSerial isa SolverStrategy
        @test IMEX isa SolverStrategy

        # Test string parsing
        @test parse_solver_strategy("strang_threads") == StrangThreads
        @test parse_solver_strategy("strang_serial") == StrangSerial
        @test parse_solver_strategy("imex") == IMEX

        # Test invalid strategy throws error
        @test_throws ArgumentError parse_solver_strategy("invalid_strategy")

        # Test enum to string conversion
        @test solver_strategy_to_string(StrangThreads) == "strang_threads"
        @test solver_strategy_to_string(StrangSerial) == "strang_serial"
        @test solver_strategy_to_string(IMEX) == "imex"
```

