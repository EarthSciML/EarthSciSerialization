# Comparisons and logical (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
@test _eval1(_op("<", _n(1.0), _n(2.0))) == 1.0
        @test _eval1(_op("<=", _n(2.0), _n(2.0))) == 1.0
        @test _eval1(_op(">", _n(1.0), _n(2.0))) == 0.0
        @test _eval1(_op(">=", _n(2.0), _n(1.0))) == 1.0
        @test _eval1(_op("==", _n(1.0), _n(1.0))) == 1.0
        @test _eval1(_op("!=", _n(1.0), _n(2.0))) == 1.0
        @test _eval1(_op("and", _op("<", _n(1.0), _n(2.0)),
                                _op("<", _n(2.0), _n(3.0)))) == 1.0
        @test _eval1(_op("or", _op(">", _n(1.0), _n(2.0)),
                               _op("<", _n(2.0), _n(3.0)))) == 1.0
        @test _eval1(_op("not", _op(">", _n(1.0), _n(2.0)))) == 1.0
```

