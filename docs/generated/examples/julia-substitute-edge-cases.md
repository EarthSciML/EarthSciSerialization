# substitute edge cases (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/expression_test.jl`

```julia
# Substitution semantics (see CONFORMANCE_SPEC.md §2.2.3):
        # - single-pass (non-transitive): bindings are not re-applied to their
        #   own replacements, so circular/self-referential bindings terminate
        # - recursive over AST structure: arbitrary nesting is supported up to
        #   native stack limits
        # - OpExpr nodes with empty args are valid inputs and preserved
        # - null/missing inputs have no Julia equivalent: Expr is a typed union

        # --- Circular references: single-pass, no cycle detection needed ---
        # Mirrors Python test_substitute_circular_reference_detection
        # (test_substitute.py:295). With bindings {x => y, y => x}, substituting
        # `x` yields `y` — the replacement `y` is NOT re-resolved.
        var_x = VarExpr("x")
        var_y = VarExpr("y")
        circular_bindings = Dict{String,EarthSciSerialization.Expr}(
            "x" => var_y,
            "y" => var_x,
        )
        @test substitute(var_x, circular_bindings) === var_y
        @test substitute(var_y, circular_bindings) === var_x

        # Self-referential binding {x => x} must terminate with x unchanged.
        self_bindings = Dict{String,EarthSciSerialization.Expr}("x" => var_x)
        @test substitute(var_x, self_bindings) === var_x

        # Mutual reference within a compound expression: each var rewritten once.
        sum_xy = OpExpr("+", EarthSciSerialization.Expr[var_x, var_y])
        result = substitute(sum_xy, circular_bindings)
        @test result isa OpExpr
        @test result.args[1] === var_y
        @test result.args[2] === var_x

        # Self-reference inside a nested replacement: inner x NOT re-substituted.
        inner_x_plus_one = OpExpr("+", EarthSciSerialization.Expr[var_x, NumExpr(1.0)])
        nested_self = Dict{String,EarthSciSerialization.Expr}("x" => inner_x_plus_one)
        nested_result = substitute(var_x, nested_self)
        @test nested_result isa OpExpr
        @test nested_result.op == "+"
        @test nested_result.args[1] === var_x  # NOT recursed into
        @test nested_result.args[2] == NumExpr(1.0)

        # --- Deep nesting: recursive, bounded only by Julia's stack ---
        # Mirrors Python test_substitute_deep_nesting (test_substitute.py:310);
        # Python uses depth 5, we use a stronger bound.
        depth = 200
        deep_expr = var_x
        for i in 0:(depth - 1)
            deep_expr = OpExpr("+", EarthSciSerialization.Expr[deep_expr, VarExpr("v$i")])
```

