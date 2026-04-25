# Tests for esm-tet symbolic ArrayOp assembly against the esm-a3z Grid trait.
#
# Acceptance: ArrayOp output for an identity-metric Cartesian test grid must
# match the numeric stencil on the same grid (within Float64 round-off). The
# test grid is the same `TestCartesianGrid` from grid_assembly_test.jl
# (periodic, identity metric), copied here so this file is self-contained.

using Test
using EarthSciSerialization
using EarthSciSerialization: AbstractCurvilinearGrid, cell_centers, cell_volume,
    cell_widths, neighbor_indices, boundary_mask, n_cells, n_dims, axis_names,
    metric_g, metric_ginv, metric_jacobian, metric_dgij_dxk,
    coord_jacobian, coord_jacobian_second,
    precompute_laplacian_stencil, apply_laplacian!,
    precompute_gradient_stencil, apply_gradient!,
    fv_laplacian_extended, fv_gradient_extended,
    laplacian_neighbor_table, gradient_neighbor_table,
    const_wrap, evaluate_arrayop
using ModelingToolkit
using Symbolics

# ---------------------------------------------------------------------------
# Minimal 2D periodic Cartesian test grid (Tier C + trivial Tier M).
# Identical to the one used in grid_assembly_test.jl. Duplicated rather than
# shared so the two test files load independently.
# ---------------------------------------------------------------------------

struct SymTestCartesianGrid <: AbstractCurvilinearGrid
    Nx::Int
    Ny::Int
    Lx::Float64
    Ly::Float64
end

_flat(g::SymTestCartesianGrid, i::Int, j::Int) = i + (j - 1) * g.Nx
_wrap(idx::Int, n::Int) = mod(idx - 1, n) + 1

EarthSciSerialization.n_cells(g::SymTestCartesianGrid) = g.Nx * g.Ny
EarthSciSerialization.n_dims(g::SymTestCartesianGrid)  = 2
EarthSciSerialization.axis_names(g::SymTestCartesianGrid) = (:x, :y)

function EarthSciSerialization.cell_centers(g::SymTestCartesianGrid, axis::Symbol)
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

function EarthSciSerialization.cell_widths(g::SymTestCartesianGrid, axis::Symbol)
    N = n_cells(g)
    w = axis === :x ? g.Lx / g.Nx :
        axis === :y ? g.Ly / g.Ny :
        throw(ArgumentError("unknown axis $axis"))
    return fill(w, N)
end

function EarthSciSerialization.cell_volume(g::SymTestCartesianGrid)
    dx = g.Lx / g.Nx; dy = g.Ly / g.Ny
    return fill(dx * dy, n_cells(g))
end

function EarthSciSerialization.neighbor_indices(g::SymTestCartesianGrid, axis::Symbol, offset::Int)
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

EarthSciSerialization.boundary_mask(g::SymTestCartesianGrid, ::Symbol, ::Symbol) =
    falses(n_cells(g))

function EarthSciSerialization.metric_g(g::SymTestCartesianGrid)
    N = n_cells(g)
    out = zeros(N, 2, 2)
    @inbounds for c in 1:N
        out[c, 1, 1] = 1.0; out[c, 2, 2] = 1.0
    end
    return out
end
EarthSciSerialization.metric_ginv(g::SymTestCartesianGrid) = metric_g(g)
EarthSciSerialization.metric_jacobian(g::SymTestCartesianGrid) = ones(n_cells(g))
EarthSciSerialization.metric_dgij_dxk(g::SymTestCartesianGrid) = zeros(n_cells(g), 2, 2, 2)

function EarthSciSerialization.coord_jacobian(g::SymTestCartesianGrid, ::Symbol)
    N = n_cells(g)
    out = zeros(N, 2, 2)
    @inbounds for c in 1:N
        out[c, 1, 1] = 1.0; out[c, 2, 2] = 1.0
    end
    return out
end
EarthSciSerialization.coord_jacobian_second(g::SymTestCartesianGrid, ::Symbol) =
    zeros(n_cells(g), 2, 2, 2)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@testset "grid_assembly_symbolic: neighbor tables match numeric stencil" begin
    g = SymTestCartesianGrid(8, 6, 2π, 2π)
    nb_lap = laplacian_neighbor_table(g; xi_axis = :x, eta_axis = :y)
    nb_grad = gradient_neighbor_table(g; xi_axis = :x, eta_axis = :y)
    @test size(nb_lap) == (n_cells(g), 9)
    @test size(nb_grad) == (n_cells(g), 5)

    # Center column is self-index for both.
    @test nb_lap[:, 1]  == collect(1:n_cells(g))
    @test nb_grad[:, 1] == collect(1:n_cells(g))

    # Match the numeric stencil's neighbor matrix on the shared C/E/W/N/S columns.
    s_lap = precompute_laplacian_stencil(g; xi_axis = :x, eta_axis = :y)
    @test nb_lap == s_lap.neighbors
    s_grad = precompute_gradient_stencil(g, :xy; xi_axis = :x, eta_axis = :y)
    @test nb_grad == s_grad.neighbors
end

@testset "grid_assembly_symbolic: fv_laplacian_extended matches numeric apply_laplacian!" begin
    g = SymTestCartesianGrid(16, 16, 2π, 2π)
    xs = cell_centers(g, :x); ys = cell_centers(g, :y)
    u = @. sin(xs) * cos(ys)

    # Numeric reference: precompute + apply.
    s = precompute_laplacian_stencil(g; xi_axis = :x, eta_axis = :y)
    du_num = similar(u)
    apply_laplacian!(du_num, u, s)

    # Symbolic ArrayOp evaluated on the same numeric field. Wrapping the
    # numeric vector as the field array lets `evaluate_arrayop` extract the
    # per-cell numeric result via `Const`-indexing, which is the same path
    # MTK takes when the ArrayOp is later compiled with concrete u(t).
    ao = fv_laplacian_extended(u, g; xi_axis = :x, eta_axis = :y)
    du_sym = evaluate_arrayop(ao)

    @test size(du_sym) == size(du_num)
    @test isapprox(du_sym, du_num; rtol = 1e-12, atol = 1e-12)
end

@testset "grid_assembly_symbolic: fv_gradient_extended matches numeric apply_gradient!" begin
    g = SymTestCartesianGrid(32, 32, 2π, 2π)
    xs = cell_centers(g, :x); ys = cell_centers(g, :y)
    u = @. sin(xs) * cos(ys)

    s = precompute_gradient_stencil(g, :xy; xi_axis = :x, eta_axis = :y)
    dux_num = similar(u); duy_num = similar(u)
    apply_gradient!(dux_num, duy_num, u, s)

    (ao_x, ao_y) = fv_gradient_extended(u, g, :xy; xi_axis = :x, eta_axis = :y)
    dux_sym = evaluate_arrayop(ao_x)
    duy_sym = evaluate_arrayop(ao_y)

    @test isapprox(dux_sym, dux_num; rtol = 1e-12, atol = 1e-12)
    @test isapprox(duy_sym, duy_num; rtol = 1e-12, atol = 1e-12)
end

@testset "grid_assembly_symbolic: ArrayOp on Symbolic field round-trips through scalarize" begin
    # Confirm the ArrayOp form is a real symbolic object MTK can consume:
    # build it on `Symbolics.@variables u(t)[1:N]` and check that scalarize
    # produces N expressions, then substitute concrete values and verify the
    # numeric output matches the numeric stencil.
    g = SymTestCartesianGrid(8, 8, 2π, 2π)
    N = n_cells(g)
    @variables t
    u_sym = first(Symbolics.@variables u(t)[1:N])

    ao = fv_laplacian_extended(collect(u_sym), g; xi_axis = :x, eta_axis = :y)
    scalars = Symbolics.scalarize(Symbolics.wrap(ao))
    @test length(scalars) == N

    # Substitute a concrete field and compare to the numeric stencil.
    xs = cell_centers(g, :x); ys = cell_centers(g, :y)
    u_vals = @. sin(xs) * cos(ys)
    subs = Dict(u_sym[c] => u_vals[c] for c in 1:N)
    du_sym = [Float64(Symbolics.value(Symbolics.substitute(s, subs))) for s in scalars]

    s_num = precompute_laplacian_stencil(g; xi_axis = :x, eta_axis = :y)
    du_num = similar(u_vals); apply_laplacian!(du_num, u_vals, s_num)

    @test isapprox(du_sym, du_num; rtol = 1e-12, atol = 1e-12)
end
