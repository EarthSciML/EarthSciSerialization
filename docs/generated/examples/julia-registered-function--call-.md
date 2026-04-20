# Registered function (call) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
# Double the argument via a user-supplied handler.
        doubler(x) = 2 * x
        expr = _op("call", _n(21.0); handler_id="double")
        @test _eval1(expr; registered_functions=Dict("double" => doubler)) == 42.0
```

