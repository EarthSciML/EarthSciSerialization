# $id (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_conformance_test.jl`

```julia
obj = JSON3.read(read(path, String))
            rules = parse_rules(obj[:rules])
            input = EarthSciSerialization._parse_expr(obj[:input])
            max_passes = haskey(obj, :max_passes) ? Int(obj[:max_passes]) : 32
            ctx = build_context(obj)

            expect = obj[:expect]
            kind = String(expect[:kind])
            if kind == "output"
                out = rewrite(input, rules, ctx; max_passes=max_passes)
                @test canonical_json(out) == String(expect[:canonical_json])
            elseif kind == "error"
                want_code = String(expect[:code])
                err = try
                    rewrite(input, rules, ctx; max_passes=max_passes)
                    nothing
                catch e
                    e
```

