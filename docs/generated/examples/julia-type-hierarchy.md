# Type Hierarchy (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/runtests.jl`

```julia
# Test that all expression types are subtypes of Expr
        @test NumExpr <: EarthSciSerialization.Expr
        @test VarExpr <: EarthSciSerialization.Expr
        @test OpExpr <: EarthSciSerialization.Expr

        # Test that trigger types are subtypes of DiscreteEventTrigger
        @test ConditionTrigger <: DiscreteEventTrigger
        @test PeriodicTrigger <: DiscreteEventTrigger
        @test PresetTimesTrigger <: DiscreteEventTrigger

        # Test that event types are subtypes of EventType
        @test ContinuousEvent <: EarthSciSerialization.EventType
        @test DiscreteEvent <: EarthSciSerialization.EventType
```

