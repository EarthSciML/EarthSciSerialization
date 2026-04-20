# tree_walk.jl evaluator (gt-e8yw) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
# ========================================================
    # Scalar op coverage
    # ========================================================
    @testset "Arithmetic ops" begin
        @test _eval1(_op("+", _n(1.0), _n(2.0), _n(3.0))) == 6.0
        @test _eval1(_op("-", _n(5.0), _n(2.0))) == 3.0
        @test _eval1(_op("-", _n(4.0))) == -4.0
        @test _eval1(_op("*", _n(2.0), _n(3.0), _n(4.0))) == 24.0
        @test _eval1(_op("/", _n(10.0), _n(4.0))) == 2.5
        @test _eval1(_op("^", _n(2.0), _n(3.0))) == 8.0
        @test _eval1(_op("pow", _n(2.0), _n(3.0))) == 8.0
```

