# 2. Mixed equations + reactions (disjoint species) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0),
            "k" => ModelVariable(ParameterVariable, default=0.1),
        )
        eqs = [Equation(_deriv("T"), _op("*", _V("k"), _V("T")))]
        model = Model(vars, eqs)

        species = [EarthSciSerialization.Species("A", default=1.0)]
        rxns = [EarthSciSerialization.Reaction("r1", nothing,
            [EarthSciSerialization.StoichiometryEntry("A", 1)],
            _N(0.5))]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns)

        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t2"),
            models=Dict("Climate" => model),
            reaction_systems=Dict("Chem" => rsys))
        flat = flatten(file)

        @test haskey(flat.state_variables, "Climate.T")
        @test haskey(flat.state_variables, "Chem.A")
        @test haskey(flat.parameters, "Climate.k")
        @test _find_eq(flat, "Climate.T") !== nothing
        @test _find_eq(flat, "Chem.A") !== nothing
```

