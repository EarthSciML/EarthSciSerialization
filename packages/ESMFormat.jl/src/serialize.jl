"""
ESM Format JSON Serialization

Provides functionality to serialize EsmFile objects to JSON strings.
"""

using JSON3

"""
    serialize_expression(expr::Expr) -> Any

Serialize an Expression to JSON-compatible format.
Handles the union type discrimination.
"""
function serialize_expression(expr::Expr)
    if isa(expr, NumExpr)
        return expr.value
    elseif isa(expr, VarExpr)
        return expr.name
    elseif isa(expr, OpExpr)
        result = Dict{String,Any}(
            "op" => expr.op,
            "args" => [serialize_expression(arg) for arg in expr.args]
        )
        if expr.wrt !== nothing
            result["wrt"] = expr.wrt
        end
        if expr.dim !== nothing
            result["dim"] = expr.dim
        end
        return result
    else
        throw(ArgumentError("Unknown expression type: $(typeof(expr))"))
    end
end

"""
    serialize_model_variable_type(var_type::ModelVariableType) -> String

Serialize ModelVariableType enum to string.
"""
function serialize_model_variable_type(var_type::ModelVariableType)::String
    if var_type == StateVariable
        return "state"
    elseif var_type == ParameterVariable
        return "parameter"
    elseif var_type == ObservedVariable
        return "observed"
    else
        throw(ArgumentError("Unknown ModelVariableType: $(var_type)"))
    end
end

"""
    serialize_trigger(trigger::DiscreteEventTrigger) -> Dict{String,Any}

Serialize DiscreteEventTrigger to JSON-compatible format.
"""
function serialize_trigger(trigger::DiscreteEventTrigger)::Dict{String,Any}
    if isa(trigger, ConditionTrigger)
        return Dict("expression" => serialize_expression(trigger.expression))
    elseif isa(trigger, PeriodicTrigger)
        result = Dict("period" => trigger.period)
        if trigger.phase != 0.0
            result["phase"] = trigger.phase
        end
        return result
    elseif isa(trigger, PresetTimesTrigger)
        return Dict("times" => trigger.times)
    else
        throw(ArgumentError("Unknown DiscreteEventTrigger type: $(typeof(trigger))"))
    end
end

"""
    serialize_event(event::EventType) -> Dict{String,Any}

Serialize EventType to JSON-compatible format.
"""
function serialize_event(event::EventType)::Dict{String,Any}
    if isa(event, ContinuousEvent)
        result = Dict{String,Any}(
            "conditions" => [serialize_expression(c) for c in event.conditions],
            "affects" => [serialize_affect_equation(a) for a in event.affects]
        )
        if event.description !== nothing
            result["description"] = event.description
        end
        return result
    elseif isa(event, DiscreteEvent)
        result = Dict{String,Any}(
            "trigger" => serialize_trigger(event.trigger),
            "affects" => [serialize_functional_affect(a) for a in event.affects]
        )
        if event.description !== nothing
            result["description"] = event.description
        end
        return result
    else
        throw(ArgumentError("Unknown EventType: $(typeof(event))"))
    end
end

"""
    serialize_discrete_event(event::DiscreteEvent) -> Dict{String,Any}

Serialize DiscreteEvent to JSON-compatible format.
"""
function serialize_discrete_event(event::DiscreteEvent)::Dict{String,Any}
    result = Dict{String,Any}(
        "trigger" => serialize_trigger(event.trigger),
        "affects" => [serialize_functional_affect(a) for a in event.affects]
    )
    if event.description !== nothing
        result["description"] = event.description
    end
    return result
end

"""
    serialize_continuous_event(event::ContinuousEvent) -> Dict{String,Any}

Serialize ContinuousEvent to JSON-compatible format.
"""
function serialize_continuous_event(event::ContinuousEvent)::Dict{String,Any}
    result = Dict{String,Any}(
        "conditions" => [serialize_expression(c) for c in event.conditions],
        "affects" => [serialize_affect_equation(a) for a in event.affects]
    )
    if event.description !== nothing
        result["description"] = event.description
    end
    return result
end

"""
    serialize_affect_equation(affect::AffectEquation) -> Dict{String,Any}

Serialize AffectEquation to JSON-compatible format.
"""
function serialize_affect_equation(affect::AffectEquation)::Dict{String,Any}
    return Dict{String,Any}(
        "lhs" => affect.lhs,
        "rhs" => serialize_expression(affect.rhs)
    )
end

"""
    serialize_functional_affect(affect::FunctionalAffect) -> Dict{String,Any}

Serialize FunctionalAffect to JSON-compatible format.
"""
function serialize_functional_affect(affect::FunctionalAffect)::Dict{String,Any}
    result = Dict{String,Any}(
        "target" => affect.target,
        "expression" => serialize_expression(affect.expression)
    )
    if affect.operation != "set"
        result["operation"] = affect.operation
    end
    return result
end

"""
    serialize_model_variable(var::ModelVariable) -> Dict{String,Any}

Serialize ModelVariable to JSON-compatible format.
"""
function serialize_model_variable(var::ModelVariable)::Dict{String,Any}
    result = Dict{String,Any}(
        "type" => serialize_model_variable_type(var.type)
    )
    if var.default !== nothing
        result["default"] = var.default
    end
    if var.description !== nothing
        result["description"] = var.description
    end
    if var.expression !== nothing
        result["expression"] = serialize_expression(var.expression)
    end
    return result
end

"""
    serialize_equation(eq::Equation) -> Dict{String,Any}

Serialize Equation to JSON-compatible format.
"""
function serialize_equation(eq::Equation)::Dict{String,Any}
    return Dict{String,Any}(
        "lhs" => serialize_expression(eq.lhs),
        "rhs" => serialize_expression(eq.rhs)
    )
end

"""
    serialize_model(model::Model) -> Dict{String,Any}

Serialize Model to JSON-compatible format.
"""
function serialize_model(model::Model)::Dict{String,Any}
    result = Dict{String,Any}(
        "variables" => Dict(k => serialize_model_variable(v) for (k, v) in model.variables),
        "equations" => [serialize_equation(eq) for eq in model.equations]
    )

    # Serialize discrete events if present
    if !isempty(model.discrete_events)
        result["discrete_events"] = [serialize_discrete_event(ev) for ev in model.discrete_events]
    end

    # Serialize continuous events if present
    if !isempty(model.continuous_events)
        result["continuous_events"] = [serialize_continuous_event(ev) for ev in model.continuous_events]
    end

    # Add subsystems if present
    if !isempty(model.subsystems)
        result["subsystems"] = Dict(k => serialize_model(v) for (k, v) in model.subsystems)
    end

    return result
end

"""
    serialize_species(species::Species) -> Dict{String,Any}

Serialize Species to JSON-compatible format.
"""
function serialize_species(species::Species)::Dict{String,Any}
    result = Dict{String,Any}("name" => species.name)
    if species.units !== nothing
        result["units"] = species.units
    end
    if species.default !== nothing
        result["default"] = species.default
    end
    if species.description !== nothing
        result["description"] = species.description
    end
    return result
end

"""
    serialize_parameter(param::Parameter) -> Dict{String,Any}

Serialize Parameter to JSON-compatible format.
"""
function serialize_parameter(param::Parameter)::Dict{String,Any}
    result = Dict{String,Any}(
        "name" => param.name,
        "default" => param.default
    )
    if param.description !== nothing
        result["description"] = param.description
    end
    if param.units !== nothing
        result["units"] = param.units
    end
    return result
end

"""
    serialize_reaction(reaction::Reaction) -> Dict{String,Any}

Serialize Reaction to JSON-compatible format.
"""
function serialize_reaction(reaction::Reaction)::Dict{String,Any}
    result = Dict{String,Any}(
        "id" => reaction.id,
        "rate" => serialize_expression(reaction.rate)
    )

    if reaction.name !== nothing
        result["name"] = reaction.name
    end

    # Handle substrates (can be null for source reactions)
    if reaction.substrates !== nothing
        result["substrates"] = [
            Dict("species" => entry.species, "stoichiometry" => entry.stoichiometry)
            for entry in reaction.substrates
        ]
    else
        result["substrates"] = nothing
    end

    # Handle products (can be null for sink reactions)
    if reaction.products !== nothing
        result["products"] = [
            Dict("species" => entry.species, "stoichiometry" => entry.stoichiometry)
            for entry in reaction.products
        ]
    else
        result["products"] = nothing
    end

    if reaction.reference !== nothing
        result["reference"] = serialize_reference(reaction.reference)
    end

    return result
end

"""
    serialize_reaction_system(rs::ReactionSystem) -> Dict{String,Any}

Serialize ReactionSystem to JSON-compatible format.
"""
function serialize_reaction_system(rs::ReactionSystem)::Dict{String,Any}
    result = Dict{String,Any}(
        "species" => [serialize_species(s) for s in rs.species],
        "reactions" => [serialize_reaction(r) for r in rs.reactions]
    )
    if !isempty(rs.parameters)
        result["parameters"] = [serialize_parameter(p) for p in rs.parameters]
    end
    return result
end

"""
    serialize_data_loader(loader::DataLoader) -> Dict{String,Any}

Serialize DataLoader to JSON-compatible format.
"""
function serialize_data_loader(loader::DataLoader)::Dict{String,Any}
    result = Dict{String,Any}(
        "type" => loader.type,
        "source" => loader.source
    )
    if !isempty(loader.parameters)
        result["parameters"] = loader.parameters
    end
    if loader.description !== nothing
        result["description"] = loader.description
    end
    return result
end

"""
    serialize_operator(op::Operator) -> Dict{String,Any}

Serialize Operator to JSON-compatible format.
"""
function serialize_operator(op::Operator)::Dict{String,Any}
    result = Dict{String,Any}(
        "type" => op.type,
        "name" => op.name
    )
    if !isempty(op.parameters)
        result["parameters"] = op.parameters
    end
    if op.description !== nothing
        result["description"] = op.description
    end
    return result
end

"""
    serialize_coupling_entry(entry::CouplingEntry) -> Dict{String,Any}

Serialize CouplingEntry to JSON-compatible format based on concrete type.
"""
function serialize_coupling_entry(entry::CouplingEntry)::Dict{String,Any}
    if entry isa CouplingOperatorCompose
        return serialize_operator_compose(entry)
    elseif entry isa CouplingCouple2
        return serialize_couple2(entry)
    elseif entry isa CouplingVariableMap
        return serialize_variable_map(entry)
    elseif entry isa CouplingOperatorApply
        return serialize_operator_apply(entry)
    elseif entry isa CouplingCallback
        return serialize_callback(entry)
    elseif entry isa CouplingEvent
        return serialize_event(entry)
    else
        throw(ArgumentError("Unknown CouplingEntry type: $(typeof(entry))"))
    end
end

"""
    serialize_operator_compose(entry::CouplingOperatorCompose) -> Dict{String,Any}

Serialize operator_compose coupling entry.
"""
function serialize_operator_compose(entry::CouplingOperatorCompose)::Dict{String,Any}
    result = Dict{String,Any}("type" => "operator_compose", "systems" => entry.systems)

    if entry.translate !== nothing
        result["translate"] = entry.translate
    end
    if entry.description !== nothing
        result["description"] = entry.description
    end

    return result
end

"""
    serialize_couple2(entry::CouplingCouple2) -> Dict{String,Any}

Serialize couple2 coupling entry.
"""
function serialize_couple2(entry::CouplingCouple2)::Dict{String,Any}
    result = Dict{String,Any}(
        "type" => "couple2",
        "systems" => entry.systems,
        "coupletype_pair" => entry.coupletype_pair,
        "connector" => entry.connector
    )

    if entry.description !== nothing
        result["description"] = entry.description
    end

    return result
end

"""
    serialize_variable_map(entry::CouplingVariableMap) -> Dict{String,Any}

Serialize variable_map coupling entry.
"""
function serialize_variable_map(entry::CouplingVariableMap)::Dict{String,Any}
    result = Dict{String,Any}(
        "type" => "variable_map",
        "from" => entry.from,
        "to" => entry.to,
        "transform" => entry.transform
    )

    if entry.factor !== nothing
        result["factor"] = entry.factor
    end
    if entry.description !== nothing
        result["description"] = entry.description
    end

    return result
end

"""
    serialize_operator_apply(entry::CouplingOperatorApply) -> Dict{String,Any}

Serialize operator_apply coupling entry.
"""
function serialize_operator_apply(entry::CouplingOperatorApply)::Dict{String,Any}
    result = Dict{String,Any}("type" => "operator_apply", "operator" => entry.operator)

    if entry.description !== nothing
        result["description"] = entry.description
    end

    return result
end

"""
    serialize_callback(entry::CouplingCallback) -> Dict{String,Any}

Serialize callback coupling entry.
"""
function serialize_callback(entry::CouplingCallback)::Dict{String,Any}
    result = Dict{String,Any}("type" => "callback", "callback_id" => entry.callback_id)

    if entry.config !== nothing
        result["config"] = entry.config
    end
    if entry.description !== nothing
        result["description"] = entry.description
    end

    return result
end

"""
    serialize_event(entry::CouplingEvent) -> Dict{String,Any}

Serialize event coupling entry.
"""
function serialize_event(entry::CouplingEvent)::Dict{String,Any}
    result = Dict{String,Any}(
        "type" => "event",
        "event_type" => entry.event_type,
        "affects" => [serialize_affect_equation(a) for a in entry.affects]
    )

    if entry.conditions !== nothing
        result["conditions"] = [serialize_expression(c) for c in entry.conditions]
    end
    if entry.trigger !== nothing
        result["trigger"] = serialize_discrete_event_trigger(entry.trigger)
    end
    if entry.affect_neg !== nothing
        result["affect_neg"] = [serialize_affect_equation(a) for a in entry.affect_neg]
    end
    if entry.discrete_parameters !== nothing
        result["discrete_parameters"] = entry.discrete_parameters
    end
    if entry.root_find !== nothing
        result["root_find"] = entry.root_find
    end
    if entry.reinitialize !== nothing
        result["reinitialize"] = entry.reinitialize
    end
    if entry.description !== nothing
        result["description"] = entry.description
    end

    return result
end

"""
    serialize_reference(ref::Reference) -> Dict{String,Any}

Serialize Reference to JSON-compatible format.
"""
function serialize_reference(ref::Reference)::Dict{String,Any}
    result = Dict{String,Any}()
    if ref.doi !== nothing
        result["doi"] = ref.doi
    end
    if ref.citation !== nothing
        result["citation"] = ref.citation
    end
    if ref.url !== nothing
        result["url"] = ref.url
    end
    if ref.notes !== nothing
        result["notes"] = ref.notes
    end
    return result
end

"""
    serialize_metadata(metadata::Metadata) -> Dict{String,Any}

Serialize Metadata to JSON-compatible format.
"""
function serialize_metadata(metadata::Metadata)::Dict{String,Any}
    result = Dict{String,Any}("name" => metadata.name)

    if metadata.description !== nothing
        result["description"] = metadata.description
    end
    if !isempty(metadata.authors)
        result["authors"] = metadata.authors
    end
    if metadata.license !== nothing
        result["license"] = metadata.license
    end
    if metadata.created !== nothing
        result["created"] = metadata.created
    end
    if metadata.modified !== nothing
        result["modified"] = metadata.modified
    end
    if !isempty(metadata.tags)
        result["tags"] = metadata.tags
    end
    if !isempty(metadata.references)
        result["references"] = [serialize_reference(r) for r in metadata.references]
    end

    return result
end

"""
    serialize_domain(domain::Domain) -> Dict{String,Any}

Serialize Domain to JSON-compatible format.
"""
function serialize_domain(domain::Domain)::Dict{String,Any}
    result = Dict{String,Any}()
    if domain.spatial !== nothing
        result["spatial"] = domain.spatial
    end
    if domain.temporal !== nothing
        result["temporal"] = domain.temporal
    end
    return result
end

"""
    serialize_solver(solver::Solver) -> Dict{String,Any}

Serialize Solver to JSON-compatible format matching the ESM schema.
"""
function serialize_solver(solver::Solver)::Dict{String,Any}
    result = Dict{String,Any}("strategy" => solver_strategy_to_string(solver.strategy))

    # Serialize configuration
    config_dict = serialize_solver_configuration(solver.config)
    if !isempty(config_dict)
        result["config"] = config_dict
    end

    return result
end

"""
    serialize_solver_configuration(config::SolverConfiguration) -> Dict{String,Any}

Serialize SolverConfiguration to JSON-compatible format.
"""
function serialize_solver_configuration(config::SolverConfiguration)::Dict{String,Any}
    result = Dict{String,Any}()

    # Add basic configuration
    if config.threads !== nothing
        result["threads"] = config.threads
    end

    if config.timestep !== nothing
        result["timestep"] = config.timestep
    end

    # Add algorithm selections
    if config.stiff_algorithm !== nothing
        result["stiff_algorithm"] = config.stiff_algorithm
    end

    if config.nonstiff_algorithm !== nothing
        result["nonstiff_algorithm"] = config.nonstiff_algorithm
    end

    if config.map_algorithm !== nothing
        result["map_algorithm"] = config.map_algorithm
    end

    # Add stiff solver parameters
    if !isempty(config.stiff_kwargs)
        result["stiff_kwargs"] = config.stiff_kwargs
    end

    # Add numerical method if specified
    if config.numerical_method !== nothing
        result["numerical_method"] = numerical_method_to_string(config.numerical_method)
    end

    # Add extra parameters
    for (key, value) in config.extra_parameters
        if !haskey(result, key)  # Don't overwrite existing keys
            result[key] = value
        end
    end

    return result
end

"""
    serialize_esm_file(file::EsmFile) -> Dict{String,Any}

Serialize EsmFile to JSON-compatible format.
"""
function serialize_esm_file(file::EsmFile)::Dict{String,Any}
    result = Dict{String,Any}(
        "esm" => file.esm,
        "metadata" => serialize_metadata(file.metadata)
    )

    if file.models !== nothing
        result["models"] = Dict(k => serialize_model(v) for (k, v) in file.models)
    end
    if file.reaction_systems !== nothing
        result["reaction_systems"] = Dict(k => serialize_reaction_system(v) for (k, v) in file.reaction_systems)
    end
    if file.data_loaders !== nothing
        result["data_loaders"] = Dict(k => serialize_data_loader(v) for (k, v) in file.data_loaders)
    end
    if file.operators !== nothing
        result["operators"] = Dict(k => serialize_operator(v) for (k, v) in file.operators)
    end
    if !isempty(file.coupling)
        result["coupling"] = [serialize_coupling_entry(c) for c in file.coupling]
    end
    if file.domain !== nothing
        result["domain"] = serialize_domain(file.domain)
    end
    if file.solver !== nothing
        result["solver"] = serialize_solver(file.solver)
    end

    return result
end

"""
    save(file::EsmFile, path::String)

Save an EsmFile object to a JSON file at the specified path.
"""
function save(file::EsmFile, path::String)
    open(path, "w") do io
        save(file, io)
    end
end

"""
    save(file::EsmFile, io::IO)

Save an EsmFile object to a JSON stream.
"""
function save(file::EsmFile, io::IO)
    serialized = serialize_esm_file(file)
    write(io, JSON3.write(serialized, indent=2))
end