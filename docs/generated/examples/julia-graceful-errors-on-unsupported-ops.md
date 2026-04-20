# Graceful errors on unsupported ops (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
@test_throws ESM.TreeWalkError _eval1(_op("wibble", _n(1.0)))
        @test_throws ESM.TreeWalkError _eval1(_op("arrayop", _n(1.0)))
        @test_throws ESM.TreeWalkError _eval1(_op("grad", _v("x");
                                                  dim="x");
                                               u_vals=Dict("x" => 1.0))
        # D in RHS is an error (LHS-only marker).
        @test_throws ESM.TreeWalkError _eval1(_op("*", _n(1.0),
                                                 _op("D", _v("x"); wrt="t"));
                                              u_vals=Dict("x" => 1.0))
```

