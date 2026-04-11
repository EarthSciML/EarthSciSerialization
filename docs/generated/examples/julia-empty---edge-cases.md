# Empty / edge cases (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_catalyst_test.jl`

```julia
empty_model = Model(Dict{String,ModelVariable}(), Equation[])
        @test_nowarn MockMTKSystem(empty_model)
        empty_sys = MockMTKSystem(empty_model; name=:EmptyModel)
        @test empty_sys isa MockMTKSystem

        # Empty reaction system
        empty_rsys = ReactionSystem(Species[], Reaction[])
        @test_nowarn MockCatalystSystem(empty_rsys)
        empty_cat = MockCatalystSystem(empty_rsys; name=:EmptyReactions)
        @test empty_cat isa MockCatalystSystem
```

