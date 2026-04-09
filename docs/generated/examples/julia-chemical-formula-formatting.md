# Chemical Formula Formatting (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/display_test.jl`

```julia
# Test format_chemical_subscripts for unicode
        @test EarthSciSerialization.format_chemical_subscripts("H2O", :unicode) == "H₂O"
        @test EarthSciSerialization.format_chemical_subscripts("CO2", :unicode) == "CO₂"
        @test EarthSciSerialization.format_chemical_subscripts("CH4", :unicode) == "CH₄"
        @test EarthSciSerialization.format_chemical_subscripts("CaCO3", :unicode) == "CaCO₃"
        @test EarthSciSerialization.format_chemical_subscripts("temp", :unicode) == "temp"  # Non-chemical variable unchanged

        # Test format_chemical_subscripts for latex
        @test EarthSciSerialization.format_chemical_subscripts("H2O", :latex) == "\\mathrm{H_{2}O}"
        @test EarthSciSerialization.format_chemical_subscripts("CO2", :latex) == "\\mathrm{CO_{2}}"
        @test EarthSciSerialization.format_chemical_subscripts("NH3", :latex) == "\\mathrm{NH_{3}}"
        @test EarthSciSerialization.format_chemical_subscripts("temp", :latex) == "temp"  # Non-chemical variable unchanged

        # Test format_chemical_subscripts for ascii
        @test EarthSciSerialization.format_chemical_subscripts("H2O", :ascii) == "H2O"   # No subscripts in ASCII
        @test EarthSciSerialization.format_chemical_subscripts("CO2", :ascii) == "CO2"   # No subscripts in ASCII
        @test EarthSciSerialization.format_chemical_subscripts("NH3", :ascii) == "NH3"   # No subscripts in ASCII
        @test EarthSciSerialization.format_chemical_subscripts("temp", :ascii) == "temp" # Non-chemical variable unchanged
```

