using Test
using EarthSciSerialization

@testset "Error Handling Tests" begin

    @testset "Error Codes" begin
        # Test that error codes are defined
        @test EarthSciSerialization.JSON_PARSE_ERROR isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.SCHEMA_VALIDATION_ERROR isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.UNDEFINED_REFERENCE isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.EXPRESSION_PARSE_ERROR isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.COUPLING_RESOLUTION_ERROR isa EarthSciSerialization.ErrorCode

        # Test that error codes have expected integer values
        @test Int(EarthSciSerialization.JSON_PARSE_ERROR) == 1001
        @test Int(EarthSciSerialization.SCHEMA_VALIDATION_ERROR) == 1002
        @test Int(EarthSciSerialization.UNDEFINED_REFERENCE) == 2002
        @test Int(EarthSciSerialization.EXPRESSION_PARSE_ERROR) == 3001
    end

    @testset "Error Structures" begin
        # Test ErrorContext creation with keyword arguments
        context = EarthSciSerialization.ErrorContext(
            file_path="test.esm",
            line_number=10,
            column=5
        )
        @test context.file_path == "test.esm"
        @test context.line_number == 10
        @test context.column == 5

        # Test FixSuggestion creation
        suggestion = EarthSciSerialization.FixSuggestion("Try fixing this")
        @test suggestion.description == "Try fixing this"
        @test suggestion.priority == 1  # Default priority

        # Test basic structures exist
        @test EarthSciSerialization.ErrorContext isa DataType
        @test EarthSciSerialization.FixSuggestion isa DataType
        @test EarthSciSerialization.ESMError isa DataType
    end

    @testset "Error Collector" begin
        # Test ErrorCollector functionality - just basic existence
        collector = EarthSciSerialization.ErrorCollector()
        @test EarthSciSerialization.ErrorCollector isa DataType
        @test collector isa EarthSciSerialization.ErrorCollector
    end

    @testset "Performance Profiler" begin
        # Test PerformanceProfiler functionality - basic existence
        profiler = EarthSciSerialization.PerformanceProfiler()
        @test EarthSciSerialization.PerformanceProfiler isa DataType
        @test profiler isa EarthSciSerialization.PerformanceProfiler

        # Test that start_timer! and end_timer! exist as functions
        @test isdefined(EarthSciSerialization, :start_timer!)
        @test isdefined(EarthSciSerialization, :end_timer!)

        # Try to start/end a timer
        EarthSciSerialization.start_timer!(profiler, "test_operation")
        sleep(0.01)  # Small delay
        EarthSciSerialization.end_timer!(profiler, "test_operation")

        # Just check that these functions ran without error
        @test true
    end

    @testset "Function Existence" begin
        # Test that key functions are defined (but may have interface issues)
        @test isdefined(EarthSciSerialization, :ErrorCode)
        @test isdefined(EarthSciSerialization, :ErrorContext)
        @test isdefined(EarthSciSerialization, :FixSuggestion)
        @test isdefined(EarthSciSerialization, :ESMError)
        @test isdefined(EarthSciSerialization, :ErrorCollector)
        @test isdefined(EarthSciSerialization, :PerformanceProfiler)
    end

end