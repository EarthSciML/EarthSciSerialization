# Inline tests-block execution runner (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tests_blocks_execution_test.jl`

```julia
fixture_path = joinpath(@__DIR__, "..", "..", "..",
                            "tests", "valid",
                            "tests_examples_comprehensive.esm")
    @test isfile(fixture_path)

    any_tests = _execute_fixture_tests(fixture_path; label="tests_examples_comprehensive")
    @test any_tests

    # tests/simulation/ physics fixtures — gt-l5b migrated these from the
    # filesystem-paired `.esm` + `reference_solutions/*.json` convention to
    # inline `tests` blocks. Walk the directory so newly-migrated fixtures
    # are picked up automatically without editing this runner.
    #
    # Known-broken fixtures exercise Julia-binding gaps rather than spec
    # gaps; they stay in the directory (the schema / other bindings can
    # still use them) but are skipped here until the underlying bugs land.
    simulation_skip = Dict(
        # SymbolicContinuousCallback API drift in MTK ext (gt-2ta2).
        "bouncing_ball.esm" => "gt-2ta2",
        # PDE fixtures (spatial indep
```

