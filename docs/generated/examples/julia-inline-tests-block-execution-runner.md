# Inline tests-block execution runner (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tests_blocks_execution_test.jl`

```julia
fixture_path = joinpath(@__DIR__, "..", "..", "..",
                            "tests", "valid",
                            "tests_examples_comprehensive.esm")
    @test isfile(fixture_path)

    file = _ESM_TB.load(fixture_path)
    @test file.models !== nothing

    # Sanity: this runner targets Models with inline tests. The Julia
    # ReactionSystem type does not currently parse `tests`/`tolerance`
    # (tracked by the ReactionSystem-tests follow-up); that branch is
    # schema-only for now.
    any_tests = false
    for (mname, model) in file.models
        isempty(model.tests) && continue
        any_tests = true
        sys = _MTK_TB.System(model; name=Symbol(mname))
        simp = _MTK_TB.mtkcompile(sys)
        for t in model.tests
            @testset "$(mname)/$(t.id)" begin
                _run_one_test(simp, Symbol(mname), model.tolerance, t)
```

