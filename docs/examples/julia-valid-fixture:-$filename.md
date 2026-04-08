# Valid fixture: $filename (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/runtests.jl`

```julia
try
                            esm_data = ESMFormat.load(filepath)
                            @test esm_data isa ESMFormat.EsmFile
                            @test !isnothing(esm_data.esm)
                            @test !isnothing(esm_data.metadata)
                            @info "✓ Successfully loaded $filename"
                        catch e
                            @warn "Failed to load valid fixture $filename: $e"
                            @test false
```

