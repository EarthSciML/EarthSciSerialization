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
    ManufacturedSolution(name, sample, derivative, periodic, domain)

A registered manufactured solution. `sample(x)` returns u(x); `derivative(x)`
returns du/dx. `periodic` and `domain` describe the sampling support so the
harness can wrap stencils correctly.
"""
struct ManufacturedSolution
    name::Symbol
    sample::Function
    derivative::Function
    periodic::Bool
    domain::Tuple{Float64,Float64}
end

# Built-in: u(x) = sin(2π x) on [0,1] periodic; du/dx = 2π cos(2π x).
const _MMS_SIN_2PI_X_PERIODIC = ManufacturedSolution(
    :sin_2pi_x_periodic,
    x -> sin(2π * x),
    x -> 2π * cos(2π * x),
    true,
    (0.0, 1.0),
)

const _MMS_REGISTRY = Dict{Symbol,ManufacturedSolution}(
    :sin_2pi_x_periodic => _MMS_SIN_2PI_X_PERIODIC,
)

"""
    register_manufactured_solution!(ms::ManufacturedSolution)

Add or replace a manufactured solution in the registry. Returns `ms`.
"""
function register_manufactured_solution!(ms::ManufacturedSolution)
    _MMS_REGISTRY[ms.name] = ms
    return ms
end

"""
    lookup_manufactured_solution(description::AbstractString) -> ManufacturedSolution

Resolve a `manufactured_solution` description string from an `input.esm` to
a registered solution. Matching is loose: punctuation and whitespace are
ignored, so e.g. `"sin(2*pi*x) on [0,1] periodic; …"` resolves to
`:sin_2pi_x_periodic`.
"""
function lookup_manufactured_solution(description::AbstractString)::ManufacturedSolution
    norm = lowercase(replace(String(description), r"[\s\*]" => ""))
    if occursin("sin(2pi", norm) || occursin("sin(2π", norm)
        return _MMS_REGISTRY[:sin_2pi_x_periodic]
    end
    throw(MMSEvaluatorError(
        "E_MMS_UNKNOWN_SOLUTION",
        "no manufactured solution registered for $(repr(description)); " *
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
# Stencil application (1D periodic, cell-centered)
# ============================================================

"""
    apply_stencil_periodic_1d(stencil_json, u::Vector{Float64},
                              bindings::Dict{String,Float64}) -> Vector{Float64}

Apply a 1D Cartesian stencil to the periodic sample vector `u`. Each entry of
`stencil_json` must carry `selector.offset` (Int) and `coeff` (an AST node).
The coefficient is evaluated once per call against `bindings`. The result has
the same length as `u`.

Used by [`mms_convergence`] to drive the manufactured-solution sweep without
re-implementing the stencil semantics in the walker.
"""
function apply_stencil_periodic_1d(stencil_json,
                                   u::Vector{Float64},
                                   bindings::Dict{String,Float64})::Vector{Float64}
    n = length(u)
    coeff_pairs = Vector{Tuple{Int,Float64}}(undef, length(stencil_json))
    for (k, s) in enumerate(stencil_json)
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
"""
function mms_convergence(rule_json::AbstractDict, input_json::AbstractDict;
                         manufactured::Union{Nothing,ManufacturedSolution}=nothing)::MMSConvergenceResult
    rule_name = String(input_json["rule"])
    spec = _resolve_rule_spec(rule_json, rule_name)
    haskey(spec, "stencil") || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "rule $(repr(rule_name)) has no `stencil` field"))
    stencil = spec["stencil"]
    declared = haskey(spec, "accuracy") ?
        parse_accuracy_order(String(spec["accuracy"])) :
        throw(MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "rule $(repr(rule_name)) has no `accuracy` field"))

    ms = manufactured === nothing ?
        lookup_manufactured_solution(String(input_json["manufactured_solution"])) :
        manufactured
    sampling = String(get(input_json, "sampling", "cell_center"))
    sampling == "cell_center" || throw(MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "only `sampling: cell_center` is currently supported (got $(repr(sampling)))"))
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
        bindings = Dict{String,Float64}("dx" => dx, "h" => dx)
        u = [ms.sample(domain_lo + (i - 0.5) * dx) for i in 1:n]
        du_num = apply_stencil_periodic_1d(stencil, u, bindings)
        du_exact = [ms.derivative(domain_lo + (i - 0.5) * dx) for i in 1:n]
        errors[k] = maximum(abs.(du_num .- du_exact))
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
                                manufactured::Union{Nothing,ManufacturedSolution}=nothing,
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
