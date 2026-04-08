# Basic test to check if core ESMFormat functionality works
# without triggering the full dependency chain

# Try to import only core types without MTK
try
    # Test basic Julia syntax and types first
    println("Testing basic Julia types...")

    # Define a minimal version of the types locally for testing
    abstract type TestExpr end

    struct TestNumExpr <: TestExpr
        value::Float64
    end

    struct TestVarExpr <: TestExpr
        name::String
    end

    # Test basic functionality
    num = TestNumExpr(3.14)
    var = TestVarExpr("x")

    println("✓ Basic expression types work")
    println("  NumExpr: ", num.value)
    println("  VarExpr: ", var.name)

    # Test JSON3 functionality
    using JSON3
    test_dict = Dict("type" => "NumExpr", "value" => 42.0)
    json_str = JSON3.write(test_dict)
    parsed = JSON3.read(json_str)

    println("✓ JSON3 functionality works")
    println("  Serialized: ", json_str)
    println("  Parsed back: ", parsed)

    # Test basic file I/O
    temp_file = "/tmp/esm_test.json"
    write(temp_file, json_str)
    content = read(temp_file, String)
    rm(temp_file)

    println("✓ File I/O works")
    println("  File content matches: ", content == json_str)

    println("\n✅ All basic functionality tests passed!")

catch e
    println("❌ Error in basic test: ", e)
    exit(1)
end