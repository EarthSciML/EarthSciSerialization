# Gradient operator spatial units (gt-sosg) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
# Shared domain + model scaffolding. `c` is the state, `x` the coord
        # we toggle between declared, declared-without-units, and absent.
        metadata = EarthSciSerialization.Metadata("grad-units-test")
        make_model(domain_name::Union{String,Nothing}) = EarthSciSerialization.Model(
            Dict{String,EarthSciSerialization.ModelVariable}(
                "c" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable;
                                                           units="mol/m^3", default=0.0),
                "t" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable;
                                                           units="s", default=1.0),
                "D" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable;
                                                           units="m^2/s", default=0.1),
            ),
            EarthSciSerialization.Equation[
                EarthSciSerialization.Equation(
                    EarthSciSerialization.OpExpr("D",
                        EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("c")];
                        wrt="t"),
                    EarthSciSerialization.OpExpr("*",
                        EarthSciSerialization.Expr[
                            EarthSciSerialization.VarExpr("D"),
                            EarthSciSerialization.OpExpr("grad",
                                EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("c")];
                                dim="x"),
                        ]),
                ),
            ];
            domain=domain_name,
        )

        @testset "Coordinate declared without units emits unit_inconsistency" begin
            domains = Dict("default" => EarthSciSerialization.Domain(
                spatial=Dict{String,Any}("x" => Dict("min" => 0.0, "max" => 10.0))))
            file = EarthSciSerialization.EsmFile("0.1.0", metadata;
                models=Dict("M" => make_model("default")),
                domains=domains)
            errors = EarthSciSerialization.validate_model_gradient_units(file, file.models["M"], "/models/M")
            @test length(errors) == 1
            @test errors[1].error_type == "unit_inconsistency"
            @test errors[1].path == "/models/M/equations/0"
            @test occursin("'x'", errors[1].message)
```

