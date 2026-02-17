"""
Code generation for the ESM format

This module provides functions to generate self-contained scripts
from ESM files in multiple target languages:
- Julia: compatible with ModelingToolkit, Catalyst, EarthSciMLBase, and OrdinaryDiffEq
- Python: compatible with SymPy, esm_format, and SciPy
"""

"""
    to_julia_code(file::EsmFile)

Generate a self-contained Julia script from an ESM file.
Returns a string containing Julia code that can be executed.
"""
function to_julia_code(file::EsmFile)
    lines = String[]

    # Header comment
    push!(lines, "# Generated Julia script from ESM file")
    push!(lines, "# ESM version: $(file.esm)")
    if !isnothing(file.metadata) && haskey(file.metadata, :title)
        push!(lines, "# Title: $(file.metadata[:title])")
    end
    if !isnothing(file.metadata) && haskey(file.metadata, :description)
        push!(lines, "# Description: $(file.metadata[:description])")
    end
    push!(lines, "")

    # Using statements
    push!(lines, "# Package imports")
    push!(lines, "using ModelingToolkit")
    push!(lines, "using Catalyst")
    push!(lines, "using EarthSciMLBase")
    push!(lines, "using OrdinaryDiffEq")
    push!(lines, "using Unitful")
    push!(lines, "")

    # Generate models
    if !isnothing(file.models) && !isempty(file.models)
        push!(lines, "# Models")
        for (name, model) in file.models
            append!(lines, generate_model_code(name, model))
            push!(lines, "")
        end
    end

    # Generate reaction systems
    if !isnothing(file.reaction_systems) && !isempty(file.reaction_systems)
        push!(lines, "# Reaction Systems")
        for (name, reaction_system) in file.reaction_systems
            append!(lines, generate_reaction_system_code(name, reaction_system))
            push!(lines, "")
        end
    end

    # Generate events
    if !isnothing(file.events) && !isempty(file.events)
        push!(lines, "# Events")
        for (name, event) in file.events
            append!(lines, generate_event_code(name, event))
            push!(lines, "")
        end
    end

    # Generate coupling as TODO comments
    if !isnothing(file.coupling) && !isempty(file.coupling)
        push!(lines, "# Coupling (TODO)")
        for coupling in file.coupling
            append!(lines, generate_coupling_comment(coupling))
        end
        push!(lines, "")
    end

    # Generate domain as TODO comment
    if !isnothing(file.domain)
        push!(lines, "# Domain (TODO)")
        append!(lines, generate_domain_comment(file.domain))
        push!(lines, "")
    end

    # Generate solver as TODO comment
    if !isnothing(file.solver)
        push!(lines, "# Solver (TODO)")
        append!(lines, generate_solver_comment(file.solver))
        push!(lines, "")
    end

    # Generate data loaders as TODO comments
    if !isnothing(file.data_loaders) && !isempty(file.data_loaders)
        push!(lines, "# Data Loaders (TODO)")
        for (name, data_loader) in file.data_loaders
            append!(lines, generate_data_loader_comment(name, data_loader))
        end
        push!(lines, "")
    end

    return join(lines, "\n")
end

"""
    to_python_code(file::EsmFile)

Generate a self-contained Python script from an ESM file.
Returns a string containing Python code that can be executed.
"""
function to_python_code(file::EsmFile)
    lines = String[]

    # Header comment
    push!(lines, "# Generated Python script from ESM file")
    push!(lines, "# ESM version: $(file.esm)")
    if !isnothing(file.metadata) && haskey(file.metadata, :title)
        push!(lines, "# Title: $(file.metadata[:title])")
    end
    if !isnothing(file.metadata) && haskey(file.metadata, :description)
        push!(lines, "# Description: $(file.metadata[:description])")
    end
    push!(lines, "")

    # Import statements
    push!(lines, "# Package imports")
    push!(lines, "import sympy as sp")
    push!(lines, "import esm_format as esm")
    push!(lines, "import scipy")
    push!(lines, "from sympy import Function")
    push!(lines, "")

    # Generate models
    if !isnothing(file.models) && !isempty(file.models)
        push!(lines, "# Models")
        for (name, model) in file.models
            append!(lines, generate_python_model_code(name, model))
            push!(lines, "")
        end
    end

    # Generate reaction systems
    if !isnothing(file.reaction_systems) && !isempty(file.reaction_systems)
        push!(lines, "# Reaction Systems")
        for (name, reaction_system) in file.reaction_systems
            append!(lines, generate_python_reaction_system_code(name, reaction_system))
            push!(lines, "")
        end
    end

    # Generate simulation stub
    push!(lines, "# Simulation setup (TODO: Configure parameters)")
    push!(lines, "tspan = (0, 10)  # time span")
    push!(lines, "parameters = {}  # parameter values")
    push!(lines, "initial_conditions = {}  # initial values")
    push!(lines, "")
    push!(lines, "# result = esm.simulate(tspan=tspan, parameters=parameters, initial_conditions=initial_conditions)")
    push!(lines, "")

    # Generate TODO comments for other features
    if !isnothing(file.coupling) && !isempty(file.coupling)
        push!(lines, "# Coupling (TODO)")
        for coupling in file.coupling
            append!(lines, generate_python_coupling_comment(coupling))
        end
        push!(lines, "")
    end

    if !isnothing(file.domain)
        push!(lines, "# Domain (TODO)")
        append!(lines, generate_python_domain_comment(file.domain))
        push!(lines, "")
    end

    if !isnothing(file.solver)
        push!(lines, "# Solver (TODO)")
        append!(lines, generate_python_solver_comment(file.solver))
        push!(lines, "")
    end

    return join(lines, "\n")
end

# Helper functions for Julia code generation

function generate_model_code(name::String, model::Model)
    lines = String[]

    push!(lines, "# Model: $name")

    # Collect state variables and parameters
    state_vars = ModelVariable[]
    parameters = ModelVariable[]

    if !isnothing(model.variables) && !isempty(model.variables)
        for variable in values(model.variables)
            if variable.type == StateVariable
                push!(state_vars, variable)
            elseif variable.type == ParameterVariable
                push!(parameters, variable)
            end
        end
    end

    # Generate @variables declaration
    if !isempty(state_vars)
        var_decls = join(map(format_variable_declaration, state_vars), " ")
        push!(lines, "@variables t $var_decls")
    end

    # Generate @parameters declaration
    if !isempty(parameters)
        param_decls = join(map(format_variable_declaration, parameters), " ")
        push!(lines, "@parameters $param_decls")
    end

    # Generate equations
    if !isnothing(model.equations) && !isempty(model.equations)
        push!(lines, "")
        push!(lines, "eqs = [")
        for equation in model.equations
            push!(lines, "    $(format_equation(equation)),")
        end
        push!(lines, "]")
    end

    # Generate @named ODESystem
    push!(lines, "")
    push!(lines, "@named $(name)_system = ODESystem(eqs)")

    return lines
end

function generate_reaction_system_code(name::String, reaction_system::ReactionSystem)
    lines = String[]

    push!(lines, "# Reaction System: $name")

    # Generate @species declaration
    if !isnothing(reaction_system.species) && !isempty(reaction_system.species)
        species_decls = join(map(format_species_declaration, values(reaction_system.species)), " ")
        push!(lines, "@species $species_decls")
    end

    # Generate @parameters for reaction parameters
    reaction_params = Set{String}()
    if !isnothing(reaction_system.reactions) && !isempty(reaction_system.reactions)
        for reaction in values(reaction_system.reactions)
            if !isnothing(reaction.rate)
                param_names = extract_parameter_names(reaction.rate)
                union!(reaction_params, param_names)
            end
        end
    end

    if !isempty(reaction_params)
        push!(lines, "@parameters $(join(reaction_params, " "))")
    end

    # Generate reactions
    if !isnothing(reaction_system.reactions) && !isempty(reaction_system.reactions)
        push!(lines, "")
        push!(lines, "rxs = [")
        for reaction in values(reaction_system.reactions)
            push!(lines, "    $(format_reaction(reaction)),")
        end
        push!(lines, "]")
    end

    # Generate @named ReactionSystem
    push!(lines, "")
    push!(lines, "@named $(name)_system = ReactionSystem(rxs)")

    return lines
end

function generate_event_code(name::String, event::Union{ContinuousEvent,DiscreteEvent})
    lines = String[]

    if event isa ContinuousEvent
        push!(lines, "# Continuous Event: $name")
        condition = format_expression(event.condition)
        affect = format_affect(event.affect)
        push!(lines, "$(name)_event = SymbolicContinuousCallback($condition, $affect)")
    else
        push!(lines, "# Discrete Event: $name")
        trigger = format_discrete_trigger(event.trigger)
        affect = format_affect(event.affect)
        push!(lines, "$(name)_event = DiscreteCallback($trigger, $affect)")
    end

    return lines
end

function generate_coupling_comment(coupling::CouplingEntry)
    lines = String[]
    push!(lines, "# TODO: Implement coupling $(typeof(coupling))")
    # Add specific coupling details based on type
    return lines
end

function generate_domain_comment(domain::Domain)
    lines = String[]
    push!(lines, "# TODO: Implement domain")
    if !isnothing(domain.spatial) && haskey(domain.spatial, :coordinates)
        coords = domain.spatial[:coordinates]
        push!(lines, "#   Spatial coordinates: $(join(coords, ", "))")
    end
    return lines
end

function generate_solver_comment(solver::Solver)
    lines = String[]
    push!(lines, "# TODO: Implement solver")
    if !isnothing(solver.strategy)
        push!(lines, "#   Strategy: $(solver.strategy)")
    end
    return lines
end

function generate_data_loader_comment(name::String, data_loader::DataLoader)
    lines = String[]
    push!(lines, "# TODO: Implement data loader $name")
    if haskey(data_loader, :source)
        push!(lines, "#   Source: $(data_loader[:source])")
    end
    return lines
end

function format_variable_declaration(variable::ModelVariable)
    decl = string(variable.name)

    # Add default value and units if present
    parts = String[]
    if !isnothing(variable.default)
        default_val = variable.default
        if isa(default_val, Int)
            push!(parts, "$(default_val).0")
        else
            push!(parts, string(default_val))
        end
    end

    if !isnothing(variable.unit)
        push!(parts, "u\"$(variable.unit)\"")
    end

    if !isempty(parts)
        decl *= "($(join(parts, ", ")))"
    end

    return decl
end

function format_species_declaration(species::Species)
    decl = string(species.name)

    if !isnothing(species.initial_value)
        initial_val = species.initial_value
        if isa(initial_val, Int)
            decl *= "($(initial_val).0)"
        else
            decl *= "($initial_val)"
        end
    end

    return decl
end

function format_equation(equation::Equation)
    lhs = format_expression(equation.lhs)
    rhs = format_expression(equation.rhs)
    return "$lhs ~ $rhs"
end

function format_reaction(reaction::Reaction)
    rate = isnothing(reaction.rate) ? "1.0" : format_expression(reaction.rate)

    # Format reactants
    reactants = if isnothing(reaction.substrates) || isempty(reaction.substrates)
        "∅"
    else
        join([s.stoichiometry != 1 ? "$(s.stoichiometry)*$(s.species)" : s.species
              for s in reaction.substrates], " + ")
    end

    # Format products
    products = if isnothing(reaction.products) || isempty(reaction.products)
        "∅"
    else
        join([p.stoichiometry != 1 ? "$(p.stoichiometry)*$(p.species)" : p.species
              for p in reaction.products], " + ")
    end

    return "Reaction($rate, [$reactants], [$products])"
end

function format_expression(expr::Expr)
    if isa(expr, NumExpr)
        return string(expr.value)
    elseif isa(expr, VarExpr)
        return expr.name
    elseif isa(expr, OpExpr)
        return format_expression_node(expr)
    else
        error("Unsupported expression type: $(typeof(expr))")
    end
end

function format_expression_node(node::OpExpr)
    op = node.op
    args = node.args

    # Apply expression mappings for Julia
    if op == "+"
        return join(map(format_expression, args), " + ")
    elseif op == "*"
        return join(map(format_expression, args), " * ")
    elseif op == "D"
        # D(x,t) → D(x) (remove time parameter)
        if length(args) >= 1
            return "D($(format_expression(args[1])))"
        end
        return "D()"
    elseif op == "exp"
        return "exp($(join(map(format_expression, args), ", ")))"
    elseif op == "ifelse"
        return "ifelse($(join(map(format_expression, args), ", ")))"
    elseif op == "Pre"
        return "Pre($(join(map(format_expression, args), ", ")))"
    elseif op == "^"
        return join(map(format_expression, args), " ^ ")
    elseif op == "grad"
        # grad(x,y) → Differential(y)(x)
        if length(args) >= 2
            return "Differential($(format_expression(args[2])))($(format_expression(args[1])))"
        elseif length(args) == 1
            return "Differential(x)($(format_expression(args[1])))"
        end
        return "Differential(x)()"
    elseif op == "-"
        if length(args) == 1
            return "-$(format_expression(args[1]))"
        else
            return join(map(format_expression, args), " - ")
        end
    elseif op == "/"
        return join(map(format_expression, args), " / ")
    elseif op in ["<", ">", "<=", ">=", "==", "!="]
        return join(map(format_expression, args), " $op ")
    elseif op == "and"
        return join(map(format_expression, args), " && ")
    elseif op == "or"
        return join(map(format_expression, args), " || ")
    elseif op == "not"
        return "!($(format_expression(args[1])))"
    else
        # For other operators, use function call syntax
        return "$op($(join(map(format_expression, args), ", ")))"
    end
end

function format_affect(affect)
    if isa(affect, Vector)
        return "[$(join(map(format_affect_equation, affect), ", "))]"
    elseif !isnothing(affect)
        return format_affect_equation(affect)
    else
        return "nothing"
    end
end

function format_affect_equation(affect)
    if haskey(affect, :lhs) && haskey(affect, :rhs)
        return "$(format_expression(affect[:lhs])) ~ $(format_expression(affect[:rhs]))"
    end
    return "nothing"
end

function format_discrete_trigger(trigger)
    if haskey(trigger, :condition)
        return format_expression(trigger[:condition])
    end
    return "true"
end

function extract_parameter_names(expr::Expr)
    params = Set{String}()

    if isa(expr, VarExpr)
        # Simple heuristic: single letters or names starting with k/K are likely parameters
        if length(expr.name) == 1 || startswith(expr.name, "k") || startswith(expr.name, "K")
            push!(params, expr.name)
        end
    elseif isa(expr, OpExpr)
        for arg in expr.args
            union!(params, extract_parameter_names(arg))
        end
    end

    return params
end

# Helper functions for Python code generation

function generate_python_model_code(name::String, model::Model)
    lines = String[]

    push!(lines, "# Model: $name")

    # Collect state variables and parameters
    state_vars = ModelVariable[]
    parameters = ModelVariable[]

    if !isnothing(model.variables) && !isempty(model.variables)
        for variable in values(model.variables)
            if variable.type == StateVariable
                push!(state_vars, variable)
            elseif variable.type == ParameterVariable
                push!(parameters, variable)
            end
        end
    end

    # Generate time symbol if needed
    has_derivatives = !isnothing(model.equations) &&
        any(eq -> has_derivative_in_expression(eq.lhs) || has_derivative_in_expression(eq.rhs),
            model.equations)

    if has_derivatives
        push!(lines, "# Time variable")
        push!(lines, "t = sp.Symbol('t')")
        push!(lines, "")
    end

    # Generate symbol/function definitions
    if !isempty(state_vars)
        push!(lines, "# State variables")
        for variable in state_vars
            comment = isnothing(variable.unit) ? "" : "  # $(variable.unit)"
            if has_derivatives
                push!(lines, "$(variable.name) = sp.Function('$(variable.name)')$comment")
            else
                push!(lines, "$(variable.name) = sp.Symbol('$(variable.name)')$comment")
            end
        end
        push!(lines, "")
    end

    if !isempty(parameters)
        push!(lines, "# Parameters")
        for parameter in parameters
            comment = isnothing(parameter.unit) ? "" : "  # $(parameter.unit)"
            push!(lines, "$(parameter.name) = sp.Symbol('$(parameter.name)')$comment")
        end
        push!(lines, "")
    end

    # Generate equations
    if !isnothing(model.equations) && !isempty(model.equations)
        push!(lines, "# Equations")
        for (i, equation) in enumerate(model.equations)
            lhs = format_python_expression(equation.lhs)
            rhs = format_python_expression(equation.rhs)
            push!(lines, "eq$i = sp.Eq($lhs, $rhs)")
        end
    end

    return lines
end

function generate_python_reaction_system_code(name::String, reaction_system::ReactionSystem)
    lines = String[]

    push!(lines, "# Reaction System: $name")

    # Generate species symbols
    if !isnothing(reaction_system.species) && !isempty(reaction_system.species)
        push!(lines, "# Species")
        for species in values(reaction_system.species)
            push!(lines, "$(species.name) = sp.Symbol('$(species.name)')")
        end
        push!(lines, "")
    end

    # Generate reaction rate expressions
    if !isnothing(reaction_system.reactions) && !isempty(reaction_system.reactions)
        push!(lines, "# Rate expressions")
        for (reaction_name, reaction) in reaction_system.reactions
            if !isnothing(reaction.rate)
                rate_expr = format_python_expression(reaction.rate)
                push!(lines, "$(reaction_name)_rate = $rate_expr")
            end
        end
        push!(lines, "")

        push!(lines, "# Stoichiometry setup (TODO: Implement reaction network)")
        for (reaction_name, reaction) in reaction_system.reactions
            push!(lines, "# Reaction: $reaction_name")
            if !isnothing(reaction.substrates) && !isempty(reaction.substrates)
                reactant_str = join([s.stoichiometry != 1 ? "$(s.stoichiometry)*$(s.species)" : s.species
                                   for s in reaction.substrates], " + ")
                push!(lines, "#   Reactants: $reactant_str")
            end
            if !isnothing(reaction.products) && !isempty(reaction.products)
                product_str = join([p.stoichiometry != 1 ? "$(p.stoichiometry)*$(p.species)" : p.species
                                  for p in reaction.products], " + ")
                push!(lines, "#   Products: $product_str")
            end
        end
    end

    return lines
end

function generate_python_coupling_comment(coupling::CouplingEntry)
    lines = String[]
    push!(lines, "# TODO: Implement coupling $(typeof(coupling))")
    return lines
end

function generate_python_domain_comment(domain::Domain)
    lines = String[]
    push!(lines, "# TODO: Implement domain")
    if !isnothing(domain.spatial) && haskey(domain.spatial, :coordinates)
        coords = domain.spatial[:coordinates]
        push!(lines, "#   Spatial coordinates: $(join(coords, ", "))")
    end
    return lines
end

function generate_python_solver_comment(solver::Solver)
    lines = String[]
    push!(lines, "# TODO: Implement solver")
    if !isnothing(solver.strategy)
        push!(lines, "#   Strategy: $(solver.strategy)")
    end
    return lines
end

function format_python_expression(expr::Expr)
    if isa(expr, NumExpr)
        return string(expr.value)
    elseif isa(expr, VarExpr)
        return expr.name
    elseif isa(expr, OpExpr)
        return format_python_expression_node(expr)
    else
        error("Unsupported expression type: $(typeof(expr))")
    end
end

function format_python_expression_node(node::OpExpr)
    op = node.op
    args = node.args

    # Apply expression mappings for Python
    if op == "+"
        return join(map(format_python_expression, args), " + ")
    elseif op == "*"
        return join(map(format_python_expression, args), " * ")
    elseif op == "D"
        # D(x,t) → Derivative(x(t), t)
        if length(args) >= 1
            var_name = format_python_expression(args[1])
            return "sp.Derivative($(var_name)(t), t)"
        end
        return "sp.Derivative()"
    elseif op == "exp"
        return "sp.exp($(join(map(format_python_expression, args), ", ")))"
    elseif op == "ifelse"
        # ifelse(condition, true_val, false_val) → sp.Piecewise((true_val, condition), (false_val, True))
        if length(args) >= 3
            condition = format_python_expression(args[1])
            true_val = format_python_expression(args[2])
            false_val = format_python_expression(args[3])
            return "sp.Piecewise(($true_val, $condition), ($false_val, True))"
        end
        return "sp.Piecewise((0, True))"
    elseif op == "Pre"
        return "Function('Pre')($(join(map(format_python_expression, args), ", ")))"
    elseif op == "^"
        return join(map(format_python_expression, args), " ** ")
    elseif op == "grad"
        # grad(x,y) → sp.Derivative(x, y)
        if length(args) >= 2
            func = format_python_expression(args[1])
            var = format_python_expression(args[2])
            return "sp.Derivative($func, $var)"
        elseif length(args) == 1
            return "sp.Derivative($(format_python_expression(args[1])), x)"
        end
        return "sp.Derivative()"
    elseif op == "-"
        if length(args) == 1
            return "-$(format_python_expression(args[1]))"
        else
            return join(map(format_python_expression, args), " - ")
        end
    elseif op == "/"
        return join(map(format_python_expression, args), " / ")
    elseif op in ["<", ">", "<=", ">=", "==", "!="]
        return join(map(format_python_expression, args), " $op ")
    elseif op == "and"
        return join(map(format_python_expression, args), " & ")
    elseif op == "or"
        return join(map(format_python_expression, args), " | ")
    elseif op == "not"
        return "~($(format_python_expression(args[1])))"
    else
        # For other operators, use function call syntax
        return "$op($(join(map(format_python_expression, args), ", ")))"
    end
end

function has_derivative_in_expression(expr::Expr)
    if isa(expr, OpExpr) && expr.op == "D"
        return true
    elseif isa(expr, OpExpr)
        return any(has_derivative_in_expression, expr.args)
    end
    return false
end