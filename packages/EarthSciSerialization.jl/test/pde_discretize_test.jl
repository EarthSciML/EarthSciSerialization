# Tests for the PDE discretization pipeline (esm-2qw):
#   EarthSciSerialization.discretize(::PDESystem, ::AbstractCurvilinearGrid)
#
# This file exercises the pipeline against a minimal inline `PDETestCartesianGrid`
# — identity metric, identity coordinate Jacobian, periodic neighbor wrap. The
# discretizer's chain-rule path collapses to plain centered FD on this grid, so
# MMS results match the classical 5-point Laplacian and centered gradient. The
# stub keeps these unit tests fast and dependency-free.
#
# The end-to-end integration against REAL EarthSciDiscretizations grids
# (`LatLonGrid`, `CubedSphereGrid`) lives in
# `pde_discretize_esd_integration_test.jl` (ess-d1e).

using Test
using EarthSciSerialization
using EarthSciSerialization: AbstractCurvilinearGrid, n_cells, n_dims, axis_names,
    cell_centers, cell_widths, cell_volume, neighbor_indices, boundary_mask,
    metric_g, metric_ginv, metric_jacobian, metric_dgij_dxk,
    coord_jacobian, coord_jacobian_second
using ModelingToolkit
using ModelingToolkit: t_nounits as t_, D_nounits as D_, Differential, PDESystem
using Symbolics
using DomainSets: Interval
using OrdinaryDiffEqTsit5

# Reuse the test grid from grid_assembly_test.jl. To avoid duplicate-method
# warnings when both files are run in the same `@testset`, we define a fresh
# struct under a different name and only override the trait methods this
# test actually consumes.

struct PDETestCartesianGrid <: AbstractCurvilinearGrid
    Nx::Int
    Ny::Int
    Lx::Float64
    Ly::Float64
end

_pflat(g::PDETestCartesianGrid, i::Int, j::Int) = i + (j - 1) * g.Nx
_pwrap(idx::Int, n::Int) = mod(idx - 1, n) + 1

EarthSciSerialization.n_cells(g::PDETestCartesianGrid) = g.Nx * g.Ny
EarthSciSerialization.n_dims(g::PDETestCartesianGrid)  = 2
EarthSciSerialization.axis_names(g::PDETestCartesianGrid) = (:x, :y)

function EarthSciSerialization.cell_centers(g::PDETestCartesianGrid, axis::Symbol)
    N = n_cells(g)
    out = Vector{Float64}(undef, N)
    dx = g.Lx / g.Nx; dy = g.Ly / g.Ny
    for j in 1:g.Ny, i in 1:g.Nx
        c = _pflat(g, i, j)
        out[c] = axis === :x ? (i - 0.5) * dx :
                 axis === :y ? (j - 0.5) * dy :
                 throw(ArgumentError("unknown axis $axis"))
    end
    return out
end

function EarthSciSerialization.cell_widths(g::PDETestCartesianGrid, axis::Symbol)
    N = n_cells(g)
    w = axis === :x ? g.Lx / g.Nx :
        axis === :y ? g.Ly / g.Ny :
        throw(ArgumentError("unknown axis $axis"))
    return fill(w, N)
end

function EarthSciSerialization.cell_volume(g::PDETestCartesianGrid)
    dx = g.Lx / g.Nx; dy = g.Ly / g.Ny
    return fill(dx * dy, n_cells(g))
end

function EarthSciSerialization.neighbor_indices(g::PDETestCartesianGrid, axis::Symbol, offset::Int)
    N = n_cells(g); out = Vector{Int}(undef, N)
    for j in 1:g.Ny, i in 1:g.Nx
        c = _pflat(g, i, j)
        if axis === :x
            ni = _pwrap(i + offset, g.Nx); out[c] = _pflat(g, ni, j)
        elseif axis === :y
            nj = _pwrap(j + offset, g.Ny); out[c] = _pflat(g, i, nj)
        else
            throw(ArgumentError("unknown axis $axis"))
        end
    end
    return out
end

EarthSciSerialization.boundary_mask(g::PDETestCartesianGrid, ::Symbol, ::Symbol) =
    falses(n_cells(g))

function EarthSciSerialization.metric_g(g::PDETestCartesianGrid)
    N = n_cells(g); out = zeros(N, 2, 2)
    @inbounds for c in 1:N; out[c, 1, 1] = 1.0; out[c, 2, 2] = 1.0; end
    return out
end
EarthSciSerialization.metric_ginv(g::PDETestCartesianGrid) = metric_g(g)
EarthSciSerialization.metric_jacobian(g::PDETestCartesianGrid) = ones(n_cells(g))
EarthSciSerialization.metric_dgij_dxk(g::PDETestCartesianGrid) = zeros(n_cells(g), 2, 2, 2)

function EarthSciSerialization.coord_jacobian(g::PDETestCartesianGrid, ::Symbol)
    N = n_cells(g); out = zeros(N, 2, 2)
    @inbounds for c in 1:N; out[c, 1, 1] = 1.0; out[c, 2, 2] = 1.0; end
    return out
end
EarthSciSerialization.coord_jacobian_second(g::PDETestCartesianGrid, ::Symbol) =
    zeros(n_cells(g), 2, 2, 2)

# ---------------------------------------------------------------------------

@testset "discretize(PDESystem, AbstractCurvilinearGrid)" begin

    @testset "Multi-variable coupled system" begin
        @parameters x y
        @variables u(..) v(..)

        # Trivial decoupled-from-space system:  du/dt = v,  dv/dt = -u
        eq1 = D_(u(t_, x, y)) ~ v(t_, x, y)
        eq2 = D_(v(t_, x, y)) ~ -u(t_, x, y)
        bcs = [
            u(0, x, y) ~ cos(y),
            v(0, x, y) ~ 0.0,
        ]
        domains = [
            t_ ∈ Interval(0.0, 1.0),
            x  ∈ Interval(0.0, 2π),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys = PDESystem(
            [eq1, eq2], bcs, domains,
            [t_, x, y], [u(t_, x, y), v(t_, x, y)],
        )

        grid = PDETestCartesianGrid(8, 8, 2π, 2π)
        prob = EarthSciSerialization.discretize(sys, grid; xi_axis=:x, eta_axis=:y)

        @test prob isa ODEProblem
        @test length(prob.u0) == 2 * 64

        sol = solve(prob, Tsit5())
        @test sol.retcode == ReturnCode.Success
    end

    @testset "Laplacian of a constant is zero" begin
        @parameters x y
        @variables u(..)
        Dx = Differential(x); Dy = Differential(y)

        eq  = [D_(u(t_, x, y)) ~ Dx(Dx(u(t_, x, y))) + Dy(Dy(u(t_, x, y)))]
        bcs = [u(0, x, y) ~ 42.0]
        domains = [
            t_ ∈ Interval(0.0, 1.0),
            x  ∈ Interval(0.0, 2π),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys = PDESystem(eq, bcs, domains, [t_, x, y], [u(t_, x, y)])

        grid = PDETestCartesianGrid(16, 16, 2π, 2π)
        prob = EarthSciSerialization.discretize(sys, grid; xi_axis=:x, eta_axis=:y)
        du = prob.f(prob.u0, prob.p, 0.0)
        @test maximum(abs, du) < 1e-10
    end

    @testset "Laplacian MMS: φ = sin(x)·sin(y), ∇²φ = -2 sin(x) sin(y)" begin
        # mtkcompile may reorder/eliminate state, so we compare against the
        # ordering-invariant `du[k] ≈ -2 u0[k]` relation that holds at every
        # cell — independent of how the compiled state is laid out.
        function _err(N)
            @parameters x y
            @variables u(..)
            Dx = Differential(x); Dy = Differential(y)

            eq  = [D_(u(t_, x, y)) ~ Dx(Dx(u(t_, x, y))) + Dy(Dy(u(t_, x, y)))]
            bcs = [u(0, x, y) ~ sin(x) * sin(y)]
            domains = [
                t_ ∈ Interval(0.0, 0.0),
                x  ∈ Interval(0.0, 2π),
                y  ∈ Interval(0.0, 2π),
            ]
            @named sys = PDESystem(eq, bcs, domains, [t_, x, y], [u(t_, x, y)])

            grid = PDETestCartesianGrid(N, N, 2π, 2π)
            prob = EarthSciSerialization.discretize(sys, grid; xi_axis=:x, eta_axis=:y)
            du = prob.f(prob.u0, prob.p, 0.0)
            # ∇²(sin x · sin y) = -2 sin x sin y, so the per-cell relation
            # du ≈ -2 · u0 holds up to O(h²) regardless of state ordering.
            return maximum(abs.(du .+ 2 .* prob.u0))
        end
        e16 = _err(16); e32 = _err(32)
        @test e16 < 0.05
        @test e32 < e16 / 3.5     # centered FD is O(h²) → ratio ≈ 4
    end

    @testset "Mixed derivative: nonzero on sin(x)·sin(y)" begin
        @parameters x y
        @variables u(..)
        Dx = Differential(x); Dy = Differential(y)

        eq  = [D_(u(t_, x, y)) ~ Dx(Dy(u(t_, x, y)))]
        bcs = [u(0, x, y) ~ sin(x) * sin(y)]
        domains = [
            t_ ∈ Interval(0.0, 0.01),
            x  ∈ Interval(0.0, 2π),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys = PDESystem(eq, bcs, domains, [t_, x, y], [u(t_, x, y)])

        grid = PDETestCartesianGrid(16, 16, 2π, 2π)
        prob = EarthSciSerialization.discretize(sys, grid; xi_axis=:x, eta_axis=:y)
        du = prob.f(prob.u0, prob.p, 0.0)
        # ∂²(sin(x)sin(y))/∂x∂y = cos(x)·cos(y) — non-trivial
        @test !all(iszero, du)
        @test maximum(abs.(du)) > 0.5
    end

    @testset "Nonlinear term: D(u^2)/Dx" begin
        @parameters x y
        @variables u(..)
        Dx = Differential(x)

        eq  = [D_(u(t_, x, y)) ~ Dx(u(t_, x, y)^2)]
        bcs = [u(0, x, y) ~ 1.0 + 0.1 * cos(x)]
        domains = [
            t_ ∈ Interval(0.0, 0.01),
            x  ∈ Interval(0.0, 2π),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys = PDESystem(eq, bcs, domains, [t_, x, y], [u(t_, x, y)])

        grid = PDETestCartesianGrid(8, 8, 2π, 2π)
        prob = EarthSciSerialization.discretize(sys, grid; xi_axis=:x, eta_axis=:y)
        du = prob.f(prob.u0, prob.p, 0.0)
        # Nonlinearity must be preserved — du should be nonzero.
        @test !all(iszero, du)
    end

    @testset "IC identification with multiple BCs" begin
        @parameters x y
        @variables u(..)
        Dx = Differential(x); Dy = Differential(y)

        eq = [D_(u(t_, x, y)) ~ 0.01 * (Dx(Dx(u(t_, x, y))) + Dy(Dy(u(t_, x, y))))]
        # First BC has the form `u(t, 0, y) ~ 0.0` — it should NOT be matched
        # as the IC because its t-arg is the symbol `t`, not the literal `0`.
        # Second BC `u(0, x, y) ~ cos(y)` should be picked.
        bcs = [
            u(t_, 0.0, y) ~ 0.0,
            u(0,    x,  y) ~ cos(y),
        ]
        domains = [
            t_ ∈ Interval(0.0, 1.0),
            x  ∈ Interval(0.0, 2π),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys = PDESystem(eq, bcs, domains, [t_, x, y], [u(t_, x, y)])

        grid = PDETestCartesianGrid(8, 8, 2π, 2π)
        prob = EarthSciSerialization.discretize(sys, grid; xi_axis=:x, eta_axis=:y)
        # Should use the cos(y) IC, not the zero BC: u0 spans cos(y) on the grid,
        # whose max value reaches ≈1 (the BC `u(t, 0, y) ~ 0.0` would zero u0).
        @test maximum(prob.u0) > 0.5
    end
end

# ---------------------------------------------------------------------------
# Boundary-condition handling on non-periodic axes (ess-gp3).
#
# The pipeline applies `sys.bcs` Dirichlet/Neumann BCs at cells whose
# `neighbor_indices` returns the sentinel 0. The reference grid below has
# non-periodic x and (optionally) non-periodic y so the sentinel exposes a
# real boundary to the discretizer.
# ---------------------------------------------------------------------------

struct PDETestBoundedGrid <: AbstractCurvilinearGrid
    Nx::Int
    Ny::Int
    Lx::Float64
    Ly::Float64
    periodic_x::Bool
    periodic_y::Bool
end

_bflat(g::PDETestBoundedGrid, i::Int, j::Int) = i + (j - 1) * g.Nx
_bwrap(idx::Int, n::Int) = mod(idx - 1, n) + 1

EarthSciSerialization.n_cells(g::PDETestBoundedGrid) = g.Nx * g.Ny
EarthSciSerialization.n_dims(g::PDETestBoundedGrid)  = 2
EarthSciSerialization.axis_names(g::PDETestBoundedGrid) = (:x, :y)

function EarthSciSerialization.cell_centers(g::PDETestBoundedGrid, axis::Symbol)
    N = n_cells(g)
    out = Vector{Float64}(undef, N)
    dx = g.Lx / g.Nx; dy = g.Ly / g.Ny
    for j in 1:g.Ny, i in 1:g.Nx
        c = _bflat(g, i, j)
        out[c] = axis === :x ? (i - 0.5) * dx :
                 axis === :y ? (j - 0.5) * dy :
                 throw(ArgumentError("unknown axis $axis"))
    end
    return out
end

function EarthSciSerialization.cell_widths(g::PDETestBoundedGrid, axis::Symbol)
    N = n_cells(g)
    w = axis === :x ? g.Lx / g.Nx :
        axis === :y ? g.Ly / g.Ny :
        throw(ArgumentError("unknown axis $axis"))
    return fill(w, N)
end

function EarthSciSerialization.cell_volume(g::PDETestBoundedGrid)
    dx = g.Lx / g.Nx; dy = g.Ly / g.Ny
    return fill(dx * dy, n_cells(g))
end

# `neighbor_indices` returns the sentinel `0` on the side that is NOT periodic,
# exactly as a real bounded-domain grid would. Periodic axes wrap.
function EarthSciSerialization.neighbor_indices(g::PDETestBoundedGrid, axis::Symbol, offset::Int)
    N = n_cells(g); out = Vector{Int}(undef, N)
    for j in 1:g.Ny, i in 1:g.Nx
        c = _bflat(g, i, j)
        if axis === :x
            ni = i + offset
            if g.periodic_x
                ni = _bwrap(ni, g.Nx)
                out[c] = _bflat(g, ni, j)
            else
                out[c] = (ni < 1 || ni > g.Nx) ? 0 : _bflat(g, ni, j)
            end
        elseif axis === :y
            nj = j + offset
            if g.periodic_y
                nj = _bwrap(nj, g.Ny)
                out[c] = _bflat(g, i, nj)
            else
                out[c] = (nj < 1 || nj > g.Ny) ? 0 : _bflat(g, i, nj)
            end
        else
            throw(ArgumentError("unknown axis $axis"))
        end
    end
    return out
end

EarthSciSerialization.boundary_mask(g::PDETestBoundedGrid, ::Symbol, ::Symbol) =
    falses(n_cells(g))

function EarthSciSerialization.metric_g(g::PDETestBoundedGrid)
    N = n_cells(g); out = zeros(N, 2, 2)
    @inbounds for c in 1:N; out[c, 1, 1] = 1.0; out[c, 2, 2] = 1.0; end
    return out
end
EarthSciSerialization.metric_ginv(g::PDETestBoundedGrid) = metric_g(g)
EarthSciSerialization.metric_jacobian(g::PDETestBoundedGrid) = ones(n_cells(g))
EarthSciSerialization.metric_dgij_dxk(g::PDETestBoundedGrid) = zeros(n_cells(g), 2, 2, 2)

function EarthSciSerialization.coord_jacobian(g::PDETestBoundedGrid, ::Symbol)
    N = n_cells(g); out = zeros(N, 2, 2)
    @inbounds for c in 1:N; out[c, 1, 1] = 1.0; out[c, 2, 2] = 1.0; end
    return out
end
EarthSciSerialization.coord_jacobian_second(g::PDETestBoundedGrid, ::Symbol) =
    zeros(n_cells(g), 2, 2, 2)

@testset "discretize(PDESystem) — non-periodic BCs (ess-gp3)" begin

    @testset "Dirichlet BC: zero-boundary MMS, sin(πx/L)·cos(y)" begin
        # ∂²u/∂x² + ∂²u/∂y² = -((π/L)² + 1) · u  for u = sin(πx/L)·cos(y).
        # With u(0, y) = u(L, y) = 0 Dirichlet BCs the cell-centered ghost
        # `u_ghost = 2·g - u_C` recovers an O(h²) stencil at the boundary
        # cells; without BCs the self-fallback gives O(1) residual there.
        L = π
        function dirichlet_mms_err(N)
            @parameters x y
            @variables u(..)
            Dx = Differential(x); Dy = Differential(y)
            eq  = [D_(u(t_, x, y)) ~ Dx(Dx(u(t_, x, y))) + Dy(Dy(u(t_, x, y)))]
            bcs = [
                u(0, x, y)      ~ sin(π * x / L) * cos(y),
                u(t_, 0.0, y)   ~ 0.0,
                u(t_, L,   y)   ~ 0.0,
            ]
            domains = [
                t_ ∈ Interval(0.0, 0.0),
                x  ∈ Interval(0.0, L),
                y  ∈ Interval(0.0, 2π),
            ]
            @named sys = PDESystem(eq, bcs, domains,
                                    [t_, x, y], [u(t_, x, y)])
            grid = PDETestBoundedGrid(N, N, L, 2π, false, true)
            prob = EarthSciSerialization.discretize(
                sys, grid; xi_axis = :x, eta_axis = :y)
            du = prob.f(prob.u0, prob.p, 0.0)
            return maximum(abs.(du .+ ((π/L)^2 + 1.0) .* prob.u0))
        end
        e16 = dirichlet_mms_err(16)
        e32 = dirichlet_mms_err(32)
        order = log2(e16 / e32)
        @info "Dirichlet MMS convergence" e16 e32 order
        @test e16 < 0.1
        @test e32 < e16
        @test order > 1.7        # O(h²) including boundary cells
    end

    @testset "Dirichlet vs no-BC: boundary residual differs" begin
        # Same MMS field. WITHOUT Dirichlet BCs the legacy self-fallback fires
        # at the x boundary; WITH BCs the discretizer uses ghost values from
        # `sys.bcs`. The two paths MUST produce different residuals at the
        # boundary cells.
        L = π
        @parameters x y
        @variables u(..)
        Dx = Differential(x); Dy = Differential(y)
        eq  = [D_(u(t_, x, y)) ~ Dx(Dx(u(t_, x, y))) + Dy(Dy(u(t_, x, y)))]
        ic  = u(0, x, y) ~ sin(π * x / L) * cos(y)
        bcs_no  = [ic]
        bcs_yes = [ic,
                   u(t_, 0.0, y) ~ 0.0,
                   u(t_, L,   y) ~ 0.0]
        domains = [
            t_ ∈ Interval(0.0, 0.0),
            x  ∈ Interval(0.0, L),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys_no  = PDESystem(eq, bcs_no,  domains,
                                    [t_, x, y], [u(t_, x, y)])
        @named sys_yes = PDESystem(eq, bcs_yes, domains,
                                    [t_, x, y], [u(t_, x, y)])
        grid = PDETestBoundedGrid(16, 16, L, 2π, false, true)
        prob_no  = EarthSciSerialization.discretize(sys_no,  grid;
                                                     xi_axis = :x, eta_axis = :y)
        prob_yes = EarthSciSerialization.discretize(sys_yes, grid;
                                                     xi_axis = :x, eta_axis = :y)
        du_no  = prob_no.f(prob_no.u0,   prob_no.p,  0.0)
        du_yes = prob_yes.f(prob_yes.u0, prob_yes.p, 0.0)
        analytic = -((π/L)^2 + 1.0) .* prob_no.u0
        res_no  = maximum(abs.(du_no  .- analytic))
        res_yes = maximum(abs.(du_yes .- analytic))
        @info "BC vs no-BC max residual" res_no res_yes
        # Without BC the self-fallback dominates the boundary cells; with BC
        # the residual collapses to the interior O(h²) error.
        @test res_yes < 0.5 * res_no
    end

    @testset "Neumann (zero-flux): constant field has zero Laplacian" begin
        # Zero-Neumann ghost `u_W = u_C` makes (u_E - 2u_C + u_W)/dx² collapse
        # to (u_E - u_C)/dx²; on a constant field every neighbor equals u_C
        # and the Laplacian is exactly 0 at every cell, boundaries included.
        L = π
        @parameters x y
        @variables u(..)
        Dx = Differential(x); Dy = Differential(y)
        eq  = [D_(u(t_, x, y)) ~ Dx(Dx(u(t_, x, y))) + Dy(Dy(u(t_, x, y)))]
        bcs = [
            u(0, x, y)               ~ 7.0,
            Dx(u(t_, 0.0, y))        ~ 0.0,
            Dx(u(t_, L,   y))        ~ 0.0,
        ]
        domains = [
            t_ ∈ Interval(0.0, 1.0),
            x  ∈ Interval(0.0, L),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys = PDESystem(eq, bcs, domains,
                                [t_, x, y], [u(t_, x, y)])
        grid = PDETestBoundedGrid(8, 8, L, 2π, false, true)
        prob = EarthSciSerialization.discretize(sys, grid;
                                                 xi_axis = :x, eta_axis = :y)
        du = prob.f(prob.u0, prob.p, 0.0)
        @test maximum(abs, du) < 1e-10
    end

    @testset "Non-zero Dirichlet: end-to-end heat solve" begin
        # ∂u/∂t = ∂²u/∂x² on x ∈ [0, π], y periodic.
        # u(t, 0, y) = u(t, π, y) = 0, u(0, x, y) = sin(x).
        # Analytic: u(x, t) = exp(-t)·sin(x). Compare against analytic at T.
        L = π; T = 0.25
        @parameters x y
        @variables u(..)
        Dx = Differential(x)
        eq  = [D_(u(t_, x, y)) ~ Dx(Dx(u(t_, x, y)))]
        bcs = [
            u(0, x, y)    ~ sin(x),
            u(t_, 0.0, y) ~ 0.0,
            u(t_, L,   y) ~ 0.0,
        ]
        domains = [
            t_ ∈ Interval(0.0, T),
            x  ∈ Interval(0.0, L),
            y  ∈ Interval(0.0, 2π),
        ]
        @named sys = PDESystem(eq, bcs, domains,
                                [t_, x, y], [u(t_, x, y)])
        grid = PDETestBoundedGrid(32, 8, L, 2π, false, true)
        prob = EarthSciSerialization.discretize(sys, grid;
                                                 xi_axis = :x, eta_axis = :y)
        sol = solve(prob, Tsit5(); abstol = 1e-10, reltol = 1e-10)
        @test sol.retcode == ReturnCode.Success
        decay = exp(-T)
        @test decay < 0.9
        err = maximum(abs.(sol.u[end] .- decay .* prob.u0))
        @info "Dirichlet heat-equation end-to-end" decay err
        @test err < 5e-3
    end
end
