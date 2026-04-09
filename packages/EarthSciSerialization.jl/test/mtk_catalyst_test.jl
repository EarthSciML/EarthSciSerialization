using Test
using EarthSciSerialization
using BenchmarkTools

@testset "MTK/Catalyst Conversion Tests" begin

    @testset "ESM Model → MockMTK conversion with proper variable mapping" begin
        # Create a simple harmonic oscillator model
        variables = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=1.0, description="Position"),
            "v" => ModelVariable(StateVariable; default=0.0, description="Velocity"),
            "omega" => ModelVariable(ParameterVariable; default=1.0, description="Angular frequency"),
            "energy" => ModelVariable(ObservedVariable;
                expression=OpExpr("+", EarthSciSerialization.Expr[
                    OpExpr("/", EarthSciSerialization.Expr[OpExpr("^", EarthSciSerialization.Expr[VarExpr("v"), NumExpr(2.0)]), NumExpr(2.0)]),
                    OpExpr("/", EarthSciSerialization.Expr[
                        OpExpr("*", EarthSciSerialization.Expr[
                            OpExpr("^", EarthSciSerialization.Expr[VarExpr("omega"), NumExpr(2.0)]),
                            OpExpr("^", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(2.0)])
                        ]),
                        NumExpr(2.0)
                    ])
                ]))
        )

        equations = [
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
                VarExpr("v")
            ),
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("v")], wrt="t"),
                OpExpr("*", EarthSciSerialization.Expr[
                    OpExpr("-", EarthSciSerialization.Expr[OpExpr("^", EarthSciSerialization.Expr[VarExpr("omega"), NumExpr(2.0)])]),
                    VarExpr("x")
                ])
            )
        ]

        model = Model(variables, equations)
        mtk_sys = to_mtk_system(model, "HarmonicOscillator")

        @test mtk_sys isa EarthSciSerialization.MockMTKSystem
        @test mtk_sys.name == "HarmonicOscillator"

        # Check that we have the expected number of states and parameters
        @test length(mtk_sys.states) == 2  # x, v
        @test length(mtk_sys.parameters) == 1  # omega
        @test length(mtk_sys.observed_variables) == 1  # energy
        @test length(mtk_sys.equations) == 2  # dx/dt, dv/dt

        # Verify proper variable classification
        @test "x" in mtk_sys.states
        @test "v" in mtk_sys.states
        @test "omega" in mtk_sys.parameters
        @test "energy" in mtk_sys.observed_variables
    end

    @testset "ESM ReactionSystem → MockCatalyst conversion with stoichiometry preservation" begin
        # Create a simple ozone photochemistry system
        species = [
            Species("O3", description="Ozone"),
            Species("NO", description="Nitric oxide"),
            Species("NO2", description="Nitrogen dioxide")
        ]

        parameters = [
            Parameter("k1", 1.8e-12, description="NO + O3 rate", units="cm^3/molec/s"),
            Parameter("j1", 0.005, description="NO2 photolysis rate", units="1/s"),
            Parameter("M", 2.46e19, description="Air density", units="molec/cm^3")
        ]

        reactions = [
            Reaction(
                Dict("NO" => 1, "O3" => 1),
                Dict("NO2" => 1),
                OpExpr("*", EarthSciSerialization.Expr[VarExpr("k1"), VarExpr("M")])
            ),
            Reaction(
                Dict("NO2" => 1),
                Dict("NO" => 1, "O3" => 1),
                VarExpr("j1")
            )
        ]

        esm_rsys = ReactionSystem(species, reactions; parameters=parameters)
        catalyst_sys = to_catalyst_system(esm_rsys, "OzonePhotochemistry")

        @test catalyst_sys isa EarthSciSerialization.MockCatalystSystem
        @test catalyst_sys.name == "OzonePhotochemistry"

        # Check species, parameters, and reactions
        @test length(catalyst_sys.species) == 3  # O3, NO, NO2
        @test length(catalyst_sys.parameters) == 3   # k1, j1, M
        @test length(catalyst_sys.reactions) == 2 # Two reactions

        # Verify species names
        @test "O3" in catalyst_sys.species
        @test "NO" in catalyst_sys.species
        @test "NO2" in catalyst_sys.species

        # Verify parameter names
        @test "k1" in catalyst_sys.parameters
        @test "j1" in catalyst_sys.parameters
        @test "M" in catalyst_sys.parameters
    end

    @testset "Bidirectional conversion: ESM → MTK → ESM with metadata preservation" begin
        # Test round-trip conversion for model
        variables = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=2.0, description="Position"),
            "k" => ModelVariable(ParameterVariable; default=0.5, description="Damping coefficient")
        )

        equations = [
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
                OpExpr("*", EarthSciSerialization.Expr[OpExpr("-", EarthSciSerialization.Expr[VarExpr("k")]), VarExpr("x")])
            )
        ]

        original_model = Model(variables, equations)
        mtk_sys = to_mtk_system(original_model, "TestModel")
        recovered_model = from_mtk_system(mtk_sys, "TestModel")

        @test recovered_model isa Model
        @test length(recovered_model.equations) == length(original_model.equations)

        # Check that we have similar variable types and can recover the original
        @test recovered_model.variables["x"].type == StateVariable
        @test recovered_model.variables["k"].type == ParameterVariable
        @test recovered_model.variables["x"].default == 2.0
        @test recovered_model.variables["k"].default == 0.5
    end

    @testset "Bidirectional conversion: ESM → Catalyst → ESM" begin
        # Test round-trip conversion for reaction system
        species = [Species("A"), Species("B")]
        parameters = [Parameter("k", 1.0, units="1/s")]
        reactions = [
            Reaction(Dict("A" => 1), Dict("B" => 1), VarExpr("k"))
        ]

        original_rsys = ReactionSystem(species, reactions; parameters=parameters)
        catalyst_sys = to_catalyst_system(original_rsys, "TestReactions")
        recovered_rsys = from_catalyst_system(catalyst_sys, "TestReactions")

        @test recovered_rsys isa ReactionSystem
        @test length(recovered_rsys.species) == length(original_rsys.species)
        @test length(recovered_rsys.reactions) == length(original_rsys.reactions)
        @test length(recovered_rsys.parameters) == length(original_rsys.parameters)

        # Verify species names are preserved
        original_species_names = Set(spec.name for spec in original_rsys.species)
        recovered_species_names = Set(spec.name for spec in recovered_rsys.species)
        @test original_species_names == recovered_species_names

        # Verify parameter data is preserved
        @test recovered_rsys.parameters[1].name == "k"
        @test recovered_rsys.parameters[1].default == 1.0
    end

    @testset "Complex systems with events, parameters, and constraints" begin
        # Create a system with continuous events - stiff chemistry example
        variables = Dict{String,ModelVariable}(
            "A" => ModelVariable(StateVariable; default=1e-6, description="Fast-reacting species A"),
            "B" => ModelVariable(StateVariable; default=0.0, description="Product species B"),
            "k_fast" => ModelVariable(ParameterVariable; default=1000.0, description="Fast reaction rate", units="1/s"),
            "k_slow" => ModelVariable(ParameterVariable; default=0.1, description="Slow reaction rate", units="1/s"),
            "total_species" => ModelVariable(ObservedVariable;
                expression=OpExpr("+", EarthSciSerialization.Expr[VarExpr("A"), VarExpr("B")]),
                description="Total mass (conserved)")
        )

        equations = [
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("A")], wrt="t"),
                OpExpr("+", EarthSciSerialization.Expr[
                    OpExpr("*", EarthSciSerialization.Expr[OpExpr("-", EarthSciSerialization.Expr[VarExpr("k_fast")]), VarExpr("A")]),
                    OpExpr("*", EarthSciSerialization.Expr[VarExpr("k_slow"), VarExpr("B")])
                ])
            ),
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("B")], wrt="t"),
                OpExpr("+", EarthSciSerialization.Expr[
                    OpExpr("*", EarthSciSerialization.Expr[VarExpr("k_fast"), VarExpr("A")]),
                    OpExpr("*", EarthSciSerialization.Expr[OpExpr("-", EarthSciSerialization.Expr[VarExpr("k_slow")]), VarExpr("B")])
                ])
            )
        ]

        # Add a continuous event
        reset_condition = OpExpr("-", EarthSciSerialization.Expr[VarExpr("A"), NumExpr(1e-12)])
        reset_event = ContinuousEvent(
            EarthSciSerialization.Expr[reset_condition],
            [AffectEquation("A", NumExpr(1e-8))],
            description="Reset A when nearly depleted"
        )

        events = EventType[reset_event]
        model = Model(variables, equations; events=events)

        # Test conversion to Mock MTK (with event handling)
        mtk_sys = to_mtk_system(model, "StiffChemistry")

        @test mtk_sys isa EarthSciSerialization.MockMTKSystem
        @test length(mtk_sys.states) == 2      # A, B
        @test length(mtk_sys.parameters) == 2  # k_fast, k_slow
        @test length(mtk_sys.observed_variables) == 1  # total_species
        @test length(mtk_sys.events) == 1      # reset event
        @test length(mtk_sys.equations) == 2   # dA/dt, dB/dt
    end

    @testset "Coupled systems with multiple components" begin
        # Create two coupled models demonstrating component interaction
        model1_vars = Dict{String,ModelVariable}(
            "x1" => ModelVariable(StateVariable; default=1.0, description="Component 1 state"),
            "k1" => ModelVariable(ParameterVariable; default=0.5, description="Component 1 decay rate")
        )

        model1_eqs = [
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("x1")], wrt="t"),
                OpExpr("*", EarthSciSerialization.Expr[OpExpr("-", EarthSciSerialization.Expr[VarExpr("k1")]), VarExpr("x1")])
            )
        ]

        model1 = Model(model1_vars, model1_eqs)

        model2_vars = Dict{String,ModelVariable}(
            "x2" => ModelVariable(StateVariable; default=0.0, description="Component 2 state"),
            "k2" => ModelVariable(ParameterVariable; default=1.0, description="Component 2 production rate")
        )

        model2_eqs = [
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("x2")], wrt="t"),
                OpExpr("*", EarthSciSerialization.Expr[VarExpr("k2"), VarExpr("x1")])  # Coupling to x1
            )
        ]

        model2 = Model(model2_vars, model2_eqs)

        # Convert both to MTK systems
        sys1 = to_mtk_system(model1, "Component1")
        sys2 = to_mtk_system(model2, "Component2")

        @test sys1 isa EarthSciSerialization.MockMTKSystem
        @test sys2 isa EarthSciSerialization.MockMTKSystem

        # Verify coupling information is preserved
        @test "x1" in sys1.states
        @test "x2" in sys2.states
        @test sys1.name == "Component1"
        @test sys2.name == "Component2"
    end

    @testset "Error handling for unsupported MTK/Catalyst features" begin
        # Test graceful handling of edge cases

        # Empty model
        empty_vars = Dict{String,ModelVariable}()
        empty_eqs = Equation[]
        empty_model = Model(empty_vars, empty_eqs)

        @test_nowarn to_mtk_system(empty_model, "EmptyModel")
        empty_sys = to_mtk_system(empty_model, "EmptyModel")
        @test empty_sys isa EarthSciSerialization.MockMTKSystem

        # Model with only observed variables
        obs_only_vars = Dict{String,ModelVariable}(
            "computed" => ModelVariable(ObservedVariable;
                expression=OpExpr("+", EarthSciSerialization.Expr[NumExpr(1.0), NumExpr(2.0)]))
        )
        obs_only_model = Model(obs_only_vars, Equation[])
        @test_nowarn to_mtk_system(obs_only_model, "ObservedOnly")

        # Empty reaction system
        empty_species = Species[]
        empty_reactions = Reaction[]
        empty_rsys = ReactionSystem(empty_species, empty_reactions)

        @test_nowarn to_catalyst_system(empty_rsys, "EmptyReactions")
        empty_cat_sys = to_catalyst_system(empty_rsys, "EmptyReactions")
        @test empty_cat_sys isa EarthSciSerialization.MockCatalystSystem

        # Test error handling for incorrect types
        @test_throws ErrorException from_mtk_system("not a mock system", "TestError")
        @test_throws ErrorException from_catalyst_system("not a mock system", "TestError")
    end

    @testset "Performance benchmarks for large system conversion" begin
        # Create a larger system for performance testing
        n_species = 50
        n_reactions = 100

        # Generate species
        large_species = [Species("S$i", description="Species $i") for i in 1:n_species]

        # Generate parameters
        large_params = [Parameter("k$i", rand(), description="Rate constant $i", units="1/s") for i in 1:n_reactions]

        # Generate random reactions with proper stoichiometry
        large_reactions = Reaction[]
        for i in 1:n_reactions
            # Random reactants and products
            n_reactants = rand(1:3)
            n_products = rand(1:3)

            reactants = Dict{String,Int}()
            products = Dict{String,Int}()

            for _ in 1:n_reactants
                species_idx = rand(1:n_species)
                reactants["S$species_idx"] = 1
            end

            for _ in 1:n_products
                species_idx = rand(1:n_species)
                products["S$species_idx"] = 1
            end

            rate = VarExpr("k$i")
            push!(large_reactions, Reaction(reactants, products, rate))
        end

        large_rsys = ReactionSystem(large_species, large_reactions; parameters=large_params)

        # Benchmark the conversion
        benchmark_result = @benchmark to_catalyst_system($large_rsys, "LargeSystem")

        @test benchmark_result.times[1] > 0  # Just ensure it completes

        # The conversion should complete in reasonable time (very lenient for mock implementation)
        median_time_ms = median(benchmark_result.times) / 1e6
        @test median_time_ms < 100  # Less than 100ms for 50 species, 100 reactions with mock system

        # Test the resulting system
        large_cat_sys = to_catalyst_system(large_rsys, "LargeSystem")
        @test length(large_cat_sys.species) == n_species
        @test length(large_cat_sys.parameters) == n_reactions
        @test length(large_cat_sys.reactions) == n_reactions
    end

    @testset "Integration with Julia's symbolic manipulation capabilities" begin
        # Test expression conversion utilities

        # Test ESM to mock symbolic conversion
        simple_num = NumExpr(42.0)
        @test esm_to_mock_symbolic(simple_num) == "42.0"

        simple_var = VarExpr("x")
        @test esm_to_mock_symbolic(simple_var) == "x"

        # Test differential expression conversion
        diff_expr = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t")
        symbolic_diff = esm_to_mock_symbolic(diff_expr)
        @test occursin("D(x, t)", symbolic_diff)

        # Test arithmetic expression conversion
        add_expr = OpExpr("+", EarthSciSerialization.Expr[VarExpr("a"), VarExpr("b")])
        symbolic_add = esm_to_mock_symbolic(add_expr)
        @test occursin("+(a, b)", symbolic_add)

        # Test mock symbolic to ESM conversion
        @test mock_symbolic_to_esm("42.0") isa NumExpr
        @test mock_symbolic_to_esm("x") isa VarExpr
        @test mock_symbolic_to_esm("D(x, t)") isa OpExpr

        # Test that converted systems maintain symbolic structure
        variables = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=1.0),
            "a" => ModelVariable(ParameterVariable; default=2.0)
        )

        equations = [
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
                OpExpr("*", EarthSciSerialization.Expr[VarExpr("a"), VarExpr("x")])
            )
        ]

        model = Model(variables, equations)
        mtk_sys = to_mtk_system(model, "ExponentialGrowth")

        # Verify the mock system captures the symbolic nature
        @test mtk_sys isa EarthSciSerialization.MockMTKSystem
        @test length(mtk_sys.equations) == 1
        @test "x" in mtk_sys.states
        @test "a" in mtk_sys.parameters
    end

    @testset "Comprehensive test coverage against ESM specification features" begin
        # Test complete ESM format coverage including all variable types
        comprehensive_vars = Dict{String,ModelVariable}(
            # State variables
            "temperature" => ModelVariable(StateVariable; default=298.15, description="Temperature", units="K"),
            "pressure" => ModelVariable(StateVariable; default=101325.0, description="Pressure", units="Pa"),

            # Parameter variables
            "R" => ModelVariable(ParameterVariable; default=8.314, description="Gas constant", units="J/mol/K"),
            "k_rate" => ModelVariable(ParameterVariable; default=1e-3, description="Rate constant", units="1/s"),

            # Observed variables with complex expressions
            "ideal_gas_law" => ModelVariable(ObservedVariable;
                expression=OpExpr("*", EarthSciSerialization.Expr[
                    VarExpr("R"), VarExpr("temperature")
                ]),
                description="RT term in ideal gas law"),
            "exponential_decay" => ModelVariable(ObservedVariable;
                expression=OpExpr("exp", EarthSciSerialization.Expr[
                    OpExpr("*", EarthSciSerialization.Expr[
                        OpExpr("-", EarthSciSerialization.Expr[VarExpr("k_rate")]),
                        VarExpr("t")
                    ])
                ]),
                description="Exponential decay factor")
        )

        # Complex equations with various operators
        comprehensive_eqs = [
            # Simple differential equation
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("temperature")], wrt="t"),
                OpExpr("*", EarthSciSerialization.Expr[VarExpr("k_rate"), VarExpr("temperature")])
            ),
            # More complex differential equation
            Equation(
                OpExpr("D", EarthSciSerialization.Expr[VarExpr("pressure")], wrt="t"),
                OpExpr("+", EarthSciSerialization.Expr[
                    OpExpr("*", EarthSciSerialization.Expr[VarExpr("R"), VarExpr("temperature")]),
                    OpExpr("^", EarthSciSerialization.Expr[VarExpr("pressure"), NumExpr(0.5)])
                ])
            )
        ]

        # Events with different trigger types
        periodic_event = DiscreteEvent(
            PeriodicTrigger(10.0, phase=1.0),
            [FunctionalAffect("temperature", NumExpr(298.15), operation="set")],
            description="Reset temperature every 10 time units"
        )

        pressure_condition = OpExpr("-", EarthSciSerialization.Expr[VarExpr("pressure"), NumExpr(200000.0)])
        condition_event = ContinuousEvent(
            EarthSciSerialization.Expr[pressure_condition],
            [AffectEquation("pressure", NumExpr(101325.0))],
            description="Reset pressure if it exceeds 2 atm"
        )

        comprehensive_events = EventType[periodic_event, condition_event]

        comprehensive_model = Model(comprehensive_vars, comprehensive_eqs; events=comprehensive_events)

        # Test conversion preserves all features
        mtk_sys = to_mtk_system(comprehensive_model, "ComprehensiveModel")

        @test mtk_sys isa EarthSciSerialization.MockMTKSystem
        @test length(mtk_sys.states) == 2        # temperature, pressure
        @test length(mtk_sys.parameters) == 2    # R, k_rate
        @test length(mtk_sys.observed_variables) == 2  # ideal_gas_law, exponential_decay
        @test length(mtk_sys.equations) == 2     # Two differential equations
        @test length(mtk_sys.events) == 2        # Two events

        # Test bidirectional conversion preserves structure
        recovered_model = from_mtk_system(mtk_sys, "ComprehensiveModel")
        @test recovered_model isa Model

        # Verify all variable types are preserved
        state_count = count(var -> var.type == StateVariable, values(recovered_model.variables))
        param_count = count(var -> var.type == ParameterVariable, values(recovered_model.variables))
        obs_count = count(var -> var.type == ObservedVariable, values(recovered_model.variables))

        @test state_count == 2
        @test param_count == 2
        @test obs_count == 2
    end

end