# Flatten System Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
@testset "FlattenedEquation construction" begin
        eq = FlattenedEquation("Atm.T", "Atm.k * Atm.T", "Atm")
        @test eq.lhs == "Atm.T"
        @test eq.rhs == "Atm.k * Atm.T"
        @test eq.source_system == "Atm"
```

