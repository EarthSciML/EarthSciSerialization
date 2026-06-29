# Declarative conservative-regrid overlap matrix through the tree-walk evaluator.
#
# The single-clip M4 kernel materializes ONE intersect_polygon ring from whole-
# array const operands. This exercises the M4+ extension: intersect_polygon RANGED
# over the src × tgt candidate pairs, so the overlap-area matrix A_ij is computed
# DECLARATIVELY — `A_ij = polygon_area(intersect_polygon(src_i, tgt_j))` over all
# pairs, the shoelace `aggregate` FAQ — with NO host-supplied A_ij/dst_areas. The
# whole geometry chain (clip → A_ij → A_j → F_tgt apply) is build-once at setup
# from the const polygon inputs, then `build_evaluator` integrates the apply.
#
# 2×2 case (planar, unit squares):
#   src cells: [0,1]² and [1,2]×[0,1];  tgt cells: [0,1]² and [0.5,1.5]×[0,1]
#   overlaps  A_ij = [[1.0, 0.5], [0.0, 0.5]]      (1.0 = full, 0.5 = half, 0.0 = none)
#   A_j       = Σ_i A_ij = [1.0, 1.0]
#   F_src     = [10, 20]  ⇒  F_tgt = A_ijᵀ·F_src / A_j = [10.0, 15.0]

using Test
using EarthSciSerialization
const _ESS = EarthSciSerialization

# ---- compact AST builders ----
_ix(args...) = Dict{String,Any}("op" => "index", "args" => collect(Any, args))
_agg(lv, set, body) = Dict{String,Any}(
    "op" => "aggregate", "semiring" => "sum_product", "output_idx" => Any[],
    "ranges" => Dict{String,Any}(lv => Dict{String,Any}("from" => set)),
    "args" => Any[], "expr" => body)
_arrop(oidx, ranges, body) = Dict{String,Any}(
    "op" => "arrayop", "output_idx" => collect(Any, oidx),
    "ranges" => Dict{String,Any}(k => Dict{String,Any}("from" => v) for (k, v) in ranges),
    "args" => Any[], "expr" => body)
_D(s, rhs) = Dict{String,Any}(
    "lhs" => Dict{String,Any}("op" => "D", "args" => Any[s], "wrt" => "t"), "rhs" => rhs)

function _ranged_clip_regrid_esm()
    ip = Dict{String,Any}("op" => "intersect_polygon", "id" => "overlap_clip",
        "manifold" => "planar", "args" => Any[_ix("src_poly", "i"), _ix("tgt_poly", "j")])
    # clip[i,j,w,c] = intersect_polygon(src_poly[i], tgt_poly[j])[w,c]
    clip = _arrop(["i", "j", "w", "c"],
        ["i" => "src_cells", "j" => "tgt_cells", "w" => "clip_ring", "c" => "coord"],
        _ix(ip, "w", "c"))
    # A_ij[i,j] = shoelace polygon_area over clip[i,j]
    vp1 = Dict{String,Any}("op" => "+", "args" => Any["v", 1])
    shoe = Dict{String,Any}("op" => "*", "args" => Any[0.5,
        Dict{String,Any}("op" => "-", "args" => Any[
            Dict{String,Any}("op" => "*", "args" => Any[_ix("clip","i","j","v",1), _ix("clip","i","j",vp1,2)]),
            Dict{String,Any}("op" => "*", "args" => Any[_ix("clip","i","j",vp1,1), _ix("clip","i","j","v",2)])])])
    A_ij = _arrop(["i", "j"], ["i" => "src_cells", "j" => "tgt_cells"], _agg("v", "clip_ring", shoe))
    A_j  = _arrop(["j"], ["j" => "tgt_cells"], _agg("i", "src_cells", _ix("A_ij", "i", "j")))
    num  = _agg("i", "src_cells", Dict{String,Any}("op" => "*",
                "args" => Any[_ix("A_ij", "i", "j"), _ix("F_src", "i")]))
    F_tgt = _arrop(["j"], ["j" => "tgt_cells"], Dict{String,Any}("op" => "/", "args" => Any[num, _ix("A_j", "j")]))

    model = Dict{String,Any}(
        "index_sets" => Dict{String,Any}(
            "coord" => Dict{String,Any}("kind" => "interval", "size" => 2),
            "verts" => Dict{String,Any}("kind" => "interval", "size" => 4),
            "src_cells" => Dict{String,Any}("kind" => "interval", "size" => 2),
            "tgt_cells" => Dict{String,Any}("kind" => "interval", "size" => 2),
            "clip_ring" => Dict{String,Any}("kind" => "derived", "from_faq" => "overlap_clip")),
        "variables" => Dict{String,Any}(
            "src_poly" => Dict{String,Any}("type" => "parameter", "shape" => Any["src_cells", "verts", "coord"]),
            "tgt_poly" => Dict{String,Any}("type" => "parameter", "shape" => Any["tgt_cells", "verts", "coord"]),
            "F_src"    => Dict{String,Any}("type" => "parameter", "shape" => Any["src_cells"]),
            "clip"  => Dict{String,Any}("type" => "observed", "shape" => Any["src_cells","tgt_cells","clip_ring","coord"], "expression" => clip),
            "A_ij"  => Dict{String,Any}("type" => "observed", "shape" => Any["src_cells","tgt_cells"], "expression" => A_ij),
            "A_j"   => Dict{String,Any}("type" => "observed", "shape" => Any["tgt_cells"], "expression" => A_j),
            "F_tgt" => Dict{String,Any}("type" => "observed", "shape" => Any["tgt_cells"], "expression" => F_tgt),
            "A11" => Dict{String,Any}("type" => "state", "shape" => Any[]),
            "A12" => Dict{String,Any}("type" => "state", "shape" => Any[]),
            "A21" => Dict{String,Any}("type" => "state", "shape" => Any[]),
            "A22" => Dict{String,Any}("type" => "state", "shape" => Any[]),
            "FT1" => Dict{String,Any}("type" => "state", "shape" => Any[]),
            "FT2" => Dict{String,Any}("type" => "state", "shape" => Any[])),
        "equations" => Any[
            _D("A11", _ix("A_ij", 1, 1)), _D("A12", _ix("A_ij", 1, 2)),
            _D("A21", _ix("A_ij", 2, 1)), _D("A22", _ix("A_ij", 2, 2)),
            _D("FT1", _ix("F_tgt", 1)),   _D("FT2", _ix("F_tgt", 2))])
    return Dict{String,Any}(
        "esm" => "0.6.0", "metadata" => Dict{String,Any}("name" => "ranged_clip_regrid_2x2"),
        "models" => Dict{String,Any}("RangedClipRegrid2x2" => model))
end

@testset "Declarative conservative-regrid A_ij via ranged intersect_polygon (M4+)" begin
    esm = _ranged_clip_regrid_esm()

    src_poly = zeros(2, 4, 2)
    tgt_poly = zeros(2, 4, 2)
    src_poly[1, :, :] = [0 0; 1 0; 1 1; 0 1]   # [0,1]²
    src_poly[2, :, :] = [1 0; 2 0; 2 1; 1 1]   # [1,2]×[0,1]
    tgt_poly[1, :, :] = [0 0; 1 0; 1 1; 0 1]   # [0,1]²
    tgt_poly[2, :, :] = [0.5 0; 1.5 0; 1.5 1; 0.5 1]   # [0.5,1.5]×[0,1]
    F_src = [10.0, 20.0]

    f!, u0, p, _tspan, vmap = build_evaluator(esm;
        const_arrays = Dict("src_poly" => src_poly, "tgt_poly" => tgt_poly, "F_src" => F_src),
        initial_conditions = Dict("A11" => 0.0, "A12" => 0.0, "A21" => 0.0,
                                  "A22" => 0.0, "FT1" => 0.0, "FT2" => 0.0))
    du = similar(u0)
    f!(du, u0, p, 0.0)

    # A_ij computed declaratively from the const polygons (no host A_ij).
    @test du[vmap["A11"]] ≈ 1.0 atol = 1e-12
    @test du[vmap["A12"]] ≈ 0.5 atol = 1e-12
    @test du[vmap["A21"]] ≈ 0.0 atol = 1e-12
    @test du[vmap["A22"]] ≈ 0.5 atol = 1e-12
    # F_tgt = the regridded field through the full declarative apply.
    @test du[vmap["FT1"]] ≈ 10.0 atol = 1e-12
    @test du[vmap["FT2"]] ≈ 15.0 atol = 1e-12
end
