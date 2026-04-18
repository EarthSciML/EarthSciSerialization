# substitute fixtures (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/expression_test.jl`

```julia
# Fixture-driven cases shared with Rust (packages/earthsci-toolkit-rs/tests/substitution.rs)
        # and Python (packages/earthsci_toolkit/tests/test_substitute.py). A new fixture case
        # lights up all three bindings at once.
        fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "substitution")
        fixture_files = ["simple_var_replace.json", "nested_substitution.json", "scoped_reference.json"]

        for filename in fixture_files
            filepath = joinpath(fixtures_dir, filename)
            @testset "$filename" begin
                @test isfile(filepath)
                cases = JSON3.read(read(filepath, String))
                @test cases isa JSON3.Array
                @test !isempty(cases)

                for (i, case) in enumerate(cases)
                    label = haskey(case, :description) ? String(case[:description]) : "case $i"
                    @testset "$label" begin
                        input_expr = EarthSciSerialization.parse_expression(case[:input])
                        bindings = Dict{String,EarthSciSerialization.Expr}(
                            string(k) => EarthSciSerialization.parse_expression(v)
                            for (k, v) in pairs(case[:bindings])
                        )
                        expected = EarthSciSerialization.parse_expression(case[:expected])
                        result = substitute(input_expr, bindings)
                        # Expr structs have no `==` method, so compare via the
                        # canonical JSON-serialized form.
                        @test EarthSciSerialization.serialize_expression(result) ==
                              EarthSciSerialization.serialize_expression(expected)
```

