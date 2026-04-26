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

    # ====================================================================
    # PPM reconstruction-style extensions (esm-k1d):
    #   sub-stencil targeting, output-kind selector, parabola pass.
    # ====================================================================

    # Centered linear edge interpolation: u_{i+1/2} ≈ ½(u_i + u_{i+1}),
    # u_{i-1/2} ≈ ½(u_{i-1} + u_i). Stored as a multi-stencil mapping so the
    # rule emits two outputs (left edge, right edge) under one accuracy claim.
    half = Dict("op" => "/", "args" => Any[1, 2])
    edge2_rule = Dict(
        "discretizations" => Dict(
            "centered_edge_linear" => Dict(
                "applies_to" => Dict("op" => "interp", "args" => Any["\$u"]),
                "grid_family" => "cartesian",
                "accuracy" => "O(dx^2)",
                "stencil" => Dict(
                    "u_L" => [
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => -1),
                             "coeff" => half),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 0),
                             "coeff" => half),
                    ],
                    "u_R" => [
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 0),
                             "coeff" => half),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 1),
                             "coeff" => half),
                    ],
                ),
            ),
        ),
    )
    edge_grids_input = Dict(
        "rule" => "centered_edge_linear",
        "manufactured_solution" =>
            "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)",
        "sampling" => "cell_center",
        "grids" => [Dict("n" => 16), Dict("n" => 32),
                    Dict("n" => 64), Dict("n" => 128)],
    )

    @testset "apply_stencil_periodic_1d — sub-stencil targeting" begin
        spec = edge2_rule["discretizations"]["centered_edge_linear"]
        n = 64
        dx = 1.0 / n
        u = [sin(2π * (i - 0.5) * dx) for i in 1:n]
        bindings = Dict("dx" => dx)

        u_L = apply_stencil_periodic_1d(spec["stencil"], u, bindings;
                                        sub_stencil="u_L")
        u_R = apply_stencil_periodic_1d(spec["stencil"], u, bindings;
                                        sub_stencil="u_R")
        # Right edge of cell i and left edge of cell i+1 must agree exactly.
        @test all(isapprox.(u_R[1:end-1], u_L[2:end]; atol=1e-14))
        @test isapprox(u_R[end], u_L[1]; atol=1e-14)  # periodic wrap

        # Bare-list form rejects an unsolicited sub_stencil arg.
        bare = [Dict("selector" => Dict("kind" => "cartesian",
                                        "axis" => "x", "offset" => 0),
                     "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_periodic_1d(
            bare, u, bindings; sub_stencil="anything")

        # Mapping form requires a sub_stencil selection.
        @test_throws MMSEvaluatorError apply_stencil_periodic_1d(
            spec["stencil"], u, bindings)

        # Unknown sub-stencil name throws.
        @test_throws MMSEvaluatorError apply_stencil_periodic_1d(
            spec["stencil"], u, bindings; sub_stencil="u_X")
    end

    @testset "mms_convergence — output_kind=value_at_edge_right" begin
        input = Base.merge(edge_grids_input, Dict(
            "sub_stencil" => "u_R",
            "output_kind" => "value_at_edge_right",
        ))
        result = mms_convergence(edge2_rule, input)
        @test result.declared_order == 2.0
        @test result.observed_min_order ≥ 1.9
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
    end

    @testset "mms_convergence — output_kind=value_at_edge_left" begin
        input = Base.merge(edge_grids_input, Dict(
            "sub_stencil" => "u_L",
            "output_kind" => "value_at_edge_left",
        ))
        result = mms_convergence(edge2_rule, input)
        @test result.observed_min_order ≥ 1.9
    end

    @testset "mms_convergence — unknown output_kind rejected" begin
        bad = Base.merge(edge_grids_input, Dict(
            "sub_stencil" => "u_R",
            "output_kind" => "value_at_face",
        ))
        @test_throws MMSEvaluatorError mms_convergence(edge2_rule, bad)
    end

    # PPM unlimited 4th-order edge value (Colella & Woodward 1984, eq. 1.6):
    #   u_{i+1/2} = (7/12)(u_i + u_{i+1}) − (1/12)(u_{i-1} + u_{i+2}).
    # u_L for cell i = u_{i-1/2} (shift the coefficients one cell left).
    seven_twelfths = Dict("op" => "/", "args" => Any[7, 12])
    minus_one_twelfth = Dict("op" => "/", "args" => Any[-1, 12])
    ppm_rule = Dict(
        "discretizations" => Dict(
            "ppm_unlimited" => Dict(
                "applies_to" => Dict("op" => "interp", "args" => Any["\$u"]),
                "grid_family" => "cartesian",
                "accuracy" => "O(dx^3)",
                "stencil" => Dict(
                    "u_L" => [
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => -2),
                             "coeff" => minus_one_twelfth),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => -1),
                             "coeff" => seven_twelfths),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 0),
                             "coeff" => seven_twelfths),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 1),
                             "coeff" => minus_one_twelfth),
                    ],
                    "u_R" => [
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => -1),
                             "coeff" => minus_one_twelfth),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 0),
                             "coeff" => seven_twelfths),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 1),
                             "coeff" => seven_twelfths),
                        Dict("selector" => Dict("kind" => "cartesian",
                                                "axis" => "\$x", "offset" => 2),
                             "coeff" => minus_one_twelfth),
                    ],
                ),
            ),
        ),
    )

    @testset "parabola_reconstruct_periodic_1d — round-trip in one cell" begin
        # Sanity: when u_L = u_R = ū, the parabola is constant ≡ ū.
        stencils = Dict(
            "u_L" => [Dict("selector" => Dict("offset" => 0), "coeff" => 1.0)],
            "u_R" => [Dict("selector" => Dict("offset" => 0), "coeff" => 1.0)],
        )
        u_bar = [3.0, 3.0, 3.0, 3.0]
        bindings = Dict("dx" => 0.25, "domain_lo" => 0.0)
        xs, vals = parabola_reconstruct_periodic_1d(
            stencils, u_bar, bindings;
            left_edge_stencil="u_L", right_edge_stencil="u_R",
            subcell_points=[0.1, 0.5, 0.9])
        @test all(isapprox.(vals, 3.0; atol=1e-14))
        @test length(xs) == length(u_bar) * 3
    end

    @testset "parabola_reconstruct_periodic_1d — input validation" begin
        bindings_full = Dict("dx" => 0.25, "domain_lo" => 0.0)
        bindings_no_dx = Dict("domain_lo" => 0.0)
        bindings_no_lo = Dict("dx" => 0.25)
        spec = Dict(
            "u_L" => [Dict("selector" => Dict("offset" => 0), "coeff" => 1.0)],
            "u_R" => [Dict("selector" => Dict("offset" => 0), "coeff" => 1.0)],
        )
        u = [1.0, 2.0]

        @test_throws MMSEvaluatorError parabola_reconstruct_periodic_1d(
            [1, 2, 3], u, bindings_full;
            left_edge_stencil="u_L", right_edge_stencil="u_R",
            subcell_points=[0.5])

        @test_throws MMSEvaluatorError parabola_reconstruct_periodic_1d(
            spec, u, bindings_no_dx;
            left_edge_stencil="u_L", right_edge_stencil="u_R",
            subcell_points=[0.5])

        @test_throws MMSEvaluatorError parabola_reconstruct_periodic_1d(
            spec, u, bindings_no_lo;
            left_edge_stencil="u_L", right_edge_stencil="u_R",
            subcell_points=[0.5])

        @test_throws MMSEvaluatorError parabola_reconstruct_periodic_1d(
            spec, u, bindings_full;
            left_edge_stencil="u_L", right_edge_stencil="u_R",
            subcell_points=[1.5])
    end

    @testset "mms_convergence — PPM parabola pass on cell averages" begin
        # PPM with the unlimited 4th-order edge formula on cell-averaged input
        # achieves third-order pointwise convergence inside the cell. We use
        # the analytic cell average (sin(2π x) integrated over [a,b]) to avoid
        # leaking quadrature error into the order estimate.
        input = Dict(
            "rule" => "ppm_unlimited",
            "manufactured_solution" =>
                "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)",
            "sampling" => "cell_average",
            "grids" => [Dict("n" => 16), Dict("n" => 32),
                        Dict("n" => 64), Dict("n" => 128)],
            "reconstruction" => Dict(
                "kind" => "parabola",
                "left_edge_stencil" => "u_L",
                "right_edge_stencil" => "u_R",
                "subcell_points" => [0.1, 0.3, 0.5, 0.7, 0.9],
            ),
        )
        result = mms_convergence(ppm_rule, input)
        @test all(result.errors .> 0)
        @test all(result.errors[i] > result.errors[i+1] for i in 1:3)
        @test result.observed_min_order ≥ 2.8  # 3rd-order with margin
        @test result.declared_order == 3.0
    end

    @testset "verify_mms_convergence — PPM parabola pass passes its threshold" begin
        input = Dict(
            "rule" => "ppm_unlimited",
            "manufactured_solution" =>
                "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)",
            "sampling" => "cell_average",
            "grids" => [Dict("n" => 16), Dict("n" => 32),
                        Dict("n" => 64), Dict("n" => 128)],
            "reconstruction" => Dict(
                "kind" => "parabola",
                "left_edge_stencil" => "u_L",
                "right_edge_stencil" => "u_R",
                "subcell_points" => [0.1, 0.3, 0.5, 0.7, 0.9],
            ),
        )
        expected = Dict(
            "rule" => "ppm_unlimited",
            "metric" => "Linf",
            "expected_min_order" => 2.8,
        )
        result = verify_mms_convergence(ppm_rule, input, expected)
        @test result.observed_min_order ≥ 2.8
    end

    @testset "mms_convergence — bad reconstruction rejected" begin
        for missing_field in ("left_edge_stencil",
                              "right_edge_stencil",
                              "subcell_points")
            recon = Dict("kind" => "parabola",
                         "left_edge_stencil" => "u_L",
                         "right_edge_stencil" => "u_R",
                         "subcell_points" => [0.5])
            delete!(recon, missing_field)
            input = Dict(
                "rule" => "ppm_unlimited",
                "manufactured_solution" =>
                    "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)",
                "sampling" => "cell_average",
                "grids" => [Dict("n" => 16), Dict("n" => 32)],
                "reconstruction" => recon,
            )
            @test_throws MMSEvaluatorError mms_convergence(ppm_rule, input)
        end

        # Unknown reconstruction kind.
        input_bad_kind = Dict(
            "rule" => "ppm_unlimited",
            "manufactured_solution" =>
                "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)",
            "sampling" => "cell_average",
            "grids" => [Dict("n" => 16), Dict("n" => 32)],
            "reconstruction" => Dict(
                "kind" => "bezier",
                "left_edge_stencil" => "u_L",
                "right_edge_stencil" => "u_R",
                "subcell_points" => [0.5],
            ),
        )
        @test_throws MMSEvaluatorError mms_convergence(ppm_rule, input_bad_kind)
    end

    @testset "mms_convergence — sampling=cell_average works on existing rule" begin
        # Centered 2nd-order FD against analytic cell averages: still O(dx^2).
        input = Base.merge(centered_input, Dict("sampling" => "cell_average"))
        result = mms_convergence(centered_2nd_uniform_rule, input)
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
    end

    @testset "ManufacturedSolution — cell_average fallback uses GL quadrature" begin
        # Without an analytic cell_average, the harness falls back to a 5-point
        # Gauss–Legendre quadrature; for sin(2π x) this is exact-enough that the
        # resulting average matches the analytic value to >1e-9.
        analytic = lookup_manufactured_solution(
            "sin(2*pi*x) on [0,1] periodic; derivative 2*pi*cos(2*pi*x)")
        no_avg = ManufacturedSolution(
            :_test_no_avg, analytic.sample, analytic.derivative, true, (0.0, 1.0))
        for (lo, hi) in ((0.0, 0.0625), (0.25, 0.5), (0.875, 1.0))
            ref = analytic.cell_average(lo, hi)
            est = EarthSciSerialization._cell_average(no_avg, lo, hi)
            @test isapprox(est, ref; atol=1e-9)
        end
    end
end
