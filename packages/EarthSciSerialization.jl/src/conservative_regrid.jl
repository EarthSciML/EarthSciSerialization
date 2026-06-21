# First-order conservative-regridding assembly (RFC `semiring-faq-unified-ir`
# §A.8 / §8.1 / §6.1; `CONFORMANCE_SPEC.md` §5.8; bead ess-my4.4.6).
#
# The **Julia per-binding assembly** of the conservative regridder — the
# `F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]` operator, with
# `A_ij = area(src_i ∩ tgt_j)` and `A_j = Σ_i A_ij` — composed from the
# already-landed machinery plus the one geometry leaf, exactly as the A.8
# decomposition prescribes (the sibling of the Python `conservative_regrid.py`,
# bead ess-my4.4.7, and the Rust assembly, ess-my4.4.12). Nothing here is a new
# physical operator:
#
#   A.8 piece                realized by                                  partition
#   ----------------------   ------------------------------------------   ----------
#   overlap pairs {(i,j)}    bin-Skolem equi-join — the relational         static
#                            engine (`Relational`: `skolem` bins +
#                            `equijoin` + `distinct`)
#   A_ij                     the `intersect_polygon` clip leaf +           static
#                            the `polygon_area` `sum_product` FAQ
#   A_j = Σ_i A_ij           group-by-`j` `sum_product` row-sum            static
#   apply Σ_i A_ij·F_src[i]  `sum_product` (sparse mat-vec)                dynamic
#   /A_j                     elementwise normalize (build-time-foldable)   static fold
#
# The broad phase (which pairs are *candidates*) is **integer-keyed and
# byte-identical** across bindings (§5.8.5): every cell is quantized to the
# integer spatial bins its bounding box spans (`floor` + `skolem`), and the
# candidates are the `equijoin` of cells sharing a bin, deduplicated with
# `distinct`. No floating-point coordinate comparison enters the broad phase —
# coordinates touch only the narrow-phase *area*. The narrow phase clips each
# candidate and drops sub-`atol` slivers (§5.8.2: "present-but-tiny" and "absent"
# both collapse to zero), turning the byte-identical *candidate* set into the
# tolerance-dependent *surviving* set.
#
# Partition-of-unity `Σ_i W_ij = 1` holds **by construction** because the
# denominator `A_j` is the row-sum of the *same* computed overlap areas
# (`ConservativeRegridding.jl`'s `dst_areas`), so it is exact regardless of
# edge-model error (§5.8.3). Global conservation
# `Σ_j A_j·F_tgt[j] = Σ_i A_i·F_src[i]` holds exactly when the target grid tiles
# the source domain (`Σ_j A_ij = A_i`); otherwise it is tolerance-/resolution-set.
#
# The A_j row-sum and the apply mat-vec are the `sum_product` FAQs of §A.8; the
# IR form of those FAQs and their execution through the tree-walk evaluator are
# the worked fixture `tests/valid/geometry/conservative_regrid_assembly.esm`,
# exercised by `test/geometry_assembly_conformance_test.jl`. Here they are the
# direct semiring reductions (`sum` / mat-vec) the producing binding emits — the
# same idiom by which `polygon_area` is the executable form of the area FAQ.

#: Tag prefix the broad-phase bin Skolem keys carry, mirroring the worked fixture
#: `tests/valid/geometry/conservative_regrid_overlap_join.esm`.
const REGRID_BIN_TAG = "bin"

#: Default per-pair area relative tolerance for the §5.8.2 / B.5 gate.
const REGRID_DEFAULT_RTOL = 1e-9

# --------------------------------------------------------------------------- #
# (1) OVERLAP PAIRS — the bin-Skolem equi-join broad phase (build-time)
# --------------------------------------------------------------------------- #

"""
    cell_bin_keys(poly, dx, dy) -> Vector

Every integer spatial-bin Skolem key the cell's bounding box spans. The cell is
quantized to the integer lattice `floor(coord/step)` (the existing `floor` op —
no bespoke binning leaf) and a key is minted with [`Relational.skolem`](@ref) for
**each** bin its bbox touches. Binning by the full bbox span (not a single
representative corner) is what makes the broad phase *complete* — it can never
miss a true overlap, so the candidate set is a genuine superset of the
surviving-overlap set (§5.8.5).

Keys are integer-componented tuples, so the resulting candidate set is
byte-identical across bindings (§5.5 determinism — no float in a key).
"""
function cell_bin_keys(poly::AbstractMatrix, dx::Real, dy::Real)
    ring = _to_matrix(poly)
    lon = @view ring[:, 1]
    lat = @view ring[:, 2]
    bx_lo = floor(Int, minimum(lon) / dx)
    bx_hi = floor(Int, maximum(lon) / dx)
    by_lo = floor(Int, minimum(lat) / dy)
    by_hi = floor(Int, maximum(lat) / dy)
    return [Relational.skolem((REGRID_BIN_TAG, bx, by))
            for bx in bx_lo:bx_hi for by in by_lo:by_hi]
end

"""
    candidate_overlap_pairs(src_polys, tgt_polys, dx, dy) -> Vector{Tuple{Int,Int}}

The bin-Skolem candidate overlap-pair set `{(i, j)}` (broad phase). Realized as a
value-equality [`Relational.equijoin`](@ref) of the `(bin_key, cell)` tables of
source and target on the shared bin key, then [`Relational.distinct`](@ref) over
the surviving `(i, j)` index pairs. Both primitives emit in the §5.5 sorted total
order, so the returned list is the **byte-identical, integer,
permutation-invariant** candidate set the §5.8.6 gate asserts on — neither the
order of `src_polys` / `tgt_polys` nor bucket iteration order can perturb it.
"""
function candidate_overlap_pairs(src_polys, tgt_polys, dx::Real, dy::Real)
    src_rows = [(key, i) for (i, p) in enumerate(src_polys)
                for key in cell_bin_keys(p, dx, dy)]
    tgt_rows = [(key, j) for (j, p) in enumerate(tgt_polys)
                for key in cell_bin_keys(p, dx, dy)]
    matched = Relational.equijoin(src_rows, tgt_rows;
                                  on_left = r -> r[1], on_right = r -> r[1])
    pairs = [(left[2], right[2]) for (left, right) in matched]
    return Tuple{Int,Int}[p for p in Relational.distinct(pairs)]
end

# --------------------------------------------------------------------------- #
# (2) A_ij — the intersect_polygon clip leaf + the polygon_area FAQ
# --------------------------------------------------------------------------- #

"""
    overlap_area(poly_a, poly_b, manifold; atol=0.0) -> Float64

The single-pair overlap area `A_ij = polygon_area(src ∩ tgt)`. The clip is the
[`intersect_polygon`](@ref) kernel leaf; the area is the [`polygon_area`](@ref)
`sum_product` FAQ (planar shoelace / Gauss–Green, or the closed-form spherical
excess). An empty / degenerate clip (`< 3` vertices) is no overlap; a sub-`atol`
sliver snaps to exactly zero (§5.8.2: "present-but-tiny" and "absent" both
collapse to zero).
"""
function overlap_area(poly_a, poly_b, manifold::AbstractString; atol::Real=0.0)
    ring = intersect_polygon(poly_a, poly_b, manifold)
    size(ring, 1) < 3 && return 0.0          # empty / degenerate clip → no overlap
    area = abs(polygon_area(ring, manifold))
    return area <= atol ? 0.0 : area
end

# --------------------------------------------------------------------------- #
# (3)+(4)+(5) A_j / apply / normalize — the regridder
# --------------------------------------------------------------------------- #

"""
    Regridder

A built-once conservative regridder (the `ConservativeRegridding.jl` `Regridder`):
the raw overlap-area matrix `A_ij`, its row-sums `A_j` (`dst_areas`), and the
normalized weights `W_ij = A_ij / A_j`. Build with [`build_regridder`](@ref) and
remap fields with [`apply_regrid`](@ref).
"""
struct Regridder
    candidate_pairs::Vector{Tuple{Int,Int}}
    A_ij::Matrix{Float64}   # [n_src, n_tgt] raw overlap areas (0 off the surviving set)
    A_j::Vector{Float64}    # [n_tgt] = Σ_i A_ij  (dst_areas)
    weights::Matrix{Float64} # [n_src, n_tgt] W_ij = A_ij / A_j
    manifold::String
end

regridder_n_src(r::Regridder) = size(r.A_ij, 1)
regridder_n_tgt(r::Regridder) = size(r.A_ij, 2)

"""
    build_regridder(src_polys, tgt_polys; manifold="planar", dx, dy, atol=0.0) -> Regridder

Build the conservative regridder for a source/target cell-polygon pair. Runs the
full A.8 static partition: broad-phase bin-Skolem candidate join
([`candidate_overlap_pairs`](@ref)), narrow-phase clip + `polygon_area` FAQ for
each candidate ([`overlap_area`](@ref), sub-`atol` slivers dropped), the
group-by-`j` row-sum `A_j` (the `sum_product` FAQ), and the normalize
`W_ij = A_ij / A_j`.
"""
function build_regridder(src_polys, tgt_polys; manifold::AbstractString="planar",
                         dx::Real, dy::Real, atol::Real=0.0)
    manifold in GEOMETRY_MANIFOLDS || throw(GeometryError(
        "unknown manifold $(repr(manifold)); the closed set is $(GEOMETRY_MANIFOLDS)"))
    ns, nt = length(src_polys), length(tgt_polys)
    pairs = candidate_overlap_pairs(src_polys, tgt_polys, dx, dy)

    A_ij = zeros(Float64, ns, nt)
    for (i, j) in pairs
        A_ij[i, j] = overlap_area(src_polys[i], tgt_polys[j], manifold; atol=atol)
    end

    # (3) A_j = Σ_i A_ij — the group-by-`j` sum_product row-sum (dst_areas). Off-
    # candidate / sub-atol entries are already 0 in A_ij, so the dense column sum
    # equals the sparse contraction over the surviving overlap set.
    A_j = vec(sum(A_ij; dims = 1))

    # (5) normalize — W_ij = A_ij / A_j for every covered target cell.
    weights = zeros(Float64, ns, nt)
    for j in 1:nt
        if A_j[j] > 0.0
            @views weights[:, j] .= A_ij[:, j] ./ A_j[j]
        end
    end
    return Regridder(pairs, A_ij, A_j, weights, String(manifold))
end

"""
    apply_regrid(r::Regridder, F_src) -> Vector{Float64}

Remap `F_src` to the target grid: `F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]` — the
apply `sum_product` FAQ (sparse mat-vec) followed by the elementwise normalize.
Target cells with no overlap (`A_j[j] == 0`) map to 0.
"""
function apply_regrid(r::Regridder, F_src::AbstractVector)
    ns, nt = regridder_n_src(r), regridder_n_tgt(r)
    length(F_src) == ns || throw(DimensionMismatch(
        "F_src has length $(length(F_src)), expected $(ns)"))
    f = collect(Float64, F_src)
    out = zeros(Float64, nt)
    for j in 1:nt
        if r.A_j[j] > 0.0
            numerator = sum(r.A_ij[i, j] * f[i] for i in 1:ns)   # Σ_i A_ij·F_src[i]
            out[j] = numerator / r.A_j[j]
        end
    end
    return out
end

"""
    partition_of_unity_residual(r::Regridder) -> Vector{Float64}

`Σ_i W_ij − 1` per target cell — zero (to floating point) by construction for
every cell with a nonzero overlap (§5.8.3).
"""
function partition_of_unity_residual(r::Regridder)
    res = zeros(Float64, regridder_n_tgt(r))
    for j in 1:regridder_n_tgt(r)
        if r.A_j[j] > 0.0
            res[j] = sum(@view r.weights[:, j]) - 1.0
        end
    end
    return res
end

"""
    conservation_residual(r::Regridder, F_src, src_areas) -> Float64

`Σ_j A_j·F_tgt[j] − Σ_i A_i·F_src[i]` — the global-mass residual (§5.8.3). Zero
(to floating point) when the target grid tiles the source domain.
"""
function conservation_residual(r::Regridder, F_src::AbstractVector, src_areas::AbstractVector)
    f = collect(Float64, F_src)
    a_i = collect(Float64, src_areas)
    f_tgt = apply_regrid(r, f)
    return sum(r.A_j .* f_tgt) - sum(a_i .* f)
end
