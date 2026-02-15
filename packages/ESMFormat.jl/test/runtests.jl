using Test
using ESMFormat

@testset "ESMFormat.jl Tests" begin

    include("parse_test.jl")
    # Temporarily disabled due to precompilation issues
    # include("mtk_catalyst_test.jl")
    include("reference_resolution_test.jl")
    include("solver_test.jl")

    @testset "Expression Types" begin
        # Test NumExpr
        num_expr = NumExpr(3.14)
        @test num_expr.value == 3.14
        @test num_expr isa ESMFormat.Expr

        # Test VarExpr
        var_expr = VarExpr("x")
        @test var_expr.name == "x"
        @test var_expr isa ESMFormat.Expr

        # Test OpExpr
        op_expr = OpExpr("+", ESMFormat.Expr[NumExpr(1.0), VarExpr("x")])
        @test op_expr.op == "+"
        @test length(op_expr.args) == 2
        @test op_expr.wrt === nothing
        @test op_expr.dim === nothing
        @test op_expr isa ESMFormat.Expr

        # Test OpExpr with optional parameters
        diff_expr = OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t", dim="time")
        @test diff_expr.wrt == "t"
        @test diff_expr.dim == "time"
    end

    @testset "Equation Types" begin
        # Test Equation
        lhs = OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t")
        rhs = OpExpr("*", ESMFormat.Expr[NumExpr(2.0), VarExpr("x")])
        eq = Equation(lhs, rhs)
        @test eq.lhs == lhs
        @test eq.rhs == rhs

        # Test AffectEquation
        affect_eq = AffectEquation("x", NumExpr(0.0))
        @test affect_eq.lhs == "x"
        @test affect_eq.rhs isa NumExpr
    end

    @testset "ModelVariable Types" begin
        # Test ModelVariableType enum
        @test StateVariable isa ModelVariableType
        @test ParameterVariable isa ModelVariableType
        @test ObservedVariable isa ModelVariableType

        # Test ModelVariable
        mv = ModelVariable(StateVariable, default=1.0, description="Test variable")
        @test mv.type == StateVariable
        @test mv.default == 1.0
        @test mv.description == "Test variable"
        @test mv.expression === nothing
    end

    @testset "Model Component Types" begin
        # Test Species
        species = Species("CO2", molecular_weight=44.01)
        @test species.name == "CO2"
        @test species.molecular_weight == 44.01
        @test species.description === nothing

        # Test Parameter
        param = Parameter("k", 0.1, description="Rate constant", units="1/s")
        @test param.name == "k"
        @test param.default == 0.1
        @test param.description == "Rate constant"
        @test param.units == "1/s"

        # Test Reaction
        reactants = Dict("A" => 1, "B" => 1)
        products = Dict("C" => 1)
        rate = OpExpr("*", ESMFormat.Expr[VarExpr("k"), VarExpr("A"), VarExpr("B")])
        reaction = Reaction(reactants, products, rate)
        @test reaction.reactants == reactants
        @test reaction.products == products
        @test reaction.rate == rate
        @test reaction.reversible == false
    end

    @testset "Event System Types" begin
        # Test DiscreteEventTrigger types
        cond_trigger = ConditionTrigger(VarExpr("x"))
        @test cond_trigger isa DiscreteEventTrigger
        @test cond_trigger.expression isa VarExpr

        periodic_trigger = PeriodicTrigger(10.0, phase=2.0)
        @test periodic_trigger isa DiscreteEventTrigger
        @test periodic_trigger.period == 10.0
        @test periodic_trigger.phase == 2.0

        preset_trigger = PresetTimesTrigger([1.0, 5.0, 10.0])
        @test preset_trigger isa DiscreteEventTrigger
        @test preset_trigger.times == [1.0, 5.0, 10.0]

        # Test FunctionalAffect
        affect = FunctionalAffect("x", NumExpr(1.0), operation="add")
        @test affect.target == "x"
        @test affect.expression isa NumExpr
        @test affect.operation == "add"
    end

    @testset "System Configuration Types" begin
        # Test Reference
        ref = Reference(doi="10.1000/test", citation="Test paper")
        @test ref.doi == "10.1000/test"
        @test ref.citation == "Test paper"
        @test ref.url === nothing
        @test ref.notes === nothing

        # Test Metadata
        metadata = Metadata("test_model",
                          description="A test model",
                          authors=["Test Author"],
                          license="MIT")
        @test metadata.name == "test_model"
        @test metadata.description == "A test model"
        @test metadata.authors == ["Test Author"]
        @test metadata.license == "MIT"

        # Test Domain
        domain = Domain(spatial=Dict("x" => [0.0, 1.0]), temporal=Dict("t" => [0.0, 100.0]))
        @test domain.spatial isa Dict
        @test domain.temporal isa Dict

        # Test Solver (new format)
        solver = Solver("imex", stiff_algorithm="Tsit5")
        solver.config.stiff_kwargs["rtol"] = 1e-8
        @test solver.strategy == IMEX
        @test solver.config.stiff_algorithm == "Tsit5"
        @test solver.config.stiff_kwargs["rtol"] == 1e-8

        # Test EsmFile
        esm_file = EsmFile("0.1.0", metadata)
        @test esm_file.esm == "0.1.0"
        @test esm_file.metadata == metadata
        @test esm_file.models === nothing
        @test esm_file.coupling == []
    end

    @testset "Type Hierarchy" begin
        # Test that all expression types are subtypes of Expr
        @test NumExpr <: ESMFormat.Expr
        @test VarExpr <: ESMFormat.Expr
        @test OpExpr <: ESMFormat.Expr

        # Test that trigger types are subtypes of DiscreteEventTrigger
        @test ConditionTrigger <: DiscreteEventTrigger
        @test PeriodicTrigger <: DiscreteEventTrigger
        @test PresetTimesTrigger <: DiscreteEventTrigger

        # Test that event types are subtypes of EventType
        @test ContinuousEvent <: ESMFormat.EventType
        @test DiscreteEvent <: ESMFormat.EventType
    end
end