# add_continuous_event / add_discrete_event / remove_event (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
m = _make_model()

        disc = DiscreteEvent(
            ConditionTrigger(VarExpr("x")),
            [FunctionalAffect("x", NumExpr(0.0))],
            description="reset",
        )
        cont = ContinuousEvent(
            ESS.Expr[VarExpr("x")],
            [AffectEquation("x", NumExpr(1.0))],
            description="bounce",
        )

        m2 = add_discrete_event(m, disc)
        @test length(m2.discrete_events) == 1
        @test m2.discrete_events[1].description == "reset"
        @test length(m2.continuous_events) == 0

        m3 = add_continuous_event(m2, cont)
        @test length(m3.continuous_events) == 1
        @test m3.continuous_events[1].description == "bounce"
        @test length(m3.discrete_events) == 1

        # Remove "reset" (matches the discrete event by description)
        m4 = remove_event(m3, "reset")
        @test length(m4.discrete_events) == 0
        @test length(m4.continuous_events) == 1

        # Remove "bounce" (the continuous event)
        m5 = remove_event(m4, "bounce")
        @test length(m5.discrete_events) == 0
        @test length(m5.continuous_events) == 0

        # Removing a missing event: warning, unchanged
        m6 = @test_logs (:warn,) match_mode=:any remove_event(m5, "ghost")
        @test length(m6.discrete_events) == 0
        @test length(m6.continuous_events) == 0
```

