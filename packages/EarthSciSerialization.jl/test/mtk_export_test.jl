using Test
using EarthSciSerialization
using JSON3
import ModelingToolkit
import Symbolics
import Catalyst
import OrdinaryDiffEqTsit5

const ESM = EarthSciSerialization
const MTK = ModelingToolkit

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

"""
Construct a 3-equation toy ODESystem via MTK macros (analogous to what a
per-model migration would touch). Returns the parent system.
"""
function _toy_ode_system(name::Symbol=:ToyDecay)
    MTK.@variables t x(t) y(t) z(t)
    MTK.@parameters k1 k2 k3
    D = MTK.Differential(t)
    eqs = [D(x) ~ -k1 * x,
           D(y) ~ k1 * x - k2 * y,
           D(z) ~ k2 * y - k3 * z]
    defaults = Dict(x => 1.0, y => 0.0, z => 0.0,
                    k1 => 0.5, k2 => 0.3, k3 => 0.1)
    return MTK.System(eqs, t; name=name, defaults=defaults)
end

function _toy_catalyst_system(name::Symbol=:ToyReactions)
    Catalyst.@variables t
    Catalyst.@species A(t) B(t)
    Catalyst.@parameters k1 k2
    rxs = [Catalyst.Reaction(k1, [A], [B]),
           Catalyst.Reaction(k2, [B], [A])]
    return Catalyst.ReactionSystem(rxs, t; name=name)
end

# ---------------------------------------------------------------------
# mtk2esm — ODESystem branch
# ---------------------------------------------------------------------

@testset "mtk2esm: basic ODESystem export" begin
    sys = _toy_ode_system()
    out = mtk2esm(sys)

    @test out isa Dict
    @test out["esm"] == "0.1.0"
    @test haskey(out, "metadata")
    @test haskey(out, "models")
    @test haskey(out["models"], "ToyDecay")

    model_dict = out["models"]["ToyDecay"]
    @test haskey(model_dict, "variables")
    @test haskey(model_dict, "equations")

    vars = model_dict["variables"]
    @test haskey(vars, "x")
    @test haskey(vars, "y")
    @test haskey(vars, "z")
    @test haskey(vars, "k1")
    @test haskey(vars, "k2")
    @test haskey(vars, "k3")

    @test vars["x"]["type"] == "state"
    @test vars["k1"]["type"] == "parameter"
    @test vars["x"]["default"] == 1.0
    @test vars["k1"]["default"] == 0.5

    @test length(model_dict["equations"]) == 3

    @test model_dict["version"] == "0.1.0"
    @test model_dict["tests"] == []
    @test model_dict["examples"] == []
end

@testset "mtk2esm: metadata kwargs pass through" begin
    sys = _toy_ode_system(:Tagged)
    out = mtk2esm(sys; metadata=(;
        description="toy decay chain",
        tags=["migration", "toy"],
        source_ref="earthsciml/UnitTests.jl@abc123",
        authors=["migrator"],
        version="0.2.0",
    ))

    @test out["metadata"]["name"] == "Tagged"
    @test out["metadata"]["description"] == "toy decay chain"
    @test out["metadata"]["authors"] == ["migrator"]
    @test out["metadata"]["tags"] == ["migration", "toy"]

    m = out["models"]["Tagged"]
    @test m["version"] == "0.2.0"
    @test m["description"] == "toy decay chain"
    @test m["metadata"]["tags"] == ["migration", "toy"]
    @test m["metadata"]["source_ref"] == "earthsciml/UnitTests.jl@abc123"
end

@testset "mtk2esm: JSON-serializable output" begin
    sys = _toy_ode_system()
    out = mtk2esm(sys)
    # Must round-trip through JSON without errors
    s = JSON3.write(out)
    parsed = JSON3.read(s)
    @test parsed["esm"] == "0.1.0"
    @test haskey(parsed["models"], "ToyDecay")
end

# ---------------------------------------------------------------------
# mtk2esm — Catalyst.ReactionSystem branch
# ---------------------------------------------------------------------

@testset "mtk2esm: Catalyst ReactionSystem export" begin
    rs = _toy_catalyst_system()
    out = mtk2esm(rs)

    @test out["esm"] == "0.1.0"
    @test haskey(out, "reaction_systems")
    @test haskey(out["reaction_systems"], "ToyReactions")

    rs_dict = out["reaction_systems"]["ToyReactions"]
    @test haskey(rs_dict, "species")
    @test haskey(rs_dict, "reactions")
    @test length(rs_dict["reactions"]) == 2

    # Species are serialized as a map keyed by name
    species_map = rs_dict["species"]
    @test species_map isa Dict || species_map isa AbstractDict
    @test haskey(species_map, "A")
    @test haskey(species_map, "B")
end

# ---------------------------------------------------------------------
# Gap detection — non-standard op triggers TODO_GAP note
# ---------------------------------------------------------------------

@testset "mtk2esm: TODO_GAP for non-standard operator" begin
    MTK.@variables t u(t)
    MTK.@parameters p
    D = MTK.Differential(t)
    # @register_symbolic creates a registered function whose call
    # survives symbolic manipulation. We synthesize one on the fly.
    @eval foo_registered(x) = x^2 + 1
    Symbolics.@register_symbolic foo_registered(x)

    eqs = [D(u) ~ foo_registered(u) + p]
    sys = MTK.System(eqs, t; name=:GapSys, defaults=Dict(u => 1.0, p => 0.5))

    # The @warn is expected — capture it to keep the test log quiet
    out = @test_logs (:warn, r"schema-gap construct") match_mode=:any mtk2esm(sys)

    model_dict = out["models"]["GapSys"]
    @test haskey(model_dict, "metadata")
    notes = get(model_dict["metadata"], "notes", [])
    @test any(occursin("TODO_GAP", String(n)) for n in notes)
    @test any(occursin("gt-p3ep", String(n)) for n in notes)
end

# ---------------------------------------------------------------------
# Round-trip smoke test — no simulation, just syntactic
# ---------------------------------------------------------------------

@testset "mtk2esm: syntactic round-trip through load/save" begin
    sys = _toy_ode_system(:RoundTrip)
    out = mtk2esm(sys)

    tmpfile = tempname() * ".esm"
    try
        open(tmpfile, "w") do io
            write(io, JSON3.write(out; indent=2))
        end

        reloaded = ESM.load(tmpfile)
        @test reloaded isa ESM.EsmFile
        @test reloaded.esm == "0.1.0"
        @test reloaded.models !== nothing
        @test haskey(reloaded.models, "RoundTrip")

        # The loaded Model must be buildable back into an MTK System.
        rt_sys = MTK.System(reloaded.models["RoundTrip"]; name=:RoundTripBack)
        @test rt_sys isa MTK.AbstractSystem

        simp = MTK.mtkcompile(rt_sys)
        @test length(MTK.unknowns(simp)) >= 3
    finally
        isfile(tmpfile) && rm(tmpfile)
    end
end

# ---------------------------------------------------------------------
# Full numerical round-trip — simulate original + round-tripped, compare
# ---------------------------------------------------------------------

@testset "mtk2esm: numerical round-trip (toy ODE)" begin
    sys = _toy_ode_system(:NumRT)
    out = mtk2esm(sys)

    tmpfile = tempname() * ".esm"
    try
        open(tmpfile, "w") do io
            write(io, JSON3.write(out; indent=2))
        end
        reloaded = ESM.load(tmpfile)
        rt_sys = MTK.System(reloaded.models["NumRT"]; name=:NumRTBack)

        # Simulate original
        simp_a = MTK.mtkcompile(sys)
        prob_a = MTK.ODEProblem(simp_a, Dict{Any,Any}(), (0.0, 5.0))
        sol_a = OrdinaryDiffEqTsit5.solve(prob_a, OrdinaryDiffEqTsit5.Tsit5();
            reltol=1e-10, abstol=1e-12)

        # Simulate round-tripped
        simp_b = MTK.mtkcompile(rt_sys)
        prob_b = MTK.ODEProblem(simp_b, Dict{Any,Any}(), (0.0, 5.0))
        sol_b = OrdinaryDiffEqTsit5.solve(prob_b, OrdinaryDiffEqTsit5.Tsit5();
            reltol=1e-10, abstol=1e-12)

        # Compare x, y, z at a few time points. Match unknowns by suffix.
        for state in ("x", "y", "z")
            u_a = nothing
            u_b = nothing
            for u in MTK.unknowns(simp_a)
                nm = string(MTK.getname(u))
                if endswith(nm, "_" * state) || nm == state
                    u_a = u; break
                end
            end
            for u in MTK.unknowns(simp_b)
                nm = string(MTK.getname(u))
                if endswith(nm, "_" * state) || nm == state
                    u_b = u; break
                end
            end
            @test u_a !== nothing
            @test u_b !== nothing
            for t in (0.0, 1.0, 2.5, 5.0)
                @test isapprox(sol_a(t, idxs=u_a), sol_b(t, idxs=u_b);
                               atol=1e-6, rtol=1e-6)
            end
        end
    finally
        isfile(tmpfile) && rm(tmpfile)
    end
end

# ---------------------------------------------------------------------
# mtk2esm_gaps quick pre-flight
# ---------------------------------------------------------------------

@testset "mtk2esm_gaps pre-flight on gap-free system" begin
    sys = _toy_ode_system(:Clean)
    gaps = mtk2esm_gaps(sys)
    @test gaps isa Vector{GapReport}
    @test isempty(gaps)  # no brownians declared
end
