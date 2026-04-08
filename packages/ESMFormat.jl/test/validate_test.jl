"""
Tests for ESM Format schema validation functionality.
"""

using Test
using ESMFormat

@testset "Schema Validation" begin

    @testset "validate_schema function" begin
        # Test valid ESM data - minimal valid structure
        valid_data = Dict(
            "esm" => "0.1.0",
            "metadata" => Dict(
                "name" => "test-model",
                "description" => "A test model"
            ),
            "models" => Dict(
                "test" => Dict(
                    "variables" => Dict(
                        "x" => Dict("type" => "state")
                    ),
                    "equations" => [
                        Dict("lhs" => "x", "rhs" => 1.0)
                    ]
                )
            )
        )

        errors = validate_schema(valid_data)
        @test isempty(errors)
        @test isa(errors, Vector{ESMFormat.SchemaError})

        # Test invalid data - missing required field
        invalid_data = Dict(
            "esm" => "0.1.0"
            # Missing required metadata field
        )

        errors = validate_schema(invalid_data)
        @test !isempty(errors)
        @test isa(errors, Vector{ESMFormat.SchemaError})
        for error in errors
            @test isa(error.path, String)
            @test isa(error.message, String)
            @test isa(error.keyword, String)
        end
    end

    @testset "SchemaError struct" begin
        error = ESMFormat.SchemaError("/test/path", "Test error message", "required")
        @test error.path == "/test/path"
        @test error.message == "Test error message"
        @test error.keyword == "required"
    end

    @testset "SchemaValidationError exception" begin
        errors = [ESMFormat.SchemaError("/", "Test error", "required")]
        exception = ESMFormat.SchemaValidationError("Validation failed", errors)
        @test exception.message == "Validation failed"
        @test length(exception.errors) == 1
        @test exception.errors[1].path == "/"
    end

    @testset "Integration with load function" begin
        # Test that load function throws SchemaValidationError on invalid schema
        invalid_json = """
        {
            "esm": "0.1.0"
        }
        """

        @test_throws ESMFormat.SchemaValidationError begin
            io = IOBuffer(invalid_json)
            ESMFormat.load(io)
        end
    end

end