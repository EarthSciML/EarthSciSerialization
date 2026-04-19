# cross-binding conformance fixtures (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
# tests/conformance/canonical/*.json — same fixtures every binding runs.
        using JSON3
        repo_root = abspath(joinpath(@__DIR__, "..", "..", ".."))
        dir = joinpath(repo_root, "tests", "conformance", "canonical")
        manifest = JSON3.read(read(joinpath(dir, "manifest.json"), String))
        fixtures = manifest.fixtures
        @test !isempty(fixtures)

        function wire_to_expr(node)
            if node isa AbstractDict || (node isa JSON3.Object)
                if haskey(node, :op) && haskey(node, :args)
                    args = ESM_Expr[wire_to_expr(a) for a in node[:args]]
                    return OpExpr(String(node[:op]), args)
```

