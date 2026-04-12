# Flatten fixture: $filename (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
try
                        esm_data = EarthSciSerialization.load(filepath)
                        flat = flatten(esm_data)
                        @test flat isa FlattenedSystem
                    catch e
                        if e isa EarthSciSerialization.SchemaValidationError ||
                           e isa EarthSciSerialization.ParseError ||
                           e isa ConflictingDerivativeError ||
                           e isa UnmappedDomainError ||
                           e isa UnsupportedMappingError ||
                           e isa DimensionPromotionError ||
                           e isa DomainUnitMismatchError
                            @test_broken false
                        else
                            @warn "Flatten test failed for $filename: $e"
                            @test false
```

