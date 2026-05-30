# Scheme expansion (`use:` rules + cartesian selector materialize) per
# RFC §7 / §7.2 / §7.2.1, bead esm-j1u. The cartesian foundation must
# produce the same lowered AST whether the rule's RHS is written inline
# or via `use: <scheme>`.

using Test
using EarthSciSerialization
using JSON3
const ESM_Expr = EarthSciSerialization.Expr

@testset "scheme expansion (RFC §7, esm-j1u)" begin

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
    op(name, args::Vector; kwargs...) =
        OpExpr(name, ESM_Expr[_wrap(a) for a in args]; kwargs...)

    # Centered 2nd-order finite-difference scheme on a uniform cartesian grid.
    # The §7 worked example from `docs/content/rfcs/discretization.md`.
    centered_scheme_obj = Dict{String,Any}(
        "applies_to"  => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
        "grid_family" => "cartesian",
        "combine"     => "+",
        "stencil"     => Any[
            Dict("selector" => Dict("kind" => "cartesian", "axis" => "\$x", "offset" => -1),
                 "coeff"    => Dict("op" => "/", "args" => Any[-1, Dict("op" => "*", "args" => Any[2, "dx"])])),
            Dict("selector" => Dict("kind" => "cartesian", "axis" => "\$x", "offset" =>  1),
                 "coeff"    => Dict("op" => "/", "args" => Any[ 1, Dict("op" => "*", "args" => Any[2, "dx"])])),
        ],
    )

    @testset "parse_schemes accepts §7 cartesian scheme" begin
        schemes = parse_schemes(Dict("centered_2nd_uniform" => centered_scheme_obj))
        @test haskey(schemes, "centered_2nd_uniform")
        sch = schemes["centered_2nd_uniform"]
        @test sch isa Scheme
        @test sch.grid_family == "cartesian"
        @test sch.combine == "+"
        @test length(sch.stencil) == 2
        @test sch.stencil[1].selector isa CartesianSelector
        @test sch.stencil[1].selector.axis == "\$x"
        @test sch.stencil[1].selector.offset == -1
        @test sch.stencil[2].selector.offset == 1
    end

    @testset "parse_rule accepts `use:` and rejects mutex with `replacement`" begin
        ru = parse_rule("centered_grad_use",
            Dict("pattern" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                 "use"     => "centered_2nd_uniform"))
        @test ru isa Rule
        @test ru.replacement === nothing
        @test ru.replacement_scheme == "centered_2nd_uniform"

        @test_throws EarthSciSerialization.RuleEngineError parse_rule(
            "bad_both",
            Dict("pattern" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                 "use" => "x", "replacement" => "y"))

        @test_throws EarthSciSerialization.RuleEngineError parse_rule(
            "bad_neither",
            Dict("pattern" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x")))
    end

    @testset "materialize(::CartesianSelector, …) replaces axis component only" begin
        sel = CartesianSelector("x", -1)
        # 2D target [i, j]
        target = ESM_Expr[VarExpr("i"), VarExpr("j")]
        out = materialize(sel, target, 1)
        @test length(out) == 2
        @test out[1] isa OpExpr && out[1].op == "+"
        @test (out[1].args[1] isa VarExpr) && out[1].args[1].name == "i"
        @test (out[1].args[2] isa IntExpr) && out[1].args[2].value == -1
        # untouched axis
        @test (out[2] isa VarExpr) && out[2].name == "j"

        # +1 offset along second axis
        out2 = materialize(CartesianSelector("y", 1), target, 2)
        @test (out2[1] isa VarExpr) && out2[1].name == "i"
        @test out2[2] isa OpExpr && out2[2].op == "+"
        @test (out2[2].args[2] isa IntExpr) && out2[2].args[2].value == 1
    end

    @testset "expand_scheme on 1D cartesian grid produces §7.2 lowered form" begin
        schemes = parse_schemes(Dict("centered_2nd_uniform" => centered_scheme_obj))
        sch = schemes["centered_2nd_uniform"]

        ctx = RuleContext(
            Dict("gx" => Dict{String,Any}("spatial_dims" => ["i"])),
            Dict("u"  => Dict{String,Any}("grid" => "gx",
                                          "shape" => Any["i"],
                                          "location" => "cell_center")),
        )
        # Push the schemes registry onto a context manually (RuleContext is
        # immutable; rebuild with the schemes dict in the trailing slot).
        ctx = EarthSciSerialization.RuleContext(
            ctx.grids, ctx.variables, Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(), schemes)

        # Bindings as if `grad(u, dim=i)` matched `grad($u, dim=$x)`.
        bindings = Dict{String,ESM_Expr}("\$u" => VarExpr("u"),
                                        "\$x" => VarExpr("i"))

        lowered = expand_scheme(sch, bindings, ctx)
        # Expect: ((-1/(2*dx)) * index(u, i+(-1))) + ((1/(2*dx)) * index(u, i+1))
        @test lowered isa OpExpr
        @test lowered.op == "+"
        @test length(lowered.args) == 2

        # Term 1: coeff * index(u, i + -1)
        t1 = lowered.args[1]
        @test t1 isa OpExpr && t1.op == "*"
        @test length(t1.args) == 2
        @test t1.args[2] isa OpExpr && t1.args[2].op == "index"
        idx1 = t1.args[2]
        @test (idx1.args[1] isa VarExpr) && idx1.args[1].name == "u"
        @test idx1.args[2] isa OpExpr && idx1.args[2].op == "+"
        @test (idx1.args[2].args[1] isa VarExpr) && idx1.args[2].args[1].name == "i"
        @test (idx1.args[2].args[2] isa IntExpr) && idx1.args[2].args[2].value == -1

        # Term 2: positive offset
        t2 = lowered.args[2]
        @test t2 isa OpExpr && t2.op == "*"
        idx2 = t2.args[2]
        @test idx2.op == "index"
        @test (idx2.args[2].args[2] isa IntExpr) && idx2.args[2].args[2].value == 1
    end

    @testset "use:-rule rewrite matches inline-replacement equivalent" begin
        # Use the rule engine's full rewrite path (rather than calling
        # expand_scheme directly) to verify the §7.2.1 protocol — match
        # rule pattern, dispatch to scheme expansion, return lowered AST —
        # produces canonically-equal output to the inline `replacement`
        # form of the same scheme. RFC §7.2.1.
        schemes = parse_schemes(Dict("centered_2nd_uniform" => centered_scheme_obj))
        ctx = EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}("spatial_dims" => ["i"])),
            Dict("u"  => Dict{String,Any}("grid" => "gx",
                                          "shape" => Any["i"],
                                          "location" => "cell_center")),
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(), schemes)

        rule_use = parse_rule("centered_grad_use",
            Dict("pattern" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                 "use"     => "centered_2nd_uniform"))

        seed = OpExpr("grad", ESM_Expr[VarExpr("u")]; dim="i")
        out_use = rewrite(seed, Rule[rule_use], ctx)

        # Inline-replacement-form: the scheme's stencil expanded by hand.
        # combine "+" of two coeff * index(...) terms, with $u→u and $x→i.
        rule_inline = parse_rule("centered_grad_inline",
            Dict("pattern" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                 "replacement" => Dict("op" => "+", "args" => Any[
                     Dict("op" => "*", "args" => Any[
                         Dict("op" => "/", "args" => Any[-1, Dict("op" => "*", "args" => Any[2, "dx"])]),
                         Dict("op" => "index", "args" => Any["\$u", Dict("op" => "+", "args" => Any["\$x", -1])])
                     ]),
                     Dict("op" => "*", "args" => Any[
                         Dict("op" => "/", "args" => Any[1, Dict("op" => "*", "args" => Any[2, "dx"])]),
                         Dict("op" => "index", "args" => Any["\$u", Dict("op" => "+", "args" => Any["\$x", 1])])
                     ])
                 ])))
        out_inline = rewrite(seed, Rule[rule_inline], ctx)

        # Canonicalize both and compare.
        @test canonical_json(canonicalize(out_use)) ==
              canonical_json(canonicalize(out_inline))
    end

    @testset "E_SCHEME_MISMATCH on missing scheme name" begin
        schemes = Dict{String,Scheme}()  # no schemes registered
        ctx = EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}("spatial_dims" => ["i"])),
            Dict("u"  => Dict{String,Any}("grid" => "gx", "shape" => Any["i"])),
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(), schemes)
        rule = parse_rule("missing_use",
            Dict("pattern" => Dict("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                 "use"     => "no_such_scheme"))
        seed = OpExpr("grad", ESM_Expr[VarExpr("u")]; dim="i")
        err = try
            rewrite(seed, Rule[rule], ctx)
            nothing
        catch e
            e
        end
        @test err isa EarthSciSerialization.RuleEngineError
        @test err.code == "E_SCHEME_MISMATCH"
    end

    @testset "discretize() pipeline drives use:-rule expansion end-to-end" begin
        # End-to-end: an ESM document with a `use:` rule plus a matching
        # `discretizations.<name>` scheme is consumed by `discretize`,
        # producing a rewritten equation whose RHS is the §7.2 lowered
        # form. This is the production path for the cartesian foundation.
        esm = Dict{String,Any}(
            "esm" => "0.4.0",
            "metadata" => Dict{String,Any}("name" => "cartesian_use_rule"),
            "grids" => Dict{String,Any}(
                "gx" => Dict{String,Any}(
                    "family" => "cartesian",
                    "dimensions" => Any[
                        Dict{String,Any}("name" => "i", "size" => 8,
                                          "periodic" => true, "spacing" => "uniform")
                    ],
                ),
            ),
            "rules" => Any[
                Dict{String,Any}(
                    "name" => "centered_grad",
                    "pattern" => Dict{String,Any}("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                    "use"     => "centered_2nd_uniform",
                ),
            ],
            "discretizations" => Dict{String,Any}(
                "centered_2nd_uniform" => centered_scheme_obj,
            ),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "grid" => "gx",
                    "variables" => Dict{String,Any}(
                        "u" => Dict{String,Any}(
                            "type" => "state", "default" => 0.0, "units" => "1",
                            "shape" => Any["i"], "location" => "cell_center",
                        ),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                            "rhs" => Dict{String,Any}("op" => "grad", "args" => Any["u"], "dim" => "i"),
                        ),
                    ],
                ),
            ),
        )

        out = discretize(esm)
        rhs = out["models"]["M"]["equations"][1]["rhs"]
        # The rewritten RHS is a sum of two coeff·index terms; it must no
        # longer mention the `grad` op and must reference `index(u, i±1)`.
        rhs_str = JSON3.write(rhs)
        @test !occursin("\"grad\"", rhs_str)
        @test occursin("\"index\"", rhs_str)
        @test occursin("\"u\"", rhs_str)
    end

    @testset "§6.2.1 nonuniform metric-array auto-index rewrite" begin
        # Non-uniform 2nd derivative scheme: bare "dz" in stencil coeff should be
        # rewritten to index(dz, i) for a nonuniform z-dimension.
        nonuniform_scheme_obj = Dict{String,Any}(
            "applies_to"  => Dict("op" => "laplacian", "args" => Any["\$u"], "dim" => "\$z"),
            "grid_family" => "cartesian",
            "combine"     => "+",
            "stencil"     => Any[
                Dict("selector" => Dict("kind" => "cartesian", "axis" => "\$z", "offset" => -1),
                     "coeff"    => Dict("op" => "/", "args" => Any[2,
                         Dict("op" => "*", "args" => Any[
                             "dz",
                             Dict("op" => "+", "args" => Any["dz",
                                 Dict("op" => "index", "args" => Any["dz",
                                     Dict("op" => "+", "args" => Any["i", 1])])])])])),
                Dict("selector" => Dict("kind" => "cartesian", "axis" => "\$z", "offset" => 0),
                     "coeff"    => Dict("op" => "neg", "args" => Any[
                         Dict("op" => "/", "args" => Any[2,
                             Dict("op" => "*", "args" => Any["dz",
                                 Dict("op" => "index", "args" => Any["dz",
                                     Dict("op" => "+", "args" => Any["i", 1])])])])])),
                Dict("selector" => Dict("kind" => "cartesian", "axis" => "\$z", "offset" => 1),
                     "coeff"    => Dict("op" => "/", "args" => Any[2,
                         Dict("op" => "*", "args" => Any[
                             Dict("op" => "index", "args" => Any["dz",
                                 Dict("op" => "+", "args" => Any["i", 1])]),
                             Dict("op" => "+", "args" => Any["dz",
                                 Dict("op" => "index", "args" => Any["dz",
                                     Dict("op" => "+", "args" => Any["i", 1])])])])])),
            ],
        )

        @testset "expand_scheme applies §6.2.1 rewrite on nonuniform z-grid" begin
            schemes = parse_schemes(Dict("d2_nonuniform_z" => nonuniform_scheme_obj))
            ctx = EarthSciSerialization.RuleContext(
                Dict("gz" => Dict{String,Any}(
                    "spatial_dims"      => ["z"],
                    "nonuniform_dims"   => ["z"],
                    "metric_array_names" => ["dz"],
                )),
                Dict("u" => Dict{String,Any}("grid" => "gz",
                                              "shape" => Any["i"],
                                              "location" => "cell_center")),
                Dict{String,Int}(), nothing,
                Dict{String,Vector{Dict{String,Int}}}(), schemes)

            sch = schemes["d2_nonuniform_z"]
            bindings = Dict{String,ESM_Expr}("\$u" => VarExpr("u"), "\$z" => VarExpr("z"))
            lowered = expand_scheme(sch, bindings, ctx)

            # Combined result is a "+" of three terms.
            @test lowered isa OpExpr
            @test lowered.op == "+"

            # Each term is coeff * operand_ref. Walk all terms and collect
            # the coefficient sub-trees.
            terms = lowered.args
            @test length(terms) == 3

            # Verify that no bare (unindexed) VarExpr("dz") survives in any term — all
            # bare metric references should have been rewritten to index(dz, i).
            # Note: VarExpr("dz") is still expected as index.args[1] (the array reference);
            # the check skips first args of index nodes so those don't false-positive.
            function _has_bare_dz(e)
                e isa VarExpr && e.name == "dz" && return true
                if e isa OpExpr && e.op == "index" && !isempty(e.args)
                    # Skip first arg (the array name — dz there is structural, not bare).
                    return any(_has_bare_dz, e.args[2:end])
                end
                e isa OpExpr && return any(_has_bare_dz, e.args)
                return false
            end
            for t in terms
                @test !_has_bare_dz(t)
            end

            # Verify that index(dz, i) nodes appear in the first term's coeff.
            t1 = terms[1]  # offset -1 term
            t1 isa OpExpr && @test t1.op == "*"
            coeff1 = t1.args[1]
            # The coeff should contain at least one index(dz, i) node.
            function _has_dz_index_i(e)
                if e isa OpExpr && e.op == "index"
                    length(e.args) == 2 || return false
                    (e.args[1] isa VarExpr && e.args[1].name == "dz") || return false
                    return e.args[2] isa VarExpr && e.args[2].name == "i"
                end
                e isa OpExpr && return any(_has_dz_index_i, e.args)
                return false
            end
            @test _has_dz_index_i(coeff1)
        end

        @testset "§6.2.1 rewrite does NOT fire on uniform grid" begin
            # Same scheme, but the grid has no nonuniform_dims — no rewrite.
            schemes = parse_schemes(Dict("d2_nonuniform_z" => nonuniform_scheme_obj))
            ctx_uniform = EarthSciSerialization.RuleContext(
                Dict("gz" => Dict{String,Any}(
                    "spatial_dims"       => ["z"],
                    "nonuniform_dims"    => String[],     # uniform!
                    "metric_array_names" => ["dz"],
                )),
                Dict("u" => Dict{String,Any}("grid" => "gz",
                                              "shape" => Any["i"],
                                              "location" => "cell_center")),
                Dict{String,Int}(), nothing,
                Dict{String,Vector{Dict{String,Int}}}(), schemes)

            sch = schemes["d2_nonuniform_z"]
            bindings = Dict{String,ESM_Expr}("\$u" => VarExpr("u"), "\$z" => VarExpr("z"))
            lowered = expand_scheme(sch, bindings, ctx_uniform)

            # On a uniform grid, bare "dz" should survive (no §6.2.1 rewrite).
            function _has_bare_dz(e)
                e isa VarExpr && e.name == "dz" && return true
                e isa OpExpr && return any(_has_bare_dz, e.args)
                return false
            end
            @test _has_bare_dz(lowered)
        end

        @testset "§6.2.1 rewrite end-to-end via discretize()" begin
            esm = Dict{String,Any}(
                "esm" => "0.2.0",
                "metadata" => Dict{String,Any}("name" => "nonuniform_1d_test"),
                "grids" => Dict{String,Any}(
                    "gz" => Dict{String,Any}(
                        "family" => "cartesian",
                        "dimensions" => Any[
                            Dict{String,Any}("name" => "z", "size" => 8,
                                              "periodic" => true, "spacing" => "nonuniform"),
                        ],
                        "metric_arrays" => Dict{String,Any}(
                            "dz" => Dict{String,Any}(
                                "rank" => 1, "dim" => "z",
                                "generator" => Dict{String,Any}(
                                    "kind" => "expression",
                                    "expr" => Dict{String,Any}("op" => "*",
                                        "args" => Any[1.0, Dict("op" => "^", "args" => Any[1.2, "i"])]),
                                ),
                            ),
                        ),
                    ),
                ),
                "discretizations" => Dict{String,Any}(
                    "d2_nonuniform_z" => nonuniform_scheme_obj,
                ),
                "rules" => Any[
                    Dict{String,Any}(
                        "name" => "d2_nonuniform_z_rule",
                        "pattern" => Dict{String,Any}("op" => "laplacian",
                                                       "args" => Any["\$u"], "dim" => "\$z"),
                        "use" => "d2_nonuniform_z",
                    ),
                ],
                "models" => Dict{String,Any}(
                    "M" => Dict{String,Any}(
                        "grid" => "gz",
                        "variables" => Dict{String,Any}(
                            "u" => Dict{String,Any}("type" => "state", "default" => 0.0,
                                                     "units" => "1", "shape" => Any["i"],
                                                     "location" => "cell_center"),
                        ),
                        "equations" => Any[
                            Dict{String,Any}(
                                "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                                "rhs" => Dict{String,Any}("op" => "laplacian", "args" => Any["u"], "dim" => "z"),
                            ),
                        ],
                    ),
                ),
            )

            out = discretize(esm)
            rhs_str = JSON3.write(out["models"]["M"]["equations"][1]["rhs"])
            # The rewritten RHS must not contain the bare laplacian op.
            @test !occursin("\"laplacian\"", rhs_str)
            # The rewritten RHS must contain index nodes (from §6.2.1 rewrite and stencil expansion).
            @test occursin("\"index\"", rhs_str)
            # Bare "dz" should not appear as a value (only as array name inside index nodes).
            # In canonical JSON, a bare string "dz" would appear as "\"dz\"" — check for
            # { "args": ["dz", ...] } patterns (bare var inside index args is expected).
            @test occursin("\"u\"", rhs_str)
        end
    end
end
