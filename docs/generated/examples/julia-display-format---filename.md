# Display format: $filename (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/runtests.jl`

```julia
try
                            display_data = JSON3.read(read(filepath, String))

                            # Fixture shape varies: some are flat arrays of cases, some are
                            # objects with a "chemical_formulas" key. Walk whatever structure
                            # we actually get and verify that any "input" expression parses.
                            cases = if display_data isa JSON3.Array
                                display_data
                            elseif display_data isa JSON3.Object && haskey(display_data, :chemical_formulas)
                                display_data[:chemical_formulas]
                            else
                                []
```

