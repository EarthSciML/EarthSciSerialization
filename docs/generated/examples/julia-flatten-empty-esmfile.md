# Flatten empty EsmFile (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
metadata = Metadata("empty_test")
        file = EsmFile("0.1.0", metadata)
        flat = flatten(file)
        @test isempty(flat.state_variables)
        @test isempty(flat.parameters)
        @test isempty(flat.variables)
        @test isempty(flat.equations)
        @test isempty(flat.metadata.source_systems)
        @test isempty(flat.metadata.coupling_rules)
```

