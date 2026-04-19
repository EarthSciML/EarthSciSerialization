# mtk2esm: basic ODESystem export (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_export_test.jl`

```julia
sys = _toy_ode_system()
    out = mtk2esm(sys)

    @test out isa Dict
    @test out["esm"] == "0.1.0"
    @test haskey(out, "metadata")
    @test haskey(out, "models")
    @test haskey(out["models"], "ToyDecay")

    model_dict = out["models"]["ToyDecay"]
    @test haskey(model_dict, "variables")
    @test haskey(model_dict, "equations")

    vars = model_dict["variables"]
    @test haskey(vars, "x")
    @test haskey(vars, "y")
    @test haskey(vars, "z")
    @test haskey(vars, "k1")
    @test haskey(vars, "k2")
    @test haskey(vars, "k3")

    @test vars["x"]["type"] == "state"
    @test vars["k1"]["type"] == "parameter"
    @test vars["x"]["default"] == 1.0
    @test vars["k1"]["default"] == 0.5

    @test length(model_dict["equations"]) == 3

    # Placeholders: tests/examples arrays, reference is omitted when
    # there is nothing to say (default version, no gaps, no source_ref).
    @test model_dict["tests"] == []
    @test model_dict["examples"] == []
```

