# Section 4 Editing Operations (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
@testset "add_variable" begin
        m = _make_model()
        @test length(m.variables) == 2

        new_var = ModelVariable(StateVariable, default=5.0, description="new state")
        m2 = add_variable(m, "y", new_var)

        @test length(m2.variables) == 3
        @test haskey(m2.variables, "y")
        @test m2.variables["y"].default == 5.0
        @test m2.variables["y"].description == "new state"
        # original model should be unchanged (non-mutating)
        @test length(m.variables) == 2
        @test !haskey(m.variables, "y")
        # equations preserved
        @test length(m2.equations) == length(m.equations)
```

