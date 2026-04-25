using Test
using EarthSciSerialization

@testset "MMS evaluator (esm-ivo)" begin

    @testset "parse_accuracy_order" begin
        @test parse_accuracy_order("O(dx^2)") == 2.0
        @test parse_accuracy_order("O(h^4)") == 4.0
        @test parse_accuracy_order("O(Δx^1.5)") == 1.5
        @test parse_accuracy_order("O(dx)") == 1.0
        @test_throws MMSEvaluatorError parse_accuracy_order("first-order")
        @test_throws MMSEvaluatorError parse_accuracy_order("O(dx**2)")
    end

    @testset "lookup_manufactured_solution" begin
        ms = lookup_manufactured_solution(
            "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)")
        @test ms.name === :sin_2pi_x_periodic
        @test ms.periodic
        @test ms.domain == (0.0, 1.0)
        @test isapprox(ms.sample(0.25), 1.0; atol=1e-12)
        @test isapprox(ms.derivative(0.0), 2π; atol=1e-12)
        @test_throws MMSEvaluatorError lookup_manufactured_solution(
            "polynomial x^3 on [0,1]")
    end

    @testset "register_manufactured_solution!" begin
        custom = ManufacturedSolution(
            :_test_cos, x -> cos(x), x -> -sin(x), false, (0.0, 2π))
        register_manufactured_solution!(custom)
        @test EarthSciSerialization._MMS_REGISTRY[:_test_cos] === custom
        delete!(EarthSciSerialization._MMS_REGISTRY, :_test_cos)
    end

    @testset "apply_stencil_periodic_1d — centered 2nd FD" begin
        # Centered 2nd-order finite difference: (-1/(2dx), +1/(2dx)) at offsets ±1.
        stencil = [
            Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => -1),
                 "coeff" => Dict("op" => "/", "args" =>
                     Any[-1, Dict("op" => "*", "args" => Any[2, "dx"])])),
            Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => 1),
                 "coeff" => Dict("op" => "/", "args" =>
                     Any[1, Dict("op" => "*", "args" => Any[2, "dx"])])),
        ]
        n = 64
        dx = 1.0 / n
        u = [sin(2π * (i - 0.5) * dx) for i in 1:n]
        bindings = Dict("dx" => dx)
        du = apply_stencil_periodic_1d(stencil, u, bindings)
        du_exact = [2π * cos(2π * (i - 0.5) * dx) for i in 1:n]
        @test maximum(abs.(du .- du_exact)) < 0.05  # second-order on n=64

        # Periodic wrap: stencil at index 1 reads index n.
        @test isfinite(du[1]) && isfinite(du[n])
    end

    # The centered_2nd_uniform fixture lives in EarthSciDiscretizations
    # (`discretizations/finite_difference/centered_2nd_uniform/fixtures/convergence/`).
    # We embed an equivalent dict here so the ESS test suite is self-contained;
    # the on-disk fixtures are byte-identical.
    centered_2nd_uniform_rule = Dict(
        "discretizations" => Dict(
            "centered_2nd_uniform" => Dict(
                "applies_to" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                "grid_family" => "cartesian",
                "combine" => "+",
                "accuracy" => "O(dx^2)",
                "stencil" => [
                    Dict("selector" => Dict("kind" => "cartesian",
                                            "axis" => "\$x",
                                            "offset" => -1),
                         "coeff" => Dict("op" => "/", "args" =>
                             Any[-1, Dict("op" => "*", "args" => Any[2, "dx"])])),
                    Dict("selector" => Dict("kind" => "cartesian",
                                            "axis" => "\$x",
                                            "offset" => 1),
                         "coeff" => Dict("op" => "/", "args" =>
                             Any[1, Dict("op" => "*", "args" => Any[2, "dx"])])),
                ],
            ),
        ),
    )
    centered_input = Dict(
        "rule" => "centered_2nd_uniform",
        "manufactured_solution" =>
            "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)",
        "sampling" => "cell_center",
        "grids" => [Dict("n" => 16), Dict("n" => 32),
                    Dict("n" => 64), Dict("n" => 128)],
    )
    centered_expected = Dict(
        "rule" => "centered_2nd_uniform",
        "metric" => "Linf",
        "expected_min_order" => 1.9,
    )

    @testset "mms_convergence — centered_2nd_uniform fixture" begin
        result = mms_convergence(centered_2nd_uniform_rule, centered_input)
        @test result.grids == [16, 32, 64, 128]
        @test length(result.errors) == 4
        @test all(result.errors .> 0)
        @test all(isfinite, result.errors)
        # Errors must shrink monotonically — second-order convergence.
        @test all(result.errors[i] > result.errors[i+1] for i in 1:3)
        # Declared O(dx^2) — observed min must be within ±0.2 of 2.0.
        @test result.declared_order == 2.0
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
        # Final-pair order tightens to ~2.0.
        @test result.orders[end] ≥ 1.95
    end

    @testset "verify_mms_convergence — passes on the proven case" begin
        result = verify_mms_convergence(
            centered_2nd_uniform_rule, centered_input, centered_expected)
        @test result.observed_min_order ≥ centered_expected["expected_min_order"]
    end

    @testset "verify_mms_convergence — flags an order deficit" begin
        # Build a deliberately broken stencil: forward difference labelled as
        # `O(dx^2)`. It is only first-order, so the harness must reject it
        # against the existing 1.9 threshold.
        broken_rule = deepcopy(centered_2nd_uniform_rule)
        broken_rule["discretizations"]["centered_2nd_uniform"]["stencil"] = [
            Dict("selector" => Dict("kind" => "cartesian",
                                    "axis" => "\$x",
                                    "offset" => 0),
                 "coeff" => Dict("op" => "/", "args" => Any[-1, "dx"])),
            Dict("selector" => Dict("kind" => "cartesian",
                                    "axis" => "\$x",
                                    "offset" => 1),
                 "coeff" => Dict("op" => "/", "args" => Any[1, "dx"])),
        ]
        @test_throws MMSEvaluatorError verify_mms_convergence(
            broken_rule, centered_input, centered_expected)
    end

    @testset "mms_convergence — bare-spec form" begin
        # Accept the inner discretization spec without the wrapping
        # `discretizations` key.
        bare = centered_2nd_uniform_rule["discretizations"]["centered_2nd_uniform"]
        result = mms_convergence(bare, centered_input)
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
    end

    @testset "mms_convergence — error paths" begin
        # Missing accuracy
        no_accuracy = deepcopy(centered_2nd_uniform_rule)
        delete!(no_accuracy["discretizations"]["centered_2nd_uniform"], "accuracy")
        @test_throws MMSEvaluatorError mms_convergence(no_accuracy, centered_input)

        # Unknown discretization name
        bad_name_input = Base.merge(centered_input, Dict("rule" => "no_such_rule"))
        @test_throws MMSEvaluatorError mms_convergence(
            centered_2nd_uniform_rule, bad_name_input)

        # Unsupported sampling
        bad_sampling = Base.merge(centered_input, Dict("sampling" => "edge"))
        @test_throws MMSEvaluatorError mms_convergence(
            centered_2nd_uniform_rule, bad_sampling)

        # Single-grid sweep cannot produce a slope
        single_grid = Base.merge(centered_input, Dict("grids" => [Dict("n" => 32)]))
        @test_throws MMSEvaluatorError mms_convergence(
            centered_2nd_uniform_rule, single_grid)
    end

    @testset "eval_coeff — direct passthrough to evaluate" begin
        # Smoke test: matches ESD's `eval_coeff` semantics so a downstream
        # walker can swap to the ESS export with no behaviour change.
        node = Dict("op" => "/", "args" =>
            Any[-1, Dict("op" => "*", "args" => Any[2, "dx"])])
        @test eval_coeff(node, Dict("dx" => 0.25)) == -2.0
        @test eval_coeff(2.5, Dict("dx" => 0.1)) == 2.5
        @test eval_coeff("dx", Dict("dx" => 0.125)) == 0.125
        @test_throws EarthSciSerialization.UnboundVariableError eval_coeff(
            "h", Dict("dx" => 0.125))
    end
end
