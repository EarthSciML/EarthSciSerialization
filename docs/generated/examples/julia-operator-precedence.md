# Operator Precedence (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/display_test.jl`

```julia
# Test get_operator_precedence - check actual values in the implementation
        @test ESMFormat.get_operator_precedence("+") == 4
        @test ESMFormat.get_operator_precedence("-") == 4
        @test ESMFormat.get_operator_precedence("*") == 5
        @test ESMFormat.get_operator_precedence("/") == 5
        @test ESMFormat.get_operator_precedence("^") == 7
        @test ESMFormat.get_operator_precedence("pow") == 8  # Based on error output
        @test ESMFormat.get_operator_precedence("sin") == 8
        @test ESMFormat.get_operator_precedence("unknown") == 8  # Unknown operators get default precedence
```

