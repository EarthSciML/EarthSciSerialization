using Test
using EarthSciSerialization
const ESM_Expr = EarthSciSerialization.Expr

@testset "canonicalize per RFC §5.4" begin

    function _wrap(a)
        if a isa ESM_Expr
            return a
        elseif a isa AbstractFloat
            return NumExpr(Float64(a))
        elseif a isa Integer
            return IntExpr(Int64(a))
        elseif a isa AbstractString
            return VarExpr(String(a))
        end
        error("cannot wrap $(typeof(a))")
    end
    op(name, args::Vector) = OpExpr(name, ESM_Expr[_wrap(a) for a in args])

    @testset "§5.4.6 float format table" begin
        cases = [
            (1.0, "1.0"),
            (-3.0, "-3.0"),
            (0.0, "0.0"),
            (-0.0, "-0.0"),
            (2.5, "2.5"),
            (1e25, "1e25"),
            (5e-324, "5e-324"),
            (1e-7, "1e-7"),
        ]
        for (v, want) in cases
            @test format_canonical_float(v) == want
        end
        # 0.1 + 0.2 = 0.30000000000000004
        a, b = 0.1, 0.2
        @test format_canonical_float(a + b) == "0.30000000000000004"
    end

    @testset "integer emission" begin
        for (v, want) in [(1, "1"), (-42, "-42"), (0, "0")]
            @test canonical_json(IntExpr(v)) == want
        end
    end

    @testset "non-finite errors" begin
        for f in [NaN, Inf, -Inf]
            @test_throws CanonicalizeError canonicalize(NumExpr(f))
        end
    end

    @testset "§5.4.8 worked example" begin
        e = op("+", Any[
            op("*", Any["a", 0]),
            "b",
            op("+", Any["a", 1]),
        ])
        @test canonical_json(e) == "{\"args\":[1,\"a\",\"b\"],\"op\":\"+\"}"
    end

    @testset "flatten basic" begin
        e = op("+", Any[op("+", Any["a", "b"]), "c"])
        @test canonical_json(e) == "{\"args\":[\"a\",\"b\",\"c\"],\"op\":\"+\"}"
    end

    @testset "type-preserving identity elim" begin
        # *(1, x) -> "x"
        @test canonical_json(op("*", Any[1, "x"])) == "\"x\""
        # *(1.0, x) keeps the 1.0
        @test canonical_json(op("*", Any[1.0, "x"])) == "{\"args\":[1.0,\"x\"],\"op\":\"*\"}"
    end

    @testset "zero annihilation type-preserving" begin
        @test canonical_json(op("*", Any[0, "x"])) == "0"
        @test canonical_json(op("*", Any[0.0, "x"])) == "0.0"
        @test canonical_json(op("*", Any[-0.0, "x"])) == "-0.0"
    end

    @testset "int/float disambiguation" begin
        a = op("+", Any[1.0, 2.5])
        b = op("+", Any[1, 2.5])
        ja = canonical_json(a)
        jb = canonical_json(b)
        @test ja != jb
        @test occursin("1.0", ja)
    end

    @testset "neg canonical" begin
        @test canonical_json(op("neg", Any[op("neg", Any["x"])])) == "\"x\""
        @test canonical_json(op("neg", Any[5])) == "-5"
        @test canonical_json(op("-", Any[0, "x"])) == "{\"args\":[\"x\"],\"op\":\"neg\"}"
    end

    @testset "div 0/0" begin
        @test_throws CanonicalizeError canonicalize(op("/", Any[0, 0]))
    end

    @testset "cross-binding conformance fixtures" begin
        # tests/conformance/canonical/*.json — same fixtures every binding runs.
        using JSON3
        repo_root = abspath(joinpath(@__DIR__, "..", "..", ".."))
        dir = joinpath(repo_root, "tests", "conformance", "canonical")
        manifest = JSON3.read(read(joinpath(dir, "manifest.json"), String))
        fixtures = manifest.fixtures
        @test !isempty(fixtures)

        function wire_to_expr(node)
            if node isa AbstractDict || (node isa JSON3.Object)
                if haskey(node, :op) && haskey(node, :args)
                    args = ESM_Expr[wire_to_expr(a) for a in node[:args]]
                    return OpExpr(String(node[:op]), args)
                end
            end
            if node isa Integer
                return IntExpr(Int64(node))
            elseif node isa AbstractFloat
                return NumExpr(Float64(node))
            elseif node isa AbstractString
                return VarExpr(String(node))
            end
            error("unknown wire form: $(typeof(node))")
        end

        for f in fixtures
            id = String(f[:id])
            path = joinpath(dir, String(f[:path]))
            fixture = JSON3.read(read(path, String))
            expr = wire_to_expr(fixture[:input])
            got = canonical_json(expr)
            want = String(fixture[:expected])
            @test got == want
        end
    end
end
