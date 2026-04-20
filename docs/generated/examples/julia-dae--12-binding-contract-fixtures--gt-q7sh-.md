# DAE §12 binding contract fixtures (gt-q7sh) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/dae_missing_conformance_test.jl`

```julia
fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests",
                            "conformance", "discretization", "dae_missing")
    manifest_path = joinpath(fixtures_dir, "manifest.json")
    manifest = JSON3.read(read(manifest_path, String))

    # Only Julia is required here; the manifest's bindings_required list is
    # used by the cross-binding harness. This Julia-side test executes every
    # fixture against the in-process `discretize()` and asserts both the
    # DAE-support-enabled and DAE-support-disabled expectations.

    for fx in manifest[:fixtures]
        id = String(fx[:id])
        path = joinpath(fixtures_dir, String(fx[:path]))
        @testset "$id" begin
            obj = JSON3.read(read(path, String))

            # Re-materialize the fixture input as a plain Dict{String,Any}
            # so `discretize()` can mutate safely.
            input = EarthSciSerialization._deep_native(obj[:input])

            for mode_expect in obj[:expect]
                mode = String(mode_expect[:mode])
                kind = String(mode_expect[:kind])

                dae_support = mode == "dae_support_enabled" ? true :
                              mode == "dae_support_disabled" ? false :
                              error("unknown mode: $mode")

                if kind == "output"
                    # Pass a fresh copy each call — discretize() does not
                    # mutate, but the Dict-typed input may be shared across
                    # modes within this loop.
                    fresh = EarthSciSerialization._deep_native(input)
                    out = discretize(fresh; dae_support=dae_support)

                    expected_class = String(mode_expect[:system_class])
                    @test out["metadata"]["system_class"] == expected_class

                    info = out["metadata"]["dae_info"]
                    @test info["algebraic_equation_count"] ==
                          Int(mode_expect[:algebraic_equation_count])

                    want_per_model = mode_expect[:per_model]
                    got_per_model = info["per_model"]
                    @test length(got_per_model) == length(want_per_model)
                    for (mname, count) in pairs(want_per_model)
                        @test got_per_model[String(mname)] == Int(count)
```

