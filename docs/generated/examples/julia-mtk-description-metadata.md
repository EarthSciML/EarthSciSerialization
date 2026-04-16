# MTK description metadata (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_metadata_test.jl`

```julia
@testset "_build_description helper" begin
        ext = Base.get_extension(EarthSciSerialization, :EarthSciSerializationMTKExt)
        bd = ext._build_description
        @test bd(nothing, nothing) === nothing
        @test bd("sea level rise", nothing) == "sea level rise"
        @test bd(nothing, "K") == "(units=K)"
        @test bd("sea level rise", "m") == "sea level rise (units=m)"
```

