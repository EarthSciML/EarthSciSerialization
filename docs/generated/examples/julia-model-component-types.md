# Model Component Types (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/runtests.jl`

```julia
# Test Species
        species = Species("CO2", units="mol/m^3", default=1e-6)
        @test species.name == "CO2"
        @test species.units == "mol/m^3"
        @test species.default == 1e-6
        @test species.description === nothing

        # Test Parameter
        param = Parameter("k", 0.1, description="Rate constant", units="1/s")
        @test param.name == "k"
        @test param.default == 0.1
        @test param.description == "Rate constant"
        @test param.units == "1/s"

        # Test Reaction
        reactants = Dict("A" => 1, "B" => 1)
        products = Dict("C" => 1)
        rate = OpExpr("*", ESMFormat.Expr[VarExpr("k"), VarExpr("A"), VarExpr("B")])
        reaction = Reaction(reactants, products, rate)
        @test reaction.reactants == reactants
        @test reaction.products == products
        @test reaction.rate == rate
        @test reaction.reversible == false
```

