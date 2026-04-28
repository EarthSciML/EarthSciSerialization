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

    # ====================================================================
    # 2D axis-split WENO5 (esm-hsa). Shares the 1D substencil shapes,
    # nested under `axes.x` / `axes.y` so the rule covers both directions.
    # ====================================================================
    weno5_2d_rule = Dict(
        "discretizations" => Dict(
            "weno5_advection_2d" => Dict(
                "applies_to" => Dict("op" => "reconstruct", "args" => Any["\$q"]),
                "form" => "weighted_essentially_nonoscillatory",
                "grid_family" => "cartesian",
                "accuracy" => "O(dx^5)",
                "axes" => Dict(
                    "x" => Dict(
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
                    "y" => Dict(
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
            ),
        ),
    )
    weno5_2d_input_x = Dict(
        "rule" => "weno5_advection_2d",
        "manufactured_solution" => Dict("name" => "phase_shifted_sine_product_2d"),
        "axis" => "x",
        "reconstruction" => "left_biased",
        "weno_epsilon" => 1.0e-6,
        "grids" => [Dict("n" => 32), Dict("n" => 64),
                    Dict("n" => 128), Dict("n" => 256)],
    )

    @testset "lookup_manufactured_solution_2d_reconstruction — built-in" begin
        ms = lookup_manufactured_solution_2d_reconstruction(
            Dict("name" => "phase_shifted_sine_product_2d"))
        @test ms isa ReconstructionManufacturedSolution2D
        @test ms.name === :phase_shifted_sine_product_2d
        # Cell average over [0,1]^2 of sin(2πx+1) sin(2πy+1) is the product
        # of the 1D averages, both zero over a full period.
        @test isapprox(ms.cell_average(0.0, 1.0, 0.0, 1.0), 0.0; atol=1e-12)
        # Face-x average at xf = 0.25 over a full y period: sin(2π·0.25 + 1) · 0.
        @test isapprox(ms.face_average_x(0.25, 0.0, 1.0), 0.0; atol=1e-12)
        # String-fallback alias.
        @test lookup_manufactured_solution_2d_reconstruction(
            "phase shifted sine product 2D").name === :phase_shifted_sine_product_2d
        @test_throws MMSEvaluatorError lookup_manufactured_solution_2d_reconstruction(
            Dict("name" => "no_such_solution"))
    end

    @testset "mms_weno5_convergence — 2D axis=x left-biased" begin
        result = mms_weno5_convergence(weno5_2d_rule, weno5_2d_input_x)
        @test result.declared_order == 5.0
        @test result.grids == [32, 64, 128, 256]
        @test all(result.errors .> 0)
        @test all(isfinite, result.errors)
        # Acceptance #3 of dsc-5od: observed_min_order ≥ 4.4.
        @test result.observed_min_order ≥ 4.4
        @test result.orders[end] ≥ 4.5
    end

    @testset "mms_weno5_convergence — 2D axis=y right-biased" begin
        input_y = Base.merge(weno5_2d_input_x,
            Dict("axis" => "y", "reconstruction" => "right_biased"))
        result = mms_weno5_convergence(weno5_2d_rule, input_y)
        @test result.observed_min_order ≥ 4.4
        @test result.orders[end] ≥ 4.5
    end

    @testset "mms_weno5_convergence — 2D dispatches via mms_convergence" begin
        # The top-level dispatcher must route 2D WENO5 to the same path
        # without a manual call to mms_weno5_convergence.
        result = mms_convergence(weno5_2d_rule, weno5_2d_input_x)
        @test result.declared_order == 5.0
        @test result.observed_min_order ≥ 4.4
    end

    @testset "mms_weno5_convergence — 2D rectangular grids (nx ≠ ny)" begin
        rect_input = Base.merge(weno5_2d_input_x, Dict(
            "grids" => [Dict("nx" => 32, "ny" => 64),
                        Dict("nx" => 64, "ny" => 128),
                        Dict("nx" => 128, "ny" => 256),
                        Dict("nx" => 256, "ny" => 512)],
        ))
        result = mms_weno5_convergence(weno5_2d_rule, rect_input)
        # axis = "x", so the convergence sequence is indexed by nx.
        @test result.grids == [32, 64, 128, 256]
        @test result.observed_min_order ≥ 4.4
    end

    @testset "mms_weno5_convergence — 2D error paths" begin
        # Bad axis selector.
        bad_axis = Base.merge(weno5_2d_input_x, Dict("axis" => "z"))
        @test_throws MMSEvaluatorError mms_weno5_convergence(weno5_2d_rule, bad_axis)

        # Spec axes block missing the requested axis.
        no_y_rule = deepcopy(weno5_2d_rule)
        delete!(no_y_rule["discretizations"]["weno5_advection_2d"]["axes"], "y")
        @test_throws MMSEvaluatorError mms_weno5_convergence(
            no_y_rule, Base.merge(weno5_2d_input_x, Dict("axis" => "y")))

        # Wrong manufactured-solution type passed via kwarg (1D into 2D).
        ms_1d = lookup_manufactured_solution(Dict("name" => "phase_shifted_sine"))
        @test_throws MMSEvaluatorError mms_weno5_convergence(
            weno5_2d_rule, weno5_2d_input_x; manufactured=ms_1d)

        # Wrong manufactured-solution type passed via kwarg (2D into 1D).
        ms_2d = lookup_manufactured_solution_2d_reconstruction(
            Dict("name" => "phase_shifted_sine_product_2d"))
        @test_throws MMSEvaluatorError mms_weno5_convergence(
            weno5_rule, weno5_input; manufactured=ms_2d)

        # Bad grid entry (neither n nor nx/ny).
        bad_grids = Base.merge(weno5_2d_input_x,
            Dict("grids" => [Dict("foo" => 32), Dict("foo" => 64)]))
        @test_throws MMSEvaluatorError mms_weno5_convergence(weno5_2d_rule, bad_grids)
    end

    @testset "register_manufactured_solution! — 2D reconstruction overload" begin
        # Smoke-test the registry overload: register a synthetic 2D MMS,
        # look it up, then unregister to keep the global registry clean.
        zero_field = ReconstructionManufacturedSolution2D(
            :_test_zero_2d,
            (x, y) -> 0.0,
            (xlo, xhi, ylo, yhi) -> 0.0,
            (xf, ylo, yhi) -> 0.0,
            (xlo, xhi, yf) -> 0.0,
            ((0.0, 1.0), (0.0, 1.0)),
        )
        register_manufactured_solution!(zero_field)
        @test lookup_manufactured_solution_2d_reconstruction(
            Dict("name" => "_test_zero_2d")).name === :_test_zero_2d
        delete!(EarthSciSerialization._MMS_REGISTRY_2D_RECONSTRUCTION, :_test_zero_2d)
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

    # ============================================================
    # 2D Arakawa C-grid staggered dispatch (esm-x9f)
    # ============================================================

    # Inline divergence_arakawa_c rule spec. Mirrors the on-disk
    # `discretizations/finite_volume/divergence_arakawa_c.json` shape so the
    # ESS test suite stays self-contained. Two-point centered C-grid divergence:
    # (ux[i+1,j] - ux[i,j])/dx + (uy[i,j+1] - uy[i,j])/dy.
    arakawa_stencil = [
        Dict("selector" => Dict("kind" => "arakawa", "stagger" => "face_x",
                                "axis" => "\$x", "offset" => 0),
             "coeff" => Dict("op" => "/", "args" => Any[-1, "dx"])),
        Dict("selector" => Dict("kind" => "arakawa", "stagger" => "face_x",
                                "axis" => "\$x", "offset" => 1),
             "coeff" => Dict("op" => "/", "args" => Any[1, "dx"])),
        Dict("selector" => Dict("kind" => "arakawa", "stagger" => "face_y",
                                "axis" => "\$y", "offset" => 0),
             "coeff" => Dict("op" => "/", "args" => Any[-1, "dy"])),
        Dict("selector" => Dict("kind" => "arakawa", "stagger" => "face_y",
                                "axis" => "\$y", "offset" => 1),
             "coeff" => Dict("op" => "/", "args" => Any[1, "dy"])),
    ]
    arakawa_rule = Dict("discretizations" => Dict("divergence_arakawa_c" => Dict(
        "applies_to" => Dict("op" => "div", "args" => Any["\$F"]),
        "grid_family" => "arakawa",
        "stagger" => "C",
        "requires_locations" => Any["face_x", "face_y"],
        "emits_location" => "cell_center",
        "combine" => "+",
        "accuracy" => "O(h^2)",
        "stencil" => arakawa_stencil,
    )))
    arakawa_input = Dict(
        "rule" => "divergence_arakawa_c",
        "manufactured_solution" => "F = (sin(2*pi*x)*cos(2*pi*y), " *
            "cos(2*pi*x)*sin(2*pi*y)); div = 4*pi*cos(2*pi*x)*cos(2*pi*y)",
        "sampling" => "cell_center",
        "grids" => [Dict("n" => 16), Dict("n" => 32),
                    Dict("n" => 64), Dict("n" => 128)],
    )
    arakawa_expected = Dict(
        "rule" => "divergence_arakawa_c",
        "metric" => "Linf",
        "expected_min_order" => 1.9,
    )

    @testset "lookup_vector_manufactured_solution — sincos 2D" begin
        ms = lookup_vector_manufactured_solution(
            "F = (sin(2*pi*x)*cos(2*pi*y), cos(2*pi*x)*sin(2*pi*y))")
        @test ms.name === :vec_sincos_2d_periodic
        @test ms.periodic
        @test ms.domain == ((0.0, 1.0), (0.0, 1.0))
        # Velocity at (0.25, 0.0) = (sin(π/2)*cos(0), cos(π/2)*sin(0)) = (1, 0).
        u, v = ms.velocity(0.25, 0.0)
        @test isapprox(u, 1.0; atol=1e-12)
        @test isapprox(v, 0.0; atol=1e-12)
        # Divergence at (0, 0) = 4π.
        @test isapprox(ms.divergence(0.0, 0.0), 4π; atol=1e-12)
        # Dict form with explicit name routes by registry key.
        ms_by_name = lookup_vector_manufactured_solution(
            Dict("name" => "vec_sincos_2d_periodic"))
        @test ms_by_name === ms
        # Dict form with expression falls through to the string lookup.
        ms_by_expr = lookup_vector_manufactured_solution(
            Dict("expression" => "F = (sin(2*pi*x)*cos(2*pi*y), " *
                                 "cos(2*pi*x)*sin(2*pi*y))"))
        @test ms_by_expr === ms
        @test_throws MMSEvaluatorError lookup_vector_manufactured_solution(
            "no such vector field")
        @test_throws MMSEvaluatorError lookup_vector_manufactured_solution(
            Dict("foo" => "bar"))
    end

    @testset "apply_stencil_2d_arakawa — canonical 2x2 fixture" begin
        # Replicates `discretizations/finite_volume/divergence_arakawa_c/
        # fixtures/canonical/{input,expected}.esm`. ux = u(x,y) = x sampled at
        # face_x faces; uy = v(x,y) = y² sampled at face_y faces. Expected
        # divergence per cell is in the fixture's expected.esm `values` field.
        ux = [0.0 0.0; 0.5 0.5; 1.0 1.0]    # shape (3, 2): nx=2, ny=2
        uy = [0.0 0.25 1.0; 0.0 0.25 1.0]   # shape (2, 3)
        cb = CellBindings(Dict{String,Float64}("dx" => 0.5, "dy" => 0.5))
        out = apply_stencil_2d_arakawa(arakawa_stencil, ux, uy, cb)
        @test size(out) == (2, 2)
        @test isapprox(out, [1.5 2.5; 1.5 2.5]; atol=1e-12)
    end

    @testset "apply_stencil_2d_arakawa — periodic MMS sample (constant field)" begin
        # On a constant velocity field, every two-point centered difference is
        # exactly zero — divergence is identically zero across all cells.
        nx, ny = 4, 3
        ux = ones(Float64, nx + 1, ny)
        uy = ones(Float64, nx, ny + 1)
        cb = CellBindings(Dict{String,Float64}("dx" => 0.25, "dy" => 1/3))
        out = apply_stencil_2d_arakawa(arakawa_stencil, ux, uy, cb)
        @test all(out .== 0.0)
    end

    @testset "apply_stencil_2d_arakawa — accepts bare axis names" begin
        # Schema-canonical axis is "$x"/"$y" (with the placeholder $); accept
        # the bare "x"/"y" too so test fixtures don't have to type the dollar.
        bare_stencil = deepcopy(arakawa_stencil)
        for s in bare_stencil
            sel = s["selector"]
            sel["axis"] = sel["axis"] == "\$x" ? "x" : "y"
        end
        ux = [0.0 0.0; 0.5 0.5; 1.0 1.0]
        uy = [0.0 0.25 1.0; 0.0 0.25 1.0]
        cb = CellBindings(Dict{String,Float64}("dx" => 0.5, "dy" => 0.5))
        out = apply_stencil_2d_arakawa(bare_stencil, ux, uy, cb)
        @test isapprox(out, [1.5 2.5; 1.5 2.5]; atol=1e-12)
    end

    @testset "apply_stencil_2d_arakawa — rejects bad selector / shape" begin
        cb = CellBindings(Dict{String,Float64}("dx" => 0.5, "dy" => 0.5))
        ux = zeros(Float64, 3, 2)
        uy = zeros(Float64, 2, 3)

        # Wrong selector kind.
        bad_kind = [Dict("selector" => Dict("kind" => "latlon",
                                            "axis" => "lon", "offset" => 0),
                         "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_2d_arakawa(
            bad_kind, ux, uy, cb)

        # Unknown axis.
        bad_axis = [Dict("selector" => Dict("kind" => "arakawa",
                                            "stagger" => "face_x",
                                            "axis" => "z", "offset" => 0),
                         "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_2d_arakawa(
            bad_axis, ux, uy, cb)

        # face_x must pair with x axis.
        cross_axis = [Dict("selector" => Dict("kind" => "arakawa",
                                              "stagger" => "face_x",
                                              "axis" => "\$y", "offset" => 0),
                           "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_2d_arakawa(
            cross_axis, ux, uy, cb)

        # Unknown stagger (e.g. cell_center) is rejected — the applier only
        # supports face-staggered velocity inputs in this iteration.
        bad_stagger = [Dict("selector" => Dict("kind" => "arakawa",
                                               "stagger" => "cell_center",
                                               "axis" => "\$x", "offset" => 0),
                            "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_2d_arakawa(
            bad_stagger, ux, uy, cb)

        # ux/uy shape mismatch.
        ux_bad = zeros(Float64, 4, 2)
        @test_throws MMSEvaluatorError apply_stencil_2d_arakawa(
            arakawa_stencil, ux_bad, uy, cb)

        # Out-of-range offset.
        oob = [Dict("selector" => Dict("kind" => "arakawa",
                                       "stagger" => "face_x",
                                       "axis" => "\$x", "offset" => 5),
                    "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_2d_arakawa(
            oob, ux, uy, cb)
    end

    @testset "mms_convergence — divergence_arakawa_c (sincos 2D MMS)" begin
        result = mms_convergence(arakawa_rule, arakawa_input)
        @test length(result.errors) == 4
        @test all(isfinite, result.errors)
        @test all(result.errors .> 0)
        @test result.declared_order == 2.0
        @test all(result.errors[i] > result.errors[i + 1] for i in 1:3)
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
        @test result.orders[end] ≥ 1.9
    end

    @testset "verify_mms_convergence — passes on arakawa C divergence" begin
        result = verify_mms_convergence(
            arakawa_rule, arakawa_input, arakawa_expected)
        @test result.observed_min_order ≥ arakawa_expected["expected_min_order"]
        @test result.observed_min_order ≥ 1.9
    end

    @testset "mms_convergence — arakawa with explicit nx/ny grid entries" begin
        # Asymmetric grids should also converge at order 2 — the stencil is
        # tensor-product-like and each axis converges independently.
        explicit = Base.merge(arakawa_input, Dict(
            "grids" => [Dict("nx" => 32, "ny" => 16),
                        Dict("nx" => 64, "ny" => 32),
                        Dict("nx" => 128, "ny" => 64)]))
        result = mms_convergence(arakawa_rule, explicit)
        @test result.observed_min_order ≥ 1.85
    end

    @testset "mms_convergence — arakawa error paths" begin
        # 1D solution on a 2D arakawa rule is a type error.
        @test_throws MMSEvaluatorError mms_convergence(
            arakawa_rule, arakawa_input;
            manufactured=lookup_manufactured_solution(
                "sin(2*pi*x) on [0,1] periodic"))

        # Grid entry missing both `n` and `nx`/`ny` is rejected.
        bad_grid = Base.merge(arakawa_input, Dict("grids" => [Dict("foo" => 1),
                                                              Dict("foo" => 2)]))
        @test_throws MMSEvaluatorError mms_convergence(arakawa_rule, bad_grid)

        # Single grid is too few.
        too_few = Base.merge(arakawa_input, Dict("grids" => [Dict("n" => 16)]))
        @test_throws MMSEvaluatorError mms_convergence(arakawa_rule, too_few)

        # Mixed selector kinds in a single stencil are rejected.
        mixed_stencil = Any[]
        for s in arakawa_stencil
            push!(mixed_stencil, deepcopy(s))
        end
        push!(mixed_stencil,
              Dict{String,Any}("selector" => Dict{String,Any}(
                                   "kind" => "cartesian",
                                   "axis" => "x", "offset" => 0),
                               "coeff" => 0.0))
        mixed = Dict("discretizations" => Dict(
            "divergence_arakawa_c" => Base.merge(
                arakawa_rule["discretizations"]["divergence_arakawa_c"],
                Dict("stencil" => mixed_stencil))))
        @test_throws MMSEvaluatorError mms_convergence(mixed, arakawa_input)
    end

    @testset "register_vector_manufactured_solution! — arakawa path" begin
        # Custom 2D vector MMS with both components nonzero in both axes.
        # F = (cos(2π x) sin(2π y), -sin(2π x) cos(2π y))
        # ∂_x [cos(2π x) sin(2π y)] = -2π sin(2π x) sin(2π y)
        # ∂_y [-sin(2π x) cos(2π y)] = -sin(2π x) · -2π sin(2π y) = 2π sin(2π x) sin(2π y)
        # Sum = 0 — divergence-free. So we use a different non-trivial choice.
        # F = (sin(2π x) sin(2π y), sin(2π x) sin(2π y))
        # ∂_x F1 = 2π cos(2π x) sin(2π y); ∂_y F2 = 2π sin(2π x) cos(2π y)
        # div = 2π (cos(2π x) sin(2π y) + sin(2π x) cos(2π y))
        custom = VectorManufacturedSolution(
            :_test_arakawa_custom,
            (x, y) -> (sin(2π * x) * sin(2π * y), sin(2π * x) * sin(2π * y)),
            (x, y) -> 2π * (cos(2π * x) * sin(2π * y) +
                            sin(2π * x) * cos(2π * y)),
            ((0.0, 1.0), (0.0, 1.0)),
            true,
        )
        register_vector_manufactured_solution!(custom)
        @test EarthSciSerialization._MMS_VECTOR_REGISTRY[:_test_arakawa_custom] === custom
        result = mms_convergence(
            arakawa_rule, arakawa_input; manufactured=custom)
        @test result.observed_min_order ≥ 1.9
        delete!(EarthSciSerialization._MMS_VECTOR_REGISTRY, :_test_arakawa_custom)
    end

    # ============================================================
    # 1D vertical face-staggered stencils (esm-bhv)
    # ============================================================
    # Inline centered_2nd_uniform_vertical rule spec. Mirrors the ESD-side rule
    # shape: a 1D vertical grid with face_top / face_bottom selectors carrying
    # offset 0, computing (u_face[i+1] − u_face[i])/dz at each cell center.
    vertical_stencil = [
        Dict("selector" => Dict("kind" => "vertical",
                                "stagger" => "face_bottom", "offset" => 0),
             "coeff" => Dict("op" => "/", "args" => Any[-1, "dz"])),
        Dict("selector" => Dict("kind" => "vertical",
                                "stagger" => "face_top", "offset" => 0),
             "coeff" => Dict("op" => "/", "args" => Any[1, "dz"])),
    ]
    vertical_rule = Dict("discretizations" => Dict(
        "centered_2nd_uniform_vertical" => Dict(
            "applies_to" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "z"),
            "grid_family" => "cartesian",
            "combine" => "+",
            "accuracy" => "O(dz^2)",
            "stencil" => vertical_stencil,
        )))
    vertical_input = Dict(
        "rule" => "centered_2nd_uniform_vertical",
        "manufactured_solution" => "sin(2*pi*z) on [0,1] vertical column",
        "sampling" => "cell_center",
        "grids" => [Dict("nz" => 16), Dict("nz" => 32),
                    Dict("nz" => 64), Dict("nz" => 128)],
    )
    vertical_expected = Dict(
        "rule" => "centered_2nd_uniform_vertical",
        "metric" => "Linf",
        "expected_min_order" => 1.9,
    )

    @testset "lookup_manufactured_solution — vertical sin(2π z)" begin
        ms = lookup_manufactured_solution(
            "sin(2*pi*z) on [0,1] vertical column")
        @test ms.name === :vertical_sin_2pi_z_unit_column
        @test ms.domain == (0.0, 1.0)
        @test !ms.periodic
        @test isapprox(ms.sample(0.25), 1.0; atol=1e-12)
        @test isapprox(ms.derivative(0.0), 2π; atol=1e-12)
        # Dict form by registry name.
        ms_by_name = lookup_manufactured_solution(
            Dict("name" => "vertical_sin_2pi_z_unit_column"))
        @test ms_by_name === ms
    end

    @testset "apply_stencil_1d_vertical — centered face-difference exact on linear" begin
        # u(z) = a + b z sampled at faces. Centered difference (u_top − u_bot)/dz
        # equals b at every cell center, exactly.
        nz = 5
        dz = 1.0 / nz
        z_face = [(i - 1) * dz for i in 1:(nz + 1)]
        a, b = 0.7, -1.25
        u_face = a .+ b .* z_face
        cb = CellBindings(Dict{String,Float64}("dz" => dz))
        out = apply_stencil_1d_vertical(vertical_stencil, u_face, cb)
        @test length(out) == nz
        @test all(isapprox.(out, b; atol=1e-12))
    end

    @testset "apply_stencil_1d_vertical — rejects bad selector / shape" begin
        cb = CellBindings(Dict{String,Float64}("dz" => 0.5))
        u_face = zeros(Float64, 3)

        # Wrong selector kind.
        bad_kind = [Dict("selector" => Dict("kind" => "cartesian",
                                            "axis" => "z", "offset" => 0),
                         "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_1d_vertical(
            bad_kind, u_face, cb)

        # Unknown stagger (cell_center is not yet supported by this applier).
        bad_stagger = [Dict("selector" => Dict("kind" => "vertical",
                                               "stagger" => "cell_center",
                                               "offset" => 0),
                            "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_1d_vertical(
            bad_stagger, u_face, cb)

        # Out-of-range offset on face_top: at cell nz with offset=+1, would
        # need u_face[nz+2], one past the domain.
        oob = [Dict("selector" => Dict("kind" => "vertical",
                                       "stagger" => "face_top",
                                       "offset" => 1),
                    "coeff" => 1.0)]
        @test_throws MMSEvaluatorError apply_stencil_1d_vertical(
            oob, u_face, cb)

        # u_face too short to host a cell.
        @test_throws MMSEvaluatorError apply_stencil_1d_vertical(
            vertical_stencil, [1.0], cb)
    end

    @testset "mms_convergence — centered_2nd_uniform_vertical (sin 2π z)" begin
        result = mms_convergence(vertical_rule, vertical_input)
        @test length(result.errors) == 4
        @test all(isfinite, result.errors)
        @test all(result.errors .> 0)
        @test result.declared_order == 2.0
        @test all(result.errors[i] > result.errors[i + 1] for i in 1:3)
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
        @test result.orders[end] ≥ 1.9
    end

    @testset "verify_mms_convergence — passes on vertical sin(2π z)" begin
        result = verify_mms_convergence(
            vertical_rule, vertical_input, vertical_expected)
        @test result.observed_min_order ≥ vertical_expected["expected_min_order"]
        @test result.observed_min_order ≥ 1.9
    end

    @testset "mms_convergence — vertical with explicit `n` grid entries" begin
        explicit = Base.merge(vertical_input, Dict(
            "grids" => [Dict("n" => 16), Dict("n" => 32), Dict("n" => 64)]))
        result = mms_convergence(vertical_rule, explicit)
        @test result.observed_min_order ≥ 1.85
    end

    @testset "mms_convergence — vertical error paths" begin
        # 2D solution on a 1D vertical rule is a type error (vector MMS).
        @test_throws MMSEvaluatorError mms_convergence(
            vertical_rule, vertical_input;
            manufactured=lookup_vector_manufactured_solution(
                "F = (sin(2*pi*x)*cos(2*pi*y), cos(2*pi*x)*sin(2*pi*y))"))

        # Grid entry missing both `nz` and `n` is rejected.
        bad_grid = Base.merge(vertical_input, Dict(
            "grids" => [Dict("foo" => 1), Dict("foo" => 2)]))
        @test_throws MMSEvaluatorError mms_convergence(vertical_rule, bad_grid)

        # Single grid is too few.
        too_few = Base.merge(vertical_input, Dict("grids" => [Dict("nz" => 16)]))
        @test_throws MMSEvaluatorError mms_convergence(vertical_rule, too_few)
    end

    # ============================================================
    # AST-walker dispatch for closed-AST lowerings (esm-4gw)
    # ============================================================

    # Centered 2nd-order finite difference expressed as a closed §4.2 AST
    # (no `stencil` block). The lowering is an `arrayop` whose body contains
    # `index(u, i±1)` against periodic BCs declared in the input fixture.
    centered_lowering_rule = Dict(
        "discretizations" => Dict(
            "centered_2nd_uniform_arrayop" => Dict(
                "applies_to" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                "grid_family" => "cartesian",
                "accuracy" => "O(dx^2)",
                "lowering" => Dict(
                    "op" => "arrayop",
                    "output_idx" => Any["i"],
                    "ranges" => Dict("i" => Any[1, "n"]),
                    "expr" => Dict(
                        "op" => "/",
                        "args" => Any[
                            Dict("op" => "-", "args" => Any[
                                Dict("op" => "index", "args" => Any[
                                    "u",
                                    Dict("op" => "+", "args" => Any["i", 1]),
                                ]),
                                Dict("op" => "index", "args" => Any[
                                    "u",
                                    Dict("op" => "-", "args" => Any["i", 1]),
                                ]),
                            ]),
                            Dict("op" => "*", "args" => Any[2, "dx"]),
                        ],
                    ),
                    "args" => Any["u"],
                ),
            ),
        ),
    )
    centered_lowering_input = Dict(
        "rule" => "centered_2nd_uniform_arrayop",
        "manufactured_solution" => Dict("name" => "phase_shifted_sine"),
        "sampling" => "cell_center",
        "grids" => [Dict("n" => 16), Dict("n" => 32),
                    Dict("n" => 64), Dict("n" => 128)],
        "boundary_conditions" => [
            Dict("type" => "periodic", "dimensions" => Any["x"]),
        ],
    )

    @testset "AST-walker dispatch — centered 2nd FD as arrayop" begin
        result = mms_convergence(centered_lowering_rule, centered_lowering_input)
        @test result.grids == [16, 32, 64, 128]
        @test length(result.errors) == 4
        @test all(result.errors .> 0) && all(isfinite, result.errors)
        @test all(result.errors[i] > result.errors[i+1] for i in 1:3)
        @test result.declared_order == 2.0
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
        @test result.orders[end] ≥ 1.95
    end

    @testset "AST-walker dispatch — verify_mms_convergence path" begin
        expected = Dict(
            "rule" => "centered_2nd_uniform_arrayop",
            "metric" => "Linf",
            "expected_min_order" => 1.9,
        )
        result = verify_mms_convergence(
            centered_lowering_rule, centered_lowering_input, expected)
        @test result.observed_min_order ≥ expected["expected_min_order"]
    end

    @testset "AST-walker dispatch — broadcast on top-level arrayop" begin
        # Same centered-difference but expressed as
        #   broadcast(*, 1.0, arrayop(...))
        # to exercise the top-level broadcast path. Identity-multiplying by a
        # scalar literal must not change the convergence rate.
        bcast_rule = deepcopy(centered_lowering_rule)
        inner = bcast_rule["discretizations"]["centered_2nd_uniform_arrayop"]["lowering"]
        bcast_rule["discretizations"]["centered_2nd_uniform_arrayop"]["lowering"] = Dict(
            "op" => "broadcast",
            "fn" => "*",
            "args" => Any[inner, 1.0],
        )
        result = mms_convergence(bcast_rule, centered_lowering_input)
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
    end

    @testset "AST-walker dispatch — bare-spec form" begin
        bare = centered_lowering_rule["discretizations"]["centered_2nd_uniform_arrayop"]
        result = mms_convergence(bare, centered_lowering_input)
        @test abs(result.observed_min_order - 2.0) ≤ 0.2
    end

    @testset "AST-walker dispatch — error paths" begin
        # Missing accuracy on the lowering rule.
        no_accuracy = deepcopy(centered_lowering_rule)
        delete!(no_accuracy["discretizations"]["centered_2nd_uniform_arrayop"], "accuracy")
        @test_throws MMSEvaluatorError mms_convergence(
            no_accuracy, centered_lowering_input)

        # Robin BC is rejected with a clear error (out of scope for esm-4gw).
        robin_input = Base.merge(centered_lowering_input, Dict(
            "boundary_conditions" => Any[
                Dict("type" => "robin", "dimensions" => Any["x"],
                     "robin_alpha" => 1.0, "robin_beta" => 0.0,
                     "robin_gamma" => 0.0)]))
        @test_throws MMSEvaluatorError mms_convergence(
            centered_lowering_rule, robin_input)

        # rank-2 output is rejected (follow-up bead).
        rank2_rule = deepcopy(centered_lowering_rule)
        rank2_rule["discretizations"]["centered_2nd_uniform_arrayop"]["lowering"]["output_idx"] =
            Any["i", "j"]
        @test_throws MMSEvaluatorError mms_convergence(
            rank2_rule, centered_lowering_input)

        # Unknown op in the lowering body is rejected.
        bad_op_rule = deepcopy(centered_lowering_rule)
        bad_op_rule["discretizations"]["centered_2nd_uniform_arrayop"]["lowering"]["expr"] =
            Dict("op" => "this_is_not_a_real_op", "args" => Any[1.0])
        @test_throws MMSEvaluatorError mms_convergence(
            bad_op_rule, centered_lowering_input)
    end

    @testset "AST-walker dispatch — periodic BC wraps explicitly" begin
        # Verify wrap-around: the centered difference at cell 1 must equal
        # (u[2] - u[n]) / (2 dx), i.e. the periodic BC was actually applied.
        n = 32
        dx = 1.0 / n
        u = [sin(2π * (i - 0.5) * dx + 1.0) for i in 1:n]
        env = EarthSciSerialization._LoweringEnv(
            Dict{String,Vector{Float64}}("u" => u),
            Dict{String,Float64}("dx" => dx, "h" => dx,
                                 "n" => Float64(n), "domain_lo" => 0.0),
            Dict{String,Int}(),
            EarthSciSerialization._AxisBC[
                EarthSciSerialization._AxisBC(:periodic, 0.0)],
        )
        lowering =
            centered_lowering_rule["discretizations"]["centered_2nd_uniform_arrayop"]["lowering"]
        result = EarthSciSerialization._eval_lowering_array(lowering, env)
        @test length(result) == n
        @test isapprox(result[1], (u[2] - u[n]) / (2 * dx); atol=1e-12)
        @test isapprox(result[n], (u[1] - u[n - 1]) / (2 * dx); atol=1e-12)
    end

    # ============================================================
    # esm-8i9: AST-walker reaches form=weighted_essentially_nonoscillatory
    # rules whose body lives in a closed-AST `lowering` (no legacy
    # reconstruction_left_biased / axes blocks), and binds multiple
    # rank-1 input arrays — enough to express the weno5_advection
    # `div($U·$q, $x)` shape end-to-end.
    # ============================================================

    # Helper: AST node for the linear-weight 5-point reconstruction of
    # cell-averaged q at face i+1/2 (offsets `offs`, integer numerators
    # `nums`, common denominator `den`). Equivalent to the WENO5 linear
    # combination with the smoothness-indicator nonlinearity dropped —
    # 5th-order accurate on smooth data, which suffices for the >= 4.7
    # convergence acceptance bar without re-implementing the full WENO5
    # weights inside the lowering AST.
    function _q_recon_5pt(offs, nums, den)
        function _idx(off::Int)
            off == 0 && return Dict("op" => "index",
                                    "args" => Any["q", "i"])
            shift = off > 0 ?
                Dict("op" => "+", "args" => Any["i", off]) :
                Dict("op" => "-", "args" => Any["i", -off])
            return Dict("op" => "index", "args" => Any["q", shift])
        end
        terms = Any[Dict("op" => "*", "args" => Any[Float64(c), _idx(o)])
                    for (o, c) in zip(offs, nums)]
        return Dict("op" => "/",
                    "args" => Any[Dict("op" => "+", "args" => terms),
                                  Float64(den)])
    end
    # Left-biased: cells {i-2..i+2} at face i+1/2.
    _q_left_5pt  = _q_recon_5pt((-2, -1, 0, 1, 2), (2, -13, 47, 27, -3), 60)
    # Right-biased: mirror image, cells {i-1..i+3} at face i+1/2.
    _q_right_5pt = _q_recon_5pt((-1, 0, 1, 2, 3), (-3, 27, 47, -13, 2), 60)

    # Closed-AST WENO5-style advection rule: form gates the dispatch, but
    # there are no `reconstruction_left_biased` / `axes` blocks — so the
    # AST-walker (esm-4gw + esm-8i9) must own this rule. The lowering
    # binds two input arrays ($U, $q) and uses `ifelse` to pick the upwind
    # 5-point reconstruction by the sign of U at the face.
    weno5_lowering_rule = Dict(
        "discretizations" => Dict(
            "weno5_advection_lowering" => Dict(
                # Multi-input applies_to: div($U · $q, $x).
                "applies_to" => Dict(
                    "op" => "div",
                    "args" => Any[
                        Dict("op" => "*", "args" => Any["\$U", "\$q"]),
                    ],
                    "dim" => "\$x",
                ),
                "form" => "weighted_essentially_nonoscillatory",
                "grid_family" => "cartesian",
                "accuracy" => "O(dx^5)",
                "lowering" => Dict(
                    "op" => "arrayop",
                    "output_idx" => Any["i"],
                    "ranges" => Dict("i" => Any[1, "n"]),
                    "args" => Any["U", "q"],
                    "expr" => Dict(
                        "op" => "*",
                        "args" => Any[
                            Dict("op" => "index", "args" => Any["U", "i"]),
                            Dict("op" => "ifelse", "args" => Any[
                                Dict("op" => ">", "args" => Any[
                                    Dict("op" => "index",
                                         "args" => Any["U", "i"]),
                                    0.0,
                                ]),
                                _q_left_5pt,
                                _q_right_5pt,
                            ]),
                        ],
                    ),
                ),
            ),
        ),
    )

    # Sweep input. `input_arrays` binds U (constant 1.0 — pure positive
    # advection) and q (smooth manufactured solution). The top-level
    # `manufactured_solution` is the reference: its `value_at_edge_right`
    # samples are the face values the reconstruction must recover.
    # Backwards-compatible — the legacy `input_array` / single-binding
    # path is exercised by the centered_lowering_rule tests above.
    weno5_lowering_input = Dict(
        "rule" => "weno5_advection_lowering",
        "manufactured_solution" => Dict("name" => "phase_shifted_sine"),
        "sampling" => "cell_average",
        "output_kind" => "value_at_edge_right",
        "input_arrays" => Any[
            Dict("name" => "U", "constant" => 1.0),
            Dict("name" => "q",
                 "manufactured_solution" => Dict("name" => "phase_shifted_sine")),
        ],
        "grids" => [Dict("n" => 32), Dict("n" => 64),
                    Dict("n" => 128), Dict("n" => 256)],
        "boundary_conditions" => [
            Dict("type" => "periodic", "dimensions" => Any["x"]),
        ],
    )

    @testset "AST-walker — closed-AST WENO5 dispatches via form fall-through" begin
        # form=weighted_essentially_nonoscillatory but no legacy keys →
        # _mms_rule_kind must NOT claim :weno5; mms_convergence routes to
        # the AST-walker via `lowering`. (Layer-B convergence acceptance.)
        result = mms_convergence(weno5_lowering_rule, weno5_lowering_input)
        @test result.declared_order == 5.0
        @test result.grids == [32, 64, 128, 256]
        @test all(result.errors .> 0) && all(isfinite, result.errors)
        @test all(result.errors[i] > result.errors[i+1] for i in 1:3)
        @test result.observed_min_order ≥ 4.7
    end

    @testset "AST-walker — _mms_rule_kind ignores form without legacy keys" begin
        # The dispatch helper itself: form alone is not enough.
        spec_no_legacy = weno5_lowering_rule["discretizations"][
            "weno5_advection_lowering"]
        @test EarthSciSerialization._mms_rule_kind(spec_no_legacy) ===
              :linear_stencil
        # Add a legacy block back in → :weno5 again.
        spec_with_legacy = deepcopy(spec_no_legacy)
        spec_with_legacy["reconstruction_left_biased"] = Dict()
        @test EarthSciSerialization._mms_rule_kind(spec_with_legacy) === :weno5
    end

    @testset "AST-walker — multi-input env binds U and q independently" begin
        # The lowering must see U and q as separate Vector{Float64} entries.
        # Choose U identically -1 → ifelse picks the right-biased branch.
        # Negating sign matches WENO5 behaviour: face value still recovered
        # at 5th order.
        right_input = Base.merge(weno5_lowering_input, Dict(
            "input_arrays" => Any[
                Dict("name" => "U", "constant" => -1.0),
                Dict("name" => "q",
                     "manufactured_solution" =>
                         Dict("name" => "phase_shifted_sine")),
            ]))
        # output = U · q_face; with U = -1, the *signed* error against
        # +q_face is the same magnitude — verify by comparing against the
        # negative reference.
        n = 64
        dx = 1.0 / n
        ms = lookup_manufactured_solution(Dict("name" => "phase_shifted_sine"))
        u_arr = fill(-1.0, n)
        q_arr = [ms.cell_average((i - 1) * dx, i * dx) for i in 1:n]
        env = EarthSciSerialization._LoweringEnv(
            Dict{String,Vector{Float64}}("U" => u_arr, "q" => q_arr),
            Dict{String,Float64}("dx" => dx, "h" => dx,
                                 "n" => Float64(n), "domain_lo" => 0.0),
            Dict{String,Int}(),
            EarthSciSerialization._AxisBC[
                EarthSciSerialization._AxisBC(:periodic, 0.0)],
        )
        lowering = weno5_lowering_rule["discretizations"][
            "weno5_advection_lowering"]["lowering"]
        result = EarthSciSerialization._eval_lowering_array(lowering, env)
        @test length(result) == n
        # |result| ≈ |q at face|; same magnitude as positive-U reconstruction.
        face = [ms.sample(i * dx) for i in 1:n]
        @test maximum(abs.(result .+ face)) < 0.01
    end

    @testset "AST-walker — input_arrays validation" begin
        # Unknown / missing fields surface E_MMS_BAD_FIXTURE.
        bad_shape = Base.merge(weno5_lowering_input, Dict(
            "input_arrays" => Dict("U" => 1.0)))   # not a list
        @test_throws MMSEvaluatorError mms_convergence(
            weno5_lowering_rule, bad_shape)

        empty_list = Base.merge(weno5_lowering_input, Dict(
            "input_arrays" => Any[]))
        @test_throws MMSEvaluatorError mms_convergence(
            weno5_lowering_rule, empty_list)

        no_name = Base.merge(weno5_lowering_input, Dict(
            "input_arrays" => Any[Dict("constant" => 1.0)]))
        @test_throws MMSEvaluatorError mms_convergence(
            weno5_lowering_rule, no_name)

        both_specs = Base.merge(weno5_lowering_input, Dict(
            "input_arrays" => Any[Dict("name" => "U",
                                       "constant" => 1.0,
                                       "manufactured_solution" =>
                                           Dict("name" => "phase_shifted_sine"))]))
        @test_throws MMSEvaluatorError mms_convergence(
            weno5_lowering_rule, both_specs)

        neither_spec = Base.merge(weno5_lowering_input, Dict(
            "input_arrays" => Any[Dict("name" => "U")]))
        @test_throws MMSEvaluatorError mms_convergence(
            weno5_lowering_rule, neither_spec)

        dup_name = Base.merge(weno5_lowering_input, Dict(
            "input_arrays" => Any[
                Dict("name" => "U", "constant" => 1.0),
                Dict("name" => "U", "constant" => 2.0),
            ]))
        @test_throws MMSEvaluatorError mms_convergence(
            weno5_lowering_rule, dup_name)
    end

    # ============================================================
    # Face-staggered Courant binding (esm-2q0)
    # ============================================================
    #
    # Face-flux rules need per-face manufactured fields that the AST-lowering
    # walker can index. Verifies:
    #   1. Face-velocity is sampled at face positions (left edge of each cell).
    #   2. Face-courant is derived as v[i] * dt / dx_face.
    #   3. dx_face_<axis> scalar is exposed for the rule's metric divides.
    #   4. A face-flux divergence rule converges at its declared order.
    #   5. Schema errors are raised for malformed bindings.

    # Face-flux divergence: forward-difference of face-sampled velocity
    # produces a cell-centered derivative. With v sampled at left faces
    # (v[i] = sin(2π * (i-1) * dx) for sin_2pi_x_periodic), the body
    # `(v[i+1] - v[i]) / dx` approximates v'(x_cell_center) at second order.
    # The face-courant binding is also declared (and references v) to
    # exercise the courant derivation path; it is unused in the lowering body
    # so the convergence rate is unaffected by the constant-dt CFL behavior.
    face_div_rule = Dict(
        "discretizations" => Dict(
            "face_flux_div_arrayop" => Dict(
                "applies_to" => Dict("op" => "grad", "args" => Any["\$v"], "dim" => "\$x"),
                "grid_family" => "cartesian",
                "accuracy" => "O(dx^2)",
                "lowering" => Dict(
                    "op" => "arrayop",
                    "output_idx" => Any["i"],
                    "ranges" => Dict("i" => Any[1, "n"]),
                    "expr" => Dict(
                        "op" => "/",
                        "args" => Any[
                            Dict("op" => "-", "args" => Any[
                                Dict("op" => "index", "args" => Any[
                                    "\$v",
                                    Dict("op" => "+", "args" => Any["i", 1]),
                                ]),
                                Dict("op" => "index", "args" => Any["\$v", "i"]),
                            ]),
                            "dx_face_xi",
                        ],
                    ),
                ),
            ),
        ),
    )
    face_div_input = Dict(
        "rule" => "face_flux_div_arrayop",
        "manufactured_solution" => Dict("name" => "sin_2pi_x_periodic"),
        "sampling" => "cell_center",
        "output_kind" => "derivative_at_cell_center",
        "grids" => [Dict("n" => 16), Dict("n" => 32),
                    Dict("n" => 64), Dict("n" => 128)],
        "boundary_conditions" => [
            Dict("type" => "periodic", "dimensions" => Any["x"]),
        ],
        "dt" => 1.0e-3,
        "bindings" => Dict(
            "\$v" => Dict(
                "kind" => "face_velocity",
                "axis" => "xi",
                "manufactured_solution" => Dict("name" => "sin_2pi_x_periodic"),
            ),
            "\$c" => Dict(
                "kind" => "face_courant",
                "axis" => "xi",
                "velocity_symbol" => "\$v",
            ),
        ),
    )

    @testset "Face-staggered Courant binding (esm-2q0)" begin
        @testset "face-flux divergence converges at second order" begin
            result = mms_convergence(face_div_rule, face_div_input)
            @test result.grids == [16, 32, 64, 128]
            @test all(result.errors .> 0) && all(isfinite, result.errors)
            @test all(result.errors[i] > result.errors[i+1] for i in 1:3)
            @test result.declared_order == 2.0
            @test abs(result.observed_min_order - 2.0) ≤ 0.2
        end

        @testset "face-velocity samples at face positions, not cell centers" begin
            # Build the env directly via the unexported helpers to inspect the
            # materialized arrays without running the full convergence sweep.
            specs = EarthSciSerialization._parse_face_bindings(face_div_input)
            @test length(specs) == 2

            n = 8
            dx = 1.0 / n
            arrays = Dict{String,Vector{Float64}}()
            scalars = Dict{String,Float64}()
            EarthSciSerialization._materialize_face_bindings!(
                arrays, scalars, specs, 0.0, dx, n, 1.0e-3)

            # Face-velocity at left edge of cell 1 is x = 0 → sin(0) = 0.
            @test isapprox(arrays["\$v"][1], 0.0; atol=1e-12)
            # Face-velocity at left edge of cell 3 (n=8) is x = 2*dx → sin(2π·0.25).
            @test isapprox(arrays["\$v"][3], sin(2π * 2 * dx); atol=1e-12)
            # Cell-center sampling would put v[1] at x=0.5*dx ≠ 0, so confirm
            # the harness did NOT sample at cell centers.
            @test !isapprox(arrays["\$v"][1], sin(2π * 0.5 * dx); atol=1e-9)

            # Face-courant: v[i] * dt / dx.
            for i in 1:n
                @test isapprox(arrays["\$c"][i], arrays["\$v"][i] * 1.0e-3 / dx;
                                atol=1e-12)
            end

            # Per-axis face spacing scalar exposed.
            @test scalars["dx_face_xi"] == dx
        end

        @testset "scalar bindings remain unchanged (backward compat)" begin
            # The pre-existing AST-walker test fixture has no `bindings` field
            # and must continue to pass with bit-for-bit identical behavior.
            # This is covered by the "AST-walker dispatch — centered 2nd FD"
            # testset above; here we additionally confirm that an empty
            # `bindings` dict is a no-op.
            no_face_input = Base.merge(face_div_input, Dict("bindings" => Dict()))
            # Without face-binding $v, the lowering's `index($v, ...)` op will
            # fail. We expect an error — verifying the bindings field really
            # was emptied (not silently merged with the prior dict).
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, no_face_input)
        end

        @testset "schema errors" begin
            # `bindings` must be an object.
            bad_type = Base.merge(face_div_input, Dict("bindings" => Any[]))
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, bad_type)

            # Missing `manufactured_solution` on face_velocity.
            bad_v = deepcopy(face_div_input)
            delete!(bad_v["bindings"]["\$v"], "manufactured_solution")
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, bad_v)

            # Missing `velocity_symbol` on face_courant.
            bad_c = deepcopy(face_div_input)
            delete!(bad_c["bindings"]["\$c"], "velocity_symbol")
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, bad_c)

            # face_courant references undeclared face_velocity.
            dangling = deepcopy(face_div_input)
            dangling["bindings"]["\$c"]["velocity_symbol"] = "\$nonexistent"
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, dangling)

            # Unknown binding kind.
            unknown_kind = deepcopy(face_div_input)
            unknown_kind["bindings"]["\$v"]["kind"] = "cell_centered_velocity"
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, unknown_kind)

            # face_courant declared but no top-level `dt`.
            no_dt = deepcopy(face_div_input)
            delete!(no_dt, "dt")
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, no_dt)

            # Non-mapping entry. (Use Dict{String,Any} so the test can assign
            # a String into a slot whose original value was a Dict.)
            bad_entry = Base.merge(face_div_input, Dict(
                "bindings" => Dict{String,Any}("\$v" => "not a mapping")))
            @test_throws MMSEvaluatorError mms_convergence(face_div_rule, bad_entry)
        end
    end

    @testset "apply_stencil_ghosted_1d (esm-37k, RFC §5.2.8)" begin
        # Centered 2nd-order finite difference: stencil = (-1/(2dx), 0, +1/(2dx))
        # at offsets ±1. Used as the carrier for every boundary_policy below.
        centered_fd = [
            Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => -1),
                 "coeff" => Dict("op" => "/", "args" =>
                     Any[-1, Dict("op" => "*", "args" => Any[2, "dx"])])),
            Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => 1),
                 "coeff" => Dict("op" => "/", "args" =>
                     Any[1, Dict("op" => "*", "args" => Any[2, "dx"])])),
        ]

        @testset "periodic kind: byte-equal to apply_stencil_periodic_1d" begin
            n = 32
            dx = 1.0 / n
            u = [sin(2π * (i - 0.5) * dx) for i in 1:n]
            bindings = Dict("dx" => dx)
            ref = apply_stencil_periodic_1d(centered_fd, u, bindings)
            for Ng in (1, 2, 5)
                got = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                               ghost_width=Ng,
                                               boundary_policy="periodic")
                @test got == ref  # bit-equal: periodic ghost fill is the same wrap
            end
        end

        @testset "reflecting kind: zero-flux at boundary on a symmetric profile" begin
            # u = cos(πx) on [0,1] (cell centers) is symmetric across the boundary
            # face, so reflecting fill leaves the centered FD operator self-consistent.
            n = 16
            dx = 1.0 / n
            u = [cos(π * (i - 0.5) * dx) for i in 1:n]
            bindings = Dict("dx" => dx)
            got = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                           ghost_width=1,
                                           boundary_policy="reflecting")
            # First interior cell: ghost is u[1] (mirror), so derivative there
            # uses (u[2] - u[1])/(2dx) — the one-sided forward difference shape.
            @test got[1] ≈ (u[2] - u[1]) / (2 * dx) atol=1e-12
            @test got[n] ≈ (u[n] - u[n - 1]) / (2 * dx) atol=1e-12
            # Compares acceptably against -π sin(πx) at interior cells.
            ref = [-π * sin(π * (i - 0.5) * dx) for i in 1:n]
            @test maximum(abs.(got[3:n - 2] .- ref[3:n - 2])) < 0.05
        end

        @testset "reflecting kind: ghosted neumann_zero alias" begin
            # neumann_zero is a v0.3.x alias for reflecting (same fill semantics).
            n = 8
            dx = 1.0 / n
            u = collect(Float64, 1:n)
            bindings = Dict("dx" => dx)
            via_reflecting = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                                     ghost_width=1,
                                                     boundary_policy="reflecting")
            via_neumann = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                                  ghost_width=1,
                                                  boundary_policy="neumann_zero")
            @test via_neumann == via_reflecting
        end

        @testset "one_sided_extrapolation: linear default exact on linear profile" begin
            # u = 2 + 3i on cell-index space → linear extrapolation is exact, so
            # the centered FD reproduces du/dx ≡ slope/dx everywhere, including
            # the first and last interior cells.
            n = 12
            dx = 0.1
            u = Float64[2.0 + 3.0 * i for i in 1:n]
            bindings = Dict("dx" => dx)
            got = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                           ghost_width=1,
                                           boundary_policy="one_sided_extrapolation")
            @test all(g -> isapprox(g, 3.0 / dx; atol=1e-10), got)
        end

        @testset "one_sided_extrapolation: degree=2 exact on quadratic profile" begin
            # u = i^2 on cell-index space → quadratic extrapolation is exact.
            # Compare against the analytic centered-FD output of the polynomial
            # (which is also exact for centered FD on quadratics).
            n = 10
            dx = 0.5
            u = Float64[Float64(i)^2 for i in 1:n]
            bindings = Dict("dx" => dx)
            got = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                           ghost_width=1,
                                           boundary_policy=Dict("kind" => "one_sided_extrapolation",
                                                                "degree" => 2))
            # Centered FD on i^2: ((i+1)^2 - (i-1)^2) / (2dx) = 4i / (2dx) = 2i/dx.
            ref = Float64[2.0 * i / dx for i in 1:n]
            @test maximum(abs.(got .- ref)) < 1e-10
        end

        @testset "one_sided_extrapolation: degree=3 exact on cubic profile" begin
            n = 12
            dx = 0.25
            u = Float64[Float64(i)^3 for i in 1:n]
            bindings = Dict("dx" => dx)
            got = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                           ghost_width=1,
                                           boundary_policy=Dict("kind" => "one_sided_extrapolation",
                                                                "degree" => 3))
            # Centered FD on i^3: ((i+1)^3 - (i-1)^3) / (2dx) = (6i^2 + 2)/(2dx).
            ref = Float64[(6.0 * i^2 + 2.0) / (2.0 * dx) for i in 1:n]
            @test maximum(abs.(got .- ref)) < 1e-10
        end

        @testset "one_sided_extrapolation: extrapolate alias defaults degree=1" begin
            n = 8
            dx = 0.1
            u = Float64[1.5 * i + 0.5 for i in 1:n]
            bindings = Dict("dx" => dx)
            got = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                           ghost_width=1,
                                           boundary_policy="extrapolate")
            @test all(g -> isapprox(g, 1.5 / dx; atol=1e-10), got)
        end

        @testset "prescribed: caller-supplied ghost values" begin
            n = 8
            dx = 0.1
            u = collect(Float64, 1:n)
            bindings = Dict("dx" => dx)
            calls = Tuple{Symbol,Int}[]
            prescribe = (side, k) -> begin
                push!(calls, (side, k))
                # Ghost cell k beyond the boundary at cell index 1-k (left)
                # or n+k (right): supply the linear extension of u.
                return side === :left ? Float64(1 - k) : Float64(n + k)
            end
            got = apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                           ghost_width=1,
                                           boundary_policy="prescribed",
                                           prescribe=prescribe)
            # Linear u[i] = i + supplied linear ghosts → exact 1/dx everywhere.
            @test all(g -> isapprox(g, 1.0 / dx; atol=1e-10), got)
            @test (:left, 1) in calls
            @test (:right, 1) in calls
        end

        @testset "prescribed: ghosted alias requires prescribe" begin
            n = 8
            dx = 0.1
            u = collect(Float64, 1:n)
            bindings = Dict("dx" => dx)
            err = try
                apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                          ghost_width=1,
                                          boundary_policy="ghosted")
                nothing
            catch e
                e
            end
            @test err isa MMSEvaluatorError
            @test err.code == "E_MMS_BAD_FIXTURE"
        end

        @testset "ghost_width too small for stencil offset" begin
            wide_stencil = [
                Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => -2),
                     "coeff" => Dict("op" => "/", "args" =>
                         Any[1, Dict("op" => "*", "args" => Any[12, "dx"])])),
                Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => -1),
                     "coeff" => Dict("op" => "/", "args" =>
                         Any[-8, Dict("op" => "*", "args" => Any[12, "dx"])])),
                Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => 1),
                     "coeff" => Dict("op" => "/", "args" =>
                         Any[8, Dict("op" => "*", "args" => Any[12, "dx"])])),
                Dict("selector" => Dict("kind" => "cartesian", "axis" => "x", "offset" => 2),
                     "coeff" => Dict("op" => "/", "args" =>
                         Any[-1, Dict("op" => "*", "args" => Any[12, "dx"])])),
            ]
            n = 16
            dx = 1.0 / n
            u = [sin(2π * (i - 0.5) * dx) for i in 1:n]
            bindings = Dict("dx" => dx)
            err = try
                apply_stencil_ghosted_1d(wide_stencil, u, bindings;
                                          ghost_width=1,
                                          boundary_policy="periodic")
                nothing
            catch e
                e
            end
            @test err isa MMSEvaluatorError
            @test err.code == "E_GHOST_WIDTH_TOO_SMALL"
        end

        @testset "panel_dispatch is recognised but unsupported" begin
            n = 8
            dx = 0.1
            u = collect(Float64, 1:n)
            bindings = Dict("dx" => dx)
            err = try
                apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                          ghost_width=1,
                                          boundary_policy=Dict(
                                              "kind" => "panel_dispatch",
                                              "interior" => "dist",
                                              "boundary" => "dist_bnd"))
                nothing
            catch e
                e
            end
            @test err isa MMSEvaluatorError
            @test err.code == "E_GHOST_FILL_UNSUPPORTED"
        end

        @testset "unknown boundary_policy kind" begin
            n = 8
            dx = 0.1
            u = collect(Float64, 1:n)
            bindings = Dict("dx" => dx)
            err = try
                apply_stencil_ghosted_1d(centered_fd, u, bindings;
                                          ghost_width=1,
                                          boundary_policy="not_a_real_kind")
                nothing
            catch e
                e
            end
            @test err isa MMSEvaluatorError
        end

        @testset "negative ghost_width" begin
            n = 8
            dx = 0.1
            u = collect(Float64, 1:n)
            bindings = Dict("dx" => dx)
            @test_throws MMSEvaluatorError apply_stencil_ghosted_1d(
                centered_fd, u, bindings;
                ghost_width=-1, boundary_policy="periodic")
        end
    end
end
