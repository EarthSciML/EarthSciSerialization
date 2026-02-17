# Performance Recording and Best Configuration (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/solver_optimization_test.jl`

```julia
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
```

