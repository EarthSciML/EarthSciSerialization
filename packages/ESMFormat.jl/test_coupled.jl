#!/usr/bin/env julia

"""
Test script for the new coupled system assembly functionality.

This tests the implementation from the Julia: Coupled system assembly task.
"""

using ESMFormat

# Create simple test systems
function create_test_models()
    # Model 1: Simple decay
    model1_vars = Dict{String,ModelVariable}(
        "x" => ModelVariable(StateVariable; default=1.0, description="Concentration"),
        "k" => ModelVariable(ParameterVariable; default=0.1, description="Decay rate")
    )

    model1_eqs = [
        Equation(
            OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", ESMFormat.Expr[OpExpr("-", ESMFormat.Expr[VarExpr("k")]), VarExpr("x")])
        )
    ]

    model1 = Model(model1_vars, model1_eqs)

    # Model 2: Simple production
    model2_vars = Dict{String,ModelVariable}(
        "y" => ModelVariable(StateVariable; default=0.0, description="Product"),
        "rate" => ModelVariable(ParameterVariable; default=0.05, description="Production rate")
    )

    model2_eqs = [
        Equation(
            OpExpr("D", ESMFormat.Expr[VarExpr("y")], wrt="t"),
            OpExpr("*", ESMFormat.Expr[VarExpr("rate"), VarExpr("x")])  # Depends on x from model1
        )
    ]

    model2 = Model(model2_vars, model2_eqs)

    return model1, model2
end

function test_coupling_types()
    println("Testing coupling type construction...")

    # Test operator_compose
    compose_coupling = CouplingOperatorCompose(["Model1", "Model2"]; description="Test composition")
    println("✓ CouplingOperatorCompose created successfully")

    # Test variable_map
    var_map = CouplingVariableMap("Model1.x", "Model2.input", "identity"; description="Map x to input")
    println("✓ CouplingVariableMap created successfully")

    # Test operator_apply
    op_apply = CouplingOperatorApply("test_operator"; description="Apply test operator")
    println("✓ CouplingOperatorApply created successfully")

    println("All coupling types constructed successfully!\n")
    return [compose_coupling, var_map, op_apply]
end

function test_to_coupled_system()
    println("Testing to_coupled_system function...")

    # Create test models
    model1, model2 = create_test_models()

    # Create test ESM file with coupling
    metadata = Metadata("Test Coupled System")
    models = Dict("Model1" => model1, "Model2" => model2)

    # Create coupling entries
    coupling_entries = [
        CouplingOperatorCompose(["Model1", "Model2"]; description="Compose the models"),
        CouplingVariableMap("Model1.x", "Model2.x", "identity"; description="Share x variable")
    ]

    esm_file = EsmFile("1.0", metadata; models=models, coupling=coupling_entries)

    # Test the main function
    coupled_system = to_coupled_system(esm_file)

    println("✓ to_coupled_system executed successfully")
    println("✓ Created $(length(coupled_system.systems)) individual systems")
    println("✓ Applied $(length(coupled_system.couplings)) coupling rules")

    # Verify systems were converted
    @assert haskey(coupled_system.systems, "Model1") "Model1 should be in coupled system"
    @assert haskey(coupled_system.systems, "Model2") "Model2 should be in coupled system"
    @assert coupled_system.systems["Model1"] isa MockMTKSystem "Model1 should be MockMTKSystem"
    @assert coupled_system.systems["Model2"] isa MockMTKSystem "Model2 should be MockMTKSystem"

    println("✓ All system conversions verified")

    # Verify couplings were processed
    @assert length(coupled_system.couplings) == 2 "Should have processed 2 coupling entries"

    println("✓ All coupling processing verified")
    println("Coupled system created successfully!\n")

    return coupled_system
end

function test_serialization()
    println("Testing coupling entry serialization...")

    # Create test coupling entries
    couplings = test_coupling_types()

    # Test serialization
    for coupling in couplings
        serialized = serialize_coupling_entry(coupling)
        println("✓ Serialized $(typeof(coupling)): type = $(serialized["type"])")

        # Test round-trip: serialize then parse
        parsed = coerce_coupling_entry(serialized)
        @assert typeof(parsed) == typeof(coupling) "Round-trip should preserve type"
        println("✓ Round-trip successful for $(typeof(coupling))")
    end

    println("All serialization tests passed!\n")
end

function main()
    println("="^60)
    println("Testing Julia Coupled System Assembly Implementation")
    println("="^60)
    println()

    try
        # Test 1: Coupling type construction
        test_coupling_types()

        # Test 2: Serialization round-trip
        test_serialization()

        # Test 3: Main to_coupled_system function
        coupled_system = test_to_coupled_system()

        println("="^60)
        println("ALL TESTS PASSED! ✅")
        println("="^60)
        println()
        println("Summary:")
        println("- Concrete coupling types implemented and working")
        println("- Serialization/parsing round-trip working")
        println("- to_coupled_system function working with mock implementation")
        println("- $(length(coupled_system.systems)) systems processed")
        println("- $(length(coupled_system.couplings)) coupling rules applied")
        println("- Ready for integration with EarthSciMLBase when available")

    catch e
        println("❌ TEST FAILED: $e")
        println("Stacktrace:")
        for (exc, bt) in Base.catch_stack()
            showerror(stdout, exc, bt)
            println()
        end
        return 1
    end

    return 0
end

if abspath(PROGRAM_FILE) == @__FILE__
    exit(main())
end