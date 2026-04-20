# Conformance harness adapter — discretize category (gt-l3dg).
#
# Contract: parse each fixture under tests/conformance/discretize/inputs/,
# run `discretize()` with the manifest's default options, emit canonical
# JSON (sorted keys, RFC §5.4.6 number format, minified), and assert
# byte-identity with the committed golden under
# tests/conformance/discretize/golden/. Each fixture is also run twice to
# assert within-binding determinism.
#
# See tests/conformance/discretize/README.md for the full contract.

using Test
using JSON3
using Printf
using EarthSciSerialization
using EarthSciSerialization: discretize, format_canonical_float

const _DISC_REPO_ROOT   = normpath(joinpath(@__DIR__, "..", "..", ".."))
const _DISC_CONF_DIR    = joinpath(_DISC_REPO_ROOT, "tests", "conformance", "discretize")
const _DISC_MANIFEST    = joinpath(_DISC_CONF_DIR, "manifest.json")
const _DISC_UPDATE_GOLD = get(ENV, "UPDATE_DISCRETIZE_GOLDEN", "") == "1"

# ---------------------------------------------------------------------------
# Canonical whole-document JSON emitter.
#
# Rules (must match the cross-binding contract documented in
# tests/conformance/discretize/README.md):
#   - Objects emit with lexicographically sorted keys.
#   - No inter-token whitespace (minified).
#   - Integers → minimal decimal.
#   - Floats   → format_canonical_float (RFC §5.4.6, same helper the
#                expression-level canonical_json uses).
#   - Booleans / nulls / strings → RFC 8259 forms.
#
# This emitter intentionally does NOT depend on JSON3's writer: JSON3
# preserves Dict insertion order, which is hash-dependent across Julia
# versions and therefore useless for byte-identity.
# ---------------------------------------------------------------------------

function _canon_emit(io::IO, x::AbstractDict)
    print(io, "{")
    ks = sort!(String[string(k) for k in keys(x)])
    for (i, k) in enumerate(ks)
        i > 1 && print(io, ",")
        _canon_emit_string(io, k)
        print(io, ":")
        _canon_emit(io, _canon_lookup(x, k))
    end
    print(io, "}")
end

function _canon_emit(io::IO, xs::AbstractVector)
    print(io, "[")
    for (i, v) in enumerate(xs)
        i > 1 && print(io, ",")
        _canon_emit(io, v)
    end
    print(io, "]")
end

_canon_emit(io::IO, t::Tuple) = _canon_emit(io, collect(t))
_canon_emit(io::IO, s::AbstractString) = _canon_emit_string(io, String(s))
_canon_emit(io::IO, b::Bool)           = print(io, b ? "true" : "false")
_canon_emit(io::IO, ::Nothing)         = print(io, "null")
_canon_emit(io::IO, n::Integer)        = print(io, string(n))
_canon_emit(io::IO, n::AbstractFloat)  = print(io, format_canonical_float(Float64(n)))

# JSON3.Object / JSON3.Array route through the AbstractDict / AbstractVector
# overloads via their iteration interface — but they yield Symbol keys, so
# _canon_lookup handles both string- and symbol-keyed maps.

function _canon_lookup(x::AbstractDict, k::String)
    haskey(x, k) && return x[k]
    sk = Symbol(k)
    haskey(x, sk) && return x[sk]
    error("canonical emit: key $(repr(k)) not found in map with keys $(collect(keys(x)))")
end

function _canon_emit_string(io::IO, s::String)
    print(io, '"')
    for c in s
        cu = UInt32(c)
        if c == '"'        ; print(io, "\\\"")
        elseif c == '\\'   ; print(io, "\\\\")
        elseif cu == 0x08  ; print(io, "\\b")
        elseif cu == 0x09  ; print(io, "\\t")
        elseif cu == 0x0A  ; print(io, "\\n")
        elseif cu == 0x0C  ; print(io, "\\f")
        elseif cu == 0x0D  ; print(io, "\\r")
        elseif cu < 0x20   ; @printf(io, "\\u%04x", cu)
        else               ; print(io, c)
        end
    end
    print(io, '"')
end

function _canonical_json(doc)::String
    io = IOBuffer()
    _canon_emit(io, doc)
    return String(take!(io))
end

# ---------------------------------------------------------------------------
# Harness driver
# ---------------------------------------------------------------------------

function _run_discretize(input_path::String, opts)::Dict{String,Any}
    raw = JSON3.read(read(input_path, String))
    max_passes = Int(get(opts, :max_passes, 32))
    strict     = Bool(get(opts, :strict_unrewritten, true))
    return discretize(raw; max_passes=max_passes, strict_unrewritten=strict)
end

@testset "Conformance: discretize (gt-l3dg, manifest-driven)" begin
    @test isfile(_DISC_MANIFEST)

    manifest = JSON3.read(read(_DISC_MANIFEST, String))
    @test manifest.category == "discretize"
    @test !isempty(manifest.fixtures)

    opts = get(manifest, :options, NamedTuple())

    for fixture in manifest.fixtures
        id          = String(fixture.id)
        input_path  = joinpath(_DISC_CONF_DIR, String(fixture.input))
        golden_path = joinpath(_DISC_CONF_DIR, String(fixture.golden))

        @testset "$(id)" begin
            @test isfile(input_path)

            # 1. Run discretize end-to-end.
            first_out = _run_discretize(input_path, opts)
            first_bytes = _canonical_json(first_out)

            # 2. Determinism: second call on same input → identical bytes.
            second_out = _run_discretize(input_path, opts)
            second_bytes = _canonical_json(second_out)
            @test first_bytes == second_bytes

            # 3. Compare vs committed golden (byte-identical).
            if _DISC_UPDATE_GOLD || !isfile(golden_path)
                mkpath(dirname(golden_path))
                open(golden_path, "w") do io
                    write(io, first_bytes)
                    write(io, "\n")
                end
                @info "Discretize golden written" id=id path=golden_path
                @test isfile(golden_path)
            else
                golden_bytes = rstrip(read(golden_path, String), '\n')
                @test first_bytes == golden_bytes
            end
        end
    end
end
