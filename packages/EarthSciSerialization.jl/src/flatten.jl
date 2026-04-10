"""
Coupled System Flattening for ESM Format.

This module provides the `flatten()` function that takes an EsmFile with coupled
systems and produces a FlattenedSystem with dot-namespaced variables. Unlike
`to_coupled_system()` which creates a MockCoupledSystem, `flatten()` produces
a unified representation where all variables are prefixed with their source
system name (e.g., "Atmosphere.temperature", "Ocean.salinity").

This is useful for:
- Inspecting the complete variable space of a coupled system
- Generating code that references all variables by their fully-qualified names
- Debugging coupling relationships
"""

# ========================================
# Types
# ========================================

"""
    FlattenedEquation

An equation in the flattened system with namespaced variables.

# Fields
- `lhs::String`: dot-namespaced variable name (e.g., "Atmosphere.T")
- `rhs::String`: expression string with namespaced references
- `source_system::String`: name of the system this equation originated from
"""
struct FlattenedEquation
    lhs::String
    rhs::String
    source_system::String
end

"""
    FlattenMetadata

Metadata about which systems were flattened and what coupling rules were applied.

# Fields
- `source_systems::Vector{String}`: names of all systems that were flattened
- `coupling_rules::Vector{String}`: human-readable descriptions of coupling rules
"""
struct FlattenMetadata
    source_systems::Vector{String}
    coupling_rules::Vector{String}
end

"""
    FlattenedSystem

A coupled system flattened into a single system with dot-namespaced variables.
All variables from individual models and reaction systems are unified into a single
namespace using "SystemName.variable" dot notation.

# Fields
- `state_variables::Vector{String}`: all state variables with system prefixes
- `parameters::Vector{String}`: all parameters with system prefixes
- `variables::Dict{String, String}`: map from namespaced variable name to its type ("state", "parameter", "observed", "species")
- `equations::Vector{FlattenedEquation}`: all equations with namespaced references
- `metadata::FlattenMetadata`: provenance information about the flattening
"""
struct FlattenedSystem
    state_variables::Vector{String}
    parameters::Vector{String}
    variables::Dict{String, String}
    equations::Vector{FlattenedEquation}
    metadata::FlattenMetadata
end

# ========================================
# Core Flatten Algorithm
# ========================================

"""
    flatten(file::EsmFile) -> FlattenedSystem

Flatten coupled systems into a single system with dot-namespaced variables.

The algorithm:
1. Iterates over all models and reaction_systems in the EsmFile
2. Namespaces all variables by prefixing with "SystemName."
3. Recursively flattens subsystems using nested dot notation (e.g., "System.Sub.var")
4. Processes coupling entries to produce human-readable rule descriptions
5. Returns a unified FlattenedSystem

# Examples
```julia
file = load("coupled_model.esm")
flat = flatten(file)
println(flat.state_variables)  # ["Atmosphere.T", "Ocean.SST", ...]
println(flat.equations[1].lhs) # "Atmosphere.T"
```
"""
function flatten(file::EsmFile)::FlattenedSystem
    state_variables = String[]
    parameters = String[]
    variables = Dict{String, String}()
    equations = Vector{FlattenedEquation}()
    source_systems = String[]

    # Process models
    if file.models !== nothing
        for (name, model) in file.models
            push!(source_systems, name)
            flatten_model!(state_variables, parameters, variables, equations, model, name)
        end
    end

    # Process reaction systems
    if file.reaction_systems !== nothing
        for (name, rsys) in file.reaction_systems
            push!(source_systems, name)
            flatten_reaction_system!(state_variables, parameters, variables, equations, rsys, name)
        end
    end

    # Process coupling entries into human-readable descriptions
    coupling_rules = String[]
    for entry in file.coupling
        push!(coupling_rules, describe_coupling_entry(entry))
    end

    metadata = FlattenMetadata(sort(source_systems), coupling_rules)

    return FlattenedSystem(state_variables, parameters, variables, equations, metadata)
end

# ========================================
# Model Flattening
# ========================================

"""
    flatten_model!(state_variables, parameters, variables, equations, model, prefix)

Flatten a Model into the accumulator vectors, prefixing all variable names with `prefix.`.
Recursively processes subsystems.
"""
function flatten_model!(state_variables::Vector{String},
                        parameters::Vector{String},
                        variables::Dict{String, String},
                        equations::Vector{FlattenedEquation},
                        model::Model,
                        prefix::String)
    # Namespace all variables
    for (var_name, var) in model.variables
        namespaced = "$(prefix).$(var_name)"
        if var.type == StateVariable
            push!(state_variables, namespaced)
            variables[namespaced] = "state"
        elseif var.type == ParameterVariable
            push!(parameters, namespaced)
            variables[namespaced] = "parameter"
        elseif var.type == ObservedVariable
            variables[namespaced] = "observed"
        end
    end

    # Namespace equations
    for eq in model.equations
        lhs_str = namespace_expression(eq.lhs, prefix)
        rhs_str = namespace_expression(eq.rhs, prefix)
        push!(equations, FlattenedEquation(lhs_str, rhs_str, prefix))
    end

    # Recursively process subsystems
    for (sub_name, sub_model) in model.subsystems
        sub_prefix = "$(prefix).$(sub_name)"
        flatten_model!(state_variables, parameters, variables, equations, sub_model, sub_prefix)
    end
end

# ========================================
# Reaction System Flattening
# ========================================

"""
    flatten_reaction_system!(state_variables, parameters, variables, equations, rsys, prefix)

Flatten a ReactionSystem into the accumulator vectors, prefixing all names with `prefix.`.
Species become state variables and reaction rate laws become equations.
Recursively processes subsystems.
"""
function flatten_reaction_system!(state_variables::Vector{String},
                                  parameters::Vector{String},
                                  variables::Dict{String, String},
                                  equations::Vector{FlattenedEquation},
                                  rsys::ReactionSystem,
                                  prefix::String)
    # Namespace species as state variables
    for species in rsys.species
        namespaced = "$(prefix).$(species.name)"
        push!(state_variables, namespaced)
        variables[namespaced] = "species"
    end

    # Namespace parameters
    for param in rsys.parameters
        namespaced = "$(prefix).$(param.name)"
        push!(parameters, namespaced)
        variables[namespaced] = "parameter"
    end

    # Convert reactions to flattened equations
    for reaction in rsys.reactions
        lhs_str = "$(prefix).$(reaction.id)"
        rhs_str = namespace_expression(reaction.rate, prefix)
        push!(equations, FlattenedEquation(lhs_str, rhs_str, prefix))
    end

    # Recursively process subsystems
    for (sub_name, sub_rsys) in rsys.subsystems
        sub_prefix = "$(prefix).$(sub_name)"
        flatten_reaction_system!(state_variables, parameters, variables, equations, sub_rsys, sub_prefix)
    end
end

# ========================================
# Expression Namespacing
# ========================================

"""
    namespace_expression(expr::Expr, prefix::String) -> String

Convert an ESM expression to a string with all variable references prefixed by `prefix.`.
Numeric literals and operators are preserved as-is.
"""
function namespace_expression(expr::Expr, prefix::String)::String
    if isa(expr, NumExpr)
        return format_number_plain(expr.value)
    elseif isa(expr, VarExpr)
        # Check if the variable already contains a dot (already qualified)
        if occursin('.', expr.name)
            return expr.name
        else
            return "$(prefix).$(expr.name)"
        end
    elseif isa(expr, OpExpr)
        return namespace_op_expression(expr, prefix)
    else
        return string(expr)
    end
end

"""
    namespace_op_expression(expr::OpExpr, prefix::String) -> String

Convert an operator expression to a string with namespaced variable references.
"""
function namespace_op_expression(expr::OpExpr, prefix::String)::String
    op = expr.op
    args = expr.args

    # Handle derivative operator specially
    if op == "D" && length(args) >= 1
        inner = namespace_expression(args[1], prefix)
        wrt = expr.wrt !== nothing ? expr.wrt : "t"
        return "D($(inner), $(wrt))"
    end

    # Binary operators
    if length(args) == 2 && op in ["+", "-", "*", "/", "^"]
        left = namespace_expression(args[1], prefix)
        right = namespace_expression(args[2], prefix)
        return "$(left) $(op) $(right)"
    end

    # Unary operators
    if length(args) == 1
        if op == "-"
            return "-($(namespace_expression(args[1], prefix)))"
        else
            return "$(op)($(namespace_expression(args[1], prefix)))"
        end
    end

    # General case: function call notation
    arg_strs = [namespace_expression(a, prefix) for a in args]
    return "$(op)($(join(arg_strs, ", ")))"
end

"""
    format_number_plain(value::Float64) -> String

Format a floating-point number as a plain string, using integer notation for whole numbers.
"""
function format_number_plain(value::Float64)::String
    if isinteger(value) && isfinite(value)
        return string(Int(value))
    else
        return string(value)
    end
end

# ========================================
# Coupling Description
# ========================================

"""
    describe_coupling_entry(entry::CouplingEntry) -> String

Produce a human-readable description of a coupling entry.
"""
function describe_coupling_entry(entry::CouplingEntry)::String
    if entry isa CouplingOperatorCompose
        systems_str = join(entry.systems, " + ")
        desc = "operator_compose($(systems_str))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingCouple
        systems_str = join(entry.systems, " <-> ")
        desc = "couple($(systems_str))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingVariableMap
        desc = "variable_map($(entry.from) -> $(entry.to), transform=$(entry.transform))"
        if entry.factor !== nothing
            desc *= " [factor=$(entry.factor)]"
        end
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingOperatorApply
        desc = "operator_apply($(entry.operator))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingCallback
        desc = "callback($(entry.callback_id))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    elseif entry isa CouplingEvent
        desc = "event($(entry.event_type))"
        if entry.description !== nothing
            desc *= " -- $(entry.description)"
        end
        return desc
    else
        return "unknown_coupling($(typeof(entry)))"
    end
end
