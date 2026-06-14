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

# ============================================================================
# §7.9 Multi-output stencil scheme — parse + loader validation (ess-494)
# ============================================================================

@testset "multi_output_stencil parse + loader validation (RFC §7.9, ess-494)" begin

    # Helper: build a minimal multi-output stencil raw object with two outputs.
    function _ppm_raw(; outputs=["q_left", "q_right"],
                        stencil_keys=["q_left", "q_right"],
                        primary=nothing,
                        extra_outputs=String[])
        stencil = Dict{String,Any}()
        for k in stencil_keys
            stencil[k] = Any[
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                     "coeff" => 0.5)
            ]
        end
        obj = Dict{String,Any}(
            "kind"       => "multi_output_stencil",
            "applies_to" => Dict("op" => "reconstruct", "args" => Any["\$q"], "dim" => "\$x"),
            "grid_family"=> "cartesian",
            "outputs"    => vcat(outputs, extra_outputs),
            "stencil"    => stencil,
        )
        if primary !== nothing
            obj["primary"] = primary
        end
        return obj
    end

    @testset "valid parse: two-output stencil" begin
        raw = _ppm_raw()
        sch = parse_multi_output_stencil_scheme("ppm", raw)
        @test sch isa MultiOutputStencilScheme
        @test sch.name == "ppm"
        @test sch.outputs == ["q_left", "q_right"]
        @test haskey(sch.stencil, "q_left")
        @test haskey(sch.stencil, "q_right")
        @test length(sch.stencil["q_left"]) == 1
        @test sch.primary === nothing
        @test sch.emits_location === nothing
    end

    @testset "valid parse: primary names a declared output" begin
        raw = _ppm_raw(primary="q_left")
        sch = parse_multi_output_stencil_scheme("ppm", raw)
        @test sch.primary == "q_left"
    end

    @testset "valid parse: parse_schemes dispatches multi_output_stencil" begin
        schemes = parse_schemes(Dict("ppm" => _ppm_raw()))
        @test haskey(schemes, "ppm")
        @test schemes["ppm"] isa MultiOutputStencilScheme
    end

    @testset "E_OUTPUTS_STENCIL_MISMATCH: outputs ≠ stencil keys" begin
        raw = _ppm_raw(outputs=["q_left", "q_right"],
                       stencil_keys=["q_left"])           # missing q_right in stencil
        ex = @test_throws EarthSciSerialization.RuleEngineError begin
            parse_multi_output_stencil_scheme("ppm", raw)
        end
        @test ex.value.code == "E_OUTPUTS_STENCIL_MISMATCH"
    end

    @testset "E_OUTPUTS_STENCIL_MISMATCH: extra stencil key not in outputs" begin
        raw = _ppm_raw(outputs=["q_left"],
                       stencil_keys=["q_left", "q_right"])  # q_right not in outputs
        ex = @test_throws EarthSciSerialization.RuleEngineError begin
            parse_multi_output_stencil_scheme("ppm", raw)
        end
        @test ex.value.code == "E_OUTPUTS_STENCIL_MISMATCH"
    end

    @testset "E_PRIMARY_NOT_AN_OUTPUT: primary not in declared outputs" begin
        raw = _ppm_raw(primary="q_center")   # q_center is not declared
        ex = @test_throws EarthSciSerialization.RuleEngineError begin
            parse_multi_output_stencil_scheme("ppm", raw)
        end
        @test ex.value.code == "E_PRIMARY_NOT_AN_OUTPUT"
    end

    @testset "E_PROVIDER_NAME_CLASH: duplicate output names" begin
        raw = _ppm_raw(outputs=["q_left", "q_left"],  # duplicate
                       stencil_keys=["q_left"])
        ex = @test_throws EarthSciSerialization.RuleEngineError begin
            parse_multi_output_stencil_scheme("ppm", raw)
        end
        @test ex.value.code == "E_PROVIDER_NAME_CLASH"
    end

    @testset "valid consumer requires: resolves to sibling multi_output_stencil" begin
        provider_raw = _ppm_raw()
        consumer_raw = Dict{String,Any}(
            "applies_to"  => Dict("op"=>"flux","args"=>Any["\$q","\$c"],"dim"=>"\$x"),
            "grid_family" => "cartesian",
            "stencil"     => Any[
                Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                     "coeff"=>Dict("op"=>"*","args"=>Any["\$c","q_left"]))
            ],
            "requires"    => Dict("q_left" => "ppm#q_left",
                                  "q_right" => "ppm#q_right"),
        )
        schemes = parse_schemes(Dict("ppm" => provider_raw, "flux" => consumer_raw))
        @test schemes["flux"] isa Scheme
        @test schemes["flux"].requires == Dict("q_left"=>"ppm#q_left",
                                               "q_right"=>"ppm#q_right")
    end

    @testset "E_PROVIDER_NOT_FOUND: requires references absent scheme" begin
        consumer_raw = Dict{String,Any}(
            "applies_to" => Dict("op"=>"flux","args"=>Any["\$q"],"dim"=>"\$x"),
            "grid_family"=> "cartesian",
            "stencil"    => Any[
                Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                     "coeff"=>1.0)
            ],
            "requires"   => Dict("ql" => "nonexistent_scheme#q_left"),
        )
        ex = @test_throws EarthSciSerialization.RuleEngineError begin
            parse_schemes(Dict("flux" => consumer_raw))
        end
        @test ex.value.code == "E_PROVIDER_NOT_FOUND"
    end

    @testset "E_PROVIDER_NOT_FOUND: requires references a plain stencil (not multi_output)" begin
        plain_raw = Dict{String,Any}(
            "applies_to" => Dict("op"=>"grad","args"=>Any["\$u"],"dim"=>"\$x"),
            "grid_family"=> "cartesian",
            "stencil"    => Any[
                Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                     "coeff"=>1.0)
            ],
        )
        consumer_raw = Dict{String,Any}(
            "applies_to" => Dict("op"=>"flux","args"=>Any["\$q"],"dim"=>"\$x"),
            "grid_family"=> "cartesian",
            "stencil"    => Any[
                Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                     "coeff"=>1.0)
            ],
            "requires"   => Dict("ql" => "plain_grad#some_output"),
        )
        ex = @test_throws EarthSciSerialization.RuleEngineError begin
            parse_schemes(Dict("plain_grad" => plain_raw, "flux" => consumer_raw))
        end
        @test ex.value.code == "E_PROVIDER_NOT_FOUND"
    end

    @testset "E_OUTPUT_NOT_FOUND: requires references undeclared output in provider" begin
        provider_raw = _ppm_raw()
        consumer_raw = Dict{String,Any}(
            "applies_to" => Dict("op"=>"flux","args"=>Any["\$q"],"dim"=>"\$x"),
            "grid_family"=> "cartesian",
            "stencil"    => Any[
                Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                     "coeff"=>1.0)
            ],
            "requires"   => Dict("ql" => "ppm#q_center"),  # q_center not in outputs
        )
        ex = @test_throws EarthSciSerialization.RuleEngineError begin
            parse_schemes(Dict("ppm" => provider_raw, "flux" => consumer_raw))
        end
        @test ex.value.code == "E_OUTPUT_NOT_FOUND"
    end

    @testset "fixture round-trip: multi_output_ppm_reconstruction.esm" begin
        path = joinpath(@__DIR__, "..", "..", "..", "tests",
                        "discretizations", "multi_output_ppm_reconstruction.esm")
        @test isfile(path)
        esm = EarthSciSerialization.load(path)
        @test esm isa EsmFile
        @test esm.discretizations !== nothing
        @test haskey(esm.discretizations, "ppm_reconstruction")
        @test haskey(esm.discretizations, "ppm_flux")
        @test esm.discretizations["ppm_reconstruction"]["kind"] == "multi_output_stencil"
        @test esm.discretizations["ppm_flux"]["kind"] == "stencil"

        schemes = parse_schemes(esm.discretizations)
        @test schemes["ppm_reconstruction"] isa MultiOutputStencilScheme
        @test schemes["ppm_flux"] isa Scheme
        ppm = schemes["ppm_reconstruction"]::MultiOutputStencilScheme
        @test ppm.outputs == ["q_left_edge", "q_right_edge"]
        @test ppm.primary === nothing
        @test ppm.emits_location == "face"
        @test haskey(ppm.stencil, "q_left_edge")
        @test haskey(ppm.stencil, "q_right_edge")
        @test length(ppm.stencil["q_left_edge"]) == 2
        @test length(ppm.stencil["q_right_edge"]) == 2
        flux = schemes["ppm_flux"]::Scheme
        @test flux.requires["q_left_edge"] == "ppm_reconstruction#q_left_edge"
        @test flux.requires["q_right_edge"] == "ppm_reconstruction#q_right_edge"
    end
end

# ============================================================================
# §7.9 Multi-output stencil scheme — trigger 1 expansion (ess-ebe)
# ============================================================================

@testset "multi_output_stencil trigger 1 expansion (RFC §7.9, ess-ebe)" begin

    # Minimal two-output reconstruction scheme with primary = "q_lo".
    # Stencil: q_lo = avg(i-1, i), q_hi = avg(i, i+1).
    recon_raw = Dict{String,Any}(
        "kind"        => "multi_output_stencil",
        "applies_to"  => Dict("op" => "recon", "args" => Any["\$q"], "dim" => "\$x"),
        "grid_family" => "cartesian",
        "outputs"     => Any["q_lo", "q_hi"],
        "emits_location" => "face",
        "primary"     => "q_lo",
        "stencil"     => Dict{String,Any}(
            "q_lo" => Any[
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>-1),
                     "coeff"    => 0.5),
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=> 0),
                     "coeff"    => 0.5),
            ],
            "q_hi" => Any[
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=> 0),
                     "coeff"    => 0.5),
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=> 1),
                     "coeff"    => 0.5),
            ],
        ),
    )
    schemes_with_recon = parse_schemes(Dict("recon1d" => recon_raw))

    function _make_ctx(; periodic=true)
        EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}(
                "spatial_dims"  => ["i"],
                "periodic_dims" => periodic ? ["i"] : String[],
                "nonuniform_dims" => String[],
                "metric_array_names" => String[],
                "dim_sizes"     => Dict{String,Any}("i" => 8),
            )),
            Dict("q" => Dict{String,Any}("grid" => "gx",
                                          "shape" => Any["i"],
                                          "location" => "cell_center")),
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(),
            Dict{String,AbstractScheme}(schemes_with_recon...),
        )
    end

    @testset "expand emits two observed equations and returns index(primary, i)" begin
        ctx = _make_ctx()
        sch = schemes_with_recon["recon1d"]::MultiOutputStencilScheme
        bindings = Dict{String,ESM_Expr}("\$q" => VarExpr("q"), "\$x" => VarExpr("i"))

        result = EarthSciSerialization.expand_multi_output_scheme_direct(sch, bindings, ctx)

        # Replacement is index(q_lo__q__i, i).
        @test result isa OpExpr
        @test result.op == "index"
        @test length(result.args) == 2
        @test result.args[1] isa VarExpr
        @test result.args[1].name == "q_lo__q__i"
        @test result.args[2] isa VarExpr
        @test result.args[2].name == "i"

        # Two observed equations emitted (one per output).
        @test length(ctx.emitted_equations) == 2

        # Both marked observed with correct emitted_by.
        for eqn in ctx.emitted_equations
            @test get(eqn, "observed", false) == true
            @test get(eqn, "emitted_by", "") == "recon1d"
            lhs = eqn["lhs"]
            @test lhs["op"] == "arrayop"
            @test lhs["output_idx"] == ["i"]
            @test lhs["ranges"] == Dict("i" => Any[1, 8])
            rhs = eqn["rhs"]
            @test rhs["op"] == "arrayop"
            @test rhs["output_idx"] == ["i"]
        end

        # LHS expressions reference the mangled output names.
        lhs_names = [eqn["lhs"]["expr"]["args"][1] for eqn in ctx.emitted_equations]
        @test Set(lhs_names) == Set(["q_lo__q__i", "q_hi__q__i"])

        # Two auto-declared variables.
        @test length(ctx.emitted_variables) == 2
        @test haskey(ctx.emitted_variables, "q_lo__q__i")
        @test haskey(ctx.emitted_variables, "q_hi__q__i")
        @test ctx.emitted_variables["q_lo__q__i"]["type"] == "observed"
        @test ctx.emitted_variables["q_lo__q__i"]["location"] == "face"
    end

    @testset "second call with same bindings is memoized (no duplicate emission)" begin
        ctx = _make_ctx()
        sch = schemes_with_recon["recon1d"]::MultiOutputStencilScheme
        b   = Dict{String,ESM_Expr}("\$q" => VarExpr("q"), "\$x" => VarExpr("i"))
        EarthSciSerialization.expand_multi_output_scheme_direct(sch, b, ctx)
        EarthSciSerialization.expand_multi_output_scheme_direct(sch, b, ctx)
        @test length(ctx.emitted_equations) == 2  # still 2, not 4
    end

    @testset "different operand binding produces distinct mangled names" begin
        ctx = EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}(
                "spatial_dims"   => ["i"],
                "periodic_dims"  => ["i"],
                "nonuniform_dims" => String[],
                "metric_array_names" => String[],
                "dim_sizes"      => Dict{String,Any}("i" => 8),
            )),
            Dict(
                "u" => Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center"),
                "v" => Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center"),
            ),
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(),
            Dict{String,AbstractScheme}(schemes_with_recon...),
        )
        sch = schemes_with_recon["recon1d"]::MultiOutputStencilScheme
        b1  = Dict{String,ESM_Expr}("\$q" => VarExpr("u"), "\$x" => VarExpr("i"))
        b2  = Dict{String,ESM_Expr}("\$q" => VarExpr("v"), "\$x" => VarExpr("i"))
        r1 = EarthSciSerialization.expand_multi_output_scheme_direct(sch, b1, ctx)
        r2 = EarthSciSerialization.expand_multi_output_scheme_direct(sch, b2, ctx)
        # 4 equations total: 2 for u, 2 for v
        @test length(ctx.emitted_equations) == 4
        @test r1.args[1].name == "q_lo__u__i"
        @test r2.args[1].name == "q_lo__v__i"
    end

    @testset "E_SCHEME_BOUNDED_DIM for non-periodic dimension" begin
        ctx = _make_ctx(periodic=false)
        sch = schemes_with_recon["recon1d"]::MultiOutputStencilScheme
        b   = Dict{String,ESM_Expr}("\$q" => VarExpr("q"), "\$x" => VarExpr("i"))
        ex  = try
            EarthSciSerialization.expand_multi_output_scheme_direct(sch, b, ctx)
            nothing
        catch e; e end
        @test ex isa EarthSciSerialization.RuleEngineError
        @test ex.code == "E_SCHEME_BOUNDED_DIM"
    end

    @testset "provider-only (primary=null) raises E_SCHEME_MISMATCH via use:-rule" begin
        provider_only_raw = Dict{String,Any}(
            "kind"        => "multi_output_stencil",
            "applies_to"  => Dict("op"=>"recon","args"=>Any["\$q"],"dim"=>"\$x"),
            "grid_family" => "cartesian",
            "outputs"     => Any["q_lo", "q_hi"],
            "stencil"     => Dict{String,Any}(
                "q_lo" => Any[Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),"coeff"=>1.0)],
                "q_hi" => Any[Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),"coeff"=>1.0)],
            ),
        )
        schemes_null_primary = parse_schemes(Dict("provider" => provider_only_raw))
        rule = parse_rule("r", Dict("pattern" => Dict("op"=>"recon","args"=>Any["\$q"],"dim"=>"\$x"),
                                    "use"     => "provider"))
        ctx = EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}("spatial_dims"=>["i"],"periodic_dims"=>["i"],
                                           "nonuniform_dims"=>String[],"metric_array_names"=>String[],
                                           "dim_sizes"=>Dict{String,Any}("i"=>8))),
            Dict("q"  => Dict{String,Any}("grid"=>"gx","shape"=>Any["i"])),
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(),
            Dict{String,AbstractScheme}(schemes_null_primary...),
        )
        seed = OpExpr("recon", ESM_Expr[VarExpr("q")]; dim="i")
        ex = try rewrite(seed, Rule[rule], ctx); nothing catch e; e end
        @test ex isa EarthSciSerialization.RuleEngineError
        @test ex.code == "E_SCHEME_MISMATCH"
        @test occursin("provider-only", ex.message)
    end

    @testset "discretize() end-to-end: emits observed equations + rewrites primary" begin
        esm = Dict{String,Any}(
            "esm"      => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "multi_output_direct"),
            "grids"    => Dict{String,Any}(
                "gx" => Dict{String,Any}(
                    "family"     => "cartesian",
                    "dimensions" => Any[
                        Dict{String,Any}("name"=>"i","size"=>8,
                                          "periodic"=>true,"spacing"=>"uniform"),
                    ],
                ),
            ),
            "discretizations" => Dict{String,Any}("recon1d" => recon_raw),
            "rules"    => Any[
                Dict{String,Any}(
                    "name"    => "recon1d_rule",
                    "pattern" => Dict{String,Any}("op"=>"recon","args"=>Any["\$q"],"dim"=>"\$x"),
                    "use"     => "recon1d",
                ),
            ],
            "models"   => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "grid"      => "gx",
                    "variables" => Dict{String,Any}(
                        "q" => Dict{String,Any}("type"=>"state","default"=>0.0,
                                                 "units"=>"1","shape"=>Any["i"],
                                                 "location"=>"cell_center"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op"=>"D","args"=>Any["q"],"wrt"=>"t"),
                            "rhs" => Dict{String,Any}("op"=>"recon","args"=>Any["q"],"dim"=>"i"),
                        ),
                    ],
                ),
            ),
        )

        out = discretize(esm)
        model_out = out["models"]["M"]

        # 1. Original equation RHS should no longer mention "recon".
        orig_rhs = JSON3.write(model_out["equations"][1]["rhs"])
        @test !occursin("\"recon\"", orig_rhs)
        # It should mention the primary mangled name.
        @test occursin("q_lo__q__i", orig_rhs)

        # 2. Two additional observed equations were injected (may be wrapped in arrayop
        #    by the arrayop lift for D(q,...), and the emitted ones have arrayop LHS already).
        eqns = model_out["equations"]
        observed_eqns = [e for e in eqns if get(e, "observed", false) == true]
        @test length(observed_eqns) == 2

        # 3. Both observed equations carry emitted_by = "recon1d".
        for e in observed_eqns
            @test get(e, "emitted_by", "") == "recon1d"
        end

        # 4. Auto-declared variables appear in model.variables.
        @test haskey(model_out["variables"], "q_lo__q__i")
        @test haskey(model_out["variables"], "q_hi__q__i")
        @test model_out["variables"]["q_lo__q__i"]["type"] == "observed"
    end
end

# ============================================================================
# §7.9 Multi-output stencil scheme — trigger 2 expansion (ess-699)
# ============================================================================

@testset "multi_output_stencil trigger 2 expansion (RFC §7.9, ess-699)" begin

    # Provider: two-output reconstruction scheme with primary=null.
    recon_provider_raw = Dict{String,Any}(
        "kind"           => "multi_output_stencil",
        "applies_to"     => Dict("op" => "reconstruct", "args" => Any["\$q"], "dim" => "\$x"),
        "grid_family"    => "cartesian",
        "outputs"        => Any["q_left_edge", "q_right_edge"],
        "emits_location" => "face",
        "stencil"        => Dict{String,Any}(
            "q_left_edge" => Any[
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>-1),
                     "coeff"    => 0.5),
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=> 0),
                     "coeff"    => 0.5),
            ],
            "q_right_edge" => Any[
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=> 0),
                     "coeff"    => 0.5),
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=> 1),
                     "coeff"    => 0.5),
            ],
        ),
    )

    # Consumer: stencil scheme with requires referencing the provider.
    # Coefficient uses the local alias names (q_left_edge, q_right_edge).
    flux_consumer_raw = Dict{String,Any}(
        "kind"        => "stencil",
        "applies_to"  => Dict("op" => "flux", "args" => Any["\$q", "\$c"], "dim" => "\$x"),
        "grid_family" => "cartesian",
        "requires"    => Dict{String,Any}(
            "q_left_edge"  => "ppm_recon#q_left_edge",
            "q_right_edge" => "ppm_recon#q_right_edge",
        ),
        "stencil"     => Any[
            Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                 "coeff"    => Dict{String,Any}(
                     "op"   => "-",
                     "args" => Any[
                         Dict("op"=>"*","args"=>Any["\$c","q_right_edge"]),
                         Dict("op"=>"*","args"=>Any["\$c","q_left_edge"]),
                     ],
                 )),
        ],
    )

    all_schemes_raw = Dict{String,Any}(
        "ppm_recon" => recon_provider_raw,
        "ppm_flux"  => flux_consumer_raw,
    )
    schemes = parse_schemes(all_schemes_raw)

    function _make_demand_ctx(; extra_vars=Dict{String,Dict{String,Any}}())
        base_vars = Dict{String,Dict{String,Any}}(
            "q" => Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center"),
            "c" => Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center"),
        )
        for (k, v) in extra_vars; base_vars[k] = v; end
        EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}(
                "spatial_dims"       => ["i"],
                "periodic_dims"      => ["i"],
                "nonuniform_dims"    => String[],
                "metric_array_names" => String[],
                "dim_sizes"          => Dict{String,Any}("i" => 8),
            )),
            base_vars,
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(),
            Dict{String,AbstractScheme}(schemes...),
        )
    end

    @testset "demand path emits provider equations and rewrites coefficient" begin
        ctx = _make_demand_ctx()
        sch = schemes["ppm_flux"]::Scheme
        b   = Dict{String,ESM_Expr}(
            "\$q" => VarExpr("q"), "\$c" => VarExpr("c"), "\$x" => VarExpr("i"))

        result = EarthSciSerialization.expand_scheme(sch, b, ctx)

        # Provider emitted two observed equations.
        @test length(ctx.emitted_equations) == 2
        for eqn in ctx.emitted_equations
            @test get(eqn, "observed", false) == true
            @test get(eqn, "emitted_by", "") == "ppm_recon"
        end

        # Two auto-declared variables.
        @test haskey(ctx.emitted_variables, "q_left_edge__q__i")
        @test haskey(ctx.emitted_variables, "q_right_edge__q__i")
        @test ctx.emitted_variables["q_left_edge__q__i"]["location"] == "face"

        # Consumer result: the stencil coefficient must reference mangled names,
        # not the bare local aliases.
        result_str = EarthSciSerialization.serialize_expression(result)
        rhs_json = JSON3.write(result_str)
        @test occursin("q_left_edge__q__i", rhs_json)
        @test occursin("q_right_edge__q__i", rhs_json)
        @test !occursin("\"q_left_edge\"", rhs_json)
        @test !occursin("\"q_right_edge\"", rhs_json)
    end

    @testset "second expand_scheme call is memoized (no duplicate provider emission)" begin
        ctx = _make_demand_ctx()
        sch = schemes["ppm_flux"]::Scheme
        b   = Dict{String,ESM_Expr}(
            "\$q" => VarExpr("q"), "\$c" => VarExpr("c"), "\$x" => VarExpr("i"))
        EarthSciSerialization.expand_scheme(sch, b, ctx)
        EarthSciSerialization.expand_scheme(sch, b, ctx)
        @test length(ctx.emitted_equations) == 2  # still 2, not 4
    end

    @testset "diamond dedup: two consumers sharing one provider emit once" begin
        # A second consumer that also requires ppm_recon.
        flux2_raw = Dict{String,Any}(
            "kind"        => "stencil",
            "applies_to"  => Dict("op" => "flux2", "args" => Any["\$q"], "dim" => "\$x"),
            "grid_family" => "cartesian",
            "requires"    => Dict{String,Any}(
                "q_left_edge" => "ppm_recon#q_left_edge",
            ),
            "stencil" => Any[
                Dict("selector" => Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),
                     "coeff"    => "q_left_edge"),
            ],
        )
        schemes2 = parse_schemes(Dict{String,Any}(
            "ppm_recon" => recon_provider_raw,
            "ppm_flux"  => flux_consumer_raw,
            "flux2"     => flux2_raw,
        ))
        ctx = EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}(
                "spatial_dims"       => ["i"],
                "periodic_dims"      => ["i"],
                "nonuniform_dims"    => String[],
                "metric_array_names" => String[],
                "dim_sizes"          => Dict{String,Any}("i" => 8),
            )),
            Dict("q" => Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center"),
                 "c" => Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center")),
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(),
            Dict{String,AbstractScheme}(schemes2...),
        )
        b_flux  = Dict{String,ESM_Expr}(
            "\$q" => VarExpr("q"), "\$c" => VarExpr("c"), "\$x" => VarExpr("i"))
        b_flux2 = Dict{String,ESM_Expr}(
            "\$q" => VarExpr("q"), "\$x" => VarExpr("i"))
        EarthSciSerialization.expand_scheme(schemes2["ppm_flux"]::Scheme, b_flux, ctx)
        EarthSciSerialization.expand_scheme(schemes2["flux2"]::Scheme, b_flux2, ctx)
        @test length(ctx.emitted_equations) == 2  # provider emitted exactly once
    end

    @testset "E_SCHEME_CYCLE: provider already on resolution stack" begin
        ctx = _make_demand_ctx()
        provider = schemes["ppm_recon"]::MultiOutputStencilScheme
        # Simulate a cycle by manually pushing the provider name.
        push!(ctx.provider_resolution_stack, "ppm_recon")
        b = Dict{String,ESM_Expr}("\$q" => VarExpr("q"), "\$x" => VarExpr("i"))
        ex = try
            EarthSciSerialization.expand_scheme(schemes["ppm_flux"]::Scheme,
                Dict{String,ESM_Expr}(
                    "\$q" => VarExpr("q"), "\$c" => VarExpr("c"), "\$x" => VarExpr("i")),
                ctx)
            nothing
        catch e; e end
        @test ex isa EarthSciSerialization.RuleEngineError
        @test ex.code == "E_SCHEME_CYCLE"
        @test occursin("ppm_recon", ex.message)
    end

    @testset "E_PROVIDER_NAME_CLASH: different provider emits same mangled name" begin
        # A second provider that happens to emit the same output name.
        clash_raw = Dict{String,Any}(
            "kind"           => "multi_output_stencil",
            "applies_to"     => Dict("op"=>"reconstruct","args"=>Any["\$q"],"dim"=>"\$x"),
            "grid_family"    => "cartesian",
            "outputs"        => Any["q_left_edge", "q_right_edge"],
            "emits_location" => "face",
            "stencil"        => Dict{String,Any}(
                "q_left_edge"  => Any[Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),"coeff"=>1.0)],
                "q_right_edge" => Any[Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),"coeff"=>1.0)],
            ),
        )
        clash_consumer_raw = Dict{String,Any}(
            "kind"        => "stencil",
            "applies_to"  => Dict("op"=>"flux2","args"=>Any["\$q"],"dim"=>"\$x"),
            "grid_family" => "cartesian",
            "requires"    => Dict{String,Any}("q_left_edge" => "clash_provider#q_left_edge"),
            "stencil"     => Any[Dict("selector"=>Dict("kind"=>"cartesian","axis"=>"\$x","offset"=>0),"coeff"=>"q_left_edge")],
        )
        schemes_clash = parse_schemes(Dict{String,Any}(
            "ppm_recon"      => recon_provider_raw,
            "clash_provider" => clash_raw,
            "ppm_flux"       => flux_consumer_raw,
            "clash_consumer" => clash_consumer_raw,
        ))
        ctx_clash = EarthSciSerialization.RuleContext(
            Dict("gx" => Dict{String,Any}(
                "spatial_dims"=>["i"],"periodic_dims"=>["i"],
                "nonuniform_dims"=>String[],"metric_array_names"=>String[],
                "dim_sizes"=>Dict{String,Any}("i"=>8))),
            Dict("q"=>Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center"),
                 "c"=>Dict{String,Any}("grid"=>"gx","shape"=>Any["i"],"location"=>"cell_center")),
            Dict{String,Int}(), nothing,
            Dict{String,Vector{Dict{String,Int}}}(),
            Dict{String,AbstractScheme}(schemes_clash...),
        )
        b_flux  = Dict{String,ESM_Expr}(
            "\$q"=>VarExpr("q"),"\$c"=>VarExpr("c"),"\$x"=>VarExpr("i"))
        b_clash = Dict{String,ESM_Expr}("\$q"=>VarExpr("q"),"\$x"=>VarExpr("i"))
        # First consumer succeeds.
        EarthSciSerialization.expand_scheme(schemes_clash["ppm_flux"]::Scheme, b_flux, ctx_clash)
        # Second consumer (clash_consumer) tries to emit q_left_edge__q__i again.
        ex = try
            EarthSciSerialization.expand_scheme(
                schemes_clash["clash_consumer"]::Scheme, b_clash, ctx_clash)
            nothing
        catch e; e end
        @test ex isa EarthSciSerialization.RuleEngineError
        @test ex.code == "E_PROVIDER_NAME_CLASH"
        @test occursin("q_left_edge__q__i", ex.message)
    end

    @testset "discretize() end-to-end: demand path emits provider + rewrites consumer" begin
        esm = Dict{String,Any}(
            "esm"      => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "multi_output_demand"),
            "grids"    => Dict{String,Any}(
                "gx" => Dict{String,Any}(
                    "family"     => "cartesian",
                    "dimensions" => Any[
                        Dict{String,Any}("name"=>"i","size"=>8,
                                          "periodic"=>true,"spacing"=>"uniform"),
                    ],
                ),
            ),
            "discretizations" => Dict{String,Any}(
                "ppm_recon" => recon_provider_raw,
                "ppm_flux"  => flux_consumer_raw,
            ),
            "rules" => Any[
                Dict{String,Any}(
                    "name"    => "flux_rule",
                    "pattern" => Dict{String,Any}(
                        "op"=>"flux","args"=>Any["\$q","\$c"],"dim"=>"\$x"),
                    "use"     => "ppm_flux",
                ),
            ],
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "grid" => "gx",
                    "variables" => Dict{String,Any}(
                        "q" => Dict{String,Any}("type"=>"state","default"=>0.0,
                                                 "units"=>"1","shape"=>Any["i"],
                                                 "location"=>"cell_center"),
                        "c" => Dict{String,Any}("type"=>"parameter","default"=>1.0,
                                                 "units"=>"1","shape"=>Any["i"],
                                                 "location"=>"cell_center"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op"=>"D","args"=>Any["q"],"wrt"=>"t"),
                            "rhs" => Dict{String,Any}(
                                "op"=>"flux","args"=>Any["q","c"],"dim"=>"i"),
                        ),
                    ],
                ),
            ),
        )

        out = discretize(esm)
        model_out = out["models"]["M"]

        # 1. Original equation RHS no longer mentions "flux".
        orig_rhs = JSON3.write(model_out["equations"][1]["rhs"])
        @test !occursin("\"flux\"", orig_rhs)

        # 2. Two provider-emitted observed equations.
        observed = [e for e in model_out["equations"] if get(e, "observed", false) == true]
        @test length(observed) == 2
        for e in observed
            @test get(e, "emitted_by", "") == "ppm_recon"
        end

        # 3. Provider output variables auto-declared.
        @test haskey(model_out["variables"], "q_left_edge__q__i")
        @test haskey(model_out["variables"], "q_right_edge__q__i")
        @test model_out["variables"]["q_left_edge__q__i"]["type"] == "observed"

        # 4. Consumer result references mangled provider output names.
        all_eqn_json = JSON3.write(model_out["equations"])
        @test occursin("q_left_edge__q__i", all_eqn_json)
        @test occursin("q_right_edge__q__i", all_eqn_json)
    end
end
