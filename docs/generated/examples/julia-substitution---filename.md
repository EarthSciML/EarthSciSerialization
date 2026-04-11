# Substitution: $filename (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/runtests.jl`

```julia
try
                            subst_data = JSON3.read(read(filepath, String))

                            # Fixtures are arrays of {input, bindings, expected} cases.
                            # Accept object-with-"tests" shape too for forward compatibility.
                            cases = if subst_data isa JSON3.Array
                                subst_data
                            elseif subst_data isa JSON3.Object && haskey(subst_data, :tests)
                                subst_data[:tests]
                            else
                                []
```

