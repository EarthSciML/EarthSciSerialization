# Parse/serialize round trip for all 7 array ops (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/array_ops_test.jl`

```julia
# arrayop
        node1 = ESM2.OpExpr("arrayop", ESM2.Expr[_var("A"), _var("B")];
            output_idx=Any["i", "j"],
            expr_body=_op("*",
                _op("index", _var("A"), _var("i"), _var("k")),
                _op("index", _var("B"), _var("k"), _var("j"))),
            reduce="+")
        j1 = ESM2.serialize_expression(node1)
        @test j1["op"] == "arrayop"
        @test j1["output_idx"] == Any["i", "j"]
        @test j1["reduce"] == "+"
        rt1 = ESM2.parse_expression(j1)
        @test rt1 isa ESM2.OpExpr
        @test rt1.output_idx == Any["i", "j"]
        @test rt1.reduce == "+"
        @test rt1.expr_body isa ESM2.OpExpr

        # makearray
        node2 = ESM2.OpExpr("makearray", ESM2.Expr[];
            regions=[[[1, 2]], [[3, 3]]],
            values=ESM2.Expr[_var("x"), _num(0)])
        j2 = ESM2.serialize_expression(node2)
        rt2 = ESM2.parse_expression(j2)
        @test rt2.regions == [[[1, 2]], [[3, 3]]]
        @test length(rt2.values) == 2

        # index
        node3 = ESM2.OpExpr("index", ESM2.Expr[_var("u"), _num(1), _num(2)])
        j3 = ESM2.serialize_expression(node3)
        rt3 = ESM2.parse_expression(j3)
        @test rt3.op == "index"
        @test length(rt3.args) == 3

        # broadcast
        node4 = ESM2.OpExpr("broadcast", ESM2.Expr[_var("A"), _var("B")]; fn="+")
        rt4 = ESM2.parse_expression(ESM2.serialize_expression(node4))
        @test rt4.fn == "+"

        # reshape
        node5 = ESM2.OpExpr("reshape", ESM2.Expr[_var("A")]; shape=Any[1, 9])
        rt5 = ESM2.parse_expression(ESM2.serialize_expression(node5))
        @test rt5.shape == Any[1, 9]

        # transpose
        node6 = ESM2.OpExpr("transpose", ESM2.Expr[_var("T")]; perm=[2, 0, 1])
        rt6 = ESM2.parse_expression(ESM2.serialize_expression(node6))
        @test rt6.perm == [2, 0, 1]

        # concat
        node7 = ESM2.OpExpr("concat", ESM2.Expr[_var("A"), _var("B")]; axis=1)
        rt7 = ESM2.parse_expression(ESM2.serialize_expression(node7))
        @test rt7.axis == 1
```

