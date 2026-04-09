# Code Generation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/test_codegen.jl`

```julia
@testset "to_julia_code" begin
        @testset "should generate basic Julia script structure" begin
            file = EsmFile(
                "0.1.0",
                Metadata(
                    "Test Model";
                    description = "A test model for code generation"
                );
                models = Dict{String,Model}(),
                reaction_systems = Dict{String,ReactionSystem}()
            )

            code = to_julia_code(file)

            @test occursin("using ModelingToolkit", code)
            @test occursin("using Catalyst", code)
            @test occursin("using EarthSciMLBase", code)
            @test occursin("using OrdinaryDiffEq", code)
            @test occursin("using Unitful", code)
            @test occursin("# Title: Test Model", code)
            @test occursin("# Description: A test model for code generation", code)
```

