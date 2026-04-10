# EarthSciSerialization.jl Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/runtests.jl`

```julia
include("parse_test.jl")
    include("validate_test.jl")
    include("structural_validation_test.jl")
    include("expression_test.jl")
    include("reactions_test.jl")
    include("display_test.jl")
    include("units_test.jl")
    include("error_handling_test.jl")
    include("mtk_catalyst_test.jl")
    include("real_mtk_integration_test.jl")
    include("reference_resolution_test.jl")
    include("test_codegen.jl")

    # Comprehensive test suite for full verification
    @testset "Comprehensive Test Suite" begin

        @testset "Valid Fixture Parse Tests" begin
            # Test loading and parsing all valid test fixtures
            valid_fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "valid")

            if isdir(valid_fixtures_dir)
                valid_files = filter(f ->
```

