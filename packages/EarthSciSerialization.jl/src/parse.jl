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
    elseif isa(data, Dict) && haskey(data, "op")
        return _parse_op_dict(data, "op", "args", "wrt", "dim",
                              "output_idx", "expr", "reduce", "ranges",
                              "regions", "values", "shape", "perm", "axis", "fn")
    elseif hasfield(typeof(data), :op) || (hasmethod(haskey, (typeof(data), String)) && haskey(data, "op"))
        return _parse_op_dict(data, :op, :args, :wrt, :dim,
                              :output_idx, :expr, :reduce, :ranges,
                              :regions, :values, :shape, :perm, :axis, :fn)
    else
        throw(ParseError("Invalid expression format: expected number, string, or object with 'op' field. Got: $(typeof(data))"))
    end
end

# Shared implementation for Dict and JSON3.Object parse paths. The key
# arguments are passed as strings for Dict and symbols for JSON3.Object.
function _parse_op_dict(data, kop, kargs, kwrt, kdim,
                        koutput_idx, kexpr, kreduce, kranges,
                        kregions, kvalues, kshape, kperm, kaxis, kfn)
    op = string(data[kop])
    args_data = get(data, kargs, [])
    args = Vector{EarthSciSerialization.Expr}([parse_expression(arg) for arg in args_data])
    wrt = get(data, kwrt, nothing)
    dim = get(data, kdim, nothing)

    output_idx = _coerce_output_idx(get(data, koutput_idx, nothing))
    raw_expr = get(data, kexpr, nothing)
    expr_body = raw_expr === nothing ? nothing : parse_expression(raw_expr)
    reduce_val = get(data, kreduce, nothing)
    reduce_str = reduce_val === nothing ? nothing : string(reduce_val)
    ranges = _coerce_ranges(get(data, kranges, nothing))
    regions = _coerce_regions(get(data, kregions, nothing))
    raw_values = get(data, kvalues, nothing)
    values_vec = raw_values === nothing ? nothing :
        Vector{EarthSciSerialization.Expr}([parse_expression(v) for v in raw_values])
    shape_vec = _coerce_shape(get(data, kshape, nothing))
    perm_raw = get(data, kperm, nothing)
    perm_vec = perm_raw === nothing ? nothing : Vector{Int}([Int(p) for p in perm_raw])
    axis_val = get(data, kaxis, nothing)
    axis_int = axis_val === nothing ? nothing : Int(axis_val)
    fn_val = get(data, kfn, nothing)
    fn_str = fn_val === nothing ? nothing : string(fn_val)

    return OpExpr(op, args;
        wrt=(wrt === nothing ? nothing : string(wrt)),
        dim=(dim === nothing ? nothing : string(dim)),
        output_idx=output_idx, expr_body=expr_body, reduce=reduce_str,
        ranges=ranges, regions=regions, values=values_vec, shape=shape_vec,
        perm=perm_vec, axis=axis_int, fn=fn_str)
end

function _coerce_output_idx(data)
    data === nothing && return nothing
    out = Vector{Any}(undef, length(data))
    for (i, entry) in enumerate(data)
        out[i] = isa(entry, Number) ? Int(entry) : string(entry)
    end
    return out
end

function _coerce_ranges(data)
    data === nothing && return nothing
    result = Dict{String,Vector{Int}}()
    for (k, v) in pairs(data)
        result[string(k)] = Vector{Int}([Int(x) for x in v])
    end
    return result
end

function _coerce_regions(data)
    data === nothing && return nothing
    return Vector{Vector{Vector{Int}}}([
        Vector{Vector{Int}}([Vector{Int}([Int(x) for x in ax]) for ax in region])
        for region in data
    ])
end

function _coerce_shape(data)
    data === nothing && return nothing
    out = Vector{Any}(undef, length(data))
    for (i, entry) in enumerate(data)
        out[i] = isa(entry, Number) ? Int(entry) : string(entry)
    end
    return out
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
    parse_trigger(data) -> DiscreteEventTrigger

Parse JSON data into a DiscreteEventTrigger based on the schema discriminator.

Accepts Dict or JSON3.Object. Uses the "type" field (preferred, per current schema)
with fallback to field-based discrimination for backward compatibility.

Schema-defined variants:
- {"type": "condition", "expression": ...} -> ConditionTrigger
- {"type": "periodic", "interval": ..., "initial_offset": ...} -> PeriodicTrigger
- {"type": "preset_times", "times": [...]} -> PresetTimesTrigger
"""
function parse_trigger(data)::DiscreteEventTrigger
    trigger_type = _get_field(data, :type, nothing)
    trigger_type_str = trigger_type === nothing ? nothing : string(trigger_type)

    if trigger_type_str == "condition" || (trigger_type_str === nothing && _has_field(data, :expression))
        expression = _get_field(data, :expression, nothing)
        if expression === nothing
            throw(ParseError("Condition trigger requires 'expression' field"))
        end
        return ConditionTrigger(parse_expression(expression))
    elseif trigger_type_str == "periodic" || (trigger_type_str === nothing && (_has_field(data, :interval) || _has_field(data, :period)))
        interval_val = _get_field(data, :interval, nothing)
        if interval_val === nothing
            interval_val = _get_field(data, :period, nothing)
        end
        if interval_val === nothing
            throw(ParseError("Periodic trigger requires 'interval' field"))
        end
        period = Float64(interval_val)
        phase_val = _get_field(data, :initial_offset, nothing)
        if phase_val === nothing
            phase_val = _get_field(data, :phase, 0.0)
        end
        phase = Float64(phase_val)
        return PeriodicTrigger(period, phase=phase)
    elseif trigger_type_str == "preset_times" || (trigger_type_str === nothing && _has_field(data, :times))
        times_val = _get_field(data, :times, nothing)
        if times_val === nothing
            throw(ParseError("Preset times trigger requires 'times' field"))
        end
        times = [Float64(t) for t in times_val]
        return PresetTimesTrigger(times)
    else
        throw(ParseError("Invalid DiscreteEventTrigger: unknown type '$(trigger_type_str)' and no recognized discriminator field"))
    end
end

# Field access helpers that work uniformly across Dict and JSON3.Object.
# JSON3.Object haskey only works with Symbol keys; Dict haskey works with either.
function _has_field(data, key::Symbol)
    try
        return haskey(data, key)
    catch
        try
            return haskey(data, string(key))
        catch
            return false
        end
    end
end

function _get_field(data, key::Symbol, default)
    if _has_field(data, key)
        try
            return data[key]
        catch
            try
                return data[string(key)]
            catch
                return default
            end
        end
    end
    return default
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

    # Inline tests / tolerance (schema gt-cc1).
    tolerance = haskey(data, :tolerance) && data.tolerance !== nothing ?
        coerce_tolerance(data.tolerance) : nothing
    tests = haskey(data, :tests) && data.tests !== nothing ?
        EarthSciSerialization.Test[coerce_test(t) for t in data.tests] :
        EarthSciSerialization.Test[]

    return Model(variables, equations;
                 discrete_events=discrete_events,
                 continuous_events=continuous_events,
                 domain=domain,
                 tolerance=tolerance,
                 tests=tests)
end

"""
    coerce_tolerance(data::Any) -> Tolerance

Parse a schema `Tolerance` object into the Julia `Tolerance` struct.
"""
function coerce_tolerance(data::Any)::Tolerance
    abs_val = haskey(data, :abs) && data.abs !== nothing ? Float64(data.abs) : nothing
    rel_val = haskey(data, :rel) && data.rel !== nothing ? Float64(data.rel) : nothing
    return Tolerance(; abs=abs_val, rel=rel_val)
end

"""
    coerce_time_span(data::Any) -> TimeSpan

Parse a schema `TimeSpan` object.
"""
function coerce_time_span(data::Any)::TimeSpan
    start_val = Float64(data.start)
    stop_val = Float64(data[Symbol("end")])
    return TimeSpan(start_val, stop_val)
end

"""
    coerce_assertion(data::Any) -> Assertion

Parse a schema `Assertion` object.
"""
function coerce_assertion(data::Any)::Assertion
    variable = string(data.variable)
    time_val = Float64(data.time)
    expected = Float64(data.expected)
    tolerance = haskey(data, :tolerance) && data.tolerance !== nothing ?
        coerce_tolerance(data.tolerance) : nothing
    return Assertion(variable, time_val, expected; tolerance=tolerance)
end

"""
    coerce_test(data::Any) -> Test

Parse a schema `Test` object into the Julia `Test` struct.
"""
function coerce_test(data::Any)::EarthSciSerialization.Test
    id = string(data.id)
    time_span = coerce_time_span(data.time_span)
    assertions = [coerce_assertion(a) for a in data.assertions]
    description = haskey(data, :description) && data.description !== nothing ?
        string(data.description) : nothing
    ic = Dict{String,Float64}()
    if haskey(data, :initial_conditions) && data.initial_conditions !== nothing
        for (k, v) in pairs(data.initial_conditions)
            ic[string(k)] = Float64(v)
        end
    end
    po = Dict{String,Float64}()
    if haskey(data, :parameter_overrides) && data.parameter_overrides !== nothing
        for (k, v) in pairs(data.parameter_overrides)
            po[string(k)] = Float64(v)
        end
    end
    tolerance = haskey(data, :tolerance) && data.tolerance !== nothing ?
        coerce_tolerance(data.tolerance) : nothing
    return EarthSciSerialization.Test(id, time_span, assertions;
        description=description,
        initial_conditions=ic,
        parameter_overrides=po,
        tolerance=tolerance)
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
    default_units = haskey(data, :default_units) && data.default_units !== nothing ? string(data.default_units) : nothing

    return ModelVariable(var_type,
                        default=default,
                        description=description,
                        expression=expression,
                        default_units=default_units)
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
    if _has_field(data, :conditions)
        return coerce_continuous_event(data)
    elseif _has_field(data, :trigger)
        return coerce_discrete_event(data)
    else
        throw(ParseError("Invalid EventType: missing 'conditions' or 'trigger' field"))
    end
end

"""
    coerce_discrete_event(data::Any) -> DiscreteEvent

Coerce JSON data specifically into DiscreteEvent.

Schema: DiscreteEvent must have a trigger, and either 'affects' (array of
AffectEquation) or 'functional_affect' (a registered handler). The Julia
DiscreteEvent type stores affects as a Vector{FunctionalAffect} where each
FunctionalAffect represents an assignment (target, expression, operation).
Schema AffectEquation entries {lhs, rhs} are converted to that form with
operation="set". The schema's 'functional_affect' (handler_id + metadata) is
currently collapsed to an empty affects list — the handler cannot be executed
symbolically, but parsing does not fail.
"""
function coerce_discrete_event(data::Any)::DiscreteEvent
    if !_has_field(data, :trigger)
        throw(ParseError("DiscreteEvent requires 'trigger' field"))
    end

    trigger = parse_trigger(_get_field(data, :trigger, nothing))

    affects = FunctionalAffect[]
    if _has_field(data, :affects)
        raw_affects = _get_field(data, :affects, [])
        for a in raw_affects
            push!(affects, _affect_equation_to_functional_affect(a))
        end
    end

    # Schema functional_affect is a registered handler descriptor; preserve
    # whatever we can so display/serialization doesn't choke.
    if isempty(affects) && _has_field(data, :functional_affect)
        fa = _get_field(data, :functional_affect, nothing)
        if fa !== nothing
            handler_id = _has_field(fa, :handler_id) ? string(_get_field(fa, :handler_id, "")) : "handler"
            push!(affects, FunctionalAffect(handler_id, NumExpr(0.0), operation="handler"))
        end
    end

    description = nothing
    if _has_field(data, :description)
        desc_val = _get_field(data, :description, nothing)
        description = desc_val === nothing ? nothing : string(desc_val)
    end
    return DiscreteEvent(trigger, affects, description=description)
end

# Convert a schema AffectEquation JSON object ({lhs, rhs}) into the Julia
# internal FunctionalAffect representation (target, expression, operation).
function _affect_equation_to_functional_affect(data)::FunctionalAffect
    if !_has_field(data, :lhs) || !_has_field(data, :rhs)
        throw(ParseError("AffectEquation requires 'lhs' and 'rhs' fields"))
    end
    target = string(_get_field(data, :lhs, ""))
    expression = parse_expression(_get_field(data, :rhs, nothing))
    return FunctionalAffect(target, expression, operation="set")
end

"""
    coerce_continuous_event(data::Any) -> ContinuousEvent

Coerce JSON data specifically into ContinuousEvent.

Handles optional schema fields (affect_neg, root_find, name, discrete_parameters)
by ignoring them — the current Julia ContinuousEvent type does not model them,
but their presence must not cause load to fail.
"""
function coerce_continuous_event(data::Any)::ContinuousEvent
    if !_has_field(data, :conditions)
        throw(ParseError("ContinuousEvent requires 'conditions' field"))
    end

    raw_conditions = _get_field(data, :conditions, [])
    conditions = Expr[parse_expression(c) for c in raw_conditions]

    raw_affects = _has_field(data, :affects) ? _get_field(data, :affects, []) : []
    affects = AffectEquation[coerce_affect_equation(a) for a in raw_affects]

    description = nothing
    if _has_field(data, :description)
        desc_val = _get_field(data, :description, nothing)
        description = desc_val === nothing ? nothing : string(desc_val)
    end

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

    # Inline tests / tolerance (schema gt-cc1) — same shape as on Model.
    tolerance = haskey(data, :tolerance) && data.tolerance !== nothing ?
        coerce_tolerance(data.tolerance) : nothing
    tests = haskey(data, :tests) && data.tests !== nothing ?
        EarthSciSerialization.Test[coerce_test(t) for t in data.tests] :
        EarthSciSerialization.Test[]

    return ReactionSystem(species, reactions; parameters=parameters, domain=domain,
                          tolerance=tolerance, tests=tests)
end

"""
    coerce_species(name::String, data::Any) -> Species

Coerce JSON data into Species type with explicit name.
"""
function coerce_species(name::String, data::Any)::Species
    units = haskey(data, :units) && data.units !== nothing ? string(data.units) : nothing
    default = haskey(data, :default) && data.default !== nothing ? Float64(data.default) : nothing
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    default_units = haskey(data, :default_units) && data.default_units !== nothing ? string(data.default_units) : nothing

    return Species(name, units=units, default=default, description=description, default_units=default_units)
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
    default_units = haskey(data, :default_units) && data.default_units !== nothing ? string(data.default_units) : nothing

    return Parameter(name, default, description=description, units=units, default_units=default_units)
end

"""
    coerce_data_loader_source(data::Any) -> DataLoaderSource

Coerce JSON data into a DataLoaderSource.
"""
function coerce_data_loader_source(data::Any)::DataLoaderSource
    url_template = string(data.url_template)
    mirrors = haskey(data, :mirrors) && data.mirrors !== nothing ?
              [string(m) for m in data.mirrors] : nothing
    return DataLoaderSource(url_template; mirrors=mirrors)
end

"""
    coerce_data_loader_temporal(data::Any) -> DataLoaderTemporal
"""
function coerce_data_loader_temporal(data::Any)::DataLoaderTemporal
    start = haskey(data, :start) && data.start !== nothing ? string(data.start) : nothing
    stop = haskey(data, :end) && data[:end] !== nothing ? string(data[:end]) : nothing
    file_period = haskey(data, :file_period) && data.file_period !== nothing ? string(data.file_period) : nothing
    frequency = haskey(data, :frequency) && data.frequency !== nothing ? string(data.frequency) : nothing
    records_per_file = if haskey(data, :records_per_file) && data.records_per_file !== nothing
        v = data.records_per_file
        v isa Number ? Int(v) : string(v)
    else
        nothing
    end
    time_variable = haskey(data, :time_variable) && data.time_variable !== nothing ? string(data.time_variable) : nothing
    return DataLoaderTemporal(; start=start, stop=stop, file_period=file_period,
                              frequency=frequency, records_per_file=records_per_file,
                              time_variable=time_variable)
end

"""
    coerce_data_loader_spatial(data::Any) -> DataLoaderSpatial
"""
function coerce_data_loader_spatial(data::Any)::DataLoaderSpatial
    crs = string(data.crs)
    grid_type = string(data.grid_type)
    staggering = haskey(data, :staggering) && data.staggering !== nothing ?
                 Dict{String,String}(string(k) => string(v) for (k, v) in pairs(data.staggering)) : nothing
    resolution = haskey(data, :resolution) && data.resolution !== nothing ?
                 Dict{String,Float64}(string(k) => Float64(v) for (k, v) in pairs(data.resolution)) : nothing
    extent = haskey(data, :extent) && data.extent !== nothing ?
             Dict{String,Vector{Float64}}(string(k) => [Float64(x) for x in v] for (k, v) in pairs(data.extent)) : nothing
    return DataLoaderSpatial(crs, grid_type;
                             staggering=staggering,
                             resolution=resolution,
                             extent=extent)
end

"""
    coerce_data_loader_variable(data::Any) -> DataLoaderVariable
"""
function coerce_data_loader_variable(data::Any)::DataLoaderVariable
    file_variable = string(data.file_variable)
    units = string(data.units)
    unit_conversion = if haskey(data, :unit_conversion) && data.unit_conversion !== nothing
        v = data.unit_conversion
        v isa Number ? Float64(v) : parse_expression(v)
    else
        nothing
    end
    description = haskey(data, :description) && data.description !== nothing ? string(data.description) : nothing
    reference = haskey(data, :reference) && data.reference !== nothing ? coerce_reference(data.reference) : nothing
    return DataLoaderVariable(file_variable, units;
                              unit_conversion=unit_conversion,
                              description=description,
                              reference=reference)
end

"""
    coerce_data_loader_regridding(data::Any) -> DataLoaderRegridding
"""
function coerce_data_loader_regridding(data::Any)::DataLoaderRegridding
    fill_value = haskey(data, :fill_value) && data.fill_value !== nothing ? Float64(data.fill_value) : nothing
    extrapolation = haskey(data, :extrapolation) && data.extrapolation !== nothing ? string(data.extrapolation) : nothing
    return DataLoaderRegridding(; fill_value=fill_value, extrapolation=extrapolation)
end

"""
    coerce_data_loader(data::Any) -> DataLoader

Coerce JSON data into the STAC-like DataLoader type.
"""
function coerce_data_loader(data::Any)::DataLoader
    kind = string(data.kind)
    source = coerce_data_loader_source(data.source)

    temporal = haskey(data, :temporal) && data.temporal !== nothing ?
               coerce_data_loader_temporal(data.temporal) : nothing
    spatial = haskey(data, :spatial) && data.spatial !== nothing ?
              coerce_data_loader_spatial(data.spatial) : nothing

    variables = Dict{String,DataLoaderVariable}(
        string(k) => coerce_data_loader_variable(v) for (k, v) in pairs(data.variables)
    )

    regridding = haskey(data, :regridding) && data.regridding !== nothing ?
                 coerce_data_loader_regridding(data.regridding) : nothing
    reference = haskey(data, :reference) && data.reference !== nothing ?
                coerce_reference(data.reference) : nothing
    metadata = haskey(data, :metadata) && data.metadata !== nothing ?
               Dict{String,Any}(string(k) => v for (k, v) in pairs(data.metadata)) : nothing

    return DataLoader(kind, source, variables;
                      temporal=temporal,
                      spatial=spatial,
                      regridding=regridding,
                      reference=reference,
                      metadata=metadata)
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
    # JSON3.Object keys are Symbols — convert to String explicitly so the
    # Dict{String,Any} constructor doesn't choke on Symbol→String conversion.
    connector_raw = data["connector"]
    connector = Dict{String,Any}(string(k) => v for (k, v) in pairs(connector_raw))
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
    config_raw = get(data, "config", nothing)
    config = if config_raw === nothing
        nothing
    else
        # JSON3.Object keys are Symbols; stringify explicitly.
        Dict{String,Any}(string(k) => v for (k, v) in pairs(config_raw))
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
Automatically resolves any subsystem references (local or remote) relative
to the directory containing the file.
"""
function load(path::String)::EsmFile
    file = open(path, "r") do io
        load(io)
    end
    # Resolve subsystem references relative to the file's directory
    base_path = dirname(abspath(path))
    resolve_subsystem_refs!(file, base_path)
    return file
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

# ========================================
# Subsystem Reference Resolution
# ========================================

"""
    SubsystemRefError

Exception thrown when subsystem reference resolution fails.
"""
struct SubsystemRefError <: Exception
    message::String
end

"""
    resolve_subsystem_refs!(file::EsmFile, base_path::String)

Resolve all subsystem references in-place. Walks all models and reaction_systems,
and for each subsystem that was parsed from a `{"ref": "..."}` object, loads the
referenced file and replaces the subsystem content.

References can be:
- Local file paths (resolved relative to `base_path`)
- Remote URLs starting with `http://` or `https://`

Circular references are detected and raise a `SubsystemRefError`.

# Arguments
- `file::EsmFile`: the parsed ESM file to resolve references in
- `base_path::String`: directory path for resolving relative file references
"""
function resolve_subsystem_refs!(file::EsmFile, base_path::String)
    visited = Set{String}()
    _resolve_refs_in_file!(file, base_path, visited)
end

"""
    _resolve_refs_in_file!(file::EsmFile, base_path::String, visited::Set{String})

Internal recursive resolver for subsystem references in an EsmFile.
"""
function _resolve_refs_in_file!(file::EsmFile, base_path::String, visited::Set{String})
    # Resolve model subsystem refs
    if file.models !== nothing
        for (name, model) in file.models
            _resolve_model_refs!(file.models, name, model, base_path, visited)
        end
    end

    # Resolve reaction system subsystem refs
    if file.reaction_systems !== nothing
        for (name, rsys) in file.reaction_systems
            _resolve_reaction_system_refs!(file.reaction_systems, name, rsys, base_path, visited)
        end
    end
end

"""
    _resolve_model_refs!(models_dict, name, model, base_path, visited)

Recursively resolve subsystem references within a Model's subsystems.
"""
function _resolve_model_refs!(models_dict::Dict{String,Model}, name::String,
                              model::Model, base_path::String, visited::Set{String})
    for (sub_name, sub_model) in model.subsystems
        # Recursively resolve nested subsystem refs
        _resolve_model_refs!(model.subsystems, sub_name, sub_model, base_path, visited)
    end
end

"""
    _resolve_reaction_system_refs!(rsys_dict, name, rsys, base_path, visited)

Recursively resolve subsystem references within a ReactionSystem's subsystems.
"""
function _resolve_reaction_system_refs!(rsys_dict::Dict{String,ReactionSystem}, name::String,
                                        rsys::ReactionSystem, base_path::String, visited::Set{String})
    for (sub_name, sub_rsys) in rsys.subsystems
        # Recursively resolve nested subsystem refs
        _resolve_reaction_system_refs!(rsys.subsystems, sub_name, sub_rsys, base_path, visited)
    end
end

"""
    _load_ref(ref::String, base_path::String, visited::Set{String}) -> EsmFile

Load a referenced ESM file from a local path or URL, with circular reference detection.

# Arguments
- `ref::String`: the reference string (local path or URL)
- `base_path::String`: directory for resolving relative paths
- `visited::Set{String}`: set of already-visited references for cycle detection
"""
function _load_ref(ref::String, base_path::String, visited::Set{String})::EsmFile
    # Normalize the reference for cycle detection
    canonical = _canonical_ref(ref, base_path)

    if canonical in visited
        throw(SubsystemRefError("Circular subsystem reference detected: $(canonical)"))
    end
    push!(visited, canonical)

    try
        if startswith(ref, "http://") || startswith(ref, "https://")
            return _load_remote_ref(ref)
        else
            return _load_local_ref(ref, base_path, visited)
        end
    catch e
        if e isa SubsystemRefError
            rethrow(e)
        else
            throw(SubsystemRefError("Failed to resolve subsystem ref '$(ref)': $(e)"))
        end
    end
end

"""
    _canonical_ref(ref::String, base_path::String) -> String

Produce a canonical key for a reference, used for cycle detection.
URLs are returned as-is; local paths are resolved to absolute paths.
"""
function _canonical_ref(ref::String, base_path::String)::String
    if startswith(ref, "http://") || startswith(ref, "https://")
        return ref
    else
        return abspath(joinpath(base_path, ref))
    end
end

"""
    _load_local_ref(ref::String, base_path::String, visited::Set{String}) -> EsmFile

Load a locally referenced ESM file.
"""
function _load_local_ref(ref::String, base_path::String, visited::Set{String})::EsmFile
    resolved_path = abspath(joinpath(base_path, ref))

    if !isfile(resolved_path)
        throw(SubsystemRefError("Referenced file not found: $(resolved_path) (from ref '$(ref)')"))
    end

    # Parse the referenced file using the IO-based load (no ref resolution on its own)
    file = open(resolved_path, "r") do io
        load(io)
    end

    # Recursively resolve refs in the loaded file, relative to its own directory
    ref_base = dirname(resolved_path)
    _resolve_refs_in_file!(file, ref_base, visited)

    return file
end

"""
    _load_remote_ref(ref::String) -> EsmFile

Load a remotely referenced ESM file from a URL.
Uses the Downloads stdlib to fetch the content.
"""
function _load_remote_ref(ref::String)::EsmFile
    local content::String
    try
        # Use Downloads.download from the Julia stdlib
        tmp = Base.download(ref)
        content = read(tmp, String)
        rm(tmp, force=true)
    catch e
        throw(SubsystemRefError("Failed to download subsystem ref '$(ref)': $(e)"))
    end

    raw_data = JSON3.read(content)

    schema_errors = validate_schema(raw_data)
    if !isempty(schema_errors)
        throw(SubsystemRefError("Schema validation failed for remote ref '$(ref)'"))
    end

    return coerce_esm_file(raw_data)
end