# Complex systems with events, parameters, and constraints (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/mtk_catalyst_test.jl`

```julia
# Create a system with continuous events - stiff chemistry example
        variables = Dict{String,ModelVariable}(
            "A" => ModelVariable(StateVariable; default=1e-6, description="Fast-reacting species A"),
            "B" => ModelVariable(StateVariable; default=0.0, description="Product species B"),
            "k_fast" => ModelVariable(ParameterVariable; default=1000.0, description="Fast reaction rate", units="1/s"),
            "k_slow" => ModelVariable(ParameterVariable; default=0.1, description="Slow reaction rate", units="1/s"),
            "total_species" => ModelVariable(ObservedVariable;
                expression=OpExpr("+", ESMFormat.Expr[VarExpr("A"), VarExpr("B")]),
                description="Total mass (conserved)")
        )

        equations = [
            Equation(
                OpExpr("D", ESMFormat.Expr[VarExpr("A")], wrt="t"),
                OpExpr("+", ESMFormat.Expr[
                    OpExpr("*", ESMFormat.Expr[OpExpr("-", ESMFormat.Expr[VarExpr("k_fast")]), VarExpr("A")]),
                    OpExpr("*", ESMFormat.Expr[VarExpr("k_slow"), VarExpr("B")])
                ])
            ),
            Equation(
                OpExpr("D", ESMFormat.Expr[VarExpr("B")], wrt="t"),
                OpExpr("+", ESMFormat.Expr[
                    OpExpr("*", ESMFormat.Expr[VarExpr("k_fast"), VarExpr("A")]),
                    OpExpr("*", ESMFormat.Expr[OpExpr("-", ESMFormat.Expr[VarExpr("k_slow")]), VarExpr("B")])
                ])
            )
        ]

        # Add a continuous event
        reset_condition = OpExpr("-", ESMFormat.Expr[VarExpr("A"), NumExpr(1e-12)])
        reset_event = ContinuousEvent(
            ESMFormat.Expr[reset_condition],
            [AffectEquation("A", NumExpr(1e-8))],
            description="Reset A when nearly depleted"
        )

        events = EventType[reset_event]
        model = Model(variables, equations; events=events)

        # Test conversion to Mock MTK (with event handling)
        mtk_sys = to_mtk_system(model, "StiffChemistry")

        @test mtk_sys isa ESMFormat.MockMTKSystem
        @test length(mtk_sys.states) == 2      # A, B
        @test length(mtk_sys.parameters) == 2  # k_fast, k_slow
        @test length(mtk_sys.observed_variables) == 1  # total_species
        @test length(mtk_sys.events) == 1      # reset event
        @test length(mtk_sys.equations) == 2   # dA/dt, dB/dt
```

