using Test
using EarthSciSerialization
using JSON3

@testset "discretize() pipeline (RFC §11, gt-gbs2)" begin

    # Helper: a minimal scalar ODE model, no PDE ops anywhere.
    function _scalar_ode_esm()
        return Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}(
                "name" => "scalar_ode",
                "description" => "dx/dt = -k * x",
            ),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "variables" => Dict{String,Any}(
                        "x" => Dict{String,Any}("type" => "state", "default" => 1.0, "units" => "1"),
                        "k" => Dict{String,Any}("type" => "parameter", "default" => 0.5, "units" => "1/s"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["x"], "wrt" => "t"),
                            "rhs" => Dict{String,Any}("op" => "*", "args" => Any[
                                Dict{String,Any}("op" => "-", "args" => Any["k"]),
                                "x",
                            ]),
                        ),
                    ],
                ),
            ),
        )
    end

    # 1D "heat-like" model where the RHS has a PDE op that a rule must rewrite.
    function _heat_1d_esm(; with_rule::Bool=true)
        esm = Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "heat_1d"),
            "grids" => Dict{String,Any}(
                "gx" => Dict{String,Any}(
                    "family" => "cartesian",
                    "dimensions" => Any[
                        Dict{String,Any}("name" => "i", "size" => 8, "periodic" => true, "spacing" => "uniform"),
                    ],
                ),
            ),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "grid" => "gx",
                    "variables" => Dict{String,Any}(
                        "u" => Dict{String,Any}(
                            "type" => "state",
                            "default" => 0.0,
                            "units" => "1",
                            "shape" => Any["i"],
                            "location" => "cell_center",
                        ),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                            # RHS is grad(u, dim="i") — must be rewritten.
                            "rhs" => Dict{String,Any}(
                                "op" => "grad", "args" => Any["u"], "dim" => "i",
                            ),
                        ),
                    ],
                ),
            ),
        )
        if with_rule
            # Rule: grad($u, dim=$x) -> -( index($u, ($x - 1)) ) + index($u, ($x + 1))
            # (stand-in for a centered-2nd rewrite without the 1/(2 dx) coefficient,
            # which would require grid-metric handling; that is Step 1b work.)
            esm["rules"] = Any[
                Dict{String,Any}(
                    "name" => "centered_grad",
                    "pattern" => Dict{String,Any}(
                        "op" => "grad", "args" => Any["\$u"], "dim" => "\$x",
                    ),
                    "replacement" => Dict{String,Any}(
                        "op" => "+",
                        "args" => Any[
                            Dict{String,Any}(
                                "op" => "-",
                                "args" => Any[
                                    Dict{String,Any}(
                                        "op" => "index",
                                        "args" => Any[
                                            "\$u",
                                            Dict{String,Any}(
                                                "op" => "-",
                                                "args" => Any["\$x", 1],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            Dict{String,Any}(
                                "op" => "index",
                                "args" => Any[
                                    "\$u",
                                    Dict{String,Any}(
                                        "op" => "+",
                                        "args" => Any["\$x", 1],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ]
        end
        return esm
    end

    @testset "Acceptance 1 — runs end-to-end on a scalar ODE" begin
        esm = _scalar_ode_esm()
        out = discretize(esm)
        @test out isa Dict{String,Any}
        @test haskey(out["metadata"], "discretized_from")
        @test out["metadata"]["discretized_from"]["name"] == "scalar_ode"
        @test "discretized" in String.(out["metadata"]["tags"])
        # Input must not be mutated.
        @test !haskey(esm["metadata"], "discretized_from")
    end

    @testset "Acceptance 1 — runs end-to-end on a 1D PDE with a matching rule" begin
        esm = _heat_1d_esm(; with_rule=true)
        out = discretize(esm)
        rhs = out["models"]["M"]["equations"][1]["rhs"]
        # After rewrite, RHS should be the indexed form; no grad op left.
        @test !occursin("\"grad\"", JSON3.write(rhs))
        @test occursin("\"index\"", JSON3.write(rhs))
    end

    @testset "Acceptance 2 — determinism (two calls byte-identical)" begin
        esm = _heat_1d_esm(; with_rule=true)
        a = discretize(esm)
        b = discretize(esm)
        # JSON3.write emits object keys in insertion order; to be robust to key
        # ordering we round-trip through canonicalize on the RHS we care about.
        rhs_a = a["models"]["M"]["equations"][1]["rhs"]
        rhs_b = b["models"]["M"]["equations"][1]["rhs"]
        @test canonical_json(EarthSciSerialization.parse_expression(rhs_a)) ==
              canonical_json(EarthSciSerialization.parse_expression(rhs_b))
        # Metadata provenance is deterministic too.
        @test a["metadata"]["discretized_from"] == b["metadata"]["discretized_from"]
    end

    @testset "Acceptance 3 — output re-parses through parse_expression" begin
        esm = _scalar_ode_esm()
        out = discretize(esm)
        rhs = out["models"]["M"]["equations"][1]["rhs"]
        parsed = EarthSciSerialization.parse_expression(rhs)
        @test parsed isa EarthSciSerialization.Expr
    end

    @testset "Acceptance 4 — E_UNREWRITTEN_PDE_OP on unmatched PDE op" begin
        esm = _heat_1d_esm(; with_rule=false)
        err = try
            discretize(esm)
            nothing
        catch e
            e
        end
        @test err isa RuleEngineError
        @test err.code == "E_UNREWRITTEN_PDE_OP"
    end

    @testset "strict_unrewritten=false stamps passthrough and retains op" begin
        esm = _heat_1d_esm(; with_rule=false)
        out = discretize(esm; strict_unrewritten=false)
        eqn = out["models"]["M"]["equations"][1]
        @test eqn["passthrough"] === true
        @test occursin("\"grad\"", JSON3.write(eqn["rhs"]))
    end

    @testset "passthrough=true on input skips the coverage check" begin
        esm = _heat_1d_esm(; with_rule=false)
        esm["models"]["M"]["equations"][1]["passthrough"] = true
        out = discretize(esm)  # default strict_unrewritten=true is fine
        @test out["models"]["M"]["equations"][1]["passthrough"] === true
    end

    @testset "BC value canonicalization (no rules)" begin
        esm = Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "bc_plain"),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "variables" => Dict{String,Any}(
                        "u" => Dict{String,Any}("type" => "state", "default" => 0.0, "units" => "1"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                            "rhs" => 0.0,
                        ),
                    ],
                    "boundary_conditions" => Dict{String,Any}(
                        "u_dirichlet_xmin" => Dict{String,Any}(
                            "variable" => "u",
                            "side"     => "xmin",
                            "kind"     => "dirichlet",
                            # 1 + 0 should canonicalize to 1.
                            "value"    => Dict{String,Any}(
                                "op" => "+", "args" => Any[1, 0],
                            ),
                        ),
                    ),
                ),
            ),
        )
        out = discretize(esm)
        bc_val = out["models"]["M"]["boundary_conditions"]["u_dirichlet_xmin"]["value"]
        @test bc_val == 1
    end

    # =====================================================================
    # RFC §12 — DAE binding contract (gt-q7sh)
    # =====================================================================

    # Helper: a mixed DAE — one differential equation plus one authored
    # algebraic constraint. Julia's §12 strategy is direct hand-off to
    # MTK (no index reduction), so this should succeed with
    # dae_support=true and fail with E_NO_DAE_SUPPORT when dae_support=false.
    function _mixed_dae_esm()
        return Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "mixed_dae"),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "variables" => Dict{String,Any}(
                        "x" => Dict{String,Any}("type" => "state",    "default" => 1.0, "units" => "1"),
                        "y" => Dict{String,Any}("type" => "observed", "units" => "1"),
                        "k" => Dict{String,Any}("type" => "parameter","default" => 0.5, "units" => "1/s"),
                    ),
                    "equations" => Any[
                        # Differential: dx/dt = -k * x
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["x"], "wrt" => "t"),
                            "rhs" => Dict{String,Any}("op" => "*", "args" => Any[
                                Dict{String,Any}("op" => "-", "args" => Any["k"]),
                                "x",
                            ]),
                        ),
                        # Algebraic: y = x^2
                        Dict{String,Any}(
                            "lhs" => "y",
                            "rhs" => Dict{String,Any}("op" => "^", "args" => Any["x", 2]),
                        ),
                    ],
                ),
            ),
        )
    end

    @testset "DAE §12 — pure ODE stamps system_class=ode" begin
        out = discretize(_scalar_ode_esm())
        @test out["metadata"]["system_class"] == "ode"
        info = out["metadata"]["dae_info"]
        @test info["algebraic_equation_count"] == 0
        @test info["per_model"]["M"] == 0
    end

    @testset "DAE §12 — mixed DAE stamps system_class=dae" begin
        out = discretize(_mixed_dae_esm())
        @test out["metadata"]["system_class"] == "dae"
        info = out["metadata"]["dae_info"]
        @test info["algebraic_equation_count"] == 1
        @test info["per_model"]["M"] == 1
    end

    @testset "DAE §12 — dae_support=false aborts with E_NO_DAE_SUPPORT" begin
        err = try
            discretize(_mixed_dae_esm(); dae_support=false)
            nothing
        catch e
            e
        end
        @test err isa RuleEngineError
        @test err.code == "E_NO_DAE_SUPPORT"
        @test occursin("models.M.equations[2]", err.message)
        @test occursin("RFC §12", err.message)
    end

    @testset "DAE §12 — pure ODE passes even with dae_support=false" begin
        out = discretize(_scalar_ode_esm(); dae_support=false)
        @test out["metadata"]["system_class"] == "ode"
    end

    @testset "DAE §12 — explicit produces:algebraic marker is algebraic" begin
        esm = _scalar_ode_esm()
        # Stamp produces:algebraic on the differential equation. The
        # classifier reads the marker first, so the equation must count
        # as algebraic even though its LHS is a time derivative.
        esm["models"]["M"]["equations"][1]["produces"] = "algebraic"
        out = discretize(esm)
        @test out["metadata"]["system_class"] == "dae"
        @test out["metadata"]["dae_info"]["algebraic_equation_count"] == 1
    end

    @testset "DAE §12 — ESM_DAE_SUPPORT=0 env var disables by default" begin
        saved = get(ENV, "ESM_DAE_SUPPORT", nothing)
        ENV["ESM_DAE_SUPPORT"] = "0"
        try
            err = try
                discretize(_mixed_dae_esm())
                nothing
            catch e
                e
            end
            @test err isa RuleEngineError
            @test err.code == "E_NO_DAE_SUPPORT"
            # Pure ODE still succeeds.
            out = discretize(_scalar_ode_esm())
            @test out["metadata"]["system_class"] == "ode"
        finally
            if saved === nothing
                delete!(ENV, "ESM_DAE_SUPPORT")
            else
                ENV["ESM_DAE_SUPPORT"] = saved
            end
        end
    end

    @testset "DAE §12 — explicit dae_support=true overrides ESM_DAE_SUPPORT=0" begin
        saved = get(ENV, "ESM_DAE_SUPPORT", nothing)
        ENV["ESM_DAE_SUPPORT"] = "0"
        try
            out = discretize(_mixed_dae_esm(); dae_support=true)
            @test out["metadata"]["system_class"] == "dae"
        finally
            if saved === nothing
                delete!(ENV, "ESM_DAE_SUPPORT")
            else
                ENV["ESM_DAE_SUPPORT"] = saved
            end
        end
    end

    @testset "DAE §12 — independent_variable respected from domain" begin
        # Model binds to a domain with independent_variable="tau"; an
        # equation with LHS D(x, wrt="t") is algebraic under this domain,
        # and D(x, wrt="tau") is differential.
        esm = Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "tau_indep"),
            "domains" => Dict{String,Any}(
                "d" => Dict{String,Any}("independent_variable" => "tau"),
            ),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "domain" => "d",
                    "variables" => Dict{String,Any}(
                        "x" => Dict{String,Any}("type" => "state", "default" => 0.0, "units" => "1"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["x"], "wrt" => "tau"),
                            "rhs" => 0.0,
                        ),
                    ],
                ),
            ),
        )
        out = discretize(esm)
        @test out["metadata"]["system_class"] == "ode"

        # Flip wrt to "t" — now algebraic under tau-indep domain.
        esm["models"]["M"]["equations"][1]["lhs"]["wrt"] = "t"
        out2 = discretize(esm)
        @test out2["metadata"]["system_class"] == "dae"
    end

    @testset "max_passes surfaces E_RULES_NOT_CONVERGED" begin
        # Rule `x -> x + 0` canonicalizes back to `x` → but a pattern that
        # refuses to fix-point: `$a -> $a + 1` on any variable `y` forever.
        esm = Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "loop"),
            "rules" => Any[
                Dict{String,Any}(
                    "name" => "never",
                    "pattern" => "\$a",
                    "replacement" => Dict{String,Any}(
                        "op" => "+", "args" => Any["\$a", 1],
                    ),
                ),
            ],
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "variables" => Dict{String,Any}(
                        "y" => Dict{String,Any}("type" => "state", "default" => 0.0, "units" => "1"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["y"], "wrt" => "t"),
                            "rhs" => "y",
                        ),
                    ],
                ),
            ),
        )
        err = try
            discretize(esm; max_passes=3)
            nothing
        catch e
            e
        end
        @test err isa RuleEngineError
        @test err.code == "E_RULES_NOT_CONVERGED"
    end
end
