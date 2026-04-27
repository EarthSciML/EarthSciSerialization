"""
    mms_evaluator.jl — Method-of-manufactured-solutions convergence harness for
    discretization rules (esm-ivo).

The evaluator complements [`eval_coeff`] by stepping back from a single stencil
coefficient to a full convergence sweep:

    rule JSON  +  manufactured-solution input  →  observed orders  ⇄  declared order

It is consumed by the ESD walker's Layer B (`run_mms_convergence`) and by any
ESM tooling that needs to verify a discretization rule's claimed analytic
accuracy against the existing `<rule>/fixtures/convergence/{input,expected}.esm`
fixtures.

The hard parts (operator semantics, unbound-variable detection, integer / float
literal rules) all live in [`parse_expression`] + [`evaluate`]; this file only
adds the loop and the manufactured-solution registry.
"""

using JSON3

# ============================================================
# Errors
# ============================================================

"""
    MMSEvaluatorError(code, message)

Raised by the MMS convergence harness. Stable codes:

- `E_MMS_BAD_ACCURACY`     — `accuracy` field cannot be parsed as `O(dx^N)`.
- `E_MMS_UNKNOWN_SOLUTION` — `manufactured_solution` description not registered.
- `E_MMS_BAD_FIXTURE`      — input/expected fixture is missing required fields.
- `E_MMS_NON_FINITE`       — stencil produced non-finite or zero error on some grid.
- `E_MMS_ORDER_DEFICIT`    — observed minimum order below the expected threshold.
"""
struct MMSEvaluatorError <: Exception
    code::String
    message::String
end

Base.showerror(io::IO, e::MMSEvaluatorError) =
    print(io, e.code, ": ", e.message)

# ============================================================
# Coefficient evaluation (JSON node → Float64)
# ============================================================

"""
    eval_coeff(node, bindings::Dict{String,Float64}) -> Float64

Evaluate a JSON-decoded coefficient node — `Number`, `String`, or
`AbstractDict` carrying `"op"`/`"args"` (and optional `"wrt"`/`"dim"`) — against
a binding table. Thin wrapper over `parse_expression` followed by `evaluate`.
"""
function eval_coeff(node, bindings::Dict{String,Float64})::Float64
    expr = parse_expression(node)
    return evaluate(expr, bindings)
end

# ============================================================
# Accuracy parsing — `O(dx^N)` → N
# ============================================================

# Match `O(<symbol>^<order>)` where <symbol> is dx, h, Δx, etc. The order may be
# a non-negative integer or float. Whitespace is tolerated. The fall-through
# `O(dx)` (no exponent) is accepted as order 1.
const _ACCURACY_RE = r"^\s*O\(\s*[A-Za-zΔ_][A-Za-z0-9_]*\s*(?:\^\s*([0-9]+(?:\.[0-9]+)?))?\s*\)\s*$"

"""
    parse_accuracy_order(s::AbstractString) -> Float64

Extract the analytic order N from a rule's `accuracy` string of the form
`"O(dx^N)"` (or `"O(h^N)"`, etc.). A bare `"O(dx)"` is order 1. Throws
`MMSEvaluatorError(E_MMS_BAD_ACCURACY, …)` on any other shape.
"""
function parse_accuracy_order(s::AbstractString)::Float64
    m = match(_ACCURACY_RE, String(s))
    m === nothing && throw(MMSEvaluatorError(
        "E_MMS_BAD_ACCURACY",
        "cannot parse accuracy string $(repr(s)); expected `O(<sym>^<order>)`"))
    captured = m.captures[1]
    captured === nothing && return 1.0
    return parse(Float64, captured)
end

# ============================================================
# Manufactured-solution registry
# ============================================================

"""
    ManufacturedSolution(name, sample, derivative, periodic, domain;
                         cell_average=nothing, edge_value=nothing)

A registered manufactured solution. `sample(x)` returns u(x); `derivative(x)`
returns du/dx. `periodic` and `domain` describe the sampling support so the
harness can wrap stencils correctly.

`cell_average(lo, hi)` is an optional analytic ū = (∫_lo^hi u dx) / (hi - lo).
When supplied it is used directly by `sampling: "cell_average"` sweeps and by
nonlinear reconstruction sweeps that consume cell-averaged inputs (e.g. WENO5);
when `nothing`, the harness falls back to a fixed 5-point Gauss–Legendre
quadrature (exact through degree 9 — well above what a 4th-order edge stencil
can exercise on a smooth solution).

`edge_value(x)` is an optional pointwise truth at a cell face — typically equal
to `sample(x)`, but kept distinct so that non-pointwise solutions can supply a
separate face evaluator. Required by nonlinear reconstruction sweeps.
"""
struct ManufacturedSolution
    name::Symbol
    sample::Function
    derivative::Function
    periodic::Bool
    domain::Tuple{Float64,Float64}
    cell_average::Union{Function,Nothing}
    edge_value::Union{Function,Nothing}
end

ManufacturedSolution(name::Symbol, sample::Function, derivative::Function,
                     periodic::Bool, domain::Tuple{Float64,Float64};
                     cell_average::Union{Nothing,Function}=nothing,
                     edge_value::Union{Nothing,Function}=nothing) =
    ManufacturedSolution(name, sample, derivative, periodic, domain,
                         cell_average, edge_value)

# Built-in: u(x) = sin(2π x) on [0,1] periodic; du/dx = 2π cos(2π x);
# ū over [a,b] = (cos(2π a) − cos(2π b)) / (2π (b − a)).
const _MMS_SIN_2PI_X_PERIODIC = ManufacturedSolution(
    :sin_2pi_x_periodic,
    x -> sin(2π * x),
    x -> 2π * cos(2π * x),
    true,
    (0.0, 1.0),
    (lo, hi) -> (cos(2π * lo) - cos(2π * hi)) / (2π * (hi - lo)),
    nothing,
)

# 5-point Gauss–Legendre nodes / weights on [-1, 1] (exact through degree 9).
# Used as the default cell-average integrator when a ManufacturedSolution does
# not carry an analytic `cell_average`.
const _GL5_NODES = (-0.9061798459386640,
                    -0.5384693101056831,
                     0.0,
                     0.5384693101056831,
                     0.9061798459386640)
const _GL5_WEIGHTS = (0.2369268850561891,
                      0.4786286704993665,
                      128.0 / 225.0,
                      0.4786286704993665,
                      0.2369268850561891)

# ū over [lo, hi] for the manufactured solution, using its analytic average if
# present and otherwise 5-point Gauss–Legendre on `sample`.
function _cell_average(ms::ManufacturedSolution, lo::Float64, hi::Float64)::Float64
    if ms.cell_average !== nothing
        return Float64(ms.cell_average(lo, hi))
    end
    half = 0.5 * (hi - lo)
    mid = 0.5 * (hi + lo)
    s = 0.0
    @inbounds for k in 1:5
        s += _GL5_WEIGHTS[k] * ms.sample(mid + half * _GL5_NODES[k])
    end
    return 0.5 * s
end

# Built-in: u(x) = sin(2π x + 1) on [0,1] periodic. The phase shift moves the
# critical points off every dyadic cell face on n ∈ {32,64,128,256}, which is
# the standard WENO5-JS smooth-MMS solution (avoids the omega_k → d_k stall
# at f'(x_{i+1/2}) = 0 — see Henrick, Aslam & Powers, JCP 2005). Supplies
# analytic `cell_average` and `edge_value` for nonlinear reconstruction sweeps.
const _MMS_PHASE_SHIFTED_SINE = ManufacturedSolution(
    :phase_shifted_sine,
    x -> sin(2π * x + 1.0),
    x -> 2π * cos(2π * x + 1.0),
    true,
    (0.0, 1.0),
    (a, b) -> (-cos(2π * b + 1.0) + cos(2π * a + 1.0)) / (2π * (b - a)),
    x -> sin(2π * x + 1.0),
)

# Built-in: u(z) = sin(2π z) on the unit column z ∈ [0, 1]; du/dz = 2π cos(2π z).
# Used by the 1D vertical-stencil MMS path (esm-bhv). The column has bounded
# support (faces at z = 0 and z = 1 are not periodic-equal), so periodic = false;
# centered-difference vertical stencils evaluated at cell centers stay inside the
# face index range without wrapping.
const _MMS_VERTICAL_SIN_2PI_Z_UNIT_COLUMN = ManufacturedSolution(
    :vertical_sin_2pi_z_unit_column,
    z -> sin(2π * z),
    z -> 2π * cos(2π * z),
    false,
    (0.0, 1.0),
    (lo, hi) -> (cos(2π * lo) - cos(2π * hi)) / (2π * (hi - lo)),
    nothing,
)

const _MMS_REGISTRY = Dict{Symbol,ManufacturedSolution}(
    :sin_2pi_x_periodic => _MMS_SIN_2PI_X_PERIODIC,
    :phase_shifted_sine => _MMS_PHASE_SHIFTED_SINE,
    :vertical_sin_2pi_z_unit_column => _MMS_VERTICAL_SIN_2PI_Z_UNIT_COLUMN,
)

"""
    ManufacturedSolution2D(name, sample, derivative_combo, domain_lon, domain_lat)

A registered 2D (lon, lat) manufactured solution. `sample(lon, lat)` returns
u(lon, lat); `derivative_combo(lon, lat, R)` returns the value the rule's
combined stencil should reproduce — for the latlon `grad`+`combine: "+"`
rule that is ∂_x u + ∂_y u with the spherical metric (∂_x = (1/(R cos_lat))
∂_lon, ∂_y = (1/R) ∂_lat). `domain_lon`/`domain_lat` describe the sampling
support so the harness can size the grid correctly. `domain_lon` is taken
to be periodic; `domain_lat` is open (poles excluded by an interior mask).
"""
struct ManufacturedSolution2D
    name::Symbol
    sample::Function          # (lon, lat) -> Float64
    derivative_combo::Function # (lon, lat, R) -> Float64
    domain_lon::Tuple{Float64,Float64}
    domain_lat::Tuple{Float64,Float64}
end

# Y_{2,0} normalized real spherical harmonic, expressed in (lat) since
# colatitude θ = π/2 − lat ⇒ cos θ = sin lat:
#   Y_{2,0}(lat) = (1/4) sqrt(5/π) (3 sin²(lat) − 1)
# It is independent of lon, so ∂_lon Y_{2,0} ≡ 0 (the lon stencil exactly
# cancels), while ∂_lat Y_{2,0} = (1/4) sqrt(5/π) · 6 sin(lat) cos(lat).
# Combined under the rule's `+`:  (1/R) · ∂_lat Y_{2,0}.
const _Y20_NORM = sqrt(5.0 / π) / 4.0

const _MMS_Y20_SPHERE = ManufacturedSolution2D(
    :Y_2_0_sphere,
    (lon, lat) -> _Y20_NORM * (3 * sin(lat)^2 - 1),
    (lon, lat, R) -> (1.0 / R) * _Y20_NORM * 6 * sin(lat) * cos(lat),
    (0.0, 2π),
    (-π / 2, π / 2),
)

const _MMS_REGISTRY_2D = Dict{Symbol,ManufacturedSolution2D}(
    :Y_2_0_sphere => _MMS_Y20_SPHERE,
)

"""
    ReconstructionManufacturedSolution2D(name, sample, cell_average,
                                         face_average_x, face_average_y, domain)

A registered 2D scalar manufactured solution for nonlinear reconstruction
sweeps (e.g. axis-split 2D WENO5). On a periodic Cartesian rectangle, the
input vector is the cell-averaged scalar and the truth at a cell face is the
perpendicular-axis-averaged value at that face — this lets a per-axis WENO5
sweep on cell averages compare against the analytic edge value on a smooth
manufactured field.

- `sample(x, y)` is the pointwise scalar.
- `cell_average(xlo, xhi, ylo, yhi)` is the analytic cell mean.
- `face_average_x(xface, ylo, yhi)` is the y-average of `sample` at the
  vertical face x = xface (the truth for an x-axis WENO5 sweep against
  cell-averaged input).
- `face_average_y(xlo, xhi, yface)` is the x-average at the horizontal face
  y = yface.
- `domain = ((xlo, xhi), (ylo, yhi))` is the periodic rectangle.
"""
struct ReconstructionManufacturedSolution2D
    name::Symbol
    sample::Function          # (x, y) -> Float64
    cell_average::Function    # (xlo, xhi, ylo, yhi) -> Float64
    face_average_x::Function  # (xface, ylo, yhi) -> Float64
    face_average_y::Function  # (xlo, xhi, yface) -> Float64
    domain::Tuple{Tuple{Float64,Float64},Tuple{Float64,Float64}}
end

# Built-in: u(x, y) = sin(2π x + 1) · sin(2π y + 1) on [0,1]². Separable, so
# both axes' WENO5 sweeps see the canonical Henrick-Aslam-Powers
# phase-shifted sine in their reconstruction direction; the perpendicular
# axis contributes only an exact analytic factor (the cell or face average
# of the orthogonal sine), keeping the L∞ error a clean function of the
# along-axis grid spacing.
const _MMS_PHASE_SHIFTED_SINE_PRODUCT_2D = ReconstructionManufacturedSolution2D(
    :phase_shifted_sine_product_2d,
    (x, y) -> sin(2π * x + 1.0) * sin(2π * y + 1.0),
    (xlo, xhi, ylo, yhi) ->
        ((-cos(2π * xhi + 1.0) + cos(2π * xlo + 1.0)) / (2π * (xhi - xlo))) *
        ((-cos(2π * yhi + 1.0) + cos(2π * ylo + 1.0)) / (2π * (yhi - ylo))),
    (xf, ylo, yhi) ->
        sin(2π * xf + 1.0) *
        ((-cos(2π * yhi + 1.0) + cos(2π * ylo + 1.0)) / (2π * (yhi - ylo))),
    (xlo, xhi, yf) ->
        ((-cos(2π * xhi + 1.0) + cos(2π * xlo + 1.0)) / (2π * (xhi - xlo))) *
        sin(2π * yf + 1.0),
    ((0.0, 1.0), (0.0, 1.0)),
)

const _MMS_REGISTRY_2D_RECONSTRUCTION = Dict{Symbol,ReconstructionManufacturedSolution2D}(
    :phase_shifted_sine_product_2d => _MMS_PHASE_SHIFTED_SINE_PRODUCT_2D,
)

"""
    register_manufactured_solution!(ms::ManufacturedSolution)
    register_manufactured_solution!(ms::ManufacturedSolution2D)
    register_manufactured_solution!(ms::ReconstructionManufacturedSolution2D)

Add or replace a manufactured solution in the registry. Returns `ms`.
1D, 2D-sphere, and 2D-reconstruction entries live in independent registries
keyed by name.
"""
function register_manufactured_solution!(ms::ManufacturedSolution)
    _MMS_REGISTRY[ms.name] = ms
    return ms
end

function register_manufactured_solution!(ms::ManufacturedSolution2D)
    _MMS_REGISTRY_2D[ms.name] = ms
    return ms
end

function register_manufactured_solution!(ms::ReconstructionManufacturedSolution2D)
    _MMS_REGISTRY_2D_RECONSTRUCTION[ms.name] = ms
    return ms
end

"""
    lookup_manufactured_solution(description) -> ManufacturedSolution

Resolve a 1D `manufactured_solution` description from an `input.esm` to a
registered solution. Accepts either a string (legacy form — loose-matched on
punctuation-stripped lowercase, e.g. `"sin(2*pi*x) on [0,1] periodic; …"` →
`:sin_2pi_x_periodic`) or an `AbstractDict` (current form — exact match on a
`name` key, then string-fallback on the `expression` key).
"""
function lookup_manufactured_solution(description::AbstractDict)::ManufacturedSolution
    if haskey(description, "name")
        sym = Symbol(String(description["name"]))
        haskey(_MMS_REGISTRY, sym) && return _MMS_REGISTRY[sym]
    end
    if haskey(description, "expression")
        return lookup_manufactured_solution(String(description["expression"]))
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no manufactured solution matches dict $(repr(description)); " *
        "register one with register_manufactured_solution!"))
end

function lookup_manufactured_solution(description::AbstractString)::ManufacturedSolution
    norm = lowercase(replace(String(description), r"[\s\*]" => ""))
    if occursin("sin(2pix+1", norm) || occursin("sin(2πx+1", norm)
        return _MMS_REGISTRY[:phase_shifted_sine]
    end
    if occursin("sin(2piz", norm) || occursin("sin(2πz", norm)
        return _MMS_REGISTRY[:vertical_sin_2pi_z_unit_column]
    end
    if occursin("sin(2pi", norm) || occursin("sin(2π", norm)
        return _MMS_REGISTRY[:sin_2pi_x_periodic]
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no manufactured solution registered for $(repr(description)); " *
        "register one with register_manufactured_solution!"))
end

"""
    lookup_manufactured_solution_2d(description::AbstractString) -> ManufacturedSolution2D

Resolve a 2D `manufactured_solution` description string to a registered
sphere/lat-lon solution. Matching is loose: alphanumerics-only comparison,
so `"Y_{2,0} spherical harmonic on the unit sphere"` resolves to
`:Y_2_0_sphere`.
"""
function lookup_manufactured_solution_2d(description::AbstractString)::ManufacturedSolution2D
    norm = replace(lowercase(String(description)), r"[^a-z0-9]" => "")
    if occursin("y20", norm) || occursin("y2_0", norm) ||
       occursin("sphericalharmonic20", norm) || occursin("sphericalharmonicy20", norm)
        return _MMS_REGISTRY_2D[:Y_2_0_sphere]
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no 2D manufactured solution registered for $(repr(description)); " *
        "register one with register_manufactured_solution!"))
end

"""
    lookup_manufactured_solution_2d_reconstruction(description) ->
        ReconstructionManufacturedSolution2D

Resolve a 2D `manufactured_solution` description for axis-split reconstruction
sweeps (e.g. 2D WENO5). Accepts either a dict (exact match on a `name` key,
then string-fallback on `expression`) or a string (loose alphanumeric match).
The built-in `:phase_shifted_sine_product_2d` is the canonical separable
phase-shifted sine product on [0,1]² used by the WENO5 cross-axis sweep.
"""
function lookup_manufactured_solution_2d_reconstruction(description::AbstractDict)::ReconstructionManufacturedSolution2D
    if haskey(description, "name")
        sym = Symbol(String(description["name"]))
        haskey(_MMS_REGISTRY_2D_RECONSTRUCTION, sym) &&
            return _MMS_REGISTRY_2D_RECONSTRUCTION[sym]
    end
    if haskey(description, "expression")
        return lookup_manufactured_solution_2d_reconstruction(String(description["expression"]))
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no 2D reconstruction manufactured solution matches dict $(repr(description)); " *
        "register one with register_manufactured_solution!"))
end

function lookup_manufactured_solution_2d_reconstruction(description::AbstractString)::ReconstructionManufacturedSolution2D
    norm = replace(lowercase(String(description)), r"[^a-z0-9]" => "")
    if occursin("phaseshiftedsineproduct", norm) ||
       occursin("phaseshiftedsineprod2d", norm) ||
       occursin("sin2pix1sin2piy1", norm)
        return _MMS_REGISTRY_2D_RECONSTRUCTION[:phase_shifted_sine_product_2d]
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no 2D reconstruction manufactured solution registered for $(repr(description)); " *
        "register one with register_manufactured_solution!"))
end

# ============================================================
# Rule extraction (input → discretization spec)
# ============================================================

# Resolve the discretization spec from a rule JSON. Accepts either a wrapping
# `{"discretizations": {<name>: spec}}` form or a bare spec dict. Returns the
# spec dict (which carries `stencil`, `accuracy`, etc.).
function _resolve_rule_spec(rule_json::AbstractDict, name::AbstractString)
    if haskey(rule_json, "discretizations")
        d = rule_json["discretizations"]
        d isa AbstractDict || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "rule json `discretizations` must be a mapping, got $(typeof(d))"))
        haskey(d, name) || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "rule json has no discretization named $(repr(name)) " *
            "(available: $(collect(keys(d))))"))
        return d[name]
    end
    return rule_json
end

# ============================================================
# Cell-indexed bindings (per-cell metric callables)
# ============================================================

"""
    CellBindings(scalars, per_cell)

Bundle of stencil-coefficient bindings that mixes index-independent scalars
(`dx`, `dlon`, `R`, …) with per-cell callables (e.g. `cos_lat[j]`,
`area[i,j]`). `bindings_at(cb, idx...)` materializes a plain
`Dict{String,Float64}` for cell `idx` by evaluating each per-cell entry at
that index. Used by [`apply_stencil_2d_latlon`] and any future grid-aware
stencil applier so that AST coefficients carrying `cos_lat` (or any
metric field) can be evaluated cell-by-cell with no walker-side
reimplementation.
"""
struct CellBindings
    scalars::Dict{String,Float64}
    per_cell::Dict{String,Function}  # name -> (idx...) -> Float64
end

CellBindings(scalars::Dict{String,Float64}) =
    CellBindings(scalars, Dict{String,Function}())

"""
    bindings_at(cb::CellBindings, idx...) -> Dict{String,Float64}

Materialize the per-cell binding dict for cell `idx`. Per-cell entries
override scalar entries with the same name.
"""
function bindings_at(cb::CellBindings, idx...)::Dict{String,Float64}
    out = copy(cb.scalars)
    for (name, fn) in cb.per_cell
        out[name] = fn(idx...)
    end
    return out
end

# ============================================================
# Stencil application (1D periodic, cell-centered)
# ============================================================

"""
    apply_stencil_periodic_1d(stencil_json, u::Vector{Float64},
                              bindings::Dict{String,Float64};
                              sub_stencil=nothing) -> Vector{Float64}

Apply a 1D Cartesian stencil to the periodic sample vector `u`. Each entry of
`stencil_json` must carry `selector.offset` (Int) and `coeff` (an AST node).
The coefficient is evaluated once per call against `bindings`. The result has
the same length as `u`.

`stencil_json` may also be an `AbstractDict` mapping sub-stencil names to
entry lists — the PPM-style "multi-output" rule layout where one rule emits
several stencils (e.g. left-edge value, right-edge value). Pass `sub_stencil`
to select which named entry to apply; an unspecified or unknown name on a
multi-stencil rule throws `MMSEvaluatorError(E_MMS_BAD_FIXTURE, …)`.

Used by [`mms_convergence`] to drive the manufactured-solution sweep without
re-implementing the stencil semantics in the walker.
"""
function apply_stencil_periodic_1d(stencil_json,
                                   u::Vector{Float64},
                                   bindings::Dict{String,Float64};
                                   sub_stencil::Union{Nothing,AbstractString}=nothing)::Vector{Float64}
    entries = _resolve_substencil(stencil_json, sub_stencil)
    n = length(u)
    coeff_pairs = Vector{Tuple{Int,Float64}}(undef, length(entries))
    for (k, s) in enumerate(entries)
        sel = s["selector"]
        coeff_pairs[k] = (Int(sel["offset"]), eval_coeff(s["coeff"], bindings))
    end
    out = zeros(Float64, n)
    @inbounds for i in 1:n
        acc = 0.0
        for (off, c) in coeff_pairs
            j = mod1(i + off, n)
            acc += c * u[j]
        end
        out[i] = acc
    end
    return out
end

# Resolve `stencil_json` to a list of stencil entries. A list is returned as-is.
# A dict is treated as a multi-output rule keyed by sub-stencil name; the caller
# must select one via `sub_stencil`. The bare-list form keeps every existing
# single-stencil rule (centered_2nd_uniform, upwind_1st_advection, …) working
# without modification.
function _resolve_substencil(stencil_json,
                             sub_stencil::Union{Nothing,AbstractString})
    if stencil_json isa AbstractDict
        sub_stencil === nothing && throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "rule has multi-stencil mapping; input.esm must select one via " *
            "`sub_stencil` (available: $(collect(keys(stencil_json))))"))
        haskey(stencil_json, sub_stencil) || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "rule has no sub-stencil $(repr(sub_stencil)) " *
            "(available: $(collect(keys(stencil_json))))"))
        return stencil_json[sub_stencil]
    end
    sub_stencil === nothing || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "`sub_stencil=$(repr(sub_stencil))` was requested but rule carries " *
        "a single stencil list, not a multi-stencil mapping"))
    return stencil_json
end

# ============================================================
# Output-kind selector
# ============================================================

"""
    OUTPUT_KINDS

Tuple of output-kind selectors recognised by [`mms_convergence`]. The selector
controls which analytic reference the per-cell stencil output is compared
against and at which point along the cell the reference is sampled:

| Kind                        | Sample point per cell `i`            | Reference        |
|-----------------------------|--------------------------------------|------------------|
| `"derivative_at_cell_center"` (default) | `lo + (i - 0.5) dx`        | `ms.derivative`  |
| `"value_at_cell_center"`    | `lo + (i - 0.5) dx`                  | `ms.sample`      |
| `"value_at_edge_left"`      | `lo + (i - 1)   dx`                  | `ms.sample`      |
| `"value_at_edge_right"`     | `lo + i         dx`                  | `ms.sample`      |

PPM-style edge reconstructions surface as `value_at_edge_left` /
`value_at_edge_right`; the parabola-pass reconstruction (see
[`parabola_reconstruct_periodic_1d`]) further composes them.
"""
const OUTPUT_KINDS = (
    "derivative_at_cell_center",
    "value_at_cell_center",
    "value_at_edge_left",
    "value_at_edge_right",
)

# Sample the analytic reference at the per-cell point implied by `output_kind`.
# Returns the `n`-vector that the stencil output is compared against.
function _reference_samples(ms::ManufacturedSolution,
                            output_kind::AbstractString,
                            domain_lo::Float64,
                            dx::Float64,
                            n::Int)::Vector{Float64}
    if output_kind == "derivative_at_cell_center"
        return [ms.derivative(domain_lo + (i - 0.5) * dx) for i in 1:n]
    elseif output_kind == "value_at_cell_center"
        return [ms.sample(domain_lo + (i - 0.5) * dx) for i in 1:n]
    elseif output_kind == "value_at_edge_left"
        return [ms.sample(domain_lo + (i - 1) * dx) for i in 1:n]
    elseif output_kind == "value_at_edge_right"
        return [ms.sample(domain_lo + i * dx) for i in 1:n]
    end
    throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "unknown output_kind $(repr(output_kind)); " *
        "expected one of $(collect(OUTPUT_KINDS))"))
end

# ============================================================
# Parabola pass — PPM sub-cell reconstruction
# ============================================================

"""
    parabola_reconstruct_periodic_1d(stencils_json, u_bar, bindings;
                                     left_edge_stencil, right_edge_stencil,
                                     subcell_points) -> (xs, vals)

Given a vector of cell-averaged samples `u_bar` and a multi-stencil mapping
`stencils_json` carrying named entries for the left- and right-edge values,
reconstruct the Colella–Woodward (1984) PPM parabola in each cell and
evaluate it at the supplied normalised sub-cell points.

Inside cell `i` with edge values `u_L`, `u_R` and average `ū`, the parabola is

    u(ξ) = u_L + ξ · (Δu + u₆ · (1 − ξ)),
    Δu = u_R − u_L,
    u₆ = 6 (ū − ½ (u_L + u_R)).

`subcell_points` is a vector of `ξ ∈ [0, 1]` sample positions; the reconstruction
is evaluated at `ξ` in every cell, yielding a flattened length-`length(u_bar) *
length(subcell_points)` vector. The returned `xs` are the matching absolute
positions assuming periodic domain `[domain_lo, domain_lo + length(u_bar)·dx)`,
with `domain_lo` and `dx` carried in `bindings` under the keys `"domain_lo"`
and `"dx"`.
"""
function parabola_reconstruct_periodic_1d(stencils_json,
                                          u_bar::Vector{Float64},
                                          bindings::Dict{String,Float64};
                                          left_edge_stencil::AbstractString,
                                          right_edge_stencil::AbstractString,
                                          subcell_points::Vector{Float64})::Tuple{Vector{Float64},Vector{Float64}}
    stencils_json isa AbstractDict || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "parabola pass requires a multi-stencil mapping; got $(typeof(stencils_json))"))
    haskey(bindings, "dx") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "parabola pass requires `dx` in bindings"))
    haskey(bindings, "domain_lo") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "parabola pass requires `domain_lo` in bindings"))
    all(0.0 .<= subcell_points .<= 1.0) || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "subcell_points must lie in [0,1]; got $(subcell_points)"))

    u_L = apply_stencil_periodic_1d(stencils_json, u_bar, bindings;
                                    sub_stencil=left_edge_stencil)
    u_R = apply_stencil_periodic_1d(stencils_json, u_bar, bindings;
                                    sub_stencil=right_edge_stencil)

    n = length(u_bar)
    dx = bindings["dx"]
    lo = bindings["domain_lo"]
    q = length(subcell_points)
    xs = Vector{Float64}(undef, n * q)
    vals = Vector{Float64}(undef, n * q)
    @inbounds for i in 1:n
        L = u_L[i]
        R = u_R[i]
        Δu = R - L
        u6 = 6.0 * (u_bar[i] - 0.5 * (L + R))
        cell_lo = lo + (i - 1) * dx
        for (jq, ξ) in enumerate(subcell_points)
            idx = (i - 1) * q + jq
            xs[idx] = cell_lo + ξ * dx
            vals[idx] = L + ξ * (Δu + u6 * (1.0 - ξ))
        end
    end
    return xs, vals
end

# ============================================================
# Stencil application (2D structured lat-lon, cell-centered)
# ============================================================

"""
    apply_stencil_2d_latlon(stencil_json, u::Matrix{Float64},
                            cb::CellBindings) -> (out::Matrix{Float64},
                                                  interior::BitMatrix)

Apply a 2D `kind: "latlon"` stencil to the cell-centered sample matrix
`u` of shape `(nlon, nlat)`. Each entry of `stencil_json` must carry a
selector with `kind == "latlon"`, `axis ∈ {"lon", "lat"}`, and
`offset::Int`, plus a `coeff` AST node. The lon axis is treated as
periodic (modulo `nlon`); the lat axis is non-periodic — cells where the
stencil would reach `j < 1` or `j > nlat` are flagged in the returned
`interior` mask so callers can compute L∞ on the interior only (poles
excluded).

The coefficient AST is evaluated cell-by-cell against `bindings_at(cb, i, j)`,
so per-cell metric fields (`cos_lat`, `R`, `dlon`, `dlat`, …) can vary
freely with index. The combine rule is `+` (sum of contributions); other
combines are not yet supported.
"""
function apply_stencil_2d_latlon(stencil_json,
                                 u::Matrix{Float64},
                                 cb::CellBindings)::Tuple{Matrix{Float64},BitMatrix}
    nlon, nlat = size(u)
    lon_pairs = Tuple{Int,Any}[]
    lat_pairs = Tuple{Int,Any}[]
    for s in stencil_json
        sel = s["selector"]
        kind = String(get(sel, "kind", ""))
        kind == "latlon" || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "apply_stencil_2d_latlon requires `selector.kind == \"latlon\"`, " *
            "got $(repr(kind))"))
        axis = String(sel["axis"])
        off = Int(sel["offset"])
        if axis == "lon"
            push!(lon_pairs, (off, s["coeff"]))
        elseif axis == "lat"
            push!(lat_pairs, (off, s["coeff"]))
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "latlon selector axis must be \"lon\" or \"lat\", got $(repr(axis))"))
        end
    end
    out = zeros(Float64, nlon, nlat)
    # interior[i,j] = true iff every lat offset stays in [1, nlat] for cell (i,j).
    interior = trues(nlon, nlat)
    max_neg_lat = isempty(lat_pairs) ? 0 : -minimum(off for (off, _) in lat_pairs)
    max_pos_lat = isempty(lat_pairs) ? 0 :  maximum(off for (off, _) in lat_pairs)
    for j in 1:nlat
        in_interior = (j - max_neg_lat >= 1) && (j + max_pos_lat <= nlat)
        for i in 1:nlon
            interior[i, j] = in_interior
            in_interior || continue
            b = bindings_at(cb, i, j)
            acc = 0.0
            for (off, coeff_node) in lon_pairs
                ii = mod1(i + off, nlon)
                acc += eval_coeff(coeff_node, b) * u[ii, j]
            end
            for (off, coeff_node) in lat_pairs
                jj = j + off
                acc += eval_coeff(coeff_node, b) * u[i, jj]
            end
            out[i, j] = acc
        end
    end
    return out, interior
end

# ============================================================
# Stencil application (2D Arakawa C-grid staggered)
# ============================================================

# Canonicalise an arakawa selector axis. Accepts both the spec-canonical
# placeholder forms ("$x", "$y") and the bare ("x", "y") shorthand so future
# rule files can drop the `$` if the schema relaxes.
function _arakawa_axis_canonical(axis::AbstractString)
    a = String(axis)
    (a == "\$x" || a == "x") && return "x"
    (a == "\$y" || a == "y") && return "y"
    return nothing
end

"""
    apply_stencil_2d_arakawa(stencil_json,
                             ux::Matrix{Float64}, uy::Matrix{Float64},
                             cb::CellBindings) -> Matrix{Float64}

Apply a 2D `kind: "arakawa"` C-grid staggered stencil to the velocity
components `ux` (sampled at face_x positions, shape `(nx+1, ny)`) and `uy`
(sampled at face_y positions, shape `(nx, ny+1)`). Returns a cell-centered
matrix of shape `(nx, ny)`.

Each entry of `stencil_json` must carry a selector with
`kind == "arakawa"`, `stagger ∈ {"face_x", "face_y"}`, an `axis` matching the
stagger (`"\$x"` for `face_x`, `"\$y"` for `face_y`; bare `"x"`/`"y"` are also
accepted), plus an `Int` `offset`. The `coeff` AST is evaluated cell-by-cell
against `bindings_at(cb, i, j)` so per-cell metric fields (`dx`, `dy`, plus
any caller-supplied per-cell entries) can vary freely.

The combine rule is `+` (sum of contributions).

Both axes are treated as periodic (face indices wrap modulo `nx` / `ny`); the
canonical Arakawa C convention stores `(nx+1) × ny` and `nx × (ny+1)` faces
with the first/last row redundantly filled, matching the `divergence_arakawa_c`
canonical fixture. Non-periodic boundaries are out of scope for this
applier — a future bead can add an `interior` mask analogous to
[`apply_stencil_2d_latlon`].

# Example

```julia
ux = [(sin(2π*(i-1)*dx) for j in 1:ny) for i in 1:nx+1]
uy = zeros(nx, ny+1)
cb = CellBindings(Dict("dx" => dx, "dy" => dy))
div = apply_stencil_2d_arakawa(stencil, ux, uy, cb)
```
"""
function apply_stencil_2d_arakawa(stencil_json,
                                   ux::Matrix{Float64},
                                   uy::Matrix{Float64},
                                   cb::CellBindings)::Matrix{Float64}
    nx_x_faces, ny_x_cells = size(ux)
    nx_y_cells, ny_y_faces = size(uy)
    nx_x_faces >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "ux must have shape (nx+1, ny) with nx ≥ 1; got $(size(ux))"))
    ny_y_faces >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "uy must have shape (nx, ny+1) with ny ≥ 1; got $(size(uy))"))
    nx = nx_x_faces - 1
    ny = ny_y_faces - 1
    nx == nx_y_cells || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "ux and uy disagree on nx: ux→$(nx) (size(ux)=$(size(ux))), " *
        "uy→$(nx_y_cells) (size(uy)=$(size(uy)))"))
    ny == ny_x_cells || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "ux and uy disagree on ny: ux→$(ny_x_cells) (size(ux)=$(size(ux))), " *
        "uy→$(ny) (size(uy)=$(size(uy)))"))

    fx_pairs = Tuple{Int,Any}[]
    fy_pairs = Tuple{Int,Any}[]
    for s in stencil_json
        sel = s["selector"]
        kind = String(get(sel, "kind", ""))
        kind == "arakawa" || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "apply_stencil_2d_arakawa requires `selector.kind == \"arakawa\"`, " *
            "got $(repr(kind))"))
        stagger = String(get(sel, "stagger", ""))
        axis_raw = String(get(sel, "axis", ""))
        canonical = _arakawa_axis_canonical(axis_raw)
        canonical === nothing && throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "arakawa selector axis must be \"\$x\" or \"\$y\" " *
            "(or \"x\"/\"y\"), got $(repr(axis_raw))"))
        off = Int(sel["offset"])
        if stagger == "face_x"
            canonical == "x" || throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "arakawa stagger \"face_x\" must pair with axis \"\$x\", " *
                "got axis $(repr(axis_raw))"))
            push!(fx_pairs, (off, s["coeff"]))
        elseif stagger == "face_y"
            canonical == "y" || throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "arakawa stagger \"face_y\" must pair with axis \"\$y\", " *
                "got axis $(repr(axis_raw))"))
            push!(fy_pairs, (off, s["coeff"]))
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "arakawa selector stagger must be \"face_x\" or \"face_y\" " *
                "(got $(repr(stagger))); cell_center / vertex selectors are " *
                "not yet supported"))
        end
    end

    # The C-grid storage gives ux at faces 1..nx+1 and uy at faces 1..ny+1, so
    # direct indexing `ux[i+off, j]` and `uy[i, j+off]` covers offset ∈ 0:1
    # without any wrap. Each face value at the periodic seam (face nx+1, face
    # ny+1) is supplied by the caller as the periodic-equal copy of face 1, so
    # for periodic MMS the seam is automatic; for non-periodic boundary cases
    # (canonical fixtures) the explicit boundary face values are honoured.
    nfx = nx + 1
    nfy = ny + 1
    out = zeros(Float64, nx, ny)
    @inbounds for j in 1:ny, i in 1:nx
        b = bindings_at(cb, i, j)
        acc = 0.0
        for (off, coeff_node) in fx_pairs
            ii = i + off
            (1 <= ii <= nfx) || throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "arakawa face_x offset $(off) at cell i=$(i) is out of range " *
                "for ux of shape $(size(ux)); only offsets that keep " *
                "1 ≤ i+offset ≤ nx+1 are supported"))
            acc += eval_coeff(coeff_node, b) * ux[ii, j]
        end
        for (off, coeff_node) in fy_pairs
            jj = j + off
            (1 <= jj <= nfy) || throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "arakawa face_y offset $(off) at cell j=$(j) is out of range " *
                "for uy of shape $(size(uy)); only offsets that keep " *
                "1 ≤ j+offset ≤ ny+1 are supported"))
            acc += eval_coeff(coeff_node, b) * uy[i, jj]
        end
        out[i, j] = acc
    end
    return out
end

# ============================================================
# Stencil application (1D vertical, face-staggered → cell-centered)
# ============================================================

"""
    apply_stencil_1d_vertical(stencil_json,
                              u_face::Vector{Float64},
                              cb::CellBindings) -> Vector{Float64}

Apply a 1D `kind: "vertical"` stencil to a vertical-face sample vector
`u_face` of shape `(nz+1,)`. Returns a cell-centered vector of shape `(nz,)`.

Each entry of `stencil_json` must carry a selector with
`kind == "vertical"`, `stagger ∈ {"face_top", "face_bottom"}`, and an `Int`
`offset`. The cell→face mapping is

- `stagger == "face_bottom"` with offset `o` reads `u_face[i + o]`
- `stagger == "face_top"`    with offset `o` reads `u_face[i + 1 + o]`

so a centered first-difference vertical-derivative stencil is

```julia
stencil = [
    Dict("selector" => Dict("kind" => "vertical",
                            "stagger" => "face_bottom", "offset" => 0),
         "coeff"    => Dict("op" => "/", "args" => Any[-1, "dz"])),
    Dict("selector" => Dict("kind" => "vertical",
                            "stagger" => "face_top",    "offset" => 0),
         "coeff"    => Dict("op" => "/", "args" => Any[ 1, "dz"])),
]
```

Both faces and cells are non-periodic — the column has finite support, with
face 1 at `z_lo` and face `nz+1` at `z_hi`. Offsets that would step outside
`[1, nz+1]` throw `MMSEvaluatorError(E_MMS_BAD_FIXTURE, …)`; for a centered
two-point stencil this is never the case, so no boundary mask is needed.

The `coeff` AST is evaluated cell-by-cell against `bindings_at(cb, i)`, so
non-uniform spacing (per-cell `dz`, `face_top`, `face_bottom`, `z`) can be
plumbed via `cb.per_cell` without changing the stencil rule.

The combine rule is `+` (sum of contributions); other combines are not yet
supported.
"""
function apply_stencil_1d_vertical(stencil_json,
                                   u_face::Vector{Float64},
                                   cb::CellBindings)::Vector{Float64}
    nf = length(u_face)
    nf >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "u_face must have shape (nz+1,) with nz ≥ 1; got length $(nf)"))
    nz = nf - 1

    bot_pairs = Tuple{Int,Any}[]   # face_bottom: u_face[i + offset]
    top_pairs = Tuple{Int,Any}[]   # face_top:    u_face[i + 1 + offset]
    for s in stencil_json
        sel = s["selector"]
        kind = String(get(sel, "kind", ""))
        kind == "vertical" || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "apply_stencil_1d_vertical requires `selector.kind == \"vertical\"`, " *
            "got $(repr(kind))"))
        stagger = String(get(sel, "stagger", ""))
        off = Int(sel["offset"])
        if stagger == "face_bottom"
            push!(bot_pairs, (off, s["coeff"]))
        elseif stagger == "face_top"
            push!(top_pairs, (off, s["coeff"]))
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "vertical selector stagger must be \"face_top\" or \"face_bottom\" " *
                "(got $(repr(stagger))); cell_center / vertex selectors are " *
                "not yet supported"))
        end
    end

    out = zeros(Float64, nz)
    @inbounds for i in 1:nz
        b = bindings_at(cb, i)
        acc = 0.0
        for (off, coeff_node) in bot_pairs
            ii = i + off
            (1 <= ii <= nf) || throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "vertical face_bottom offset $(off) at cell i=$(i) is out of " *
                "range for u_face of length $(nf); only offsets that keep " *
                "1 ≤ i+offset ≤ nz+1 are supported"))
            acc += eval_coeff(coeff_node, b) * u_face[ii]
        end
        for (off, coeff_node) in top_pairs
            ii = i + 1 + off
            (1 <= ii <= nf) || throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "vertical face_top offset $(off) at cell i=$(i) is out of " *
                "range for u_face of length $(nf); only offsets that keep " *
                "1 ≤ i+1+offset ≤ nz+1 are supported"))
            acc += eval_coeff(coeff_node, b) * u_face[ii]
        end
        out[i] = acc
    end
    return out
end

# Detect whether a stencil is 2D lat-lon by selector kind. Returns the kind
# string of the first entry; throws if entries disagree. Multi-stencil
# mappings (PPM-style {name: [entries…]}) are flat-cartesian by construction
# and report kind "cartesian" without inspecting their bodies.
function _stencil_kind(stencil_json)::String
    if stencil_json isa AbstractDict
        return "cartesian"
    end
    isempty(stencil_json) && throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE", "stencil is empty"))
    first_kind = String(get(first(stencil_json)["selector"], "kind", ""))
    for s in stencil_json
        k = String(get(s["selector"], "kind", ""))
        k == first_kind || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "mixed selector kinds in stencil: $(repr(first_kind)) and $(repr(k))"))
    end
    return first_kind
end

# ============================================================
# Convergence sweep
# ============================================================

"""
    MMSConvergenceResult(grids, errors, orders, observed_min_order, declared_order)

Outcome of a manufactured-solution convergence sweep. `errors[i]` is the L∞
error on grid `grids[i]`; `orders[i]` is the empirical refinement order
between `grids[i]` and `grids[i+1]` (so `length(orders) == length(grids)-1`).
"""
struct MMSConvergenceResult
    grids::Vector{Int}
    errors::Vector{Float64}
    orders::Vector{Float64}
    observed_min_order::Float64
    declared_order::Float64
end

"""
    mms_convergence(rule_json, input_json; manufactured=nothing) -> MMSConvergenceResult

Run a manufactured-solution convergence sweep using the rule's stencil and the
fixture's grid sequence. The rule's `accuracy` string is parsed to populate
`declared_order`; the actual numeric stencil is exercised via the ESS AST
evaluator (no walker-side reimplementation).

`rule_json` may be the full rule file (with a top-level `discretizations` key)
or just the inner spec dict. `input_json` is the parsed `input.esm` and must
carry `rule`, `manufactured_solution`, `sampling`, and `grids`.

`manufactured` defaults to `nothing`, in which case the harness resolves the
solution from `input_json["manufactured_solution"]` via
[`lookup_manufactured_solution`]. Pass an explicit `ManufacturedSolution` to
override (useful for tests with custom u(x)).

# Multi-stencil rules (PPM-style)

For rules that emit several named stencils (e.g. PPM left-edge / right-edge
reconstruction), the rule's `stencil` field is a mapping `{name: [entries…]}`
rather than a bare list. Two `input_json` keys then drive the sweep:

- `"sub_stencil"` — name of the entry to apply. Required when the rule
  carries a multi-stencil mapping.
- `"output_kind"` — one of [`OUTPUT_KINDS`](@ref); selects the per-cell
  reference point and analytic field. Defaults to `"derivative_at_cell_center"`,
  preserving every existing single-stencil rule's contract.

A `reconstruction` block in `input_json` enables the PPM parabola pass
(see [`parabola_reconstruct_periodic_1d`]):

```json
{ "reconstruction": {
    "kind": "parabola",
    "left_edge_stencil":  "u_L",
    "right_edge_stencil": "u_R",
    "subcell_points":     [0.1, 0.3, 0.5, 0.7, 0.9]
}}
```

When present, the harness measures pointwise L∞ error of the parabolic
reconstruction against the manufactured solution at every sub-cell sample.
"""
function mms_convergence(rule_json::AbstractDict, input_json::AbstractDict;
                         manufactured=nothing)::MMSConvergenceResult
    rule_name = String(input_json["rule"])
    spec = _resolve_rule_spec(rule_json, rule_name)
    if _mms_rule_kind(spec) === :weno5
        return mms_weno5_convergence(rule_json, input_json; manufactured=manufactured)
    end
    haskey(spec, "stencil") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "rule $(repr(rule_name)) has no `stencil` field"))
    stencil = spec["stencil"]
    declared = haskey(spec, "accuracy") ?
        parse_accuracy_order(String(spec["accuracy"])) :
        throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "rule $(repr(rule_name)) has no `accuracy` field"))

    sampling = String(get(input_json, "sampling", "cell_center"))
    sampling in ("cell_center", "cell_average") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "sampling must be \"cell_center\" or \"cell_average\" (got $(repr(sampling)))"))

    kind = _stencil_kind(stencil)
    if kind == "latlon"
        return _mms_convergence_2d_latlon(stencil, input_json, declared, manufactured)
    elseif kind == "arakawa"
        return _mms_convergence_2d_arakawa(stencil, input_json, declared, manufactured)
    elseif kind == "vertical"
        return _mms_convergence_1d_vertical(stencil, input_json, declared, manufactured)
    elseif kind != "cartesian" && kind != ""
        throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "unsupported selector kind $(repr(kind)); " *
            "expected one of \"cartesian\", \"latlon\", \"arakawa\", \"vertical\""))
    end
    # 1D cartesian path falls through to the inline body below.
    manufactured isa Union{Nothing,ManufacturedSolution} || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "1D cartesian stencil requires a `ManufacturedSolution`, got $(typeof(manufactured))"))
    ms = manufactured === nothing ?
        lookup_manufactured_solution(input_json["manufactured_solution"]) :
        manufactured
    raw_grids = input_json["grids"]
    raw_grids isa AbstractVector || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `grids` must be an array, got $(typeof(raw_grids))"))
    grids = Int[Int(g["n"]) for g in raw_grids]
    length(grids) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "convergence requires at least two grids; got $(grids)"))

    sub_stencil_field = get(input_json, "sub_stencil", nothing)
    sub_stencil = sub_stencil_field === nothing ? nothing : String(sub_stencil_field)
    output_kind = String(get(input_json, "output_kind", "derivative_at_cell_center"))
    output_kind in OUTPUT_KINDS || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "unknown output_kind $(repr(output_kind)); " *
        "expected one of $(collect(OUTPUT_KINDS))"))
    reconstruction = get(input_json, "reconstruction", nothing)

    domain_lo, domain_hi = ms.domain
    L = domain_hi - domain_lo
    errors = Vector{Float64}(undef, length(grids))
    for (k, n) in enumerate(grids)
        dx = L / n
        bindings = Dict{String,Float64}(
            "dx" => dx, "h" => dx, "domain_lo" => domain_lo)
        u = sampling == "cell_average" ?
            [_cell_average(ms,
                           domain_lo + (i - 1) * dx,
                           domain_lo + i * dx) for i in 1:n] :
            [ms.sample(domain_lo + (i - 0.5) * dx) for i in 1:n]
        if reconstruction === nothing
            num = apply_stencil_periodic_1d(stencil, u, bindings;
                                            sub_stencil=sub_stencil)
            ref = _reference_samples(ms, output_kind, domain_lo, dx, n)
            errors[k] = maximum(abs.(num .- ref))
        else
            errors[k] = _parabola_pass_error(stencil, u, bindings,
                                             ms, reconstruction)
        end
    end

    return _finalize_convergence(grids, errors, declared)
end

# 2D structured lat-lon convergence. Uses Y_{2,0}-style sphere MMS with R
# (radius) plumbing and a per-cell `cos_lat` binding. Each grid entry may
# carry `nlon`/`nlat` directly, or a single `n` (then `nlon = 2n`, `nlat = n`,
# the canonical sphere-MMS aspect ratio). The error metric is L∞ over the
# interior cells (poles excluded by the lat stencil's reach).
function _mms_convergence_2d_latlon(stencil, input_json::AbstractDict,
                                    declared::Float64,
                                    manufactured)::MMSConvergenceResult
    manufactured isa Union{Nothing,ManufacturedSolution2D} || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "2D latlon stencil requires a `ManufacturedSolution2D`, got $(typeof(manufactured))"))
    ms = manufactured === nothing ?
        lookup_manufactured_solution_2d(String(input_json["manufactured_solution"])) :
        manufactured
    R = Float64(get(input_json, "radius", 1.0))
    R > 0 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "radius must be positive, got $(R)"))
    raw_grids = input_json["grids"]
    raw_grids isa AbstractVector || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `grids` must be an array, got $(typeof(raw_grids))"))
    grid_pairs = Tuple{Int,Int}[]
    for g in raw_grids
        if haskey(g, "nlon") && haskey(g, "nlat")
            push!(grid_pairs, (Int(g["nlon"]), Int(g["nlat"])))
        elseif haskey(g, "n")
            n = Int(g["n"])
            push!(grid_pairs, (2 * n, n))
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "latlon grid entry must carry `nlon`+`nlat` or `n`; got keys $(collect(keys(g)))"))
        end
    end
    length(grid_pairs) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "convergence requires at least two grids; got $(grid_pairs)"))

    lon_lo, lon_hi = ms.domain_lon
    lat_lo, lat_hi = ms.domain_lat
    Llon = lon_hi - lon_lo
    Llat = lat_hi - lat_lo

    grids = [nlat for (_, nlat) in grid_pairs]  # index by lat resolution
    errors = Vector{Float64}(undef, length(grid_pairs))
    for (k, (nlon, nlat)) in enumerate(grid_pairs)
        dlon = Llon / nlon
        dlat = Llat / nlat
        lon_centers = [lon_lo + (i - 0.5) * dlon for i in 1:nlon]
        lat_centers = [lat_lo + (j - 0.5) * dlat for j in 1:nlat]
        u = [ms.sample(lon_centers[i], lat_centers[j]) for i in 1:nlon, j in 1:nlat]
        cb = CellBindings(
            Dict{String,Float64}("dlon" => dlon, "dlat" => dlat,
                                 "h" => min(dlon, dlat), "R" => R),
            Dict{String,Function}(
                "cos_lat" => (i, j) -> cos(lat_centers[j]),
                "lat"     => (i, j) -> lat_centers[j],
                "lon"     => (i, j) -> lon_centers[i],
            ),
        )
        du_num, interior = apply_stencil_2d_latlon(stencil, u, cb)
        du_exact = [ms.derivative_combo(lon_centers[i], lat_centers[j], R)
                    for i in 1:nlon, j in 1:nlat]
        diffs = abs.(du_num .- du_exact)
        any(interior) || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "no interior cells on grid (nlon=$(nlon), nlat=$(nlat)); " *
            "lat stencil reach exceeds nlat"))
        errors[k] = maximum(diffs[interior])
    end

    return _finalize_convergence(grids, errors, declared)
end

# 2D Arakawa C-grid staggered convergence. Samples the manufactured velocity
# field at face_x positions for the x-component and face_y positions for the
# y-component, applies the cell-centered divergence stencil, and compares
# against the analytic divergence at cell centers. The error metric is L∞
# over all cells (no boundary mask — both axes are periodic).
#
# Each grid entry may carry `nx`/`ny` directly, or a single `n` (then
# `nx = ny = n`, the canonical square-grid case). The fixture domain is taken
# from the manufactured solution's `domain` field; both axes are assumed
# periodic to match the C-grid stencil's wrap convention.
function _mms_convergence_2d_arakawa(stencil, input_json::AbstractDict,
                                     declared::Float64,
                                     manufactured)::MMSConvergenceResult
    manufactured isa Union{Nothing,VectorManufacturedSolution} || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "2D arakawa stencil requires a `VectorManufacturedSolution`, got $(typeof(manufactured))"))
    ms = manufactured === nothing ?
        lookup_vector_manufactured_solution(input_json["manufactured_solution"]) :
        manufactured
    ms.periodic || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "arakawa convergence requires a periodic manufactured solution; " *
        "$(ms.name) is non-periodic"))

    raw_grids = input_json["grids"]
    raw_grids isa AbstractVector || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `grids` must be an array, got $(typeof(raw_grids))"))
    grid_pairs = Tuple{Int,Int}[]
    for g in raw_grids
        if haskey(g, "nx") && haskey(g, "ny")
            push!(grid_pairs, (Int(g["nx"]), Int(g["ny"])))
        elseif haskey(g, "n")
            n = Int(g["n"])
            push!(grid_pairs, (n, n))
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "arakawa grid entry must carry `nx`+`ny` or `n`; " *
                "got keys $(collect(keys(g)))"))
        end
    end
    length(grid_pairs) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "convergence requires at least two grids; got $(grid_pairs)"))

    (xlo, xhi), (ylo, yhi) = ms.domain
    Lx = xhi - xlo
    Ly = yhi - ylo
    Lx > 0 && Ly > 0 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "arakawa MMS requires positive domain extents; got $(ms.domain)"))

    grids = [ny for (_, ny) in grid_pairs]
    errors = Vector{Float64}(undef, length(grid_pairs))
    for (k, (nx, ny)) in enumerate(grid_pairs)
        dx = Lx / nx
        dy = Ly / ny
        # Sample ux at face_x positions: x_face = xlo + (i-1)*dx for i = 1..nx+1,
        # y_cell = ylo + (j-0.5)*dy for j = 1..ny.
        ux = Matrix{Float64}(undef, nx + 1, ny)
        for j in 1:ny
            yc = ylo + (j - 0.5) * dy
            for i in 1:(nx + 1)
                xf = xlo + (i - 1) * dx
                u_val, _ = ms.velocity(xf, yc)
                ux[i, j] = u_val
            end
        end
        # Sample uy at face_y positions: y_face = ylo + (j-1)*dy for j = 1..ny+1,
        # x_cell = xlo + (i-0.5)*dx for i = 1..nx.
        uy = Matrix{Float64}(undef, nx, ny + 1)
        for j in 1:(ny + 1)
            yf = ylo + (j - 1) * dy
            for i in 1:nx
                xc = xlo + (i - 0.5) * dx
                _, v_val = ms.velocity(xc, yf)
                uy[i, j] = v_val
            end
        end
        cb = CellBindings(
            Dict{String,Float64}("dx" => dx, "dy" => dy,
                                 "h" => min(dx, dy)),
            Dict{String,Function}(
                "x" => (i, j) -> xlo + (i - 0.5) * dx,
                "y" => (i, j) -> ylo + (j - 0.5) * dy,
            ),
        )
        div_num = apply_stencil_2d_arakawa(stencil, ux, uy, cb)
        div_exact = [ms.divergence(xlo + (i - 0.5) * dx,
                                   ylo + (j - 0.5) * dy)
                     for i in 1:nx, j in 1:ny]
        errors[k] = maximum(abs.(div_num .- div_exact))
    end

    return _finalize_convergence(grids, errors, declared)
end

# 1D vertical (face-staggered → cell-centered) convergence. Each grid entry
# may carry `nz` directly, or the generic `n`. The fixture domain is taken
# from the manufactured solution's `domain` field; the column is non-periodic.
# The error metric is L∞ over all `nz` cells — interior coverage is implicit
# because face-staggered offsets ∈ {0, +1} stay inside [1, nz+1] without wrap.
function _mms_convergence_1d_vertical(stencil, input_json::AbstractDict,
                                      declared::Float64,
                                      manufactured)::MMSConvergenceResult
    manufactured isa Union{Nothing,ManufacturedSolution} || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "1D vertical stencil requires a `ManufacturedSolution`, got $(typeof(manufactured))"))
    ms = manufactured === nothing ?
        lookup_manufactured_solution(input_json["manufactured_solution"]) :
        manufactured

    raw_grids = input_json["grids"]
    raw_grids isa AbstractVector || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `grids` must be an array, got $(typeof(raw_grids))"))
    grids = Int[]
    for g in raw_grids
        if haskey(g, "nz")
            push!(grids, Int(g["nz"]))
        elseif haskey(g, "n")
            push!(grids, Int(g["n"]))
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "vertical grid entry must carry `nz` or `n`; " *
                "got keys $(collect(keys(g)))"))
        end
    end
    length(grids) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "convergence requires at least two grids; got $(grids)"))

    z_lo, z_hi = ms.domain
    H = z_hi - z_lo
    H > 0 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "vertical MMS requires positive column extent; got $(ms.domain)"))

    errors = Vector{Float64}(undef, length(grids))
    for (k, nz) in enumerate(grids)
        dz = H / nz
        # Sample at face positions z_lo + (i-1)*dz for i = 1..nz+1.
        face_z = [z_lo + (i - 1) * dz for i in 1:(nz + 1)]
        u_face = [ms.sample(z) for z in face_z]
        # Per-cell metric exposes dz as both a scalar and a per-cell callable
        # so AST coefficients written either as bare "dz" or as
        # `index(dz, $target)` resolve in this harness without rewriting.
        # `face_top` / `face_bottom` and `z` are also exposed per-cell so
        # non-uniform-spacing rules (later) can read the face/center positions.
        cb = CellBindings(
            Dict{String,Float64}("dz" => dz, "h" => dz),
            Dict{String,Function}(
                "z"           => i -> z_lo + (i - 0.5) * dz,
                "face_bottom" => i -> face_z[i],
                "face_top"    => i -> face_z[i + 1],
            ),
        )
        u_num = apply_stencil_1d_vertical(stencil, u_face, cb)
        u_exact = [ms.derivative(z_lo + (i - 0.5) * dz) for i in 1:nz]
        errors[k] = maximum(abs.(u_num .- u_exact))
    end

    return _finalize_convergence(grids, errors, declared)
end

# Common tail: fail-fast non-finite check, refinement orders, observed min.
function _finalize_convergence(grids::Vector{Int}, errors::Vector{Float64},
                               declared::Float64)::MMSConvergenceResult
    if any(!isfinite, errors) || any(e -> e <= 0, errors)
        throw(MMSEvaluatorError(
            "E_MMS_NON_FINITE",
            "non-finite or zero error on some grid; errors=$(errors)"))
    end
    orders = [log2(errors[i] / errors[i + 1]) for i in 1:(length(errors) - 1)]
    observed_min = minimum(orders)
    return MMSConvergenceResult(grids, errors, orders, observed_min, declared)
end

# Drive one parabola-pass error measurement per grid resolution. Pulled out so
# `mms_convergence` stays linear and the field-extraction errors stay close to
# the field names the user wrote.
function _parabola_pass_error(stencil, u_bar::Vector{Float64},
                              bindings::Dict{String,Float64},
                              ms::ManufacturedSolution,
                              reconstruction::AbstractDict)::Float64
    kind = String(get(reconstruction, "kind", "parabola"))
    kind == "parabola" || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "unknown reconstruction kind $(repr(kind)); only \"parabola\" is supported"))
    haskey(reconstruction, "left_edge_stencil") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "reconstruction.parabola requires `left_edge_stencil`"))
    haskey(reconstruction, "right_edge_stencil") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "reconstruction.parabola requires `right_edge_stencil`"))
    haskey(reconstruction, "subcell_points") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "reconstruction.parabola requires `subcell_points`"))
    pts = Float64[Float64(p) for p in reconstruction["subcell_points"]]
    xs, vals = parabola_reconstruct_periodic_1d(
        stencil, u_bar, bindings;
        left_edge_stencil=String(reconstruction["left_edge_stencil"]),
        right_edge_stencil=String(reconstruction["right_edge_stencil"]),
        subcell_points=pts,
    )
    refs = ms.sample.(xs)
    return maximum(abs.(vals .- refs))
end

"""
    verify_mms_convergence(rule_json, input_json, expected_json;
                           manufactured=nothing, tolerance=0.2) -> MMSConvergenceResult

Run [`mms_convergence`] and then check that the observed minimum order meets
`expected_json["expected_min_order"]`. Throws
`MMSEvaluatorError(E_MMS_ORDER_DEFICIT, …)` if the threshold is not met.

`tolerance` is reserved for callers that want to enforce a band around the
declared order rather than the fixture's own threshold; the default of 0.2
matches the convention `|observed − declared| ≤ 0.2` used by the bead's
acceptance criterion.
"""
function verify_mms_convergence(rule_json::AbstractDict,
                                input_json::AbstractDict,
                                expected_json::AbstractDict;
                                manufactured=nothing,
                                tolerance::Float64=0.2)::MMSConvergenceResult
    haskey(expected_json, "expected_min_order") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "expected.esm has no `expected_min_order` field"))
    threshold = Float64(expected_json["expected_min_order"])
    result = mms_convergence(rule_json, input_json; manufactured=manufactured)
    if result.observed_min_order < threshold
        throw(MMSEvaluatorError(
            "E_MMS_ORDER_DEFICIT",
            "observed min order $(round(result.observed_min_order; digits=3)) " *
            "below expected $(threshold); errors=$(result.errors)"))
    end
    if abs(result.observed_min_order - result.declared_order) > tolerance &&
       result.observed_min_order < result.declared_order - tolerance
        # Soft check: only escalate when below the declared band; high-side
        # superconvergence is fine.
        throw(MMSEvaluatorError(
            "E_MMS_ORDER_DEFICIT",
            "observed min order $(round(result.observed_min_order; digits=3)) " *
            "outside ±$(tolerance) of declared $(result.declared_order); " *
            "errors=$(result.errors)"))
    end
    return result
end

# ============================================================
# MPAS-style unstructured MMS support (esm-0sy)
# ============================================================
#
# The existing convergence harness above is restricted to 1D Cartesian periodic
# stencils. MPAS-style discretizations (e.g. `mpas_cell_div` in
# tests/discretizations/mpas_cell_div.esm) use:
#
#   - `reduction`-kind stencil selectors that iterate over a connectivity table
#     (`edgesOnCell`) with a per-cell variable arity (`nEdgesOnCell[$target]`),
#   - `index`-op coefficients that look up array entries in connectivity +
#     metric tables (`edgesOnCell`, `dvEdge`, `areaCell`),
#   - vector manufactured solutions (edge-normal flux F = u·n̂ rather than a
#     scalar u(x)) sampled at edge midpoints, and
#   - a per-cell sign convention from the staggering rule (RFC §7.4):
#     `outward_from_first_cell` flips the sign on edges where the target cell
#     sits in `cellsOnEdge[2,e]` rather than `cellsOnEdge[1,e]`.
#
# The pieces below add just enough to drive a convergence sweep on the
# `mpas_cell_div` rule using a refining periodic quad mesh (regular 4-valence
# unstructured fixture). The same machinery accepts any MPAS-like mesh that
# supplies the canonical field set, so a hex/Voronoi generator can drop in
# later without changing the stencil applier.

# ============================================================
# Vector manufactured-solution registry
# ============================================================

"""
    VectorManufacturedSolution(name, velocity, divergence, domain, periodic)

Vector-field manufactured solution for MPAS-style cell-centered divergence /
gradient MMS. `velocity(x, y) -> (u, v)` returns the analytic velocity at a
point; `divergence(x, y) -> div(u)` returns the analytic divergence at a cell
center. `domain` is `((xmin, xmax), (ymin, ymax))`; `periodic` indicates
periodic wrap on both axes.
"""
struct VectorManufacturedSolution
    name::Symbol
    velocity::Function
    divergence::Function
    domain::NTuple{2,Tuple{Float64,Float64}}
    periodic::Bool
end

# Built-in: u(x,y) = (sin(2π x), 0) on [0,1]² periodic; div(u) = 2π cos(2π x).
const _MMS_VEC_SIN_2PI_X_PERIODIC = VectorManufacturedSolution(
    :vec_sin_2pi_x_periodic,
    (x, y) -> (sin(2π * x), 0.0),
    (x, y) -> 2π * cos(2π * x),
    ((0.0, 1.0), (0.0, 1.0)),
    true,
)

# Built-in: u(x,y) = (sin(2π x) cos(2π y), cos(2π x) sin(2π y)) on [0,1]² periodic;
# div(u) = 2π cos(2π x) cos(2π y) + 2π cos(2π x) cos(2π y) = 4π cos(2π x) cos(2π y).
# Both components are non-trivial in both axes, which exercises a 2D staggered
# divergence stencil more thoroughly than the 1D-style (sin(2π x), 0) field
# (whose y-axis contribution is identically zero).
const _MMS_VEC_SINCOS_2D_PERIODIC = VectorManufacturedSolution(
    :vec_sincos_2d_periodic,
    (x, y) -> (sin(2π * x) * cos(2π * y), cos(2π * x) * sin(2π * y)),
    (x, y) -> 4π * cos(2π * x) * cos(2π * y),
    ((0.0, 1.0), (0.0, 1.0)),
    true,
)

const _MMS_VECTOR_REGISTRY = Dict{Symbol,VectorManufacturedSolution}(
    :vec_sin_2pi_x_periodic => _MMS_VEC_SIN_2PI_X_PERIODIC,
    :vec_sincos_2d_periodic => _MMS_VEC_SINCOS_2D_PERIODIC,
)

"""
    register_vector_manufactured_solution!(ms::VectorManufacturedSolution)

Add or replace a vector manufactured solution in the registry. Returns `ms`.
"""
function register_vector_manufactured_solution!(ms::VectorManufacturedSolution)
    _MMS_VECTOR_REGISTRY[ms.name] = ms
    return ms
end

"""
    lookup_vector_manufactured_solution(description::AbstractString) ->
        VectorManufacturedSolution

Resolve a `manufactured_solution` description string from an MPAS-style
`input.esm` to a registered vector solution. Punctuation and whitespace are
ignored. Throws `MMSEvaluatorError(E_MMS_UNKNOWN_SOLUTION, …)` on no match.
"""
function lookup_vector_manufactured_solution(
        description::AbstractString)::VectorManufacturedSolution
    norm = lowercase(replace(String(description), r"[\s\*]" => ""))
    # Two non-trivial 2D periodic components — match before the 1D (sin, 0)
    # pattern so a description like "sin(2π x) cos(2π y), cos(2π x) sin(2π y)"
    # routes to the correct entry.
    if (occursin("sin(2pix)cos(2piy)", norm) ||
        occursin("sin(2πx)cos(2πy)", norm) ||
        occursin("vec=(sin(2pix)cos(2piy)", norm) ||
        occursin("vec=(sin(2πx)cos(2πy)", norm) ||
        occursin("sincos2d", norm) || occursin("sincos_2d", norm))
        return _MMS_VECTOR_REGISTRY[:vec_sincos_2d_periodic]
    end
    if (occursin("sin(2pi", norm) || occursin("sin(2π", norm)) &&
       (occursin(",0)", norm) || occursin("vec=(sin", norm) ||
        occursin("v=0", norm))
        return _MMS_VECTOR_REGISTRY[:vec_sin_2pi_x_periodic]
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no vector manufactured solution registered for $(repr(description)); " *
        "register one with register_vector_manufactured_solution!"))
end

"""
    lookup_vector_manufactured_solution(description::AbstractDict) ->
        VectorManufacturedSolution

Resolve a vector manufactured solution from a dict description. Accepts a
`"name"` key (exact match against the registry) and falls back to
string-matching on the `"expression"` key.
"""
function lookup_vector_manufactured_solution(
        description::AbstractDict)::VectorManufacturedSolution
    if haskey(description, "name")
        sym = Symbol(String(description["name"]))
        haskey(_MMS_VECTOR_REGISTRY, sym) && return _MMS_VECTOR_REGISTRY[sym]
    end
    if haskey(description, "expression")
        return lookup_vector_manufactured_solution(String(description["expression"]))
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no vector manufactured solution matches dict $(repr(description)); " *
        "register one with register_vector_manufactured_solution!"))
end

# ============================================================
# MPAS-like mesh
# ============================================================

"""
    MPASLikeMesh

Minimal MPAS-style topology + geometry for cell-centered MMS testing.

Carries the canonical MPAS field set:

- `nCells`, `nEdges`                              — counts
- `cellsOnEdge :: Matrix{Int}`   (`nEdges × 2`)   — adjacent cells per edge
- `edgesOnCell :: Matrix{Int}`   (`nCells × maxEdges`) — edges per cell
- `nEdgesOnCell :: Vector{Int}`  (`nCells`)       — per-cell edge count
- `dcEdge, dvEdge :: Vector{Float64}` (`nEdges`)  — center-to-center, side length
- `areaCell :: Vector{Float64}` (`nCells`)
- `cell_centers :: Matrix{Float64}` (`nCells × 2`)
- `edge_midpoints :: Matrix{Float64}` (`nEdges × 2`)
- `edge_normals :: Matrix{Float64}` (`nEdges × 2`) — points from
  `cellsOnEdge[e,1]` toward `cellsOnEdge[e,2]` (RFC §7.4
  `outward_from_first_cell`)
- `domain :: ((xmin,xmax),(ymin,ymax))`

Index order matches the canonical MPAS NetCDF layout (`[nCells, maxEdges]`,
`[nEdges, 2]`) so AST coefficients written as `index(edgesOnCell, \$target, k)`
or `index(cellsOnEdge, e, 1)` resolve naturally. All indices are 1-based
(Julia native). Builders MUST pre-resolve periodic wrap so consumers never see
boundary sentinels.
"""
struct MPASLikeMesh
    nCells::Int
    nEdges::Int
    cellsOnEdge::Matrix{Int}
    edgesOnCell::Matrix{Int}
    nEdgesOnCell::Vector{Int}
    dcEdge::Vector{Float64}
    dvEdge::Vector{Float64}
    areaCell::Vector{Float64}
    cell_centers::Matrix{Float64}
    edge_midpoints::Matrix{Float64}
    edge_normals::Matrix{Float64}
    domain::NTuple{2,Tuple{Float64,Float64}}
end

"""
    make_periodic_quad_mesh(n::Int; L::Float64=1.0) -> MPASLikeMesh

Build a doubly-periodic regular quad mesh on `[0,L]²` with `n × n` cells.
Each cell has exactly 4 edges (`maxEdges == 4`); cell-to-edge wiring uses the
order `(east, north, west, south)`. The mesh has the same canonical field set
as a true MPAS Voronoi mesh, so `apply_mpas_cell_stencil` and
`mms_convergence_mpas` exercise the unstructured code path even though the
geometry is uniform.

The chosen ordering puts each cell's "east" edge in `cellsOnEdge[1, e]` (i.e.
the host cell to the west of the edge), with the edge normal pointing east
toward `cellsOnEdge[2, e]` — matching the staggering rule's
`outward_from_first_cell` convention.
"""
function make_periodic_quad_mesh(n::Int; L::Float64=1.0)::MPASLikeMesh
    n >= 2 || throw(ArgumentError("make_periodic_quad_mesh: n must be ≥ 2"))
    nCells = n * n
    nEdges = 2 * nCells  # one east + one north edge per cell on a torus
    h = L / n

    # 1-based linear index for cell at column i, row j (1..n each).
    cell_id(i, j) = (j - 1) * n + i
    # East-edge id for the cell at (i,j): edges 1..nCells (one per cell).
    east_edge(i, j) = cell_id(i, j)
    # North-edge id: shifted by nCells.
    north_edge(i, j) = nCells + cell_id(i, j)

    cellsOnEdge   = zeros(Int, nEdges, 2)
    edgesOnCell   = zeros(Int, nCells, 4)
    nEdgesOnCell  = fill(4, nCells)
    dcEdge        = fill(h, nEdges)
    dvEdge        = fill(h, nEdges)
    areaCell      = fill(h * h, nCells)
    cell_centers  = zeros(Float64, nCells, 2)
    edge_midpoints = zeros(Float64, nEdges, 2)
    edge_normals  = zeros(Float64, nEdges, 2)

    wrap(k) = mod1(k, n)

    for j in 1:n, i in 1:n
        c = cell_id(i, j)
        cell_centers[c, 1] = (i - 0.5) * h
        cell_centers[c, 2] = (j - 0.5) * h

        e_e = east_edge(i, j)
        e_n = north_edge(i, j)
        e_w = east_edge(wrap(i - 1), j)
        e_s = north_edge(i, wrap(j - 1))

        # edge order on the cell: (east, north, west, south)
        edgesOnCell[c, 1] = e_e
        edgesOnCell[c, 2] = e_n
        edgesOnCell[c, 3] = e_w
        edgesOnCell[c, 4] = e_s
    end

    for j in 1:n, i in 1:n
        # east edge of cell (i,j): between (i,j) [first] and (i+1,j) [second]
        e = east_edge(i, j)
        cellsOnEdge[e, 1] = cell_id(i, j)
        cellsOnEdge[e, 2] = cell_id(wrap(i + 1), j)
        edge_midpoints[e, 1] = i * h
        edge_midpoints[e, 2] = (j - 0.5) * h
        edge_normals[e, 1] = 1.0
        edge_normals[e, 2] = 0.0

        # north edge of cell (i,j): between (i,j) [first] and (i,j+1) [second]
        e = north_edge(i, j)
        cellsOnEdge[e, 1] = cell_id(i, j)
        cellsOnEdge[e, 2] = cell_id(i, wrap(j + 1))
        edge_midpoints[e, 1] = (i - 0.5) * h
        edge_midpoints[e, 2] = j * h
        edge_normals[e, 1] = 0.0
        edge_normals[e, 2] = 1.0
    end

    return MPASLikeMesh(
        nCells, nEdges, cellsOnEdge, edgesOnCell, nEdgesOnCell,
        dcEdge, dvEdge, areaCell,
        cell_centers, edge_midpoints, edge_normals,
        ((0.0, L), (0.0, L)),
    )
end

# ============================================================
# MPAS coefficient evaluator (`index` ops + scalar bindings)
# ============================================================

"""
    MPASCoeffContext(arrays, scalars)

Bindings for evaluating an MPAS stencil coefficient AST inside a reduction
loop. `arrays` keys map to integer / float vectors or matrices (e.g.
`"edgesOnCell"`, `"dvEdge"`, `"areaCell"`); `scalars` carry per-iteration
state (`"\$target"` = current cell id, `"k"` = current reduction index) plus
any grid scalars (`"dx"`, `"h"`).
"""
struct MPASCoeffContext
    arrays::Dict{String,Any}
    scalars::Dict{String,Float64}
end

# Coerce a scalar coefficient sub-expression (Number, String, Dict) to Float64
# inside an MPAS context.
function _eval_mpas_coeff_scalar(node, ctx::MPASCoeffContext)::Float64
    if node isa Number
        return Float64(node)
    elseif node isa AbstractString
        s = String(node)
        haskey(ctx.scalars, s) || throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "MPAS coefficient references unbound scalar $(repr(s)); " *
            "available: $(collect(keys(ctx.scalars)))"))
        return ctx.scalars[s]
    elseif node isa AbstractDict
        op = String(node["op"])
        args = node["args"]
        if op == "index"
            return _eval_mpas_index(node, ctx)
        elseif op == "+"
            return sum(_eval_mpas_coeff_scalar(a, ctx) for a in args)
        elseif op == "-"
            length(args) == 1 && return -_eval_mpas_coeff_scalar(args[1], ctx)
            length(args) == 2 && return _eval_mpas_coeff_scalar(args[1], ctx) -
                                        _eval_mpas_coeff_scalar(args[2], ctx)
            throw(ArgumentError("MPAS `-` op needs 1 or 2 args, got $(length(args))"))
        elseif op == "*"
            acc = 1.0
            for a in args
                acc *= _eval_mpas_coeff_scalar(a, ctx)
            end
            return acc
        elseif op == "/"
            length(args) == 2 || throw(ArgumentError(
                "MPAS `/` op requires 2 args, got $(length(args))"))
            denom = _eval_mpas_coeff_scalar(args[2], ctx)
            denom == 0.0 && throw(DivideError())
            return _eval_mpas_coeff_scalar(args[1], ctx) / denom
        elseif op == "^"
            length(args) == 2 || throw(ArgumentError(
                "MPAS `^` op requires 2 args, got $(length(args))"))
            return _eval_mpas_coeff_scalar(args[1], ctx) ^
                   _eval_mpas_coeff_scalar(args[2], ctx)
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "MPAS coefficient evaluator does not support op $(repr(op))"))
        end
    else
        throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "MPAS coefficient node has unsupported type $(typeof(node))"))
    end
end

# Evaluate an `index` op as a Float64. The first arg must be the array name
# (string); subsequent args are integer-valued sub-expressions.
function _eval_mpas_index(node::AbstractDict, ctx::MPASCoeffContext)::Float64
    args = node["args"]
    length(args) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "MPAS `index` op requires array name + at least one index, got args=$(args)"))
    name_node = args[1]
    name_node isa AbstractString || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "MPAS `index` op first arg must be a string array name, got $(typeof(name_node))"))
    name = String(name_node)
    haskey(ctx.arrays, name) || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "MPAS coefficient references unbound array $(repr(name)); " *
        "available: $(collect(keys(ctx.arrays)))"))
    arr = ctx.arrays[name]
    nidx = length(args) - 1
    idxs = ntuple(i -> begin
        v = _eval_mpas_coeff_scalar(args[i + 1], ctx)
        Int(round(v))
    end, nidx)
    return Float64(arr[idxs...])
end

# ============================================================
# Reduction-stencil application
# ============================================================

"""
    apply_mpas_cell_stencil(stencil_json, edge_field::Vector{Float64},
                            mesh::MPASLikeMesh; scalars=Dict{String,Float64}(),
                            sign_convention::AbstractString="outward_from_first_cell"
                            ) -> Vector{Float64}

Apply an MPAS cell-centered reduction stencil (e.g. `mpas_cell_div`) to an
edge-centered field, returning a cell-centered output vector of length
`mesh.nCells`.

`stencil_json` MUST contain a single entry whose `selector.kind == "reduction"`
with `table == "edgesOnCell"`, `count_expr == index(nEdgesOnCell, \$target)`,
and `combine == "+"`. The `coeff` AST may use `index` ops over any of the
canonical arrays (`edgesOnCell`, `cellsOnEdge`, `dvEdge`, `dcEdge`, `areaCell`,
`nEdgesOnCell`) plus the scalar bindings `\$target`, `k`, and any caller-
supplied scalars (e.g. `dx`).

The per-cell sign is applied automatically per `sign_convention`:
`"outward_from_first_cell"` (RFC §7.4) flips the sign on edges where the
target cell appears as `cellsOnEdge[2, e]`. Pass `"none"` to disable.
"""
function apply_mpas_cell_stencil(stencil_json,
                                 edge_field::Vector{Float64},
                                 mesh::MPASLikeMesh;
                                 scalars::Dict{String,Float64}=Dict{String,Float64}(),
                                 sign_convention::AbstractString="outward_from_first_cell"
                                 )::Vector{Float64}
    length(edge_field) == mesh.nEdges || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "edge_field length $(length(edge_field)) ≠ mesh.nEdges $(mesh.nEdges)"))
    length(stencil_json) == 1 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "MPAS reduction stencil expects exactly one entry, got $(length(stencil_json))"))
    entry = stencil_json[1]
    sel = entry["selector"]
    String(sel["kind"]) == "reduction" || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "apply_mpas_cell_stencil requires selector.kind == 'reduction', got $(repr(sel["kind"]))"))
    String(sel["table"]) == "edgesOnCell" || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "apply_mpas_cell_stencil currently supports table == 'edgesOnCell' only " *
        "(got $(repr(sel["table"])))"))
    String(get(sel, "combine", "+")) == "+" || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "apply_mpas_cell_stencil currently supports combine == '+' only"))
    coeff_node = entry["coeff"]

    arrays = Dict{String,Any}(
        "edgesOnCell" => mesh.edgesOnCell,
        "cellsOnEdge" => mesh.cellsOnEdge,
        "nEdgesOnCell" => mesh.nEdgesOnCell,
        "dcEdge" => mesh.dcEdge,
        "dvEdge" => mesh.dvEdge,
        "areaCell" => mesh.areaCell,
    )
    out = zeros(Float64, mesh.nCells)
    apply_sign = sign_convention == "outward_from_first_cell"
    apply_sign || sign_convention == "none" || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "unsupported sign_convention $(repr(sign_convention)); " *
        "expected 'outward_from_first_cell' or 'none'"))

    @inbounds for c in 1:mesh.nCells
        kmax = mesh.nEdgesOnCell[c]
        acc = 0.0
        for k in 1:kmax
            scal = copy(scalars)
            scal["\$target"] = Float64(c)
            scal["k"] = Float64(k)
            ctx = MPASCoeffContext(arrays, scal)
            coeff = _eval_mpas_coeff_scalar(coeff_node, ctx)
            e = mesh.edgesOnCell[c, k]
            sgn = (apply_sign && mesh.cellsOnEdge[e, 2] == c) ? -1.0 : 1.0
            acc += coeff * sgn * edge_field[e]
        end
        out[c] = acc
    end
    return out
end

# ============================================================
# Convergence sweep — MPAS cell-centered divergence
# ============================================================

"""
    sample_edge_normal_flux(mesh::MPASLikeMesh,
                            ms::VectorManufacturedSolution) -> Vector{Float64}

Sample the edge-normal flux F_e = u(midpoint_e) · n̂_e for every edge, using
the manufactured velocity field. Returns a vector of length `mesh.nEdges`.
"""
function sample_edge_normal_flux(mesh::MPASLikeMesh,
                                 ms::VectorManufacturedSolution)::Vector{Float64}
    F = zeros(Float64, mesh.nEdges)
    @inbounds for e in 1:mesh.nEdges
        x = mesh.edge_midpoints[e, 1]
        y = mesh.edge_midpoints[e, 2]
        u, v = ms.velocity(x, y)
        F[e] = u * mesh.edge_normals[e, 1] + v * mesh.edge_normals[e, 2]
    end
    return F
end

"""
    sample_cell_divergence(mesh::MPASLikeMesh,
                           ms::VectorManufacturedSolution) -> Vector{Float64}

Sample the analytic divergence at each cell center.
"""
function sample_cell_divergence(mesh::MPASLikeMesh,
                                ms::VectorManufacturedSolution)::Vector{Float64}
    d = zeros(Float64, mesh.nCells)
    @inbounds for c in 1:mesh.nCells
        x = mesh.cell_centers[c, 1]
        y = mesh.cell_centers[c, 2]
        d[c] = ms.divergence(x, y)
    end
    return d
end

"""
    mms_convergence_mpas(rule_json, input_json;
                          manufactured=nothing,
                          mesh_builder=make_periodic_quad_mesh,
                          sign_convention="outward_from_first_cell"
                          ) -> MMSConvergenceResult

Run an MPAS-style cell-centered divergence convergence sweep. The fixture
schema mirrors the structured `mms_convergence` driver:

```jsonc
{
  "rule": "mpas_cell_div",
  "manufactured_solution": "vec=(sin(2*pi*x), 0); div=2*pi*cos(2*pi*x)",
  "sampling": "cell_center",
  "grids": [{"n": 8}, {"n": 16}, {"n": 32}, {"n": 64}],
  "topology": "quad_periodic"   // optional; default "quad_periodic"
}
```

`mesh_builder(n)` is invoked per grid. The default builds a doubly-periodic
regular quad mesh; pass a custom builder (e.g. a hex/Voronoi generator) to
exercise other unstructured topologies — the stencil applier is topology-
agnostic given the MPAS field set.
"""
function mms_convergence_mpas(rule_json::AbstractDict, input_json::AbstractDict;
        manufactured::Union{Nothing,VectorManufacturedSolution}=nothing,
        mesh_builder::Function=make_periodic_quad_mesh,
        sign_convention::AbstractString="outward_from_first_cell"
        )::MMSConvergenceResult
    rule_name = String(input_json["rule"])
    spec = _resolve_rule_spec(rule_json, rule_name)
    haskey(spec, "stencil") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "rule $(repr(rule_name)) has no `stencil` field"))
    haskey(spec, "accuracy") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "rule $(repr(rule_name)) has no `accuracy` field"))
    declared = parse_accuracy_order(String(spec["accuracy"]))
    stencil = spec["stencil"]

    ms = manufactured === nothing ?
        lookup_vector_manufactured_solution(String(input_json["manufactured_solution"])) :
        manufactured

    sampling = String(get(input_json, "sampling", "cell_center"))
    sampling == "cell_center" || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "MPAS MMS only supports `sampling: cell_center` (got $(repr(sampling)))"))

    raw_grids = input_json["grids"]
    raw_grids isa AbstractVector || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `grids` must be an array, got $(typeof(raw_grids))"))
    grids = Int[Int(g["n"]) for g in raw_grids]
    length(grids) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "convergence requires at least two grids; got $(grids)"))

    domain_lo_x = ms.domain[1][1]
    domain_hi_x = ms.domain[1][2]
    Lx = domain_hi_x - domain_lo_x

    errors = Vector{Float64}(undef, length(grids))
    for (k, n) in enumerate(grids)
        mesh = mesh_builder(n)
        h = Lx / n
        F = sample_edge_normal_flux(mesh, ms)
        d_exact = sample_cell_divergence(mesh, ms)
        d_num = apply_mpas_cell_stencil(stencil, F, mesh;
            scalars=Dict{String,Float64}("dx" => h, "h" => h),
            sign_convention=sign_convention)
        errors[k] = maximum(abs.(d_num .- d_exact))
    end

    if any(!isfinite, errors) || any(e -> e <= 0, errors)
        throw(MMSEvaluatorError(
            "E_MMS_NON_FINITE",
            "non-finite or zero error on some grid; errors=$(errors)"))
    end

    orders = [log2(errors[i] / errors[i + 1]) for i in 1:(length(errors) - 1)]
    observed_min = minimum(orders)
    return MMSConvergenceResult(grids, errors, orders, observed_min, declared)
end

"""
    verify_mms_convergence_mpas(rule_json, input_json, expected_json;
                                 manufactured=nothing,
                                 mesh_builder=make_periodic_quad_mesh,
                                 sign_convention="outward_from_first_cell",
                                 tolerance=0.2) -> MMSConvergenceResult

MPAS-flavor twin of [`verify_mms_convergence`]. Throws
`MMSEvaluatorError(E_MMS_ORDER_DEFICIT, …)` if the observed minimum order is
below `expected_json["expected_min_order"]` or more than `tolerance` below
the declared order.
"""
function verify_mms_convergence_mpas(rule_json::AbstractDict,
        input_json::AbstractDict, expected_json::AbstractDict;
        manufactured::Union{Nothing,VectorManufacturedSolution}=nothing,
        mesh_builder::Function=make_periodic_quad_mesh,
        sign_convention::AbstractString="outward_from_first_cell",
        tolerance::Float64=0.2)::MMSConvergenceResult
    haskey(expected_json, "expected_min_order") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "expected.esm has no `expected_min_order` field"))
    threshold = Float64(expected_json["expected_min_order"])
    result = mms_convergence_mpas(rule_json, input_json;
        manufactured=manufactured, mesh_builder=mesh_builder,
        sign_convention=sign_convention)
    if result.observed_min_order < threshold
        throw(MMSEvaluatorError(
            "E_MMS_ORDER_DEFICIT",
            "observed min order $(round(result.observed_min_order; digits=3)) " *
            "below expected $(threshold); errors=$(result.errors)"))
    end
    if abs(result.observed_min_order - result.declared_order) > tolerance &&
       result.observed_min_order < result.declared_order - tolerance
        throw(MMSEvaluatorError(
            "E_MMS_ORDER_DEFICIT",
            "observed min order $(round(result.observed_min_order; digits=3)) " *
            "outside ±$(tolerance) of declared $(result.declared_order); " *
            "errors=$(result.errors)"))
    end
    return result
end

# ============================================================
# WENO5 nonlinear reconstruction (esm-rq3)
# ============================================================

# Internal helper: extract `(offsets, coeffs)` for a candidate sub-stencil's
# linear pass. Sub-stencil coefficients in the schema are pure rationals
# (no `dx`), so eval_coeff is run against an empty binding table.
function _weno_candidate_pairs(candidate, bindings)
    stencil = candidate["stencil"]
    pairs = Vector{Tuple{Int,Float64}}(undef, length(stencil))
    for (k, s) in enumerate(stencil)
        pairs[k] = (Int(s["selector"]["offset"]),
                    eval_coeff(s["coeff"], bindings))
    end
    return pairs
end

"""
    apply_weno5_reconstruction_periodic_1d(spec, q, side; eps=1e-6) -> Vector{Float64}

Reconstruct cell-edge values from periodic cell averages `q` using the
classical Jiang-Shu (1996) WENO5 nonlinear weights.

`spec` is a discretization spec dict carrying the
`reconstruction_left_biased` / `reconstruction_right_biased` blocks (each
with `candidates[*].stencil` of length 3 and `linear_weights.{d0,d1,d2}`).
`side` is `:left_biased` (returns `q_{i+1/2}^L`, the right face of cell `i`,
upwind for u > 0) or `:right_biased` (returns `q_{i-1/2}^R`, the left face
of cell `i`, upwind for u < 0). `eps` is the smoothness-indicator
regularisation (Jiang-Shu 1996 eq. 2.10; `1e-6` is the canonical value).

The candidate sub-stencils' linear coefficients are pulled from the schema
via [`eval_coeff`]; the smoothness indicators (Shu 1998 eq. 2.16) and
nonlinear-weight ratio form (Jiang-Shu 1996 eqs. 2.9–2.10) are applied
in-kernel because the §7 stencil schema cannot yet express the ratio
form (see `discretizations/finite_volume/weno5_advection.json`,
`nonlinear_weights.comment`).
"""
function apply_weno5_reconstruction_periodic_1d(spec::AbstractDict,
                                                q::Vector{Float64},
                                                side::Symbol;
                                                eps::Float64=1e-6)::Vector{Float64}
    rk = side === :left_biased  ? "reconstruction_left_biased"  :
         side === :right_biased ? "reconstruction_right_biased" :
         throw(MMSEvaluatorError(
             "E_MMS_BAD_FIXTURE",
             "WENO5 reconstruction side must be :left_biased or :right_biased, " *
             "got $(repr(side))"))
    haskey(spec, rk) || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "rule has no $(repr(rk)) block (required for WENO5 nonlinear sweep)"))
    block = spec[rk]
    cands = block["candidates"]
    length(cands) == 3 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "WENO5 expects 3 candidate sub-stencils, got $(length(cands))"))
    bindings = Dict{String,Float64}()
    pairs = ntuple(k -> _weno_candidate_pairs(cands[k], bindings), 3)

    haskey(block, "linear_weights") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "WENO5 $(rk) block has no `linear_weights`"))
    lw = block["linear_weights"]
    d0 = eval_coeff(lw["d0"], bindings)
    d1 = eval_coeff(lw["d1"], bindings)
    d2 = eval_coeff(lw["d2"], bindings)

    n = length(q)
    out = Vector{Float64}(undef, n)
    @inbounds for i in 1:n
        # Linear candidate evaluations (p0,p1,p2) — index reflection for
        # right-biased is encoded directly in the schema's stencil offsets,
        # so the same linear pass handles both sides.
        p0 = 0.0; p1 = 0.0; p2 = 0.0
        for (off, c) in pairs[1]; p0 += c * q[mod1(i + off, n)]; end
        for (off, c) in pairs[2]; p1 += c * q[mod1(i + off, n)]; end
        for (off, c) in pairs[3]; p2 += c * q[mod1(i + off, n)]; end

        # Smoothness indicators in the support window of each side. The
        # right-biased block uses index-reflected support (j -> -j), so the
        # quadratic-form formulae are written in the corresponding direction.
        if side === :left_biased
            qm2 = q[mod1(i - 2, n)]
            qm1 = q[mod1(i - 1, n)]
            q0  = q[i]
            qp1 = q[mod1(i + 1, n)]
            qp2 = q[mod1(i + 2, n)]
        else
            qm2 = q[mod1(i + 2, n)]
            qm1 = q[mod1(i + 1, n)]
            q0  = q[i]
            qp1 = q[mod1(i - 1, n)]
            qp2 = q[mod1(i - 2, n)]
        end
        b0 = (13/12) * (qm2 - 2qm1 + q0)^2  + (1/4) * (qm2 - 4qm1 + 3q0)^2
        b1 = (13/12) * (qm1 - 2q0  + qp1)^2 + (1/4) * (qm1 - qp1)^2
        b2 = (13/12) * (q0  - 2qp1 + qp2)^2 + (1/4) * (3q0  - 4qp1 + qp2)^2

        a0 = d0 / (eps + b0)^2
        a1 = d1 / (eps + b1)^2
        a2 = d2 / (eps + b2)^2
        s = a0 + a1 + a2
        out[i] = (a0/s) * p0 + (a1/s) * p1 + (a2/s) * p2
    end
    return out
end

# Internal: dispatch helper. Returns `:weno5` for WENO5 nonlinear
# reconstruction rules, else `:linear_stencil` (the original sweep path).
function _mms_rule_kind(spec::AbstractDict)::Symbol
    form = String(get(spec, "form", ""))
    if form == "weighted_essentially_nonoscillatory"
        return :weno5
    end
    return :linear_stencil
end

# Internal: parse `reconstruction` from input fixture as a `:left_biased` or
# `:right_biased` Symbol.
function _parse_reconstruction_side(s)::Symbol
    str = lowercase(strip(String(s)))
    str == "left_biased"  && return :left_biased
    str == "right_biased" && return :right_biased
    throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `reconstruction` must be \"left_biased\" or \"right_biased\", " *
        "got $(repr(s))"))
end

"""
    mms_weno5_convergence(rule_json, input_json; manufactured=nothing) -> MMSConvergenceResult

Run a manufactured-solution convergence sweep for a WENO5 nonlinear
reconstruction rule (`form == "weighted_essentially_nonoscillatory"`).

Two rule shapes are supported:

1. **1D**: the spec carries top-level `reconstruction_left_biased` /
   `reconstruction_right_biased` blocks. `input_json` must declare
   `reconstruction`, `weno_epsilon`, `grids` (entries with `n`), and
   `manufactured_solution` resolving to a 1D `ManufacturedSolution` with
   `cell_average(a, b)` and `edge_value(x)`.
2. **2D axis-split**: the spec carries an `axes` mapping with `x` and/or
   `y` entries, each holding their own `reconstruction_left_biased` /
   `reconstruction_right_biased` blocks. `input_json` adds an `axis`
   selector (`"x"` or `"y"`, defaults to `"x"`), accepts `grids` entries
   with `n` (square) or `nx`+`ny`, and resolves `manufactured_solution`
   to a `ReconstructionManufacturedSolution2D` (e.g. the built-in
   `:phase_shifted_sine_product_2d`). The chosen axis's WENO5 sweep is
   applied row-wise (or column-wise), and the L∞ error is taken against
   the perpendicular-axis-averaged analytic face value.

In both shapes the returned `MMSConvergenceResult` reports the L∞ error of
the reconstructed face value over the grid sequence.
"""
function mms_weno5_convergence(rule_json::AbstractDict, input_json::AbstractDict;
                               manufactured=nothing)::MMSConvergenceResult
    rule_name = String(input_json["rule"])
    spec = _resolve_rule_spec(rule_json, rule_name)
    _mms_rule_kind(spec) === :weno5 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "rule $(repr(rule_name)) is not a WENO5 nonlinear reconstruction " *
        "(form=$(repr(get(spec, "form", nothing))))"))
    declared = haskey(spec, "accuracy") ?
        parse_accuracy_order(String(spec["accuracy"])) :
        throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "rule $(repr(rule_name)) has no `accuracy` field"))

    if haskey(spec, "axes")
        return _mms_weno5_convergence_2d(spec, input_json, declared, manufactured)
    end
    return _mms_weno5_convergence_1d(spec, input_json, declared, manufactured)
end

# 1D WENO5 convergence sweep: top-level reconstruction_left/right_biased
# blocks, 1D ManufacturedSolution with cell_average + edge_value.
function _mms_weno5_convergence_1d(spec::AbstractDict, input_json::AbstractDict,
                                   declared::Float64,
                                   manufactured)::MMSConvergenceResult
    manufactured isa Union{Nothing,ManufacturedSolution} || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "1D WENO5 sweep requires a `ManufacturedSolution`, got $(typeof(manufactured))"))
    ms = manufactured === nothing ?
        lookup_manufactured_solution(input_json["manufactured_solution"]) :
        manufactured
    ms.cell_average === nothing && throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "WENO5 sweep requires a manufactured solution with `cell_average`; " *
        "$(ms.name) has none"))
    ms.edge_value === nothing && throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "WENO5 sweep requires a manufactured solution with `edge_value`; " *
        "$(ms.name) has none"))

    side = _parse_reconstruction_side(get(input_json, "reconstruction", "left_biased"))
    eps = Float64(get(input_json, "weno_epsilon", 1e-6))
    raw_grids = input_json["grids"]
    raw_grids isa AbstractVector || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `grids` must be an array, got $(typeof(raw_grids))"))
    grids = Int[Int(g["n"]) for g in raw_grids]
    length(grids) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "convergence requires at least two grids; got $(grids)"))

    domain_lo, domain_hi = ms.domain
    L = domain_hi - domain_lo
    errors = Vector{Float64}(undef, length(grids))
    for (k, n) in enumerate(grids)
        dx = L / n
        q = [ms.cell_average(domain_lo + (i - 1) * dx,
                             domain_lo + i       * dx) for i in 1:n]
        qhat = apply_weno5_reconstruction_periodic_1d(spec, q, side; eps=eps)
        # Truth at the upwind face of cell i. Left-biased reconstructs the
        # right face (x_{i+1/2}); right-biased reconstructs the left face
        # (x_{i-1/2}).
        face_truth = side === :left_biased ?
            [ms.edge_value(domain_lo + i       * dx) for i in 1:n] :
            [ms.edge_value(domain_lo + (i - 1) * dx) for i in 1:n]
        errors[k] = maximum(abs.(qhat .- face_truth))
    end

    return _finalize_convergence(grids, errors, declared)
end

# 2D axis-split WENO5 convergence sweep. The spec's `axes.<axis>` block is a
# 1D-shaped reconstruction sub-spec; the sweep applies the existing 1D
# kernel along the chosen axis on each row/column of a 2D cell-averaged
# manufactured field, and compares against the perpendicular-axis-averaged
# analytic face value. WENO5 is positively homogeneous, so on a separable
# manufactured solution u(x,y) = f(x) g(y) the 2D sweep degenerates to the
# 1D kernel scaled by the orthogonal cell average — preserving the
# Henrick-Aslam-Powers ≥ 4.5 smooth-MMS rate without re-deriving WENO5
# weights in 2D.
function _mms_weno5_convergence_2d(spec::AbstractDict, input_json::AbstractDict,
                                   declared::Float64,
                                   manufactured)::MMSConvergenceResult
    axes_block = spec["axes"]
    axes_block isa AbstractDict || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "WENO5 2D rule's `axes` field must be a mapping, got $(typeof(axes_block))"))

    axis = String(get(input_json, "axis", "x"))
    axis in ("x", "y") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `axis` must be \"x\" or \"y\" (got $(repr(axis)))"))
    haskey(axes_block, axis) || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "WENO5 2D rule has no `axes.$(axis)` block " *
        "(available: $(collect(keys(axes_block))))"))
    axis_spec = axes_block[axis]

    side = _parse_reconstruction_side(get(input_json, "reconstruction", "left_biased"))
    eps = Float64(get(input_json, "weno_epsilon", 1e-6))

    manufactured isa Union{Nothing,ReconstructionManufacturedSolution2D} ||
        throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "2D WENO5 sweep requires a `ReconstructionManufacturedSolution2D`, " *
            "got $(typeof(manufactured))"))
    ms = manufactured === nothing ?
        lookup_manufactured_solution_2d_reconstruction(input_json["manufactured_solution"]) :
        manufactured

    raw_grids = input_json["grids"]
    raw_grids isa AbstractVector || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "input.esm `grids` must be an array, got $(typeof(raw_grids))"))
    grid_pairs = Tuple{Int,Int}[]
    for g in raw_grids
        if haskey(g, "nx") && haskey(g, "ny")
            push!(grid_pairs, (Int(g["nx"]), Int(g["ny"])))
        elseif haskey(g, "n")
            n = Int(g["n"])
            push!(grid_pairs, (n, n))
        else
            throw(MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "2D WENO5 grid entry must carry `nx`+`ny` or `n`; " *
                "got keys $(collect(keys(g)))"))
        end
    end
    length(grid_pairs) >= 2 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "convergence requires at least two grids; got $(grid_pairs)"))

    (xlo, xhi), (ylo, yhi) = ms.domain
    Lx = xhi - xlo
    Ly = yhi - ylo
    Lx > 0 && Ly > 0 || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "2D WENO5 MMS requires positive domain extents; got $(ms.domain)"))

    # Index the convergence sequence by the along-axis resolution.
    grids = Int[axis == "x" ? nx : ny for (nx, ny) in grid_pairs]
    errors = Vector{Float64}(undef, length(grid_pairs))
    for (k, (nx, ny)) in enumerate(grid_pairs)
        dx = Lx / nx
        dy = Ly / ny
        u = Matrix{Float64}(undef, nx, ny)
        for j in 1:ny, i in 1:nx
            u[i, j] = ms.cell_average(xlo + (i - 1) * dx, xlo + i * dx,
                                      ylo + (j - 1) * dy, ylo + j * dy)
        end
        if axis == "x"
            err = 0.0
            for j in 1:ny
                col = Vector{Float64}(undef, nx)
                @inbounds for i in 1:nx
                    col[i] = u[i, j]
                end
                qhat = apply_weno5_reconstruction_periodic_1d(axis_spec, col, side; eps=eps)
                ylo_j = ylo + (j - 1) * dy
                yhi_j = ylo + j * dy
                @inbounds for i in 1:nx
                    xf = side === :left_biased ? xlo + i * dx : xlo + (i - 1) * dx
                    truth = ms.face_average_x(xf, ylo_j, yhi_j)
                    err = max(err, abs(qhat[i] - truth))
                end
            end
            errors[k] = err
        else  # axis == "y"
            err = 0.0
            for i in 1:nx
                row = Vector{Float64}(undef, ny)
                @inbounds for j in 1:ny
                    row[j] = u[i, j]
                end
                qhat = apply_weno5_reconstruction_periodic_1d(axis_spec, row, side; eps=eps)
                xlo_i = xlo + (i - 1) * dx
                xhi_i = xlo + i * dx
                @inbounds for j in 1:ny
                    yf = side === :left_biased ? ylo + j * dy : ylo + (j - 1) * dy
                    truth = ms.face_average_y(xlo_i, xhi_i, yf)
                    err = max(err, abs(qhat[j] - truth))
                end
            end
            errors[k] = err
        end
    end

    return _finalize_convergence(grids, errors, declared)
end
