# 6. operator_compose across two models (summed RHS) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# Two models both declaring T with D(T)/dt; compose them.
        vars1 = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable),
            "k" => ModelVariable(ParameterVariable, default=0.1),
        )
        eqs1 = [Equation(_deriv("T"), _op("*", _V("k"), _V("T")))]
        m1 = Model(vars1, eqs1)

        vars2 = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable),
            "j" => ModelVariable(ParameterVariable, default=0.05),
        )
        eqs2 = [Equation(_deriv("T"), _op("*", _V("j"), _V("T")))]
        m2 = Model(vars2, eqs2)

        coupling = CouplingEntry[
            CouplingOperatorCompose(["A", "B"];
                translate=Dict{String,Any}("A.T" => "B.T")),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t6"),
            models=Dict("A" => m1, "B" => m2),
            coupling=coupling)
        flat = flatten(file)

        # After compose we expect a single equation for the canonical dep var
        # (B.T, since A.T was translated to B.T) and none for A.T.
        @test _find_eq(flat, "B.T") !== nothing
        eq = _find_eq(flat, "B.T")
        # Merged RHS MUST reference BOTH A's parameter (k) AND B's parameter (j),
        # i.e. both sides of the summed equation made it through the merge.
        # Using || would mask the case where only one side survived.
        @test _uses_var(eq.rhs, "A.k")
        @test _uses_var(eq.rhs, "B.j")
        # And both state references (A.T and B.T) must appear.
        @test _uses_var(eq.rhs, "A.T")
        @test _uses_var(eq.rhs, "B.T")
        # The top-level RHS should be a sum (+) of the two composed terms.
        @test eq.rhs isa EarthSciSerialization.OpExpr
        @test (eq.rhs::EarthSciSerialization.OpExpr).op == "+"
```

