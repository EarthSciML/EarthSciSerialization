# Performance: large reaction system mock conversion (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_catalyst_test.jl`

```julia
n_species = 20
        n_reactions = 30
        large_species = [Species("S$i") for i in 1:n_species]
        large_params = [Parameter("k$i", rand()) for i in 1:n_reactions]
        large_reactions = Reaction[]
        for i in 1:n_reactions
            reactants = Dict{String,Int}("S$(rand(1:n_species))" => 1)
            products = Dict{String,Int}("S$(rand(1:n_species))" => 1)
            push!(large_reactions, Reaction(reactants, products, VarExpr("k$i")))
```

