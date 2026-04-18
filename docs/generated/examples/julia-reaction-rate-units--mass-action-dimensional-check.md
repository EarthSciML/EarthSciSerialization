# Reaction rate units: mass-action dimensional check (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
metadata = EarthSciSerialization.Metadata("test-rxn-units")

        @testset "Second-order reaction with 1/s rate constant is rejected" begin
            # A + B -> C with concentrations in mol/L but rate constant in 1/s
            # (should be L/(mol*s)). Mirrors tests/invalid/units_reaction_rate_mismatch.esm.
            species = [
                EarthSciSerialization.Species("A"; units="mol/L", default=1.0),
                EarthSciSerialization.Species("B"; units="mol/L", default=1.0),
                EarthSciSerialization.Species("C"; units="mol/L", default=0.0),
            ]
            parameters = [EarthSciSerialization.Parameter("k", 0.1; units="1/s")]
            reactions = [
                EarthSciSerialization.Reaction(
                    "R1",
                    [EarthSciSerialization.StoichiometryEntry("A", 1), EarthSciSerialization.StoichiometryEntry("B", 1)],
                    [EarthSciSerialization.StoichiometryEntry("C", 1)],
                    EarthSciSerialization.VarExpr("k"),
                ),
            ]
            rs = EarthSciSerialization.ReactionSystem(species, reactions; parameters=parameters)
            errors = EarthSciSerialization.validate_reaction_rate_units(rs, "/reaction_systems/Bad")
            @test length(errors) == 1
            @test errors[1].error_type == "unit_inconsistency"
            @test errors[1].path == "/reaction_systems/Bad/reactions/0"
```

