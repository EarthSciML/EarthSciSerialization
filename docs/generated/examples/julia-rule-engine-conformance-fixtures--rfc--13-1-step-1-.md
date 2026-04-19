# rule engine conformance fixtures (RFC §13.1 Step 1) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_conformance_test.jl`

```julia
fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests",
                            "conformance", "discretization", "infra",
                            "rule_engine")
    manifest_path = joinpath(fixtures_dir, "manifest.json")
    manifest = JSON3.read(read(manifest_path, String))

    function build_context(obj)
        haskey(obj, :context) || return RuleContext()
        cx = obj[:context]
        grids = Dict{String,Dict{String,Any}}()
        if haskey(cx, :grids)
            for (k, v) in pairs(cx[:grids])
                entry = Dict{String,Any}()
                for (k2, v2) in pairs(v)
                    entry[String(k2)] = [String(s) for s in v2]
```

