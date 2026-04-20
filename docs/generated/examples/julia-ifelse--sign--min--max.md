# ifelse, sign, min, max (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
@test _eval1(_op("ifelse", _op("<", _n(1.0), _n(2.0)),
                                   _n(10.0), _n(20.0))) == 10.0
        @test _eval1(_op("ifelse", _op(">", _n(1.0), _n(2.0)),
                                   _n(10.0), _n(20.0))) == 20.0
        @test _eval1(_op("sign", _n(-3.0))) == -1.0
        @test _eval1(_op("sign", _n(0.0))) == 0.0
        @test _eval1(_op("sign", _n(42.0))) == 1.0
        @test _eval1(_op("min", _n(3.0), _n(1.0), _n(2.0))) == 1.0
        @test _eval1(_op("max", _n(3.0), _n(5.0), _n(2.0))) == 5.0
```

