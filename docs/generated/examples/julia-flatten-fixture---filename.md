# Flatten fixture: $filename (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
try
                        esm_data = EarthSciSerialization.load(filepath)
                        flat = flatten(esm_data)
                        @test flat isa FlattenedSystem
                        @test flat.metadata isa FlattenMetadata
                    catch e
                        if e isa EarthSciSerialization.SchemaValidationError || e isa EarthSciSerialization.ParseError
                            @test_broken false  # Can't flatten if parsing fails
                        else
                            @warn "Flatten test failed for $filename: $e"
                            @test false
```

