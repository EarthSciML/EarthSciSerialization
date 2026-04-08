using Test
using ESMFormat

@testset "Error Handling Tests" begin

    @testset "Error Codes" begin
        # Test that error codes are defined
        @test ESMFormat.JSON_PARSE_ERROR isa ESMFormat.ErrorCode
        @test ESMFormat.SCHEMA_VALIDATION_ERROR isa ESMFormat.ErrorCode
        @test ESMFormat.UNDEFINED_REFERENCE isa ESMFormat.ErrorCode
        @test ESMFormat.EXPRESSION_PARSE_ERROR isa ESMFormat.ErrorCode
        @test ESMFormat.COUPLING_RESOLUTION_ERROR isa ESMFormat.ErrorCode

        # Test that error codes have expected integer values
        @test Int(ESMFormat.JSON_PARSE_ERROR) == 1001
        @test Int(ESMFormat.SCHEMA_VALIDATION_ERROR) == 1002
        @test Int(ESMFormat.UNDEFINED_REFERENCE) == 2002
        @test Int(ESMFormat.EXPRESSION_PARSE_ERROR) == 3001
    end

    @testset "Error Structures" begin
        # Test ErrorContext creation with keyword arguments
        context = ESMFormat.ErrorContext(
            file_path="test.esm",
            line_number=10,
            column=5
        )
        @test context.file_path == "test.esm"
        @test context.line_number == 10
        @test context.column == 5

        # Test FixSuggestion creation
        suggestion = ESMFormat.FixSuggestion("Try fixing this")
        @test suggestion.description == "Try fixing this"
        @test suggestion.priority == 1  # Default priority

        # Test basic structures exist
        @test ESMFormat.ErrorContext isa DataType
        @test ESMFormat.FixSuggestion isa DataType
        @test ESMFormat.ESMError isa DataType
    end

    @testset "Error Collector" begin
        # Test ErrorCollector functionality - just basic existence
        collector = ESMFormat.ErrorCollector()
        @test ESMFormat.ErrorCollector isa DataType
        @test collector isa ESMFormat.ErrorCollector
    end

    @testset "Performance Profiler" begin
        # Test PerformanceProfiler functionality - basic existence
        profiler = ESMFormat.PerformanceProfiler()
        @test ESMFormat.PerformanceProfiler isa DataType
        @test profiler isa ESMFormat.PerformanceProfiler

        # Test that start_timer! and end_timer! exist as functions
        @test isdefined(ESMFormat, :start_timer!)
        @test isdefined(ESMFormat, :end_timer!)

        # Try to start/end a timer
        ESMFormat.start_timer!(profiler, "test_operation")
        sleep(0.01)  # Small delay
        ESMFormat.end_timer!(profiler, "test_operation")

        # Just check that these functions ran without error
        @test true
    end

    @testset "Function Existence" begin
        # Test that key functions are defined (but may have interface issues)
        @test isdefined(ESMFormat, :ErrorCode)
        @test isdefined(ESMFormat, :ErrorContext)
        @test isdefined(ESMFormat, :FixSuggestion)
        @test isdefined(ESMFormat, :ESMError)
        @test isdefined(ESMFormat, :ErrorCollector)
        @test isdefined(ESMFormat, :PerformanceProfiler)
    end

end