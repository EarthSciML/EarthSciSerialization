# Reaction with invalid stoichiometry (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
# StoichiometryEntry enforces finite, positive stoichiometry at
            # construction (gt-1e96), so negative values are rejected before
            # validate_structural ever sees them.
            @test_throws ArgumentError EarthSciSerialization.StoichiometryEntry("A", -1)
```

