# ESM ReactionSystem → MockCatalystSystem constructor preserves stoichiometry (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_catalyst_test.jl`

```julia
species = [
            Species("O3", description="Ozone"),
            Species("NO", description="Nitric oxide"),
            Species("NO2", description="Nitrogen dioxide"),
        ]
        parameters = [
            Parameter("k1", 1.8e-12, description="NO + O3 rate", units="cm^3/molec/s"),
            Parameter("j1", 0.005, description="NO2 photolysis rate", units="1/s"),
            Parameter("M", 2.46e19, description="Air density", units="molec/cm^3"),
        ]
        reactions = [
            Reaction(Dict("NO" => 1, "O3" => 1), Dict("NO2" => 1),
                     OpExpr("*", EarthSciSerialization.Expr[VarExpr("k1"), VarExpr("M")])),
            Reaction(Dict("NO2" => 1), Dict("NO" => 1, "O3" => 1),
                     VarExpr("j1")),
        ]

        rsys = ReactionSystem(species, reactions; parameters=parameters)
        cat_sys = MockCatalystSystem(rsys; name=:OzonePhotochemistry)

        @test cat_sys isa MockCatalystSystem
        @test cat_sys.name == :OzonePhotochemistry
        @test length(cat_sys.species) == 3
        @test length(cat_sys.parameters) == 3
        @test length(cat_sys.reactions) == 2
        @test "O3" in cat_sys.species
        @test "NO" in cat_sys.species
        @test "NO2" in cat_sys.species
        @test "k1" in cat_sys.parameters
```

