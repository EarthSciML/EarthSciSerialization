# Round-trip: $filename (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/runtests.jl`

```julia
try
                            # Load original
                            original = ESMFormat.load(filepath)

                            # Create temp file for round-trip test
                            temp_file = tempname() * ".esm"

                            try
                                # Save and reload
                                ESMFormat.save(temp_file, original)
                                reloaded = ESMFormat.load(temp_file)

                                # Compare key fields
                                @test original.esm == reloaded.esm
                                @test original.metadata.name == reloaded.metadata.name

                                # For files with models, compare model count
                                if !isnothing(original.models) && !isnothing(reloaded.models)
                                    @test length(original.models) == length(reloaded.models)
```

