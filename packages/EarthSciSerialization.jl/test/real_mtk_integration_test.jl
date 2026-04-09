using Test
using EarthSciSerialization

@testset "Real MTK Integration Tests" begin

    @testset "Real MTK System Creation Verification" begin
        # This test ensures that when ModelingToolkit is available,
        # to_mtk_system creates real MTK systems, not mock systems

        # Check if MTK is available
        mtk_available = check_mtk_availability()

        if !mtk_available
            @test_skip "ModelingToolkit not available - skipping real integration tests"
            return
        end

        # Create a simple test model
        vars = Dict(
            "x" => ModelVariable(StateVariable, default=1.0),
            "k" => ModelVariable(ParameterVariable, default=0.5)
        )

        # Simple equation: dx/dt = -k*x
        lhs = OpExpr("D", [VarExpr("x")], wrt="t")
        rhs = OpExpr("*", [OpExpr("-", [VarExpr("k")]), VarExpr("x")])
        eq = Equation(lhs, rhs)

        model = Model(vars, [eq])

        # Test that real MTK system is created when MTK is available
        mtk_sys = to_mtk_system(model, "RealMTKTest")

        # This should NOT be a MockMTKSystem when MTK is available
        @test !(mtk_sys isa EarthSciSerialization.MockMTKSystem)

        # It should be some kind of MTK system type
        type_str = string(typeof(mtk_sys))
        @test occursin("MTK", type_str) ||
              occursin("ODE", type_str) ||
              occursin("System", type_str)

        @info "✅ Successfully created real MTK system of type: $(typeof(mtk_sys))"
    end

    @testset "Real MTK System with Observed Variables" begin
        mtk_available = check_mtk_availability()

        if !mtk_available
            @test_skip "ModelingToolkit not available"
            return
        end

        # Create model with observed variable
        vars = Dict(
            "x" => ModelVariable(StateVariable, default=1.0),
            "k" => ModelVariable(ParameterVariable, default=0.5),
            "energy" => ModelVariable(ObservedVariable,
                expression=OpExpr("*", [NumExpr(0.5), OpExpr("^", [VarExpr("x"), NumExpr(2.0)])]))
        )

        # dx/dt = -k*x
        eq = Equation(
            OpExpr("D", [VarExpr("x")], wrt="t"),
            OpExpr("*", [OpExpr("-", [VarExpr("k")]), VarExpr("x")])
        )

        model = Model(vars, [eq])
        mtk_sys = to_mtk_system(model, "ObservedTest")

        @test !(mtk_sys isa EarthSciSerialization.MockMTKSystem)
        @info "✅ Real MTK system with observed variables created successfully"
    end

    @testset "Real MTK System with Events" begin
        mtk_available = check_mtk_availability()

        if !mtk_available
            @test_skip "ModelingToolkit not available"
            return
        end

        # Create model with discrete event
        vars = Dict(
            "x" => ModelVariable(StateVariable, default=1.0),
            "k" => ModelVariable(ParameterVariable, default=0.1)
        )

        eq = Equation(
            OpExpr("D", [VarExpr("x")], wrt="t"),
            OpExpr("*", [OpExpr("-", [VarExpr("k")]), VarExpr("x")])
        )

        # Add a discrete event that resets x when it gets too small
        trigger = ConditionTrigger(OpExpr("<", [VarExpr("x"), NumExpr(0.1)]))
        affect = FunctionalAffect("x", NumExpr(1.0), operation="set")
        event = DiscreteEvent(trigger, [affect])

        model = Model(vars, [eq]; events=EventType[event])
        mtk_sys = to_mtk_system(model, "EventTest")

        @test !(mtk_sys isa EarthSciSerialization.MockMTKSystem)
        @info "✅ Real MTK system with events created successfully"
    end
end