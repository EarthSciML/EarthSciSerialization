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

    # ============================================================
    # MPAS-style unstructured MMS support (esm-0sy)
    # ============================================================

    @testset "make_periodic_quad_mesh — topology and metric" begin
        mesh = make_periodic_quad_mesh(4)
        @test mesh.nCells == 16
        @test mesh.nEdges == 32
        @test all(mesh.nEdgesOnCell .== 4)
        @test all(mesh.dcEdge .≈ 0.25)
        @test all(mesh.dvEdge .≈ 0.25)
        @test all(mesh.areaCell .≈ 0.0625)

        # Every cell sees each of its 4 edges; each edge is referenced twice.
        edge_visits = zeros(Int, mesh.nEdges)
        for c in 1:mesh.nCells, k in 1:mesh.nEdgesOnCell[c]
            edge_visits[mesh.edgesOnCell[c, k]] += 1
        end
        @test all(edge_visits .== 2)

        # cellsOnEdge agrees with edgesOnCell — for every (c, e) the cell c
        # appears in cellsOnEdge[e, :].
        for c in 1:mesh.nCells, k in 1:mesh.nEdgesOnCell[c]
            e = mesh.edgesOnCell[c, k]
            @test c == mesh.cellsOnEdge[e, 1] || c == mesh.cellsOnEdge[e, 2]
        end

        # Edge normals are unit-length axis-aligned.
        for e in 1:mesh.nEdges
            nrm = sqrt(mesh.edge_normals[e, 1]^2 + mesh.edge_normals[e, 2]^2)
            @test nrm ≈ 1.0
        end

        # Periodic wrap: cells in the leftmost column see east edges that
        # connect them to the rightmost column.
        n = 4
        c_left = 1
        e_w = mesh.edgesOnCell[c_left, 3]  # west edge of cell (1,1)
        @test mesh.cellsOnEdge[e_w, 1] == n        # cell (n,1) sits "before"
        @test mesh.cellsOnEdge[e_w, 2] == c_left
    end

    @testset "MPASCoeffContext — index op + scalar bindings" begin
        mesh = make_periodic_quad_mesh(4)
        ctx = EarthSciSerialization.MPASCoeffContext(
            Dict{String,Any}(
                "edgesOnCell" => mesh.edgesOnCell,
                "areaCell"    => mesh.areaCell,
                "dvEdge"      => mesh.dvEdge,
            ),
            Dict{String,Float64}("\$target" => 1.0, "k" => 2.0, "h" => 0.25),
        )
        # index(edgesOnCell, $target, k) == mesh.edgesOnCell[1, 2]
        idx_node = Dict("op" => "index", "args" =>
            Any["edgesOnCell", "\$target", "k"])
        @test EarthSciSerialization._eval_mpas_coeff_scalar(idx_node, ctx) ≈
              Float64(mesh.edgesOnCell[1, 2])
        # composed: dvEdge[edgesOnCell[$target,k]] / areaCell[$target]
        coeff = Dict("op" => "/", "args" => Any[
            Dict("op" => "index", "args" =>
                Any["dvEdge",
                    Dict("op" => "index", "args" =>
                        Any["edgesOnCell", "\$target", "k"])]),
            Dict("op" => "index", "args" => Any["areaCell", "\$target"]),
        ])
        c = 1; k = 2
        e_expect = mesh.edgesOnCell[c, k]
        @test EarthSciSerialization._eval_mpas_coeff_scalar(coeff, ctx) ≈
              mesh.dvEdge[e_expect] / mesh.areaCell[c]

        # Unknown scalar: clear error.
        bad = Dict("op" => "index", "args" => Any["dvEdge", "no_such_var"])
        @test_throws MMSEvaluatorError EarthSciSerialization._eval_mpas_coeff_scalar(
            bad, ctx)
        # Unknown array: clear error.
        bad2 = Dict("op" => "index", "args" => Any["no_such_array", "\$target"])
        @test_throws MMSEvaluatorError EarthSciSerialization._eval_mpas_coeff_scalar(
            bad2, ctx)
    end

    # MPAS cell-centered divergence stencil (matches tests/discretizations/
    # mpas_cell_div.esm). The coefficient walks edgesOnCell with the canonical
    # index ops; the per-cell sign comes from the MPAS C-grid staggering rule
    # (edge_normal_convention = outward_from_first_cell), applied by the
    # stencil engine, not the coefficient itself.
    mpas_cell_div_rule = Dict(
        "discretizations" => Dict(
            "mpas_cell_div" => Dict(
                "applies_to" => Dict("op" => "div", "args" => Any["\$F"], "dim" => "cell"),
                "grid_family" => "unstructured",
                "requires_locations" => Any["edge_normal"],
                "emits_location" => "cell_center",
                "combine" => "+",
                "accuracy" => "O(dx^2)",
                "stencil" => [
                    Dict(
                        "selector" => Dict(
                            "kind" => "reduction",
                            "table" => "edgesOnCell",
                            "count_expr" => Dict("op" => "index", "args" =>
                                Any["nEdgesOnCell", "\$target"]),
                            "k_bound" => "k",
                            "combine" => "+",
                        ),
                        "coeff" => Dict(
                            "op" => "/",
                            "args" => Any[
                                Dict("op" => "index", "args" => Any[
                                    "dvEdge",
                                    Dict("op" => "index", "args" =>
                                        Any["edgesOnCell", "\$target", "k"]),
                                ]),
                                Dict("op" => "index", "args" =>
                                    Any["areaCell", "\$target"]),
                            ],
                        ),
                    ),
                ],
            ),
        ),
    )
    mpas_cell_div_input = Dict(
        "rule" => "mpas_cell_div",
        "manufactured_solution" =>
            "vec=(sin(2*pi*x), 0); div=2*pi*cos(2*pi*x) on [0,1]^2 periodic",
        "sampling" => "cell_center",
        "grids" => [Dict("n" => 8), Dict("n" => 16),
                    Dict("n" => 32), Dict("n" => 64)],
        "topology" => "quad_periodic",
    )
    mpas_cell_div_expected = Dict(
        "rule" => "mpas_cell_div",
        "metric" => "Linf",
        "expected_min_order" => 1.9,
    )

    @testset "apply_mpas_cell_stencil — divergence theorem on uniform mesh" begin
        mesh = make_periodic_quad_mesh(32)
        ms = lookup_vector_manufactured_solution(
            "vec=(sin(2*pi*x), 0); div=2*pi*cos(2*pi*x)")
        F = sample_edge_normal_flux(mesh, ms)
        d_num = apply_mpas_cell_stencil(
            mpas_cell_div_rule["discretizations"]["mpas_cell_div"]["stencil"],
            F, mesh)
        d_exact = sample_cell_divergence(mesh, ms)
        # Second-order on n=32 should already have L∞ error well below 0.05.
        @test maximum(abs.(d_num .- d_exact)) < 0.05
    end

    @testset "mms_convergence_mpas — quad_periodic, mpas_cell_div" begin
        result = mms_convergence_mpas(mpas_cell_div_rule, mpas_cell_div_input)
        @test result.grids == [8, 16, 32, 64]
        @test length(result.errors) == 4
        @test all(result.errors .> 0)
        @test all(isfinite, result.errors)
        @test all(result.errors[i] > result.errors[i + 1] for i in 1:3)
        @test result.declared_order == 2.0
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
        @test result.orders[end] ≥ 1.9
    end

    @testset "verify_mms_convergence_mpas — passes the proven case" begin
        result = verify_mms_convergence_mpas(
            mpas_cell_div_rule, mpas_cell_div_input, mpas_cell_div_expected)
        @test result.observed_min_order ≥ mpas_cell_div_expected["expected_min_order"]
    end

    @testset "verify_mms_convergence_mpas — flags an order deficit" begin
        # Drop the dvEdge weighting → the stencil becomes a non-converging
        # average that does not approximate the divergence at all.
        broken = deepcopy(mpas_cell_div_rule)
        broken["discretizations"]["mpas_cell_div"]["stencil"][1]["coeff"] =
            Dict("op" => "/", "args" => Any[
                1.0,
                Dict("op" => "index", "args" => Any["areaCell", "\$target"]),
            ])
        @test_throws MMSEvaluatorError verify_mms_convergence_mpas(
            broken, mpas_cell_div_input, mpas_cell_div_expected)
    end

    @testset "register_vector_manufactured_solution!" begin
        custom = VectorManufacturedSolution(
            :_test_zero_field,
            (x, y) -> (0.0, 0.0),
            (x, y) -> 0.0,
            ((0.0, 1.0), (0.0, 1.0)),
            true,
        )
        register_vector_manufactured_solution!(custom)
        @test EarthSciSerialization._MMS_VECTOR_REGISTRY[:_test_zero_field] === custom
        delete!(EarthSciSerialization._MMS_VECTOR_REGISTRY, :_test_zero_field)
    end

    @testset "mms_convergence_mpas — error paths" begin
        # Missing accuracy
        no_accuracy = deepcopy(mpas_cell_div_rule)
        delete!(no_accuracy["discretizations"]["mpas_cell_div"], "accuracy")
        @test_throws MMSEvaluatorError mms_convergence_mpas(
            no_accuracy, mpas_cell_div_input)

        # Unknown rule name
        bad_name = Base.merge(mpas_cell_div_input, Dict("rule" => "no_such_rule"))
        @test_throws MMSEvaluatorError mms_convergence_mpas(
            mpas_cell_div_rule, bad_name)

        # Unsupported sampling
        bad_sampling = Base.merge(mpas_cell_div_input,
            Dict("sampling" => "edge"))
        @test_throws MMSEvaluatorError mms_convergence_mpas(
            mpas_cell_div_rule, bad_sampling)

        # Single-grid sweep cannot produce a slope
        single = Base.merge(mpas_cell_div_input, Dict("grids" => [Dict("n" => 32)]))
        @test_throws MMSEvaluatorError mms_convergence_mpas(
            mpas_cell_div_rule, single)

        # Unknown manufactured solution
        unknown_ms = Base.merge(mpas_cell_div_input,
            Dict("manufactured_solution" => "polynomial x^3"))
        @test_throws MMSEvaluatorError mms_convergence_mpas(
            mpas_cell_div_rule, unknown_ms)
    end

    @testset "lookup_vector_manufactured_solution" begin
        ms = lookup_vector_manufactured_solution(
            "vec=(sin(2*pi*x), 0); div=2*pi*cos(2*pi*x)")
        @test ms.name === :vec_sin_2pi_x_periodic
        @test ms.periodic
        @test ms.domain == ((0.0, 1.0), (0.0, 1.0))
        u, v = ms.velocity(0.25, 0.5)
        @test isapprox(u, 1.0; atol=1e-12)
        @test v == 0.0
        @test isapprox(ms.divergence(0.0, 0.0), 2π; atol=1e-12)
        @test_throws MMSEvaluatorError lookup_vector_manufactured_solution(
            "polynomial x^3")
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
