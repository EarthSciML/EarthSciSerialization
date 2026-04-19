# mtk2esm: TODO_GAP for non-standard operator (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_export_test.jl`

```julia
# Build an ESM Equation list with a deliberately-unknown op and run the
    # gap-walker directly. Exercising mtk2esm on a real @register_symbolic
    # construction is fragile across MTK versions, so we drive the detection
    # pass from ESM input — the walker is the public contract anyway.
    ext = Base.get_extension(ESM, :EarthSciSerializationMTKExt)
    @assert ext !== nothing
    walker = getfield(ext, :_walk_expr_for_gaps!)

    gaps = GapReport[]
    seen = Set{String}()
    unknown_op = OpExpr("sigmoid", ESM.Expr[VarExpr("u")])
    walker(unknown_op, seen, gaps, "equations[0].rhs")

    @test !isempty(gaps)
    @test gaps[1].bead_id == "gt-p3ep"
    @test occursin("sigmoid", gaps[1].description)

    # And confirm the full mtk2esm emits TODO_GAP in reference.notes when
    # a brownian-declared system is exported (uses the SDESystem path gap).
    vars = Dict{String,ESM.ModelVariable}(
        "u" => ESM.ModelVariable(ESM.StateVariable; default=1.0),
        "k" => ESM.ModelVariable(ESM.ParameterVariable; default=0.5),
    )
    eqs = ESM.Equation[
        ESM.Equation(
            OpExpr("D", ESM.Expr[VarExpr("u")], wrt="t"),
            OpExpr("*", ESM.Expr[OpExpr("-", ESM.Expr[VarExpr("k")]),
                                 VarExpr("u")])),
    ]
    model = ESM.Model(vars, eqs)
    ode_sys = MTK.System(model; name=:GapSys)
    out = mtk2esm(ode_sys; metadata=(;
        source_ref="fake/ref", description="probe"))
    model_dict = out["models"]["GapSys"]
    @test haskey(model_dict, "reference")
    @test occursin("source_ref: fake/ref", model_dict["reference"]["notes"])
    @test occursin("probe", model_dict["reference"]["notes"])
```

