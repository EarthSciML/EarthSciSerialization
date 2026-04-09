# Display Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/display_test.jl`

```julia
@testset "Utility Functions" begin
        # Test to_subscript
        @test EarthSciSerialization.to_subscript(0) == "₀"
        @test EarthSciSerialization.to_subscript(123) == "₁₂₃"
        @test EarthSciSerialization.to_subscript(5) == "₅"

        # Test to_superscript
        @test EarthSciSerialization.to_superscript("1") == "¹"
        @test EarthSciSerialization.to_superscript("23") == "²³"
        @test EarthSciSerialization.to_superscript("-1") == "⁻¹"
        @test EarthSciSerialization.to_superscript("+2") == "⁺²"

        # Test has_element_pattern
        @test EarthSciSerialization.has_element_pattern("H2O") == true
        @test EarthSciSerialization.has_element_pattern("CO2") == true
        @test EarthSciSerialization.has_element_pattern("NH3") == true
        @test EarthSciSerialization.has_element_pattern("xyz") == false
        @test EarthSciSerialization.has_element_pattern("temp") == false
        @test EarthSciSerialization.has_element_pattern("H") == true
        @test EarthSciSerialization.has_element_pattern("He") == true
```

