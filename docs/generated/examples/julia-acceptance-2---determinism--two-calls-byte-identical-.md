# Acceptance 2 — determinism (two calls byte-identical) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _heat_1d_esm(; with_rule=true)
        a = discretize(esm)
        b = discretize(esm)
        # JSON3.write emits object keys in insertion order; to be robust to key
        # ordering we round-trip through canonicalize on the RHS we care about.
        rhs_a = a["models"]["M"]["equations"][1]["rhs"]
        rhs_b = b["models"]["M"]["equations"][1]["rhs"]
        @test canonical_json(EarthSciSerialization.parse_expression(rhs_a)) ==
              canonical_json(EarthSciSerialization.parse_expression(rhs_b))
        # Metadata provenance is deterministic too.
        @test a["metadata"]["discretized_from"] == b["metadata"]["discretized_from"]
```

