# 13. VALIDATION: UnmappedDomainError type exists and is constructable (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
err = UnmappedDomainError("src", "tgt")
        @test err.source == "src" && err.target == "tgt"
        @test sprint(showerror, err) |> x -> occursin("UnmappedDomainError", x)
```

