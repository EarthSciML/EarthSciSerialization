using Test
using ESMFormat

@testset "Solver System Tests" begin

    @testset "Solver Strategy Enum" begin
        # Test enum values exist
        @test StrangThreads isa SolverStrategy
        @test StrangSerial isa SolverStrategy
        @test IMEX isa SolverStrategy

        # Test string parsing
        @test parse_solver_strategy("strang_threads") == StrangThreads
        @test parse_solver_strategy("strang_serial") == StrangSerial
        @test parse_solver_strategy("imex") == IMEX

        # Test invalid strategy throws error
        @test_throws ArgumentError parse_solver_strategy("invalid_strategy")

        # Test enum to string conversion
        @test solver_strategy_to_string(StrangThreads) == "strang_threads"
        @test solver_strategy_to_string(StrangSerial) == "strang_serial"
        @test solver_strategy_to_string(IMEX) == "imex"
    end

    @testset "Numerical Method Enum" begin
        # Test enum values exist
        @test FiniteDifferenceMethod isa NumericalMethod
        @test FiniteElementMethod isa NumericalMethod
        @test FiniteVolumeMethod isa NumericalMethod

        # Test string parsing
        @test parse_numerical_method("fdm") == FiniteDifferenceMethod
        @test parse_numerical_method("finite_difference") == FiniteDifferenceMethod
        @test parse_numerical_method("fem") == FiniteElementMethod
        @test parse_numerical_method("finite_element") == FiniteElementMethod
        @test parse_numerical_method("fvm") == FiniteVolumeMethod
        @test parse_numerical_method("finite_volume") == FiniteVolumeMethod

        # Test case insensitive parsing
        @test parse_numerical_method("FDM") == FiniteDifferenceMethod
        @test parse_numerical_method("Fem") == FiniteElementMethod

        # Test invalid method throws error
        @test_throws ArgumentError parse_numerical_method("invalid_method")

        # Test enum to string conversion
        @test numerical_method_to_string(FiniteDifferenceMethod) == "fdm"
        @test numerical_method_to_string(FiniteElementMethod) == "fem"
        @test numerical_method_to_string(FiniteVolumeMethod) == "fvm"
    end

    @testset "SolverConfiguration" begin
        # Test default construction
        config = SolverConfiguration()
        @test config.threads === nothing
        @test config.timestep === nothing
        @test config.stiff_algorithm === nothing
        @test config.nonstiff_algorithm === nothing
        @test config.map_algorithm === nothing
        @test haskey(config.stiff_kwargs, "abstol")
        @test haskey(config.stiff_kwargs, "reltol")
        @test config.numerical_method === nothing
        @test isempty(config.extra_parameters)

        # Test construction with parameters
        config2 = SolverConfiguration(
            threads=4,
            timestep=0.01,
            stiff_algorithm="QNDF",
            nonstiff_algorithm="Tsit5",
            numerical_method=FiniteDifferenceMethod,
            extra_parameters=Dict("custom_param" => 42)
        )
        @test config2.threads == 4
        @test config2.timestep == 0.01
        @test config2.stiff_algorithm == "QNDF"
        @test config2.nonstiff_algorithm == "Tsit5"
        @test config2.numerical_method == FiniteDifferenceMethod
        @test config2.extra_parameters["custom_param"] == 42
    end

    @testset "Solver Construction" begin
        # Test construction with enum strategy
        config = SolverConfiguration(threads=2, stiff_algorithm="QNDF")
        solver = Solver(StrangThreads, config)
        @test solver.strategy == StrangThreads
        @test solver.config.threads == 2
        @test solver.config.stiff_algorithm == "QNDF"

        # Test construction with string strategy
        solver2 = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.001)
        @test solver2.strategy == IMEX
        @test solver2.config.stiff_algorithm == "KenCarp4"
        @test solver2.config.timestep == 0.001

        # Test invalid string strategy throws error
        @test_throws ArgumentError Solver("invalid_strategy")
    end

    @testset "Solver Compatibility Validation" begin
        # Test valid Strang threads configuration
        solver1 = Solver("strang_threads",
                        threads=4,
                        stiff_algorithm="QNDF",
                        nonstiff_algorithm="Tsit5")
        @test validate_solver_compatibility(solver1) == true

        # Test invalid Strang threads (no thread count)
        solver2 = Solver("strang_threads", stiff_algorithm="QNDF")
        @test validate_solver_compatibility(solver2) == false

        # Test valid Strang serial configuration
        solver3 = Solver("strang_serial",
                        stiff_algorithm="QNDF",
                        nonstiff_algorithm="Tsit5")
        @test validate_solver_compatibility(solver3) == true

        # Test invalid Strang serial (too many threads)
        solver4 = Solver("strang_serial",
                        threads=4,
                        stiff_algorithm="QNDF",
                        nonstiff_algorithm="Tsit5")
        @test validate_solver_compatibility(solver4) == false

        # Test valid IMEX configuration
        solver5 = Solver("imex", stiff_algorithm="KenCarp4")
        @test validate_solver_compatibility(solver5) == true

        # Test invalid timestep
        solver6 = Solver("imex", stiff_algorithm="KenCarp4", timestep=-0.1)
        @test validate_solver_compatibility(solver6) == false

        # Test invalid tolerance
        solver7 = Solver("imex", stiff_algorithm="KenCarp4")
        solver7.config.stiff_kwargs["abstol"] = -1e-8
        @test validate_solver_compatibility(solver7) == false
    end

    @testset "Algorithm Recommendations" begin
        # Test FDM recommendations
        rec1 = get_recommended_algorithms(StrangThreads, FiniteDifferenceMethod)
        @test rec1["stiff_algorithm"] == "QNDF"
        @test rec1["nonstiff_algorithm"] == "Tsit5"

        # Test FEM recommendations
        rec2 = get_recommended_algorithms(IMEX, FiniteElementMethod)
        @test rec2["stiff_algorithm"] == "ARKODE"

        # Test FVM recommendations
        rec3 = get_recommended_algorithms(StrangSerial, FiniteVolumeMethod)
        @test rec3["stiff_algorithm"] == "QBDF"
        @test rec3["nonstiff_algorithm"] == "Tsit5"
    end

    @testset "create_solver_with_method" begin
        # Test creation with method and strategy
        solver = create_solver_with_method("strang_threads", "fdm", threads=4)
        @test solver.strategy == StrangThreads
        @test solver.config.numerical_method == FiniteDifferenceMethod
        @test solver.config.stiff_algorithm == "QNDF"
        @test solver.config.nonstiff_algorithm == "Tsit5"
        @test solver.config.threads == 4
        @test validate_solver_compatibility(solver) == true

        # Test IMEX + FEM combination
        solver2 = create_solver_with_method("imex", "fem", timestep=0.01)
        @test solver2.strategy == IMEX
        @test solver2.config.numerical_method == FiniteElementMethod
        @test solver2.config.stiff_algorithm == "ARKODE"
        @test solver2.config.timestep == 0.01
        @test validate_solver_compatibility(solver2) == true
    end

    @testset "Solver Serialization and Parsing" begin
        # Test new format serialization
        solver = Solver("strang_threads",
                       threads=4,
                       stiff_algorithm="QNDF",
                       nonstiff_algorithm="Tsit5",
                       timestep=0.01,
                       numerical_method=FiniteDifferenceMethod)

        serialized = serialize_solver(solver)
        @test serialized["strategy"] == "strang_threads"
        @test serialized["config"]["threads"] == 4
        @test serialized["config"]["stiff_algorithm"] == "QNDF"
        @test serialized["config"]["nonstiff_algorithm"] == "Tsit5"
        @test serialized["config"]["timestep"] == 0.01
        @test serialized["config"]["numerical_method"] == "fdm"

        # Test parsing new format - convert string keys to symbols for coerce_solver
        serialized_with_symbols = Dict(Symbol(k) => v for (k, v) in serialized)
        # Also convert nested config
        if haskey(serialized_with_symbols, :config)
            serialized_with_symbols[:config] = Dict(Symbol(k) => v for (k, v) in serialized_with_symbols[:config])
        end
        parsed_solver = coerce_solver(serialized_with_symbols)
        @test parsed_solver.strategy == StrangThreads
        @test parsed_solver.config.threads == 4
        @test parsed_solver.config.stiff_algorithm == "QNDF"
        @test parsed_solver.config.nonstiff_algorithm == "Tsit5"
        @test parsed_solver.config.timestep == 0.01
        @test parsed_solver.config.numerical_method == FiniteDifferenceMethod

        # Test round-trip serialization/parsing
        reserialized = serialize_solver(parsed_solver)
        # Compare relevant fields (serialized format should match)
        @test reserialized["strategy"] == serialized["strategy"]
        @test reserialized["config"]["threads"] == serialized["config"]["threads"]
    end

    @testset "Legacy Format Parsing" begin
        # Test legacy format with algorithm field
        legacy_data = Dict(
            :algorithm => "Tsit5",
            :tolerances => Dict("rtol" => 1e-6, "abstol" => 1e-8),
            :parameters => Dict("maxiters" => 1000)
        )

        # Should parse with warning
        solver = coerce_solver(legacy_data)
        @test solver.strategy == IMEX  # Default strategy for legacy format
        @test solver.config.stiff_algorithm == "Tsit5"
        @test solver.config.stiff_kwargs["reltol"] == 1e-6
        @test solver.config.stiff_kwargs["abstol"] == 1e-8
        @test solver.config.extra_parameters["maxiters"] == 1000
    end

    @testset "Schema Compliance" begin
        # Test that serialized format matches expected schema structure
        solver = Solver("imex", stiff_algorithm="KenCarp4", timestep=0.001)
        serialized = serialize_solver(solver)

        # Should have required strategy field
        @test haskey(serialized, "strategy")
        @test serialized["strategy"] in ["strang_threads", "strang_serial", "imex"]

        # Should have config field with proper structure
        @test haskey(serialized, "config")
        config = serialized["config"]

        # Test that config follows expected schema
        if haskey(config, "threads")
            @test config["threads"] isa Integer
            @test config["threads"] >= 1
        end

        if haskey(config, "timestep")
            @test config["timestep"] isa Real
            @test config["timestep"] > 0
        end

        if haskey(config, "stiff_kwargs")
            stiff_kwargs = config["stiff_kwargs"]
            @test stiff_kwargs isa Dict
            if haskey(stiff_kwargs, "abstol")
                @test stiff_kwargs["abstol"] isa Real
            end
            if haskey(stiff_kwargs, "reltol")
                @test stiff_kwargs["reltol"] isa Real
            end
        end
    end

    @testset "Error Handling" begin
        # Test missing strategy field
        invalid_data = Dict(:config => Dict(:threads => 4))
        @test_throws ArgumentError coerce_solver(invalid_data)

        # Test invalid strategy
        invalid_data2 = Dict(:strategy => "unknown_strategy")
        @test_throws ArgumentError coerce_solver(invalid_data2)
    end

end