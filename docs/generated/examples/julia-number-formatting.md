# Number Formatting (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/display_test.jl`

```julia
# Test format_number for unicode with small numbers
        @test EarthSciSerialization.format_number(3.14, :unicode) == "3.14"
        @test EarthSciSerialization.format_number(1.0, :unicode) == "1"  # Julia formats 1.0 as "1"
        @test EarthSciSerialization.format_number(-2.5, :unicode) == "-2.5"
        @test EarthSciSerialization.format_number(0, :unicode) == "0"

        # Test format_number for latex with small numbers
        @test EarthSciSerialization.format_number(3.14, :latex) == "3.14"
        @test EarthSciSerialization.format_number(1.0, :latex) == "1"  # Julia formats 1.0 as "1"
        @test EarthSciSerialization.format_number(-2.5, :latex) == "-2.5"
```

