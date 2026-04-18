# Correctly-dimensioned second-order rate constant passes (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
species = [
                EarthSciSerialization.Species("A"; units="mol/L", default=1.0),
                EarthSciSerialization.Species("B"; units="mol/L", default=1.0),
                EarthSciSerialization.Species("C"; units="mol/L", default=0.0),
            ]
            parameters = [EarthSciSerialization.Parameter("k", 0.1; units="L/(mol*s)")]
            reactions = [
                EarthSciSerialization.Reaction(
                    "R1",
                    [EarthSciSerialization.StoichiometryEntry("A", 1), EarthSciSerialization.StoichiometryEntry("B", 1)],
                    [EarthSciSerialization.StoichiometryEntry("C", 1)],
                    EarthSciSerialization.VarExpr("k"),
                ),
            ]
            rs = EarthSciSerialization.ReactionSystem(species, reactions; parameters=parameters)
            errors = EarthSciSerialization.validate_reaction_rate_units(rs, "/reaction_systems/Good")
            @test isempty(errors)
```

