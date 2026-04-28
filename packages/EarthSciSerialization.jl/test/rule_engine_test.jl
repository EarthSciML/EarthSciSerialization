using Test
using EarthSciSerialization
using JSON3
const ESM_Expr = EarthSciSerialization.Expr

@testset "rule engine per RFC §5.2" begin

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

    @testset "simple match + replace" begin
        # Rule: +($a, 0) -> $a
        pat = op("+", Any[VarExpr("\$a"), 0])
        repl = VarExpr("\$a")
        rule = Rule("add_zero", pat, repl)
        seed = op("+", Any["x", 0])
        out = rewrite(seed, Rule[rule])
        @test canonical_json(out) == "\"x\""
    end

    @testset "non-linear pattern (§5.2.2)" begin
        # Rule: -($a, $a) -> 0
        pat = op("-", Any[VarExpr("\$a"), VarExpr("\$a")])
        repl = IntExpr(0)
        rule = Rule("self_minus", pat, repl)

        # Match: a - a
        m1 = match_pattern(pat, op("-", Any["x", "x"]))
        @test m1 !== nothing
        @test haskey(m1, "\$a")

        # No match: a - b
        m2 = match_pattern(pat, op("-", Any["x", "y"]))
        @test m2 === nothing
    end

    @testset "sibling-field pattern vars (name class)" begin
        # Rule: D($u, wrt=$x) -> index($u, $x)
        pat = OpExpr("D", ESM_Expr[VarExpr("\$u")]; wrt="\$x")
        repl = OpExpr("index", ESM_Expr[VarExpr("\$u"), VarExpr("\$x")])
        rule = Rule("deriv_index", pat, repl)

        seed = OpExpr("D", ESM_Expr[VarExpr("T")]; wrt="t")
        out = rewrite(seed, Rule[rule])
        @test out isa OpExpr
        @test out.op == "index"
        @test length(out.args) == 2
        @test (out.args[1] isa VarExpr) && out.args[1].name == "T"
        @test (out.args[2] isa VarExpr) && out.args[2].name == "t"
    end

    @testset "top-down seal after rewrite (§5.2.5)" begin
        # Rule: $a + $a -> 2*$a
        pat = op("+", Any[VarExpr("\$a"), VarExpr("\$a")])
        repl = op("*", Any[2, VarExpr("\$a")])
        rule = Rule("double", pat, repl)

        # Input: ((x + x) + (x + x))
        inner = op("+", Any["x", "x"])
        seed = OpExpr("+", ESM_Expr[inner, inner])

        # Pass 1: root matches ($a := (x+x)). Replacement is 2 * (x+x).
        # Seal: do not descend.
        # Pass 2: root is 2 * (x+x). No match at root; descend. The (x+x)
        # subtree matches; rewrite to 2*x.
        # Pass 3: tree stable.
        out = rewrite(seed, Rule[rule])
        @test canonical_json(out) == canonical_json(
            op("*", Any[2, op("*", Any[2, "x"])]))
    end

    @testset "fixed-point: repeated reductions" begin
        # Rule: +($a, 0) -> $a
        rule = Rule("add_zero",
            op("+", Any[VarExpr("\$a"), 0]),
            VarExpr("\$a"))
        # ((x + 0) + 0) -- needs 2 passes
        seed = op("+", Any[op("+", Any["x", 0]), 0])
        out = rewrite(seed, Rule[rule])
        @test canonical_json(out) == "\"x\""
    end

    @testset "E_RULES_NOT_CONVERGED" begin
        # Rule: $a -> +($a, 0)  (each pass rewrites root once then seals;
        # next pass walks the new root and rewrites again forever).
        # With max_passes=3 this must abort.
        pat = VarExpr("\$a")
        repl = op("+", Any[VarExpr("\$a"), 0])
        rule = Rule("explode", pat, repl)
        @test_throws RuleEngineError rewrite(VarExpr("x"), Rule[rule];
                                             max_passes=3)
        # Confirm error code.
        caught = nothing
        try
            rewrite(VarExpr("x"), Rule[rule]; max_passes=3)
        catch e
            caught = e
        end
        @test caught isa RuleEngineError
        @test caught.code == "E_RULES_NOT_CONVERGED"
    end

    @testset "guards: var_has_grid" begin
        pat = op("grad", Any[VarExpr("\$u")])
        # name-class grad.dim pattern variable
        pat = OpExpr("grad", ESM_Expr[VarExpr("\$u")]; dim="\$x")
        repl = VarExpr("\$u")
        guards = [Guard("var_has_grid",
                        Dict{String,Any}("pvar" => "\$u", "grid" => "g1"))]
        rule = Rule("drop_grad", pat, guards, repl, nothing)

        ctx_match = RuleContext(
            Dict{String,Dict{String,Any}}(
                "g1" => Dict{String,Any}("spatial_dims" => ["x"])),
            Dict{String,Dict{String,Any}}(
                "T" => Dict{String,Any}("grid" => "g1")))
        out = rewrite(OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x"),
                      Rule[rule], ctx_match)
        @test out isa VarExpr && out.name == "T"

        # With a variable on the wrong grid, no rewrite.
        ctx_nomatch = RuleContext(
            Dict{String,Dict{String,Any}}(
                "g1" => Dict{String,Any}("spatial_dims" => ["x"])),
            Dict{String,Dict{String,Any}}(
                "T" => Dict{String,Any}("grid" => "g2")))
        out2 = rewrite(OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x"),
                       Rule[rule], ctx_nomatch)
        @test out2 isa OpExpr && out2.op == "grad"
    end

    @testset "guards: dim_is_periodic via bound grid pvar" begin
        # Pattern binds $g via var_has_grid, then dim_is_periodic consumes it.
        pat = op("grad", Any[VarExpr("\$u")])
        pat = OpExpr("grad", ESM_Expr[VarExpr("\$u")]; dim="\$x")
        repl = op("index", Any[VarExpr("\$u"), VarExpr("\$x")])
        guards = [
            Guard("var_has_grid",
                  Dict{String,Any}("pvar" => "\$u", "grid" => "\$g")),
            Guard("dim_is_periodic",
                  Dict{String,Any}("pvar" => "\$x", "grid" => "\$g")),
        ]
        rule = Rule("p_wrap", pat, guards, repl, nothing)
        ctx = RuleContext(
            Dict{String,Dict{String,Any}}(
                "g1" => Dict{String,Any}(
                    "spatial_dims" => ["x"],
                    "periodic_dims" => ["x"])),
            Dict{String,Dict{String,Any}}(
                "T" => Dict{String,Any}("grid" => "g1")))
        out = rewrite(OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x"),
                      Rule[rule], ctx)
        @test out isa OpExpr && out.op == "index"
    end

    @testset "parse_rules from JSON" begin
        json = """
        {
          "drop_zero": {
            "pattern":     {"op": "+", "args": ["\$a", 0]},
            "replacement": "\$a"
          },
          "self_mul_zero": {
            "pattern":     {"op": "*", "args": ["\$a", 0]},
            "replacement": 0
          }
        }
        """
        obj = JSON3.read(json)
        rules = parse_rules(obj)
        @test length(rules) == 2
        @test rules[1].name == "drop_zero"
        @test rules[2].name == "self_mul_zero"

        # Array form preserves order explicitly.
        json_arr = """
        [
          {"name": "a_first",  "pattern": {"op": "*", "args": ["\$a", 0]}, "replacement": 0},
          {"name": "b_second", "pattern": {"op": "+", "args": ["\$a", 0]}, "replacement": "\$a"}
        ]
        """
        obj2 = JSON3.read(json_arr)
        rules2 = parse_rules(obj2)
        @test [r.name for r in rules2] == ["a_first", "b_second"]
    end

    @testset "E_UNREWRITTEN_PDE_OP" begin
        # grad() remains — should error.
        expr = OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x")
        @test_throws RuleEngineError check_unrewritten_pde_ops(expr)

        # After rewriting to index(), check passes.
        expr2 = op("index", Any["T", "x"])
        @test check_unrewritten_pde_ops(expr2) === nothing
    end

    @testset "boundary_policy + ghost_width (RFC §5.2.8 / §7, esm-bet)" begin
        @testset "string-form boundary_policy: new closed-set kinds" begin
            for kind in ("periodic", "reflecting", "one_sided_extrapolation",
                         "prescribed", "ghosted", "neumann_zero", "extrapolate")
                json = """
                {"name": "r", "pattern": "\$a", "replacement": "\$a",
                 "boundary_policy": "$kind"}
                """
                obj = JSON3.read(json)
                rules = parse_rules([obj])
                @test rules[1].boundary_policy == kind
            end
        end

        @testset "string-form boundary_policy rejects unknown" begin
            json = """{"name": "r", "pattern": "\$a", "replacement": "\$a",
                       "boundary_policy": "nope"}"""
            obj = JSON3.read(json)
            @test_throws RuleEngineError parse_rules([obj])
        end

        @testset "string-form rejects panel_dispatch (object-form-only)" begin
            json = """{"name": "r", "pattern": "\$a", "replacement": "\$a",
                       "boundary_policy": "panel_dispatch"}"""
            obj = JSON3.read(json)
            @test_throws RuleEngineError parse_rules([obj])
        end

        @testset "per-axis boundary_policy with panel_dispatch" begin
            json = """
            {"name": "ppm", "pattern": "\$a", "replacement": "\$a",
             "boundary_policy": {"by_axis": {
               "xi":  {"kind": "panel_dispatch", "interior": "dist_xi",  "boundary": "dist_xi_bnd"},
               "eta": {"kind": "panel_dispatch", "interior": "dist_eta", "boundary": "dist_eta_bnd"}
             }}}
            """
            obj = JSON3.read(json)
            rules = parse_rules([obj])
            bp = rules[1].boundary_policy
            @test bp isa Dict
            @test bp["xi"].kind == "panel_dispatch"
            @test bp["xi"].interior == "dist_xi"
            @test bp["xi"].boundary == "dist_xi_bnd"
            @test bp["eta"].kind == "panel_dispatch"
        end

        @testset "per-axis one_sided_extrapolation with degree" begin
            json = """
            {"name": "r", "pattern": "\$a", "replacement": "\$a",
             "boundary_policy": {"by_axis": {
               "x": {"kind": "one_sided_extrapolation", "degree": 2}
             }}}
            """
            obj = JSON3.read(json)
            rules = parse_rules([obj])
            spec = rules[1].boundary_policy["x"]
            @test spec.kind == "one_sided_extrapolation"
            @test spec.degree == 2
        end

        @testset "panel_dispatch requires interior + boundary" begin
            json = """
            {"name": "r", "pattern": "\$a", "replacement": "\$a",
             "boundary_policy": {"by_axis": {"xi": {"kind": "panel_dispatch"}}}}
            """
            obj = JSON3.read(json)
            @test_throws RuleEngineError parse_rules([obj])
        end

        @testset "rejects out-of-range degree" begin
            json = """
            {"name": "r", "pattern": "\$a", "replacement": "\$a",
             "boundary_policy": {"by_axis": {
               "x": {"kind": "one_sided_extrapolation", "degree": 5}
             }}}
            """
            obj = JSON3.read(json)
            @test_throws RuleEngineError parse_rules([obj])
        end

        @testset "ghost_width scalar form" begin
            json = """{"name": "r", "pattern": "\$a", "replacement": "\$a",
                       "ghost_width": 3}"""
            obj = JSON3.read(json)
            rules = parse_rules([obj])
            @test rules[1].ghost_width == 3
        end

        @testset "ghost_width per-axis form" begin
            json = """
            {"name": "r", "pattern": "\$a", "replacement": "\$a",
             "ghost_width": {"by_axis": {"xi": 3, "eta": 2}}}
            """
            obj = JSON3.read(json)
            rules = parse_rules([obj])
            gw = rules[1].ghost_width
            @test gw isa Dict
            @test gw["xi"] == 3
            @test gw["eta"] == 2
        end

        @testset "ghost_width rejects negative" begin
            json = """{"name": "r", "pattern": "\$a", "replacement": "\$a",
                       "ghost_width": -1}"""
            obj = JSON3.read(json)
            @test_throws RuleEngineError parse_rules([obj])
        end

        @testset "ghost_width rejects string" begin
            json = """{"name": "r", "pattern": "\$a", "replacement": "\$a",
                       "ghost_width": "3"}"""
            obj = JSON3.read(json)
            @test_throws RuleEngineError parse_rules([obj])
        end
    end

end
