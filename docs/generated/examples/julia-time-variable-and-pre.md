# Time variable and Pre (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
@test _eval1(_v("t"); t=3.5) == 3.5
        @test _eval1(_op("Pre", _v("x")); u_vals=Dict("x" => 2.0)) == 2.0
```

