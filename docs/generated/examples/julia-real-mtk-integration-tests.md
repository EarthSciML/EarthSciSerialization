# Real MTK Integration Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/real_mtk_integration_test.jl`

```julia
@testset "Real MTK System Creation Verification" begin
        # This test ensures that when ModelingToolkit is available,
        # to_mtk_system creates real MTK systems, not mock systems

        # Check if MTK is available
        mtk_available = check_mtk_availability()

        if !mtk_available
            @test_skip "ModelingToolkit not available - skipping real integration tests"
            return
```

