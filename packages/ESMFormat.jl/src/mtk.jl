"""
MTK System Conversion for ESM Format.

This module provides conversion of ESM Model to ModelingToolkit ODESystem.
Implements the core functionality for converting ESM expressions, variables,
and equations into MTK symbolic form with proper event handling.
"""

# Use shared availability checking from availability.jl
# No need for local constants - they are defined in availability.jl

# Also need to load Dates for the now() function
try
    using Dates
catch e
    @warn "Dates not available: $e"
end

# Struct definition for MockMTKSystem
struct MockMTKSystem
    name::String
    states::Vector{String}
    parameters::Vector{String}
    observed_variables::Vector{String}
    equations::Vector{String}
    events::Vector{String}
    metadata::Dict{String, Any}
    advanced_features::Bool
end

"""
    to_mtk_system(model::Model, name::Union{String,Nothing}=nothing)

Convert an ESM Model to a ModelingToolkit ODESystem or MockMTKSystem.

# Arguments
- `model::Model`: ESM model containing variables, equations, and events
- `name::Union{String,Nothing}`: Optional name for the system (defaults to :anonymous)

# Returns
- `ODESystem` or `MockMTKSystem`: Real or mock system depending on availability

# Expression mapping:
- `OpExpr('+')` → +
- `OpExpr('D', wrt='t')` → Differential(t)(var)
- `OpExpr('exp')` → exp
- `OpExpr('Pre')` → Pre
- `OpExpr('grad', dim='y')` → Differential(y)(var)
- `OpExpr('ifelse')` → ifelse
- `NumExpr` → literal
- `VarExpr` → @variables/@parameters based on type

Creates symbolic variables for state vars as functions of t, parameters as plain symbols.
Maps equations to MTK ~ syntax. Maps continuous events to SymbolicContinuousCallback,
discrete events to SymbolicDiscreteCallback.
"""
function to_mtk_system(model::Model, name::Union{String,Nothing}=nothing)
    sys_name = name === nothing ? "anonymous" : name

    # Check MTK availability lazily
    if !check_mtk_availability()
        @info "Using mock MTK system (ModelingToolkit not available)"
        return create_mock_mtk_system_basic(model, sys_name)
    end

    try
        return create_real_mtk_system_basic(model, sys_name)
    catch e
        @warn "Failed to create real MTK system, using mock: $e"
        return create_mock_mtk_system_basic(model, sys_name)
    end
end

"""
    create_mock_mtk_system_basic(model::Model, name::String) -> MockMTKSystem

Create a mock MTK system for testing when ModelingToolkit is not available.
"""
function create_mock_mtk_system_basic(model::Model, name::String)
    states = String[]
    parameters = String[]
    observed_vars = String[]

    # Process variables
    for (var_name, model_var) in model.variables
        if model_var.type == StateVariable
            push!(states, var_name)
        elseif model_var.type == ParameterVariable
            push!(parameters, var_name)
        elseif model_var.type == ObservedVariable
            push!(observed_vars, var_name)
        end
    end

    equations = ["equation_$i" for i in 1:length(model.equations)]

    # Process both discrete and continuous events
    events = []
    for (i, event) in enumerate(model.discrete_events)
        push!(events, "discrete_event_$i: trigger=$(typeof(event.trigger))")
    end
    for (i, event) in enumerate(model.continuous_events)
        push!(events, "continuous_event_$i: conditions=$(length(event.conditions))")
    end

    # Try to get current time, fallback if not available
    current_time = try
        string(Dates.now())
    catch
        "unknown_time"
    end

    metadata = Dict{String, Any}(
        "creation_time" => current_time,
        "esm_variables_count" => length(model.variables),
        "esm_equations_count" => length(model.equations),
        "esm_discrete_events_count" => length(model.discrete_events),
        "esm_continuous_events_count" => length(model.continuous_events),
        "advanced_features_enabled" => false,
        "mock_system" => true
    )

    return MockMTKSystem(name, states, parameters, observed_vars, equations, events, metadata, false)
end

# Real MTK system creation when ModelingToolkit is available
function create_real_mtk_system_basic(model::Model, name::String)
    # Import ModelingToolkit symbols into current scope
    @eval using ModelingToolkit: @variables, @parameters, ODESystem, Differential, Equation
    @eval using Symbolics: Num

    # Create time variable
    @eval @variables t
    t_sym = @eval t

    # Create symbolic variables for each model variable
    states = []
    parameters = []
    observed = []
    var_dict = Dict{String, Any}()

    for (var_name, model_var) in model.variables
        if model_var.type == StateVariable
            # Create state variable as function of time
            var_symbol = Symbol(var_name)
            @eval @variables $(var_symbol)(t)
            sym_var = @eval $(var_symbol)
            push!(states, sym_var)
            var_dict[var_name] = sym_var
        elseif model_var.type == ParameterVariable
            # Create parameter
            @eval @parameters $(Symbol(var_name))
            param_var = @eval $(Symbol(var_name))
            push!(parameters, param_var)
            var_dict[var_name] = param_var
        elseif model_var.type == ObservedVariable
            if model_var.expression !== nothing
                # Create observed variable with expression
                expr_sym = esm_to_mtk_expr(model_var.expression, var_dict, t_sym)
                var_symbol = Symbol(var_name)
                @eval @variables $(var_symbol)(t)
                obs_var = @eval $(var_symbol)
                push!(observed, obs_var)
                var_dict[var_name] = obs_var
            end
        end
    end

    # Convert equations
    eqs = []
    for equation in model.equations
        lhs = esm_to_mtk_expr(equation.lhs, var_dict, t_sym)
        rhs = esm_to_mtk_expr(equation.rhs, var_dict, t_sym)

        # Create MTK equation
        mtk_eq = @eval Equation($lhs, $rhs)
        push!(eqs, mtk_eq)
    end

    # Process events and create callbacks
    continuous_callbacks = []
    discrete_callbacks = []

    # Process continuous events
    for event in model.continuous_events
        try
            # Convert all conditions to MTK symbolic expressions
            conditions_mtk = []
            for condition in event.conditions
                cond_mtk = esm_to_mtk_expr(condition, var_dict, t_sym)
                push!(conditions_mtk, cond_mtk)
            end

            # Convert affects to MTK equations
            affects_mtk = []
            for affect in event.affects
                if haskey(var_dict, affect.lhs)
                    target_var = var_dict[affect.lhs]
                    rhs_mtk = esm_to_mtk_expr(affect.rhs, var_dict, t_sym)
                    affect_eq = @eval Equation($target_var, $rhs_mtk)
                    push!(affects_mtk, affect_eq)
                else
                    @warn "Target variable $(affect.lhs) not found for continuous event affect"
                end
            end

            if !isempty(conditions_mtk) && !isempty(affects_mtk)
                # For now, use the first condition (MTK callbacks typically have single condition)
                condition = conditions_mtk[1]
                @eval using ModelingToolkit: SymbolicContinuousCallback
                cb = @eval SymbolicContinuousCallback($condition, $affects_mtk)
                push!(continuous_callbacks, cb)
            end
        catch e
            @warn "Failed to process continuous event: $e"
        end
    end

    # Process discrete events
    for event in model.discrete_events
        try
            # Convert affects to MTK equations
            affects_mtk = []
            for affect in event.affects
                if affect isa FunctionalAffect && haskey(var_dict, affect.target)
                    target_var = var_dict[affect.target]
                    rhs_mtk = esm_to_mtk_expr(affect.expression, var_dict, t_sym)

                    # Handle different operation types
                    if affect.operation == "set"
                        affect_eq = @eval Equation($target_var, $rhs_mtk)
                    elseif affect.operation == "add"
                        affect_eq = @eval Equation($target_var, $target_var + $rhs_mtk)
                    elseif affect.operation == "multiply"
                        affect_eq = @eval Equation($target_var, $target_var * $rhs_mtk)
                    else
                        # Default to set operation
                        affect_eq = @eval Equation($target_var, $rhs_mtk)
                    end
                    push!(affects_mtk, affect_eq)
                else
                    @warn "Target variable $(affect.target) not found for discrete event affect"
                end
            end

            if !isempty(affects_mtk)
                @eval using ModelingToolkit: SymbolicDiscreteCallback

                if event.trigger isa ConditionTrigger
                    # Condition-based discrete event
                    condition = esm_to_mtk_expr(event.trigger.expression, var_dict, t_sym)
                    cb = @eval SymbolicDiscreteCallback($condition, $affects_mtk)
                    push!(discrete_callbacks, cb)
                elseif event.trigger isa PeriodicTrigger
                    # Periodic discrete event - use period as the condition
                    period = event.trigger.period
                    phase = event.trigger.phase
                    # For periodic triggers, we can use a simple periodic callback with the period
                    # Note: This is a simplified implementation
                    cb = @eval SymbolicDiscreteCallback($period, $affects_mtk)
                    push!(discrete_callbacks, cb)
                elseif event.trigger isa PresetTimesTrigger
                    # Preset times trigger - use first time as trigger (simplified)
                    # In a full implementation, we'd create multiple callbacks or handle differently
                    if !isempty(event.trigger.times)
                        first_time = event.trigger.times[1]
                        cb = @eval SymbolicDiscreteCallback($first_time, $affects_mtk)
                        push!(discrete_callbacks, cb)
                    end
                else
                    @warn "Unknown discrete event trigger type: $(typeof(event.trigger))"
                end
            end
        catch e
            @warn "Failed to process discrete event: $e"
        end
    end

    # Create ODESystem with events if any exist
    system_kwargs = Dict(:name => Symbol(name))
    if !isempty(continuous_callbacks)
        system_kwargs[:continuous_events] = continuous_callbacks
    end
    if !isempty(discrete_callbacks)
        system_kwargs[:discrete_events] = discrete_callbacks
    end

    system = @eval ODESystem($eqs, $t_sym, $states, $parameters; $(system_kwargs...))

    return system
end

function esm_to_mtk_expr(expr::Expr, var_dict::Dict{String, Any}, t)
    @eval using Symbolics: Differential

    if expr isa VarExpr
        var_name = expr.name
        if haskey(var_dict, var_name)
            return var_dict[var_name]
        else
            error("Variable $var_name not found in variable dictionary")
        end
    elseif expr isa NumExpr
        return expr.value
    elseif expr isa OpExpr
        if expr.op == "D"
            # Differential operator
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            D = @eval Differential($t)
            return @eval $D($arg)
        elseif expr.op == "+"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left + $right
        elseif expr.op == "-"
            if length(expr.args) == 1
                arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
                return @eval -$arg
            else
                left = esm_to_mtk_expr(expr.args[1], var_dict, t)
                right = esm_to_mtk_expr(expr.args[2], var_dict, t)
                return @eval $left - $right
            end
        elseif expr.op == "*"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left * $right
        elseif expr.op == "/"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left / $right
        elseif expr.op == "^"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left ^ $right
        elseif expr.op == "exp"
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            return @eval exp($arg)
        elseif expr.op == "log"
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            return @eval log($arg)
        elseif expr.op == "sin"
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            return @eval sin($arg)
        elseif expr.op == "cos"
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            return @eval cos($arg)
        elseif expr.op == "tan"
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            return @eval tan($arg)
        elseif expr.op == "ifelse"
            # ifelse(condition, true_value, false_value)
            condition = esm_to_mtk_expr(expr.args[1], var_dict, t)
            true_val = esm_to_mtk_expr(expr.args[2], var_dict, t)
            false_val = esm_to_mtk_expr(expr.args[3], var_dict, t)
            return @eval ifelse($condition, $true_val, $false_val)
        elseif expr.op == "Pre"
            # Pre operator - previous value (for discrete events)
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            @eval using ModelingToolkit: Pre
            return @eval Pre($arg)
        elseif expr.op == "grad"
            # Gradient operator with respect to spatial dimension
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            if expr.dim !== nothing
                dim_var = Symbol(expr.dim)
                @eval @variables $(dim_var)
                dim_sym = @eval $(dim_var)
                D = @eval Differential($dim_sym)
                return @eval $D($arg)
            else
                error("grad operator requires dim parameter")
            end
        elseif expr.op == "div"
            # Divergence operator with respect to spatial dimension
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            if expr.dim !== nothing
                dim_var = Symbol(expr.dim)
                @eval @variables $(dim_var)
                dim_sym = @eval $(dim_var)
                D = @eval Differential($dim_sym)
                return @eval $D($arg)
            else
                error("div operator requires dim parameter")
            end
        elseif expr.op == "laplacian"
            # Laplacian operator - second derivative
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            # For simplicity, assume spatial dimension x if not specified
            @eval @variables x
            x_sym = @eval x
            D = @eval Differential($x_sym)
            return @eval $D($D($arg))
        # Comparison operators
        elseif expr.op == ">"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left > $right
        elseif expr.op == "<"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left < $right
        elseif expr.op == ">="
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left >= $right
        elseif expr.op == "<="
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left <= $right
        elseif expr.op == "=="
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left == $right
        elseif expr.op == "!="
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left != $right
        # Logical operators
        elseif expr.op == "&&"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left && $right
        elseif expr.op == "||"
            left = esm_to_mtk_expr(expr.args[1], var_dict, t)
            right = esm_to_mtk_expr(expr.args[2], var_dict, t)
            return @eval $left || $right
        elseif expr.op == "!"
            arg = esm_to_mtk_expr(expr.args[1], var_dict, t)
            return @eval !($arg)
        else
            error("Unsupported operation: $(expr.op)")
        end
    else
        error("Unsupported expression type: $(typeof(expr))")
    end
end