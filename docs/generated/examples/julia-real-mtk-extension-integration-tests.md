# Real MTK Extension Integration Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/real_mtk_integration_test.jl`

```julia
@testset "Extension loads and registers System constructor" begin
        ext = Base.get_extension(EarthSciSerialization, :EarthSciSerializationMTKExt)
        @test ext !== nothing
        @test hasmethod(ModelingToolkit.System,
                        Tuple{EarthSciSerialization.Model})
        @test hasmethod(ModelingToolkit.System,
                        Tuple{EarthSciSerialization.FlattenedSystem})
        @test hasmethod(ModelingToolkit.PDESystem,
                        Tuple{EarthSciSerialization.FlattenedSystem})
```

