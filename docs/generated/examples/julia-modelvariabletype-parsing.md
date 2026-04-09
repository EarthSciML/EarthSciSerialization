# ModelVariableType Parsing (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/parse_test.jl`

```julia
# Test schema values
        @test EarthSciSerialization.parse_model_variable_type("state") == StateVariable
        @test EarthSciSerialization.parse_model_variable_type("parameter") == ParameterVariable
        @test EarthSciSerialization.parse_model_variable_type("observed") == ObservedVariable

        # Test Julia enum values for compatibility
        @test EarthSciSerialization.parse_model_variable_type("StateVariable") == StateVariable
        @test EarthSciSerialization.parse_model_variable_type("ParameterVariable") == ParameterVariable
        @test EarthSciSerialization.parse_model_variable_type("ObservedVariable") == ObservedVariable
```

