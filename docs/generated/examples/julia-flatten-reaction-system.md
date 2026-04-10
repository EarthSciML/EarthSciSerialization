# Flatten reaction system (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
species = [
            Species("A", default=1.0),
            Species("B", default=0.5)
        ]
        params = [
            Parameter("k1", 0.1, description="Rate constant")
        ]
        rate = OpExpr("*", EarthSciSerialization.Expr[VarExpr("k1"), VarExpr("A")])
        reactions = [
            Reaction("r1",
                     [EarthSciSerialization.StoichiometryEntry("A", 1)],
                     [EarthSciSerialization.StoichiometryEntry("B", 1)],
                     rate, name="A to B")
        ]
        rsys = ReactionSystem(species, reactions, parameters=params)

        rsys_dict = Dict{String, ReactionSystem}("Chemistry" => rsys)
        metadata = Metadata("reaction_test")
        file = EsmFile("0.1.0", metadata, reaction_systems=rsys_dict)

        flat = flatten(file)

        @test "Chemistry.A" in flat.state_variables
        @test "Chemistry.B" in flat.state_variables
        @test "Chemistry.k1" in flat.parameters
        @test flat.variables["Chemistry.A"] == "species"
        @test flat.variables["Chemistry.B"] == "species"
        @test flat.variables["Chemistry.k1"] == "parameter"
        @test length(flat.equations) == 1
        @test flat.equations[1].source_system == "Chemistry"
        @test occursin("Chemistry.k1", flat.equations[1].rhs)
```

