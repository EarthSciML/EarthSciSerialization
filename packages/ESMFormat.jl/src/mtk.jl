"""
MTK System Conversion for ESM Format.

This module provides conversion of ESM Model to ModelingToolkit ODESystem.
Implements the core functionality for converting ESM expressions, variables,
and equations into MTK symbolic form with proper event handling.
"""

using ModelingToolkit
using Symbolics

"""
    to_mtk_system(model::Model, name::Union{String,Nothing}=nothing)::ODESystem

Convert an ESM Model to a ModelingToolkit ODESystem.

# Arguments
- `model::Model`: ESM model containing variables, equations, and events
- `name::Union{String,Nothing}`: Optional name for the system (defaults to :anonymous)

# Returns
- `ODESystem`: ModelingToolkit ODESystem representation

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
function to_mtk_system(model::Model, name::Union{String,Nothing}=nothing)::ODESystem
    # Create independent variable (time)
    @variables t

    # Create symbolic variable dictionaries
    symbolic_vars = Dict{String, Any}()
    states = []
    parameters = []

    # Process model variables - create symbolic variables based on type
    for (var_name, model_var) in model.variables
        var_symbol = Symbol(var_name)

        if model_var.type == StateVariable
            # State variables are functions of time: x(t)
            state_var = only(@variables $var_symbol(t))
            symbolic_vars[var_name] = state_var
            push!(states, state_var)

        elseif model_var.type == ParameterVariable
            # Parameters are plain symbols: p
            param_var = only(@variables $var_symbol)
            symbolic_vars[var_name] = param_var
            push!(parameters, param_var)

        elseif model_var.type == ObservedVariable
            # Observed variables are plain symbols, but their expressions will be handled separately
            obs_var = only(@variables $var_symbol)
            symbolic_vars[var_name] = obs_var
        end
    end

    # Convert equations to MTK form
    equations = []
    for eq in model.equations
        lhs_symbolic = esm_to_mtk_expr(eq.lhs, symbolic_vars, t)
        rhs_symbolic = esm_to_mtk_expr(eq.rhs, symbolic_vars, t)
        mtk_eq = lhs_symbolic ~ rhs_symbolic
        push!(equations, mtk_eq)
    end

    # Handle observed variables
    observed = []
    for (var_name, model_var) in model.variables
        if model_var.type == ObservedVariable && model_var.expression !== nothing
            obs_var = symbolic_vars[var_name]
            obs_expr = esm_to_mtk_expr(model_var.expression, symbolic_vars, t)
            push!(observed, obs_var ~ obs_expr)
        end
    end

    # Process events
    continuous_events = []
    discrete_events = []

    for event in model.events
        if event isa ContinuousEvent
            # Convert continuous events to SymbolicContinuousCallback
            condition = esm_to_mtk_expr(event.condition, symbolic_vars, t)

            # Process affects
            affects = []
            for affect in event.affects
                if affect isa AffectEquation
                    target_var = symbolic_vars[affect.lhs]
                    affect_expr = esm_to_mtk_expr(affect.rhs, symbolic_vars, t)
                    push!(affects, target_var ~ affect_expr)
                end
            end

            if hasfield(typeof(event), :affect_neg) && event.affect_neg !== nothing
                # Handle negative affects if present
                affects_neg = []
                for affect in event.affect_neg
                    if affect isa AffectEquation
                        target_var = symbolic_vars[affect.lhs]
                        affect_expr = esm_to_mtk_expr(affect.rhs, symbolic_vars, t)
                        push!(affects_neg, target_var ~ affect_expr)
                    end
                end
                cb = SymbolicContinuousCallback(condition, affects, affect_neg=affects_neg)
            else
                cb = SymbolicContinuousCallback(condition, affects)
            end
            push!(continuous_events, cb)

        elseif event isa DiscreteEvent
            # Convert discrete events to SymbolicDiscreteCallback
            affects = []
            for affect in event.affects
                if affect isa AffectEquation
                    target_var = symbolic_vars[affect.lhs]
                    affect_expr = esm_to_mtk_expr(affect.rhs, symbolic_vars, t)
                    push!(affects, target_var ~ affect_expr)
                elseif affect isa FunctionalAffect
                    target_var = symbolic_vars[affect.target]
                    affect_expr = esm_to_mtk_expr(affect.expression, symbolic_vars, t)

                    # Apply the specified operation
                    if affect.operation == "set"
                        push!(affects, target_var ~ affect_expr)
                    elseif affect.operation == "add"
                        push!(affects, target_var ~ target_var + affect_expr)
                    elseif affect.operation == "multiply"
                        push!(affects, target_var ~ target_var * affect_expr)
                    end
                end
            end

            if event.trigger isa ConditionTrigger
                condition = esm_to_mtk_expr(event.trigger.expression, symbolic_vars, t)
                cb = SymbolicDiscreteCallback(condition, affects)
            elseif event.trigger isa PeriodicTrigger
                cb = SymbolicDiscreteCallback(event.trigger.period, affects)
            elseif event.trigger isa PresetTimesTrigger
                cb = SymbolicDiscreteCallback(event.trigger.times, affects)
            else
                continue  # Skip unknown trigger types
            end
            push!(discrete_events, cb)
        end
    end

    # Build the ODESystem
    sys_kwargs = Dict{Symbol, Any}()
    if !isempty(observed)
        sys_kwargs[:observed] = observed
    end
    if !isempty(continuous_events)
        sys_kwargs[:continuous_events] = continuous_events
    end
    if !isempty(discrete_events)
        sys_kwargs[:discrete_events] = discrete_events
    end

    # Set system name
    if name !== nothing
        sys_kwargs[:name] = Symbol(name)
    else
        sys_kwargs[:name] = :anonymous
    end

    return ODESystem(equations, t, states, parameters; sys_kwargs...)
end

"""
    esm_to_mtk_expr(expr::Expr, var_dict::Dict{String, Any}, t) -> Any

Convert ESM expression to MTK symbolic expression.

Maps ESM expression nodes to MTK symbolic equivalents with proper handling
of differential operators, mathematical functions, and variable references.
"""
function esm_to_mtk_expr(expr::Expr, var_dict::Dict{String, Any}, t)
    if expr isa NumExpr
        return expr.value

    elseif expr isa VarExpr
        if haskey(var_dict, expr.name)
            return var_dict[expr.name]
        else
            # Create a new variable if not found (should not happen in well-formed models)
            var_sym = only(@variables $(Symbol(expr.name)))
            var_dict[expr.name] = var_sym
            return var_sym
        end

    elseif expr isa OpExpr
        # Convert arguments recursively
        args = [esm_to_mtk_expr(arg, var_dict, t) for arg in expr.args]

        # Handle differential operators
        if expr.op == "D"
            if expr.wrt == "t" || expr.wrt === nothing
                # Time derivative: D(x) → Differential(t)(x)
                return Differential(t)(args[1])
            else
                # Spatial derivative: D(x, wrt=y) → Differential(y)(x)
                wrt_var = var_dict[expr.wrt]
                return Differential(wrt_var)(args[1])
            end

        # Handle gradient operator
        elseif expr.op == "grad" && expr.dim !== nothing
            # grad(f, dim=y) → Differential(y)(f)
            dim_var = var_dict[expr.dim]
            return Differential(dim_var)(args[1])

        # Handle Pre operator (previous value)
        elseif expr.op == "Pre"
            # Pre(x) → Pre(x) - MTK handles this internally
            return Pre(args[1])

        # Basic arithmetic operators
        elseif expr.op == "+"
            return length(args) == 1 ? args[1] : sum(args)
        elseif expr.op == "-"
            return length(args) == 1 ? -args[1] : args[1] - sum(args[2:end])
        elseif expr.op == "*"
            return length(args) == 1 ? args[1] : prod(args)
        elseif expr.op == "/"
            return args[1] / args[2]
        elseif expr.op == "^"
            return args[1] ^ args[2]

        # Mathematical functions
        elseif expr.op == "exp"
            return exp(args[1])
        elseif expr.op == "log"
            return log(args[1])
        elseif expr.op == "log10"
            return log10(args[1])
        elseif expr.op == "sin"
            return sin(args[1])
        elseif expr.op == "cos"
            return cos(args[1])
        elseif expr.op == "tan"
            return tan(args[1])
        elseif expr.op == "sqrt"
            return sqrt(args[1])
        elseif expr.op == "abs"
            return abs(args[1])
        elseif expr.op == "max"
            return max(args...)
        elseif expr.op == "min"
            return min(args...)

        # Conditional operator
        elseif expr.op == "ifelse"
            return ifelse(args[1], args[2], args[3])

        else
            # Try to evaluate as a generic function
            try
                func_sym = Symbol(expr.op)
                return eval(func_sym)(args...)
            catch e
                error("Unknown operator: $(expr.op)")
            end
        end
    end

    error("Unknown expression type: $(typeof(expr))")
end