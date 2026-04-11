# 14. VALIDATION: UnsupportedRegriddingError type exists and is constructable (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
err = UnsupportedRegriddingError("cubic_spline")
        @test err.strategy == "cubic_spline"
        @test occursin("cubic_spline", sprint(showerror, err))

        # Also cover the remaining two error types.
        dp = DimensionPromotionError("cannot promote")
        @test occursin("cannot promote", sprint(showerror, dp))
        du = DomainUnitMismatchError("T", "K", "degC")
        @test occursin("T", sprint(showerror, du))
```

