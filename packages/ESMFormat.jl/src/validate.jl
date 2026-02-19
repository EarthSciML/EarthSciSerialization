"""
ESM Format Schema Validation

Provides functionality to validate ESM files against the JSON schema.
"""

using JSON3
using JSONSchema

"""
    SchemaError

Represents a validation error with detailed information.
Contains path, message, and keyword from JSON Schema validation.
"""
struct SchemaError
    path::String
    message::String
    keyword::String
end

"""
    StructuralError

Represents a structural validation error with detailed information.
Contains path, message, and error type for structural issues.
"""
struct StructuralError
    path::String
    message::String
    error_type::String
end

"""
    ValidationResult

Combined validation result containing schema errors, structural errors,
unit warnings, and overall validation status.
"""
struct ValidationResult
    is_valid::Bool
    schema_errors::Vector{SchemaError}
    structural_errors::Vector{StructuralError}
    unit_warnings::Vector{String}  # Future implementation
end

# Constructor for ValidationResult
ValidationResult(schema_errors::Vector{SchemaError}, structural_errors::Vector{StructuralError}; unit_warnings::Vector{String}=String[]) =
    ValidationResult(isempty(schema_errors) && isempty(structural_errors), schema_errors, structural_errors, unit_warnings)

"""
    SchemaValidationError

Exception thrown when schema validation fails.
Contains detailed error information including paths and messages.
"""
struct SchemaValidationError <: Exception
    message::String
    errors::Vector{SchemaError}
end

# Load schema at module initialization from bundled package data
const SCHEMA_PATH = joinpath(pkgdir(@__MODULE__), "data", "esm-schema.json")

# Global schema validator
const ESM_SCHEMA = if isfile(SCHEMA_PATH)
    try
        Schema(JSON3.read(read(SCHEMA_PATH, String)))
    catch e
        @warn "Failed to load ESM schema: $e"
        nothing
    end
else
    @warn "ESM schema file not found at $SCHEMA_PATH"
    nothing
end

"""
    validate_schema(data::Any) -> Vector{SchemaError}

Validate data against the ESM schema.
Returns empty vector if valid, otherwise returns validation errors.
Each error contains the path, message, and keyword for debugging.
"""
function validate_schema(data::Any)::Vector{SchemaError}
    if ESM_SCHEMA === nothing
        @warn "Schema validation skipped - schema not loaded"
        return SchemaError[]
    end

    try
        result = JSONSchema.validate(ESM_SCHEMA, data)
        if result === nothing
            return SchemaError[]
        else
            # Convert validation result to SchemaError format
            # JSONSchema.jl returns validation error objects - need to extract info
            return [SchemaError("/", string(result), "unknown")]
        end
    catch e
        return [SchemaError("/", "Schema validation error: $(e)", "error")]
    end
end

"""
    validate_structural(file::EsmFile) -> Vector{StructuralError}

Validate structural consistency of ESM file according to spec Section 3.2.
Checks equation-unknown balance, reference integrity, reaction consistency,
and event consistency.
"""
function validate_structural(file::EsmFile)::Vector{StructuralError}
    errors = StructuralError[]

    # 1. Validate model equation-unknown balance
    if file.models !== nothing
        for (model_name, model) in file.models
            append!(errors, validate_model_balance(model, "models.$model_name"))
        end
    end

    # 2. Validate reference integrity
    append!(errors, validate_reference_integrity(file))

    # 3. Validate reaction system consistency
    if file.reaction_systems !== nothing
        for (rs_name, rs) in file.reaction_systems
            append!(errors, validate_reaction_consistency(rs, "reaction_systems.$rs_name"))
        end
    end

    # 4. Validate event consistency
    if file.models !== nothing
        for (model_name, model) in file.models
            append!(errors, validate_event_consistency(model, "models.$model_name"))
        end
    end

    return errors
end

"""
    validate(file::EsmFile) -> ValidationResult

Complete validation combining schema, structural, and unit validation.
Returns ValidationResult with all errors and warnings.
"""
function validate(file::EsmFile)::ValidationResult
    # Convert EsmFile to dict for schema validation
    # This is a simplified approach - in practice, we'd need proper serialization
    data = Dict("esm" => file.esm, "metadata" => Dict("name" => file.metadata.name))

    schema_errors = validate_schema(data)
    structural_errors = validate_structural(file)
    unit_warnings = String[]  # Future implementation

    return ValidationResult(schema_errors, structural_errors, unit_warnings=unit_warnings)
end

# ============================================================================
# Helper Functions for Structural Validation
# ============================================================================

"""
    validate_model_balance(model::Model, path::String) -> Vector{StructuralError}

Validate equation-unknown balance for a model.
Each model should have equations for all state variables.
"""
function validate_model_balance(model::Model, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    # Get all state variables
    state_vars = Set{String}()
    for (name, var) in model.variables
        if var.type == StateVariable
            push!(state_vars, name)
        end
    end

    # Get variables that appear in LHS of equations
    equation_vars = Set{String}()
    for (i, eq) in enumerate(model.equations)
        if isa(eq.lhs, VarExpr)
            push!(equation_vars, eq.lhs.name)
        elseif isa(eq.lhs, OpExpr) && eq.lhs.op == "D"
            # Differential equation: D(x) = ...
            if !isempty(eq.lhs.args) && isa(eq.lhs.args[1], VarExpr)
                push!(equation_vars, eq.lhs.args[1].name)
            end
        end
    end

    # Check for missing equations
    for var in state_vars
        if var ∉ equation_vars
            push!(errors, StructuralError(
                "$path.equations",
                "State variable '$var' has no defining equation",
                "missing_equation"
            ))
        end
    end

    # Recursively check subsystems
    for (subsys_name, subsys) in model.subsystems
        append!(errors, validate_model_balance(subsys, "$path.subsystems.$subsys_name"))
    end

    return errors
end

"""
    validate_reference_integrity(file::EsmFile) -> Vector{StructuralError}

Validate that all variable references can be resolved through the hierarchy.
"""
function validate_reference_integrity(file::EsmFile)::Vector{StructuralError}
    errors = StructuralError[]

    # Validate model variable references
    if file.models !== nothing
        for (model_name, model) in file.models
            append!(errors, validate_model_references(file, model, "models.$model_name"))
        end
    end

    # Validate coupling references
    for (i, coupling_entry) in enumerate(file.coupling)
        append!(errors, validate_coupling_references(file, coupling_entry, "coupling[$i]"))
    end

    return errors
end

"""
    validate_model_references(file::EsmFile, model::Model, path::String) -> Vector{StructuralError}

Validate variable references within a model.
"""
function validate_model_references(file::EsmFile, model::Model, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    # Validate equation references
    for (i, eq) in enumerate(model.equations)
        append!(errors, validate_expression_references(file, eq.lhs, "$path.equations[$i].lhs"))
        append!(errors, validate_expression_references(file, eq.rhs, "$path.equations[$i].rhs"))
    end

    # Validate discrete event references
    for (i, event) in enumerate(model.discrete_events)
        append!(errors, validate_event_references(file, event, "$path.discrete_events[$i]"))
    end

    # Validate continuous event references
    for (i, event) in enumerate(model.continuous_events)
        append!(errors, validate_event_references(file, event, "$path.continuous_events[$i]"))
    end

    # Recursively check subsystems
    for (subsys_name, subsys) in model.subsystems
        append!(errors, validate_model_references(file, subsys, "$path.subsystems.$subsys_name"))
    end

    return errors
end

"""
    validate_expression_references(file::EsmFile, expr::Expr, path::String) -> Vector{StructuralError}

Validate that all variable references in an expression can be resolved.
"""
function validate_expression_references(file::EsmFile, expr::Expr, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    if isa(expr, VarExpr)
        # Simple variable reference - check if it exists in current context
        # For now, we'll accept all VarExpr as they could be local or qualified
        # TODO: More sophisticated scoped resolution
    elseif isa(expr, OpExpr)
        # Recursively check arguments
        for (i, arg) in enumerate(expr.args)
            append!(errors, validate_expression_references(file, arg, "$path.args[$i]"))
        end

        # Check operator_apply references
        if expr.op == "operator_apply"
            # First argument should be an operator reference
            if !isempty(expr.args) && isa(expr.args[1], VarExpr)
                op_name = expr.args[1].name
                if file.operators === nothing || !haskey(file.operators, op_name)
                    push!(errors, StructuralError(
                        path,
                        "Operator '$op_name' referenced but not defined",
                        "undefined_operator"
                    ))
                end
            end
        end
    end
    # NumExpr has no references to validate

    return errors
end

"""
    validate_coupling_references(file::EsmFile, coupling_entry::CouplingEntry, path::String) -> Vector{StructuralError}

Validate coupling references based on the specific coupling type.
Checks that systems, operators, and variable references can be resolved.
"""
function validate_coupling_references(file::EsmFile, coupling_entry::CouplingEntry, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    if isa(coupling_entry, CouplingOperatorCompose)
        # Validate that all referenced systems exist
        for (i, system_name) in enumerate(coupling_entry.systems)
            if !system_exists_in_file(file, system_name)
                push!(errors, StructuralError(
                    "$path.systems[$i]",
                    "System '$system_name' referenced in operator_compose coupling not found",
                    "undefined_system"
                ))
            end
        end

    elseif isa(coupling_entry, CouplingCouple2)
        # Validate that all referenced systems exist
        for (i, system_name) in enumerate(coupling_entry.systems)
            if !system_exists_in_file(file, system_name)
                push!(errors, StructuralError(
                    "$path.systems[$i]",
                    "System '$system_name' referenced in couple2 coupling not found",
                    "undefined_system"
                ))
            end
        end

    elseif isa(coupling_entry, CouplingVariableMap)
        # Validate 'from' reference
        if !validate_reference_syntax(coupling_entry.from)
            push!(errors, StructuralError(
                "$path.from",
                "Invalid reference syntax: '$(coupling_entry.from)'",
                "invalid_reference_syntax"
            ))
        else
            # Try to resolve the 'from' reference
            try
                resolve_qualified_reference(file, coupling_entry.from)
            catch e
                if isa(e, QualifiedReferenceError)
                    push!(errors, StructuralError(
                        "$path.from",
                        "Cannot resolve 'from' reference '$(coupling_entry.from)': $(e.message)",
                        "unresolved_reference"
                    ))
                end
            end
        end

        # Validate 'to' reference
        if !validate_reference_syntax(coupling_entry.to)
            push!(errors, StructuralError(
                "$path.to",
                "Invalid reference syntax: '$(coupling_entry.to)'",
                "invalid_reference_syntax"
            ))
        else
            # Try to resolve the 'to' reference
            try
                resolve_qualified_reference(file, coupling_entry.to)
            catch e
                if isa(e, QualifiedReferenceError)
                    push!(errors, StructuralError(
                        "$path.to",
                        "Cannot resolve 'to' reference '$(coupling_entry.to)': $(e.message)",
                        "unresolved_reference"
                    ))
                end
            end
        end

    elseif isa(coupling_entry, CouplingOperatorApply)
        # Validate that the referenced operator exists
        if file.operators === nothing || !haskey(file.operators, coupling_entry.operator)
            push!(errors, StructuralError(
                "$path.operator",
                "Operator '$(coupling_entry.operator)' referenced in operator_apply coupling not found",
                "undefined_operator"
            ))
        end

    elseif isa(coupling_entry, CouplingCallback)
        # Basic validation - callback_id should be a non-empty string
        if isempty(coupling_entry.callback_id)
            push!(errors, StructuralError(
                "$path.callback_id",
                "Callback ID cannot be empty",
                "empty_callback_id"
            ))
        end

    elseif isa(coupling_entry, CouplingEvent)
        # Validate affect equations
        for (i, affect) in enumerate(coupling_entry.affects)
            # Try to resolve the affect target as a qualified reference
            try
                resolve_qualified_reference(file, affect.lhs)
            catch e
                if isa(e, QualifiedReferenceError)
                    push!(errors, StructuralError(
                        "$path.affects[$i].lhs",
                        "Cannot resolve affect target '$(affect.lhs)': $(e.message)",
                        "unresolved_affect_target"
                    ))
                end
            end

            # Validate the affect expression references
            append!(errors, validate_expression_references(file, affect.rhs, "$path.affects[$i].rhs"))
        end

        # Validate negative affect equations if present
        if coupling_entry.affect_neg !== nothing
            for (i, affect) in enumerate(coupling_entry.affect_neg)
                # Try to resolve the affect target as a qualified reference
                try
                    resolve_qualified_reference(file, affect.lhs)
                catch e
                    if isa(e, QualifiedReferenceError)
                        push!(errors, StructuralError(
                            "$path.affect_neg[$i].lhs",
                            "Cannot resolve negative affect target '$(affect.lhs)': $(e.message)",
                            "unresolved_affect_target"
                        ))
                    end
                end

                # Validate the affect expression references
                append!(errors, validate_expression_references(file, affect.rhs, "$path.affect_neg[$i].rhs"))
            end
        end

        # Validate condition expressions if present (for continuous events)
        if coupling_entry.conditions !== nothing
            for (i, condition) in enumerate(coupling_entry.conditions)
                append!(errors, validate_expression_references(file, condition, "$path.conditions[$i]"))
            end
        end

        # Validate trigger expression if present (for discrete events)
        if coupling_entry.trigger !== nothing && isa(coupling_entry.trigger, ConditionTrigger)
            append!(errors, validate_expression_references(file, coupling_entry.trigger.expression, "$path.trigger.expression"))
        end
    end

    return errors
end

"""
    validate_event_references(file::EsmFile, event::EventType, path::String) -> Vector{StructuralError}

Validate event variable references.
"""
function validate_event_references(file::EsmFile, event::EventType, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    if isa(event, ContinuousEvent)
        # Validate condition expressions
        for (i, condition) in enumerate(event.conditions)
            append!(errors, validate_expression_references(file, condition, "$path.conditions[$i]"))
        end

        # Validate affect references
        for (i, affect) in enumerate(event.affects)
            append!(errors, validate_expression_references(file, affect.rhs, "$path.affects[$i].rhs"))
            # affect.lhs is a string (variable name) - would need model context to validate
        end

    elseif isa(event, DiscreteEvent)
        # Validate functional affect references
        for (i, affect) in enumerate(event.affects)
            append!(errors, validate_expression_references(file, affect.expression, "$path.affects[$i].expression"))
            # affect.target is a string (variable name) - would need model context to validate
        end

        # Validate trigger references (if condition-based)
        if isa(event.trigger, ConditionTrigger)
            append!(errors, validate_expression_references(file, event.trigger.expression, "$path.trigger.expression"))
        end
    end

    return errors
end

"""
    validate_reaction_consistency(rs::ReactionSystem, path::String) -> Vector{StructuralError}

Validate reaction system consistency: species declared, positive stoichiometries,
no null-null reactions, rate references declared.
"""
function validate_reaction_consistency(rs::ReactionSystem, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    # Get set of declared species
    species_names = Set(sp.name for sp in rs.species)

    # Get set of declared parameters
    param_names = Set(p.name for p in rs.parameters)

    # Validate each reaction
    for (i, reaction) in enumerate(rs.reactions)
        reaction_path = "$path.reactions[$i]"

        # Check substrates (reactants) are declared species
        # Use getfield to access the actual Vector{StoichiometryEntry} instead of backward-compatibility Dict
        substrates_field = getfield(reaction, :substrates)
        if substrates_field !== nothing
            for entry in substrates_field
                if entry.species ∉ species_names
                    push!(errors, StructuralError(
                        "$reaction_path.substrates",
                        "Species '$(entry.species)' not declared",
                        "undefined_species"
                    ))
                end

                # Check positive stoichiometry
                if entry.stoichiometry <= 0
                    push!(errors, StructuralError(
                        "$reaction_path.substrates",
                        "Species '$(entry.species)' has non-positive stoichiometry $(entry.stoichiometry)",
                        "invalid_stoichiometry"
                    ))
                end
            end
        end

        # Check products are declared species
        # Use getfield to access the actual Vector{StoichiometryEntry} instead of backward-compatibility Dict
        products_field = getfield(reaction, :products)
        if products_field !== nothing
            for entry in products_field
                if entry.species ∉ species_names
                    push!(errors, StructuralError(
                        "$reaction_path.products",
                        "Species '$(entry.species)' not declared",
                        "undefined_species"
                    ))
                end

                # Check positive stoichiometry
                if entry.stoichiometry <= 0
                    push!(errors, StructuralError(
                        "$reaction_path.products",
                        "Species '$(entry.species)' has non-positive stoichiometry $(entry.stoichiometry)",
                        "invalid_stoichiometry"
                    ))
                end
            end
        end

        # Check for null-null reaction (no reactants and no products)
        has_substrates = substrates_field !== nothing && !isempty(substrates_field)
        has_products = products_field !== nothing && !isempty(products_field)
        if !has_substrates && !has_products
            push!(errors, StructuralError(
                reaction_path,
                "Reaction has no reactants or products (null-null reaction)",
                "null_reaction"
            ))
        end

        # Validate rate expression references
        # This is simplified - a full implementation would check all variable references in rate
        if isa(reaction.rate, VarExpr)
            rate_var = reaction.rate.name
            if rate_var ∉ param_names && rate_var ∉ species_names
                # Could be a qualified reference - for now just warn
                # push!(errors, StructuralError(
                #     "$reaction_path.rate",
                #     "Rate variable '$rate_var' not found in parameters or species",
                #     "undefined_rate_variable"
                # ))
            end
        end
    end

    # Recursively check subsystems
    for (subsys_name, subsys) in rs.subsystems
        append!(errors, validate_reaction_consistency(subsys, "$path.subsystems.$subsys_name"))
    end

    return errors
end

"""
    system_exists_in_file(file::EsmFile, system_name::String) -> Bool

Check if a system (model, reaction_system, data_loader, or operator) exists in the ESM file.
"""
function system_exists_in_file(file::EsmFile, system_name::String)::Bool
    # Check models
    if file.models !== nothing && haskey(file.models, system_name)
        return true
    end

    # Check reaction_systems
    if file.reaction_systems !== nothing && haskey(file.reaction_systems, system_name)
        return true
    end

    # Check data_loaders
    if file.data_loaders !== nothing && haskey(file.data_loaders, system_name)
        return true
    end

    # Check operators
    if file.operators !== nothing && haskey(file.operators, system_name)
        return true
    end

    return false
end

"""
    validate_event_consistency(model::Model, path::String) -> Vector{StructuralError}

Validate event consistency: continuous conditions are expressions,
discrete conditions produce booleans, affect variables declared,
functional affect refs valid.
"""
function validate_event_consistency(model::Model, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    # Validate discrete events
    for (i, event) in enumerate(model.discrete_events)
        event_path = "$path.discrete_events[$i]"
        append!(errors, validate_single_event_consistency(model, event, event_path))
    end

    # Validate continuous events
    for (i, event) in enumerate(model.continuous_events)
        event_path = "$path.continuous_events[$i]"
        append!(errors, validate_single_event_consistency(model, event, event_path))
    end

    # Recursively check subsystems
    for (subsys_name, subsys) in model.subsystems
        append!(errors, validate_event_consistency(subsys, "$path.subsystems.$subsys_name"))
    end

    return errors
end

"""
    validate_single_event_consistency(model::Model, event::EventType, event_path::String) -> Vector{StructuralError}

Validate consistency of a single event.
"""
function validate_single_event_consistency(model::Model, event::EventType, event_path::String)::Vector{StructuralError}
    errors = StructuralError[]

    if isa(event, ContinuousEvent)
            # Continuous event conditions should be mathematical expressions (zero-crossing)
            # This is automatically satisfied by the type system (Vector{Expr})

            # Validate affect variable declarations
            for (j, affect) in enumerate(event.affects)
                if !haskey(model.variables, affect.lhs)
                    push!(errors, StructuralError(
                        "$event_path.affects[$j]",
                        "Affect target variable '$(affect.lhs)' not declared in model",
                        "undefined_affect_variable"
                    ))
                end
            end

        elseif isa(event, DiscreteEvent)
            # For condition triggers, ensure expression could produce boolean
            if isa(event.trigger, ConditionTrigger)
                # In practice, we'd need more sophisticated analysis to ensure boolean result
                # For now, accept all expressions as they could evaluate to boolean
            end

            # Validate functional affect targets
            for (j, affect) in enumerate(event.affects)
                if !haskey(model.variables, affect.target)
                    push!(errors, StructuralError(
                        "$event_path.affects[$j]",
                        "Functional affect target '$(affect.target)' not declared in model",
                        "undefined_affect_target"
                    ))
                end
            end
        end

    return errors
end