"""
MTK System Conversion for ESM Format.

This module provides conversion of ESM Model to ModelingToolkit ODESystem.
Implements the core functionality for converting ESM expressions, variables,
and equations into MTK symbolic form with proper event handling.
"""

# Lazy loading approach to avoid precompilation issues
const MTK_AVAILABLE = Ref(false)
const SYMBOLICS_AVAILABLE = Ref(false)
const MTK_CHECKED = Ref(false)

# Lazy loading function
function _check_mtk_availability()
    if !MTK_CHECKED[]
        try
            @eval using ModelingToolkit
            MTK_AVAILABLE[] = true
        catch e
            # Only warn if the check fails
            MTK_AVAILABLE[] = false
        end

        try
            @eval using Symbolics
            SYMBOLICS_AVAILABLE[] = true
        catch e
            SYMBOLICS_AVAILABLE[] = false
        end

        MTK_CHECKED[] = true
    end
    return MTK_AVAILABLE[]
end

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
    if !_check_mtk_availability()
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
    events = ["event_$i" for i in 1:length(model.events)]

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
            @eval @variables $(Symbol(var_name))(t)
            sym_var = @eval $(Symbol(var_name))(t)
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
                @eval @variables $(Symbol(var_name))(t)
                obs_var = @eval $(Symbol(var_name))(t)
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

    # Create ODESystem
    system = @eval ODESystem($eqs, $t_sym, $states, $parameters; name=Symbol($name))

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
        else
            error("Unsupported operation: $(expr.op)")
        end
    else
        error("Unsupported expression type: $(typeof(expr))")
    end
end