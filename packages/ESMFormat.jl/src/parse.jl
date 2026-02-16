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
        args = Vector{ESMFormat.Expr}([parse_expression(arg) for arg in args_data])
        wrt = get(data, "wrt", nothing)
        dim = get(data, "dim", nothing)
        return OpExpr(op, args, wrt=wrt, dim=dim)
    elseif hasfield(typeof(data), :op) || (hasmethod(haskey, (typeof(data), String)) && haskey(data, "op"))
        # Handle JSON3.Object specifically
        op = string(data.op)
        args_data = get(data, :args, [])
        args = Vector{ESMFormat.Expr}([parse_expression(arg) for arg in args_data])
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

    domain = if haskey(data, :domain) && data.domain !== nothing
        coerce_domain(data.domain)
    else
        nothing
    end

    solver = if haskey(data, :solver) && data.solver !== nothing
        coerce_solver(data.solver)
    else
        nothing
    end

    return EsmFile(esm, metadata,
                  models=models,
                  reaction_systems=reaction_systems,
                  data_loaders=data_loaders,
                  operators=operators,
                  coupling=coupling,
                  domain=domain,
                  solver=solver)
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
    events = haskey(data, :events) ? [coerce_event(ev) for ev in data.events] : EventType[]

    return Model(variables, equations, events=events)
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
    return Equation(lhs, rhs)
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
    species = [coerce_species(s) for s in data.species]
    reactions = [coerce_reaction(r) for r in data.reactions]
    parameters = haskey(data, :parameters) ? [coerce_parameter(p) for p in data.parameters] : Parameter[]

    return ReactionSystem(species, reactions, parameters=parameters)
end

"""
    coerce_species(data::Any) -> Species

Coerce JSON data into Species type.
"""
function coerce_species(data::Any)::Species
    name = string(data.name)
    molecular_weight = haskey(data, :molecular_weight) && data.molecular_weight !== nothing ? Float64(data.molecular_weight) : nothing
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing

    return Species(name, molecular_weight=molecular_weight, description=description)
end

"""
    coerce_reaction(data::Any) -> Reaction

Coerce JSON data into Reaction type.
"""
function coerce_reaction(data::Any)::Reaction
    reactants = Dict{String,Int}(string(k) => Int(v) for (k, v) in pairs(data.reactants))
    products = Dict{String,Int}(string(k) => Int(v) for (k, v) in pairs(data.products))
    rate = parse_expression(data.rate)
    reversible = haskey(data, :reversible) ? Bool(data.reversible) : false

    return Reaction(reactants, products, rate, reversible=reversible)
end

"""
    coerce_parameter(data::Any) -> Parameter

Coerce JSON data into Parameter type.
"""
function coerce_parameter(data::Any)::Parameter
    name = string(data.name)
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
    source = string(data.source)
    parameters = haskey(data, :parameters) ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.parameters)) : Dict{String,Any}()
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing

    return DataLoader(loader_type, source, parameters=parameters, description=description)
end

"""
    coerce_operator(data::Any) -> Operator

Coerce JSON data into Operator type.
"""
function coerce_operator(data::Any)::Operator
    op_type = string(data.type)
    name = string(data.name)
    parameters = haskey(data, :parameters) ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.parameters)) : Dict{String,Any}()
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing

    return Operator(op_type, name, parameters=parameters, description=description)
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
    elseif coupling_type == "couple2"
        return coerce_couple2(data)
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

    return CouplingOperatorCompose(systems; translate=translate, description=description)
end

"""
    coerce_couple2(data::AbstractDict) -> CouplingCouple2

Parse couple2 coupling entry.
"""
function coerce_couple2(data::AbstractDict)::CouplingCouple2
    required_fields = ["systems", "coupletype_pair", "connector"]
    for field in required_fields
        if !haskey(data, field)
            throw(ParseError("couple2 requires '$field' field"))
        end
    end

    systems = Vector{String}(data["systems"])
    coupletype_pair = Vector{String}(data["coupletype_pair"])
    connector = Dict{String,Any}(data["connector"])
    description = get(data, "description", nothing)

    return CouplingCouple2(systems, coupletype_pair, connector; description=description)
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

    return CouplingVariableMap(from, to, transform; factor=factor, description=description)
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
    coerce_solver(data::Any) -> Solver

Coerce JSON data into Solver type.
Supports both old format (algorithm field) and new format (strategy/config fields).
"""
function coerce_solver(data::Any)::Solver
    # Handle legacy format with algorithm field
    if haskey(data, :algorithm)
        @warn "Legacy Solver format with 'algorithm' field is deprecated. Use 'strategy' and 'config' fields instead."
        algorithm = string(data[:algorithm])

        # Convert legacy tolerances to stiff_kwargs format
        tolerances = haskey(data, :tolerances) ?
            Dict{String,Float64}(string(k) => Float64(v) for (k, v) in pairs(data[:tolerances])) :
            Dict("reltol"=>1e-6, "abstol"=>1e-8)

        stiff_kwargs = Dict{String,Any}()
        if haskey(tolerances, "reltol")
            stiff_kwargs["reltol"] = tolerances["reltol"]
        end
        if haskey(tolerances, "abstol")
            stiff_kwargs["abstol"] = tolerances["abstol"]
        end
        # Ensure we always have both tolerances for legacy format
        if !haskey(stiff_kwargs, "reltol")
            stiff_kwargs["reltol"] = 1e-6
        end
        if !haskey(stiff_kwargs, "abstol")
            stiff_kwargs["abstol"] = 1e-8
        end

        # Create configuration from legacy parameters
        extra_parameters = haskey(data, :parameters) ?
            Dict{String,Any}(string(k) => v for (k, v) in pairs(data[:parameters])) :
            Dict{String,Any}()

        config = SolverConfiguration(
            stiff_algorithm=algorithm,
            stiff_kwargs=stiff_kwargs,
            extra_parameters=extra_parameters
        )

        # Default to IMEX strategy for legacy format
        return Solver(IMEX, config)
    end

    # Handle new format with strategy and config
    if !haskey(data, :strategy)
        throw(ArgumentError("Solver must have 'strategy' field"))
    end

    strategy_str = string(data[:strategy])
    strategy = parse_solver_strategy(strategy_str)

    # Parse configuration if present
    config_data = haskey(data, :config) ? data[:config] : nothing
    config = coerce_solver_configuration(config_data)

    return Solver(strategy, config)
end

"""
    coerce_solver_configuration(data::Any) -> SolverConfiguration

Coerce JSON data into SolverConfiguration type.
"""
function coerce_solver_configuration(data)::SolverConfiguration
    if data === nothing
        return SolverConfiguration()
    end

    # Extract basic configuration
    threads = haskey(data, :threads) && data[:threads] !== nothing ? Int(data[:threads]) : nothing
    timestep = haskey(data, :timestep) && data[:timestep] !== nothing ? Float64(data[:timestep]) : nothing

    # Extract algorithm selections
    stiff_algorithm = haskey(data, :stiff_algorithm) && data[:stiff_algorithm] !== nothing ?
        string(data[:stiff_algorithm]) : nothing
    nonstiff_algorithm = haskey(data, :nonstiff_algorithm) && data[:nonstiff_algorithm] !== nothing ?
        string(data[:nonstiff_algorithm]) : nothing
    map_algorithm = haskey(data, :map_algorithm) && data[:map_algorithm] !== nothing ?
        string(data[:map_algorithm]) : nothing

    # Extract stiff solver parameters
    stiff_kwargs = Dict{String,Any}()
    if haskey(data, :stiff_kwargs) && data[:stiff_kwargs] !== nothing
        for (k, v) in pairs(data[:stiff_kwargs])
            stiff_kwargs[string(k)] = v
        end
    else
        # Default tolerances
        stiff_kwargs["abstol"] = 1e-8
        stiff_kwargs["reltol"] = 1e-6
    end

    # Extract numerical method if specified
    numerical_method = nothing
    if haskey(data, :numerical_method) && data[:numerical_method] !== nothing
        numerical_method = parse_numerical_method(string(data[:numerical_method]))
    end

    # Collect any additional parameters
    extra_parameters = Dict{String,Any}()
    for (key, value) in pairs(data)
        key_str = string(key)
        if !(key_str in ["threads", "timestep", "stiff_algorithm", "nonstiff_algorithm",
                        "map_algorithm", "stiff_kwargs", "numerical_method"])
            extra_parameters[key_str] = value
        end
    end

    return SolverConfiguration(
        threads=threads,
        timestep=timestep,
        stiff_algorithm=stiff_algorithm,
        nonstiff_algorithm=nonstiff_algorithm,
        map_algorithm=map_algorithm,
        stiff_kwargs=stiff_kwargs,
        numerical_method=numerical_method,
        extra_parameters=extra_parameters
    )
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