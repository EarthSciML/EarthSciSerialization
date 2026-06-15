# End-to-end pathway test for tree_walk simulation runner (esm-qrj).
#
# Asserts tree_walk works as an OFFICIAL ESS Julia simulation runner:
# the model travels parse → discretize → build_evaluator → solve.

using Test
using JSON3
using EarthSciSerialization
import OrdinaryDiffEqTsit5

const _E2E_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))

@testset "tree_walk e2e: parse → discretize → build_evaluator → solve (esm-qrj)" begin
    fixture = joinpath(_E2E_REPO_ROOT, "tests", "conformance", "discretize",
                       "inputs", "scalar_ode.esm")
    @test isfile(fixture)

    esm = JSON3.read(read(fixture, String))
    discretized = discretize(esm)
    @test discretized isa Dict{String,Any}
    @test discretized["metadata"]["system_class"] == "ode"

    f!, u0, p, tspan_default, var_map = build_evaluator(discretized)
    @test haskey(var_map, "x")
    @test length(u0) == 1
    @test u0[var_map["x"]] == 1.0
    @test p.k == 0.5
    @test tspan_default == (0.0, 1.0)

    prob = OrdinaryDiffEqTsit5.ODEProblem(f!, u0, (0.0, 4.0), p)
    sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                    reltol=1e-9, abstol=1e-11)
    @test isapprox(sol.u[end][var_map["x"]], exp(-2.0); rtol=1e-7)
end

@testset "tree_walk e2e: 1D PDE → discretize(lift_1d_arrayop=true) → build_evaluator" begin
    # A 1D periodic advection document whose grad op is rewritten by a
    # centered-difference rule with the 1/(2·dx) coefficient. With
    # lift_1d_arrayop=true the equation lifts to arrayop form and the
    # tree-walk evaluator expands it per cell, so one f! evaluation must
    # reproduce the centered stencil exactly.
    n = 8
    dx = 1.0 / n
    esm = Dict{String,Any}(
        "esm"      => "0.4.0",
        "metadata" => Dict{String,Any}("name" => "advection_1d_lift"),
        "grids"    => Dict{String,Any}(
            "gx" => Dict{String,Any}(
                "family"     => "cartesian",
                "dimensions" => Any[
                    Dict{String,Any}("name" => "i", "size" => n,
                                      "periodic" => true, "spacing" => "uniform"),
                ],
            ),
        ),
        "rules" => Any[
            Dict{String,Any}(
                "name"    => "centered_grad",
                "pattern" => Dict{String,Any}("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                "replacement" => Dict{String,Any}(
                    "op"   => "/",
                    "args" => Any[
                        Dict{String,Any}("op" => "-", "args" => Any[
                            Dict{String,Any}("op" => "index", "args" => Any[
                                "\$u", Dict{String,Any}("op" => "+", "args" => Any["\$x", 1])]),
                            Dict{String,Any}("op" => "index", "args" => Any[
                                "\$u", Dict{String,Any}("op" => "-", "args" => Any["\$x", 1])]),
                        ]),
                        Dict{String,Any}("op" => "*", "args" => Any[2, "dx"]),
                    ],
                ),
            ),
        ],
        "models" => Dict{String,Any}(
            "M" => Dict{String,Any}(
                "grid" => "gx",
                "variables" => Dict{String,Any}(
                    "u" => Dict{String,Any}(
                        "type" => "state", "default" => 0.0, "units" => "1",
                        "shape" => Any["i"], "location" => "cell_center",
                    ),
                    "dx" => Dict{String,Any}(
                        "type" => "parameter", "default" => dx, "units" => "1",
                    ),
                ),
                "equations" => Any[
                    Dict{String,Any}(
                        "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                        "rhs" => Dict{String,Any}("op" => "grad", "args" => Any["u"], "dim" => "i"),
                    ),
                ],
            ),
        ),
    )

    discretized = discretize(esm; lift_1d_arrayop=true)
    @test discretized["models"]["M"]["equations"][1]["lhs"]["op"] == "arrayop"

    f!, u0, p, _tspan, var_map = build_evaluator(discretized)
    @test length(u0) == n
    cell_x(i) = (i - 0.5) * dx
    for i in 1:n
        u0[var_map["u[$i]"]] = sin(2π * cell_x(i))
    end
    du = similar(u0)
    f!(du, u0, p, 0.0)

    wrap(i) = mod(i - 1, n) + 1
    for i in 1:n
        expected = (sin(2π * cell_x(wrap(i + 1))) - sin(2π * cell_x(wrap(i - 1)))) / (2 * dx)
        @test isapprox(du[var_map["u[$i]"]], expected; rtol=1e-12, atol=1e-12)
    end
end

@testset "tree_walk e2e: bounded 1D with dirichlet + neumann BCs (ess-gp3)" begin
    # D(u) = grad(u) → -u[i-1] + u[i+1]; dirichlet 3 at imin, zero-flux at
    # imax. One f! evaluation must show the ghost-value substitution at the
    # left boundary and the zero-flux mirror at the right, exactly.
    n = 8
    esm = Dict{String,Any}(
        "esm"      => "0.4.0",
        "metadata" => Dict{String,Any}("name" => "bounded_1d_bc"),
        "grids"    => Dict{String,Any}(
            "gx" => Dict{String,Any}(
                "family"     => "cartesian",
                "dimensions" => Any[Dict{String,Any}(
                    "name" => "i", "size" => n,
                    "periodic" => false, "spacing" => "uniform")],
            ),
        ),
        "rules" => Any[Dict{String,Any}(
            "name"    => "centered_grad",
            "pattern" => Dict{String,Any}("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
            "replacement" => Dict{String,Any}("op" => "+", "args" => Any[
                Dict{String,Any}("op" => "-", "args" => Any[
                    Dict{String,Any}("op" => "index", "args" => Any[
                        "\$u", Dict{String,Any}("op" => "-", "args" => Any["\$x", 1])])]),
                Dict{String,Any}("op" => "index", "args" => Any[
                    "\$u", Dict{String,Any}("op" => "+", "args" => Any["\$x", 1])]),
            ]),
        )],
        "models" => Dict{String,Any}(
            "M" => Dict{String,Any}(
                "grid" => "gx",
                "variables" => Dict{String,Any}(
                    "u" => Dict{String,Any}(
                        "type" => "state", "default" => 0.0, "units" => "1",
                        "shape" => Any["i"], "location" => "cell_center")),
                "equations" => Any[Dict{String,Any}(
                    "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                    "rhs" => Dict{String,Any}("op" => "grad", "args" => Any["u"], "dim" => "i"))],
                "boundary_conditions" => Dict{String,Any}(
                    "left"  => Dict{String,Any}("variable" => "u", "kind" => "dirichlet",
                                                 "side" => "imin", "value" => 3),
                    "right" => Dict{String,Any}("variable" => "u", "kind" => "neumann",
                                                 "side" => "imax", "value" => 0)),
            ),
        ),
    )

    d = discretize(esm; lift_1d_arrayop=true)
    f!, u0, p, _ts, vm = build_evaluator(d)
    for i in 1:n
        u0[vm["u[$i]"]] = Float64(i)^2
    end
    du = similar(u0)
    f!(du, u0, p, 0.0)
    u(i) = Float64(i)^2
    expect(i) = i == 1 ? -3.0 + u(2) :
                i == n ? -u(n - 1) + u(n) :
                -u(i - 1) + u(i + 1)
    for i in 1:n
        @test du[vm["u[$i]"]] == expect(i)
    end
end

@testset "tree_walk e2e: two-domain interface BC value-continuity (ess-x76)" begin
    # Two 1D heat domains (u on [0,1], v on [1,2]) joined at x=1 by an
    # interface BC. Both read a diffusion stencil u[i-1] - 2*u[i] + u[i+1]
    # where the ghost outside the domain reads from the coupled variable.
    # N=4 cells each, D=1, dx=0.25 → D/dx²=16. The interface coupling
    # means the combined 8-cell system is equivalent to a single 8-cell heat
    # equation with Dirichlet BCs at both outer ends.
    n = 4
    dx = 0.25
    alpha = 1.0 / (dx * dx)   # D/dx² = 16
    esm = Dict{String,Any}(
        "esm"      => "0.4.0",
        "metadata" => Dict{String,Any}("name" => "interface_bc_e2e"),
        "grids"    => Dict{String,Any}(
            "g" => Dict{String,Any}(
                "family"     => "cartesian",
                "dimensions" => Any[Dict{String,Any}(
                    "name" => "i", "size" => n,
                    "periodic" => false, "spacing" => "uniform")],
            ),
        ),
        "models" => Dict{String,Any}(
            "M" => Dict{String,Any}(
                "grid" => "g",
                "variables" => Dict{String,Any}(
                    "u" => Dict{String,Any}(
                        "type" => "state", "default" => 0.0, "units" => "1",
                        "shape" => Any["i"], "location" => "cell_center"),
                    "v" => Dict{String,Any}(
                        "type" => "state", "default" => 0.0, "units" => "1",
                        "shape" => Any["i"], "location" => "cell_center")),
                "equations" => Any[
                    Dict{String,Any}(
                        "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                        "rhs" => Dict{String,Any}("op" => "*", "args" => Any[
                            alpha,
                            Dict{String,Any}("op" => "+", "args" => Any[
                                Dict{String,Any}("op" => "index", "args" => Any["u", Dict{String,Any}("op" => "-", "args" => Any["i", 1])]),
                                Dict{String,Any}("op" => "*", "args" => Any[-2, Dict{String,Any}("op" => "index", "args" => Any["u", "i"])]),
                                Dict{String,Any}("op" => "index", "args" => Any["u", Dict{String,Any}("op" => "+", "args" => Any["i", 1])])])])),
                    Dict{String,Any}(
                        "lhs" => Dict{String,Any}("op" => "D", "args" => Any["v"], "wrt" => "t"),
                        "rhs" => Dict{String,Any}("op" => "*", "args" => Any[
                            alpha,
                            Dict{String,Any}("op" => "+", "args" => Any[
                                Dict{String,Any}("op" => "index", "args" => Any["v", Dict{String,Any}("op" => "-", "args" => Any["i", 1])]),
                                Dict{String,Any}("op" => "*", "args" => Any[-2, Dict{String,Any}("op" => "index", "args" => Any["v", "i"])]),
                                Dict{String,Any}("op" => "index", "args" => Any["v", Dict{String,Any}("op" => "+", "args" => Any["i", 1])])])])),
                ],
                "boundary_conditions" => Dict{String,Any}(
                    "u_left"  => Dict{String,Any}("variable" => "u", "kind" => "dirichlet",
                                                   "side" => "imin", "value" => 0),
                    "u_right" => Dict{String,Any}("variable" => "u", "kind" => "interface",
                                                   "side" => "imax", "coupled_variable" => "v"),
                    "v_left"  => Dict{String,Any}("variable" => "v", "kind" => "interface",
                                                   "side" => "imin", "coupled_variable" => "u"),
                    "v_right" => Dict{String,Any}("variable" => "v", "kind" => "dirichlet",
                                                   "side" => "imax", "value" => 0)),
            ),
        ),
    )

    d = discretize(esm; lift_1d_arrayop=true)
    f!, u0, p, _ts, vm = build_evaluator(d)

    # IC: mode-1 sinusoid of the combined 8-cell system (cells i=1..8).
    # sin(i*π/9) for i=1..4 → u; i=5..8 → v.
    for i in 1:n
        u0[vm["u[$i]"]] = sin(i * π / 9)
        u0[vm["v[$i]"]] = sin((i + 4) * π / 9)
    end

    prob = OrdinaryDiffEqTsit5.ODEProblem(f!, u0, (0.0, 0.1), p)
    sol  = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                     reltol=1e-6, abstol=1e-8)

    # At t=0.1 the mode-1 eigenvalue λ₁=16*(2cos(π/9)-2) ≈ -1.9298 gives
    # decay factor exp(λ₁·0.1) ≈ 0.82450.
    decay = exp(16 * (2cos(π / 9) - 2) * 0.1)
    for i in 1:n
        @test isapprox(sol(0.1)[vm["u[$i]"]], sin(i * π / 9) * decay; rtol=1e-3)
        @test isapprox(sol(0.1)[vm["v[$i]"]], sin((i + 4) * π / 9) * decay; rtol=1e-3)
    end
end

@testset "tree_walk e2e: from_grid non-uniform stencil → build_evaluator with const_arrays (ess-d0a)" begin
    # 1D periodic domain [0, 2π) with smooth exponential stretching.
    # Equation: D(u)/Dt = ∂u/∂z discretized with stencil_gen spacing=from_grid.
    # Exact solution: u(z, t) = sin(z + t) (wave moving with unit speed).
    # Verify that const_arrays injection works and achieves 2nd-order convergence.
    function run_nonuniform(N)
        # Periodic smooth stretch: z_k = 2π*k/N + ε*sin(2π*k/N), k=0..N-1 (0-based)
        epsilon = 0.3
        z = [2π * k / N + epsilon * sin(2π * k / N) for k in 0:N-1]

        # Fornberg weights for each cell (1-based): 2-node stencil {i-1, i+1}
        stgfw_n1 = Vector{Float64}(undef, N)
        stgfw_p1 = Vector{Float64}(undef, N)
        for i in 1:N
            im1 = mod1(i - 1, N)
            ip1 = mod1(i + 1, N)
            z_im1 = z[im1] - (i == 1 ? 2π : 0.0)  # periodic left-boundary wrap
            z_ip1 = z[ip1] + (i == N ? 2π : 0.0)  # periodic right-boundary wrap
            w = EarthSciSerialization._fornberg_weights_float(z[i], [z_im1, z_ip1], 1)
            stgfw_n1[i] = w[1]
            stgfw_p1[i] = w[2]
        end

        esm = Dict{String,Any}(
            "esm"      => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "nonuniform_conv_$N"),
            "grids"    => Dict{String,Any}(
                "gz" => Dict{String,Any}(
                    "family"     => "cartesian",
                    "dimensions" => Any[Dict{String,Any}(
                        "name" => "z", "size" => N,
                        "periodic" => true, "spacing" => "nonuniform")],
                ),
            ),
            "discretizations" => Dict{String,Any}(
                "ng_grad" => Dict{String,Any}(
                    "applies_to"  => Dict{String,Any}(
                        "op" => "grad", "args" => Any["\$u"], "dim" => "\$z"),
                    "grid_family" => "cartesian",
                    "combine"     => "+",
                    "stencil_gen" => Dict{String,Any}(
                        "method"         => "fornberg",
                        "deriv_order"    => 1,
                        "accuracy_order" => 2,
                        "stagger"        => "centered",
                        "axis"           => "\$z",
                        "spacing"        => "from_grid",
                    ),
                ),
            ),
            "rules"  => Any[Dict{String,Any}(
                "name"    => "r",
                "pattern" => Dict{String,Any}("op" => "grad", "args" => Any["\$u"], "dim" => "\$z"),
                "use"     => "ng_grad",
            )],
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "grid"      => "gz",
                    "variables" => Dict{String,Any}(
                        "u" => Dict{String,Any}(
                            "type"     => "state",
                            "default"  => 0.0,
                            "units"    => "1",
                            "shape"    => Any["z"],
                            "location" => "cell_center",
                        ),
                    ),
                    "equations" => Any[Dict{String,Any}(
                        "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                        "rhs" => Dict{String,Any}("op" => "grad", "args" => Any["u"], "dim" => "z"),
                    )],
                ),
            ),
        )

        disc = EarthSciSerialization.discretize(esm; lift_1d_arrayop=true)
        f!, u0, _, _, var_map = EarthSciSerialization.build_evaluator(disc;
            const_arrays=Dict("__stgfw_z_2_n1" => stgfw_n1, "__stgfw_z_2_p1" => stgfw_p1))

        for i in 1:N
            u0[var_map["u[$i]"]] = sin(z[i])
        end

        prob = OrdinaryDiffEqTsit5.ODEProblem(f!, u0, (0.0, 0.1), nothing)
        sol  = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                         reltol=1e-9, abstol=1e-11)
        # Exact: u(z, 0.1) = sin(z + 0.1)
        return maximum(abs(sol.u[end][var_map["u[$i]"]] - sin(z[i] + 0.1)) for i in 1:N)
    end

    err16 = run_nonuniform(16)
    err32 = run_nonuniform(32)
    @test err16 < 1e-2          # sanity: non-trivial accuracy at N=16
    # 2nd-order: halving h → ~4× error reduction
    @test err16 / err32 > 3.0
end
