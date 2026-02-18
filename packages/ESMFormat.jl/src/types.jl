"""
Type definitions for EarthSciML Serialization Format.

This module defines the complete type hierarchy for the ESM format,
matching the JSON schema definitions for language-agnostic model interchange.
"""

# ========================================
# 1. Expression Type Hierarchy
# ========================================

"""
    abstract type Expr end

Abstract base type for all mathematical expressions in the ESM format.
Expressions can be numeric literals, variable references, or operator nodes.
"""
abstract type Expr end

"""
    NumExpr(value::Float64)

Numeric literal expression containing a floating-point value.
"""
struct NumExpr <: Expr
    value::Float64
end

"""
    VarExpr(name::String)

Variable or parameter reference expression containing a name string.
"""
struct VarExpr <: Expr
    name::String
end

"""
    OpExpr(op::String, args::Vector{Expr}, wrt::Union{String,Nothing}, dim::Union{String,Nothing})

Operator expression node containing:
- `op`: operator name (e.g., "+", "*", "log", "D")
- `args`: vector of argument expressions
- `wrt`: variable name for differentiation (optional)
- `dim`: dimension for spatial operators (optional)
"""
struct OpExpr <: Expr
    op::String
    args::Vector{Expr}
    wrt::Union{String,Nothing}
    dim::Union{String,Nothing}

    # Constructor with optional parameters
    OpExpr(op::String, args::Vector{Expr}; wrt=nothing, dim=nothing) =
        new(op, args, wrt, dim)
end

# ========================================
# 2. Equation Types
# ========================================

"""
    Equation(lhs::Expr, rhs::Expr)

Mathematical equation with left-hand side and right-hand side expressions.
Used for differential equations and algebraic constraints.
"""
struct Equation
    lhs::Expr
    rhs::Expr
end

"""
    AffectEquation(lhs::String, rhs::Expr)

Assignment equation for discrete events.
- `lhs`: target variable name (string)
- `rhs`: expression for the new value
"""
struct AffectEquation
    lhs::String
    rhs::Expr
end

# ========================================
# 3. Event System Base Types
# ========================================

"""
    abstract type EventType end

Abstract base type for all event types in the ESM format.
"""
abstract type EventType end

"""
    abstract type DiscreteEventTrigger end

Abstract base type for discrete event triggers.
"""
abstract type DiscreteEventTrigger end

"""
    ConditionTrigger(expression::Expr)

Trigger based on boolean condition expression.
"""
struct ConditionTrigger <: DiscreteEventTrigger
    expression::Expr
end

"""
    PeriodicTrigger(period::Float64, phase::Float64)

Trigger that fires periodically.
- `period`: time interval between triggers
- `phase`: time offset for first trigger
"""
struct PeriodicTrigger <: DiscreteEventTrigger
    period::Float64
    phase::Float64

    # Constructor with optional phase
    PeriodicTrigger(period::Float64; phase=0.0) = new(period, phase)
end

"""
    PresetTimesTrigger(times::Vector{Float64})

Trigger that fires at preset times.
"""
struct PresetTimesTrigger <: DiscreteEventTrigger
    times::Vector{Float64}
end

"""
    FunctionalAffect

Functional affect for discrete events.
"""
struct FunctionalAffect
    target::String
    expression::Expr
    operation::String  # "set", "add", "multiply", etc.

    # Constructor with default operation
    FunctionalAffect(target::String, expression::Expr; operation="set") =
        new(target, expression, operation)
end

# ========================================
# 4. Event Types
# ========================================

"""
    ContinuousEvent <: EventType

Event triggered by zero-crossing of condition expressions.
"""
struct ContinuousEvent <: EventType
    conditions::Vector{Expr}
    affects::Vector{AffectEquation}
    description::Union{String,Nothing}

    # Constructor with optional description
    ContinuousEvent(conditions::Vector{Expr}, affects::Vector{AffectEquation}; description=nothing) =
        new(conditions, affects, description)
end

"""
    DiscreteEvent <: EventType

Event triggered by discrete triggers with functional affects.
"""
struct DiscreteEvent <: EventType
    trigger::DiscreteEventTrigger
    affects::Vector{FunctionalAffect}
    description::Union{String,Nothing}

    # Constructor with optional description
    DiscreteEvent(trigger::DiscreteEventTrigger, affects::Vector{FunctionalAffect}; description=nothing) =
        new(trigger, affects, description)
end

# ========================================
# 5. Model Component Types
# ========================================

"""
    @enum ModelVariableType

Type enumeration for model variables:
- StateVariable: differential state variables
- ParameterVariable: constant parameters
- ObservedVariable: derived/computed variables
"""
@enum ModelVariableType begin
    StateVariable
    ParameterVariable
    ObservedVariable
end

"""
    ModelVariable

Structure defining a model variable with its type, default value, and optional expression.
"""
struct ModelVariable
    type::ModelVariableType
    default::Union{Float64,Nothing}
    description::Union{String,Nothing}
    expression::Union{Expr,Nothing}
    units::Union{String,Nothing}

    # Constructor with optional parameters
    ModelVariable(type::ModelVariableType;
                  default=nothing,
                  description=nothing,
                  expression=nothing,
                  units=nothing) =
        new(type, default, description, expression, units)
end

"""
    Model

ODE-based model component containing variables, equations, and optional subsystems.
Supports hierarchical composition through subsystems.
"""
struct Model
    variables::Dict{String,ModelVariable}
    equations::Vector{Equation}
    events::Vector{EventType}
    subsystems::Dict{String,Model}

    # Constructor with optional events and subsystems
    Model(variables::Dict{String,ModelVariable}, equations::Vector{Equation};
          events=EventType[], subsystems=Dict{String,Model}()) =
        new(variables, equations, events, subsystems)
end

"""
    Species

Chemical species definition with name and optional properties.
"""
struct Species
    name::String
    units::Union{String,Nothing}
    default::Union{Float64,Nothing}
    description::Union{String,Nothing}

    # Constructor with optional parameters
    Species(name::String; units=nothing, default=nothing, description=nothing) =
        new(name, units, default, description)
end

"""
    Parameter

Model parameter with name, default value, and optional metadata.
"""
struct Parameter
    name::String
    default::Float64
    description::Union{String,Nothing}
    units::Union{String,Nothing}

    # Constructor with optional parameters
    Parameter(name::String, default::Float64; description=nothing, units=nothing) =
        new(name, default, description, units)
end



# ========================================
# 6. Data and Operator Types
# ========================================

"""
    abstract type CouplingEntry end

Abstract base type for coupling entries that connect model components.
"""
abstract type CouplingEntry end

"""
    DataLoader

External data source registration (by reference).
Runtime-specific data loading functionality.
"""
struct DataLoader
    type::String
    source::String
    parameters::Dict{String,Any}
    description::Union{String,Nothing}

    # Constructor with optional parameters and description
    DataLoader(type::String, source::String; parameters=Dict{String,Any}(), description=nothing) =
        new(type, source, parameters, description)
end

"""
    Operator

Registered runtime operator (by reference).
Platform-specific computational kernels and operations.
"""
struct Operator
    type::String
    name::String
    parameters::Dict{String,Any}
    description::Union{String,Nothing}

    # Constructor with optional parameters and description
    Operator(type::String, name::String; parameters=Dict{String,Any}(), description=nothing) =
        new(type, name, parameters, description)
end

# ========================================
# 7. System Configuration Types
# ========================================

"""
    Domain

Spatial and temporal domain specification.
"""
struct Domain
    spatial::Union{Dict{String,Any},Nothing}
    temporal::Union{Dict{String,Any},Nothing}

    # Constructor with optional parameters
    Domain(; spatial=nothing, temporal=nothing) = new(spatial, temporal)
end

"""
    @enum SolverStrategy

Enumeration of supported solver strategies:
- StrangThreads: Strang splitting with parallel processing
- StrangSerial: Strang splitting with serial processing
- IMEX: Implicit-Explicit method
"""
@enum SolverStrategy begin
    StrangThreads
    StrangSerial
    IMEX
end

"""
    @enum NumericalMethod

Enumeration of supported numerical methods:
- FiniteDifferenceMethod (FDM): Finite difference discretization
- FiniteElementMethod (FEM): Finite element discretization
- FiniteVolumeMethod (FVM): Finite volume discretization
"""
@enum NumericalMethod begin
    FiniteDifferenceMethod
    FiniteElementMethod
    FiniteVolumeMethod
end

"""
    SolverConfiguration

Strategy-specific configuration for solver methods.
Contains method-specific parameters, tolerances, and algorithms.
"""
struct SolverConfiguration
    # Core configuration
    threads::Union{Int,Nothing}
    timestep::Union{Float64,Nothing}

    # Algorithm selection
    stiff_algorithm::Union{String,Nothing}
    nonstiff_algorithm::Union{String,Nothing}
    map_algorithm::Union{String,Nothing}

    # Convergence criteria
    stiff_kwargs::Dict{String,Any}

    # Numerical method information
    numerical_method::Union{NumericalMethod,Nothing}

    # Additional parameters
    extra_parameters::Dict{String,Any}

    # Constructor with optional parameters
    SolverConfiguration(;
                       threads=nothing,
                       timestep=nothing,
                       stiff_algorithm=nothing,
                       nonstiff_algorithm=nothing,
                       map_algorithm=nothing,
                       stiff_kwargs=Dict{String,Any}("abstol"=>1e-8, "reltol"=>1e-6),
                       numerical_method=nothing,
                       extra_parameters=Dict{String,Any}()) =
        new(threads, timestep, stiff_algorithm, nonstiff_algorithm, map_algorithm,
            stiff_kwargs, numerical_method, extra_parameters)
end

"""
    Solver

Enhanced solver strategy and configuration supporting different numerical methods,
solver parameters, convergence criteria, and method compatibility checking.
"""
struct Solver
    strategy::SolverStrategy
    config::SolverConfiguration

    # Constructor with strategy and configuration
    Solver(strategy::SolverStrategy, config::SolverConfiguration) =
        new(strategy, config)

    # Convenience constructor with strategy string
    function Solver(strategy_str::String; kwargs...)
        strategy = parse_solver_strategy(strategy_str)
        config = SolverConfiguration(; kwargs...)
        return new(strategy, config)
    end
end

"""
    parse_solver_strategy(strategy_str::String) -> SolverStrategy

Parse solver strategy string to enum value.
"""
function parse_solver_strategy(strategy_str::String)::SolverStrategy
    strategy_map = Dict{String,SolverStrategy}(
        "strang_threads" => StrangThreads,
        "strang_serial" => StrangSerial,
        "imex" => IMEX
    )

    if !haskey(strategy_map, strategy_str)
        throw(ArgumentError("Unknown solver strategy: $strategy_str. Supported strategies: $(keys(strategy_map))"))
    end

    return strategy_map[strategy_str]
end

"""
    solver_strategy_to_string(strategy::SolverStrategy) -> String

Convert solver strategy enum to string representation.
"""
function solver_strategy_to_string(strategy::SolverStrategy)::String
    strategy_map = Dict{SolverStrategy,String}(
        StrangThreads => "strang_threads",
        StrangSerial => "strang_serial",
        IMEX => "imex"
    )

    return strategy_map[strategy]
end

"""
    parse_numerical_method(method_str::String) -> NumericalMethod

Parse numerical method string to enum value.
"""
function parse_numerical_method(method_str::String)::NumericalMethod
    method_map = Dict{String,NumericalMethod}(
        "fdm" => FiniteDifferenceMethod,
        "finite_difference" => FiniteDifferenceMethod,
        "fem" => FiniteElementMethod,
        "finite_element" => FiniteElementMethod,
        "fvm" => FiniteVolumeMethod,
        "finite_volume" => FiniteVolumeMethod
    )

    if !haskey(method_map, lowercase(method_str))
        throw(ArgumentError("Unknown numerical method: $method_str. Supported methods: $(keys(method_map))"))
    end

    return method_map[lowercase(method_str)]
end

"""
    numerical_method_to_string(method::NumericalMethod) -> String

Convert numerical method enum to string representation.
"""
function numerical_method_to_string(method::NumericalMethod)::String
    method_map = Dict{NumericalMethod,String}(
        FiniteDifferenceMethod => "fdm",
        FiniteElementMethod => "fem",
        FiniteVolumeMethod => "fvm"
    )

    return method_map[method]
end

"""
    validate_solver_compatibility(solver::Solver) -> Bool

Check compatibility between solver strategy and configuration.
Returns true if configuration is compatible with strategy.
"""
function validate_solver_compatibility(solver::Solver)::Bool
    strategy = solver.strategy
    config = solver.config

    # Strategy-specific validation
    if strategy == StrangThreads
        # Strang with threads requires thread count
        if config.threads === nothing || config.threads < 1
            return false
        end

        # Should have both stiff and nonstiff algorithms for splitting
        if config.stiff_algorithm === nothing && config.nonstiff_algorithm === nothing
            return false
        end
    elseif strategy == StrangSerial
        # Strang serial shouldn't specify threads > 1
        if config.threads !== nothing && config.threads > 1
            return false
        end

        # Should have both stiff and nonstiff algorithms for splitting
        if config.stiff_algorithm === nothing && config.nonstiff_algorithm === nothing
            return false
        end
    elseif strategy == IMEX
        # IMEX should have stiff algorithm specified
        if config.stiff_algorithm === nothing
            return false
        end
    end

    # Timestep validation
    if config.timestep !== nothing && config.timestep <= 0
        return false
    end

    # Tolerance validation
    if haskey(config.stiff_kwargs, "abstol") && config.stiff_kwargs["abstol"] <= 0
        return false
    end
    if haskey(config.stiff_kwargs, "reltol") && config.stiff_kwargs["reltol"] <= 0
        return false
    end

    return true
end

"""
    get_recommended_algorithms(strategy::SolverStrategy, method::NumericalMethod) -> Dict{String,String}

Get recommended algorithm combinations for a given strategy and numerical method.
"""
function get_recommended_algorithms(strategy::SolverStrategy, method::NumericalMethod)::Dict{String,String}
    recommendations = Dict{String,String}()

    if strategy == StrangThreads || strategy == StrangSerial
        if method == FiniteDifferenceMethod
            recommendations["stiff_algorithm"] = "QNDF"
            recommendations["nonstiff_algorithm"] = "Tsit5"
        elseif method == FiniteElementMethod
            recommendations["stiff_algorithm"] = "KenCarp4"
            recommendations["nonstiff_algorithm"] = "Tsit5"
        elseif method == FiniteVolumeMethod
            recommendations["stiff_algorithm"] = "QBDF"
            recommendations["nonstiff_algorithm"] = "Tsit5"
        end
    elseif strategy == IMEX
        if method == FiniteDifferenceMethod
            recommendations["stiff_algorithm"] = "KenCarp4"
        elseif method == FiniteElementMethod
            recommendations["stiff_algorithm"] = "ARKODE"
        elseif method == FiniteVolumeMethod
            recommendations["stiff_algorithm"] = "KenCarp5"
        end
    end

    return recommendations
end

"""
    create_solver_with_method(strategy_str::String, method_str::String; kwargs...) -> Solver

Convenience constructor to create a solver with recommended settings for a given
strategy and numerical method combination.
"""
function create_solver_with_method(strategy_str::String, method_str::String; kwargs...)::Solver
    strategy = parse_solver_strategy(strategy_str)
    method = parse_numerical_method(method_str)

    # Get recommended algorithms
    recommendations = get_recommended_algorithms(strategy, method)

    # Merge recommendations with user-provided kwargs
    # Convert recommendations to symbol keys to match kwargs
    rec_symbols = Dict{Symbol, Any}(Symbol(k) => v for (k, v) in recommendations)
    config_args = merge(rec_symbols, Dict{Symbol, Any}(kwargs))
    config_args[:numerical_method] = method

    config = SolverConfiguration(; NamedTuple(Symbol(k) => v for (k, v) in config_args)...)

    solver = Solver(strategy, config)

    # Validate compatibility
    if !validate_solver_compatibility(solver)
        @warn "Solver configuration may not be compatible with strategy $strategy_str and method $method_str"
    end

    return solver
end

"""
    Reference

Academic citation or data source reference.
"""
struct Reference
    doi::Union{String,Nothing}
    citation::Union{String,Nothing}
    url::Union{String,Nothing}
    notes::Union{String,Nothing}

    # Constructor with all optional parameters
    Reference(; doi=nothing, citation=nothing, url=nothing, notes=nothing) =
        new(doi, citation, url, notes)
end

"""
    StoichiometryEntry

A species with its stoichiometric coefficient in a reaction.
"""
struct StoichiometryEntry
    species::String
    stoichiometry::Int

    # Constructor
    StoichiometryEntry(species::String, stoichiometry::Int) = new(species, stoichiometry)
end

"""
    Reaction

Chemical reaction with substrates, products, and rate expression.
"""
struct Reaction
    id::String
    name::Union{String,Nothing}
    substrates::Union{Vector{StoichiometryEntry},Nothing}  # null for source reactions (∅ → X)
    products::Union{Vector{StoichiometryEntry},Nothing}    # null for sink reactions (X → ∅)
    rate::Expr
    reference::Union{Reference,Nothing}

    # Constructor with optional parameters
    Reaction(id::String, substrates::Union{Vector{StoichiometryEntry},Nothing},
             products::Union{Vector{StoichiometryEntry},Nothing}, rate::Expr;
             name=nothing, reference=nothing) =
        new(id, name, substrates, products, rate, reference)
end

"""
    ReactionSystem

Collection of chemical reactions with associated species, supporting hierarchical composition.
"""
struct ReactionSystem
    species::Vector{Species}
    reactions::Vector{Reaction}
    parameters::Vector{Parameter}
    subsystems::Dict{String,ReactionSystem}

    # Constructor with optional parameters and subsystems
    ReactionSystem(species::Vector{Species}, reactions::Vector{Reaction};
                   parameters=Parameter[], subsystems=Dict{String,ReactionSystem}()) =
        new(species, reactions, parameters, subsystems)
end

"""
    Metadata

Authorship, provenance, and description metadata.
"""
struct Metadata
    name::String
    description::Union{String,Nothing}
    authors::Vector{String}
    license::Union{String,Nothing}
    created::Union{String,Nothing}  # ISO 8601 timestamp
    modified::Union{String,Nothing} # ISO 8601 timestamp
    tags::Vector{String}
    references::Vector{Reference}

    # Constructor with optional parameters
    Metadata(name::String;
             description=nothing,
             authors=String[],
             license=nothing,
             created=nothing,
             modified=nothing,
             tags=String[],
             references=Reference[]) =
        new(name, description, authors, license, created, modified, tags, references)
end

"""
    EsmFile

Main ESM file structure containing all components.
"""
struct EsmFile
    esm::String  # Version string
    metadata::Metadata
    models::Union{Dict{String,Model},Nothing}
    reaction_systems::Union{Dict{String,ReactionSystem},Nothing}
    data_loaders::Union{Dict{String,DataLoader},Nothing}
    operators::Union{Dict{String,Operator},Nothing}
    coupling::Vector{CouplingEntry}
    domain::Union{Domain,Nothing}
    solver::Union{Solver,Nothing}

    # Constructor with optional parameters
    EsmFile(esm::String, metadata::Metadata;
            models=nothing,
            reaction_systems=nothing,
            data_loaders=nothing,
            operators=nothing,
            coupling=CouplingEntry[],
            domain=nothing,
            solver=nothing) =
        new(esm, metadata, models, reaction_systems, data_loaders, operators, coupling, domain, solver)
end

# ========================================
# 8. Reference Resolution System
# ========================================

"""
    QualifiedReferenceError

Exception thrown when qualified reference resolution fails.
Contains detailed error information.
"""
struct QualifiedReferenceError <: Exception
    message::String
    reference::String
    path::Vector{String}
end

"""
    ReferenceResolution

Result of qualified reference resolution containing the resolved variable
and its location information.
"""
struct ReferenceResolution
    variable_name::String
    system_path::Vector{String}
    system_type::Symbol  # :model, :reaction_system, :data_loader, :operator
    resolved_system::Union{Model,ReactionSystem,DataLoader,Operator}
end

"""
    resolve_qualified_reference(esm_file::EsmFile, reference::String) -> ReferenceResolution

Resolve a qualified reference string using hierarchical dot notation.

The reference string is split on dots to produce segments [s₁, s₂, …, sₙ].
The final segment sₙ is the variable name. The preceding segments [s₁, …, sₙ₋₁]
form a path through the subsystem hierarchy.

## Algorithm
1. Split reference on "." to get segments
2. First segment must match a top-level system (models, reaction_systems, data_loaders, operators)
3. Each subsequent segment must match a key in the parent system's subsystems map
4. Final segment is the variable name to resolve

## Examples
- `"SuperFast.O3"` → Variable `O3` in top-level model `SuperFast`
- `"SuperFast.GasPhase.O3"` → Variable `O3` in subsystem `GasPhase` of model `SuperFast`
- `"Atmosphere.Chemistry.FastChem.NO2"` → Variable `NO2` in nested subsystems

## Throws
- `QualifiedReferenceError` if reference cannot be resolved
"""
function resolve_qualified_reference(esm_file::EsmFile, reference::String)::ReferenceResolution
    if isempty(reference)
        throw(QualifiedReferenceError("Empty reference string", reference, String[]))
    end

    segments = split(reference, ".")
    if length(segments) < 1
        throw(QualifiedReferenceError("Invalid reference format", reference, String[]))
    end

    # Extract variable name (last segment) and system path
    variable_name = String(segments[end])
    system_path = String.(segments[1:end-1])

    # Handle bare references (no dot)
    if length(system_path) == 0
        throw(QualifiedReferenceError("Bare references not supported without system context", reference, String[]))
    end

    # Resolve the system path
    top_level_name = system_path[1]
    remaining_path = system_path[2:end]

    # Find top-level system
    system, system_type = find_top_level_system(esm_file, top_level_name)
    if system === nothing
        throw(QualifiedReferenceError("Top-level system '$(top_level_name)' not found", reference, system_path[1:1]))
    end

    # Traverse subsystem hierarchy
    current_system = system
    traversed_path = [top_level_name]

    for segment in remaining_path
        push!(traversed_path, segment)
        current_system = find_subsystem(current_system, segment)
        if current_system === nothing
            throw(QualifiedReferenceError("Subsystem '$(segment)' not found in path", reference, traversed_path))
        end
    end

    # Validate that the variable exists in the final system
    if !variable_exists_in_system(current_system, variable_name)
        throw(QualifiedReferenceError("Variable '$(variable_name)' not found in system", reference, system_path))
    end

    return ReferenceResolution(variable_name, system_path, system_type, current_system)
end

"""
    find_top_level_system(esm_file::EsmFile, name::String) -> (Union{Model,ReactionSystem,DataLoader,Operator,Nothing}, Symbol)

Find a top-level system by name in models, reaction_systems, data_loaders, or operators.
Returns the system and its type, or (nothing, :none) if not found.
"""
function find_top_level_system(esm_file::EsmFile, name::String)
    # Check models
    if esm_file.models !== nothing && haskey(esm_file.models, name)
        return (esm_file.models[name], :model)
    end

    # Check reaction_systems
    if esm_file.reaction_systems !== nothing && haskey(esm_file.reaction_systems, name)
        return (esm_file.reaction_systems[name], :reaction_system)
    end

    # Check data_loaders
    if esm_file.data_loaders !== nothing && haskey(esm_file.data_loaders, name)
        return (esm_file.data_loaders[name], :data_loader)
    end

    # Check operators
    if esm_file.operators !== nothing && haskey(esm_file.operators, name)
        return (esm_file.operators[name], :operator)
    end

    return (nothing, :none)
end

"""
    find_subsystem(system::Union{Model,ReactionSystem}, name::String) -> Union{Model,ReactionSystem,Nothing}

Find a subsystem by name within a Model or ReactionSystem.
Returns the subsystem or nothing if not found.
"""
function find_subsystem(system::Model, name::String)::Union{Model,Nothing}
    return get(system.subsystems, name, nothing)
end

function find_subsystem(system::ReactionSystem, name::String)::Union{ReactionSystem,Nothing}
    return get(system.subsystems, name, nothing)
end

function find_subsystem(system::Union{DataLoader,Operator}, name::String)
    # Data loaders and operators don't have subsystems
    return nothing
end

"""
    variable_exists_in_system(system, variable_name::String) -> Bool

Check if a variable exists in the given system.
"""
function variable_exists_in_system(system::Model, variable_name::String)::Bool
    return haskey(system.variables, variable_name)
end

function variable_exists_in_system(system::ReactionSystem, variable_name::String)::Bool
    # Check species
    for species in system.species
        if species.name == variable_name
            return true
        end
    end

    # Check parameters
    for param in system.parameters
        if param.name == variable_name
            return true
        end
    end

    return false
end

function variable_exists_in_system(system::Union{DataLoader,Operator}, variable_name::String)::Bool
    # Data loaders and operators are referenced by type/name, not variables
    return false
end

"""
    validate_reference_syntax(reference::String) -> Bool

Validate that a reference string follows proper dot notation syntax.
"""
function validate_reference_syntax(reference::String)::Bool
    if isempty(reference)
        return false
    end

    # No leading or trailing dots
    if startswith(reference, ".") || endswith(reference, ".")
        return false
    end

    # No consecutive dots
    if occursin("..", reference)
        return false
    end

    # All segments should be valid identifiers
    segments = split(reference, ".")
    for segment in segments
        if isempty(segment) || !is_valid_identifier(String(segment))
            return false
        end
    end

    return true
end

"""
    is_valid_identifier(name::String) -> Bool

Check if a string is a valid identifier (letters, numbers, underscores, no leading digit).
"""
function is_valid_identifier(name::String)::Bool
    if isempty(name)
        return false
    end

    # Must start with letter or underscore
    if !isletter(name[1]) && name[1] != '_'
        return false
    end

    # Rest can be letters, digits, or underscores
    for c in name[2:end]
        if !isletter(c) && !isdigit(c) && c != '_'
            return false
        end
    end

    return true
end

# ========================================
# 9. Backward Compatibility Helpers
# ========================================

"""
    dict_to_stoichiometry_entries(dict::Dict{String,Int}) -> Vector{StoichiometryEntry}

Convert old-style Dict{String,Int} format to new StoichiometryEntry vector format.
"""
function dict_to_stoichiometry_entries(dict::Dict{String,Int})::Vector{StoichiometryEntry}
    return [StoichiometryEntry(species, stoichiometry) for (species, stoichiometry) in dict]
end

"""
    stoichiometry_entries_to_dict(entries::Vector{StoichiometryEntry}) -> Dict{String,Int}

Convert new StoichiometryEntry vector format to old-style Dict{String,Int} format.
"""
function stoichiometry_entries_to_dict(entries::Vector{StoichiometryEntry})::Dict{String,Int}
    return Dict(entry.species => entry.stoichiometry for entry in entries)
end

"""
    Reaction(reactants::Dict{String,Int}, products::Dict{String,Int}, rate::Expr; reversible=false) -> Reaction

Legacy constructor for backward compatibility. Creates a reaction with auto-generated ID.
"""
function Reaction(reactants::Dict{String,Int}, products::Dict{String,Int}, rate::Expr; reversible=false)
    # Generate a simple ID based on the reactants and products
    id = "reaction_$(hash(string(reactants, products, rate)))"

    substrates = isempty(reactants) ? nothing : dict_to_stoichiometry_entries(reactants)
    products_vec = isempty(products) ? nothing : dict_to_stoichiometry_entries(products)

    return Reaction(id, substrates, products_vec, rate)
end

"""
    get_reactants_dict(reaction::Reaction) -> Dict{String,Int}

Get reactants as dictionary for backward compatibility.
"""
function get_reactants_dict(reaction::Reaction)::Dict{String,Int}
    # Use getfield to avoid infinite recursion
    substrates_field = getfield(reaction, :substrates)
    if substrates_field === nothing
        return Dict{String,Int}()
    else
        return stoichiometry_entries_to_dict(substrates_field)
    end
end

"""
    get_products_dict(reaction::Reaction) -> Dict{String,Int}

Get products as dictionary for backward compatibility.
"""
function get_products_dict(reaction::Reaction)::Dict{String,Int}
    # Use getfield to avoid infinite recursion
    products_field = getfield(reaction, :products)
    if products_field === nothing
        return Dict{String,Int}()
    else
        return stoichiometry_entries_to_dict(products_field)
    end
end

# Add property access for backward compatibility
# Only override specific properties that are needed for backward compatibility
Base.getproperty(reaction::Reaction, name::Symbol) = begin
    if name == :reactants
        return get_reactants_dict(reaction)
    elseif name == :reversible
        return false  # Not supported in new schema
    else
        return getfield(reaction, name)
    end
end

# Add a separate property for old-style products access
Base.propertynames(::Type{Reaction}, private::Bool=false) = begin
    names = fieldnames(Reaction)
    if private
        return (names..., :reactants, :reversible)
    else
        return names
    end
end