# scalar_explicit — empty-list shape parses as zero dims (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/arrayed_vars_test.jl`

```julia
first, second = roundtrip("scalar_explicit.esm")
        for esm in (first, second)
            mass = varof(esm, "ScalarExplicit", "mass")
            # Empty list and nothing are both valid scalar forms.
            dims = mass.shape === nothing ? 0 : length(mass.shape)
            @test dims == 0
            @test mass.location === nothing
```

