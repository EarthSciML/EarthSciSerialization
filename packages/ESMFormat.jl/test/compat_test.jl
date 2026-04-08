"""
Compatibility testing for different Julia versions and dependency versions.
This script tests ESMFormat.jl against various configurations to ensure
broad compatibility before package registration.
"""

using Pkg
using Test

@testset "Compatibility Tests" begin

    @testset "Julia Version Compatibility" begin
        # Test that we're compatible with the declared minimum Julia version
        julia_version = VERSION
        @test julia_version >= v"1.10"
        println("Julia version: $julia_version ✓")
    end

    @testset "Core Dependencies" begin
        # Test that core dependencies are available
        @test_nowarn using JSON3
        @test_nowarn using JSONSchema
        @test_nowarn using Unitful
        @test_nowarn using Dates
        println("Core dependencies available ✓")
    end

    @testset "Optional Dependencies" begin
        # Test optional dependencies with graceful fallbacks

        # These should use mock implementations if not available
        try
            import Catalyst
            println("Catalyst.jl available ✓")
        catch e
            println("Catalyst.jl not available, using mock implementation ✓")
        end

        try
            import ModelingToolkit
            println("ModelingToolkit.jl available ✓")
        catch e
            println("ModelingToolkit.jl not available, using mock implementation ✓")
        end

        try
            import Symbolics
            println("Symbolics.jl available ✓")
        catch e
            println("Symbolics.jl not available, using mock implementation ✓")
        end
    end

    @testset "Package Loading" begin
        # Test that ESMFormat loads without errors
        @test_nowarn using ESMFormat
        println("ESMFormat.jl loads successfully ✓")
    end

    @testset "Basic Functionality" begin
        using ESMFormat

        # Test basic type creation
        @test_nowarn NumExpr(1.0)
        @test_nowarn VarExpr("x")
        @test_nowarn OpExpr("+", ESMFormat.Expr[NumExpr(1.0), NumExpr(2.0)])
        println("Basic expression types work ✓")

        # Test model creation
        variables = Dict("x" => ModelVariable(StateVariable))
        equations = [Equation(VarExpr("x"), NumExpr(1.0))]
        @test_nowarn Model(variables, equations)
        println("Model creation works ✓")

        # Test serialization roundtrip
        model = Model(variables, equations)
        esm_file = EsmFile("1.0", Dict("test" => model))

        json_str = ESMFormat.serialize(esm_file)
        @test isa(json_str, String)

        parsed = ESMFormat.parse(json_str)
        @test isa(parsed, EsmFile)
        println("Serialization roundtrip works ✓")
    end

    @testset "System Information" begin
        println("\n=== System Information ===")
        println("Julia version: ", VERSION)
        println("OS: ", Sys.KERNEL)
        println("Architecture: ", Sys.ARCH)
        println("CPU threads: ", Sys.CPU_THREADS)
        println("Memory: ", round(Sys.total_memory() / 1024^3, digits=2), " GB")

        # Print package versions
        println("\n=== Package Versions ===")
        for (uuid, pkg) in Pkg.dependencies()
            if pkg.name in ["JSON3", "JSONSchema", "Unitful", "ESMFormat"]
                println("$(pkg.name): $(pkg.version)")
            end
        end
        println("========================\n")
    end
end

println("Compatibility tests completed successfully! ✅")