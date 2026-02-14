"""
ESM Format JSON Parsing

Provides functionality to load and validate ESM files from JSON strings or files.
Uses manual JSON parsing and type coercion for full control over the deserialization process.
"""

using JSON3
using JSONSchema

"""
    SchemaValidationError

Exception thrown when schema validation fails.
Contains detailed error information including paths and messages.
"""
struct SchemaValidationError <: Exception
    message::String
    errors::Vector{Dict{String,Any}}
end

"""
    ParseError

Exception thrown when JSON parsing fails.
"""
struct ParseError <: Exception
    message::String
    original_error::Union{Exception,Nothing}

    ParseError(message::String, original_error=nothing) = new(message, original_error)
end

# Load schema at module initialization
const SCHEMA_PATH = joinpath(@__DIR__, "..", "..", "..", "esm-schema.json")

# Global schema validator
const ESM_SCHEMA = if isfile(SCHEMA_PATH)
    try
        Schema(JSON3.read(read(SCHEMA_PATH, String)))
    catch e
        @warn "Failed to load ESM schema: $e"
        nothing
    end
else
    @warn "ESM schema file not found at $SCHEMA_PATH"
    nothing
end

"""
    validate_schema(data::Any) -> Vector{Dict{String,Any}}

Validate data against the ESM schema.
Returns empty vector if valid, otherwise returns validation errors.
"""
function validate_schema(data::Any)
    if ESM_SCHEMA === nothing
        @warn "Schema validation skipped - schema not loaded"
        return Dict{String,Any}[]
    end

    try
        result = JSONSchema.validate(ESM_SCHEMA, data)
        if result === nothing
            return Dict{String,Any}[]
        else
            # Convert validation result to error format
            return [Dict("message" => string(result), "path" => "/")]
        end
    catch e
        return [Dict("message" => "Schema validation error: $(e)", "path" => "/")]
    end
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

Coerce JSON data into CouplingEntry type (placeholder for now).
"""
function coerce_coupling_entry(data::Any)::CouplingEntry
    # CouplingEntry is abstract - this needs to be implemented based on actual subtypes
    # For now, return a dummy implementation
    throw(ParseError("CouplingEntry parsing not yet implemented"))
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
"""
function coerce_solver(data::Any)::Solver
    algorithm = string(data.algorithm)
    tolerances = haskey(data, :tolerances) ? Dict{String,Float64}(string(k) => Float64(v) for (k, v) in pairs(data.tolerances)) : Dict("rtol"=>1e-6, "atol"=>1e-8)
    max_iterations = haskey(data, :max_iterations) && data.max_iterations !== nothing ? Int(data.max_iterations) : nothing
    parameters = haskey(data, :parameters) ? Dict{String,Any}(string(k) => v for (k, v) in pairs(data.parameters)) : Dict{String,Any}()

    return Solver(algorithm, tolerances=tolerances, max_iterations=max_iterations, parameters=parameters)
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
                error_msg *= "  - $(error["path"]): $(error["message"])\\n"
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