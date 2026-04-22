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
            append!(errors, validate_reaction_rate_units(rs, "/reaction_systems/$rs_name"))
        end
    end

    # 4. Validate event consistency
    if file.models !== nothing
        for (model_name, model) in file.models
            append!(errors, validate_event_consistency(model, "models.$model_name"))
            append!(errors, validate_model_gradient_units(file, model, "/models/$model_name"))
            append!(errors, validate_physical_constant_units(model, "/models/$model_name"))
            append!(errors, validate_conversion_factor_consistency(model, "/models/$model_name"))
            append!(errors, validate_pde_aware_assertions(file, model_name, model))
        end
    end

    # 5. Validate multi-domain consistency
    append!(errors, validate_multi_domain(file))

    # 6. Conflicting derivative detection (§4.7.5 item E). A species cannot
    # have both an explicit D(X, t) = ... equation and a reaction contribution.
    # `_find_conflicting_derivatives` is defined in flatten.jl.
    conflicting = _find_conflicting_derivatives(file)
    for name in conflicting
        push!(errors, StructuralError(
            "models/reaction_systems",
            "Species '$name' has both an explicit derivative equation and a reaction contribution",
            "conflicting_derivative",
        ))
    end

    return errors
end

"""
    validate(file::EsmFile) -> ValidationResult

Complete validation combining schema, structural, and unit validation.
Returns ValidationResult with all errors and warnings.
"""
function validate(file::EsmFile)::ValidationResult
    # Schema validation requires the full serialized document: the schema's
    # top-level `anyOf` requires either `models` or `reaction_systems`, so a
    # stub dict with just `esm` and `metadata.name` would always fail.
    data = serialize_esm_file(file)

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

    elseif isa(coupling_entry, CouplingCouple)
        # Validate that all referenced systems exist
        for (i, system_name) in enumerate(coupling_entry.systems)
            if !system_exists_in_file(file, system_name)
                push!(errors, StructuralError(
                    "$path.systems[$i]",
                    "System '$system_name' referenced in couple coupling not found",
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
    validate_reaction_rate_units(rs::ReactionSystem, path::String) -> Vector{StructuralError}

Enforce the mass-action dimensional constraint from spec §7.4: for each reaction,
rate * prod(substrate^stoichiometry) must have dimensions of species/time. The
reference concentration unit is taken from the first substrate (matching TS/Python).

The check is skipped when the reference concentration unit is dimensionless
(mol/mol, ppm, …) because atmospheric-chemistry rate expressions commonly bake
a number-density factor into rate constants.
"""
function validate_reaction_rate_units(rs::ReactionSystem, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    # Build name → unit-string map using ONLY explicitly declared units.
    # Mirrors Python's conservative scope: skip when any relevant unit is
    # absent, so we do not surface false positives on partially-annotated
    # fixtures (e.g. tests that omit units to exercise other rules).
    species_units = Dict{String, String}()
    for species in rs.species
        species.units !== nothing && (species_units[species.name] = species.units)
    end
    param_units = Dict{String, String}()
    for param in rs.parameters
        param.units !== nothing && (param_units[param.name] = param.units)
    end

    time_unit = parse_units("s")

    for (i, reaction) in enumerate(rs.reactions)
        # Only check bare-variable rate references whose symbol has declared
        # units. Compound rate expressions are skipped because atmospheric-
        # chemistry rate constants routinely carry implicit units on numeric
        # literals, which defeats literal dimensional analysis.
        isa(reaction.rate, VarExpr) || continue
        rate_name = reaction.rate.name
        rate_units_str = get(param_units, rate_name, get(species_units, rate_name, nothing))
        rate_units_str === nothing && continue
        rate_dim = parse_units(rate_units_str)
        rate_dim === nothing && continue

        substrates_field = getfield(reaction, :substrates)
        (substrates_field === nothing || isempty(substrates_field)) && continue

        # Require every referenced substrate to have declared units.
        # Fractional stoichiometries on substrates produce non-integer unit
        # exponents, which Unitful does not support for dimensional analysis —
        # skip the dimensional check in that case (fractional substrates are
        # unusual; fractional *products* are the common atmospheric-chemistry
        # case and don't enter this path).
        resolvable = true
        substrate_dim = Unitful.NoUnits
        species_dim = nothing
        total_order = 0.0
        fractional_substrate = false
        for substrate in substrates_field
            sp_units_str = get(species_units, substrate.species, nothing)
            if sp_units_str === nothing
                resolvable = false
                break
            end
            sp_dim = parse_units(sp_units_str)
            if sp_dim === nothing
                resolvable = false
                break
            end
            species_dim === nothing && (species_dim = sp_dim)
            if !isinteger(substrate.stoichiometry)
                fractional_substrate = true
                break
            end
            substrate_dim = substrate_dim * (sp_dim^Int(substrate.stoichiometry))
            total_order += substrate.stoichiometry
        end
        fractional_substrate && continue
        (!resolvable || species_dim === nothing) && continue
        time_unit === nothing && continue

        # Skip when the reference concentration unit is dimensionless
        # (mol/mol, ppm, …) — mass-action convention is ambiguous there.
        dimension(species_dim) == dimension(Unitful.NoUnits) && continue

        expected_dim = species_dim / time_unit
        full_dim = rate_dim * substrate_dim
        if dimension(full_dim) != dimension(expected_dim)
            first_sp_units = get(species_units, substrates_field[1].species, "")
            order_str = isinteger(total_order) ? string(Int(total_order)) : string(total_order)
            push!(errors, StructuralError(
                "$path/reactions/$(i-1)",
                "Reaction $(reaction.id) rate '$rate_name' units '$rate_units_str' " *
                "incompatible with order-$order_str reaction for species units " *
                "'$first_sp_units' (expected rate*substrates to have dimensions of species/time)",
                "unit_inconsistency",
            ))
        end
    end

    # Recurse into subsystems
    for (subsys_name, subsys) in rs.subsystems
        append!(errors, validate_reaction_rate_units(subsys, "$path/subsystems/$subsys_name"))
    end

    return errors
end

"""
    _collect_spatial_dim_names(file::EsmFile, model::Model) -> Union{Vector{String},Nothing}

Return the ordered list of spatial dimension names for a component, or
`nothing` when the component is 0-D (no `domain` reference, missing domain
entry, or a domain whose `spatial` map is missing/empty).
"""
function _collect_spatial_dim_names(file::EsmFile, model::Model)
    model.domain === nothing && return nothing
    file.domains === nothing && return nothing
    haskey(file.domains, model.domain) || return nothing
    domain = file.domains[model.domain]
    domain.spatial === nothing && return nothing
    names = collect(keys(domain.spatial))
    isempty(names) && return nothing
    return String[string(n) for n in names]
end

"""
    validate_pde_aware_assertions(file::EsmFile, model_name::String, model::Model) -> Vector{StructuralError}

Per-binding structural rules for esm-spec §6.6.5 (PDE-aware assertions) and
§6.7.4 (pinned_coords on field plots). These rules require resolved-domain
information that JSON Schema cannot express:

- A 0-D component MUST NOT carry an Assertion that sets `coords` or `reduce`.
- A PDE component (≥1 spatial dim) MUST NOT carry an Assertion that omits
  BOTH `coords` and `reduce`.
- `coords` keys MUST name dimensions declared in `component.domain.spatial`.
- `pinned_coords` on `field_slice`/`field_snapshot` plots MUST cover every
  spatial dimension not used by the plot's `x` (and `y`) axes.

Mirrors the implementations in `earthsci-toolkit-rs/src/validate.rs` and
`earthsci_toolkit/src/earthsci_toolkit/parse.py::_check_pde_aware_assertions`.
"""
function validate_pde_aware_assertions(file::EsmFile, model_name::AbstractString,
                                        model::Model)::Vector{StructuralError}
    errors = StructuralError[]
    spatial_dims = _collect_spatial_dim_names(file, model)
    is_0d = spatial_dims === nothing

    for (ti, test) in enumerate(model.tests)
        for (ai, a) in enumerate(test.assertions)
            path = "/models/$model_name/tests/$(ti-1)/assertions/$(ai-1)"
            has_coords = a.coords !== nothing
            has_reduce = a.reduce !== nothing
            if is_0d
                if has_coords || has_reduce
                    offending = has_coords ? "coords" : "reduce"
                    push!(errors, StructuralError(
                        path,
                        "Assertion on 0-D component '$model_name' must not set coords or reduce (test '$(test.id)', variable '$(a.variable)', offending field '$offending')",
                        "assertion_spatial_on_0d",
                    ))
                end
            else
                dims = spatial_dims
                if !has_coords && !has_reduce
                    push!(errors, StructuralError(
                        path,
                        "Assertion on PDE component '$model_name' must set either coords or reduce (test '$(test.id)', variable '$(a.variable)', spatial dimensions $(dims))",
                        "assertion_missing_spatial_on_pde",
                    ))
                end
                if has_coords
                    for key in keys(a.coords)
                        if !(string(key) in dims)
                            push!(errors, StructuralError(
                                path,
                                "Assertion coords key '$key' is not a spatial dimension of component '$model_name' (declared dimensions: $dims)",
                                "assertion_coords_unknown_dim",
                            ))
                        end
                    end
                end
            end
        end
    end

    # Field-plot coverage. `model.examples` carries raw JSON3 objects (see
    # `coerce_model` in parse.jl); we avoid a typed Plot struct because
    # examples are non-normative illustrative runs, not simulation inputs.
    for (ei, ex) in enumerate(model.examples)
        example_id = (haskey(ex, :id) && ex.id !== nothing) ? string(ex.id) : ""
        haskey(ex, :plots) && ex.plots !== nothing || continue
        for (pi, plot) in enumerate(ex.plots)
            ptype = (haskey(plot, :type) && plot.type !== nothing) ? string(plot.type) : ""
            (ptype == "field_slice" || ptype == "field_snapshot") || continue
            ppath = "/models/$model_name/examples/$(ei-1)/plots/$(pi-1)"
            plot_id = (haskey(plot, :id) && plot.id !== nothing) ? string(plot.id) : ""
            if spatial_dims === nothing
                push!(errors, StructuralError(
                    ppath,
                    "Field plot type '$ptype' requires a component with a spatial domain, but component '$model_name' is 0-D (example '$example_id', plot '$plot_id')",
                    "plot_field_on_0d",
                ))
                continue
            end
            dims = spatial_dims
            used_axes = String[]
            if haskey(plot, :x) && plot.x !== nothing &&
                    haskey(plot.x, :variable) && plot.x.variable !== nothing
                push!(used_axes, string(plot.x.variable))
            end
            if ptype == "field_snapshot" && haskey(plot, :y) && plot.y !== nothing &&
                    haskey(plot.y, :variable) && plot.y.variable !== nothing
                push!(used_axes, string(plot.y.variable))
            end
            pinned_keys = String[]
            if haskey(plot, :pinned_coords) && plot.pinned_coords !== nothing
                for k in keys(plot.pinned_coords)
                    push!(pinned_keys, string(k))
                end
            end
            missing_dims = [d for d in dims if !(d in used_axes) && !(d in pinned_keys)]
            if !isempty(missing_dims)
                push!(errors, StructuralError(
                    ppath,
                    "$ptype plot on component '$model_name' must pin non-axis spatial dimension '$(missing_dims[1])' in pinned_coords (example '$example_id', plot '$plot_id', missing $(missing_dims))",
                    "plot_pinned_coords_missing",
                ))
            end
        end
    end

    return errors
end

"""
    validate_model_gradient_units(file::EsmFile, model::Model, path::String) -> Vector{StructuralError}

Flag `grad` / `div` / `laplacian` operators whose spatial coordinate is declared
in the enclosing model's domain but carries no units. Mirrors the TypeScript
binding's coordinate-resolution path (see `packages/earthsci-toolkit/src/units.ts`):
the coordinate is identified by the operator node's `dim` and looked up in
`file.domains[model.domain].spatial`. Coordinates absent from the domain map
are left alone (fallback to the legacy metre denominator behaviour); coordinates
that are declared without units are dimensionally ambiguous and surface as
`unit_inconsistency`. Recurses into subsystems.
"""
function validate_model_gradient_units(file::EsmFile, model::Model, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    # Build coordinate → units-string map from the enclosing domain. A missing
    # domain reference, missing domain entry, or missing `spatial` table all
    # short-circuit: we cannot resolve coordinates and therefore fall back to
    # legacy behaviour for child operators. Subsystems still recurse so they
    # can pick up their own domain (none currently override, but the recursion
    # mirrors the other *_consistency validators).
    coord_units = _collect_coordinate_units(file, model)

    if coord_units !== nothing
        for (i, eq) in enumerate(model.equations)
            eq_path = "$path/equations/$(i-1)"
            append!(errors, _check_gradient_ops(eq.lhs, coord_units, eq_path, i-1))
            append!(errors, _check_gradient_ops(eq.rhs, coord_units, eq_path, i-1))
        end
    end

    for (subsys_name, subsys) in model.subsystems
        append!(errors, validate_model_gradient_units(file, subsys, "$path/subsystems/$subsys_name"))
    end

    return errors
end

# Returns a Dict{String, Union{String,Nothing}} mapping dim-name → declared
# units (or `nothing` if the coordinate entry has no units field), or `nothing`
# when no resolvable domain/spatial table exists.
function _collect_coordinate_units(file::EsmFile, model::Model)::Union{Dict{String,Union{String,Nothing}},Nothing}
    model.domain === nothing && return nothing
    file.domains === nothing && return nothing
    haskey(file.domains, model.domain) || return nothing
    spatial = file.domains[model.domain].spatial
    spatial === nothing && return nothing

    coords = Dict{String,Union{String,Nothing}}()
    for (dim_name, dim) in spatial
        coords[dim_name] = _lookup_units_field(dim)
    end
    return coords
end

# Look up a `units` field on a coord descriptor produced by either path:
# parse.jl preserves the raw JSON3 object (symbol keys) in Dict{String,Any}
# values, while test-time constructors pass plain Dict{String,String} for
# ergonomics. Check Symbol first (JSON3 path), then fall back to String.
function _lookup_units_field(dim)::Union{String,Nothing}
    for key in (:units, "units")
        local ok, val
        try
            ok = haskey(dim, key)
        catch
            ok = false
        end
        ok || continue
        try
            val = dim[key]
        catch
            continue
        end
        val === nothing && continue
        s = String(val)
        isempty(s) || return s
    end
    return nothing
end

function _check_gradient_ops(expr::Expr, coord_units::Dict{String,Union{String,Nothing}},
                             eq_path::String, eq_index::Int)::Vector{StructuralError}
    errors = StructuralError[]
    if expr isa OpExpr
        if expr.op in ("grad", "div", "laplacian") && expr.dim !== nothing
            dim_name = expr.dim
            if haskey(coord_units, dim_name) && coord_units[dim_name] === nothing
                # Describe the operand for the error message: use the variable
                # name if it's a bare reference, otherwise fall back to the
                # operator's own label. Matches the TS binding's user-visible
                # framing without committing to a fully-rendered expression.
                operand_label = if !isempty(expr.args) && expr.args[1] isa VarExpr
                    "variable '$(expr.args[1].name)'"
                else
                    "$(expr.op) operand"
                end
                push!(errors, StructuralError(
                    eq_path,
                    "Gradient operator applied to $operand_label with incompatible spatial " *
                    "units: coordinate '$dim_name' has no declared units",
                    "unit_inconsistency",
                ))
            end
        end
        for arg in expr.args
            append!(errors, _check_gradient_ops(arg, coord_units, eq_path, eq_index))
        end
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

# ============================================================================
# Multi-Domain Validation
# ============================================================================

"""
    validate_multi_domain(file::EsmFile) -> Vector{StructuralError}

Validate multi-domain consistency:
1. Model/ReactionSystem `domain` must reference a key in `domains`
2. Interface `domains` must reference valid domain names
3. Interface dimension_mapping.shared/constraints must reference valid dimensions
4. Coupling `interface` must reference a key in `interfaces`
5. `lifting` only valid when source or target is 0D (domain is null)
"""
function validate_multi_domain(file::EsmFile)::Vector{StructuralError}
    errors = StructuralError[]

    domain_names = file.domains !== nothing ? Set(keys(file.domains)) : Set{String}()
    interface_names = file.interfaces !== nothing ? Set(keys(file.interfaces)) : Set{String}()

    # 1. Validate model domain references
    if file.models !== nothing
        for (model_name, model) in file.models
            if model.domain !== nothing && !isempty(domain_names)
                if model.domain ∉ domain_names
                    push!(errors, StructuralError(
                        "models.$model_name.domain",
                        "Domain '$(model.domain)' not found in domains",
                        "undefined_domain"
                    ))
                end
            elseif model.domain !== nothing && isempty(domain_names)
                push!(errors, StructuralError(
                    "models.$model_name.domain",
                    "Domain '$(model.domain)' referenced but no domains defined",
                    "undefined_domain"
                ))
            end
        end
    end

    # 1b. Validate reaction system domain references
    if file.reaction_systems !== nothing
        for (rs_name, rs) in file.reaction_systems
            if rs.domain !== nothing && !isempty(domain_names)
                if rs.domain ∉ domain_names
                    push!(errors, StructuralError(
                        "reaction_systems.$rs_name.domain",
                        "Domain '$(rs.domain)' not found in domains",
                        "undefined_domain"
                    ))
                end
            elseif rs.domain !== nothing && isempty(domain_names)
                push!(errors, StructuralError(
                    "reaction_systems.$rs_name.domain",
                    "Domain '$(rs.domain)' referenced but no domains defined",
                    "undefined_domain"
                ))
            end
        end
    end

    # 2. Validate interface domain references
    if file.interfaces !== nothing
        for (iface_name, iface) in file.interfaces
            for (i, dom_name) in enumerate(iface.domains)
                if dom_name ∉ domain_names
                    push!(errors, StructuralError(
                        "interfaces.$iface_name.domains[$i]",
                        "Domain '$dom_name' not found in domains",
                        "undefined_domain"
                    ))
                end
            end

            # 3. Validate dimension_mapping references
            append!(errors, validate_interface_dimensions(file, iface, iface_name))
        end
    end

    # 4 & 5. Validate coupling interface/lifting references
    for (i, coupling_entry) in enumerate(file.coupling)
        append!(errors, validate_coupling_multi_domain(file, coupling_entry, "coupling[$i]"))
    end

    return errors
end

"""
    validate_interface_dimensions(file::EsmFile, iface::Interface, iface_name::String) -> Vector{StructuralError}

Validate that dimension_mapping.shared and dimension_mapping.constraints reference
valid dimensions from the domains they belong to.
"""
function validate_interface_dimensions(file::EsmFile, iface::Interface, iface_name::String)::Vector{StructuralError}
    errors = StructuralError[]

    dm = iface.dimension_mapping

    # Build set of valid "domain.dimension" references from the interface's domains
    valid_dim_refs = Set{String}()
    if file.domains !== nothing
        for dom_name in iface.domains
            if haskey(file.domains, dom_name)
                domain = file.domains[dom_name]
                if domain.spatial !== nothing
                    for dim_name in keys(domain.spatial)
                        push!(valid_dim_refs, "$dom_name.$dim_name")
                    end
                end
            end
        end
    end

    # Validate shared dimension keys (format: "domain.dimension")
    if haskey(dm, "shared") && dm["shared"] !== nothing
        shared = dm["shared"]
        if isa(shared, AbstractDict)
            for (key, value) in shared
                if !isempty(valid_dim_refs) && key ∉ valid_dim_refs
                    push!(errors, StructuralError(
                        "interfaces.$iface_name.dimension_mapping.shared",
                        "Dimension reference '$key' does not match any dimension in the interface's domains",
                        "invalid_dimension_reference"
                    ))
                end
                if isa(value, String) && !isempty(valid_dim_refs) && value ∉ valid_dim_refs
                    push!(errors, StructuralError(
                        "interfaces.$iface_name.dimension_mapping.shared",
                        "Dimension reference '$value' does not match any dimension in the interface's domains",
                        "invalid_dimension_reference"
                    ))
                end
            end
        end
    end

    # Validate constraints dimension keys (format: "domain.dimension")
    if haskey(dm, "constraints") && dm["constraints"] !== nothing
        constraints = dm["constraints"]
        if isa(constraints, AbstractDict)
            for (key, _) in constraints
                if !isempty(valid_dim_refs) && key ∉ valid_dim_refs
                    push!(errors, StructuralError(
                        "interfaces.$iface_name.dimension_mapping.constraints",
                        "Dimension reference '$key' does not match any dimension in the interface's domains",
                        "invalid_dimension_reference"
                    ))
                end
            end
        end
    end

    return errors
end

"""
    get_system_domain(file::EsmFile, system_name::String) -> Union{String,Nothing,Missing}

Get the domain of a system by name. Returns:
- String: the domain name
- nothing: system is 0D (no domain)
- missing: system not found
"""
function get_system_domain(file::EsmFile, system_name::String)
    if file.models !== nothing && haskey(file.models, system_name)
        return file.models[system_name].domain
    end
    if file.reaction_systems !== nothing && haskey(file.reaction_systems, system_name)
        return file.reaction_systems[system_name].domain
    end
    return missing
end

"""
    validate_coupling_multi_domain(file::EsmFile, coupling_entry::CouplingEntry, path::String) -> Vector{StructuralError}

Validate coupling interface and lifting fields:
- `interface` must reference a key in `interfaces`
- `lifting` is only valid when source or target is 0D (domain is null)
"""
function validate_coupling_multi_domain(file::EsmFile, coupling_entry::CouplingEntry, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    interface_names = file.interfaces !== nothing ? Set(keys(file.interfaces)) : Set{String}()

    # Extract interface, lifting, and systems from coupling types that support them
    iface_field = nothing
    lifting_field = nothing
    system_names = String[]

    if isa(coupling_entry, CouplingOperatorCompose)
        iface_field = coupling_entry.interface
        lifting_field = coupling_entry.lifting
        system_names = coupling_entry.systems
    elseif isa(coupling_entry, CouplingCouple)
        iface_field = coupling_entry.interface
        lifting_field = coupling_entry.lifting
        system_names = coupling_entry.systems
    elseif isa(coupling_entry, CouplingVariableMap)
        iface_field = coupling_entry.interface
        lifting_field = coupling_entry.lifting
        # Extract system names from qualified references (first segment before '.')
        from_parts = split(coupling_entry.from, ".")
        to_parts = split(coupling_entry.to, ".")
        if length(from_parts) >= 2
            push!(system_names, String(from_parts[1]))
        end
        if length(to_parts) >= 2
            push!(system_names, String(to_parts[1]))
        end
    else
        return errors  # Other coupling types don't have interface/lifting
    end

    # 4. Validate interface reference
    if iface_field !== nothing
        if iface_field ∉ interface_names
            push!(errors, StructuralError(
                "$path.interface",
                "Interface '$(iface_field)' not found in interfaces",
                "undefined_interface"
            ))
        end
    end

    # 5. Validate lifting: only valid when source or target is 0D
    if lifting_field !== nothing && !isempty(system_names)
        has_0d_system = false
        for sys_name in system_names
            domain = get_system_domain(file, sys_name)
            if domain === nothing  # 0D system (no domain)
                has_0d_system = true
                break
            end
        end
        if !has_0d_system
            push!(errors, StructuralError(
                "$path.lifting",
                "Lifting '$(lifting_field)' is only valid when source or target is 0D (domain is null), but all systems have domains",
                "invalid_lifting"
            ))
        end
    end

    return errors
end

"""
Well-known physical constants whose declared units can be dimensionally
verified against a canonical form. Conservative on purpose — names chosen
to minimize collision with common non-constant uses (e.g., no `c` for
speed of light, which conflicts with concentration). Mirrors Python's
`_KNOWN_PHYSICAL_CONSTANTS` (gt-j91l / gt-3tgv).

Each tuple is (name, canonical_units, description).
"""
const _KNOWN_PHYSICAL_CONSTANTS = (
    ("R", "J/(mol*K)", "ideal gas constant"),
    ("k_B", "J/K", "Boltzmann constant"),
    ("N_A", "1/mol", "Avogadro constant"),
)

# Returns true when the expression tree references a variable by exact name
# (string leaf match). Walks operator arg lists recursively.
function _expr_references_name(expr, name::String)::Bool
    if expr isa VarExpr
        return expr.name == name
    elseif expr isa OpExpr
        for arg in expr.args
            if _expr_references_name(arg, name)
                return true
            end
        end
    end
    return false
end

"""
    validate_physical_constant_units(model::Model, path::String) -> Vector{StructuralError}

Flag parameters whose name matches a well-known physical constant but whose
declared units are dimensionally incompatible with the canonical form (e.g.,
`R` declared as `kcal/mol` — missing temperature — instead of `J/(mol*K)`).
Reports at the first observed-variable usage site in the same model;
otherwise at the declaration. Mirrors Python's
`parse._check_physical_constant_units` (gt-3tgv). Recurses into subsystems.
"""
function validate_physical_constant_units(model::Model, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    for (constant_name, canonical, description) in _KNOWN_PHYSICAL_CONSTANTS
        haskey(model.variables, constant_name) || continue
        var = model.variables[constant_name]
        var.type == ParameterVariable || continue
        declared_str = var.units
        (declared_str === nothing || isempty(declared_str)) && continue

        declared_unit = parse_units(String(declared_str))
        canonical_unit = parse_units(canonical)
        (declared_unit === nothing || canonical_unit === nothing) && continue
        dimension(declared_unit) == dimension(canonical_unit) && continue

        usage_name = nothing
        for (other_name, other_var) in model.variables
            other_var.type == ObservedVariable || continue
            other_var.expression === nothing && continue
            if _expr_references_name(other_var.expression, constant_name)
                usage_name = other_name
                break
            end
        end
        target = usage_name === nothing ? constant_name : usage_name

        push!(errors, StructuralError(
            "$path/variables/$target",
            "Physical constant used with incorrect dimensional analysis " *
            "(constant '$constant_name' ($description) declared with units '$declared_str', " *
            "expected dimensions compatible with '$canonical')",
            "unit_inconsistency",
        ))
    end

    # Recurse into subsystems
    for (subsys_name, subsys) in model.subsystems
        append!(errors, validate_physical_constant_units(subsys, "$path/subsystems/$subsys_name"))
    end

    return errors
end

# Compute the linear conversion factor from `from_units` to `to_units`, or
# `nothing` when the conversion is affine (e.g., degC → K) or the units can't
# be parsed/converted. A conversion is linear iff 0 `from_units` converts to
# 0 `to_units` (within tolerance).
function _linear_conversion_factor(from_units::String, to_units::String)::Union{Float64,Nothing}
    from_unit = parse_units(from_units)
    to_unit = parse_units(to_units)
    (from_unit === nothing || to_unit === nothing) && return nothing
    dimension(from_unit) == dimension(to_unit) || return nothing
    try
        q0 = Unitful.ustrip(Unitful.uconvert(to_unit, 0.0 * from_unit))
        q1 = Unitful.ustrip(Unitful.uconvert(to_unit, 1.0 * from_unit))
        abs(q0) > 1e-12 && return nothing  # affine
        return Float64(q1)
    catch
        return nothing
    end
end

"""
    validate_conversion_factor_consistency(model::Model, path::String) -> Vector{StructuralError}

Flag observed variables whose defining expression is `<numeric> * <var>`
(or `<var> * <numeric>`) where the declared units and the source variable's
units are dimensionally compatible but the numeric literal disagrees with the
correct linear conversion factor. Only linear (non-affine) conversions are
checked. Mirrors Python's `parse._check_conversion_factor_consistency`
(gt-nvdv). Recurses into subsystems.
"""
function validate_conversion_factor_consistency(model::Model, path::String)::Vector{StructuralError}
    errors = StructuralError[]

    for (vname, var) in model.variables
        var.type == ObservedVariable || continue
        lhs_units = var.units
        (lhs_units === nothing || isempty(lhs_units)) && continue
        expr = var.expression
        expr isa OpExpr || continue
        expr.op == "*" || continue
        length(expr.args) == 2 || continue

        numeric = nothing
        var_ref = nothing
        for a in expr.args
            if a isa NumExpr
                numeric = Float64(a.value)
            elseif a isa IntExpr
                numeric = Float64(a.value)
            elseif a isa VarExpr
                var_ref = a.name
            end
        end
        (numeric === nothing || var_ref === nothing) && continue

        src_var = get(model.variables, var_ref, nothing)
        src_var === nothing && continue
        src_units = src_var.units
        (src_units === nothing || isempty(src_units)) && continue

        # Skip identical unit strings — no conversion to check.
        src_units == lhs_units && continue

        factor = _linear_conversion_factor(String(src_units), String(lhs_units))
        (factor === nothing || factor == 0) && continue
        abs(numeric - factor) <= 1e-9 * max(abs(factor), 1.0) && continue

        push!(errors, StructuralError(
            "$path/variables/$vname",
            "Unit conversion factor is incorrect for specified unit transformation " *
            "(variable '$vname', declared_units='$lhs_units', source_units='$src_units', " *
            "declared_factor=$numeric, expected_factor=$factor)",
            "unit_inconsistency",
        ))
    end

    # Recurse into subsystems
    for (subsys_name, subsys) in model.subsystems
        append!(errors, validate_conversion_factor_consistency(subsys, "$path/subsystems/$subsys_name"))
    end

    return errors
end