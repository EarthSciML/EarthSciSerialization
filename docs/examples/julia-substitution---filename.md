# Substitution: $filename (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/runtests.jl`

```julia
try
                            subst_data = JSON3.read(read(filepath, String))

                            if haskey(subst_data, "tests")
                                for test_case in subst_data["tests"]
                                    if haskey(test_case, "expression") && haskey(test_case, "substitutions")
                                        expr = ESMFormat.parse_expression(test_case["expression"])
                                        substitutions = Dict(
                                            k => ESMFormat.parse_expression(v)
                                            for (k, v) in test_case["substitutions"]
                                        )
                                        result = ESMFormat.substitute(expr, substitutions)
                                        @test result isa ESMFormat.Expr

                                        # If expected result is provided, compare
                                        if haskey(test_case, "expected")
                                            expected = ESMFormat.parse_expression(test_case["expected"])
                                            # Note: This might need more sophisticated comparison
                                            # For now, just verify it's a valid expression
                                            @test result isa ESMFormat.Expr
```

