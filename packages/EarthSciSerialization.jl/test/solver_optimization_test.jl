using Test
using EarthSciSerialization

@testset "Solver Optimization Tests" begin

    @testset "PerformanceMetrics" begin
        # Test construction
        metrics = PerformanceMetrics(1.5, 25, 1e-6, 1024*1024, 0.85, true)
        @test metrics.execution_time == 1.5
        @test metrics.convergence_iterations == 25
        @test metrics.error_norm == 1e-6
        @test metrics.memory_usage == 1024*1024
        @test metrics.stability_indicator == 0.85
        @test metrics.success == true

        # Test performance scoring
        score = EarthSciSerialization.calculate_performance_score(metrics)
        @test score > 0.0
        @test score <= 1.0

        # Test failed run scoring
        failed_metrics = PerformanceMetrics(1.0, 100, 1e-3, 1024*1024, 0.1, false)
        @test EarthSciSerialization.calculate_performance_score(failed_metrics) == 0.0
    end

    @testset "ProblemCharacteristics" begin
        # Test default construction
        characteristics = ProblemCharacteristics()
        @test characteristics.stiffness_ratio == 1.0
        @test characteristics.nonlinearity_measure == 0.5
        @test characteristics.problem_size == 100
        @test characteristics.spatial_dimensions == 1
        @test characteristics.temporal_scale == 1.0
        @test characteristics.sparsity_pattern == "sparse"

        # Test construction with custom values
        custom_chars = ProblemCharacteristics(
            stiffness_ratio=1000.0,
            nonlinearity_measure=0.8,
            problem_size=5000,
            spatial_dimensions=3,
            temporal_scale=1e-6,
            sparsity_pattern="dense"
        )
        @test custom_chars.stiffness_ratio == 1000.0
        @test custom_chars.nonlinearity_measure == 0.8
        @test custom_chars.problem_size == 5000
        @test custom_chars.spatial_dimensions == 3
        @test custom_chars.temporal_scale == 1e-6
        @test custom_chars.sparsity_pattern == "dense"
    end

    @testset "OptimizationStrategy Types" begin
        # Test GridSearchStrategy
        param_ranges = Dict{String,Vector{Any}}(
            "abstol" => [1e-6, 1e-8, 1e-10],
            "reltol" => [1e-3, 1e-4, 1e-6]
        )
        grid_strategy = GridSearchStrategy(param_ranges)
        @test grid_strategy.parameter_ranges == param_ranges
        @test grid_strategy.max_evaluations == 50

        grid_strategy_custom = GridSearchStrategy(param_ranges, max_evaluations=100)
        @test grid_strategy_custom.max_evaluations == 100

        # Test AdaptiveStrategy
        adaptive_strategy = AdaptiveStrategy()
        @test adaptive_strategy.learning_rate == 0.1
        @test adaptive_strategy.adaptation_threshold == 0.05
        @test adaptive_strategy.history_window == 10

        adaptive_custom = AdaptiveStrategy(learning_rate=0.2, adaptation_threshold=0.1, history_window=5)
        @test adaptive_custom.learning_rate == 0.2
        @test adaptive_custom.adaptation_threshold == 0.1
        @test adaptive_custom.history_window == 5
    end

    @testset "SolverOptimizer" begin
        # Test construction
        strategy = AdaptiveStrategy()
        optimizer = SolverOptimizer(strategy)
        @test optimizer.strategy === strategy
        @test isempty(optimizer.history.configurations)
        @test isempty(optimizer.history.metrics)
        @test isempty(optimizer.history.timestamps)
        @test optimizer.current_best === nothing
        @test optimizer.best_performance === nothing
        @test optimizer.problem_characteristics === nothing

        # Test setting problem characteristics
        characteristics = ProblemCharacteristics(stiffness_ratio=100.0, problem_size=1000)
        set_problem_characteristics!(optimizer, characteristics)
        @test optimizer.problem_characteristics === characteristics
    end

    @testset "Performance Recording and Best Configuration" begin
        optimizer = SolverOptimizer(AdaptiveStrategy())
        solver = Solver("strang_threads", threads=4, stiff_algorithm="QNDF")

        # Record first performance
        metrics1 = PerformanceMetrics(2.0, 30, 1e-5, 1024*1024, 0.7, true)
        record_performance!(optimizer, solver.config, metrics1)

        @test length(optimizer.history.configurations) == 1
        @test length(optimizer.history.metrics) == 1
        @test optimizer.current_best == solver.config
        @test optimizer.best_performance === metrics1

        # Record better performance
        better_solver = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.01)
        metrics2 = PerformanceMetrics(1.0, 20, 1e-7, 512*1024, 0.9, true)
        record_performance!(optimizer, better_solver.config, metrics2)

        @test length(optimizer.history.configurations) == 2
        @test optimizer.current_best == better_solver.config
        @test optimizer.best_performance === metrics2

        # Record worse performance (should not update best)
        worse_solver = Solver("strang_serial", stiff_algorithm="QBDF")
        metrics3 = PerformanceMetrics(3.0, 50, 1e-4, 2*1024*1024, 0.5, true)
        record_performance!(optimizer, worse_solver.config, metrics3)

        @test length(optimizer.history.configurations) == 3
        @test optimizer.current_best == better_solver.config  # Should still be the better one
        @test optimizer.best_performance === metrics2

        # Test get_best_configuration
        best_config = get_best_configuration(optimizer)
        @test best_config == better_solver.config
    end

    @testset "Configuration Dictionary Conversion" begin
        # Test solver_config_to_dict
        config = SolverConfiguration(
            threads=4,
            timestep=0.01,
            stiff_algorithm="QNDF",
            nonstiff_algorithm="Tsit5",
            numerical_method=FiniteDifferenceMethod,
            stiff_kwargs=Dict("abstol" => 1e-8, "reltol" => 1e-6),
            extra_parameters=Dict("custom_param" => 42)
        )

        dict_config = EarthSciSerialization.solver_config_to_dict(config)
        @test dict_config["threads"] == 4
        @test dict_config["timestep"] == 0.01
        @test dict_config["stiff_algorithm"] == "QNDF"
        @test dict_config["nonstiff_algorithm"] == "Tsit5"
        @test dict_config["numerical_method"] == FiniteDifferenceMethod
        @test dict_config["abstol"] == 1e-8
        @test dict_config["reltol"] == 1e-6
        @test dict_config["custom_param"] == 42

        # Test dict_to_solver_config (round trip)
        converted_config = EarthSciSerialization.dict_to_solver_config(dict_config)
        @test converted_config.threads == config.threads
        @test converted_config.timestep == config.timestep
        @test converted_config.stiff_algorithm == config.stiff_algorithm
        @test converted_config.nonstiff_algorithm == config.nonstiff_algorithm
        @test converted_config.numerical_method == config.numerical_method
        @test converted_config.stiff_kwargs["abstol"] == config.stiff_kwargs["abstol"]
        @test converted_config.stiff_kwargs["reltol"] == config.stiff_kwargs["reltol"]
        @test converted_config.extra_parameters["custom_param"] == config.extra_parameters["custom_param"]
    end

    @testset "Problem Characteristics Adaptation" begin
        base_config = Dict{String,Any}(
            "abstol" => 1e-6,
            "reltol" => 1e-4,
            "timestep" => 1e-2,
            "threads" => 2
        )

        # Test stiff problem adaptation
        stiff_characteristics = ProblemCharacteristics(
            stiffness_ratio=1000.0,
            temporal_scale=1e-6,
            problem_size=100
        )

        adapted_config = EarthSciSerialization.adapt_for_problem_characteristics(base_config, stiff_characteristics)
        @test adapted_config.stiff_kwargs["abstol"] == 1e-10  # Tighter tolerance
        @test adapted_config.stiff_kwargs["reltol"] == 1e-8   # Tighter tolerance
        @test adapted_config.stiff_algorithm == "QNDF"       # Stiff solver
        @test adapted_config.timestep < base_config["timestep"]  # Smaller timestep
        @test adapted_config.threads == 1  # Small problem, single thread

        # Test non-stiff problem adaptation
        nonstiff_characteristics = ProblemCharacteristics(
            stiffness_ratio=5.0,
            temporal_scale=1.0,
            problem_size=15000
        )

        adapted_config2 = EarthSciSerialization.adapt_for_problem_characteristics(base_config, nonstiff_characteristics)
        @test adapted_config2.stiff_kwargs["abstol"] == 1e-6
        @test adapted_config2.stiff_kwargs["reltol"] == 1e-4
        @test adapted_config2.nonstiff_algorithm == "Tsit5"  # Fast explicit method
        @test adapted_config2.threads > 1  # Large problem, use multiple threads
    end

    @testset "Auto-tuning Convenience Functions" begin
        # Test create_auto_tuning_optimizer
        adaptive_optimizer = create_auto_tuning_optimizer(strategy="adaptive")
        @test adaptive_optimizer.strategy isa AdaptiveStrategy

        grid_optimizer = create_auto_tuning_optimizer(strategy="grid_search", max_evaluations=100)
        @test grid_optimizer.strategy isa GridSearchStrategy
        @test grid_optimizer.strategy.max_evaluations == 100

        # Test invalid strategy
        @test_throws ErrorException create_auto_tuning_optimizer(strategy="invalid")

        # Test auto_tune_solver
        base_solver = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.01)
        characteristics = ProblemCharacteristics(
            stiffness_ratio=500.0,
            problem_size=2000,
            temporal_scale=1e-5
        )

        tuned_solver = auto_tune_solver(base_solver, characteristics, max_iterations=10)
        @test tuned_solver isa Solver
        @test tuned_solver.strategy == base_solver.strategy
        # Configuration should be adapted based on characteristics
        @test tuned_solver.config !== base_solver.config
    end

    @testset "Grid Search Strategy Suggestion" begin
        param_ranges = Dict{String,Vector{Any}}(
            "abstol" => [1e-6, 1e-8, 1e-10],
            "timestep" => [1e-3, 1e-2, 1e-1]
        )
        strategy = GridSearchStrategy(param_ranges, max_evaluations=10)
        optimizer = SolverOptimizer(strategy)
        base_solver = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.01)

        # Test suggestion with empty history
        suggested_config = suggest_next_configuration(optimizer, base_solver)
        @test suggested_config isa SolverConfiguration

        # Test suggestion with some history
        metrics = PerformanceMetrics(1.0, 20, 1e-7, 1024*1024, 0.8, true)
        record_performance!(optimizer, suggested_config, metrics)

        suggested_config2 = suggest_next_configuration(optimizer, base_solver)
        @test suggested_config2 isa SolverConfiguration
    end

    @testset "Adaptive Strategy Suggestion" begin
        strategy = AdaptiveStrategy()
        optimizer = SolverOptimizer(strategy)
        base_solver = Solver("strang_threads", threads=4, stiff_algorithm="QNDF")
        characteristics = ProblemCharacteristics(stiffness_ratio=200.0, problem_size=1000)

        set_problem_characteristics!(optimizer, characteristics)

        # Test suggestion with minimal history
        suggested_config = suggest_next_configuration(optimizer, base_solver)
        @test suggested_config isa SolverConfiguration

        # Add some history
        for i in 1:5
            metrics = PerformanceMetrics(
                1.0 + 0.1*i, 20 + i, 1e-7, 1024*1024, 0.8 - 0.02*i, true
            )
            config = SolverConfiguration(threads=i, timestep=0.01*i)
            record_performance!(optimizer, config, metrics)
        end

        # Test suggestion with sufficient history
        suggested_config2 = suggest_next_configuration(optimizer, base_solver)
        @test suggested_config2 isa SolverConfiguration
    end

    @testset "Performance Comparison" begin
        # Test is_better_performance function
        good_metrics = PerformanceMetrics(1.0, 20, 1e-8, 512*1024, 0.9, true)
        bad_metrics = PerformanceMetrics(3.0, 100, 1e-4, 2*1024*1024, 0.5, true)
        failed_metrics = PerformanceMetrics(1.0, 20, 1e-8, 512*1024, 0.9, false)

        @test EarthSciSerialization.is_better_performance(good_metrics, bad_metrics) == true
        @test EarthSciSerialization.is_better_performance(bad_metrics, good_metrics) == false
        @test EarthSciSerialization.is_better_performance(failed_metrics, good_metrics) == false
        @test EarthSciSerialization.is_better_performance(good_metrics, failed_metrics) == true

        # Test performance scores
        good_score = EarthSciSerialization.calculate_performance_score(good_metrics)
        bad_score = EarthSciSerialization.calculate_performance_score(bad_metrics)
        @test good_score > bad_score
    end

    @testset "Parameter Adaptation" begin
        # Test configuration parameter adaptation
        config = SolverConfiguration(
            timestep=0.01,
            stiff_kwargs=Dict("abstol" => 1e-6, "reltol" => 1e-4)
        )

        # High error metrics should tighten tolerances
        high_error_metrics = PerformanceMetrics(1.0, 20, 1e-3, 1024*1024, 0.6, true)
        adapted_config = EarthSciSerialization.adapt_configuration_parameters(config, high_error_metrics, 0.1)
        @test adapted_config.stiff_kwargs["abstol"] < config.stiff_kwargs["abstol"]
        @test adapted_config.stiff_kwargs["reltol"] < config.stiff_kwargs["reltol"]

        # Low error, high stability metrics should relax tolerances
        excellent_metrics = PerformanceMetrics(0.5, 5, 1e-10, 256*1024, 0.95, true)
        relaxed_config = EarthSciSerialization.adapt_configuration_parameters(config, excellent_metrics, 0.1)
        @test relaxed_config.stiff_kwargs["abstol"] > config.stiff_kwargs["abstol"]
        @test relaxed_config.stiff_kwargs["reltol"] > config.stiff_kwargs["reltol"]

        # High iterations should reduce timestep
        slow_convergence_metrics = PerformanceMetrics(2.0, 150, 1e-6, 1024*1024, 0.8, true)
        smaller_step_config = EarthSciSerialization.adapt_configuration_parameters(config, slow_convergence_metrics, 0.1)
        @test smaller_step_config.timestep < config.timestep

        # Fast convergence should increase timestep
        fast_convergence_metrics = PerformanceMetrics(0.8, 5, 1e-6, 1024*1024, 0.8, true)
        larger_step_config = EarthSciSerialization.adapt_configuration_parameters(config, fast_convergence_metrics, 0.1)
        @test larger_step_config.timestep > config.timestep
    end

end