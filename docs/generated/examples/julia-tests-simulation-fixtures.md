# tests/simulation fixtures (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tests_blocks_execution_test.jl`

```julia
for fname in sim_files
                if haskey(simulation_skip, fname)
                    @testset "$(fname) [SKIPPED: $(simulation_skip[fname])]" begin
                        @test_skip false
```

