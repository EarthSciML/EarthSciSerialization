"""
Editing operations for ESM format structures.

This module implements all editing operations specified in ESM Libraries Spec Section 4,
including variable operations, equation operations, reaction operations, event operations,
coupling operations, and model-level operations.
"""

# Variable operations (Section 4.1)

"""
    add_variable(model::Model, name::String, variable::ModelVariable) -> Model

Add a new variable to a model.

Creates a new model with the additional variable. Warns if variable already exists.
"""
function add_variable(model::Model, name::String, variable::ModelVariable)::Model
    new_variables = copy(model.variables)

    if haskey(new_variables, name)
        @warn "Variable '$name' already exists, replacing"
    end

    new_variables[name] = variable

    return Model(
        new_variables,
        model.equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=get(model, :continuous_events, ContinuousEvent[]),
        discrete_events=get(model, :discrete_events, DiscreteEvent[]),
        description=get(model, :description, nothing)
    )
end

"""
    remove_variable(model::Model, name::String) -> Model

Remove a variable from a model.

Creates a new model without the specified variable. Warns about dependencies
but does not automatically update equations that reference the variable.
"""
function remove_variable(model::Model, name::String)::Model
    new_variables = copy(model.variables)

    if !haskey(new_variables, name)
        @warn "Variable '$name' does not exist"
        return model
    end

    # Check for dependencies
    dependent_equations = Int[]
    for (i, eq) in enumerate(model.equations)
        lhs_vars = free_variables(eq.lhs)
        rhs_vars = free_variables(eq.rhs)
        if name in lhs_vars || name in rhs_vars
            push!(dependent_equations, i)
        end
    end

    if !isempty(dependent_equations)
        @warn "Variable '$name' is used in equations: $dependent_equations. These equations may become invalid."
    end

    delete!(new_variables, name)

    return Model(
        new_variables,
        model.equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=get(model, :continuous_events, ContinuousEvent[]),
        discrete_events=get(model, :discrete_events, DiscreteEvent[]),
        description=get(model, :description, nothing)
    )
end

"""
    rename_variable(model::Model, old_name::String, new_name::String) -> Model

Rename a variable throughout the model.

Updates the variable definition and all references in equations.
"""
function rename_variable(model::Model, old_name::String, new_name::String)::Model
    if !haskey(model.variables, old_name)
        @warn "Variable '$old_name' does not exist"
        return model
    end

    if haskey(model.variables, new_name)
        @warn "Variable '$new_name' already exists, this will replace it"
    end

    # Update variables dictionary
    new_variables = copy(model.variables)
    variable = new_variables[old_name]
    delete!(new_variables, old_name)
    new_variables[new_name] = variable

    # Update equations
    substitution = Dict(old_name => VarExpr(new_name))
    new_equations = [
        Equation(
            substitute(eq.lhs, substitution),
            substitute(eq.rhs, substitution)
        )
        for eq in model.equations
    ]

    return Model(
        new_variables,
        new_equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=get(model, :continuous_events, ContinuousEvent[]),
        discrete_events=get(model, :discrete_events, DiscreteEvent[]),
        description=get(model, :description, nothing)
    )
end

# Equation operations (Section 4.2)

"""
    add_equation(model::Model, equation::Equation) -> Model

Add a new equation to a model.

Appends the equation to the end of the equations list.
"""
function add_equation(model::Model, equation::Equation)::Model
    new_equations = copy(model.equations)
    push!(new_equations, equation)

    return Model(
        model.variables,
        new_equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=get(model, :continuous_events, ContinuousEvent[]),
        discrete_events=get(model, :discrete_events, DiscreteEvent[]),
        description=get(model, :description, nothing)
    )
end

"""
    remove_equation(model::Model, index::Int) -> Model
    remove_equation(model::Model, lhs_pattern::Expr) -> Model

Remove an equation from a model.

Can remove by index (1-based) or by matching the left-hand side expression.
"""
function remove_equation(model::Model, index::Int)::Model
    if index < 1 || index > length(model.equations)
        @warn "Equation index $index out of bounds (1-$(length(model.equations)))"
        return model
    end

    new_equations = copy(model.equations)
    deleteat!(new_equations, index)

    return Model(
        model.variables,
        new_equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=get(model, :continuous_events, ContinuousEvent[]),
        discrete_events=get(model, :discrete_events, DiscreteEvent[]),
        description=get(model, :description, nothing)
    )
end

function remove_equation(model::Model, lhs_pattern::ESMFormat.Expr)::Model
    # Find equation with matching LHS
    for (i, eq) in enumerate(model.equations)
        if eq.lhs == lhs_pattern  # This requires Expr equality to be defined
            return remove_equation(model, i)
        end
    end

    @warn "No equation found with LHS matching: $lhs_pattern"
    return model
end

"""
    substitute_in_equations(model::Model, bindings::Dict{String, Expr}) -> Model

Apply substitutions across all equations in a model.

Replaces variables according to the bindings dictionary.
"""
function substitute_in_equations(model::Model, bindings::Dict{String, ESMFormat.Expr})::Model
    new_equations = [
        Equation(
            substitute(eq.lhs, bindings),
            substitute(eq.rhs, bindings)
        )
        for eq in model.equations
    ]

    return Model(
        model.variables,
        new_equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=get(model, :continuous_events, ContinuousEvent[]),
        discrete_events=get(model, :discrete_events, DiscreteEvent[]),
        description=get(model, :description, nothing)
    )
end

# Reaction operations (Section 4.3)

"""
    add_reaction(system::ReactionSystem, reaction::Reaction) -> ReactionSystem

Add a new reaction to a reaction system.
"""
function add_reaction(system::ReactionSystem, reaction::Reaction)::ReactionSystem
    new_reactions = copy(system.reactions)
    push!(new_reactions, reaction)

    return ReactionSystem(
        system.species,
        new_reactions,
        parameters=system.parameters,
        subsystems=get(system, :subsystems, Dict{String,ReactionSystem}()),
        description=get(system, :description, nothing)
    )
end

"""
    remove_reaction(system::ReactionSystem, id::String) -> ReactionSystem

Remove a reaction by its ID.

Note: This assumes reactions have an `id` field. If not available,
this function will search by reaction equality.
"""
function remove_reaction(system::ReactionSystem, id::String)::ReactionSystem
    new_reactions = Reaction[]

    for reaction in system.reactions
        reaction_id = get(reaction, :id, nothing)
        if reaction_id != id
            push!(new_reactions, reaction)
        end
    end

    if length(new_reactions) == length(system.reactions)
        @warn "No reaction found with id: $id"
    end

    return ReactionSystem(
        system.species,
        new_reactions,
        parameters=system.parameters,
        subsystems=get(system, :subsystems, Dict{String,ReactionSystem}()),
        description=get(system, :description, nothing)
    )
end

"""
    add_species(system::ReactionSystem, name::String, species::Species) -> ReactionSystem

Add a new species to a reaction system.
"""
function add_species(system::ReactionSystem, name::String, species::Species)::ReactionSystem
    new_species = copy(system.species)

    # Check if species already exists
    for existing in new_species
        if existing.name == name
            @warn "Species '$name' already exists, replacing"
            # Remove the existing one
            filter!(s -> s.name != name, new_species)
            break
        end
    end

    push!(new_species, species)

    return ReactionSystem(
        new_species,
        system.reactions,
        parameters=system.parameters,
        subsystems=get(system, :subsystems, Dict{String,ReactionSystem}()),
        description=get(system, :description, nothing)
    )
end

"""
    remove_species(system::ReactionSystem, name::String) -> ReactionSystem

Remove a species from a reaction system.

Warns about dependent reactions but does not automatically update them.
"""
function remove_species(system::ReactionSystem, name::String)::ReactionSystem
    # Check for dependencies
    dependent_reactions = Int[]
    for (i, reaction) in enumerate(system.reactions)
        if haskey(reaction.reactants, name) || haskey(reaction.products, name)
            push!(dependent_reactions, i)
        end
    end

    if !isempty(dependent_reactions)
        @warn "Species '$name' is used in reactions: $dependent_reactions. These reactions may become invalid."
    end

    # Remove species
    new_species = filter(s -> s.name != name, system.species)

    if length(new_species) == length(system.species)
        @warn "Species '$name' not found"
    end

    return ReactionSystem(
        new_species,
        system.reactions,
        parameters=system.parameters,
        subsystems=get(system, :subsystems, Dict{String,ReactionSystem}()),
        description=get(system, :description, nothing)
    )
end

# Event operations (Section 4.4)

"""
    add_continuous_event(model::Model, event::ContinuousEvent) -> Model

Add a continuous event to a model.
"""
function add_continuous_event(model::Model, event::ContinuousEvent)::Model
    new_events = copy(get(model, :continuous_events, ContinuousEvent[]))
    push!(new_events, event)

    return Model(
        model.variables,
        model.equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=new_events,
        discrete_events=get(model, :discrete_events, DiscreteEvent[]),
        description=get(model, :description, nothing)
    )
end

"""
    add_discrete_event(model::Model, event::DiscreteEvent) -> Model

Add a discrete event to a model.
"""
function add_discrete_event(model::Model, event::DiscreteEvent)::Model
    new_events = copy(get(model, :discrete_events, DiscreteEvent[]))
    push!(new_events, event)

    return Model(
        model.variables,
        model.equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=get(model, :continuous_events, ContinuousEvent[]),
        discrete_events=new_events,
        description=get(model, :description, nothing)
    )
end

"""
    remove_event(model::Model, name::String) -> Model

Remove an event by name from a model.

Searches both continuous and discrete events.
"""
function remove_event(model::Model, name::String)::Model
    # Remove from continuous events
    continuous_events = get(model, :continuous_events, ContinuousEvent[])
    new_continuous = filter(e -> get(e, :name, "") != name, continuous_events)

    # Remove from discrete events
    discrete_events = get(model, :discrete_events, DiscreteEvent[])
    new_discrete = filter(e -> get(e, :name, "") != name, discrete_events)

    if length(new_continuous) == length(continuous_events) &&
       length(new_discrete) == length(discrete_events)
        @warn "Event '$name' not found"
    end

    return Model(
        model.variables,
        model.equations,
        subsystems=get(model, :subsystems, Dict{String,Model}()),
        continuous_events=new_continuous,
        discrete_events=new_discrete,
        description=get(model, :description, nothing)
    )
end

# Coupling operations (Section 4.5)

"""
    add_coupling(file::EsmFile, entry::CouplingEntry) -> EsmFile

Add a coupling entry to an ESM file.
"""
function add_coupling(file::EsmFile, entry::CouplingEntry)::EsmFile
    new_coupling = copy(file.coupling)
    push!(new_coupling, entry)

    return EsmFile(
        file.models,
        file.reaction_systems,
        file.data_loaders,
        file.operators,
        new_coupling,
        domain=get(file, :domain, nothing),
        solver=get(file, :solver, nothing),
        references=get(file, :references, Reference[]),
        metadata=get(file, :metadata, nothing)
    )
end

"""
    remove_coupling(file::EsmFile, index::Int) -> EsmFile

Remove a coupling entry by index.
"""
function remove_coupling(file::EsmFile, index::Int)::EsmFile
    if index < 1 || index > length(file.coupling)
        @warn "Coupling index $index out of bounds (1-$(length(file.coupling)))"
        return file
    end

    new_coupling = copy(file.coupling)
    deleteat!(new_coupling, index)

    return EsmFile(
        file.models,
        file.reaction_systems,
        file.data_loaders,
        file.operators,
        new_coupling,
        domain=get(file, :domain, nothing),
        solver=get(file, :solver, nothing),
        references=get(file, :references, Reference[]),
        metadata=get(file, :metadata, nothing)
    )
end

"""
    compose(file::EsmFile, system_a::String, system_b::String) -> EsmFile

Convenience function to create an operator_compose coupling entry.
"""
function compose(file::EsmFile, system_a::String, system_b::String)::EsmFile
    coupling_entry = CouplingOperatorCompose(system_a, system_b)
    return add_coupling(file, coupling_entry)
end

"""
    map_variable(file::EsmFile, from::String, to::String, transform::Union{Expr,Nothing}=nothing) -> EsmFile

Convenience function to create a variable_map coupling entry.
"""
function map_variable(file::EsmFile, from::String, to::String, transform::Union{ESMFormat.Expr,Nothing}=nothing)::EsmFile
    coupling_entry = CouplingVariableMap(from, to, transform)
    return add_coupling(file, coupling_entry)
end

# Model-level operations (Section 4.6)

"""
    merge(file_a::EsmFile, file_b::EsmFile) -> EsmFile

Merge two ESM files.

Combines all components from both files. In case of conflicts, components
from file_b take precedence.
"""
function merge(file_a::EsmFile, file_b::EsmFile)::EsmFile
    # Merge dictionaries (file_b takes precedence), handling nothing values
    merged_models = file_a.models === nothing ? file_b.models :
                   file_b.models === nothing ? file_a.models :
                   Base.merge(file_a.models, file_b.models)

    merged_reaction_systems = file_a.reaction_systems === nothing ? file_b.reaction_systems :
                             file_b.reaction_systems === nothing ? file_a.reaction_systems :
                             Base.merge(file_a.reaction_systems, file_b.reaction_systems)

    merged_data_loaders = file_a.data_loaders === nothing ? file_b.data_loaders :
                         file_b.data_loaders === nothing ? file_a.data_loaders :
                         Base.merge(file_a.data_loaders, file_b.data_loaders)

    merged_operators = file_a.operators === nothing ? file_b.operators :
                      file_b.operators === nothing ? file_a.operators :
                      Base.merge(file_a.operators, file_b.operators)

    # Combine coupling arrays
    merged_coupling = vcat(file_a.coupling, file_b.coupling)

    # Merge other fields (file_b takes precedence)
    merged_domain = file_b.domain !== nothing ? file_b.domain : file_a.domain
    merged_solver = file_b.solver !== nothing ? file_b.solver : file_a.solver
    merged_metadata = file_b.metadata

    return EsmFile(
        file_b.esm,  # Use file_b's version
        merged_metadata,
        models=merged_models,
        reaction_systems=merged_reaction_systems,
        data_loaders=merged_data_loaders,
        operators=merged_operators,
        coupling=merged_coupling,
        domain=merged_domain,
        solver=merged_solver
    )
end

"""
    extract(file::EsmFile, component_name::String) -> EsmFile

Extract a single component into a standalone ESM file.

Creates a new file containing only the specified component and any
coupling entries that reference it.
"""
function extract(file::EsmFile, component_name::String)::EsmFile
    # Find the component
    extracted_models = Dict{String,Model}()
    extracted_reaction_systems = Dict{String,ReactionSystem}()
    extracted_data_loaders = Dict{String,DataLoader}()
    extracted_operators = Dict{String,Operator}()

    if haskey(file.models, component_name)
        extracted_models[component_name] = file.models[component_name]
    elseif haskey(file.reaction_systems, component_name)
        extracted_reaction_systems[component_name] = file.reaction_systems[component_name]
    elseif haskey(file.data_loaders, component_name)
        extracted_data_loaders[component_name] = file.data_loaders[component_name]
    elseif haskey(file.operators, component_name)
        extracted_operators[component_name] = file.operators[component_name]
    else
        @warn "Component '$component_name' not found"
        return EsmFile(
            Dict{String,Model}(),
            Dict{String,ReactionSystem}(),
            Dict{String,DataLoader}(),
            Dict{String,Operator}(),
            CouplingEntry[]
        )
    end

    # Find relevant coupling entries
    relevant_coupling = CouplingEntry[]
    for coupling in file.coupling
        # Check if this coupling involves the extracted component
        involves_component = false

        if coupling isa CouplingOperatorCompose
            involves_component = (coupling.system_a == component_name || coupling.system_b == component_name)
        elseif coupling isa CouplingCouple2
            involves_component = (coupling.system_a == component_name || coupling.system_b == component_name)
        elseif coupling isa CouplingVariableMap
            # Check if source or target involves this component
            source_parts = split(coupling.source, ".")
            target_parts = split(coupling.target, ".")
            involves_component = (length(source_parts) > 0 && source_parts[1] == component_name) ||
                                (length(target_parts) > 0 && target_parts[1] == component_name)
        elseif coupling isa CouplingOperatorApply
            involves_component = (coupling.operator == component_name || component_name in coupling.systems)
        end

        if involves_component
            push!(relevant_coupling, coupling)
        end
    end

    return EsmFile(
        extracted_models,
        extracted_reaction_systems,
        extracted_data_loaders,
        extracted_operators,
        relevant_coupling,
        domain=get(file, :domain, nothing),
        solver=get(file, :solver, nothing),
        references=get(file, :references, Reference[]),
        metadata=get(file, :metadata, nothing)
    )
end