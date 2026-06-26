# C4 regrid driver — reproject + horizontal regrid + `lev=min` (bead ess-14f.5,
# JL-J2). The Julia sibling of the Rust `regrid_driver.rs` (ess-14f.10) and Python
# `earthsci_toolkit.data_loaders.regrid_driver` (ess-2fy).
#
# The ESS-Julia orchestration that lands a data-loader's RAW native arrays onto a
# model's projected target domain grid, consuming the EXISTING ESD declarative
# rules numerically (no new primitive):
#
#   1. Resolve the target grid. A model domain (e.g. `camp_fire_surface`) gives a
#      projected `(x, y)` lattice in metres plus a `spatial_ref` PROJ string.
#      [`build_target_grid`](@ref) builds the lattice (`min + i·spacing` per dim)
#      and applies the ESD reprojection rule (`reproject.jl`) to get the lon/lat
#      cell **centers** (point/bspline sampling) and cell **corner rings**
#      (conservative overlap). Built once and cached.
#   2. Reduce `lev=min` early. A 3-D field (`lev, lat, lon`) collapses to the
#      ground surface via [`lev_min_reduce`](@ref), the numeric image of the ESD
#      `lev_min_surface_reduce` rule (keep the slice at the minimum `lev`).
#   3. Horizontal regrid per method. [`regrid_field`](@ref) dispatches on the
#      per-variable [`RegridSpec`](@ref) `method` to a `regrid_kernels.jl` kernel —
#      `bspline`, `conservative`, or `cell_average`.
#
# The output is a flat `Float64` vector in the target domain's spatial-dim order
# (C-order: cell `(i, j)` at flat index `(i-1)*shape[2] + j`).
#
# [`ESDRegrid`](@ref) is the consumer-facing [`RegridApplier`](@ref) (the JL-J1
# seam, ess-14f.4): it builds the static target geometry + overlap matrix ONCE at
# construction and reduces each refresh to the cheap apply (a matvec `Aᵀf ./ A_j`
# for the conservative method), then writes the result into the live forcing
# buffer in place.

# --------------------------------------------------------------------------- #
# Target grid construction
# --------------------------------------------------------------------------- #

"""
    SpatialDim(min, max, grid_spacing)

One spatial dimension of a model domain: `[min, max]` in projected units with a
fixed `grid_spacing`. The `(name => SpatialDim)` list passed to
[`build_target_grid`](@ref) mirrors a domain's `spatial` block.
"""
struct SpatialDim
    min::Float64
    max::Float64
    grid_spacing::Float64
end

"""
    TargetGrid

A model domain's grid expressed in lon/lat for regridding. `dims` are the
horizontal spatial dim names in domain order (e.g. `["x", "y"]`); `shape` is the
matching cell count per dim. `center_lon` / `center_lat` are the reprojected cell
centers, flattened C-order over `shape` (cell `(i, j)` at flat index
`(i-1)*shape[2] + j`). `corner_rings` holds one CCW `4×2` `(lon, lat)` ring per
cell in the same C-order (empty for a 1-D grid). Mirrors Python/Rust `TargetGrid`.
"""
struct TargetGrid
    dims::Vector{String}
    shape::Vector{Int}
    centers::Dict{String,Vector{Float64}}
    center_lon::Vector{Float64}
    center_lat::Vector{Float64}
    corner_rings::Vector{Matrix{Float64}}
end

# Cell-center coordinates and spacing for one spatial dimension. Node count follows
# `spatial_discretize` — `round((max−min)/spacing) + 1` — so the lattice spans
# `[min, max]`. Mirrors Python `_dim_nodes`. Round-half-away-from-zero matches the
# Rust `f64::round`.
function _dim_nodes(spec::SpatialDim)
    (isfinite(spec.grid_spacing) && spec.grid_spacing > 0) || throw(RegridError(
        "target domain dimension needs a positive grid_spacing"))
    n = Int(round((spec.max - spec.min) / spec.grid_spacing, RoundNearestTiesAway)) + 1
    n < 1 && throw(RegridError("target domain dimension has no cells"))
    nodes = [spec.min + i * spec.grid_spacing for i in 0:n-1]
    return nodes, spec.grid_spacing
end

"""
    build_target_grid(dims, spatial_ref) -> TargetGrid

Build a lon/lat [`TargetGrid`](@ref) from an ordered list of `name => SpatialDim`
pairs. Supports a 2-D horizontal grid (the camp-fire `x`/`y` surface case); a 1-D
grid is also handled (no corner rings). The `spatial_ref` PROJ string drives the
projected→lon/lat conversion (`longlat` identity or spherical `lcc`); the
[`Reprojector`](@ref) (and its `LccCone`) is derived once and reused for every
center and corner. Mirrors Python/Rust `build_target_grid`.
"""
function build_target_grid(dims::AbstractVector{<:Pair{<:AbstractString,SpatialDim}},
                           spatial_ref::Union{AbstractString,Nothing})
    isempty(dims) && throw(RegridError("target domain has no spatial dimensions"))
    reproj = reprojector_from_spatial_ref(spatial_ref)

    dim_names = String[String(p.first) for p in dims]
    centers = Dict{String,Vector{Float64}}()
    spacing = Dict{String,Float64}()
    for p in dims
        nodes, sp = _dim_nodes(p.second)
        centers[String(p.first)] = nodes
        spacing[String(p.first)] = sp
    end
    shape = Int[length(centers[d]) for d in dim_names]

    if length(dim_names) == 1
        d0 = dim_names[1]
        lon = Float64[]
        lat = Float64[]
        for x in centers[d0]
            clon, clat = xy_to_lonlat(reproj, x, 0.0)
            push!(lon, clon)
            push!(lat, clat)
        end
        return TargetGrid(dim_names, shape, centers, lon, lat, Matrix{Float64}[])
    end
    length(dim_names) == 2 || throw(RegridError(
        "target grid build supports 1-D or 2-D domains; got $(length(dim_names)) dims"))

    d0 = dim_names[1]
    d1 = dim_names[2]
    h0 = spacing[d0] / 2.0
    h1 = spacing[d1] / 2.0
    nodes0 = centers[d0]
    nodes1 = centers[d1]
    center_lon = Float64[]
    center_lat = Float64[]
    corner_rings = Matrix{Float64}[]
    # Mesh d0 outer, d1 inner so flattening matches the C-order layout.
    for x0 in nodes0, y0 in nodes1
        clon, clat = xy_to_lonlat(reproj, x0, y0)
        push!(center_lon, clon)
        push!(center_lat, clat)
        # Cell corner ring: each center ± half-spacing, reprojected, CCW.
        corners = ((x0 - h0, y0 - h1), (x0 + h0, y0 - h1),
                   (x0 + h0, y0 + h1), (x0 - h0, y0 + h1))
        ring = Matrix{Float64}(undef, 4, 2)
        for (rr, (cx, cy)) in enumerate(corners)
            rl, ra = xy_to_lonlat(reproj, cx, cy)
            ring[rr, 1] = rl
            ring[rr, 2] = ra
        end
        push!(corner_rings, ring)
    end
    return TargetGrid(dim_names, shape, centers, center_lon, center_lat, corner_rings)
end

# Pull a numeric `min`/`max`/`grid_spacing` from a domain spatial-dim spec, which
# may be a `Dict` (string or symbol keys) or an object with properties.
function _dim_spec_field(spec, key::AbstractString)
    if spec isa AbstractDict
        haskey(spec, key) && return Float64(spec[key])
        haskey(spec, Symbol(key)) && return Float64(spec[Symbol(key)])
        return nothing
    end
    s = Symbol(key)
    if hasproperty(spec, s)
        v = getproperty(spec, s)
        v === nothing || return Float64(v)
    end
    return nothing
end

"""
    build_target_grid_from_domain(domain::Domain, spatial_ref=nothing) -> TargetGrid

Build a [`TargetGrid`](@ref) from a model [`Domain`](@ref) and its PROJ
`spatial_ref`. Reads `domain.spatial` (a `{dim => {min, max, grid_spacing}}`
mapping); dimensions are taken in **alphabetical** key order (matching the Rust
`build_target_grid_from_domain`, where `serde_json` yields keys alphabetically —
for the camp-fire `x`/`y` surface this is the natural order). A non-alphabetical
dim order must use [`build_target_grid`](@ref) with an explicit ordered list.

`spatial_ref` is taken separately because the Julia [`Domain`](@ref) struct does
not carry it (the schema places `spatial_ref` as a domain-level sibling of
`spatial`; pass it explicitly from the parsed file).
"""
function build_target_grid_from_domain(domain::Domain,
                                       spatial_ref::Union{AbstractString,Nothing}=nothing)
    spatial = domain.spatial
    (spatial === nothing || isempty(spatial)) &&
        throw(RegridError("target domain has no spatial dimensions"))
    names = sort!(collect(keys(spatial)))
    dims = Pair{String,SpatialDim}[]
    for name in names
        spec = spatial[name]
        mn = _dim_spec_field(spec, "min")
        mx = _dim_spec_field(spec, "max")
        gs = _dim_spec_field(spec, "grid_spacing")
        (mn === nothing || mx === nothing || gs === nothing) && throw(RegridError(
            "domain dimension $(repr(name)) needs numeric min, max and grid_spacing"))
        push!(dims, String(name) => SpatialDim(mn, mx, gs))
    end
    return build_target_grid(dims, spatial_ref)
end

# --------------------------------------------------------------------------- #
# lev=min surface reduction (ESD lev_min_surface_reduce rule)
# --------------------------------------------------------------------------- #

"""
    lev_min_reduce(field, lev_coord, lev_axis) -> Array

Collapse an N-D field to the surface by keeping the minimum-`lev` slice along
`lev_axis` (1-based). `lev_coord` are the vertical coordinate values; the slice at
`argmin(lev_coord)` is returned (the numeric image of the ESD
`lev_min_surface_reduce` value-at-argmin rule). The first minimum wins. Mirrors
Python/Rust `lev_min_reduce`.
"""
function lev_min_reduce(field::AbstractArray, lev_coord::AbstractVector, lev_axis::Integer)
    (1 <= lev_axis <= ndims(field)) || throw(RegridError(
        "lev_axis $lev_axis out of range for $(ndims(field))-D field"))
    size(field, lev_axis) == length(lev_coord) || throw(RegridError(
        "lev axis size $(size(field, lev_axis)) != lev_coord size $(length(lev_coord))"))
    isempty(lev_coord) && throw(RegridError("lev_coord is empty"))
    # First index of the minimum (strict `<` keeps the first, numpy argmin).
    k = 1
    best = lev_coord[1]
    for (i, v) in enumerate(lev_coord)
        if v < best
            best = v
            k = i
        end
    end
    return copy(selectdim(field, lev_axis, k))
end

# --------------------------------------------------------------------------- #
# Source-cell rings (separable lat/lon grid -> per-cell corner polygons)
# --------------------------------------------------------------------------- #

# Cell edges (n+1) bracketing `n` ascending centers (midpoint split, the two ends
# reflected). Mirrors Python `_edges_from_centers`.
function edges_from_centers(centers::AbstractVector)
    n = length(centers)
    n == 0 && return Float64[]
    n == 1 && return Float64[centers[1] - 0.5, centers[1] + 0.5]
    edges = Vector{Float64}(undef, n + 1)
    first_mid = (centers[1] + centers[2]) / 2.0
    edges[1] = centers[1] - (first_mid - centers[1])
    for i in 1:n-1
        edges[i+1] = (centers[i] + centers[i+1]) / 2.0
    end
    last_mid = (centers[n-1] + centers[n]) / 2.0
    edges[n+1] = centers[n] + (centers[n] - last_mid)
    return edges
end

# One CCW 4-vertex `(lon, lat)` ring per source cell, flattened `[lat, lon]`
# C-order (cell `(a, b)` at flat `(a-1)*nlon + b`). Mirrors Python
# `_source_cell_rings`.
function source_cell_rings(src_lon::AbstractVector, src_lat::AbstractVector)
    lon_e = edges_from_centers(src_lon)
    lat_e = edges_from_centers(src_lat)
    rings = Matrix{Float64}[]
    for a in eachindex(src_lat)
        y0 = lat_e[a]
        y1 = lat_e[a+1]
        for b in eachindex(src_lon)
            x0 = lon_e[b]
            x1 = lon_e[b+1]
            push!(rings, [x0 y0; x1 y0; x1 y1; x0 y1])
        end
    end
    return rings
end

# --------------------------------------------------------------------------- #
# Horizontal regrid dispatch
# --------------------------------------------------------------------------- #

# C-order (`[lat, lon]`, lat outer / lon inner) flatten of a `(nlat, nlon)` matrix,
# matching `source_cell_rings` order and the Python/Rust `field.reshape(-1)`.
_row_major_vec(M::AbstractMatrix) = [M[a, b] for a in axes(M, 1) for b in axes(M, 2)]

"""
    regrid_field(field_2d, src_lon, src_lat, target, method;
                 manifold="planar", missing_value=NaN, atol=0.0) -> Vector{Float64}

Regrid a 2-D `(lat, lon)` source field onto `target` by `method`, returning a flat
vector in the target's C-order cell layout. `bspline` samples the source grid
bilinearly at each target center; `conservative` performs an overlap-area remap of
source cells onto the target corner rings; `cell_average` bins the source nodes
(treated as scattered points) into the target cells. Mirrors Python/Rust
`regrid_field`.
"""
function regrid_field(field_2d::AbstractMatrix, src_lon::AbstractVector,
                      src_lat::AbstractVector, target::TargetGrid, method::AbstractString;
                      manifold::AbstractString="planar", missing_value::Real=NaN, atol::Real=0.0)
    nlat = length(src_lat)
    nlon = length(src_lon)
    size(field_2d) == (nlat, nlon) || throw(RegridError(
        "source field shape $(size(field_2d)) != (nlat=$nlat, nlon=$nlon)"))
    if method == "bspline"
        base_x, s_x = locate_1d(target.center_lon, collect(Float64, src_lon))
        base_y, s_y = locate_1d(target.center_lat, collect(Float64, src_lat))
        f_xy = permutedims(field_2d)        # (nlon, nlat), indexed [lon, lat]
        return bspline_regrid_bilinear_2d(f_xy, base_x, base_y, s_x, s_y)
    elseif method == "conservative"
        src_rings = source_cell_rings(collect(Float64, src_lon), collect(Float64, src_lat))
        f_src = _row_major_vec(field_2d)    # [lat, lon] C-order matches src_rings
        F_tgt, _A, _Aj = conservative_regrid(f_src, src_rings, target.corner_rings,
                                             String(manifold), atol)
        return F_tgt
    elseif method == "cell_average"
        s_lon = Float64[]
        s_lat = Float64[]
        for la in src_lat, lo in src_lon    # lat outer, lon inner (C-order stations)
            push!(s_lon, lo)
            push!(s_lat, la)
        end
        f_src = _row_major_vec(field_2d)
        dx = min_unique_spacing(target.center_lon)
        dy = min_unique_spacing(target.center_lat)
        return cell_average_regrid(f_src, s_lon, s_lat, target.center_lon,
                                   target.center_lat, dx, dy, missing_value)
    else
        throw(RegridError(
            "unknown regrid method $(repr(method)); expected bspline|conservative|cell_average"))
    end
end

# Smallest gap between distinct values (rounded to 9 decimals), or `1.0` for a
# single value — the `cell_average` target bin size. Mirrors Python's
# `min(diff(unique(round(coords, 9))))`.
function min_unique_spacing(vals::AbstractVector)
    length(vals) <= 1 && return 1.0
    rounded = sort!(unique!([round(v * 1e9) / 1e9 for v in vals]))
    length(rounded) <= 1 && return 1.0
    return minimum(rounded[k+1] - rounded[k] for k in 1:length(rounded)-1)
end

"""
    regrid_loader_field(values, src_lon, src_lat, target, method;
                        lev_coord=nothing, lev_axis=1, manifold="planar",
                        missing_value=NaN, atol=0.0) -> Vector{Float64}

Full per-field pipeline: `lev=min` (if `lev_coord` given) → horizontal regrid →
flat. `values` is the raw loaded field; when `lev_coord` is supplied the field is
first collapsed to the surface along `lev_axis` (1-based), then regridded onto
`target` by `method`. Mirrors Python/Rust `regrid_loader_field`.
"""
function regrid_loader_field(values::AbstractArray, src_lon::AbstractVector,
                             src_lat::AbstractVector, target::TargetGrid, method::AbstractString;
                             lev_coord::Union{Nothing,AbstractVector}=nothing, lev_axis::Integer=1,
                             manifold::AbstractString="planar", missing_value::Real=NaN, atol::Real=0.0)
    arr = lev_coord === nothing ? values : lev_min_reduce(values, lev_coord, lev_axis)
    ndims(arr) == 2 || throw(RegridError(
        "regrid expects a 2-D field after lev reduction; got ndim=$(ndims(arr))"))
    return regrid_field(arr, src_lon, src_lat, target, method;
                        manifold=manifold, missing_value=missing_value, atol=atol)
end

# --------------------------------------------------------------------------- #
# ESDRegrid — the consumer-facing RegridApplier (cached geometry, cheap refresh)
# --------------------------------------------------------------------------- #

# Static per-method plans, built ONCE at ESDRegrid construction.
struct _ConservativePlan
    A::Matrix{Float64}     # [n_src, n_tgt] overlap-area matrix
    A_j::Vector{Float64}   # target-cell areas (column sums)
end
struct _BsplinePlan
    base_x::Vector{Int}
    s_x::Vector{Float64}
    base_y::Vector{Int}
    s_y::Vector{Float64}
end
struct _CellAvgPlan
    station_lon::Vector{Float64}
    station_lat::Vector{Float64}
    dx::Float64
    dy::Float64
end

const _REGRID_METHODS = ("conservative", "bspline", "cell_average")

"""
    ESDRegrid(target, src_lon, src_lat; methods, missing_values=Dict(),
              lev_coords=Dict(), manifold="planar", atol=0.0)
    ESDRegrid(target, src_lon, src_lat, specs::Dict{String,RegridSpec}; kwargs...)

A [`RegridApplier`](@ref) that lands a provider's RAW native arrays on a model's
projected sim grid using the landed ESD rules (reproject + `lev=min` + per-variable
regrid). The **static** geometry — the [`TargetGrid`](@ref) corner rings, the
conservative overlap matrix `A` / its column sums `A_j`, the bspline source-locate
indices, and the cell-average station bins — is built ONCE here at construction
from the shared native source grid (`src_lon`, `src_lat`). Each
[`apply_regrid!`](@ref) is then the cheap per-method apply: a matvec `Aᵀf ./ A_j`
for `conservative`, a cached bilinear blend for `bspline`, a cached binning for
`cell_average`. The result is written into the live forcing buffer in place.

`methods` maps each forcing variable to its regrid method (`"conservative"`,
`"bspline"`, or `"cell_average"`) — typically the model's per-variable
[`RegridSpec`](@ref) `method`; the `specs` constructor reads it (and
`missing_value`) straight from a `Dict{String,RegridSpec}`. `missing_values` is the
`cell_average` no-data fill per variable (default `NaN`). `lev_coords` supplies the
vertical coordinate for any 3-D variable, which is collapsed to the surface
(`lev=min`) before the horizontal regrid; variables absent from `lev_coords` are
treated as 2-D `(lat, lon)`.

The provider sample handed to [`apply_regrid!`](@ref) yields each variable's native
field (via the same extraction [`IdentityRegrid`](@ref) uses: an `AbstractDict`
keyed by variable, or a bare array). The native field is a flat **C-order**
sequence (`[lev,] lat, lon`) of length `nlev*nlat*nlon` / `nlat*nlon`, or an array
already shaped `(nlev, nlat, nlon)` / `(nlat, nlon)`.
"""
struct ESDRegrid <: RegridApplier
    target::TargetGrid
    src_lon::Vector{Float64}
    src_lat::Vector{Float64}
    methods::Dict{String,String}
    missing_values::Dict{String,Float64}
    lev_coords::Dict{String,Vector{Float64}}
    manifold::String
    atol::Float64
    conservative::Union{Nothing,_ConservativePlan}
    bspline::Union{Nothing,_BsplinePlan}
    cell_average::Union{Nothing,_CellAvgPlan}
end

function ESDRegrid(target::TargetGrid, src_lon::AbstractVector, src_lat::AbstractVector;
                   methods::AbstractDict, missing_values::AbstractDict=Dict{String,Float64}(),
                   lev_coords::AbstractDict=Dict{String,Vector{Float64}}(),
                   manifold::AbstractString="planar", atol::Real=0.0)
    length(target.shape) == 2 || throw(RegridError(
        "ESDRegrid requires a 2-D target grid; got $(length(target.shape)) dims"))
    slon = collect(Float64, src_lon)
    slat = collect(Float64, src_lat)
    method_map = Dict{String,String}()
    for (v, m) in methods
        String(m) in _REGRID_METHODS || throw(RegridError(
            "unknown regrid method $(repr(m)) for variable $(repr(v)); " *
            "expected bspline|conservative|cell_average"))
        method_map[String(v)] = String(m)
    end
    mset = Set(values(method_map))

    cons = nothing
    if "conservative" in mset
        src_rings = source_cell_rings(slon, slat)
        A = overlap_area_matrix(src_rings, target.corner_rings, String(manifold), atol)
        cons = _ConservativePlan(A, vec(sum(A, dims=1)))
    end
    bspl = nothing
    if "bspline" in mset
        bx, sx = locate_1d(target.center_lon, slon)
        by, sy = locate_1d(target.center_lat, slat)
        bspl = _BsplinePlan(bx, sx, by, sy)
    end
    cavg = nothing
    if "cell_average" in mset
        st_lon = Float64[]
        st_lat = Float64[]
        for la in slat, lo in slon          # lat outer, lon inner (C-order stations)
            push!(st_lon, lo)
            push!(st_lat, la)
        end
        dx = min_unique_spacing(target.center_lon)
        dy = min_unique_spacing(target.center_lat)
        cavg = _CellAvgPlan(st_lon, st_lat, dx, dy)
    end

    return ESDRegrid(
        target, slon, slat, method_map,
        Dict{String,Float64}(String(k) => Float64(v) for (k, v) in missing_values),
        Dict{String,Vector{Float64}}(String(k) => collect(Float64, v) for (k, v) in lev_coords),
        String(manifold), Float64(atol), cons, bspl, cavg)
end

function ESDRegrid(target::TargetGrid, src_lon::AbstractVector, src_lat::AbstractVector,
                   specs::AbstractDict{<:AbstractString,RegridSpec}; kwargs...)
    methods = Dict{String,String}()
    missing_values = Dict{String,Float64}()
    for (v, spec) in specs
        spec.method === nothing && throw(RegridError(
            "RegridSpec for variable $(repr(v)) has no method; cannot build ESDRegrid"))
        methods[String(v)] = spec.method
        spec.missing_value === nothing || (missing_values[String(v)] = spec.missing_value)
    end
    return ESDRegrid(target, src_lon, src_lat; methods=methods, missing_values=missing_values, kwargs...)
end

# Reshape an opaque native field (flat C-order vector or correctly-shaped array)
# into the `(nlat, nlon)` matrix the kernels consume, applying `lev=min` for a 3-D
# variable.
function _native_field_2d(r::ESDRegrid, var::AbstractString, field)
    nlat = length(r.src_lat)
    nlon = length(r.src_lon)
    if haskey(r.lev_coords, var)
        lev = r.lev_coords[var]
        arr3 = _as_corder_array(field, (length(lev), nlat, nlon))
        return lev_min_reduce(arr3, lev, 1)          # lev axis = 1 (C-order [lev,lat,lon])
    else
        return _as_corder_array(field, (nlat, nlon))
    end
end

# A flat C-order vector reshaped to `dims`, or a correctly-shaped array used as-is.
function _as_corder_array(field, dims::NTuple{N,Int}) where {N}
    n = prod(dims)
    if field isa AbstractVector
        length(field) == n || throw(RefreshError(
            "ESDRegrid: native field has $(length(field)) elements but expected $n " *
            "for C-order shape $dims"))
        flat = collect(Float64, field)
        if N == 2
            return permutedims(reshape(flat, dims[2], dims[1]))
        else
            return permutedims(reshape(flat, dims[3], dims[2], dims[1]), (3, 2, 1))
        end
    elseif field isa AbstractArray && ndims(field) == N && size(field) == dims
        return Array{Float64}(field)
    else
        throw(RefreshError(
            "ESDRegrid: native field must be a flat C-order vector of length $n or an " *
            "array of shape $dims; got $(typeof(field))" *
            (field isa AbstractArray ? " with size $(size(field))" : "")))
    end
end

# The cheap per-method apply over a `(nlat, nlon)` field → flat C-order target.
function _apply_regrid_method(r::ESDRegrid, var::AbstractString, field2d::AbstractMatrix)
    method = r.methods[var]
    if method == "conservative"
        plan = r.conservative::_ConservativePlan
        f_src = _row_major_vec(field2d)
        num = plan.A' * f_src                       # Aᵀf — the cheap matvec
        A_j = plan.A_j
        return [A_j[j] > 0.0 ? num[j] / A_j[j] : 0.0 for j in eachindex(A_j)]
    elseif method == "bspline"
        plan = r.bspline::_BsplinePlan
        f_xy = permutedims(field2d)                 # (nlon, nlat)
        return bspline_regrid_bilinear_2d(f_xy, plan.base_x, plan.base_y, plan.s_x, plan.s_y)
    else  # cell_average
        plan = r.cell_average::_CellAvgPlan
        mv = get(r.missing_values, var, NaN)
        f_src = _row_major_vec(field2d)
        return cell_average_regrid(f_src, plan.station_lon, plan.station_lat,
                                   r.target.center_lon, r.target.center_lat, plan.dx, plan.dy, mv)
    end
end

# Scatter a flat C-order target vector into the live buffer IN PLACE. The buffer
# (length `shape[1]*shape[2]`, a `Vector` or `(n0, n1)` Matrix) is interpreted
# column-major as the `(n0, n1)` sim grid: cell `(i, j)` of the C-order output
# lands at `buffer[i, j]`.
function _scatter_corder!(buffer::Array{Float64}, out::AbstractVector, shape::Vector{Int})
    n0 = shape[1]
    n1 = shape[2]
    length(buffer) == n0 * n1 || throw(RefreshError(
        "ESDRegrid: target grid has $(n0 * n1) cells but the buffer has $(length(buffer)) elements"))
    bm = reshape(buffer, n0, n1)                     # column-major view, shares memory
    @inbounds for i in 1:n0, j in 1:n1
        bm[i, j] = out[(i - 1) * n1 + j]
    end
    return buffer
end

"""
    apply_regrid!(r::ESDRegrid, buffer, var, sample) -> buffer

Extract `var`'s native field from `sample`, collapse `lev=min` if 3-D, run the
cached per-variable regrid (the cheap matvec / bilinear / binning apply), and write
the result into `buffer` IN PLACE (column-major over the target `(n0, n1)` grid).
"""
function apply_regrid!(r::ESDRegrid, buffer::Array{Float64}, var::AbstractString, sample)
    v = String(var)
    haskey(r.methods, v) || throw(RefreshError(
        "ESDRegrid: no regrid method configured for variable '$v' " *
        "(configured: $(sort!(collect(keys(r.methods)))))"))
    field = _regrid_field(sample, v)                 # same extraction IdentityRegrid uses
    field2d = _native_field_2d(r, v, field)
    out = _apply_regrid_method(r, v, field2d)
    return _scatter_corder!(buffer, out, r.target.shape)
end
