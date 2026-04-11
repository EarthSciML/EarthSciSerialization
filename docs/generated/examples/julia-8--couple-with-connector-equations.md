# 8. couple with connector equations (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
v1 = Dict{String, ModelVariable}("x" => ModelVariable(StateVariable))
        m1 = Model(v1, Equation[Equation(_deriv("x"), _V("x"))])
        v2 = Dict{String, ModelVariable}("y" => ModelVariable(StateVariable))
        m2 = Model(v2, Equation[Equation(_deriv("y"), _V("y"))])

        # Connector equation structured as an already-parsed Equation object.
        connector_eq = Equation(_V("A.x"), _V("B.y"))
        connector = Dict{String, Any}("equations" => [connector_eq])

        coupling = CouplingEntry[CouplingCouple(["A", "B"], connector)]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t8"),
            models=Dict("A" => m1, "B" => m2),
            coupling=coupling)
        flat = flatten(file)

        # The connector equation should appear in the flattened equations.
        found_connector = any(flat.equations) do eq
            eq.lhs isa EarthSciSerialization.VarExpr && eq.lhs.name == "A.x" &&
            eq.rhs isa EarthSciSerialization.VarExpr && eq.rhs.name == "B.y"
```

