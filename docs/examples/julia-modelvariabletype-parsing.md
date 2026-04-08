# ModelVariableType Parsing (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/parse_test.jl`

```julia
# Test schema values
        @test ESMFormat.parse_model_variable_type("state") == StateVariable
        @test ESMFormat.parse_model_variable_type("parameter") == ParameterVariable
        @test ESMFormat.parse_model_variable_type("observed") == ObservedVariable

        # Test Julia enum values for compatibility
        @test ESMFormat.parse_model_variable_type("StateVariable") == StateVariable
        @test ESMFormat.parse_model_variable_type("ParameterVariable") == ParameterVariable
        @test ESMFormat.parse_model_variable_type("ObservedVariable") == ObservedVariable
```

