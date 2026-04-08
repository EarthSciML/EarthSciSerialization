"""
Solver Parameter Optimization and Auto-tuning

This module provides capabilities for automatically optimizing solver parameters,
monitoring performance, and adapting parameters based on problem characteristics.
"""

# ========================================
# Performance Monitoring Types
# ========================================

"""
    PerformanceMetrics

Stores performance metrics from solver execution.
"""
struct PerformanceMetrics
    execution_time::Float64
    convergence_iterations::Int
    error_norm::Float64
    memory_usage::Int  # in bytes
    stability_indicator::Float64  # 0.0 = unstable, 1.0 = stable
    success::Bool

    # Constructor
    PerformanceMetrics(execution_time, convergence_iterations, error_norm,
                      memory_usage, stability_indicator, success) =
        new(execution_time, convergence_iterations, error_norm,
            memory_usage, stability_indicator, success)
end

"""
    ProblemCharacteristics

Characterizes the mathematical properties of the problem being solved.
"""
struct ProblemCharacteristics
    stiffness_ratio::Float64  # Ratio of fastest to slowest timescales
    nonlinearity_measure::Float64  # Measure of system nonlinearity
    problem_size::Int  # Number of variables/equations
    spatial_dimensions::Int  # Number of spatial dimensions
    temporal_scale::Float64  # Characteristic time scale
    sparsity_pattern::String  # "dense", "sparse", "banded"

    # Constructor with defaults
    ProblemCharacteristics(; stiffness_ratio=1.0, nonlinearity_measure=0.5,
                          problem_size=100, spatial_dimensions=1,
                          temporal_scale=1.0, sparsity_pattern="sparse") =
        new(stiffness_ratio, nonlinearity_measure, problem_size,
            spatial_dimensions, temporal_scale, sparsity_pattern)
end

# ========================================
# Optimization Strategy Types
# ========================================

"""
    OptimizationStrategy

Abstract base type for different parameter optimization strategies.
"""
abstract type OptimizationStrategy end

"""
    GridSearchStrategy <: OptimizationStrategy

Grid search over predefined parameter ranges.
"""
struct GridSearchStrategy <: OptimizationStrategy
    parameter_ranges::Dict{String,Vector{Any}}
    max_evaluations::Int

    GridSearchStrategy(parameter_ranges::Dict{String,Vector{Any}}; max_evaluations=50) =
        new(parameter_ranges, max_evaluations)
end

"""
    AdaptiveStrategy <: OptimizationStrategy

Adaptive parameter adjustment based on performance feedback.
"""
struct AdaptiveStrategy <: OptimizationStrategy
    learning_rate::Float64
    adaptation_threshold::Float64
    history_window::Int

    AdaptiveStrategy(; learning_rate=0.1, adaptation_threshold=0.05, history_window=10) =
        new(learning_rate, adaptation_threshold, history_window)
end

# ========================================
# Optimization State Management
# ========================================

"""
    OptimizationHistory

Tracks the history of parameter configurations and their performance.
"""
mutable struct OptimizationHistory
    configurations::Vector{SolverConfiguration}
    metrics::Vector{PerformanceMetrics}
    timestamps::Vector{Float64}

    OptimizationHistory() = new(Vector{SolverConfiguration}(),
                               Vector{PerformanceMetrics}(),
                               Vector{Float64}())
end

"""
    SolverOptimizer

Main optimization controller that manages parameter tuning.
"""
mutable struct SolverOptimizer
    strategy::OptimizationStrategy
    history::OptimizationHistory
    current_best::Union{SolverConfiguration,Nothing}
    best_performance::Union{PerformanceMetrics,Nothing}
    problem_characteristics::Union{ProblemCharacteristics,Nothing}

    SolverOptimizer(strategy::OptimizationStrategy) =
        new(strategy, OptimizationHistory(), nothing, nothing, nothing)
end

# ========================================
# Core Optimization Functions
# ========================================

"""
    set_problem_characteristics!(optimizer::SolverOptimizer, characteristics::ProblemCharacteristics)

Set the problem characteristics for the optimizer to use in parameter selection.
"""
function set_problem_characteristics!(optimizer::SolverOptimizer, characteristics::ProblemCharacteristics)
    optimizer.problem_characteristics = characteristics
    return optimizer
end

"""
    record_performance!(optimizer::SolverOptimizer, config::SolverConfiguration, metrics::PerformanceMetrics)

Record a performance measurement for a given configuration.
"""
function record_performance!(optimizer::SolverOptimizer, config::SolverConfiguration, metrics::PerformanceMetrics)
    push!(optimizer.history.configurations, config)
    push!(optimizer.history.metrics, metrics)
    push!(optimizer.history.timestamps, time())

    # Update best configuration if this one is better
    if optimizer.best_performance === nothing || is_better_performance(metrics, optimizer.best_performance)
        optimizer.current_best = config
        optimizer.best_performance = metrics
    end

    return optimizer
end

"""
    is_better_performance(new_metrics::PerformanceMetrics, current_best::PerformanceMetrics) -> Bool

Determine if new performance metrics are better than current best.
Priority: success > stability > speed > memory efficiency
"""
function is_better_performance(new_metrics::PerformanceMetrics, current_best::PerformanceMetrics)::Bool
    # Failed runs are never better
    if !new_metrics.success
        return false
    end

    # If current best failed but new one succeeded, new is better
    if !current_best.success && new_metrics.success
        return true
    end

    # Both succeeded, compare based on composite score
    new_score = calculate_performance_score(new_metrics)
    current_score = calculate_performance_score(current_best)

    return new_score > current_score
end

"""
    calculate_performance_score(metrics::PerformanceMetrics) -> Float64

Calculate a composite performance score (higher is better).
"""
function calculate_performance_score(metrics::PerformanceMetrics)::Float64
    if !metrics.success
        return 0.0
    end

    # Normalize and weight different metrics
    # Weights: stability (40%), speed (30%), accuracy (20%), memory (10%)
    stability_weight = 0.4
    speed_weight = 0.3
    accuracy_weight = 0.2
    memory_weight = 0.1

    # Normalize execution time (lower is better, so invert)
    speed_score = 1.0 / (1.0 + metrics.execution_time)

    # Stability score (higher is better)
    stability_score = metrics.stability_indicator

    # Accuracy score (lower error is better, so invert)
    accuracy_score = 1.0 / (1.0 + metrics.error_norm)

    # Memory efficiency (lower usage is better, normalized to GB scale)
    memory_gb = metrics.memory_usage / (1024^3)
    memory_score = 1.0 / (1.0 + memory_gb)

    return (stability_weight * stability_score +
            speed_weight * speed_score +
            accuracy_weight * accuracy_score +
            memory_weight * memory_score)
end

"""
    get_best_configuration(optimizer::SolverOptimizer) -> Union{SolverConfiguration, Nothing}

Get the current best solver configuration.
"""
function get_best_configuration(optimizer::SolverOptimizer)
    return optimizer.current_best
end

"""
    suggest_next_configuration(optimizer::SolverOptimizer, base_solver::Solver) -> SolverConfiguration

Suggest the next configuration to try based on optimization strategy and history.
"""
function suggest_next_configuration(optimizer::SolverOptimizer, base_solver::Solver)::SolverConfiguration
    if optimizer.strategy isa GridSearchStrategy
        return suggest_grid_search_configuration(optimizer.strategy, optimizer.history, base_solver)
    elseif optimizer.strategy isa AdaptiveStrategy
        return suggest_adaptive_configuration(optimizer.strategy, optimizer.history, base_solver,
                                             optimizer.problem_characteristics)
    else
        error("Unknown optimization strategy: $(typeof(optimizer.strategy))")
    end
end

# ========================================
# Strategy-Specific Implementation
# ========================================

"""
    suggest_grid_search_configuration(strategy::GridSearchStrategy, history::OptimizationHistory, base_solver::Solver) -> SolverConfiguration

Suggest next configuration using grid search strategy.
"""
function suggest_grid_search_configuration(strategy::GridSearchStrategy, history::OptimizationHistory,
                                         base_solver::Solver)::SolverConfiguration
    # Start with base configuration
    config_dict = solver_config_to_dict(base_solver.config)

    # If we haven't tried many configurations yet, explore parameter space
    if length(history.configurations) < strategy.max_evaluations
        for (param_name, param_values) in strategy.parameter_ranges
            if haskey(config_dict, param_name)
                # Choose a value we haven't tried much
                chosen_value = param_values[mod(length(history.configurations), length(param_values)) + 1]
                config_dict[param_name] = chosen_value
            end
        end
    else
        # Use best known configuration
        if !isempty(history.configurations)
            best_idx = findmax(calculate_performance_score.(history.metrics))[2]
            return history.configurations[best_idx]
        end
    end

    return dict_to_solver_config(config_dict)
end

"""
    suggest_adaptive_configuration(strategy::AdaptiveStrategy, history::OptimizationHistory,
                                  base_solver::Solver, problem_chars::Union{ProblemCharacteristics,Nothing}) -> SolverConfiguration

Suggest next configuration using adaptive strategy.
"""
function suggest_adaptive_configuration(strategy::AdaptiveStrategy, history::OptimizationHistory,
                                       base_solver::Solver, problem_chars::Union{ProblemCharacteristics,Nothing})::SolverConfiguration
    config_dict = solver_config_to_dict(base_solver.config)

    # If we don't have enough history, use problem characteristics to guide initial choice
    if length(history.configurations) < 3
        if problem_chars !== nothing
            return adapt_for_problem_characteristics(config_dict, problem_chars)
        else
            return base_solver.config
        end
    end

    # Use recent history to adapt parameters
    recent_window = min(strategy.history_window, length(history.configurations))
    recent_configs = history.configurations[end-recent_window+1:end]
    recent_metrics = history.metrics[end-recent_window+1:end]

    # Find the best recent configuration
    best_idx = findmax(calculate_performance_score.(recent_metrics))[2]
    best_config = recent_configs[best_idx]
    best_metrics = recent_metrics[best_idx]

    # Adapt parameters based on performance trends
    adapted_config = adapt_configuration_parameters(best_config, best_metrics, strategy.learning_rate)

    return adapted_config
end

# ========================================
# Helper Functions
# ========================================

"""
    solver_config_to_dict(config::SolverConfiguration) -> Dict{String,Any}

Convert SolverConfiguration to dictionary for manipulation.
"""
function solver_config_to_dict(config::SolverConfiguration)::Dict{String,Any}
    result = Dict{String,Any}()

    if config.threads !== nothing
        result["threads"] = config.threads
    end
    if config.timestep !== nothing
        result["timestep"] = config.timestep
    end
    if config.stiff_algorithm !== nothing
        result["stiff_algorithm"] = config.stiff_algorithm
    end
    if config.nonstiff_algorithm !== nothing
        result["nonstiff_algorithm"] = config.nonstiff_algorithm
    end
    if config.numerical_method !== nothing
        result["numerical_method"] = config.numerical_method
    end

    # Add tolerance parameters
    merge!(result, config.stiff_kwargs)
    merge!(result, config.extra_parameters)

    return result
end

"""
    dict_to_solver_config(config_dict::Dict{String,Any}) -> SolverConfiguration

Convert dictionary back to SolverConfiguration.
"""
function dict_to_solver_config(config_dict::Dict{String,Any})::SolverConfiguration
    # Extract standard parameters
    threads = get(config_dict, "threads", nothing)
    timestep = get(config_dict, "timestep", nothing)
    stiff_algorithm = get(config_dict, "stiff_algorithm", nothing)
    nonstiff_algorithm = get(config_dict, "nonstiff_algorithm", nothing)
    map_algorithm = get(config_dict, "map_algorithm", nothing)
    numerical_method = get(config_dict, "numerical_method", nothing)

    # Extract tolerance parameters
    stiff_kwargs = Dict{String,Any}()
    for key in ["abstol", "reltol", "maxiters", "dtmin", "dtmax"]
        if haskey(config_dict, key)
            stiff_kwargs[key] = config_dict[key]
        end
    end

    # Extract extra parameters (everything else)
    standard_keys = Set(["threads", "timestep", "stiff_algorithm", "nonstiff_algorithm",
                        "map_algorithm", "numerical_method", "abstol", "reltol",
                        "maxiters", "dtmin", "dtmax"])
    extra_parameters = Dict{String,Any}()
    for (key, value) in config_dict
        if !(key in standard_keys)
            extra_parameters[key] = value
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
    adapt_for_problem_characteristics(config_dict::Dict{String,Any}, characteristics::ProblemCharacteristics) -> SolverConfiguration

Adapt configuration based on problem characteristics.
"""
function adapt_for_problem_characteristics(config_dict::Dict{String,Any}, characteristics::ProblemCharacteristics)::SolverConfiguration
    # Adjust tolerances based on problem stiffness
    if characteristics.stiffness_ratio > 100.0  # Very stiff problem
        config_dict["abstol"] = 1e-10
        config_dict["reltol"] = 1e-8
        config_dict["stiff_algorithm"] = "QNDF"  # Good for stiff problems
    elseif characteristics.stiffness_ratio < 10.0  # Non-stiff problem
        config_dict["abstol"] = 1e-6
        config_dict["reltol"] = 1e-4
        config_dict["nonstiff_algorithm"] = "Tsit5"  # Fast explicit method
    end

    # Adjust timestep based on temporal scale
    if characteristics.temporal_scale <= 1e-6  # Very fast dynamics
        new_timestep = characteristics.temporal_scale / 100
        # Ensure the new timestep is actually smaller than the current one
        if haskey(config_dict, "timestep") && config_dict["timestep"] != nothing
            current_timestep = config_dict["timestep"]
            # Choose the smaller of the calculated timestep or half the current one
            config_dict["timestep"] = min(new_timestep, current_timestep * 0.5)
        else
            config_dict["timestep"] = new_timestep
        end
    elseif characteristics.temporal_scale > 1e6  # Very slow dynamics
        config_dict["timestep"] = characteristics.temporal_scale / 1000
    else
        # For normal temporal scales, use a moderate timestep if not already set
        if !haskey(config_dict, "timestep") || config_dict["timestep"] == nothing
            config_dict["timestep"] = characteristics.temporal_scale / 1000
        else
            # Adjust existing timestep based on temporal scale
            current_timestep = config_dict["timestep"]
            if current_timestep > characteristics.temporal_scale / 10
                config_dict["timestep"] = characteristics.temporal_scale / 100
            end
        end
    end

    # Adjust threading based on problem size
    if characteristics.problem_size > 10000  # Large problem
        config_dict["threads"] = min(8, max(2, Threads.nthreads()))
    else  # Small problem - overhead may not be worth it
        config_dict["threads"] = 1
    end

    return dict_to_solver_config(config_dict)
end

"""
    adapt_configuration_parameters(config::SolverConfiguration, metrics::PerformanceMetrics, learning_rate::Float64) -> SolverConfiguration

Adapt configuration parameters based on performance metrics.
"""
function adapt_configuration_parameters(config::SolverConfiguration, metrics::PerformanceMetrics, learning_rate::Float64)::SolverConfiguration
    config_dict = solver_config_to_dict(config)

    # Adjust tolerances based on error and stability
    if metrics.error_norm > 1e-4 || metrics.stability_indicator < 0.7
        # Tighten tolerances
        if haskey(config_dict, "abstol")
            config_dict["abstol"] = config_dict["abstol"] * (1.0 - learning_rate)
        end
        if haskey(config_dict, "reltol")
            config_dict["reltol"] = config_dict["reltol"] * (1.0 - learning_rate)
        end
    elseif metrics.error_norm < 1e-8 && metrics.stability_indicator > 0.9
        # Relax tolerances to improve speed
        if haskey(config_dict, "abstol")
            config_dict["abstol"] = config_dict["abstol"] * (1.0 + learning_rate * 0.5)
        end
        if haskey(config_dict, "reltol")
            config_dict["reltol"] = config_dict["reltol"] * (1.0 + learning_rate * 0.5)
        end
    end

    # Adjust timestep based on convergence behavior
    if metrics.convergence_iterations > 100 && haskey(config_dict, "timestep")
        # Reduce timestep to improve convergence
        config_dict["timestep"] = config_dict["timestep"] * (1.0 - learning_rate)
    elseif metrics.convergence_iterations < 10 && haskey(config_dict, "timestep")
        # Increase timestep for efficiency
        config_dict["timestep"] = config_dict["timestep"] * (1.0 + learning_rate * 0.3)
    end

    return dict_to_solver_config(config_dict)
end

# ========================================
# Auto-tuning Convenience Functions
# ========================================

"""
    create_auto_tuning_optimizer(;strategy="adaptive", max_evaluations=50) -> SolverOptimizer

Create a solver optimizer with sensible defaults for auto-tuning.
"""
function create_auto_tuning_optimizer(; strategy="adaptive", max_evaluations=50)::SolverOptimizer
    if strategy == "adaptive"
        return SolverOptimizer(AdaptiveStrategy())
    elseif strategy == "grid_search"
        # Default parameter ranges for grid search
        param_ranges = Dict{String,Vector{Any}}(
            "abstol" => [1e-6, 1e-8, 1e-10, 1e-12],
            "reltol" => [1e-3, 1e-4, 1e-6, 1e-8],
            "timestep" => [1e-4, 1e-3, 1e-2, 1e-1],
            "threads" => [1, 2, 4, 8]
        )
        return SolverOptimizer(GridSearchStrategy(param_ranges, max_evaluations=max_evaluations))
    else
        error("Unknown strategy: $strategy. Use 'adaptive' or 'grid_search'.")
    end
end

"""
    auto_tune_solver(base_solver::Solver, problem_characteristics::ProblemCharacteristics;
                    max_iterations=20) -> Solver

Automatically tune solver parameters based on problem characteristics.
Returns an optimized solver configuration.
"""
function auto_tune_solver(base_solver::Solver, problem_characteristics::ProblemCharacteristics;
                         max_iterations=20)::Solver
    optimizer = create_auto_tuning_optimizer(strategy="adaptive")
    set_problem_characteristics!(optimizer, problem_characteristics)

    best_config = base_solver.config

    # In a real implementation, we would run the solver and measure performance
    # For now, we'll use the problem characteristics to make an informed guess
    adapted_config = adapt_for_problem_characteristics(
        solver_config_to_dict(base_solver.config),
        problem_characteristics
    )

    # Create mock performance metrics based on characteristics
    mock_metrics = PerformanceMetrics(
        1.0,  # execution_time
        50,   # convergence_iterations
        1e-6, # error_norm
        1024*1024*100,  # memory_usage (100MB)
        0.8,  # stability_indicator
        true  # success
    )

    record_performance!(optimizer, adapted_config, mock_metrics)

    return Solver(base_solver.strategy, optimizer.current_best)
end