@testset "Flatten System Tests" begin

    @testset "FlattenedEquation construction" begin
        eq = FlattenedEquation("Atm.T", "Atm.k * Atm.T", "Atm")
        @test eq.lhs == "Atm.T"
        @test eq.rhs == "Atm.k * Atm.T"
        @test eq.source_system == "Atm"
    end

    @testset "FlattenMetadata construction" begin
        meta = FlattenMetadata(["Atm", "Ocean"], ["operator_compose(Atm + Ocean)"])
        @test meta.source_systems == ["Atm", "Ocean"]
        @test length(meta.coupling_rules) == 1
    end

    @testset "FlattenedSystem construction" begin
        fs = FlattenedSystem(
            ["Atm.T"],
            ["Atm.k"],
            Dict("Atm.T" => "state", "Atm.k" => "parameter"),
            [FlattenedEquation("Atm.T", "Atm.k * Atm.T", "Atm")],
            FlattenMetadata(["Atm"], String[])
        )
        @test length(fs.state_variables) == 1
        @test length(fs.parameters) == 1
        @test fs.variables["Atm.T"] == "state"
        @test fs.variables["Atm.k"] == "parameter"
    end

    @testset "Flatten empty EsmFile" begin
        metadata = Metadata("empty_test")
        file = EsmFile("0.1.0", metadata)
        flat = flatten(file)
        @test isempty(flat.state_variables)
        @test isempty(flat.parameters)
        @test isempty(flat.variables)
        @test isempty(flat.equations)
        @test isempty(flat.metadata.source_systems)
        @test isempty(flat.metadata.coupling_rules)
    end

    @testset "Flatten single model" begin
        vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0, description="Temperature"),
            "k" => ModelVariable(ParameterVariable, default=0.1),
            "obs" => ModelVariable(ObservedVariable)
        )

        lhs = OpExpr("D", EarthSciSerialization.Expr[VarExpr("T")], wrt="t")
        rhs = OpExpr("*", EarthSciSerialization.Expr[VarExpr("k"), VarExpr("T")])
        eqs = [Equation(lhs, rhs)]

        model = Model(vars, eqs)
        models = Dict{String, Model}("Atmosphere" => model)
        metadata = Metadata("single_model_test")
        file = EsmFile("0.1.0", metadata, models=models)

        flat = flatten(file)

        @test "Atmosphere.T" in flat.state_variables
        @test "Atmosphere.k" in flat.parameters
        @test flat.variables["Atmosphere.T"] == "state"
        @test flat.variables["Atmosphere.k"] == "parameter"
        @test flat.variables["Atmosphere.obs"] == "observed"
        @test length(flat.equations) == 1
        @test flat.equations[1].source_system == "Atmosphere"
        @test occursin("Atmosphere.T", flat.equations[1].lhs)
        @test occursin("Atmosphere.k", flat.equations[1].rhs)
        @test "Atmosphere" in flat.metadata.source_systems
    end

    @testset "Flatten model with subsystems" begin
        # Inner subsystem
        inner_vars = Dict{String, ModelVariable}(
            "x" => ModelVariable(StateVariable, default=1.0)
        )
        inner_model = Model(inner_vars, Equation[])

        # Outer model with subsystem
        outer_vars = Dict{String, ModelVariable}(
            "y" => ModelVariable(StateVariable, default=2.0)
        )
        outer_model = Model(outer_vars, Equation[],
                           subsystems=Dict{String, Model}("Inner" => inner_model))

        models = Dict{String, Model}("Outer" => outer_model)
        metadata = Metadata("subsystem_test")
        file = EsmFile("0.1.0", metadata, models=models)

        flat = flatten(file)

        @test "Outer.y" in flat.state_variables
        @test "Outer.Inner.x" in flat.state_variables
        @test flat.variables["Outer.y"] == "state"
        @test flat.variables["Outer.Inner.x"] == "state"
    end

    @testset "Flatten reaction system" begin
        species = [
            Species("A", default=1.0),
            Species("B", default=0.5)
        ]
        params = [
            Parameter("k1", 0.1, description="Rate constant")
        ]
        rate = OpExpr("*", EarthSciSerialization.Expr[VarExpr("k1"), VarExpr("A")])
        reactions = [
            Reaction("r1",
                     [EarthSciSerialization.StoichiometryEntry("A", 1)],
                     [EarthSciSerialization.StoichiometryEntry("B", 1)],
                     rate, name="A to B")
        ]
        rsys = ReactionSystem(species, reactions, parameters=params)

        rsys_dict = Dict{String, ReactionSystem}("Chemistry" => rsys)
        metadata = Metadata("reaction_test")
        file = EsmFile("0.1.0", metadata, reaction_systems=rsys_dict)

        flat = flatten(file)

        @test "Chemistry.A" in flat.state_variables
        @test "Chemistry.B" in flat.state_variables
        @test "Chemistry.k1" in flat.parameters
        @test flat.variables["Chemistry.A"] == "species"
        @test flat.variables["Chemistry.B"] == "species"
        @test flat.variables["Chemistry.k1"] == "parameter"
        @test length(flat.equations) == 1
        @test flat.equations[1].source_system == "Chemistry"
        @test occursin("Chemistry.k1", flat.equations[1].rhs)
    end

    @testset "Flatten with coupling entries" begin
        vars1 = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0)
        )
        vars2 = Dict{String, ModelVariable}(
            "SST" => ModelVariable(StateVariable, default=290.0)
        )
        model1 = Model(vars1, Equation[])
        model2 = Model(vars2, Equation[])

        coupling = CouplingEntry[
            CouplingOperatorCompose(["Atm", "Ocean"], description="Compose atmosphere and ocean"),
            CouplingVariableMap("Atm.T", "Ocean.SST", "identity", description="Map T to SST")
        ]

        models = Dict{String, Model}("Atm" => model1, "Ocean" => model2)
        metadata = Metadata("coupling_test")
        file = EsmFile("0.1.0", metadata, models=models, coupling=coupling)

        flat = flatten(file)

        @test length(flat.metadata.coupling_rules) == 2
        @test occursin("operator_compose", flat.metadata.coupling_rules[1])
        @test occursin("variable_map", flat.metadata.coupling_rules[2])
        @test occursin("Atm", flat.metadata.coupling_rules[1])
        @test occursin("Ocean", flat.metadata.coupling_rules[1])
    end

    @testset "Flatten mixed models and reaction systems" begin
        model_vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0)
        )
        model = Model(model_vars, Equation[])

        species = [Species("O3", default=1e-6)]
        rsys = ReactionSystem(species, Reaction[])

        models = Dict{String, Model}("Climate" => model)
        rsys_dict = Dict{String, ReactionSystem}("Chemistry" => rsys)
        metadata = Metadata("mixed_test")
        file = EsmFile("0.1.0", metadata, models=models, reaction_systems=rsys_dict)

        flat = flatten(file)

        @test "Climate.T" in flat.state_variables
        @test "Chemistry.O3" in flat.state_variables
        @test flat.variables["Climate.T"] == "state"
        @test flat.variables["Chemistry.O3"] == "species"
        @test length(flat.metadata.source_systems) == 2
    end

    @testset "Expression namespacing" begin
        # Test numeric expression
        num = NumExpr(42.0)
        @test EarthSciSerialization.namespace_expression(num, "Sys") == "42"

        num_float = NumExpr(3.14)
        @test EarthSciSerialization.namespace_expression(num_float, "Sys") == "3.14"

        # Test variable expression
        var = VarExpr("x")
        @test EarthSciSerialization.namespace_expression(var, "Sys") == "Sys.x"

        # Test already-qualified variable
        qual_var = VarExpr("Other.y")
        @test EarthSciSerialization.namespace_expression(qual_var, "Sys") == "Other.y"

        # Test binary op expression
        op = OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(1.0)])
        result = EarthSciSerialization.namespace_expression(op, "Sys")
        @test occursin("Sys.x", result)
        @test occursin("+", result)
        @test occursin("1", result)

        # Test derivative expression
        deriv = OpExpr("D", EarthSciSerialization.Expr[VarExpr("T")], wrt="t")
        result = EarthSciSerialization.namespace_expression(deriv, "Atm")
        @test occursin("D(", result)
        @test occursin("Atm.T", result)
    end

    @testset "Coupling entry descriptions" begin
        entry1 = CouplingOperatorCompose(["A", "B"], description="Test compose")
        desc1 = EarthSciSerialization.describe_coupling_entry(entry1)
        @test occursin("operator_compose", desc1)
        @test occursin("A + B", desc1)
        @test occursin("Test compose", desc1)

        entry2 = CouplingVariableMap("A.x", "B.y", "identity")
        desc2 = EarthSciSerialization.describe_coupling_entry(entry2)
        @test occursin("variable_map", desc2)
        @test occursin("A.x", desc2)
        @test occursin("B.y", desc2)
        @test occursin("identity", desc2)

        entry3 = CouplingVariableMap("A.x", "B.y", "conversion_factor", factor=2.5)
        desc3 = EarthSciSerialization.describe_coupling_entry(entry3)
        @test occursin("2.5", desc3)

        entry4 = CouplingOperatorApply("MyOp", description="Apply op")
        desc4 = EarthSciSerialization.describe_coupling_entry(entry4)
        @test occursin("operator_apply", desc4)
        @test occursin("MyOp", desc4)

        entry5 = CouplingCallback("cb1", description="A callback")
        desc5 = EarthSciSerialization.describe_coupling_entry(entry5)
        @test occursin("callback", desc5)
        @test occursin("cb1", desc5)
    end

    @testset "Flatten valid fixtures" begin
        valid_fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "valid")
        if isdir(valid_fixtures_dir)
            valid_files = filter(f -> endswith(f, ".esm"), readdir(valid_fixtures_dir))
            for filename in valid_files[1:min(5, length(valid_files))]
                filepath = joinpath(valid_fixtures_dir, filename)
                @testset "Flatten fixture: $filename" begin
                    try
                        esm_data = EarthSciSerialization.load(filepath)
                        flat = flatten(esm_data)
                        @test flat isa FlattenedSystem
                        @test flat.metadata isa FlattenMetadata
                    catch e
                        if e isa EarthSciSerialization.SchemaValidationError || e isa EarthSciSerialization.ParseError
                            @test_broken false  # Can't flatten if parsing fails
                        else
                            @warn "Flatten test failed for $filename: $e"
                            @test false
                        end
                    end
                end
            end
        else
            @warn "Valid fixtures directory not found: $valid_fixtures_dir"
        end
    end
end
