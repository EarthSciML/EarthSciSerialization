# Tests for parse-time expansion of `expression_templates` (RFC v2 §4, esm-giy).

using Test
using JSON3
using EarthSciSerialization

const _ET_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))
const _ET_FIXTURE = joinpath(_ET_REPO_ROOT, "tests", "valid", "expression_templates_arrhenius.esm")

# OpExpr / IntExpr / NumExpr / VarExpr fall back to identity-equality
# for `==`. Walk the tree structurally so test failures show shape
# differences rather than identity mismatches.
function _expr_equal(a, b)
    typeof(a) == typeof(b) || return false
    if a isa EarthSciSerialization.OpExpr
        return a.op == b.op &&
               length(a.args) == length(b.args) &&
               all(_expr_equal(x, y) for (x, y) in zip(a.args, b.args))
    elseif a isa EarthSciSerialization.IntExpr || a isa EarthSciSerialization.NumExpr
        return a.value == b.value
    elseif a isa EarthSciSerialization.VarExpr
        return a.name == b.name
    else
        return a == b
    end
end

function _arrhenius_inline(a_pre::Real, ea::Real)
    EarthSciSerialization.OpExpr(
        "*",
        [
            EarthSciSerialization.NumExpr(Float64(a_pre)),
            EarthSciSerialization.OpExpr(
                "exp",
                [EarthSciSerialization.OpExpr(
                    "/",
                    [EarthSciSerialization.OpExpr(
                        "-",
                        [EarthSciSerialization.IntExpr(Int64(ea))],
                    ),
                     EarthSciSerialization.VarExpr("T")],
                )],
            ),
            EarthSciSerialization.VarExpr("num_density"),
        ],
    )
end

@testset "expression_templates parse-time expansion" begin
    @testset "fixture loads with rates expanded" begin
        esm = EarthSciSerialization.load(_ET_FIXTURE)
        rs = esm.reaction_systems["ToyArrhenius"]
        @test length(rs.reactions) == 3
        cases = [
            ("R1", 1.8e-12, 1500),
            ("R2", 3.0e-13, 460),
            ("R3", 4.5e-14, 920),
        ]
        for (rid, a_pre, ea) in cases
            r = first(filter(r -> r.id == rid, rs.reactions))
            expected = _arrhenius_inline(a_pre, ea)
            @test _expr_equal(r.rate, expected)
        end
    end

    @testset "rejects pre-0.4.0 with apply_expression_template" begin
        raw = JSON3.read(read(_ET_FIXTURE, String))
        d = EarthSciSerialization._to_native_json(raw)::Dict{String,Any}
        d["esm"] = "0.3.0"
        @test_throws EarthSciSerialization.ParseError EarthSciSerialization.expand_expression_templates!(d)
    end

    @testset "rejects unknown template name" begin
        raw = JSON3.read(read(_ET_FIXTURE, String))
        d = EarthSciSerialization._to_native_json(raw)::Dict{String,Any}
        d["reaction_systems"]["ToyArrhenius"]["reactions"][1]["rate"] = Dict{String,Any}(
            "op" => "apply_expression_template",
            "args" => Any[],
            "name" => "no_such_template",
            "bindings" => Dict{String,Any}("A_pre" => 1.0, "Ea" => 1.0),
        )
        @test_throws EarthSciSerialization.ParseError EarthSciSerialization.expand_expression_templates!(d)
    end

    @testset "rejects missing binding" begin
        raw = JSON3.read(read(_ET_FIXTURE, String))
        d = EarthSciSerialization._to_native_json(raw)::Dict{String,Any}
        d["reaction_systems"]["ToyArrhenius"]["reactions"][1]["rate"] = Dict{String,Any}(
            "op" => "apply_expression_template",
            "args" => Any[],
            "name" => "arrhenius",
            "bindings" => Dict{String,Any}("A_pre" => 1.0),
        )
        @test_throws EarthSciSerialization.ParseError EarthSciSerialization.expand_expression_templates!(d)
    end

    @testset "rejects extra binding" begin
        raw = JSON3.read(read(_ET_FIXTURE, String))
        d = EarthSciSerialization._to_native_json(raw)::Dict{String,Any}
        d["reaction_systems"]["ToyArrhenius"]["reactions"][1]["rate"] = Dict{String,Any}(
            "op" => "apply_expression_template",
            "args" => Any[],
            "name" => "arrhenius",
            "bindings" => Dict{String,Any}("A_pre" => 1.0, "Ea" => 1.0, "Junk" => 2.0),
        )
        @test_throws EarthSciSerialization.ParseError EarthSciSerialization.expand_expression_templates!(d)
    end

    @testset "expansion is deterministic across two loads" begin
        esm1 = EarthSciSerialization.load(_ET_FIXTURE)
        esm2 = EarthSciSerialization.load(_ET_FIXTURE)
        rs1 = esm1.reaction_systems["ToyArrhenius"].reactions
        rs2 = esm2.reaction_systems["ToyArrhenius"].reactions
        @test length(rs1) == length(rs2)
        for i in eachindex(rs1)
            @test _expr_equal(rs1[i].rate, rs2[i].rate)
        end
    end
end
