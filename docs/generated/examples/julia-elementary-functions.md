# Elementary functions (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
@test _eval1(_op("sin", _n(0.0))) == 0.0
        @test _eval1(_op("cos", _n(0.0))) == 1.0
        @test _eval1(_op("exp", _n(0.0))) == 1.0
        @test _eval1(_op("log", _n(1.0))) == 0.0
        @test _eval1(_op("log10", _n(100.0))) ≈ 2.0
        @test _eval1(_op("sqrt", _n(9.0))) == 3.0
        @test _eval1(_op("abs", _n(-7.5))) == 7.5
        @test _eval1(_op("floor", _n(1.7))) == 1.0
        @test _eval1(_op("ceil", _n(1.3))) == 2.0
        @test _eval1(_op("atan2", _n(1.0), _n(1.0))) ≈ π / 4
```

