# extract returns empty when component not found (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
file = EsmFile("0.1.0", Metadata("t");
                       models=Dict("A" => Model(Dict{String,ModelVariable}(), Equation[])),
                       coupling=CouplingEntry[])
        ex = @test_logs (:warn,) match_mode=:any ESS.extract(file, "Missing")
        @test isempty(ex.models)
        @test isempty(ex.coupling)
```

