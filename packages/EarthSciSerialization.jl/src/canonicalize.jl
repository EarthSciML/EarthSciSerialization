# Canonical AST form per discretization RFC §5.4.
#
# Implements `canonicalize(expr)` and `canonical_json(expr)` such that two
# ASTs are canonically equal iff their `canonical_json` outputs are
# byte-identical.
#
# See `docs/rfcs/discretization.md` §5.4.1–§5.4.7 for the normative rules.

"""
    CanonicalizeError(code::String, message::String)

Error raised by [`canonicalize`](@ref). The `code` field carries one of the
RFC §5.4.6 / §5.4.7 stable error codes (`E_CANONICAL_NONFINITE`,
`E_CANONICAL_DIVBY_ZERO`).
"""
struct CanonicalizeError <: Exception
    code::String
    message::String
end

Base.showerror(io::IO, e::CanonicalizeError) =
    print(io, "CanonicalizeError(", e.code, "): ", e.message)

"""
    canonicalize(expr::Expr) -> Expr

Canonicalize an expression tree per discretization RFC §5.4. Returns a new
tree; the input is not mutated. Throws [`CanonicalizeError`](@ref) for
NaN/Inf or `0/0`.
"""
function canonicalize end

canonicalize(e::IntExpr) = e

function canonicalize(e::NumExpr)
    isfinite(e.value) || throw(CanonicalizeError("E_CANONICAL_NONFINITE",
        "non-finite float in canonical form"))
    return e
end

canonicalize(e::VarExpr) = e

function canonicalize(e::OpExpr)
    new_args = Vector{Expr}(undef, length(e.args))
    for (i, a) in enumerate(e.args)
        new_args[i] = canonicalize(a)
    end
    work = OpExpr(e.op, new_args;
                  wrt=e.wrt, dim=e.dim, output_idx=e.output_idx,
                  expr_body=e.expr_body, reduce=e.reduce, ranges=e.ranges,
                  regions=e.regions, values=e.values, shape=e.shape,
                  perm=e.perm, axis=e.axis, fn=e.fn,
                  name=e.name, value=e.value)
    if work.op == "+"
        return _canon_add(work)
    elseif work.op == "*"
        return _canon_mul(work)
    elseif work.op == "-"
        return _canon_sub(work)
    elseif work.op == "/"
        return _canon_div(work)
    elseif work.op == "neg"
        return _canon_neg(work)
    end
    return work
end

function _canon_add(node::OpExpr)
    flat = _flatten_same_op(node.args, "+")
    others, _had_int_zero, had_float_zero = _partition_identity(flat, 0)
    if had_float_zero && !_all_float_literals(others)
        push!(others, NumExpr(0.0))
    end
    if isempty(others)
        return had_float_zero ? NumExpr(0.0) : IntExpr(0)
    end
    if length(others) == 1
        return others[1]
    end
    _sort_args!(others)
    return OpExpr("+", others)
end

function _canon_mul(node::OpExpr)
    flat = _flatten_same_op(node.args, "*")
    for a in flat
        if a isa IntExpr && a.value == 0
            return IntExpr(0)
        end
        if a isa NumExpr && a.value == 0.0
            # Preserve signbit: -0.0 stays as -0.0 via copysign.
            return NumExpr(copysign(0.0, a.value))
        end
    end
    others, _had_int_one, had_float_one = _partition_identity(flat, 1)
    if had_float_one && !_all_float_literals(others)
        push!(others, NumExpr(1.0))
    end
    if isempty(others)
        return had_float_one ? NumExpr(1.0) : IntExpr(1)
    end
    if length(others) == 1
        return others[1]
    end
    _sort_args!(others)
    return OpExpr("*", others)
end

function _canon_sub(node::OpExpr)
    if length(node.args) == 1
        return _canon_neg_value(node.args[1])
    end
    if length(node.args) == 2
        a, b = node.args[1], node.args[2]
        if _is_zero_any(a)
            return _canon_neg_value(b)
        end
        if _is_zero_any(b)
            if b isa NumExpr && a isa IntExpr
                return NumExpr(Float64(a.value))
            end
            return a
        end
    end
    return node
end

function _canon_div(node::OpExpr)
    length(node.args) == 2 || return node
    a, b = node.args[1], node.args[2]
    if _is_zero_any(a) && _is_zero_any(b)
        throw(CanonicalizeError("E_CANONICAL_DIVBY_ZERO", "0/0 in canonical form"))
    end
    if _is_one_any(b)
        if b isa NumExpr && a isa IntExpr
            return NumExpr(Float64(a.value))
        end
        return a
    end
    if _is_zero_any(a)
        return a isa NumExpr ? NumExpr(0.0) : IntExpr(0)
    end
    return node
end

function _canon_neg(node::OpExpr)
    length(node.args) == 1 || return node
    return _canon_neg_value(node.args[1])
end

function _canon_neg_value(arg::Expr)
    if arg isa IntExpr
        return IntExpr(-arg.value)
    elseif arg isa NumExpr
        return NumExpr(-arg.value)
    elseif arg isa OpExpr && arg.op == "neg" && length(arg.args) == 1
        return arg.args[1]
    end
    return OpExpr("neg", Expr[arg])
end

function _flatten_same_op(args::Vector{Expr}, op::String)
    out = Expr[]
    for a in args
        if a isa OpExpr && a.op == op
            append!(out, a.args)
        else
            push!(out, a)
        end
    end
    return out
end

function _partition_identity(args::Vector{Expr}, identity::Int)
    others = Expr[]
    had_int = false
    had_float = false
    for a in args
        if a isa IntExpr && a.value == identity
            had_int = true
            continue
        end
        if a isa NumExpr && a.value == Float64(identity)
            had_float = true
            continue
        end
        push!(others, a)
    end
    return others, had_int, had_float
end

_all_float_literals(args::Vector{Expr}) = !isempty(args) && all(a -> a isa NumExpr, args)

_is_zero_any(e) = (e isa IntExpr && e.value == 0) || (e isa NumExpr && e.value == 0.0)
_is_one_any(e)  = (e isa IntExpr && e.value == 1) || (e isa NumExpr && e.value == 1.0)

function _arg_tier(e::Expr)
    if e isa IntExpr || e isa NumExpr
        return 0
    elseif e isa VarExpr
        return 1
    elseif e isa OpExpr
        return 2
    end
    return 3
end

_numeric_key(e::IntExpr) = Float64(e.value)
_numeric_key(e::NumExpr) = e.value
_numeric_key(e::Expr)    = 0.0

function _sort_args!(args::Vector{Expr})
    cache = Dict{Int,String}()
    function get_json(idx::Int, e::Expr)
        haskey(cache, idx) && return cache[idx]
        s = _emit_json(e)
        cache[idx] = s
        return s
    end
    indices = collect(1:length(args))
    sort!(indices; lt = (i, j) -> _compare(args[i], args[j], i, j, get_json))
    snap = [args[i] for i in indices]
    for i in 1:length(args)
        args[i] = snap[i]
    end
end

function _compare(a::Expr, b::Expr, ia::Int, ib::Int, get_json)
    ta, tb = _arg_tier(a), _arg_tier(b)
    if ta != tb
        return ta < tb
    end
    if ta == 0
        av, bv = _numeric_key(a), _numeric_key(b)
        if av != bv
            return av < bv
        end
        # int before float at equal magnitude.
        return (a isa IntExpr) && (b isa NumExpr)
    elseif ta == 1
        return (a::VarExpr).name < (b::VarExpr).name
    else
        return get_json(ia, a) < get_json(ib, b)
    end
end

"""
    canonical_json(expr::Expr) -> String

Emit the canonical on-wire JSON form of an expression per RFC §5.4.6: keys
sorted, no extraneous whitespace, shortest round-trip floats with trailing-`.0`
disambiguation for integer-valued magnitudes, exponent-form (`1e25`, `5e-324`)
outside `[1e-6, 1e21)`, signed zero preserved.
"""
function canonical_json(expr::Expr)::String
    return _emit_json(canonicalize(expr))
end

function _emit_json(e::Expr)::String
    if e isa IntExpr
        return string(e.value)
    elseif e isa NumExpr
        return format_canonical_float(e.value)
    elseif e isa VarExpr
        return _json_string(e.name)
    elseif e isa OpExpr
        return _emit_node_json(e)
    end
    error("cannot canonicalize value of type $(typeof(e))")
end

function _emit_node_json(n::OpExpr)::String
    entries = Tuple{String,String}[]
    push!(entries, ("op", _json_string(n.op)))
    args_str = "[" * join((_emit_json(a) for a in n.args), ",") * "]"
    push!(entries, ("args", args_str))
    if n.wrt !== nothing
        push!(entries, ("wrt", _json_string(n.wrt::String)))
    end
    if n.dim !== nothing
        push!(entries, ("dim", _json_string(n.dim::String)))
    end
    if n.name !== nothing
        push!(entries, ("name", _json_string(n.name::String)))
    end
    if n.value !== nothing
        push!(entries, ("value", _emit_canonical_value(n.value)))
    end
    sort!(entries, by = kv -> kv[1])
    body = join(("$(_json_string(k)):$v" for (k, v) in entries), ",")
    return "{" * body * "}"
end

function _json_string(s::AbstractString)::String
    # Use JSON3 to escape, but JSON3.write returns a string with surrounding
    # quotes. Strip and re-quote to avoid newlines/etc.
    return JSON3.write(String(s))
end

# Canonical JSON for `const`-op values. Values are JSON-typed (integer,
# Float64, AbstractString, or nested arrays thereof per esm-spec §4.2 / §9.2).
# Floats use the same canonical-float formatter as `NumExpr`; integers emit
# as bare digit-only tokens; arrays recurse element-wise.
function _emit_canonical_value(v)::String
    if v isa Bool
        return v ? "true" : "false"
    elseif v isa Integer
        return string(v)
    elseif v isa AbstractFloat
        return format_canonical_float(Float64(v))
    elseif v isa AbstractString
        return _json_string(v)
    elseif v isa AbstractArray
        return "[" * join((_emit_canonical_value(x) for x in v), ",") * "]"
    end
    throw(CanonicalizeError("E_CANONICAL_NONFINITE",
        "unsupported `const` value type: $(typeof(v))"))
end

"""
    format_canonical_float(f::Float64) -> String

Format a finite `Float64` per RFC §5.4.6.
"""
function format_canonical_float(f::Float64)::String
    isfinite(f) || throw(CanonicalizeError("E_CANONICAL_NONFINITE",
        "non-finite float in canonical form"))
    if f == 0.0
        return signbit(f) ? "-0.0" : "0.0"
    end
    a = abs(f)
    use_exp = a < 1e-6 || a >= 1e21
    if use_exp
        # Julia's default Base.show gives shortest round-trip ("Ryu"); for
        # scientific values it prints e.g. "1.0e25" or "5.0e-324". Need to
        # normalize: strip mantissa trailing zeros after '.', strip leading
        # exponent zeros, no leading + on exp.
        return _normalize_julia_exp(repr(f))
    end
    s = repr(f)
    if occursin('e', s) || occursin('E', s)
        # Within plain range but Julia chose exponent — convert to plain.
        s = _expand_to_plain(f)
    end
    if !occursin('.', s)
        s *= ".0"
    end
    return s
end

function _normalize_julia_exp(s::String)::String
    # Examples: "1.0e25" -> "1e25", "5.0e-324" -> "5e-324", "3.14e-10" -> "3.14e-10"
    s = lowercase(s)
    if !occursin('e', s)
        return s
    end
    parts = split(s, 'e'; limit=2)
    mant = parts[1]
    exp = parts[2]
    # Strip mantissa trailing zeros after '.'.
    if occursin('.', mant)
        mant = rstrip(mant, '0')
        mant = rstrip(mant, '.')
    end
    if isempty(mant)
        mant = "0"
    end
    # Normalize exponent: drop leading +, drop leading 0s preserving sign.
    if startswith(exp, "+")
        exp = exp[2:end]
    end
    sign = ""
    if startswith(exp, "-")
        sign = "-"
        exp = exp[2:end]
    end
    exp = lstrip(exp, '0')
    if isempty(exp)
        exp = "0"
    end
    return string(mant, "e", sign, exp)
end

function _expand_to_plain(f::Float64)::String
    # Julia's @sprintf with %.17g preserves precision; then trim trailing zeros.
    # Simpler: convert via string and special-case the rare path.
    s = repr(f)
    if !occursin('e', lowercase(s))
        return s
    end
    # Use BigFloat to get a clean expansion then trim.
    b = BigFloat(s)
    # Render without exponent — use printf format.
    out = string(b)
    # `string(BigFloat)` may still use scientific. Fallback: format manually.
    if occursin('e', lowercase(out))
        # Manual: split mantissa and exponent, shift decimal.
        parts = split(lowercase(s), 'e')
        mant = parts[1]
        exp = parse(Int, parts[2])
        out = _shift_decimal(mant, exp)
    end
    if occursin('.', out)
        out = rstrip(out, '0')
        out = rstrip(out, '.')
    end
    return out
end

function _shift_decimal(mant::AbstractString, exp::Int)::String
    sign = ""
    if startswith(mant, '-')
        sign = "-"
        mant = mant[2:end]
    end
    if !occursin('.', mant)
        mant = mant * "."
    end
    dot = findfirst('.', mant)
    digits = String(replace(String(mant), '.' => ""))
    pos = dot - 1 + exp  # new decimal position from start
    if pos <= 0
        digits = "0"^(1 - pos) * digits
        pos = 1
    elseif pos > length(digits)
        digits = digits * "0"^(pos - length(digits))
    end
    if pos == length(digits)
        return string(sign, digits)
    end
    return string(sign, digits[1:pos], ".", digits[pos+1:end])
end
