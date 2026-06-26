# Coordinate reprojection for the C4 regrid bridge (bead ess-14f.5, JL-J2).
#
# The Julia sibling of the Rust `reproject.rs` (ess-14f.10) and Python
# `earthsci_toolkit.data_loaders.reproject` (ess-2fy) drivers. The horizontal
# regridder (`regrid_driver.jl`) bins source and target cells by **lon/lat**: it
# is CRS-agnostic and consumes geometry already in a shared geographic frame. A
# *projected* target domain (e.g. a Lambert Conformal Conic `camp_fire_surface`
# grid in metres) must therefore have its `(x, y)` lattice converted to
# `(lon, lat)` before regridding.
#
# This module supplies that conversion, mirroring the ESD reprojection rules
# (`reprojection/longlat.esm` identity and `reprojection/lambert_conformal.esm` /
# the `lambert_conformal_construction` corner inverse) byte-for-byte with the
# Python/Rust drivers. Both are **spherical** closed-form transforms (Snyder, *Map
# Projections — A Working Manual*, USGS PP 1395, §15) built from elementary ops —
# no PROJ runtime dependency. Supported projections: `longlat` and
# `lambert_conformal` (`lcc`); other CRS values have no ESD rule yet and raise.
#
# The forward/inverse pair is self-consistent for any radius, so the projected
# `(x, y)` lattice round-trips exactly regardless of the assumed `R`.

"""
    RegridError(message)

A reprojection / regrid-kernel / regrid-driver failure (an unsupported `+proj`,
a missing standard parallel, a degenerate cone, mismatched kernel lengths, or a
field that cannot be landed on the target domain). The Julia C4 bridge
(`reproject.jl` / `regrid_kernels.jl` / `regrid_driver.jl`) raises this for every
such error; it is the counterpart of the Python `ReprojectionError` /
`RegridKernelError` / `RegridDriverError` family.
"""
struct RegridError <: Exception
    message::String
end
Base.showerror(io::IO, e::RegridError) = print(io, "RegridError: ", e.message)

"""
Spherical Earth radius assumed for a `+datum=WGS84` / unspecified-radius
projected CRS. 6 370 997 m (the WGS84 authalic radius used across atmospheric-
model LCC grids). Only affects absolute scale, never the forward∘inverse
round-trip. Matches the Python/Rust `DEFAULT_SPHERE_RADIUS_M`.
"""
const DEFAULT_SPHERE_RADIUS_M = 6_370_997.0

# `π/180`, `180/π`, `π/4`, `π/2` written explicitly (rather than `deg2rad` /
# `Base` irrationals) so the arithmetic is bit-identical to the Python driver and
# the Rust `DEG2RAD`/`RAD2DEG`/`FRAC_PI_4`/`FRAC_PI_2` constants.
const _DEG2RAD = Float64(pi) / 180.0
const _RAD2DEG = 180.0 / Float64(pi)
const _FRAC_PI_4 = Float64(pi) / 4.0
const _FRAC_PI_2 = Float64(pi) / 2.0

"""
    parse_proj_string(spatial_ref) -> Dict{String,Any}

Parse a PROJ.4 `spatial_ref` string into a parameter map. Handles the
`+key=value` / bare `+flag` token grammar (e.g. `"+proj=lcc +lat_1=30.0
+lat_2=60.0 +lat_0=39.0 +lon_0=-97.0 +datum=WGS84 +units=m +no_defs"`). Numeric
values become `Float64`; non-numeric values stay `String`; bare flags map to
`true`. Mirrors Python `parse_proj_string` (the `float | str | True` dict).
"""
function parse_proj_string(spatial_ref::AbstractString)
    out = Dict{String,Any}()
    for token in split(spatial_ref)
        startswith(token, "+") || continue
        body = token[2:end]
        eq = findfirst('=', body)
        if eq === nothing
            isempty(body) || (out[body] = true)
        else
            key = body[1:prevind(body, eq)]
            value = body[nextind(body, eq):end]
            num = tryparse(Float64, value)
            out[String(key)] = num === nothing ? String(value) : num
        end
    end
    return out
end

# Numeric parameter lookup — the value only when `key` is a `Float64`.
proj_number(params::AbstractDict, key::AbstractString) =
    (v = get(params, key, nothing); v isa Float64 ? v : nothing)

# String parameter lookup — the value only when `key` is a `String`.
proj_text(params::AbstractDict, key::AbstractString) =
    (v = get(params, key, nothing); v isa AbstractString ? String(v) : nothing)

# Resolve the spherical radius: `+R`, else `+a`, else the default. Mirrors Python
# `_sphere_radius`.
_sphere_radius(params::AbstractDict) =
    something(proj_number(params, "R"), proj_number(params, "a"), DEFAULT_SPHERE_RADIUS_M)

"""
    LccCone(n, rf, rho0, lon_0, radius)

Snyder LCC cone constants derived once from a parsed CRS param map — the reusable
core of `reprojection/lambert_conformal.esm`. Holding the cone lets a whole
lattice be transformed without re-deriving the (trig-heavy) constants per point:
`n` the cone constant, `rf = R·F` the radius scale, `rho0` the latitude-of-origin
polar distance, `lon_0` the central meridian (degrees), `radius` the sphere `R`.
"""
struct LccCone
    n::Float64
    rf::Float64
    rho0::Float64
    lon_0::Float64
    radius::Float64
end

"""
    lcc_cone(params) -> LccCone

Build the [`LccCone`](@ref) from a parsed CRS param map. Reproduces
`reprojection/lambert_conformal.esm`: the standard-parallel cone constant `n`
(with the tangent-cone `lat_1 == lat_2` limit), the radius scale `RF = R·F` and
the latitude-of-origin polar distance `ρ0`. `lat_*` are degrees; `lat_2`/`lat_0`
default to `lat_1`, `lon_0` defaults to `0`. Mirrors Python `_lcc_cone`.
"""
function lcc_cone(params::AbstractDict)
    lat_1 = proj_number(params, "lat_1")
    lat_1 === nothing && throw(RegridError("lambert_conformal CRS requires +lat_1"))
    lat_2 = something(proj_number(params, "lat_2"), lat_1)
    lat_0 = something(proj_number(params, "lat_0"), lat_1)
    lon_0 = something(proj_number(params, "lon_0"), 0.0)
    radius = _sphere_radius(params)

    phi1 = lat_1 * _DEG2RAD
    phi2 = lat_2 * _DEG2RAD
    phi0 = lat_0 * _DEG2RAD
    t1 = tan(_FRAC_PI_4 + phi1 / 2.0)
    t2 = tan(_FRAC_PI_4 + phi2 / 2.0)
    t0 = tan(_FRAC_PI_4 + phi0 / 2.0)
    n = abs(phi1 - phi2) < 1e-12 ? sin(phi1) : log(cos(phi1) / cos(phi2)) / log(t2 / t1)
    n == 0.0 && throw(RegridError("degenerate LCC cone constant n == 0"))
    big_f = cos(phi1) * t1^n / n
    rf = radius * big_f
    rho0 = rf / t0^n
    return LccCone(n, rf, rho0, lon_0, radius)
end

"""
    lcc_forward_cone(lon, lat, cone) -> (x, y)

Spherical LCC forward over a precomputed [`LccCone`](@ref): `(lon, lat)` degrees →
projected `(x, y)` metres.
"""
function lcc_forward_cone(lon::Real, lat::Real, cone::LccCone)
    phi = lat * _DEG2RAD
    tphi = tan(_FRAC_PI_4 + phi / 2.0)
    rho = cone.rf / tphi^cone.n
    theta = cone.n * ((lon - cone.lon_0) * _DEG2RAD)
    x = rho * sin(theta)
    y = cone.rho0 - rho * cos(theta)
    return (x, y)
end

"""
    lcc_inverse_cone(x, y, cone) -> (lon, lat)

Spherical LCC inverse over a precomputed [`LccCone`](@ref): projected `(x, y)`
metres → `(lon, lat)` degrees. Closed form (Snyder 15-5/15-7/15-8/15-9), matching
the `lambert_conformal_construction` corner inverse rule.
"""
function lcc_inverse_cone(x::Real, y::Real, cone::LccCone)
    rho0_my = cone.rho0 - y
    rho_inv = copysign(1.0, cone.n) * sqrt(x * x + rho0_my * rho0_my)
    theta_inv = atan(x, rho0_my)
    lon = cone.lon_0 + (theta_inv / cone.n) * _RAD2DEG
    lat = (2.0 * atan((cone.rf / rho_inv)^(1.0 / cone.n)) - _FRAC_PI_2) * _RAD2DEG
    return (lon, lat)
end

"""
    lcc_forward(lon, lat, params) -> (x, y)

Spherical LCC forward from a parsed param map (builds the cone). Mirrors Python
`lcc_forward`.
"""
lcc_forward(lon::Real, lat::Real, params::AbstractDict) =
    lcc_forward_cone(lon, lat, lcc_cone(params))

"""
    lcc_inverse(x, y, params) -> (lon, lat)

Spherical LCC inverse from a parsed param map (builds the cone). Mirrors Python
`lcc_inverse`.
"""
lcc_inverse(x::Real, y::Real, params::AbstractDict) =
    lcc_inverse_cone(x, y, lcc_cone(params))

# --------------------------------------------------------------------------- #
# Reprojector — a resolved projected→geographic transform, built once.
# --------------------------------------------------------------------------- #

"""
    Reprojector

A resolved projected→geographic transform, built once from a `spatial_ref` and
applied per lattice point (`[`xy_to_lonlat`](@ref)`). The efficient core of the
driver: a `+proj=lcc` domain derives its (trig-heavy) [`LccCone`](@ref) a single
time rather than re-parsing/re-deriving for every cell corner. Concrete cases are
[`IdentityReprojector`](@ref) (`+proj=longlat` / missing) and
[`LccReprojector`](@ref) (`+proj=lcc`).
"""
abstract type Reprojector end

"""`+proj=longlat` (or a missing/empty `spatial_ref`): `(lon, lat) = (x, y)`."""
struct IdentityReprojector <: Reprojector end

"""`+proj=lcc`: apply the spherical LCC inverse with this cone."""
struct LccReprojector <: Reprojector
    cone::LccCone
end

"""
    xy_to_lonlat(reproj, x, y) -> (lon, lat)

Convert one projected `(x, y)` point to `(lon, lat)` under a [`Reprojector`](@ref).
"""
xy_to_lonlat(::IdentityReprojector, x::Real, y::Real) = (Float64(x), Float64(y))
xy_to_lonlat(r::LccReprojector, x::Real, y::Real) = lcc_inverse_cone(x, y, r.cone)

"""
    reprojector_from_spatial_ref(spatial_ref) -> Reprojector

Resolve the transform for a domain `spatial_ref` PROJ string. `nothing`/empty and
`+proj=longlat` (and its `latlong`/`lonlat` spellings) give an
[`IdentityReprojector`](@ref); `+proj=lcc` derives an [`LccCone`](@ref). Any other
projection has no backing reproject rule and raises. Mirrors the dispatch of
Python `reproject_xy_to_lonlat`.
"""
function reprojector_from_spatial_ref(spatial_ref::Union{AbstractString,Nothing})
    (spatial_ref === nothing || isempty(spatial_ref)) && return IdentityReprojector()
    params = parse_proj_string(spatial_ref)
    proj = something(proj_text(params, "proj"), "longlat")
    if proj == "longlat" || proj == "latlong" || proj == "lonlat"
        return IdentityReprojector()
    elseif proj == "lcc"
        return LccReprojector(lcc_cone(params))
    else
        throw(RegridError(
            "no reprojection rule for +proj=$(repr(proj)); supported: longlat, lcc"))
    end
end

"""
    reproject_xy_to_lonlat(x, y, spatial_ref) -> (lon, lat)

Convert a single projected `(x, y)` point to `(lon, lat)` per `spatial_ref`.
`+proj=longlat` (and a missing/empty `spatial_ref`) is the identity; `+proj=lcc`
applies the spherical LCC inverse; any other projection raises. Mirrors Python
`reproject_xy_to_lonlat` (scalar). Callers transforming a whole lattice should
build a [`Reprojector`](@ref) once (via [`reprojector_from_spatial_ref`](@ref))
and reuse it.
"""
reproject_xy_to_lonlat(x::Real, y::Real, spatial_ref::Union{AbstractString,Nothing}) =
    xy_to_lonlat(reprojector_from_spatial_ref(spatial_ref), x, y)
