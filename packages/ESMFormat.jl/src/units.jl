"""
Unit validation functionality using Unitful.jl.

This module provides dimensional analysis and unit validation for ESM format
expressions, equations, and models as specified in ESM Libraries Spec Section 3.3.
"""

using Unitful

"""
Parse a unit string into a Unitful.Units object.

Handles common scientific units and compositions used in Earth system models.
"""
function parse_units(unit_str::String)::Union{Unitful.Units, Nothing}
    if isempty(unit_str) || unit_str == "dimensionless"
        return Unitful.NoUnits
    end

    try
        # Handle some common ESM unit patterns
        unit_str = replace(unit_str, r"mol/mol" => "mol/mol")  # Keep as-is for concentration
        unit_str = replace(unit_str, r"\bmol\b" => "mol")
        unit_str = replace(unit_str, r"\bs\b" => "s")
        unit_str = replace(unit_str, r"\bm\b" => "m")
        unit_str = replace(unit_str, r"\bkg\b" => "kg")
        unit_str = replace(unit_str, r"\bK\b" => "K")
        unit_str = replace(unit_str, r"\bPa\b" => "Pa")
        unit_str = replace(unit_str, r"\bJ\b" => "J")

        # Try to parse with Unitful
        parsed = uparse(unit_str)
        # Handle both FreeUnits (for unit strings like "mol/L") and Quantity (for strings like "1/s")
        if isa(parsed, Unitful.Units)
            return parsed  # Already units
        else
            return unit(parsed)  # Extract units from quantity
        end
    catch e
        @warn "Unable to parse unit string: '$unit_str'" exception=e
        return nothing
    end
end

"""
Get the dimensions of an expression by propagating units through operations.

This performs dimensional analysis to determine the units that result from
evaluating an expression, assuming all variables have known units.
"""
function get_expression_dimensions(expr::ESMFormat.Expr, var_units::Dict{String, String})::Union{Unitful.Units, Nothing}
    if expr isa NumExpr
        # Numbers are dimensionless unless specified otherwise
        return Unitful.NoUnits
    elseif expr isa VarExpr
        # Look up variable units
        unit_str = get(var_units, expr.name, "")
        return parse_units(unit_str)
    elseif expr isa OpExpr
        # Handle different operators
        if expr.op == "+"
            # Addition: all arguments must have same dimensions
            arg_dims = [get_expression_dimensions(arg, var_units) for arg in expr.args]

            # Filter out nothing values
            valid_dims = filter(d -> d !== nothing, arg_dims)

            if isempty(valid_dims)
                return nothing
            end

            # Check all dimensions are the same
            first_dim = valid_dims[1]
            for dim in valid_dims[2:end]
                if dimension(dim) != dimension(first_dim)
                    @warn "Dimensional inconsistency in addition: $(dimension(first_dim)) + $(dimension(dim))"
                    return nothing
                end
            end

            return first_dim

        elseif expr.op == "-"
            # Subtraction: same as addition
            return get_expression_dimensions(OpExpr("+", expr.args), var_units)

        elseif expr.op == "*"
            # Multiplication: multiply dimensions
            result = Unitful.NoUnits
            for arg in expr.args
                arg_dim = get_expression_dimensions(arg, var_units)
                if arg_dim !== nothing
                    result = result * arg_dim
                end
            end
            return result

        elseif expr.op == "/"
            # Division: divide dimensions
            if length(expr.args) != 2
                @warn "Division operator requires exactly 2 arguments"
                return nothing
            end

            num_dim = get_expression_dimensions(expr.args[1], var_units)
            den_dim = get_expression_dimensions(expr.args[2], var_units)

            if num_dim !== nothing && den_dim !== nothing
                return num_dim / den_dim
            end

            return nothing

        elseif expr.op == "^" || expr.op == "pow"
            # Power: raise dimension to power (exponent must be dimensionless)
            if length(expr.args) != 2
                @warn "Power operator requires exactly 2 arguments"
                return nothing
            end

            base_dim = get_expression_dimensions(expr.args[1], var_units)
            exp_dim = get_expression_dimensions(expr.args[2], var_units)

            if base_dim !== nothing && exp_dim !== nothing
                # Exponent should be dimensionless
                if dimension(exp_dim) != dimension(Unitful.NoUnits)
                    @warn "Exponent in power operation should be dimensionless, got: $(dimension(exp_dim))"
                    return nothing
                end

                # For now, assume integer powers - could be extended for fractional powers
                if expr.args[2] isa NumExpr
                    power = expr.args[2].value
                    if power isa Number && isinteger(power)
                        return base_dim^Int(power)
                    end
                end

                @warn "Power operation with non-integer exponent not fully supported"
                return base_dim  # Fallback
            end

            return nothing

        elseif expr.op in ["sin", "cos", "tan", "exp", "log", "ln", "sqrt"]
            # Transcendental functions: argument should be dimensionless, result is dimensionless
            if length(expr.args) != 1
                @warn "Function $(expr.op) requires exactly 1 argument"
                return nothing
            end

            arg_dim = get_expression_dimensions(expr.args[1], var_units)
            if arg_dim !== nothing && dimension(arg_dim) != dimension(Unitful.NoUnits)
                @warn "Argument to $(expr.op) should be dimensionless, got: $(dimension(arg_dim))"
                return nothing
            end

            return Unitful.NoUnits

        elseif expr.op == "D"
            # Derivative: check if it's a time derivative
            if length(expr.args) != 1
                @warn "Derivative operator D requires exactly 1 argument"
                return nothing
            end

            # Get dimensions of the variable being differentiated
            var_dim = get_expression_dimensions(expr.args[1], var_units)

            # Check what we're differentiating with respect to
            wrt = expr.wrt !== nothing ? expr.wrt : "t"  # Default to time
            wrt_unit_str = get(var_units, wrt, "s")  # Default to seconds
            wrt_dim = parse_units(wrt_unit_str)

            if var_dim !== nothing && wrt_dim !== nothing
                return var_dim / wrt_dim
            end

            return nothing

        else
            @warn "Unknown operator: $(expr.op)"
            return nothing
        end
    else
        @warn "Unknown expression type: $(typeof(expr))"
        return nothing
    end
end

"""
Validate that an equation is dimensionally consistent.

Checks that the left-hand side and right-hand side have the same dimensions.
"""
function validate_equation_dimensions(eq::Equation, var_units::Dict{String, String})::Bool
    lhs_dim = get_expression_dimensions(eq.lhs, var_units)
    rhs_dim = get_expression_dimensions(eq.rhs, var_units)

    if lhs_dim === nothing || rhs_dim === nothing
        @warn "Cannot determine dimensions for equation: $(eq.lhs) = $(eq.rhs)"
        return false
    end

    if dimension(lhs_dim) != dimension(rhs_dim)
        @warn "Dimensional inconsistency in equation: $(eq.lhs) = $(eq.rhs)"
        @warn "  LHS dimensions: $(dimension(lhs_dim))"
        @warn "  RHS dimensions: $(dimension(rhs_dim))"
        return false
    end

    return true
end

"""
Validate dimensions for all equations in a model.

Returns true if all equations are dimensionally consistent.
"""
function validate_model_dimensions(model::Model)::Bool
    # Build variable units dictionary
    var_units = Dict{String, String}()
    for (name, var) in model.variables
        var_units[name] = var.units !== nothing ? var.units : ""
    end

    # Validate each equation
    all_valid = true
    for (i, equation) in enumerate(model.equations)
        if !validate_equation_dimensions(equation, var_units)
            @warn "Equation $i failed dimensional validation"
            all_valid = false
        end
    end

    return all_valid
end

"""
Validate dimensions for all reactions in a reaction system.

For reactions, validates that rate expressions have appropriate dimensions
(typically concentration/time for elementary reactions).
"""
function validate_reaction_system_dimensions(rxn_sys::ReactionSystem)::Bool
    # Build units dictionary
    var_units = Dict{String, String}()

    # Add species units
    for species in rxn_sys.species
        # Use species units field if available, otherwise default to concentration units
        var_units[species.name] = species.units !== nothing ? species.units : "mol/L"
    end

    # Add parameter units
    for param in rxn_sys.parameters
        var_units[param.name] = param.units !== nothing ? param.units : ""
    end

    # Validate each reaction rate
    all_valid = true
    for (i, reaction) in enumerate(rxn_sys.reactions)
        rate_dim = get_expression_dimensions(reaction.rate, var_units)

        if rate_dim !== nothing
            # For mass action kinetics, rate should have dimensions of concentration/time
            # multiplied by concentration^(total_reactant_order - 1)

            # Calculate total reaction order from substrates (reactants)
            total_order = 0
            if reaction.substrates !== nothing
                for substrate in reaction.substrates
                    total_order += substrate.stoichiometry
                end
            end

            # Expected dimensions for rate constant: concentration/time / concentration^total_order
            # = concentration^(1-total_order) / time
            # For zero-order: concentration/time
            # For first-order: 1/time
            # For second-order: 1/(concentration*time)
            expected_conc_power = 1 - total_order

            # This is a simplified check - in practice, rate constant units depend on reaction order
            @debug "Reaction $i rate dimensions: $(dimension(rate_dim))"
            @debug "Reaction $i total order: $total_order, expected concentration power: $expected_conc_power"
        else
            @warn "Cannot determine dimensions for reaction $i rate expression"
            all_valid = false
        end
    end

    return all_valid
end

"""
Validate dimensions for all components in an ESM file.

Returns true if all models and reaction systems pass dimensional validation.
"""
function validate_file_dimensions(file::EsmFile)::Bool
    all_valid = true

    # Validate models
    for (name, model) in file.models
        @info "Validating dimensions for model: $name"
        if !validate_model_dimensions(model)
            @warn "Model $name failed dimensional validation"
            all_valid = false
        end
    end

    # Validate reaction systems
    for (name, rxn_sys) in file.reaction_systems
        @info "Validating dimensions for reaction system: $name"
        if !validate_reaction_system_dimensions(rxn_sys)
            @warn "Reaction system $name failed dimensional validation"
            all_valid = false
        end
    end

    return all_valid
end

"""
Infer appropriate units for a variable based on its usage in equations.

This can help suggest units when they are not explicitly specified.
"""
function infer_variable_units(var_name::String, equations::Vector{Equation}, known_units::Dict{String, String})::Union{String, Nothing}
    # Look for equations where this variable appears
    for eq in equations
        lhs_vars = free_variables(eq.lhs)
        rhs_vars = free_variables(eq.rhs)

        if var_name in lhs_vars
            # Variable appears on LHS - its units should match RHS
            rhs_dim = get_expression_dimensions(eq.rhs, known_units)
            if rhs_dim !== nothing
                return string(rhs_dim)
            end
        elseif var_name in rhs_vars
            # Variable appears on RHS - need more sophisticated analysis
            # This is more complex and would require symbolic manipulation
            continue
        end
    end

    return nothing
end