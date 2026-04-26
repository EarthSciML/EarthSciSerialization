# Valid fixture: $filename (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/EarthSciSerialization.jl/test/runtests.jl`

```julia
try
                            esm_data = EarthSciSerialization.load(filepath)
                            @test esm_data isa EarthSciSerialization.EsmFile
                            @test !isnothing(esm_data.esm)
                            @test !isnothing(esm_data.metadata)
                            @info "✓ Successfully loaded $filename"
                        catch e
                            @warn "Failed to load valid fixture $filename: $e"
                            @test false
```

