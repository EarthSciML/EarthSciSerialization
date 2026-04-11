# 5. ConflictingDerivativeError for explicit D + reaction on same species (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# Model with explicit D(O3)/dt = ...
        mvars = Dict{String, ModelVariable}(
            "O3" => ModelVariable(StateVariable, default=1e-6),
            "k" => ModelVariable(ParameterVariable, default=0.1),
        )
        meqs = [Equation(_deriv("O3"), _op("-", _op("*", _V("k"), _V("O3"))))]
        model = Model(mvars, meqs)

        # Reaction system also touches O3
        species = [EarthSciSerialization.Species("O3", default=1e-6)]
        rate = _V("kr")
        rxns = [EarthSciSerialization.Reaction("r1", nothing,
            [EarthSciSerialization.StoichiometryEntry("O3", 1)], rate)]
        params = [EarthSciSerialization.Parameter("kr", 0.01)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns, parameters=params)

        # Model prefix is "SimpleOzone" and reaction system is also "SimpleOzone"
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t5"),
            models=Dict("SimpleOzone" => model),
            reaction_systems=Dict("SimpleOzone" => rsys))

        # Flatten must throw.
        err = nothing
        try
            flatten(file)
        catch e
            err = e
```

