"""
ESM Format JSON Parsing

Provides functionality to load and validate ESM files from JSON strings or files.
Uses manual JSON parsing and type coercion for full control over the deserialization process.
"""

using JSON3
using JSONSchema


"""
    ParseError

Exception thrown when JSON parsing fails.
"""
struct ParseError <: Exception
    message::String
    original_error::Union{Exception,Nothing}

    ParseError(message::String, original_error=nothing) = new(message, original_error)
end


"""
    parse_expression(data::Any) -> Expr

Parse JSON data into an Expression (NumExpr, VarExpr, or OpExpr).
Handles the oneOf discriminated union based on JSON structure.
"""
function parse_expression(data::Any)::Expr
    if isa(data, Number)
        return NumExpr(Float64(data))
    elseif isa(data, String)
        return VarExpr(data)
    elseif (isa(data, Dict) || hasfield(typeof(data), :op)) && haskey(data, "op")
        # It's an OpExpr object - handle both Dict and JSON3.Object
        op = string(data["op"])
        args_data = get(data, "args", [])
        args = Vector{EarthSciSerialization.Expr}([parse_expression(arg) for arg in args_data])
        wrt = get(data, "wrt", nothing)
        dim = get(data, "dim", nothing)
        return OpExpr(op, args, wrt=wrt, dim=dim)
    elseif hasfield(typeof(data), :op) || (hasmethod(haskey, (typeof(data), String)) && haskey(data, "op"))
        # Handle JSON3.Object specifically
        op = string(data.op)
        args_data = get(data, :args, [])
        args = Vector{EarthSciSerialization.Expr}([parse_expression(arg) for arg in args_data])
        wrt = get(data, :wrt, nothing)
        dim = get(data, :dim, nothing)
        return OpExpr(op, args, wrt=wrt, dim=dim)
    else
        throw(ParseError("Invalid expression format: expected number, string, or object with 'op' field. Got: $(typeof(data))"))
    end
end

"""
    parse_model_variable_type(data::String) -> ModelVariableType

Parse string into ModelVariableType enum.
"""
function parse_model_variable_type(data::String)::ModelVariableType
    if data == "state" || data == "StateVariable"
        return StateVariable
    elseif data == "parameter" || data == "ParameterVariable"
        return ParameterVariable
    elseif data == "observed" || data == "ObservedVariable"
        return ObservedVariable
    else
        throw(ParseError("Invalid ModelVariableType: $data"))
    end
end

"""
    parse_trigger(data::Dict) -> DiscreteEventTrigger

Parse JSON data into a DiscreteEventTrigger based on discriminator fields.
"""
function parse_trigger(data::Dict)::DiscreteEventTrigger
    if haskey(data, "expression")
        return ConditionTrigger(parse_expression(data["expression"]))
    elseif haskey(data, "period")
        period = Float64(data["period"])
        phase = get(data, "phase", 0.0)
        return PeriodicTrigger(period, phase=phase)
    elseif haskey(data, "times")
        times = [Float64(t) for t in data["times"]]
        return PresetTimesTrigger(times)
    else
        throw(ParseError("Invalid DiscreteEventTrigger: no recognized discriminator field"))
    end
end

"""
    coerce_esm_file(data::Any) -> EsmFile

Coerce raw JSON data into properly typed EsmFile with custom union type handling.
"""
function coerce_esm_file(data::Any)::EsmFile
    # Extract required fields
    esm = string(data.esm)
    metadata = coerce_metadata(data.metadata)

    # Extract optional fields with proper null/missing handling
    models = if haskey(data, :models) && data.models !== nothing
        Dict{String,Model}(string(k) => coerce_model(v) for (k, v) in pairs(data.models))
    else
        nothing
    end

    reaction_systems = if haskey(data, :reaction_systems) && data.reaction_systems !== nothing
        Dict{String,ReactionSystem}(string(k) => coerce_reaction_system(v) for (k, v) in pairs(data.reaction_systems))
    else
        nothing
    end

    data_loaders = if haskey(data, :data_loaders) && data.data_loaders !== nothing
        Dict{String,DataLoader}(string(k) => coerce_data_loader(v) for (k, v) in pairs(data.data_loaders))
    else
        nothing
    end

    operators = if haskey(data, :operators) && data.operators !== nothing
        Dict{String,Operator}(string(k) => coerce_operator(v) for (k, v) in pairs(data.operators))
    else
        nothing
    end

    coupling = if haskey(data, :coupling) && data.coupling !== nothing
        CouplingEntry[coerce_coupling_entry(c) for c in data.coupling]
    else
        CouplingEntry[]
    end

    domains = if haskey(data, :domains) && data.domains !== nothing
        Dict{String,Domain}(string(k) => coerce_domain(v) for (k, v) in pairs(data.domains))
    else
        nothing
    end

    interfaces = if haskey(data, :interfaces) && data.interfaces !== nothing
        Dict{String,Interface}(string(k) => coerce_interface(v) for (k, v) in pairs(data.interfaces))
    else
        nothing
    end

    return EsmFile(esm, metadata,
                  models=models,
                  reaction_systems=reaction_systems,
                  data_loaders=data_loaders,
                  operators=operators,
                  coupling=coupling,
                  domains=domains,
                  interfaces=interfaces)
end

"""
    coerce_metadata(data::Any) -> Metadata

Coerce JSON data into Metadata type.
"""
function coerce_metadata(data::Any)::Metadata
    name = string(data.name)
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    authors = haskey(data, :authors) ? [string(a) for a in data.authors] : String[]
    license = haskey(data, :license) && data.license !== nothing ? string(data.license) : nothing
    created = haskey(data, :created) && data.created !== nothing ? string(data.created) : nothing
    modified = haskey(data, :modified) && data.modified !== nothing ? string(data.modified) : nothing
    tags = haskey(data, :tags) ? [string(t) for t in data.tags] : String[]
    references = haskey(data, :references) ? [coerce_reference(r) for r in data.references] : Reference[]

    return Metadata(name,
                   description=description,
                   authors=authors,
                   license=license,
                   created=created,
                   modified=modified,
                   tags=tags,
                   references=references)
end

"""
    coerce_reference(data::Any) -> Reference

Coerce JSON data into Reference type.
"""
function coerce_reference(data::Any)::Reference
    doi = haskey(data, :doi) && data.doi !== nothing ? string(data.doi) : nothing
    citation = haskey(data, :citation) && data.citation !== nothing ? string(data.citation) : nothing
    url = haskey(data, :url) && data.url !== nothing ? string(data.url) : nothing
    notes = haskey(data, :notes) && data.notes !== nothing ? string(data.notes) : nothing

    return Reference(doi=doi, citation=citation, url=url, notes=notes)
end

"""
    coerce_model(data::Any) -> Model

Coerce JSON data into Model type.
"""
function coerce_model(data::Any)::Model
    variables = Dict{String,ModelVariable}()
    for (k, v) in pairs(data.variables)
        variables[string(k)] = coerce_model_variable(v)
    end

    equations = [coerce_equation(eq) for eq in data.equations]

    # Handle new schema format with separate event arrays
    discrete_events = DiscreteEvent[]
    continuous_events = ContinuousEvent[]

    if haskey(data, :discrete_events)
        discrete_events = [coerce_discrete_event(ev) for ev in data.discrete_events]
    end

    if haskey(data, :continuous_events)
        continuous_events = [coerce_continuous_event(ev) for ev in data.continuous_events]
    end

    # Backwards compatibility: handle old 'events' field
    if haskey(data, :events)
        mixed_events = [coerce_event(ev) for ev in data.events]
        return create_model_with_mixed_events(variables, equations, mixed_events)
    end

    domain = haskey(data, :domain) && data.domain !== nothing ? string(data.domain) : nothing

    return Model(variables, equations, discrete_events=discrete_events,
                continuous_events=continuous_events, domain=domain)
end

"""
    coerce_model_variable(data::Any) -> ModelVariable

Coerce JSON data into ModelVariable type.
"""
function coerce_model_variable(data::Any)::ModelVariable
    var_type = parse_model_variable_type(string(data.type))
    default = haskey(data, :default) && data.default !== nothing ? Float64(data.default) : nothing
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    expression = haskey(data, :expression) && data.expression !== nothing ? parse_expression(data.expression) : nothing

    return ModelVariable(var_type,
                        default=default,
                        description=description,
                        expression=expression)
end

"""
    coerce_equation(data::Any) -> Equation

Coerce JSON data into Equation type.
"""
function coerce_equation(data::Any)::Equation
    lhs = parse_expression(data.lhs)
    rhs = parse_expression(data.rhs)
    comment = haskey(data, :_comment) && data._comment !== nothing ? string(data._comment) : nothing
    return Equation(lhs, rhs; _comment=comment)
end

"""
    coerce_event(data::Any) -> EventType

Coerce JSON data into EventType (ContinuousEvent or DiscreteEvent).
"""
function coerce_event(data::Any)::EventType
    if haskey(data, :conditions)
        # ContinuousEvent
        conditions = [parse_expression(c) for c in data.conditions]
        affects = [coerce_affect_equation(a) for a in data.affects]
        description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
        return ContinuousEvent(conditions, affects, description=description)
    elseif haskey(data, :trigger)
        # DiscreteEvent
        trigger = parse_trigger(data.trigger)
        affects = [coerce_functional_affect(a) for a in data.affects]
        description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
        return DiscreteEvent(trigger, affects, description=description)
    else
        throw(ParseError("Invalid EventType: missing 'conditions' or 'trigger' field"))
    end
end

"""
    coerce_discrete_event(data::Any) -> DiscreteEvent

Coerce JSON data specifically into DiscreteEvent.
"""
function coerce_discrete_event(data::Any)::DiscreteEvent
    if !haskey(data, :trigger)
        throw(ParseError("DiscreteEvent requires 'trigger' field"))
    end

    trigger = parse_trigger(data.trigger)
    affects = [coerce_functional_affect(a) for a in data.affects]
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    return DiscreteEvent(trigger, affects, description=description)
end

"""
    coerce_continuous_event(data::Any) -> ContinuousEvent

Coerce JSON data specifically into ContinuousEvent.
"""
function coerce_continuous_event(data::Any)::ContinuousEvent
    if !haskey(data, :conditions)
        throw(ParseError("ContinuousEvent requires 'conditions' field"))
    end

    conditions = [parse_expression(c) for c in data.conditions]
    affects = [coerce_affect_equation(a) for a in data.affects]
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    return ContinuousEvent(conditions, affects, description=description)
end

"""
    coerce_affect_equation(data::Any) -> AffectEquation

Coerce JSON data into AffectEquation type.
"""
function coerce_affect_equation(data::Any)::AffectEquation
    lhs = string(data.lhs)
    rhs = parse_expression(data.rhs)
    return AffectEquation(lhs, rhs)
end

"""
    coerce_functional_affect(data::Any) -> FunctionalAffect

Coerce JSON data into FunctionalAffect type.
"""
function coerce_functional_affect(data::Any)::FunctionalAffect
    target = string(data.target)
    expression = parse_expression(data.expression)
    operation = haskey(data, :operation) ? string(data.operation) : "set"
    return FunctionalAffect(target, expression, operation=operation)
end

"""
    coerce_reaction_system(data::Any) -> ReactionSystem

Coerce JSON data into ReactionSystem type.
"""
function coerce_reaction_system(data::Any)::ReactionSystem
    # Convert species dict to vector - species are now keyed by name
    species = [coerce_species(string(k), v) for (k, v) in pairs(data.species)]
    reactions = [coerce_reaction(r) for r in data.reactions]
    # Convert parameters dict to vector - parameters are now keyed by name
    parameters = haskey(data, :parameters) ? [coerce_parameter(string(k), v) for (k, v) in pairs(data.parameters)] : Parameter[]

    domain = haskey(data, :domain) && data.domain !== nothing ? string(data.domain) : nothing

    return ReactionSystem(species, reactions, parameters=parameters, domain=domain)
end

"""
    coerce_species(name::String, data::Any) -> Species

Coerce JSON data into Species type with explicit name.
"""
function coerce_species(name::String, data::Any)::Species
    units = haskey(data, :units) && data.units !== nothing ? string(data.units) : nothing
    default = haskey(data, :default) && data.default !== nothing ? Float64(data.default) : nothing
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing

    return Species(name, units=units, default=default, description=description)
end

"""
    coerce_reaction(data::Any) -> Reaction

Coerce JSON data into Reaction type.
"""
function coerce_reaction(data::Any)::Reaction
    id = string(data.id)
    name = haskey(data, :name) && data.name !== nothing ? string(data.name) : nothing

    # Handle substrates (can be null for source reactions)
    substrates = if haskey(data, :substrates) && data.substrates !== nothing
        [StoichiometryEntry(string(entry.species), Int(entry.stoichiometry)) for entry in data.substrates]
    else
        nothing
    end

    # Handle products (can be null for sink reactions)
    products = if haskey(data, :products) && data.products !== nothing
        [StoichiometryEntry(string(entry.species), Int(entry.stoichiometry)) for entry in data.products]
    else
        nothing
    end

    rate = parse_expression(data.rate)

    reference = if haskey(data, :reference) && data.reference !== nothing
        coerce_reference(data.reference)
    else
        nothing
    end

    return Reaction(id, substrates, products, rate, name=name, reference=reference)
end

"""
    coerce_parameter(name::String, data::Any) -> Parameter

Coerce JSON data into Parameter type with explicit name.
"""
function coerce_parameter(name::String, data::Any)::Parameter
    default = Float64(data.default)
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    units = haskey(data, :units) && data.units !== nothing ? string(data.units) : nothing

    return Parameter(name, default, description=description, units=units)
end

"""
    coerce_data_loader(data::Any) -> DataLoader

Coerce JSON data into DataLoader type.
"""
function coerce_data_loader(data::Any)::DataLoader
    loader_type = string(data.type)
    loader_id = string(data.loader_id)

    config = haskey(data, :config) ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.config)) : nothing
    reference = haskey(data, :reference) && data.reference !== nothing ? coerce_reference(data.reference) : nothing
    provides = haskey(data, :provides) ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.provides)) : Dict{String,Any}()
    temporal_resolution = haskey(data, :temporal_resolution) && data.temporal_resolution !== nothing ? string(data.temporal_resolution) : nothing
    spatial_resolution = haskey(data, :spatial_resolution) && data.spatial_resolution !== nothing ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.spatial_resolution)) : nothing
    interpolation = haskey(data, :interpolation) && data.interpolation !== nothing ? string(data.interpolation) : nothing

    return DataLoader(loader_type, loader_id, provides,
                     config=config,
                     reference=reference,
                     temporal_resolution=temporal_resolution,
                     spatial_resolution=spatial_resolution,
                     interpolation=interpolation)
end

"""
    coerce_operator(data::Any) -> Operator

Coerce JSON data into Operator type.
"""
function coerce_operator(data::Any)::Operator
    operator_id = string(data.operator_id)
    needed_vars = haskey(data, :needed_vars) ? [string(v) for v in data.needed_vars] : String[]

    reference = haskey(data, :reference) && data.reference !== nothing ? coerce_reference(data.reference) : nothing
    config = haskey(data, :config) && data.config !== nothing ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.config)) : nothing
    modifies = haskey(data, :modifies) && data.modifies !== nothing ? [string(v) for v in data.modifies] : nothing
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing

    return Operator(operator_id, needed_vars,
                   reference=reference,
                   config=config,
                   modifies=modifies,
                   description=description)
end

"""
    coerce_coupling_entry(data::Any) -> CouplingEntry

Coerce JSON data into concrete CouplingEntry subtype based on the 'type' field.
"""
function coerce_coupling_entry(data::Any)::CouplingEntry
    if !(data isa AbstractDict) || !haskey(data, "type")
        throw(ParseError("CouplingEntry must be an object with 'type' field"))
    end

    coupling_type = data["type"]

    if coupling_type == "operator_compose"
        return coerce_operator_compose(data)
    elseif coupling_type == "couple"
        return coerce_couple(data)
    elseif coupling_type == "variable_map"
        return coerce_variable_map(data)
    elseif coupling_type == "operator_apply"
        return coerce_operator_apply(data)
    elseif coupling_type == "callback"
        return coerce_callback(data)
    elseif coupling_type == "event"
        return coerce_event(data)
    else
        throw(ParseError("Unknown coupling type: $coupling_type"))
    end
end

"""
    coerce_operator_compose(data::AbstractDict) -> CouplingOperatorCompose

Parse operator_compose coupling entry.
"""
function coerce_operator_compose(data::AbstractDict)::CouplingOperatorCompose
    if !haskey(data, "systems")
        throw(ParseError("operator_compose requires 'systems' field"))
    end

    systems = Vector{String}(data["systems"])
    translate = get(data, "translate", nothing)
    description = get(data, "description", nothing)
    interface = get(data, "interface", nothing)
    if interface !== nothing
        interface = String(interface)
    end
    lifting = get(data, "lifting", nothing)
    if lifting !== nothing
        lifting = String(lifting)
    end

    return CouplingOperatorCompose(systems; translate=translate, description=description, interface=interface, lifting=lifting)
end

"""
    coerce_couple(data::AbstractDict) -> CouplingCouple

Parse couple coupling entry.
"""
function coerce_couple(data::AbstractDict)::CouplingCouple
    required_fields = ["systems", "connector"]
    for field in required_fields
        if !haskey(data, field)
            throw(ParseError("couple requires '$field' field"))
        end
    end

    systems = Vector{String}(data["systems"])
    connector = Dict{String,Any}(data["connector"])
    description = get(data, "description", nothing)
    interface = get(data, "interface", nothing)
    if interface !== nothing
        interface = String(interface)
    end
    lifting = get(data, "lifting", nothing)
    if lifting !== nothing
        lifting = String(lifting)
    end

    return CouplingCouple(systems, connector; description=description, interface=interface, lifting=lifting)
end

"""
    coerce_variable_map(data::AbstractDict) -> CouplingVariableMap

Parse variable_map coupling entry.
"""
function coerce_variable_map(data::AbstractDict)::CouplingVariableMap
    required_fields = ["from", "to", "transform"]
    for field in required_fields
        if !haskey(data, field)
            throw(ParseError("variable_map requires '$field' field"))
        end
    end

    from = String(data["from"])
    to = String(data["to"])
    transform = String(data["transform"])
    factor = get(data, "factor", nothing)
    if factor !== nothing
        factor = Float64(factor)
    end
    description = get(data, "description", nothing)
    interface = get(data, "interface", nothing)
    if interface !== nothing
        interface = String(interface)
    end
    lifting = get(data, "lifting", nothing)
    if lifting !== nothing
        lifting = String(lifting)
    end

    return CouplingVariableMap(from, to, transform; factor=factor, description=description, interface=interface, lifting=lifting)
end

"""
    coerce_operator_apply(data::AbstractDict) -> CouplingOperatorApply

Parse operator_apply coupling entry.
"""
function coerce_operator_apply(data::AbstractDict)::CouplingOperatorApply
    if !haskey(data, "operator")
        throw(ParseError("operator_apply requires 'operator' field"))
    end

    operator = String(data["operator"])
    description = get(data, "description", nothing)

    return CouplingOperatorApply(operator; description=description)
end

"""
    coerce_callback(data::AbstractDict) -> CouplingCallback

Parse callback coupling entry.
"""
function coerce_callback(data::AbstractDict)::CouplingCallback
    if !haskey(data, "callback_id")
        throw(ParseError("callback requires 'callback_id' field"))
    end

    callback_id = String(data["callback_id"])
    config = get(data, "config", nothing)
    if config !== nothing
        config = Dict{String,Any}(config)
    end
    description = get(data, "description", nothing)

    return CouplingCallback(callback_id; config=config, description=description)
end

"""
    coerce_event(data::AbstractDict) -> CouplingEvent

Parse event coupling entry.
"""
function coerce_event(data::AbstractDict)::CouplingEvent
    if !haskey(data, "event_type")
        throw(ParseError("event requires 'event_type' field"))
    end

    event_type = String(data["event_type"])

    # Parse conditions for continuous events
    conditions = nothing
    if haskey(data, "conditions")
        conditions = [coerce_expression(c) for c in data["conditions"]]
    end

    # Parse trigger for discrete events
    trigger = nothing
    if haskey(data, "trigger")
        trigger = coerce_discrete_event_trigger(data["trigger"])
    end

    # Parse affects (required)
    if !haskey(data, "affects")
        throw(ParseError("event requires 'affects' field"))
    end
    affects = [coerce_affect_equation(a) for a in data["affects"]]

    # Parse optional fields
    affect_neg = nothing
    if haskey(data, "affect_neg") && data["affect_neg"] !== nothing
        affect_neg = [coerce_affect_equation(a) for a in data["affect_neg"]]
    end

    discrete_parameters = nothing
    if haskey(data, "discrete_parameters")
        discrete_parameters = Vector{String}(data["discrete_parameters"])
    end

    root_find = get(data, "root_find", nothing)
    if root_find !== nothing
        root_find = String(root_find)
    end

    reinitialize = get(data, "reinitialize", nothing)
    if reinitialize !== nothing
        reinitialize = Bool(reinitialize)
    end

    description = get(data, "description", nothing)

    return CouplingEvent(event_type, affects;
                        conditions=conditions, trigger=trigger, affect_neg=affect_neg,
                        discrete_parameters=discrete_parameters, root_find=root_find,
                        reinitialize=reinitialize, description=description)
end

"""
    coerce_domain(data::Any) -> Domain

Coerce JSON data into Domain type.
"""
function coerce_domain(data::Any)::Domain
    spatial = haskey(data, :spatial) && data.spatial !== nothing ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.spatial)) : nothing
    temporal = haskey(data, :temporal) && data.temporal !== nothing ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.temporal)) : nothing

    return Domain(spatial=spatial, temporal=temporal)
end

"""
    coerce_interface(data::Any) -> Interface

Coerce JSON data into Interface type.
"""
function coerce_interface(data::Any)::Interface
    domains = [string(d) for d in data.domains]
    dimension_mapping = Dict{String,Any}(string(k) => v for (k, v) in pairs(data.dimension_mapping))
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    regridding = haskey(data, :regridding) && data.regridding !== nothing ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.regridding)) : nothing

    return Interface(domains, dimension_mapping; description=description, regridding=regridding)
end

"""
    load(path::String) -> EsmFile

Load and parse an ESM file from a file path.
"""
function load(path::String)::EsmFile
    open(path, "r") do io
        load(io)
    end
end

"""
    load(io::IO) -> EsmFile

Load and parse an ESM file from an IO stream.
"""
function load(io::IO)::EsmFile
    try
        # Read JSON content
        json_string = read(io, String)
        raw_data = JSON3.read(json_string)

        # Validate schema
        schema_errors = validate_schema(raw_data)
        if !isempty(schema_errors)
            error_msg = "Schema validation failed with $(length(schema_errors)) error(s):\\n"
            for error in schema_errors
                error_msg *= "  - $(error.path): $(error.message) ($(error.keyword))\\n"
            end
            throw(SchemaValidationError(error_msg, schema_errors))
        end

        # Coerce types and return
        return coerce_esm_file(raw_data)

    catch e
        if isa(e, Exception) && hasfield(typeof(e), :msg)
            throw(ParseError("Invalid JSON: $(e.msg)", e))
        else
            rethrow(e)
        end
    end
end