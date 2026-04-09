# Real MTK System with Events (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/real_mtk_integration_test.jl`

```julia
mtk_available = check_mtk_availability()

        if !mtk_available
            @test_skip "ModelingToolkit not available"
            return
```

