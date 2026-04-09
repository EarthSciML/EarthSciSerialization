# Display Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/display_test.jl`

```julia
@testset "Utility Functions" begin
        # Test to_subscript
        @test ESMFormat.to_subscript(0) == "₀"
        @test ESMFormat.to_subscript(123) == "₁₂₃"
        @test ESMFormat.to_subscript(5) == "₅"

        # Test to_superscript
        @test ESMFormat.to_superscript("1") == "¹"
        @test ESMFormat.to_superscript("23") == "²³"
        @test ESMFormat.to_superscript("-1") == "⁻¹"
        @test ESMFormat.to_superscript("+2") == "⁺²"

        # Test has_element_pattern
        @test ESMFormat.has_element_pattern("H2O") == true
        @test ESMFormat.has_element_pattern("CO2") == true
        @test ESMFormat.has_element_pattern("NH3") == true
        @test ESMFormat.has_element_pattern("xyz") == false
        @test ESMFormat.has_element_pattern("temp") == false
        @test ESMFormat.has_element_pattern("H") == true
        @test ESMFormat.has_element_pattern("He") == true
```

