# MTK/Catalyst Mock Conversion Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_catalyst_test.jl`

```julia
@testset "ESM Model → MockMTKSystem constructor preserves variable classification" begin
        # Simple harmonic oscillator
        variables = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=1.0, description="Position"),
            "v" => ModelVariable(StateVariable; default=0.0, description="Velocity"),
            "omega" => ModelVariable(ParameterVariable; default=1.0, description="Angular frequency"),
            "energy" => ModelVariable(ObservedVariable;
                expression=OpExpr("+", EarthSciSerialization.Expr[
                    OpExpr("/", EarthSciSerialization.Expr[OpExpr("^", EarthSciSerialization.Expr[VarExpr("v"), NumExpr(2.0)]), NumExpr(2.0)]),
                    OpExpr("/", EarthSciSerialization.Expr[
                        OpExpr("*", EarthSciSerialization.Expr[
                            OpExpr("^", EarthSciSerialization.Expr[VarExpr("omega"), NumExpr(2.0)]),
                            OpExpr("^", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(2.0)])
                        ]),
                        NumExpr(2.0)
                    ])
                ]))
        )

        equations = [
            Equation(OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
                     VarExpr("v")),
            Equation(OpExpr("D", EarthSciSerialization.Expr[VarExpr("v")], wrt="t"),
                     OpExpr("*", EarthSciSerialization.Expr[
                        OpExpr("-", EarthSciSerialization.Expr[OpExpr("^", EarthSciSerialization.Expr[VarExpr("omega"), NumExpr(2.0)])]),
                        VarExpr("x")]))
        ]

        model = Model(variables, equations)
        mtk_sys = MockMTKSystem(model; name=:HarmonicOscillator)

        @test mtk_sys isa MockMTKSystem
        @test mtk_sys.name == :HarmonicOscillator
        @test length(mtk_sys.state_variables) == 2  # x, v
        @test length(mtk_sys.parameters) == 1        # omega
        @test length(mtk_sys.observed_variables) == 1 # energy
        @test length(mtk_sys.equations) == 3          # dx/dt, dv/dt, energy ~ expr

        # After flatten, names are namespaced with the system name.
        @test "HarmonicOscillator.x" in mtk_sys.state_variables
        @test "HarmonicOscillator.v" in mtk_sys.state_variables
        @test "HarmonicOscillator.omega" in mtk_sys.parameters
        @test "HarmonicOscillator.energy" in mtk_sys.observed_variables
```

