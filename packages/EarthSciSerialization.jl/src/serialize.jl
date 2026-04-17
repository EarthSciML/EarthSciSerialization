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
        if expr.output_idx !== nothing
            result["output_idx"] = expr.output_idx
        end
        if expr.expr_body !== nothing
            result["expr"] = serialize_expression(expr.expr_body)
        end
        if expr.reduce !== nothing
            result["reduce"] = expr.reduce
        end
        if expr.ranges !== nothing
            result["ranges"] = Dict{String,Any}(k => v for (k, v) in expr.ranges)
        end
        if expr.regions !== nothing
            result["regions"] = expr.regions
        end
        if expr.values !== nothing
            result["values"] = [serialize_expression(v) for v in expr.values]
        end
        if expr.shape !== nothing
            result["shape"] = expr.shape
        end
        if expr.perm !== nothing
            result["perm"] = expr.perm
        end
        if expr.axis !== nothing
            result["axis"] = expr.axis
        end
        if expr.fn !== nothing
            result["fn"] = expr.fn
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
        return Dict("type" => "condition", "expression" => serialize_expression(trigger.expression))
    elseif isa(trigger, PeriodicTrigger)
        result = Dict("type" => "periodic", "interval" => trigger.period)
        if trigger.phase != 0.0
            result["initial_offset"] = trigger.phase
        end
        return result
    elseif isa(trigger, PresetTimesTrigger)
        return Dict("type" => "preset_times", "times" => trigger.times)
    else
        throw(ArgumentError("Unknown DiscreteEventTrigger type: $(typeof(trigger))"))
    end
end

"""
    serialize_discrete_event_trigger(trigger::DiscreteEventTrigger) -> Dict{String,Any}

Alias for serialize_trigger for backward compatibility.
"""
function serialize_discrete_event_trigger(trigger::DiscreteEventTrigger)::Dict{String,Any}
    return serialize_trigger(trigger)
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
        return serialize_discrete_event(event)
    else
        throw(ArgumentError("Unknown EventType: $(typeof(event))"))
    end
end

"""
    serialize_discrete_event(event::DiscreteEvent) -> Dict{String,Any}

Serialize DiscreteEvent to the schema shape. Julia stores event affects as a
Vector{FunctionalAffect}(target, expression, operation) for legacy reasons,
but the schema requires discrete_events[].affects to be an array of
AffectEquation objects ({lhs, rhs}). Emit the schema shape.
"""
function serialize_discrete_event(event::DiscreteEvent)::Dict{String,Any}
    result = Dict{String,Any}(
        "trigger" => serialize_trigger(event.trigger),
        "affects" => [Dict{String,Any}(
            "lhs" => a.target,
            "rhs" => serialize_expression(a.expression),
        ) for a in event.affects]
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
    if var.default_units !== nothing
        result["default_units"] = var.default_units
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
    result = Dict{String,Any}(
        "lhs" => serialize_expression(eq.lhs),
        "rhs" => serialize_expression(eq.rhs)
    )
    if eq._comment !== nothing
        result["_comment"] = eq._comment
    end
    return result
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

    if model.domain !== nothing
        result["domain"] = model.domain
    end

    if model.tolerance !== nothing
        result["tolerance"] = serialize_tolerance(model.tolerance)
    end

    if !isempty(model.tests)
        result["tests"] = [serialize_test(t) for t in model.tests]
    end

    return result
end

"""
    serialize_tolerance(tol::Tolerance) -> Dict{String,Any}
"""
function serialize_tolerance(tol::Tolerance)::Dict{String,Any}
    result = Dict{String,Any}()
    if tol.abs !== nothing
        result["abs"] = tol.abs
    end
    if tol.rel !== nothing
        result["rel"] = tol.rel
    end
    return result
end

"""
    serialize_time_span(span::TimeSpan) -> Dict{String,Any}
"""
function serialize_time_span(span::TimeSpan)::Dict{String,Any}
    return Dict{String,Any}("start" => span.start, "end" => span.stop)
end

"""
    serialize_assertion(a::Assertion) -> Dict{String,Any}
"""
function serialize_assertion(a::Assertion)::Dict{String,Any}
    result = Dict{String,Any}(
        "variable" => a.variable,
        "time" => a.time,
        "expected" => a.expected,
    )
    if a.tolerance !== nothing
        result["tolerance"] = serialize_tolerance(a.tolerance)
    end
    return result
end

"""
    serialize_test(t::Test) -> Dict{String,Any}
"""
function serialize_test(t::EarthSciSerialization.Test)::Dict{String,Any}
    result = Dict{String,Any}(
        "id" => t.id,
        "time_span" => serialize_time_span(t.time_span),
        "assertions" => [serialize_assertion(a) for a in t.assertions],
    )
    if t.description !== nothing
        result["description"] = t.description
    end
    if !isempty(t.initial_conditions)
        result["initial_conditions"] = Dict{String,Any}(
            k => v for (k, v) in t.initial_conditions)
    end
    if !isempty(t.parameter_overrides)
        result["parameter_overrides"] = Dict{String,Any}(
            k => v for (k, v) in t.parameter_overrides)
    end
    if t.tolerance !== nothing
        result["tolerance"] = serialize_tolerance(t.tolerance)
    end
    return result
end

"""
    serialize_species(species::Species) -> Dict{String,Any}

Serialize Species to JSON-compatible format.
Note: Species name is the key in the species dictionary, not a property of the Species object.
"""
function serialize_species(species::Species)::Dict{String,Any}
    result = Dict{String,Any}()
    if species.units !== nothing
        result["units"] = species.units
    end
    if species.default !== nothing
        result["default"] = species.default
    end
    if species.default_units !== nothing
        result["default_units"] = species.default_units
    end
    if species.description !== nothing
        result["description"] = species.description
    end
    return result
end

"""
    serialize_parameter(param::Parameter) -> Dict{String,Any}

Serialize Parameter to JSON-compatible format.
Note: Parameter name is the key in the parameters dictionary, not a property of the Parameter object.
"""
function serialize_parameter(param::Parameter)::Dict{String,Any}
    result = Dict{String,Any}()
    if param.default !== nothing
        result["default"] = param.default
    end
    if param.description !== nothing
        result["description"] = param.description
    end
    if param.units !== nothing
        result["units"] = param.units
    end
    if param.default_units !== nothing
        result["default_units"] = param.default_units
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

    # Use getfield to bypass the legacy getproperty override that converts
    # :products into a Dict{String,Int}. We want the raw
    # Vector{StoichiometryEntry} so serialization can emit schema-compliant
    # {species, stoichiometry} objects.
    substrates_raw = getfield(reaction, :substrates)
    if substrates_raw !== nothing
        result["substrates"] = [
            Dict("species" => entry.species, "stoichiometry" => entry.stoichiometry)
            for entry in substrates_raw
        ]
    else
        result["substrates"] = nothing
    end

    products_raw = getfield(reaction, :products)
    if products_raw !== nothing
        result["products"] = [
            Dict("species" => entry.species, "stoichiometry" => entry.stoichiometry)
            for entry in products_raw
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
        "species" => Dict(s.name => serialize_species(s) for s in rs.species),
        "parameters" => Dict(p.name => serialize_parameter(p) for p in rs.parameters),
        "reactions" => [serialize_reaction(r) for r in rs.reactions]
    )

    if rs.domain !== nothing
        result["domain"] = rs.domain
    end

    if rs.tolerance !== nothing
        result["tolerance"] = serialize_tolerance(rs.tolerance)
    end

    if !isempty(rs.tests)
        result["tests"] = [serialize_test(t) for t in rs.tests]
    end

    return result
end

"""
    serialize_data_loader_source(src::DataLoaderSource) -> Dict{String,Any}
"""
function serialize_data_loader_source(src::DataLoaderSource)::Dict{String,Any}
    result = Dict{String,Any}("url_template" => src.url_template)
    if src.mirrors !== nothing
        result["mirrors"] = src.mirrors
    end
    return result
end

"""
    serialize_data_loader_temporal(t::DataLoaderTemporal) -> Dict{String,Any}
"""
function serialize_data_loader_temporal(t::DataLoaderTemporal)::Dict{String,Any}
    result = Dict{String,Any}()
    t.start !== nothing && (result["start"] = t.start)
    t.stop !== nothing && (result["end"] = t.stop)
    t.file_period !== nothing && (result["file_period"] = t.file_period)
    t.frequency !== nothing && (result["frequency"] = t.frequency)
    t.records_per_file !== nothing && (result["records_per_file"] = t.records_per_file)
    t.time_variable !== nothing && (result["time_variable"] = t.time_variable)
    return result
end

"""
    serialize_data_loader_spatial(s::DataLoaderSpatial) -> Dict{String,Any}
"""
function serialize_data_loader_spatial(s::DataLoaderSpatial)::Dict{String,Any}
    result = Dict{String,Any}(
        "crs" => s.crs,
        "grid_type" => s.grid_type,
    )
    s.staggering !== nothing && (result["staggering"] = s.staggering)
    s.resolution !== nothing && (result["resolution"] = s.resolution)
    s.extent !== nothing && (result["extent"] = s.extent)
    return result
end

"""
    serialize_data_loader_variable(v::DataLoaderVariable) -> Dict{String,Any}
"""
function serialize_data_loader_variable(v::DataLoaderVariable)::Dict{String,Any}
    result = Dict{String,Any}(
        "file_variable" => v.file_variable,
        "units" => v.units,
    )
    if v.unit_conversion !== nothing
        result["unit_conversion"] = v.unit_conversion isa Number ?
            v.unit_conversion : serialize_expression(v.unit_conversion)
    end
    v.description !== nothing && (result["description"] = v.description)
    v.reference !== nothing && (result["reference"] = serialize_reference(v.reference))
    return result
end

"""
    serialize_data_loader_regridding(r::DataLoaderRegridding) -> Dict{String,Any}
"""
function serialize_data_loader_regridding(r::DataLoaderRegridding)::Dict{String,Any}
    result = Dict{String,Any}()
    r.fill_value !== nothing && (result["fill_value"] = r.fill_value)
    r.extrapolation !== nothing && (result["extrapolation"] = r.extrapolation)
    return result
end

"""
    serialize_data_loader(loader::DataLoader) -> Dict{String,Any}

Serialize DataLoader to JSON-compatible format (STAC-like shape).
"""
function serialize_data_loader(loader::DataLoader)::Dict{String,Any}
    result = Dict{String,Any}(
        "kind" => loader.kind,
        "source" => serialize_data_loader_source(loader.source),
        "variables" => Dict{String,Any}(
            k => serialize_data_loader_variable(v) for (k, v) in loader.variables
        ),
    )
    if loader.temporal !== nothing
        result["temporal"] = serialize_data_loader_temporal(loader.temporal)
    end
    if loader.spatial !== nothing
        result["spatial"] = serialize_data_loader_spatial(loader.spatial)
    end
    if loader.regridding !== nothing
        result["regridding"] = serialize_data_loader_regridding(loader.regridding)
    end
    if loader.reference !== nothing
        result["reference"] = serialize_reference(loader.reference)
    end
    if loader.metadata !== nothing
        result["metadata"] = loader.metadata
    end
    return result
end

"""
    serialize_operator(op::Operator) -> Dict{String,Any}

Serialize Operator to JSON-compatible format.
"""
function serialize_operator(op::Operator)::Dict{String,Any}
    result = Dict{String,Any}(
        "operator_id" => op.operator_id,
        "needed_vars" => op.needed_vars
    )
    if op.reference !== nothing
        result["reference"] = serialize_reference(op.reference)
    end
    if op.config !== nothing
        result["config"] = op.config
    end
    if op.modifies !== nothing
        result["modifies"] = op.modifies
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
    elseif entry isa CouplingCouple
        return serialize_couple(entry)
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
    if entry.interface !== nothing
        result["interface"] = entry.interface
    end
    if entry.lifting !== nothing
        result["lifting"] = entry.lifting
    end

    return result
end

"""
    serialize_couple(entry::CouplingCouple) -> Dict{String,Any}

Serialize couple coupling entry.
"""
function serialize_couple(entry::CouplingCouple)::Dict{String,Any}
    result = Dict{String,Any}(
        "type" => "couple",
        "systems" => entry.systems,
        "connector" => entry.connector
    )

    if entry.description !== nothing
        result["description"] = entry.description
    end
    if entry.interface !== nothing
        result["interface"] = entry.interface
    end
    if entry.lifting !== nothing
        result["lifting"] = entry.lifting
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
    if entry.interface !== nothing
        result["interface"] = entry.interface
    end
    if entry.lifting !== nothing
        result["lifting"] = entry.lifting
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
    serialize_interface(iface::Interface) -> Dict{String,Any}

Serialize Interface to JSON-compatible format.
"""
function serialize_interface(iface::Interface)::Dict{String,Any}
    result = Dict{String,Any}(
        "domains" => iface.domains,
        "dimension_mapping" => iface.dimension_mapping
    )
    if iface.description !== nothing
        result["description"] = iface.description
    end
    if iface.regridding !== nothing
        result["regridding"] = iface.regridding
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
    if file.domains !== nothing
        result["domains"] = Dict(k => serialize_domain(v) for (k, v) in file.domains)
    end
    if file.interfaces !== nothing
        result["interfaces"] = Dict(k => serialize_interface(v) for (k, v) in file.interfaces)
    end

    return result
end

"""
    save(file::EsmFile, path::String)
    save(path::String, file::EsmFile)

Save an EsmFile object to a JSON file at the specified path.
Accepts either argument order for ergonomics (file, path) or (path, file).
"""
function save(file::EsmFile, path::String)
    open(path, "w") do io
        save(file, io)
    end
end

save(path::String, file::EsmFile) = save(file, path)

"""
    save(file::EsmFile, io::IO)

Save an EsmFile object to a JSON stream.
"""
function save(file::EsmFile, io::IO)
    serialized = serialize_esm_file(file)
    write(io, JSON3.write(serialized, indent=2))
end