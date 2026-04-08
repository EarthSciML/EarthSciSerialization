# Type Hierarchy (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/runtests.jl`

```julia
# Test that all expression types are subtypes of Expr
        @test NumExpr <: ESMFormat.Expr
        @test VarExpr <: ESMFormat.Expr
        @test OpExpr <: ESMFormat.Expr

        # Test that trigger types are subtypes of DiscreteEventTrigger
        @test ConditionTrigger <: DiscreteEventTrigger
        @test PeriodicTrigger <: DiscreteEventTrigger
        @test PresetTimesTrigger <: DiscreteEventTrigger

        # Test that event types are subtypes of EventType
        @test ContinuousEvent <: ESMFormat.EventType
        @test DiscreteEvent <: ESMFormat.EventType
```

