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

    # ============================================================
    # 2D structured + per-cell metric bindings (esm-5ur)
    # ============================================================

    @testset "CellBindings — bindings_at materializes per-cell dict" begin
        cb = CellBindings(
            Dict{String,Float64}("R" => 6.371e6, "dlon" => 0.1, "dlat" => 0.05),
            Dict{String,Function}(
                "cos_lat" => (i, j) -> cos(0.1 * j),
                "lat"     => (i, j) -> 0.1 * j,
            ),
        )
        b = bindings_at(cb, 3, 7)
        @test b["R"] == 6.371e6
        @test b["dlon"] == 0.1
        @test isapprox(b["cos_lat"], cos(0.7); atol=1e-12)
        @test isapprox(b["lat"], 0.7; atol=1e-12)
        # Per-cell entries override scalars with the same name.
        cb2 = CellBindings(
            Dict{String,Float64}("x" => 1.0),
            Dict{String,Function}("x" => (i, j) -> 2.0),
        )
        @test bindings_at(cb2, 0, 0)["x"] == 2.0
    end

    @testset "lookup_manufactured_solution_2d — Y_{2,0}" begin
        ms2 = lookup_manufactured_solution_2d(
            "Y_{2,0} spherical harmonic on the unit sphere")
        @test ms2.name === :Y_2_0_sphere
        @test ms2.domain_lon == (0.0, 2π)
        @test ms2.domain_lat == (-π / 2, π / 2)
        # Lon-independent: gradient_combo at (lon, lat, R) doesn't depend on lon.
        v1 = ms2.derivative_combo(0.0, 0.3, 1.0)
        v2 = ms2.derivative_combo(1.7, 0.3, 1.0)
        @test isapprox(v1, v2; atol=1e-12)
        # At equator (lat=0): ∂_lat Y_{2,0} = 0 ⇒ combined = 0.
        @test isapprox(ms2.derivative_combo(0.0, 0.0, 1.0), 0.0; atol=1e-12)
        @test_throws MMSEvaluatorError lookup_manufactured_solution_2d(
            "polynomial blob")
    end

    # The latlon rule lives in EarthSciDiscretizations
    # (`discretizations/finite_difference/centered_2nd_uniform_latlon.json`).
    # Embed the equivalent dict here so the ESS test suite is self-contained.
    centered_2nd_latlon_rule = Dict(
        "discretizations" => Dict(
            "centered_2nd_uniform_latlon" => Dict(
                "applies_to" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$k"),
                "grid_family" => "latlon",
                "combine" => "+",
                "accuracy" => "O(h^2)",
                "stencil" => [
                    Dict("selector" => Dict("kind" => "latlon",
                                            "axis" => "lon", "offset" => -1),
                         "coeff" => Dict("op" => "/", "args" => Any[
                             -1, Dict("op" => "*", "args" =>
                                 Any[2, "R", "cos_lat", "dlon"])])),
                    Dict("selector" => Dict("kind" => "latlon",
                                            "axis" => "lon", "offset" => 1),
                         "coeff" => Dict("op" => "/", "args" => Any[
                             1, Dict("op" => "*", "args" =>
                                 Any[2, "R", "cos_lat", "dlon"])])),
                    Dict("selector" => Dict("kind" => "latlon",
                                            "axis" => "lat", "offset" => -1),
                         "coeff" => Dict("op" => "/", "args" => Any[
                             -1, Dict("op" => "*", "args" => Any[2, "R", "dlat"])])),
                    Dict("selector" => Dict("kind" => "latlon",
                                            "axis" => "lat", "offset" => 1),
                         "coeff" => Dict("op" => "/", "args" => Any[
                             1, Dict("op" => "*", "args" => Any[2, "R", "dlat"])])),
                ],
            ),
        ),
    )
    latlon_input = Dict(
        "rule" => "centered_2nd_uniform_latlon",
        "manufactured_solution" =>
            "Y_{2,0} spherical harmonic on the unit sphere; " *
            "globally smooth, lon-independent",
        "sampling" => "cell_center",
        "radius" => 1.0,
        "grids" => [Dict("n" => 16), Dict("n" => 32),
                    Dict("n" => 64), Dict("n" => 128)],
    )
    latlon_expected = Dict(
        "rule" => "centered_2nd_uniform_latlon",
        "metric" => "Linf",
        "expected_min_order" => 1.9,
    )

    @testset "apply_stencil_2d_latlon — interior mask + per-cell cos_lat" begin
        # Build a tiny 4×3 lat-lon stencil application by hand and check that
        # interior excludes lat boundaries and that cos_lat is read per-cell.
        nlon, nlat = 4, 3
        stencil = centered_2nd_latlon_rule["discretizations"]["centered_2nd_uniform_latlon"]["stencil"]
        u = ones(Float64, nlon, nlat)        # constant field — derivative is 0
        dlon = 2π / nlon
        dlat = π / nlat
        lat_centers = [-π / 2 + (j - 0.5) * dlat for j in 1:nlat]
        cb = CellBindings(
            Dict{String,Float64}("R" => 1.0, "dlon" => dlon, "dlat" => dlat),
            Dict{String,Function}(
                "cos_lat" => (i, j) -> cos(lat_centers[j]),
            ),
        )
        out, interior = apply_stencil_2d_latlon(stencil, u, cb)
        # Interior is only the middle lat row (j=2); j=1 and j=3 are excluded.
        @test interior[1, 2] && interior[2, 2] && interior[3, 2] && interior[4, 2]
        @test !interior[1, 1] && !interior[1, 3]
        # On a constant field, the interior result is exactly zero.
        @test all(out[interior] .== 0.0)
        # Boundary cells were skipped (default zero in the output).
        @test all(out[.!interior] .== 0.0)
    end

    @testset "apply_stencil_2d_latlon — rejects mixed/wrong selector kinds" begin
        bad_kind = [
            Dict("selector" => Dict("kind" => "cartesian",
                                    "axis" => "x", "offset" => 1),
                 "coeff" => 1.0),
        ]
        u = zeros(Float64, 2, 2)
        cb = CellBindings(Dict{String,Float64}())
        @test_throws MMSEvaluatorError apply_stencil_2d_latlon(bad_kind, u, cb)

        bad_axis = [
            Dict("selector" => Dict("kind" => "latlon",
                                    "axis" => "z", "offset" => 1),
                 "coeff" => 1.0),
        ]
        @test_throws MMSEvaluatorError apply_stencil_2d_latlon(bad_axis, u, cb)
    end

    @testset "mms_convergence — centered_2nd_uniform_latlon (Y_{2,0})" begin
        result = mms_convergence(centered_2nd_latlon_rule, latlon_input)
        @test length(result.errors) == 4
        @test all(isfinite, result.errors)
        @test all(result.errors .> 0)
        # 2nd-order convergence on the lat axis.
        @test result.declared_order == 2.0
        @test all(result.errors[i] > result.errors[i + 1] for i in 1:3)
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
        @test result.orders[end] ≥ 1.9
    end

    @testset "verify_mms_convergence — passes on Y_{2,0} latlon" begin
        result = verify_mms_convergence(
            centered_2nd_latlon_rule, latlon_input, latlon_expected)
        @test result.observed_min_order ≥ latlon_expected["expected_min_order"]
    end

    @testset "mms_convergence — latlon error paths" begin
        # nlon/nlat explicit form is accepted alongside `n`.
        explicit = Base.merge(latlon_input, Dict(
            "grids" => [Dict("nlon" => 32, "nlat" => 16),
                        Dict("nlon" => 64, "nlat" => 32),
                        Dict("nlon" => 128, "nlat" => 64)]))
        result = mms_convergence(centered_2nd_latlon_rule, explicit)
        @test result.observed_min_order ≥ 1.9

        # Mixed selector kinds in a single stencil are rejected.
        mixed_stencil = Any[]
        for s in centered_2nd_latlon_rule["discretizations"]["centered_2nd_uniform_latlon"]["stencil"]
            push!(mixed_stencil, deepcopy(s))
        end
        push!(mixed_stencil,
              Dict{String,Any}("selector" => Dict{String,Any}(
                                   "kind" => "cartesian",
                                   "axis" => "x", "offset" => 0),
                               "coeff" => 0.0))
        mixed = Dict("discretizations" => Dict(
            "centered_2nd_uniform_latlon" => Base.merge(
                centered_2nd_latlon_rule["discretizations"]["centered_2nd_uniform_latlon"],
                Dict("stencil" => mixed_stencil))))
        @test_throws MMSEvaluatorError mms_convergence(mixed, latlon_input)

        # Negative radius is rejected.
        bad_R = Base.merge(latlon_input, Dict("radius" => -1.0))
        @test_throws MMSEvaluatorError mms_convergence(
            centered_2nd_latlon_rule, bad_R)

        # Grid entry missing both `n` and `nlon`/`nlat` is rejected.
        bad_grid = Base.merge(latlon_input, Dict("grids" => [Dict("foo" => 1),
                                                              Dict("foo" => 2)]))
        @test_throws MMSEvaluatorError mms_convergence(
            centered_2nd_latlon_rule, bad_grid)

        # 1D solution on a 2D rule is a type error.
        @test_throws MMSEvaluatorError mms_convergence(
            centered_2nd_latlon_rule, latlon_input;
            manufactured=lookup_manufactured_solution(
                "sin(2*pi*x) on [0,1] periodic"))
    end

    @testset "register_manufactured_solution! — 2D path" begin
        # 2D MMS exercising the registry path without hitting machine zero.
        # u(lon, lat) = lat^3: ∂_lon = 0, ∂_lat = 3 lat^2; centered 2nd FD on
        # a cubic carries a known O(dlat^2) truncation term (= dlat^2 / R).
        custom = ManufacturedSolution2D(
            :_test_lat_cubic,
            (lon, lat) -> lat^3,
            (lon, lat, R) -> 3 * lat^2 / R,
            (0.0, 2π),
            (-1.0, 1.0),  # avoid lat = ±π/2 (cos = 0 in lon coeff)
        )
        register_manufactured_solution!(custom)
        @test EarthSciSerialization._MMS_REGISTRY_2D[:_test_lat_cubic] === custom
        result = mms_convergence(
            centered_2nd_latlon_rule, latlon_input; manufactured=custom)
        # Pure 2nd-order convergence on a cubic.
        @test result.observed_min_order ≥ 1.95
        delete!(EarthSciSerialization._MMS_REGISTRY_2D, :_test_lat_cubic)
    end

    # Inline WENO5 rule spec. Mirrors the on-disk
    # `discretizations/finite_volume/weno5_advection.json` shape so the ESS
    # test suite is self-contained — the §7 stencil schema cannot yet express
    # the nonlinear-weight ratio form, so the kernel applies it in-code (see
    # mms_evaluator.jl `apply_weno5_reconstruction_periodic_1d`).
    function _weno5_substencil(offsets, coeffs)
        [Dict("selector" => Dict("kind" => "cartesian", "axis" => "\$x",
                                 "offset" => off),
              "coeff" => Dict("op" => "/", "args" => Any[num, den]))
         for (off, (num, den)) in zip(offsets, coeffs)]
    end
    weno5_rule = Dict(
        "discretizations" => Dict(
            "weno5_advection" => Dict(
                "applies_to" => Dict("op" => "reconstruct", "args" => Any["\$q"],
                                     "dim" => "\$x"),
                "form" => "weighted_essentially_nonoscillatory",
                "grid_family" => "cartesian",
                "accuracy" => "O(dx^5)",
                "reconstruction_left_biased" => Dict(
                    "candidates" => [
                        Dict("stencil" => _weno5_substencil(
                            [-2, -1, 0], [(1, 3), (-7, 6), (11, 6)])),
                        Dict("stencil" => _weno5_substencil(
                            [-1, 0, 1],  [(-1, 6), (5, 6), (1, 3)])),
                        Dict("stencil" => _weno5_substencil(
                            [0, 1, 2],   [(1, 3), (5, 6), (-1, 6)])),
                    ],
                    "linear_weights" => Dict(
                        "d0" => Dict("op" => "/", "args" => Any[1, 10]),
                        "d1" => Dict("op" => "/", "args" => Any[6, 10]),
                        "d2" => Dict("op" => "/", "args" => Any[3, 10]),
                    ),
                ),
                "reconstruction_right_biased" => Dict(
                    "candidates" => [
                        Dict("stencil" => _weno5_substencil(
                            [2, 1, 0],   [(1, 3), (-7, 6), (11, 6)])),
                        Dict("stencil" => _weno5_substencil(
                            [1, 0, -1],  [(-1, 6), (5, 6), (1, 3)])),
                        Dict("stencil" => _weno5_substencil(
                            [0, -1, -2], [(1, 3), (5, 6), (-1, 6)])),
                    ],
                    "linear_weights" => Dict(
                        "d0" => Dict("op" => "/", "args" => Any[1, 10]),
                        "d1" => Dict("op" => "/", "args" => Any[6, 10]),
                        "d2" => Dict("op" => "/", "args" => Any[3, 10]),
                    ),
                ),
            ),
        ),
    )
    weno5_input = Dict(
        "rule" => "weno5_advection",
        "manufactured_solution" => Dict("name" => "phase_shifted_sine"),
        "reconstruction" => "left_biased",
        "weno_epsilon" => 1.0e-6,
        "grids" => [Dict("n" => 32), Dict("n" => 64),
                    Dict("n" => 128), Dict("n" => 256)],
    )

    @testset "lookup_manufactured_solution — dict + phase-shifted sine" begin
        ms = lookup_manufactured_solution(Dict("name" => "phase_shifted_sine"))
        @test ms.name === :phase_shifted_sine
        @test ms.cell_average !== nothing
        @test ms.edge_value !== nothing
        # Cell average over a full period of sin(2πx + 1) is zero.
        @test isapprox(ms.cell_average(0.0, 1.0), 0.0; atol=1e-12)
        # Half-period analytic check.
        @test isapprox(ms.cell_average(0.0, 0.5),
                       (-cos(π + 1.0) + cos(1.0)) / π; atol=1e-12)
        @test isapprox(ms.edge_value(0.25), sin(π/2 + 1.0); atol=1e-12)

        # String fallback via expression key.
        ms2 = lookup_manufactured_solution(
            Dict("expression" => "sin(2*pi*x+1) on [0,1] periodic"))
        @test ms2.name === :phase_shifted_sine

        # Unknown dict descriptor surfaces E_MMS_UNKNOWN_SOLUTION.
        @test_throws MMSEvaluatorError lookup_manufactured_solution(
            Dict("name" => "no_such_solution"))
    end

    @testset "apply_weno5_reconstruction_periodic_1d — smooth convergence" begin
        spec = weno5_rule["discretizations"]["weno5_advection"]
        ms = lookup_manufactured_solution(Dict("name" => "phase_shifted_sine"))
        # Smooth-MMS convergence: the L∞ error of WENO5 against the analytic
        # face value must contract at order ≥ 4.5 between successive halvings
        # on n ∈ {64, 128, 256} (Henrick-Aslam-Powers result; canonical 5).
        function err_at(n)
            dx = 1.0 / n
            q = [ms.cell_average((i - 1) * dx, i * dx) for i in 1:n]
            qhat = apply_weno5_reconstruction_periodic_1d(spec, q, :left_biased)
            face = [ms.edge_value(i * dx) for i in 1:n]
            return maximum(abs.(qhat .- face))
        end
        e64  = err_at(64)
        e128 = err_at(128)
        e256 = err_at(256)
        @test e64 > e128 > e256
        @test log2(e64  / e128) ≥ 4.5
        @test log2(e128 / e256) ≥ 4.5
    end

    @testset "mms_weno5_convergence — left-biased smooth sweep" begin
        result = mms_weno5_convergence(weno5_rule, weno5_input)
        @test result.declared_order == 5.0
        @test result.grids == [32, 64, 128, 256]
        @test all(result.errors .> 0)
        @test all(isfinite, result.errors)
        # All consecutive doublings must hit ≥ 4.5; final pair tightens to ~5.
        @test all(o -> o ≥ 4.5, result.orders)
        @test result.orders[end] ≥ 4.8
        @test result.observed_min_order ≥ 4.5
    end

    @testset "mms_weno5_convergence — right-biased symmetric" begin
        right = Base.merge(weno5_input, Dict("reconstruction" => "right_biased"))
        result = mms_weno5_convergence(weno5_rule, right)
        @test result.observed_min_order ≥ 4.5
        @test result.orders[end] ≥ 4.8
    end

    @testset "mms_convergence — dispatches to WENO5 on `form` field" begin
        # Top-level `mms_convergence` must transparently route nonlinear
        # reconstruction rules (form == weighted_essentially_nonoscillatory)
        # through the WENO5 path. Same fixture, different entry point.
        result = mms_convergence(weno5_rule, weno5_input)
        @test result.declared_order == 5.0
        @test result.observed_min_order ≥ 4.5
    end

    @testset "mms_weno5_convergence — error paths" begin
        # WENO5 sweep rejects a manufactured solution without cell_average.
        bad_input = Base.merge(weno5_input, Dict(
            "manufactured_solution" => Dict("name" => "sin_2pi_x_periodic")))
        @test_throws MMSEvaluatorError mms_weno5_convergence(weno5_rule, bad_input)

        # Bad reconstruction side string.
        bad_side = Base.merge(weno5_input, Dict("reconstruction" => "centered"))
        @test_throws MMSEvaluatorError mms_weno5_convergence(weno5_rule, bad_side)

        # Bad reconstruction side passed directly to the kernel.
        @test_throws MMSEvaluatorError apply_weno5_reconstruction_periodic_1d(
            weno5_rule["discretizations"]["weno5_advection"],
            zeros(Float64, 32), :centered)

        # WENO5 convergence rejects a non-WENO rule.
        @test_throws MMSEvaluatorError mms_weno5_convergence(
            centered_2nd_uniform_rule,
            Base.merge(centered_input,
                       Dict("manufactured_solution" =>
                                Dict("name" => "phase_shifted_sine"))))
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
