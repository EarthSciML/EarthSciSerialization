# infer_array_shapes (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/array_ops_test.jl`

```julia
# Scalar-only: empty dict.
        eq_scalar = ESM2.Equation(
            _op("D", _var("x"); wrt="t"),
            _op("-", _var("x")))
        @test isempty(infer_array_shapes([eq_scalar]))

        # 1D: u[i] over i in 1:5 → u has shape [1:5].
        eq_arr = ESM2.Equation(
            _arrayop1d(_d_index("u", _var("i")), "i", 1, 5),
            _arrayop1d(_op("-", _idx("u", _var("i"))), "i", 1, 5))
        shapes = infer_array_shapes([eq_arr])
        @test haskey(shapes, "u")
        @test shapes["u"] == [1:5]

        # 1D with offset: u[i-1] + u[i+1] where i in 2:9 → u has shape [1:10].
        body = _op("+",
            _idx("u", _op("-", _var("i"), _num(1))),
            _idx("u", _op("+", _var("i"), _num(1))))
        eq_off = ESM2.Equation(
            _arrayop1d(_d_index("u", _var("i")), "i", 2, 9),
            _arrayop1d(body, "i", 2, 9))
        shapes_off = infer_array_shapes([eq_off])
        @test shapes_off["u"] == [1:10]

        # 2D: u[i,j] over i in 1:4, j in 1:3 → shape [1:4, 1:3].
        eq_2d = ESM2.Equation(
            _arrayop2d(_op("D", _idx("u", _var("i"), _var("j")); wrt="t"),
                       "i", 1, 4, "j", 1, 3),
            _arrayop2d(_op("-", _idx("u", _var("i"), _var("j"))),
                       "i", 1, 4, "j", 1, 3))
        shapes_2d = infer_array_shapes([eq_2d])
        @test shapes_2d["u"] == [1:4, 1:3]
```

