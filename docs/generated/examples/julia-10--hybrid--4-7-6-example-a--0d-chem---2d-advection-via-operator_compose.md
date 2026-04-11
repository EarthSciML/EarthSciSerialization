# 10. HYBRID §4.7.6 Example A: 0D chem + 2D advection via operator_compose (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# Spec §4.7.6 Worked example: 0D chemistry system on a 2D grid is
        # composed with an Advection model whose equations use the `_var`
        # placeholder. Expected result: a single combined equation for each
        # chemistry state variable whose RHS contains BOTH the chemistry rate
        # terms AND the advection terms; indep
```

