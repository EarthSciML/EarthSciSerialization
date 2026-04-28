"""
Closed function registry — Julia reference implementation (esm-tzp / esm-4aw).

Implements the spec-defined closed function set from esm-spec §9.2:

* `datetime.year`, `month`, `day`, `hour`, `minute`, `second`,
  `day_of_year`, `julian_day`, `is_leap_year` — proleptic-Gregorian
  calendar decomposition of an IEEE-754 `binary64` UTC scalar
  (seconds since the Unix epoch, no leap-second consultation).
* `interp.searchsorted` — 1-based search-into-sorted-array (Julia's
  `searchsortedfirst` semantics with explicit out-of-range / NaN /
  duplicate behavior pinned by spec).
* `interp.linear` / `interp.bilinear` — 1-D / 2-D linear interpolation
  with extrapolate-flat boundaries. Pinned evaluation order
  (`a + w * (b - a)`) for cross-binding bit-equivalence on
  exactly-representable IEEE-754 inputs (esm-94w).

The set is **closed**: callers MUST reject any `fn`-op `name` outside this
list (diagnostic `unknown_closed_function`). This module provides:

- [`closed_function_names`](@ref) — the public closed-set as a `Set{String}`.
- [`evaluate_closed_function`](@ref) — dispatch entry point used by both the
  expression-tree evaluator (`expression.jl`) and the tree-walk evaluator
  (`tree_walk.jl`).
- [`lower_enums!`](@ref) — load-time pass that resolves every `enum` op in an
  [`EsmFile`](@ref) to a `const` integer per esm-spec §9.3.
- [`ClosedFunctionError`](@ref) — error type carrying spec-defined diagnostic
  codes (`unknown_closed_function`, `closed_function_overflow`,
  `searchsorted_non_monotonic`, `closed_function_arity`).

Calendar arithmetic uses the Julia stdlib `Dates` module with the
proleptic-Gregorian default; the v0.3.0 spec contract forbids leap-second
consultation, which `Dates` already honors. `julian_day` is computed via the
Fliegel–van Flandern (1968) integer formula plus the fractional-day offset,
giving ≤ 1 ulp agreement with the spec reference.
"""

using Dates

"""
    ClosedFunctionError(code::String, message::String)

Raised by the closed function registry when the spec contract is violated.
`code` is one of the stable diagnostic codes pinned by esm-spec §9.1–§9.2:

- `unknown_closed_function` — `fn`-op `name` is not in the v0.3.0 set.
- `closed_function_arity` — wrong number of arguments for the named function.
- `closed_function_overflow` — integer-typed result would overflow Int32.
- `searchsorted_non_monotonic` — `xs` is not non-decreasing.
- `searchsorted_nan_in_table` — `xs` contains a NaN entry.
- `interp_non_monotonic_axis` — `interp.linear` / `interp.bilinear` axis is
  not strictly increasing (esm-spec §9.2; equal-adjacent rejected because the
  blend denominator would be zero).
- `interp_axis_length_mismatch` — `interp.linear`: `len(table) != len(axis)`;
  `interp.bilinear`: `len(table) != len(axis_x)`, or any inner row length
  differs from `len(axis_y)`.
- `interp_nan_in_axis` — any `axis` (or `axis_x`, `axis_y`) contains a NaN.
- `interp_axis_too_short` — any axis has fewer than 2 entries.
- `interp_table_not_const` / `interp_axis_not_const` — table / axis argument
  is not a literal `const`-op array (e.g. a variable reference). Raised by
  the AST extraction site, not by `evaluate_closed_function` directly.
"""
struct ClosedFunctionError <: Exception
    code::String
    message::String
end

Base.showerror(io::IO, e::ClosedFunctionError) =
    print(io, "ClosedFunctionError(", e.code, "): ", e.message)

"""
    closed_function_names() -> Set{String}

Return the v0.3.0 closed function set. Bindings MUST reject any `fn`-op
`name` not in this set. The set is intentionally narrow; new entries
require a spec rev (esm-spec §9.1).
"""
function closed_function_names()::Set{String}
    return Set{String}([
        "datetime.year",
        "datetime.month",
        "datetime.day",
        "datetime.hour",
        "datetime.minute",
        "datetime.second",
        "datetime.day_of_year",
        "datetime.julian_day",
        "datetime.is_leap_year",
        "interp.searchsorted",
        "interp.linear",
        "interp.bilinear",
    ])
end

const _CLOSED_FUNCTION_NAMES = closed_function_names()

# Range-check an integer-typed closed-function result and box as Int32. The
# spec pins integer outputs to signed 32-bit; `Dates.year(t_utc)` could in
# principle exceed that for absurd inputs.
function _check_int32(name::String, v::Integer)::Int32
    if v < typemin(Int32) || v > typemax(Int32)
        throw(ClosedFunctionError("closed_function_overflow",
            "$(name): result $(v) overflows Int32"))
    end
    return Int32(v)
end

"""
    evaluate_closed_function(name::String, args::Vector) -> Any

Dispatch a closed function call. `name` is the dotted-module spec name
(e.g. `"datetime.julian_day"`); `args` is a vector of evaluated argument
values. Integer-typed results are returned as `Int32` to make the integer
contract explicit to callers; float-typed results are `Float64`.

For `interp.searchsorted` the second argument must be the table (a
`Vector{<:Real}`) — the caller is responsible for extracting the array
from a `const`-op AST node before invoking this function.

Throws [`ClosedFunctionError`](@ref) on contract violations.
"""
function evaluate_closed_function(name::String, args::AbstractVector)
    if !(name in _CLOSED_FUNCTION_NAMES)
        throw(ClosedFunctionError("unknown_closed_function",
            "`fn` name `$(name)` is not in the v0.3.0 closed function registry " *
            "(esm-spec §9.2). Adding a primitive requires a spec rev."))
    end

    if name == "datetime.year"
        _expect_arity(name, args, 1)
        return _check_int32(name, year(_to_datetime(args[1])))
    elseif name == "datetime.month"
        _expect_arity(name, args, 1)
        return Int32(month(_to_datetime(args[1])))
    elseif name == "datetime.day"
        _expect_arity(name, args, 1)
        return Int32(day(_to_datetime(args[1])))
    elseif name == "datetime.hour"
        _expect_arity(name, args, 1)
        return Int32(hour(_to_datetime(args[1])))
    elseif name == "datetime.minute"
        _expect_arity(name, args, 1)
        return Int32(minute(_to_datetime(args[1])))
    elseif name == "datetime.second"
        _expect_arity(name, args, 1)
        return Int32(second(_to_datetime(args[1])))
    elseif name == "datetime.day_of_year"
        _expect_arity(name, args, 1)
        return Int32(dayofyear(_to_datetime(args[1])))
    elseif name == "datetime.julian_day"
        _expect_arity(name, args, 1)
        return _datetime_julian_day(Float64(args[1]))
    elseif name == "datetime.is_leap_year"
        _expect_arity(name, args, 1)
        y = year(_to_datetime(args[1]))
        return isleapyear(y) ? Int32(1) : Int32(0)
    elseif name == "interp.searchsorted"
        _expect_arity(name, args, 2)
        return _interp_searchsorted(name, Float64(args[1]), args[2])
    elseif name == "interp.linear"
        _expect_arity(name, args, 3)
        return _interp_linear(name, args[1], args[2], Float64(args[3]))
    elseif name == "interp.bilinear"
        _expect_arity(name, args, 5)
        return _interp_bilinear(name, args[1], args[2], args[3],
                                Float64(args[4]), Float64(args[5]))
    end
    # Should be unreachable — `name in _CLOSED_FUNCTION_NAMES` covered above.
    throw(ClosedFunctionError("unknown_closed_function",
        "internal: `fn` name `$(name)` is in the registry but has no dispatch arm"))
end

# Convert a UTC scalar time (seconds since Unix epoch) to a `Dates.DateTime`
# at millisecond resolution. The spec pins floor-divmod by 86400 for the
# (date, time-of-day) split; `Dates.unix2datetime` does this with the
# proleptic-Gregorian calendar already.
@inline function _to_datetime(t_utc)::DateTime
    return unix2datetime(Float64(t_utc))
end

# Fliegel–van Flandern (1968) integer JDN, plus fractional-day offset from
# noon-UTC. Returns Float64 with ≤ 1 ulp agreement to the spec reference
# computation — the only floating-point operation is the final divide by
# 86400 (one rounded operation).
function _datetime_julian_day(t_utc::Float64)::Float64
    dt = unix2datetime(t_utc)
    y = year(dt); m = month(dt); d = day(dt)
    jdn = (1461 * (y + 4800 + (m - 14) ÷ 12)) ÷ 4 +
          (367 * (m - 2 - 12 * ((m - 14) ÷ 12))) ÷ 12 -
          (3 * ((y + 4900 + (m - 14) ÷ 12) ÷ 100)) ÷ 4 +
          d - 32075
    # JDN counts noon-to-noon; convert time-of-day seconds (since 00:00 UTC)
    # to a fractional offset relative to noon. The spec pins this offset as
    # `(time_of_day_seconds − 43200) / 86400` (esm-spec §9.2.1).
    seconds_in_day = mod(t_utc, 86400.0)
    return Float64(jdn) + (seconds_in_day - 43200.0) / 86400.0
end

# `interp.searchsorted` per esm-spec §9.2.2: 1-based, left-side bias
# (smallest `i` with `xs[i] ≥ x`), out-of-range below → 1, above → N+1,
# NaN x → N+1, NaN entries in xs → error, non-monotonic xs → error.
function _interp_searchsorted(name::String, x::Float64, xs)::Int32
    if !(xs isa AbstractVector)
        throw(ClosedFunctionError("closed_function_arity",
            "$(name): xs argument must be an array (got $(typeof(xs)))"))
    end
    n = length(xs)
    if n == 0
        # An empty table has no valid index; return 1 per the "above-range
        # → N+1" rule extended to N=0 (the only consistent extension that
        # composes with `index`).
        return Int32(1)
    end
    # Validate monotonicity + NaN-in-table once per call.
    prev = NaN
    for (i, raw) in enumerate(xs)
        v = Float64(raw)
        if isnan(v)
            throw(ClosedFunctionError("searchsorted_nan_in_table",
                "$(name): xs[$(i)] is NaN; NaN entries in xs are forbidden"))
        end
        if i > 1 && v < prev
            throw(ClosedFunctionError("searchsorted_non_monotonic",
                "$(name): xs is not non-decreasing (xs[$(i)]=$(v) < xs[$(i-1)]=$(prev))"))
        end
        prev = v
    end
    # NaN x → N+1 (treated as "greater than every finite element").
    if isnan(x)
        return _check_int32(name, n + 1)
    end
    # Linear scan for the smallest 1-based index with xs[i] ≥ x. The spec
    # mandates left-side bias on duplicates; binary search would also work
    # but linear is O(N) on table sizes that the §9.2 inline-cap pins
    # to ≤ 1024 entries.
    @inbounds for i in 1:n
        if Float64(xs[i]) >= x
            return _check_int32(name, i)
        end
    end
    return _check_int32(name, n + 1)
end

# Validate a 1-D axis used by `interp.linear` / `interp.bilinear`. Per
# esm-spec §9.2: strictly increasing, no NaN, length ≥ 2. Returns the axis
# coerced to `Vector{Float64}` for downstream blending. `axis_label` names
# the failing axis ("axis", "axis_x", "axis_y") for the diagnostic.
function _validate_interp_axis(name::String, axis_raw, axis_label::String)::Vector{Float64}
    if !(axis_raw isa AbstractVector)
        throw(ClosedFunctionError("closed_function_arity",
            "$(name): `$(axis_label)` must be an array (got $(typeof(axis_raw)))"))
    end
    n = length(axis_raw)
    if n < 2
        throw(ClosedFunctionError("interp_axis_too_short",
            "$(name): `$(axis_label)` has $(n) entries; need ≥ 2 to define a blend interval."))
    end
    out = Vector{Float64}(undef, n)
    @inbounds for i in 1:n
        v = Float64(axis_raw[i])
        if isnan(v)
            throw(ClosedFunctionError("interp_nan_in_axis",
                "$(name): `$(axis_label)`[$(i)] is NaN; axis arrays must be all-finite."))
        end
        if i > 1 && !(v > out[i-1])
            throw(ClosedFunctionError("interp_non_monotonic_axis",
                "$(name): `$(axis_label)` is not strictly increasing " *
                "(`$(axis_label)`[$(i)] = $(v) is not > `$(axis_label)`[$(i-1)] = $(out[i-1]))."))
        end
        out[i] = v
    end
    return out
end

# `interp.linear` per esm-spec §9.2: extrapolate-flat clamps + pinned
# evaluation order `t[i] + w * (t[i+1] - t[i])` for endpoint exactness.
function _interp_linear(name::String, table_raw, axis_raw, x::Float64)::Float64
    if !(table_raw isa AbstractVector)
        throw(ClosedFunctionError("closed_function_arity",
            "$(name): `table` must be an array (got $(typeof(table_raw)))"))
    end
    axis = _validate_interp_axis(name, axis_raw, "axis")
    if length(table_raw) != length(axis)
        throw(ClosedFunctionError("interp_axis_length_mismatch",
            "$(name): `len(table)` = $(length(table_raw)) but `len(axis)` = $(length(axis))."))
    end
    n = length(axis)
    # Extrapolate-flat clamps. NaN x bypasses both clamps (IEEE-754 ≤/≥ on NaN
    # are false) and falls through to the in-cell blend, where (x - axis[i])
    # is NaN and propagates through the result — matching the spec.
    if x <= axis[1]
        return Float64(table_raw[1])
    elseif x >= axis[n]
        return Float64(table_raw[n])
    end
    # In-range: locate i with axis[i] ≤ x < axis[i+1]. n ≥ 2 guaranteed by
    # `_validate_interp_axis`. Linear scan; tables are §9.2-capped at the
    # const-op inline limit, so this is O(N) on small N.
    i = 1
    @inbounds for k in 1:(n - 1)
        if axis[k] <= x < axis[k + 1]
            i = k
            break
        end
    end
    @inbounds begin
        ai   = axis[i];     ai1   = axis[i + 1]
        ti   = Float64(table_raw[i]);    ti1 = Float64(table_raw[i + 1])
        w    = (x - ai) / (ai1 - ai)
        return ti + w * (ti1 - ti)
    end
end

# `interp.bilinear` per esm-spec §9.2: per-axis extrapolate-flat clamps,
# cell-location convention "largest i with x_i ≤ x_q", pinned evaluation
# order (two x-blends, one y-blend, each in `a + w*(b-a)` form).
function _interp_bilinear(name::String, table_raw, axis_x_raw, axis_y_raw,
                          x::Float64, y::Float64)::Float64
    if !(table_raw isa AbstractVector)
        throw(ClosedFunctionError("closed_function_arity",
            "$(name): `table` must be an array (got $(typeof(table_raw)))"))
    end
    axis_x = _validate_interp_axis(name, axis_x_raw, "axis_x")
    axis_y = _validate_interp_axis(name, axis_y_raw, "axis_y")
    Nx = length(axis_x)
    Ny = length(axis_y)
    if length(table_raw) != Nx
        throw(ClosedFunctionError("interp_axis_length_mismatch",
            "$(name): outer `len(table)` = $(length(table_raw)) but `len(axis_x)` = $(Nx)."))
    end
    # Validate every inner row length matches Ny (rejects ragged tables).
    @inbounds for i in 1:Nx
        row = table_raw[i]
        if !(row isa AbstractVector)
            throw(ClosedFunctionError("closed_function_arity",
                "$(name): `table[$(i)]` must be an array (got $(typeof(row)))"))
        end
        if length(row) != Ny
            throw(ClosedFunctionError("interp_axis_length_mismatch",
                "$(name): `len(table[$(i)])` = $(length(row)) but `len(axis_y)` = $(Ny)."))
        end
    end
    # Per-axis extrapolate-flat clamp. NaN x or y propagates through (IEEE-754
    # ≤/≥ on NaN are false → x_q stays NaN → wx is NaN → result is NaN).
    x_q = x <= axis_x[1] ? axis_x[1] :
          x >= axis_x[Nx] ? axis_x[Nx] : x
    y_q = y <= axis_y[1] ? axis_y[1] :
          y >= axis_y[Ny] ? axis_y[Ny] : y
    # Cell location: largest i in [1, Nx-1] with axis_x[i] ≤ x_q (analog j).
    # Default to last cell so the corner-at-max case (wx = 1) lands correctly
    # in the pinned-form blend. NaN x_q falls through with i = Nx-1 (irrelevant
    # because the blend will be NaN anyway).
    i = Nx - 1
    @inbounds for k in (Nx - 1):-1:1
        if axis_x[k] <= x_q
            i = k
            break
        end
    end
    j = Ny - 1
    @inbounds for k in (Ny - 1):-1:1
        if axis_y[k] <= y_q
            j = k
            break
        end
    end
    @inbounds begin
        xi   = axis_x[i];   xip1 = axis_x[i + 1]
        yj   = axis_y[j];   yjp1 = axis_y[j + 1]
        wx = (x_q - xi) / (xip1 - xi)
        wy = (y_q - yj) / (yjp1 - yj)
        # Two 1-D x-blends, then one y-blend. Pinned form `a + w*(b - a)`
        # required for cross-binding bit-equivalence (esm-spec §9.2).
        t_ij     = Float64(table_raw[i][j])
        t_i1j    = Float64(table_raw[i + 1][j])
        t_ijp1   = Float64(table_raw[i][j + 1])
        t_i1jp1  = Float64(table_raw[i + 1][j + 1])
        row_j   = t_ij    + wx * (t_i1j   - t_ij)
        row_jp1 = t_ijp1  + wx * (t_i1jp1 - t_ijp1)
        return row_j + wy * (row_jp1 - row_j)
    end
end

@inline function _expect_arity(name::String, args::AbstractVector, n::Int)
    length(args) == n ||
        throw(ClosedFunctionError("closed_function_arity",
            "$(name) expects $(n) argument(s), got $(length(args))"))
    return nothing
end

# ============================================================
# Enum lowering — esm-spec §9.3
# ============================================================

"""
    lower_enums!(file::EsmFile)

Walk every expression tree in `file` and replace each `enum` op with a
`const` integer per the file's `enums` block. After this pass runs, no
`enum`-op nodes remain in the in-memory representation.

Validation (esm-spec §9.3):
- An `enum` op naming an undeclared enum raises `ParseError("unknown_enum: ...")`.
- An `enum` op naming a symbol not declared under that enum raises
  `ParseError("unknown_enum_symbol: ...")`.
- A file with no `enums` block raises if any `enum` op is encountered.

Mutates `file` in place; returns the file for convenience.
"""
function lower_enums!(file::EsmFile)::EsmFile
    enums = file.enums === nothing ? Dict{String,Dict{String,Int}}() : file.enums
    if file.models !== nothing
        for (_, m) in file.models
            _lower_model_enums!(m, enums)
        end
    end
    if file.reaction_systems !== nothing
        for (_, rs) in file.reaction_systems
            _lower_reaction_system_enums!(rs, enums)
        end
    end
    if file.coupling !== nothing
        for ce in file.coupling
            _lower_coupling_entry_enums!(ce, enums)
        end
    end
    return file
end

function _lower_model_enums!(model::Model, enums::Dict{String,Dict{String,Int}})
    for (_, var) in model.variables
        if var.expression !== nothing
            # ModelVariable.expression is read-only after construction, so we
            # rebuild the dict entry with the lowered expression.
            lowered = _lower_expr_enums(var.expression, enums)
            if lowered !== var.expression
                _replace_var_expression!(model.variables, var, lowered)
            end
        end
    end
    new_eqs = Equation[]
    for eq in model.equations
        push!(new_eqs, Equation(_lower_expr_enums(eq.lhs, enums),
                                _lower_expr_enums(eq.rhs, enums);
                                _comment=eq._comment))
    end
    empty!(model.equations)
    append!(model.equations, new_eqs)

    new_init_eqs = Equation[]
    for eq in model.initialization_equations
        push!(new_init_eqs, Equation(_lower_expr_enums(eq.lhs, enums),
                                     _lower_expr_enums(eq.rhs, enums);
                                     _comment=eq._comment))
    end
    empty!(model.initialization_equations)
    append!(model.initialization_equations, new_init_eqs)

    for (_, sub) in model.subsystems
        _lower_model_enums!(sub, enums)
    end
end

function _replace_var_expression!(vars::Dict{String,ModelVariable},
                                  var::ModelVariable, new_expr::Expr)
    # ModelVariable is immutable; rebuild it with the new expression and
    # update the dictionary in place. Find the key by identity.
    target_key = nothing
    for (k, v) in vars
        if v === var
            target_key = k
            break
        end
    end
    target_key === nothing && return  # dropped during iteration; ignore
    vars[target_key] = ModelVariable(var.type;
        default=var.default, description=var.description,
        expression=new_expr, units=var.units, default_units=var.default_units,
        shape=var.shape, location=var.location,
        noise_kind=var.noise_kind, correlation_group=var.correlation_group)
end

function _lower_reaction_system_enums!(rs::ReactionSystem,
                                       enums::Dict{String,Dict{String,Int}})
    new_reactions = Reaction[]
    for r in rs.reactions
        # Use getfield to bypass the back-compat property override that
        # turns `r.products`/`r.reactants` into `Dict{String,Float64}`.
        push!(new_reactions, Reaction(getfield(r, :id),
            getfield(r, :substrates),
            getfield(r, :products),
            _lower_expr_enums(getfield(r, :rate), enums);
            name=getfield(r, :name),
            reference=getfield(r, :reference)))
    end
    empty!(rs.reactions)
    append!(rs.reactions, new_reactions)
    for (_, sub) in rs.subsystems
        _lower_reaction_system_enums!(sub, enums)
    end
end

function _lower_coupling_entry_enums!(ce::CouplingEntry,
                                      enums::Dict{String,Dict{String,Int}})
    if ce isa CouplingCouple && haskey(ce.connector, "equations")
        eqs = ce.connector["equations"]
        if eqs isa AbstractVector
            for (i, e) in enumerate(eqs)
                if e isa AbstractDict && haskey(e, "expression")
                    expr_obj = e["expression"]
                    if expr_obj isa Expr
                        e["expression"] = _lower_expr_enums(expr_obj, enums)
                    end
                end
            end
        end
    end
end

# Recursive enum-op lowering. Returns a new tree only if a substitution
# occurred; otherwise returns the input unchanged so identity-based caching
# upstream still works.
function _lower_expr_enums(e::NumExpr, _) ; return e end
function _lower_expr_enums(e::IntExpr, _) ; return e end
function _lower_expr_enums(e::VarExpr, _) ; return e end

function _lower_expr_enums(e::OpExpr,
                           enums::Dict{String,Dict{String,Int}})::Expr
    if e.op == "enum"
        # esm-spec §4.5: args are exactly two strings — the enum name and the
        # symbolic key. Strings come through `parse_expression` as `VarExpr`,
        # so we read `.name` to recover them.
        if length(e.args) != 2
            throw(ParseError("`enum` op expects 2 args (enum_name, symbol_name), got $(length(e.args))"))
        end
        a1, a2 = e.args[1], e.args[2]
        enum_name = a1 isa VarExpr ? a1.name :
                    a1 isa OpExpr && a1.op == "const" && a1.value isa AbstractString ? String(a1.value) :
                    throw(ParseError("`enum` op: first arg must be a string"))
        symbol_name = a2 isa VarExpr ? a2.name :
                      a2 isa OpExpr && a2.op == "const" && a2.value isa AbstractString ? String(a2.value) :
                      throw(ParseError("`enum` op: second arg must be a string"))
        if !haskey(enums, enum_name)
            throw(ParseError("unknown_enum: enum `$(enum_name)` is not declared in the file's `enums` block"))
        end
        mapping = enums[enum_name]
        if !haskey(mapping, symbol_name)
            throw(ParseError("unknown_enum_symbol: symbol `$(symbol_name)` is not declared under enum `$(enum_name)`"))
        end
        return OpExpr("const", Expr[]; value=mapping[symbol_name])
    end
    # Recurse — rebuild the op with lowered arguments.
    new_args = Vector{Expr}(undef, length(e.args))
    changed = false
    for (i, a) in enumerate(e.args)
        new_args[i] = _lower_expr_enums(a, enums)
        if !(new_args[i] === a)
            changed = true
        end
    end
    new_body = e.expr_body === nothing ? nothing : _lower_expr_enums(e.expr_body, enums)
    body_changed = !(new_body === e.expr_body)
    new_values = e.values
    values_changed = false
    if e.values !== nothing
        new_values = Vector{Expr}(undef, length(e.values))
        for (i, v) in enumerate(e.values)
            new_values[i] = _lower_expr_enums(v, enums)
            if !(new_values[i] === v)
                values_changed = true
            end
        end
    end
    # Recurse into table_lookup.axes (per-axis input expression map).
    new_table_axes = e.table_axes
    table_axes_changed = false
    if e.table_axes !== nothing
        new_table_axes = Dict{String,Expr}()
        for (k, v) in e.table_axes
            new_v = _lower_expr_enums(v, enums)
            new_table_axes[k] = new_v
            if !(new_v === v)
                table_axes_changed = true
            end
        end
    end
    if !changed && !body_changed && !values_changed && !table_axes_changed
        return e
    end
    return OpExpr(e.op, new_args;
        wrt=e.wrt, dim=e.dim, output_idx=e.output_idx,
        expr_body=new_body, reduce=e.reduce, ranges=e.ranges,
        regions=e.regions, values=new_values, shape=e.shape,
        perm=e.perm, axis=e.axis, fn=e.fn, name=e.name, value=e.value,
        table=e.table, table_axes=new_table_axes, output=e.output)
end
