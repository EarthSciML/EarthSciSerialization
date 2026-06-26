# Horizontal regridding kernels for the C4 regrid bridge (bead ess-14f.5, JL-J2).
#
# The Julia sibling of the Rust `regrid_kernels.rs` (ess-14f.10) and Python
# `earthsci_toolkit.data_loaders.regrid_kernels` (ess-2fy). The C4 driver
# (`regrid_driver.jl`) selects one of these by the per-variable [`RegridSpec`](@ref)
# `method`. Each kernel is the numeric realisation of an ESD declarative rule — the
# bridge reproduces the rule arithmetic rather than evaluating the `.esm` AST, so
# the fold orders below match the rule ASTs (and the Python/Rust goldens) exactly:
#
#   * `bspline` → `regridding/bspline_regrid.esm` (degree-1 Linear1D / Bilinear2D
#     tensor product and degree-3 Cubic1D).
#   * `conservative` → `regridding/conservative_regrid_overlap_join.esm`: the
#     overlap-area matrix `A_ij = area(src_i ∩ tgt_j)`, column sums `A_j = Σ_i A_ij`
#     and the partition-of-unity apply `F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]`. The
#     per-pair overlap area reuses the landed M4 geometry kernels
#     ([`intersect_polygon`](@ref) + [`polygon_area`](@ref)) — no new primitive.
#   * `cell_average` → `regridding/point_cell_average_regrid.esm`: bin scattered
#     points into target cells and average, emitting `missing_value` for empties.
#
# Rings are `n×2` `Matrix{Float64}` of lon/lat vertices — the operand type the
# `geometry.jl` clip/area kernels already accept (implicitly closed).

# --------------------------------------------------------------------------- #
# Source-grid location: target query -> (1-based base node, fractional offset s)
# --------------------------------------------------------------------------- #

"""
    locate_1d(query, nodes; clamp=true) -> (base, s)

Locate `query` points within ascending 1-D `nodes`. Returns `(base, s)` where
`base` is the **1-based** index of the lower bracketing node and `s` the
fractional offset into `[nodes[base], nodes[base+1])` — the host inputs the
`bspline_regrid` rule consumes. With `clamp` (the bilinear-default extrapolation),
out-of-range queries clamp `s` to `[0, 1]` so edge values are held. Mirrors Python
`locate_1d`: `searchsorted(side="right") − 1`, base index clipped to `[0, n−2]`
(here re-expressed 1-based).
"""
function locate_1d(query::AbstractVector, nodes::AbstractVector; clamp::Bool=true)
    length(nodes) < 2 && throw(RegridError("locate_1d needs at least 2 source nodes"))
    max_base1 = length(nodes) - 1          # 1-based index of the last valid base node
    base = Vector{Int}(undef, length(query))
    s = Vector{Float64}(undef, length(query))
    for (k, q) in enumerate(query)
        # searchsortedlast = count of nodes <= q (ascending) = searchsorted(side="right").
        sr = searchsortedlast(nodes, q)
        idx = max(1, min(sr, max_base1))   # 1-based base node, clipped to [1, n-1]
        x0 = nodes[idx]
        x1 = nodes[idx+1]
        frac = x1 != x0 ? (q - x0) / (x1 - x0) : 0.0
        if clamp
            frac = max(0.0, min(frac, 1.0))
        end
        base[k] = idx
        s[k] = frac
    end
    return base, s
end

# --------------------------------------------------------------------------- #
# bspline_regrid.esm — byte-exact fold order
# --------------------------------------------------------------------------- #

"""
    bspline_regrid_linear_1d(f_src, base, s) -> Vector{Float64}

`BSplineRegridLinear1D`: `(1−s)·F[base] + s·F[base+1]` (1-based `base`), evaluated
per query point. Mirrors Python `bspline_regrid_linear_1d`.
"""
function bspline_regrid_linear_1d(f_src::AbstractVector, base::AbstractVector{<:Integer},
                                  s::AbstractVector)
    out = Vector{Float64}(undef, length(base))
    for k in eachindex(base)
        b = base[k]
        sk = s[k]
        t0 = (1.0 - sk) * f_src[b]
        t1 = sk * f_src[b+1]
        out[k] = t0 + t1
    end
    return out
end

"""
    bspline_regrid_cubic_1d(f_src, base, s) -> Vector{Float64}

`BSplineRegridCubic1D`: degree-3 Lagrange cardinal sum over 4 nodes. Reproduces
the rule's flat n-ary fold: each weight product is `((coeff·f1)·f2)·f3` and the
four terms sum left-to-right `((t0+t1)+t2)+t3`. Mirrors Python
`bspline_regrid_cubic_1d`.
"""
function bspline_regrid_cubic_1d(f_src::AbstractVector, base::AbstractVector{<:Integer},
                                 s::AbstractVector)
    term(coeff, factors, f_k) = begin
        wp = coeff
        for f in factors
            wp *= f
        end
        wp * f_k
    end
    out = Vector{Float64}(undef, length(base))
    for k in eachindex(base)
        b = base[k]
        sk = s[k]
        t0 = term(-1.0 / 6.0, (sk, sk - 1.0, sk - 2.0), f_src[b])
        t1 = term(1.0 / 2.0, (sk + 1.0, sk - 1.0, sk - 2.0), f_src[b+1])
        t2 = term(-1.0 / 2.0, (sk + 1.0, sk, sk - 2.0), f_src[b+2])
        t3 = term(1.0 / 6.0, (sk + 1.0, sk, sk - 1.0), f_src[b+3])
        out[k] = ((t0 + t1) + t2) + t3
    end
    return out
end

"""
    bspline_regrid_bilinear_2d(f_src, base_x, base_y, s_x, s_y) -> Vector{Float64}

`BSplineRegridBilinear2D`: degree-1 tensor product over a `[x, y]` grid. `f_src` is
indexed `[x_index, y_index]`; `base_x`/`base_y` are 1-based. Term and factor order
match the rule AST (`((t0+t1)+t2)+t3`). Mirrors Python `bspline_regrid_bilinear_2d`.
"""
function bspline_regrid_bilinear_2d(f_src::AbstractMatrix, base_x::AbstractVector{<:Integer},
                                    base_y::AbstractVector{<:Integer}, s_x::AbstractVector,
                                    s_y::AbstractVector)
    out = Vector{Float64}(undef, length(base_x))
    for k in eachindex(base_x)
        bx = base_x[k]
        by = base_y[k]
        sx = s_x[k]
        sy = s_y[k]
        t0 = ((1.0 - sx) * (1.0 - sy)) * f_src[bx, by]
        t1 = (sx * (1.0 - sy)) * f_src[bx+1, by]
        t2 = ((1.0 - sx) * sy) * f_src[bx, by+1]
        t3 = (sx * sy) * f_src[bx+1, by+1]
        out[k] = ((t0 + t1) + t2) + t3
    end
    return out
end

# --------------------------------------------------------------------------- #
# conservative_regrid_overlap_join.esm — geometry-derived overlap assembly
# --------------------------------------------------------------------------- #

"""
    overlap_area_matrix(src_rings, tgt_rings, manifold, atol) -> Matrix{Float64}

Build `A_ij = area(src_i ∩ tgt_j)` via the landed M4 geometry kernels. Each ring
is an `n×2` `Matrix{Float64}` of `(lon, lat)` vertices (implicitly closed, the
[`intersect_polygon`](@ref) contract). Overlap areas at or below `atol` are
dropped to exactly `0` (the rule's `filter: A_ij > atol` sliver gate). Returns the
dense `[n_src, n_tgt]` raw-area matrix. Mirrors Python `overlap_area_matrix`.
"""
function overlap_area_matrix(src_rings::AbstractVector, tgt_rings::AbstractVector,
                             manifold::AbstractString, atol::Real)
    n_s = length(src_rings)
    n_t = length(tgt_rings)
    A = zeros(Float64, n_s, n_t)
    for i in 1:n_s
        for j in 1:n_t
            clip = intersect_polygon(src_rings[i], tgt_rings[j], manifold)
            size(clip, 1) < 3 && continue
            # `polygon_area` closes the ring internally, so the open
            # `intersect_polygon` output is passed directly.
            area = polygon_area(clip, manifold)
            if area > atol
                A[i, j] = area
            end
        end
    end
    return A
end

"""
    conservative_regrid(f_src, src_rings, tgt_rings, manifold, atol) -> (F_tgt, A, A_j)

First-order conservative remap of cell values `f_src` src→tgt. `A` is the overlap-
area matrix, `A_j` the target-cell areas (column sums = the `dst_areas`
denominator) and `F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]`. Empty target cells
(`A_j == 0`) yield `0`. Mass is conserved (`Σ_j A_j·F_tgt = Σ_ij A_ij·F_src`) and
the weights `A_ij/A_j` partition unity over each covered target cell. The
`Aᵀ·f_src` matvec is the cheap per-refresh apply. Mirrors Python
`conservative_regrid`.
"""
function conservative_regrid(f_src::AbstractVector, src_rings::AbstractVector,
                             tgt_rings::AbstractVector, manifold::AbstractString, atol::Real)
    A = overlap_area_matrix(src_rings, tgt_rings, manifold, atol)
    length(f_src) == size(A, 1) || throw(RegridError(
        "F_src length $(length(f_src)) != source cell count $(size(A, 1))"))
    A_j = vec(sum(A, dims=1))                 # column sums, length n_tgt
    num = A' * collect(Float64, f_src)        # num[j] = Σ_i A_ij·F_i
    F_tgt = [A_j[j] > 0.0 ? num[j] / A_j[j] : 0.0 for j in eachindex(A_j)]
    return F_tgt, A, A_j
end

# --------------------------------------------------------------------------- #
# point_cell_average_regrid.esm — scattered-point binning + cell average
# --------------------------------------------------------------------------- #

"""
    cell_average_regrid(station_val, station_lon, station_lat, cell_lon, cell_lat,
                        dx, dy, missing_value) -> Vector{Float64}

Average scattered station values into target cells by integer bin. A station and a
cell match when their `(floor(lon/dx), floor(lat/dy))` bins are equal; the cell
value is the mean of its matched stations, or `missing_value` when no station
lands in it. Mirrors Python `cell_average_regrid`.
"""
function cell_average_regrid(station_val::AbstractVector, station_lon::AbstractVector,
                             station_lat::AbstractVector, cell_lon::AbstractVector,
                             cell_lat::AbstractVector, dx::Real, dy::Real, missing_value::Real)
    s_bin_x = [floor(Int, v / dx) for v in station_lon]
    s_bin_y = [floor(Int, v / dy) for v in station_lat]
    out = Vector{Float64}(undef, length(cell_lon))
    for j in eachindex(cell_lon)
        cbx = floor(Int, cell_lon[j] / dx)
        cby = floor(Int, cell_lat[j] / dy)
        sum_v = 0.0
        count = 0
        for i in eachindex(station_val)
            if s_bin_x[i] == cbx && s_bin_y[i] == cby
                sum_v += station_val[i]
                count += 1
            end
        end
        out[j] = count > 0 ? sum_v / count : Float64(missing_value)
    end
    return out
end
