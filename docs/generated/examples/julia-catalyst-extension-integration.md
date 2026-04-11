# Catalyst Extension Integration (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/catalyst_extension_test.jl`

```julia
@testset "Loading Catalyst activates both extensions" begin
        mtk_ext = Base.get_extension(EarthSciSerialization,
                                     :EarthSciSerializationMTKExt)
        cat_ext = Base.get_extension(EarthSciSerialization,
                                     :EarthSciSerializationCatalystExt)
        @test mtk_ext !== nothing
        @test cat_ext !== nothing
        @test hasmethod(Catalyst.ReactionSystem,
                        Tuple{EarthSciSerialization.ReactionSystem})
```

