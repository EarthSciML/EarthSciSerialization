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

    # Constructor with optional parameters
    ModelVariable(type::ModelVariableType;
                  default=nothing,
                  description=nothing,
                  expression=nothing) =
        new(type, default, description, expression)
end

"""
    Model

ODE-based model component containing variables and equations.
"""
struct Model
    variables::Dict{String,ModelVariable}
    equations::Vector{Equation}
    events::Vector{EventType}

    # Constructor with optional events
    Model(variables::Dict{String,ModelVariable}, equations::Vector{Equation}; events=EventType[]) =
        new(variables, equations, events)
end

"""
    Species

Chemical species definition with name and optional properties.
"""
struct Species
    name::String
    molecular_weight::Union{Float64,Nothing}
    description::Union{String,Nothing}

    # Constructor with optional parameters
    Species(name::String; molecular_weight=nothing, description=nothing) =
        new(name, molecular_weight, description)
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

"""
    Reaction

Chemical reaction with reactants, products, and rate expression.
"""
struct Reaction
    reactants::Dict{String,Int}  # species => stoichiometry
    products::Dict{String,Int}   # species => stoichiometry
    rate::Expr
    reversible::Bool

    # Constructor with optional reversible parameter
    Reaction(reactants::Dict{String,Int}, products::Dict{String,Int}, rate::Expr; reversible=false) =
        new(reactants, products, rate, reversible)
end

"""
    ReactionSystem

Collection of chemical reactions with associated species.
"""
struct ReactionSystem
    species::Vector{Species}
    reactions::Vector{Reaction}
    parameters::Vector{Parameter}

    # Constructor with optional parameters
    ReactionSystem(species::Vector{Species}, reactions::Vector{Reaction}; parameters=[]) =
        new(species, reactions, parameters)
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
    Solver

Solver strategy and configuration.
"""
struct Solver
    algorithm::String
    tolerances::Dict{String,Float64}
    max_iterations::Union{Int,Nothing}
    parameters::Dict{String,Any}

    # Constructor with optional parameters
    Solver(algorithm::String;
           tolerances=Dict("rtol"=>1e-6, "atol"=>1e-8),
           max_iterations=nothing,
           parameters=Dict{String,Any}()) =
        new(algorithm, tolerances, max_iterations, parameters)
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