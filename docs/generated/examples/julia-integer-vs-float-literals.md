# Integer vs float literals (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
@test _eval1(_i(7)) == 7.0
        @test _eval1(_op("+", _i(1), _i(2))) == 3.0
        @test _eval1(_op("*", _i(3), _n(1.5))) == 4.5
```

