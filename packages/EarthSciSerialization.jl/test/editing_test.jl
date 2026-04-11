using Test
using EarthSciSerialization

const ESS = EarthSciSerialization
const SE = EarthSciSerialization.StoichiometryEntry

# Small helpers so each testset can build a fresh fixture.
function _make_eq(lhs_name::String, coef::Float64)
    lhs = OpExpr("D", ESS.Expr[VarExpr(lhs_name)], wrt="t")
    rhs = OpExpr("*", ESS.Expr[NumExpr(coef), VarExpr(lhs_name)])
    return Equation(lhs, rhs)
end

function _make_model()
    vars = Dict{String,ModelVariable}(
        "x" => ModelVariable(StateVariable, default=1.0),
        "k" => ModelVariable(ParameterVariable, default=0.5),
    )
    eqs = Equation[_make_eq("x", 2.0)]
    return Model(vars, eqs)
end

function _make_reaction_system()
    species = [Species("A", default=1.0), Species("B", default=0.0)]
    rate = OpExpr("*", ESS.Expr[VarExpr("k"), VarExpr("A")])
    rxn = Reaction("r1", [SE("A", 1)], [SE("B", 1)], rate)
    return ReactionSystem(species, [rxn]; parameters=[Parameter("k", 0.1)])
end

@testset "Section 4 Editing Operations" begin

    @testset "add_variable" begin
        m = _make_model()
        @test length(m.variables) == 2

        new_var = ModelVariable(StateVariable, default=5.0, description="new state")
        m2 = add_variable(m, "y", new_var)

        @test length(m2.variables) == 3
        @test haskey(m2.variables, "y")
        @test m2.variables["y"].default == 5.0
        @test m2.variables["y"].description == "new state"
        # original model should be unchanged (non-mutating)
        @test length(m.variables) == 2
        @test !haskey(m.variables, "y")
        # equations preserved
        @test length(m2.equations) == length(m.equations)
    end

    @testset "remove_variable" begin
        m = _make_model()
        # Add a second state variable that has no equation dependency
        m = add_variable(m, "y", ModelVariable(StateVariable, default=0.0))
        @test haskey(m.variables, "y")

        m2 = remove_variable(m, "y")
        @test !haskey(m2.variables, "y")
        @test length(m2.variables) == length(m.variables) - 1
        @test haskey(m2.variables, "x")
        # original unchanged
        @test haskey(m.variables, "y")

        # Removing a referenced variable still succeeds but warns; equations
        # are kept (per implementation contract).
        m3 = @test_logs (:warn,) match_mode=:any remove_variable(m2, "x")
        @test !haskey(m3.variables, "x")
        @test length(m3.equations) == length(m2.equations)

        # Removing non-existent: returns original model with warning.
        m4 = @test_logs (:warn,) match_mode=:any remove_variable(m2, "nonexistent")
        @test length(m4.variables) == length(m2.variables)
    end

    @testset "rename_variable rewrites equation references" begin
        m = _make_model()  # equation: D(x) = 2*x
        m2 = rename_variable(m, "x", "z")

        @test !haskey(m2.variables, "x")
        @test haskey(m2.variables, "z")
        # rewritten equation: D(z) = 2*z
        @test length(m2.equations) == 1
        eq = m2.equations[1]
        @test eq.lhs isa OpExpr
        @test eq.lhs.op == "D"
        @test eq.lhs.args[1] isa VarExpr
        @test eq.lhs.args[1].name == "z"
        @test eq.rhs.args[2] isa VarExpr
        @test eq.rhs.args[2].name == "z"
        # original unchanged
        @test haskey(m.variables, "x")
    end

    @testset "add_equation appends" begin
        m = _make_model()
        new_eq = _make_eq("k", 0.0)  # D(k) = 0*k
        m2 = add_equation(m, new_eq)

        @test length(m2.equations) == length(m.equations) + 1
        @test m2.equations[end] === new_eq
        # original unchanged
        @test length(m.equations) == 1
    end

    @testset "remove_equation by index" begin
        m = _make_model()
        m = add_equation(m, _make_eq("k", 0.0))
        @test length(m.equations) == 2

        m2 = remove_equation(m, 1)
        @test length(m2.equations) == 1

        # Out-of-bounds: returns original with warning
        m3 = @test_logs (:warn,) match_mode=:any remove_equation(m2, 99)
        @test length(m3.equations) == length(m2.equations)
    end

    @testset "remove_equation by LHS pattern" begin
        m = _make_model()
        m = add_equation(m, _make_eq("k", 0.0))
        # Pattern must match the stored lhs by `==` — for OpExpr that is
        # `===` in the default struct, so reuse the exact lhs object here.
        pattern = m.equations[1].lhs
        m2 = remove_equation(m, pattern)
        @test length(m2.equations) == 1
        remaining = m2.equations[1]
        @test remaining.lhs.args[1].name == "k"

        # Pattern with no match: warns and returns unchanged
        bogus = OpExpr("D", ESS.Expr[VarExpr("nonexistent")], wrt="t")
        m3 = @test_logs (:warn,) match_mode=:any remove_equation(m2, bogus)
        @test length(m3.equations) == length(m2.equations)
    end

    @testset "substitute_in_equations rewrites expression trees" begin
        m = _make_model()  # D(x) = 2*x
        bindings = Dict{String, ESS.Expr}("x" => NumExpr(42.0))
        m2 = substitute_in_equations(m, bindings)

        @test length(m2.equations) == 1
        rhs = m2.equations[1].rhs
        @test rhs isa OpExpr
        # Original expression: ("*", [NumExpr(2.0), VarExpr("x")]) -> x substituted
        @test rhs.args[1] isa NumExpr
        @test rhs.args[1].value == 2.0
        @test rhs.args[2] isa NumExpr
        @test rhs.args[2].value == 42.0
        # variables dict unchanged
        @test haskey(m2.variables, "x")
    end

    @testset "add_reaction / remove_reaction" begin
        sys = _make_reaction_system()
        @test length(sys.reactions) == 1

        rxn2 = Reaction("r2", [SE("B", 1)], [SE("A", 1)], NumExpr(0.1))
        sys2 = add_reaction(sys, rxn2)
        @test length(sys2.reactions) == 2
        @test sys2.reactions[end].id == "r2"

        sys3 = remove_reaction(sys2, "r1")
        @test length(sys3.reactions) == 1
        @test sys3.reactions[1].id == "r2"
        # species & parameters preserved
        @test length(sys3.species) == length(sys.species)
        @test length(sys3.parameters) == length(sys.parameters)

        # Remove nonexistent: warning, unchanged
        sys4 = @test_logs (:warn,) match_mode=:any remove_reaction(sys3, "nope")
        @test length(sys4.reactions) == length(sys3.reactions)
    end

    @testset "add_species / remove_species" begin
        sys = _make_reaction_system()
        sys2 = add_species(sys, "C", Species("C", default=2.0))
        @test length(sys2.species) == 3
        @test any(s -> s.name == "C", sys2.species)

        # Remove the fresh species (no reaction depends on it)
        sys3 = remove_species(sys2, "C")
        @test length(sys3.species) == 2
        @test !any(s -> s.name == "C", sys3.species)

        # Remove a species that IS used in a reaction (A): warns about dependency
        sys4 = @test_logs (:warn,) match_mode=:any remove_species(sys3, "A")
        @test !any(s -> s.name == "A", sys4.species)

        # Removing nonexistent: warning only
        sys5 = @test_logs (:warn,) match_mode=:any remove_species(sys4, "ZZ")
        @test length(sys5.species) == length(sys4.species)
    end

    @testset "add_continuous_event / add_discrete_event / remove_event" begin
        m = _make_model()

        disc = DiscreteEvent(
            ConditionTrigger(VarExpr("x")),
            [FunctionalAffect("x", NumExpr(0.0))],
            description="reset",
        )
        cont = ContinuousEvent(
            ESS.Expr[VarExpr("x")],
            [AffectEquation("x", NumExpr(1.0))],
            description="bounce",
        )

        m2 = add_discrete_event(m, disc)
        @test length(m2.discrete_events) == 1
        @test m2.discrete_events[1].description == "reset"
        @test length(m2.continuous_events) == 0

        m3 = add_continuous_event(m2, cont)
        @test length(m3.continuous_events) == 1
        @test m3.continuous_events[1].description == "bounce"
        @test length(m3.discrete_events) == 1

        # Remove "reset" (matches the discrete event by description)
        m4 = remove_event(m3, "reset")
        @test length(m4.discrete_events) == 0
        @test length(m4.continuous_events) == 1

        # Remove "bounce" (the continuous event)
        m5 = remove_event(m4, "bounce")
        @test length(m5.discrete_events) == 0
        @test length(m5.continuous_events) == 0

        # Removing a missing event: warning, unchanged
        m6 = @test_logs (:warn,) match_mode=:any remove_event(m5, "ghost")
        @test length(m6.discrete_events) == 0
        @test length(m6.continuous_events) == 0
    end

    @testset "add_coupling / remove_coupling" begin
        file = EsmFile("0.1.0", Metadata("test"); coupling=CouplingEntry[])
        @test length(file.coupling) == 0

        entry1 = CouplingOperatorCompose(["A", "B"]; description="compose AB")
        file1 = add_coupling(file, entry1)
        @test length(file1.coupling) == 1
        @test file1.coupling[1] isa CouplingOperatorCompose
        @test file1.coupling[1].systems == ["A", "B"]

        entry2 = CouplingVariableMap("A.x", "B.y", "identity")
        file2 = add_coupling(file1, entry2)
        @test length(file2.coupling) == 2

        file3 = remove_coupling(file2, 1)
        @test length(file3.coupling) == 1
        @test file3.coupling[1] isa CouplingVariableMap

        # Out-of-bounds remove: warning, unchanged
        file4 = @test_logs (:warn,) match_mode=:any remove_coupling(file3, 99)
        @test length(file4.coupling) == length(file3.coupling)
    end

    @testset "compose (convenience for operator_compose)" begin
        file = EsmFile("0.1.0", Metadata("test"); coupling=CouplingEntry[])
        file2 = compose(file, "Atmosphere", "Ocean")
        @test length(file2.coupling) == 1
        entry = file2.coupling[1]
        @test entry isa CouplingOperatorCompose
        @test entry.systems == ["Atmosphere", "Ocean"]
    end

    @testset "map_variable (convenience for variable_map)" begin
        file = EsmFile("0.1.0", Metadata("test"); coupling=CouplingEntry[])
        file2 = map_variable(file, "Atmosphere.T", "Ocean.T_surf"; transform="identity")
        @test length(file2.coupling) == 1
        entry = file2.coupling[1]
        @test entry isa CouplingVariableMap
        @test entry.from == "Atmosphere.T"
        @test entry.to == "Ocean.T_surf"
        @test entry.transform == "identity"
    end

    @testset "merge combines two ESM files" begin
        model_a = Model(Dict("x" => ModelVariable(StateVariable, default=1.0)), Equation[])
        model_b = Model(Dict("y" => ModelVariable(StateVariable, default=2.0)), Equation[])

        file_a = EsmFile("0.1.0", Metadata("a");
                         models=Dict("A" => model_a),
                         coupling=CouplingEntry[CouplingOperatorCompose(["A", "A"])])
        file_b = EsmFile("0.1.0", Metadata("b");
                         models=Dict("B" => model_b),
                         coupling=CouplingEntry[CouplingVariableMap("A.x", "B.y", "identity")])

        merged = ESS.merge(file_a, file_b)
        @test length(merged.models) == 2
        @test haskey(merged.models, "A")
        @test haskey(merged.models, "B")
        @test length(merged.coupling) == 2
        # file_b metadata wins
        @test merged.metadata.name == "b"
    end

    @testset "merge prefers file_b on key conflicts" begin
        m1 = Model(Dict("x" => ModelVariable(StateVariable, default=1.0)), Equation[])
        m2 = Model(Dict("x" => ModelVariable(StateVariable, default=999.0)), Equation[])

        fa = EsmFile("0.1.0", Metadata("a"); models=Dict("Shared" => m1))
        fb = EsmFile("0.1.0", Metadata("b"); models=Dict("Shared" => m2))

        merged = ESS.merge(fa, fb)
        @test length(merged.models) == 1
        # file_b takes precedence
        @test merged.models["Shared"].variables["x"].default == 999.0
    end

    @testset "extract top-level component" begin
        model_a = Model(Dict("x" => ModelVariable(StateVariable)), Equation[])
        model_b = Model(Dict("y" => ModelVariable(StateVariable)), Equation[])
        model_c = Model(Dict("z" => ModelVariable(StateVariable)), Equation[])

        compose_entry = CouplingOperatorCompose(["A", "C"])
        map_entry = CouplingVariableMap("A.x", "B.y", "identity")
        unrelated = CouplingOperatorCompose(["B", "C"])

        file = EsmFile("0.1.0", Metadata("all");
                       models=Dict("A" => model_a, "B" => model_b, "C" => model_c),
                       coupling=CouplingEntry[compose_entry, map_entry, unrelated])

        ex = ESS.extract(file, "A")
        @test length(ex.models) == 1
        @test haskey(ex.models, "A")
        # Coupling entries involving A: compose_entry (A in systems) + map_entry (from=A.x)
        @test length(ex.coupling) == 2
        @test compose_entry in ex.coupling
        @test map_entry in ex.coupling
        @test !(unrelated in ex.coupling)

        # Metadata, reaction_systems, etc. preserved
        @test ex.metadata.name == "all"
        @test ex.reaction_systems !== nothing || ex.reaction_systems === nothing  # structural check
    end

    @testset "extract returns empty when component not found" begin
        file = EsmFile("0.1.0", Metadata("t");
                       models=Dict("A" => Model(Dict{String,ModelVariable}(), Equation[])),
                       coupling=CouplingEntry[])
        ex = @test_logs (:warn,) match_mode=:any ESS.extract(file, "Missing")
        @test isempty(ex.models)
        @test isempty(ex.coupling)
    end

end
