# Tests for esm-xom grid-metric assembly against the esm-a3z Grid trait.
#
# Test strategy: the ESD-side concrete grids (CubedSphereGrid, LatLonGrid)
# don't exist in ESS yet (follow-up bead) — so we exercise the trait +
# assembly against a minimal in-test `TestCartesianGrid` that implements
# Tier C and a trivial Tier M (identity metric, J=1). On such a grid the
# covariant Laplacian collapses to the classical 5-point finite-difference
# Laplacian and the gradient to centered differences, which we verify by
# MMS (manufactured solutions).

using Test
using EarthSciSerialization
using EarthSciSerialization: AbstractCurvilinearGrid, cell_centers, cell_volume,
    cell_widths, neighbor_indices, boundary_mask, n_cells, n_dims, axis_names,
    metric_g, metric_ginv, metric_jacobian, metric_dgij_dxk,
    coord_jacobian, coord_jacobian_second,
    precompute_laplacian_stencil, apply_laplacian!,
    precompute_gradient_stencil, apply_gradient!

# ---------------------------------------------------------------------------
# Minimal 2D periodic Cartesian test grid (Tier C + trivial Tier M).
#
# Cells are indexed in column-major order: flat = i + (j-1)*Nx  for i∈1:Nx, j∈1:Ny.
# Periodic neighbors wrap along both axes, so neighbor_indices never returns 0.
# ---------------------------------------------------------------------------

struct TestCartesianGrid <: AbstractCurvilinearGrid
    Nx::Int
    Ny::Int
    Lx::Float64
    Ly::Float64
end

_flat(g::TestCartesianGrid, i::Int, j::Int) = i + (j - 1) * g.Nx
_wrap(idx::Int, n::Int) = mod(idx - 1, n) + 1

EarthSciSerialization.n_cells(g::TestCartesianGrid) = g.Nx * g.Ny
EarthSciSerialization.n_dims(g::TestCartesianGrid)  = 2
EarthSciSerialization.axis_names(g::TestCartesianGrid) = (:x, :y)

function EarthSciSerialization.cell_centers(g::TestCartesianGrid, axis::Symbol)
    N = n_cells(g)
    out = Vector{Float64}(undef, N)
    dx = g.Lx / g.Nx; dy = g.Ly / g.Ny
    for j in 1:g.Ny, i in 1:g.Nx
        c = _flat(g, i, j)
        out[c] = axis === :x ? (i - 0.5) * dx :
                 axis === :y ? (j - 0.5) * dy :
                 throw(ArgumentError("unknown axis $axis"))
    end
    return out
end

function EarthSciSerialization.cell_widths(g::TestCartesianGrid, axis::Symbol)
    N = n_cells(g)
    w = axis === :x ? g.Lx / g.Nx :
        axis === :y ? g.Ly / g.Ny :
        throw(ArgumentError("unknown axis $axis"))
    return fill(w, N)
end

function EarthSciSerialization.cell_volume(g::TestCartesianGrid)
    dx = g.Lx / g.Nx; dy = g.Ly / g.Ny
    return fill(dx * dy, n_cells(g))
end

function EarthSciSerialization.neighbor_indices(g::TestCartesianGrid, axis::Symbol, offset::Int)
    N = n_cells(g)
    out = Vector{Int}(undef, N)
    for j in 1:g.Ny, i in 1:g.Nx
        c = _flat(g, i, j)
        if axis === :x
            ni = _wrap(i + offset, g.Nx)
            out[c] = _flat(g, ni, j)
        elseif axis === :y
            nj = _wrap(j + offset, g.Ny)
            out[c] = _flat(g, i, nj)
        else
            throw(ArgumentError("unknown axis $axis"))
        end
    end
    return out
end

function EarthSciSerialization.boundary_mask(g::TestCartesianGrid, axis::Symbol, side::Symbol)
    # Periodic: no cells are on a boundary in the topological sense.
    return falses(n_cells(g))
end

# Tier M — trivial identity metric for this uniform-Cartesian test grid.
function EarthSciSerialization.metric_g(g::TestCartesianGrid)
    N = n_cells(g)
    out = zeros(N, 2, 2)
    @inbounds for c in 1:N
        out[c, 1, 1] = 1.0
        out[c, 2, 2] = 1.0
    end
    return out
end
EarthSciSerialization.metric_ginv(g::TestCartesianGrid) = metric_g(g)         # identity self-inverse
EarthSciSerialization.metric_jacobian(g::TestCartesianGrid) = ones(n_cells(g))
EarthSciSerialization.metric_dgij_dxk(g::TestCartesianGrid) = zeros(n_cells(g), 2, 2, 2)

function EarthSciSerialization.coord_jacobian(g::TestCartesianGrid, target::Symbol)
    # For this identity-mapped grid, computational = physical, so ∂ξ/∂x is identity.
    N = n_cells(g)
    out = zeros(N, 2, 2)
    @inbounds for c in 1:N
        out[c, 1, 1] = 1.0
        out[c, 2, 2] = 1.0
    end
    return out
end
EarthSciSerialization.coord_jacobian_second(g::TestCartesianGrid, target::Symbol) =
    zeros(n_cells(g), 2, 2, 2)

# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

@testset "grid_assembly: AbstractGrid trait" begin
    g = TestCartesianGrid(8, 6, 2π, 2π)

    @test n_cells(g) == 48
    @test n_dims(g) == 2
    @test axis_names(g) === (:x, :y)

    xs = cell_centers(g, :x); ys = cell_centers(g, :y)
    @test length(xs) == 48 && length(ys) == 48
    @test cell_widths(g, :x) == fill(2π / 8, 48)

    @test size(metric_g(g))        == (48, 2, 2)
    @test size(metric_ginv(g))     == (48, 2, 2)
    @test length(metric_jacobian(g)) == 48
    @test size(metric_dgij_dxk(g)) == (48, 2, 2, 2)

    # Periodic neighbor sanity: for cell (1, j) the :x, -1 neighbor is (Nx, j).
    nE = neighbor_indices(g, :x, +1)
    nW = neighbor_indices(g, :x, -1)
    @test all(nE .> 0)
    @test all(nW .> 0)
end

@testset "grid_assembly: precompute_laplacian_stencil (identity metric)" begin
    g = TestCartesianGrid(16, 16, 2π, 2π)
    stencil = precompute_laplacian_stencil(g; xi_axis = :x, eta_axis = :y)

    @test size(stencil.weights)   == (n_cells(g), 9)
    @test size(stencil.neighbors) == (n_cells(g), 9)

    # On identity metric: cross-metric weights (NE, NW, SE, SW) must be zero,
    # and the 5-point classical Laplacian weights must match.
    dx = 2π / 16
    @test all(iszero, stencil.weights[:, 6:9])                       # no cross terms
    @test all(stencil.weights[:, 1] .≈ -2 / dx^2 - 2 / dx^2)          # center
    @test all(stencil.weights[:, 2] .≈  1 / dx^2)                    # east
    @test all(stencil.weights[:, 3] .≈  1 / dx^2)                    # west
    @test all(stencil.weights[:, 4] .≈  1 / dx^2)                    # north
    @test all(stencil.weights[:, 5] .≈  1 / dx^2)                    # south
end

@testset "grid_assembly: apply_laplacian! MMS convergence" begin
    # Method of manufactured solutions: φ = sin(x)·sin(y), ∇²φ = -2 sin(x) sin(y)
    function _err(N)
        g = TestCartesianGrid(N, N, 2π, 2π)
        stencil = precompute_laplacian_stencil(g; xi_axis = :x, eta_axis = :y)
        xs = cell_centers(g, :x); ys = cell_centers(g, :y)
        u = @. sin(xs) * sin(ys)
        analytical = -2 .* u
        du = similar(u)
        apply_laplacian!(du, u, stencil)
        return maximum(abs.(du .- analytical))
    end
    e32 = _err(32); e64 = _err(64)
    @test e32 < 0.05                           # coarse bound on 32²
    @test e64 < e32 / 3.5                      # centered FD is O(h²) → ratio ≈ 4
end

@testset "grid_assembly: apply_gradient! on identity target" begin
    g = TestCartesianGrid(32, 32, 2π, 2π)
    stencil = precompute_gradient_stencil(g, :xy; xi_axis = :x, eta_axis = :y)
    xs = cell_centers(g, :x); ys = cell_centers(g, :y)

    # φ = sin(x)·cos(y)  ⇒  ∂φ/∂x = cos(x)·cos(y),  ∂φ/∂y = -sin(x)·sin(y)
    u = @. sin(xs) * cos(ys)
    dux = similar(u); duy = similar(u)
    apply_gradient!(dux, duy, u, stencil)

    ax = @. cos(xs) * cos(ys)
    ay = @. -sin(xs) * sin(ys)
    @test maximum(abs.(dux .- ax)) < 0.01
    @test maximum(abs.(duy .- ay)) < 0.01
end

@testset "grid_assembly: input validation" begin
    g = TestCartesianGrid(8, 8, 2π, 2π)
    s = precompute_laplacian_stencil(g; xi_axis = :x, eta_axis = :y)

    u = zeros(n_cells(g))
    du = zeros(n_cells(g) + 1)
    @test_throws DimensionMismatch apply_laplacian!(du, u, s)
end
