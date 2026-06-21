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
#
# `polygon_area` is NOT a new op: the area of a clipped vertex ring is an ordinary
# `sum_product` FAQ over the ring (RFC §8.1). The builders below assemble that FAQ
# as an `OpExpr` and `_polygon_area_via_faq` evaluates it through the SAME generic
# aggregate machinery the tree-walk evaluator uses (`_resolve_indices` →
# `_resolve_scalar_arrayop` → `evaluate_expr`) — so the production overlap area is
# the FAQ, and the imperative `geometry.polygon_area` / `_spherical_signed_area`
# loops are only the cross-check oracle. Coordinate columns are 1-based (1 = lon,
# 2 = lat) over the CLOSED ring, so the wrap edge `v→1` is the ordinary `v+1`
# lookup `close_ring` provides.

# Degrees→radians factor — identical to `deg2rad(x) = x·(π/180)`, so the FAQ's
# lon-lat→sphere map matches the imperative oracle (`_lonlat_to_unit`) bit-for-bit.
const _REGRID_DEG2RAD = π / 180

# `index(overlap_clip, idx, col)` — read coordinate `col` (1 = lon, 2 = lat) of
# clip-ring vertex `idx` (an `Expr`: a range symbol, an affine `v+1`, or a literal).
_clip_col(idx::Expr, col::Int) =
    OpExpr("index", Expr[VarExpr("overlap_clip"), idx, IntExpr(col)])

"""
    _shoelace_area_faq(n) -> OpExpr

The planar `polygon_area` FAQ over the closed clip ring: the Gauss–Green shoelace
`0.5·Σ_v (x_v·y_{v+1} − x_{v+1}·y_v)` — an ordinary `sum_product` aggregate (§8.1),
the same AST as `tests/valid/geometry/intersect_polygon_planar_area.esm`.
"""
function _shoelace_area_faq(n::Int)::OpExpr
    v = VarExpr("v")
    vnext = OpExpr("+", Expr[VarExpr("v"), IntExpr(1)])
    cross = OpExpr("-", Expr[
        OpExpr("*", Expr[_clip_col(v, 1), _clip_col(vnext, 2)]),
        OpExpr("*", Expr[_clip_col(vnext, 1), _clip_col(v, 2)]),
    ])
    return OpExpr("aggregate", Expr[VarExpr("overlap_clip")];
                  semiring="sum_product", output_idx=Any[],
                  ranges=Dict{String,Any}("v" => [1, n]),
                  expr_body=OpExpr("*", Expr[NumExpr(0.5), cross]))
end

# Unit 3-vector AST `(cosφ·cosλ, cosφ·sinλ, sinφ)` of clip-ring vertex `idx`.
function _clip_unit_vec(idx::Expr)
    lon = OpExpr("*", Expr[_clip_col(idx, 1), NumExpr(_REGRID_DEG2RAD)])
    lat = OpExpr("*", Expr[_clip_col(idx, 2), NumExpr(_REGRID_DEG2RAD)])
    cos_lat = OpExpr("cos", Expr[lat])
    return (OpExpr("*", Expr[cos_lat, OpExpr("cos", Expr[lon])]),
            OpExpr("*", Expr[cos_lat, OpExpr("sin", Expr[lon])]),
            OpExpr("sin", Expr[lat]))
end

_dot3(u, v) = OpExpr("+", Expr[
    OpExpr("*", Expr[u[1], v[1]]),
    OpExpr("*", Expr[u[2], v[2]]),
    OpExpr("*", Expr[u[3], v[3]])])

_cross3(u, v) = (
    OpExpr("-", Expr[OpExpr("*", Expr[u[2], v[3]]), OpExpr("*", Expr[u[3], v[2]])]),
    OpExpr("-", Expr[OpExpr("*", Expr[u[3], v[1]]), OpExpr("*", Expr[u[1], v[3]])]),
    OpExpr("-", Expr[OpExpr("*", Expr[u[1], v[2]]), OpExpr("*", Expr[u[2], v[1]])]))

# Van Oosterom–Strackee signed solid angle of triangle a,b,c:
# 2·atan2(a·(b×c), 1 + a·b + b·c + c·a).
function _spherical_excess(a, b, c)
    triple = _dot3(a, _cross3(b, c))
    denom = OpExpr("+", Expr[NumExpr(1.0), _dot3(a, b), _dot3(b, c), _dot3(c, a)])
    return OpExpr("*", Expr[NumExpr(2.0), OpExpr("atan2", Expr[triple, denom])])
end

"""
    _spherical_area_faq(n) -> OpExpr

The spherical `polygon_area` FAQ over the closed clip ring: the great-circle fan
triangulation `Σ_v E(v_1, v_v, v_{v+1})` of Van Oosterom–Strackee spherical
excesses — an ordinary `sum_product` aggregate (§8.1), the spherical sibling of
[`_shoelace_area_faq`](@ref). Ranging the *full* closed ring is exact: the two
degenerate fan endpoints (`v=1` ⇒ `E(v_1,v_1,v_2)`, `v=n` ⇒ `E(v_1,v_n,v_1)`)
carry zero excess, so the sum collapses to the `Σ_{i=2}^{n-1}` fan the oracle
`_spherical_signed_area` computes. Unit sphere (radius 1).
"""
function _spherical_area_faq(n::Int)::OpExpr
    apex = _clip_unit_vec(IntExpr(1))
    here = _clip_unit_vec(VarExpr("v"))
    nxt  = _clip_unit_vec(OpExpr("+", Expr[VarExpr("v"), IntExpr(1)]))
    return OpExpr("aggregate", Expr[VarExpr("overlap_clip")];
                  semiring="sum_product", output_idx=Any[],
                  ranges=Dict{String,Any}("v" => [1, n]),
                  expr_body=_spherical_excess(apex, here, nxt))
end

"""
    _polygon_area_via_faq(closed_ring, manifold) -> Float64

Evaluate the (unsigned) `polygon_area` FAQ for a CLOSED clip ring (`n+1` rows)
through the generic aggregate machinery: register the ring as the `overlap_clip`
const-array, build the planar shoelace / spherical-excess `sum_product` FAQ, and
run it through `_resolve_indices` (→ `_resolve_scalar_arrayop`) + `evaluate_expr`
— the same tree-walk path `build_evaluator` uses. Returns `0.0` for a degenerate
(`< 3` distinct vertex) ring.
"""
function _polygon_area_via_faq(closed_ring::AbstractMatrix, manifold::AbstractString)::Float64
    n = max(size(closed_ring, 1) - 1, 0)   # closed ring has n+1 rows
    n < 3 && return 0.0
    faq = manifold == "planar" ? _shoelace_area_faq(n) : _spherical_area_faq(n)
    const_arrays = Dict{String,AbstractArray{Float64}}("overlap_clip" => Matrix{Float64}(closed_ring))
    array_var_info = Dict{String,Tuple{Vector{Int},Vector{Int}}}()
    var_map = Dict{String,Int}()
    resolved = _resolve_indices(faq, array_var_info, var_map, const_arrays)
    return abs(evaluate_expr(resolved, Dict{String,Float64}()))
end

"""
    overlap_area(poly_a, poly_b, manifold; atol=0.0) -> Float64

The single-pair overlap area `A_ij = polygon_area(src ∩ tgt)`. The clip is the
[`intersect_polygon`](@ref) kernel leaf; the area is the `polygon_area`
`sum_product` FAQ — the planar shoelace ([`_shoelace_area_faq`](@ref)) or the
spherical-excess fan ([`_spherical_area_faq`](@ref)) — evaluated through the
generic aggregate machinery by [`_polygon_area_via_faq`](@ref), with the imperative
[`polygon_area`](@ref) now only the cross-check oracle. An empty / degenerate clip
(`< 3` vertices) is no overlap; a sub-`atol` sliver snaps to exactly zero (§5.8.2:
"present-but-tiny" and "absent" both collapse to zero).
"""
function overlap_area(poly_a, poly_b, manifold::AbstractString; atol::Real=0.0)
    ring = intersect_polygon(poly_a, poly_b, manifold)
    size(ring, 1) < 3 && return 0.0          # empty / degenerate clip → no overlap
    area = _polygon_area_via_faq(close_ring(ring), manifold)
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
