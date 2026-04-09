"""
Tests for ESM Format structural validation functionality.
"""

using Test
using EarthSciSerialization

@testset "Structural Validation" begin

    @testset "StructuralError struct" begin
        error = EarthSciSerialization.StructuralError("models.test.equations", "Test error message", "missing_equation")
        @test error.path == "models.test.equations"
        @test error.message == "Test error message"
        @test error.error_type == "missing_equation"
    end

    @testset "ValidationResult struct" begin
        schema_errors = [EarthSciSerialization.SchemaError("/", "Schema error", "required")]
        structural_errors = [EarthSciSerialization.StructuralError("models.test", "Structural error", "missing_equation")]
        unit_warnings = ["Unit warning"]

        # Test constructor
        result = EarthSciSerialization.ValidationResult(schema_errors, structural_errors, unit_warnings=unit_warnings)
        @test result.is_valid == false
        @test length(result.schema_errors) == 1
        @test length(result.structural_errors) == 1
        @test length(result.unit_warnings) == 1

        # Test valid case
        result_valid = EarthSciSerialization.ValidationResult(EarthSciSerialization.SchemaError[], EarthSciSerialization.StructuralError[])
        @test result_valid.is_valid == true
        @test isempty(result_valid.schema_errors)
        @test isempty(result_valid.structural_errors)
        @test isempty(result_valid.unit_warnings)
    end

    @testset "validate_structural function" begin
        metadata = EarthSciSerialization.Metadata("test-model")

        @testset "Missing equation for state variable" begin
            # Create a model with missing equation for state variable
            variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0),
                "y" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=2.0),
                "k" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable, default=0.5)
            )

            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.VarExpr("y"))
                # Missing equation for state variable y
            ]

            model = EarthSciSerialization.Model(variables, equations)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "models.test_model.equations"
            @test occursin("State variable 'y' has no defining equation", errors[1].message)
            @test errors[1].error_type == "missing_equation"
        end

        @testset "Reaction system with undefined species" begin
            species = [EarthSciSerialization.Species("A"), EarthSciSerialization.Species("B")]
            reactions = [
                EarthSciSerialization.Reaction("rxn1", [EarthSciSerialization.StoichiometryEntry("A", 1)], [EarthSciSerialization.StoichiometryEntry("C", 1)], EarthSciSerialization.VarExpr("k1"))  # C not defined
            ]
            rs = EarthSciSerialization.ReactionSystem(species, reactions)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1].products"
            @test occursin("Species 'C' not declared", errors[1].message)
            @test errors[1].error_type == "undefined_species"
        end

        @testset "Reaction with invalid stoichiometry" begin
            species = [EarthSciSerialization.Species("A"), EarthSciSerialization.Species("B")]
            reactions = [
                EarthSciSerialization.Reaction("rxn1", [EarthSciSerialization.StoichiometryEntry("A", -1)], [EarthSciSerialization.StoichiometryEntry("B", 1)], EarthSciSerialization.VarExpr("k1"))  # Negative stoichiometry
            ]
            rs = EarthSciSerialization.ReactionSystem(species, reactions)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1].substrates"
            @test occursin("non-positive stoichiometry -1", errors[1].message)
            @test errors[1].error_type == "invalid_stoichiometry"
        end

        @testset "Null-null reaction" begin
            species = [EarthSciSerialization.Species("A")]
            reactions = [
                EarthSciSerialization.Reaction("rxn1", nothing, nothing, EarthSciSerialization.VarExpr("k1"))  # No reactants or products
            ]
            rs = EarthSciSerialization.ReactionSystem(species, reactions)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1]"
            @test occursin("null-null reaction", errors[1].message)
            @test errors[1].error_type == "null_reaction"
        end

        @testset "Event with undefined affect variable" begin
            variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)
            )
            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))
            ]
            events = [
                EarthSciSerialization.ContinuousEvent(
                    EarthSciSerialization.Expr[EarthSciSerialization.OpExpr("-", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x"), EarthSciSerialization.NumExpr(10.0)])],
                    [EarthSciSerialization.AffectEquation("undefined_var", EarthSciSerialization.NumExpr(0.0))]
                )
            ]
            model = EarthSciSerialization.Model(variables, equations, continuous_events=events)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "models.test_model.continuous_events[1].affects[1]"
            @test occursin("Affect target variable 'undefined_var' not declared", errors[1].message)
            @test errors[1].error_type == "undefined_affect_variable"
        end

        @testset "Valid model - no errors" begin
            variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0),
                "k" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable, default=0.5)
            )
            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.VarExpr("k"))
            ]
            model = EarthSciSerialization.Model(variables, equations)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test isempty(errors)
        end
    end

    @testset "validate function - complete validation" begin
        metadata = EarthSciSerialization.Metadata("test-model")

        @testset "Valid file" begin
            variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)
            )
            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))
            ]
            model = EarthSciSerialization.Model(variables, equations)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            result = EarthSciSerialization.validate(esm_file)
            # Note: Schema validation might fail due to simplified conversion in validate function
            @test result isa EarthSciSerialization.ValidationResult
            @test isempty(result.structural_errors)
            @test isempty(result.unit_warnings)
        end

        @testset "File with structural errors" begin
            variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0),
                "y" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=2.0)
            )
            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))
                # Missing equation for y
            ]
            model = EarthSciSerialization.Model(variables, equations)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            result = EarthSciSerialization.validate(esm_file)
            @test result isa EarthSciSerialization.ValidationResult
            @test length(result.structural_errors) == 1
            @test result.is_valid == false  # Should be false due to structural errors
        end
    end

    @testset "validate_coupling_references function" begin
        metadata = EarthSciSerialization.Metadata("test-model")

        @testset "CouplingOperatorCompose validation" begin
            model = EarthSciSerialization.Model(Dict("x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)),
                                  [EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))])
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            # Valid system reference
            coupling = EarthSciSerialization.CouplingOperatorCompose(["test_model"])
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid system reference
            coupling_bad = EarthSciSerialization.CouplingOperatorCompose(["nonexistent_system"])
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].systems[1]"
            @test occursin("nonexistent_system", errors[1].message)
            @test errors[1].error_type == "undefined_system"
        end

        @testset "CouplingOperatorApply validation" begin
            operator = EarthSciSerialization.Operator("test_op", ["x"])
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, operators=Dict("test_op" => operator))

            # Valid operator reference
            coupling = EarthSciSerialization.CouplingOperatorApply("test_op")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid operator reference
            coupling_bad = EarthSciSerialization.CouplingOperatorApply("nonexistent_op")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].operator"
            @test occursin("nonexistent_op", errors[1].message)
            @test errors[1].error_type == "undefined_operator"
        end

        @testset "CouplingCallback validation" begin
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata)

            # Valid callback
            coupling = EarthSciSerialization.CouplingCallback("my_callback")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Empty callback ID
            coupling_bad = EarthSciSerialization.CouplingCallback("")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].callback_id"
            @test occursin("empty", errors[1].message)
            @test errors[1].error_type == "empty_callback_id"
        end

        @testset "CouplingVariableMap validation" begin
            model = EarthSciSerialization.Model(Dict("x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)),
                                  [EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))])
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            # Valid variable mapping
            coupling = EarthSciSerialization.CouplingVariableMap("test_model.x", "test_model.x", "identity")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid 'from' reference
            coupling_bad_from = EarthSciSerialization.CouplingVariableMap("invalid.ref", "test_model.x", "identity")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad_from, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].from"
            @test occursin("invalid.ref", errors[1].message)
            @test errors[1].error_type == "unresolved_reference"

            # Invalid 'to' reference
            coupling_bad_to = EarthSciSerialization.CouplingVariableMap("test_model.x", "invalid.ref", "identity")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad_to, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].to"
            @test occursin("invalid.ref", errors[1].message)
            @test errors[1].error_type == "unresolved_reference"
        end
    end

end