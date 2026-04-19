using Test
using EarthSciSerialization
using JSON3

@testset "rule engine conformance fixtures (RFC §13.1 Step 1)" begin
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
                end
                grids[String(k)] = entry
            end
        end
        vars = Dict{String,Dict{String,Any}}()
        if haskey(cx, :variables)
            for (k, v) in pairs(cx[:variables])
                entry = Dict{String,Any}()
                for (k2, v2) in pairs(v)
                    entry[String(k2)] = v2 isa AbstractString ? String(v2) : v2
                end
                vars[String(k)] = entry
            end
        end
        return RuleContext(grids, vars)
    end

    for fx in manifest[:fixtures]
        id = String(fx[:id])
        path = joinpath(fixtures_dir, String(fx[:path]))
        @testset "$id" begin
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
                end
                @test err isa RuleEngineError
                @test err !== nothing && err.code == want_code
            else
                error("unknown expect.kind: $kind")
            end
        end
    end
end
