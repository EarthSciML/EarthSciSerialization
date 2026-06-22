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

    @testset "lift_1d_arrayop=true lifts 1D shaped variables to arrayop form" begin
        # Default: 1D shaped variables keep the bare D(u) LHS (golden-stable).
        esm = _heat_1d_esm(; with_rule=true)
        out_default = discretize(esm)
        lhs_default = out_default["models"]["M"]["equations"][1]["lhs"]
        @test lhs_default["op"] == "D"

        # Opt-in: same document lifts to arrayop with ranges from the grid,
        # and periodic stencil accesses wrap declaratively via makearray regions.
        out = discretize(esm; lift_1d_arrayop=true)
        eqn = out["models"]["M"]["equations"][1]
        @test eqn["lhs"]["op"] == "arrayop"
        @test eqn["lhs"]["output_idx"] == Any["i"]
        @test eqn["lhs"]["ranges"] == Dict{String,Any}("i" => Any[1, 8])
        @test eqn["rhs"]["op"] == "arrayop"
        rhs_str = JSON3.write(eqn["rhs"])
        @test occursin("\"index\"", rhs_str)
        # Periodic wrapping lowers declaratively through the makearray-region
        # path; the imperative ifelse fold is retired (ess-8ne).
        @test occursin("\"makearray\"", rhs_str)
        @test !occursin("\"ifelse\"", rhs_str)
    end

    @testset "arrayop lift wraps periodic accesses of every shaped grid variable via makearray (ess-8ne)" begin
        # A stencil RHS may index shaped fields other than the equation's LHS
        # variable (e.g. a space-varying velocity in an advection rule); the
        # declarative periodic lowering must wrap those reads too, not just the
        # LHS variable's. Each single-cell boundary region instantiates the
        # stencil at a literal cell, so every out-of-range read — into u OR U —
        # is wrapped modulo the size to a concrete in-bounds index (no ifelse).
        esm = _heat_1d_esm(; with_rule=true)
        esm["models"]["M"]["variables"]["U"] = Dict{String,Any}(
            "type" => "state", "default" => 1.0, "units" => "1",
            "shape" => Any["i"], "location" => "cell_center",
        )
        # Rule replacement gains a literal reference to U at an offset:
        #   grad($u, dim=$x) -> index(U, $x+1) * index($u, $x+1) - index($u, $x-1)
        esm["rules"][1]["replacement"] = Dict{String,Any}(
            "op" => "-",
            "args" => Any[
                Dict{String,Any}("op" => "*", "args" => Any[
                    Dict{String,Any}("op" => "index", "args" => Any[
                        "U", Dict{String,Any}("op" => "+", "args" => Any["\$x", 1])]),
                    Dict{String,Any}("op" => "index", "args" => Any[
                        "\$u", Dict{String,Any}("op" => "+", "args" => Any["\$x", 1])]),
                ]),
                Dict{String,Any}("op" => "index", "args" => Any[
                    "\$u", Dict{String,Any}("op" => "-", "args" => Any["\$x", 1])]),
            ],
        )
        out = discretize(esm; lift_1d_arrayop=true)
        rhs = out["models"]["M"]["equations"][1]["rhs"]
        @test rhs["op"] == "arrayop"

        # Body is index(makearray(regions, values), i): region 0 is the raw
        # full-grid stencil; the rest are single-cell wrapped boundary regions.
        n = 8
        body = rhs["expr"]
        @test body["op"] == "index"
        ma = body["args"][1]
        @test ma["op"] == "makearray"
        @test ma["regions"][1] == Any[Any[1, n]]            # region 0 = full grid
        @test !occursin("\"ifelse\"", JSON3.write(rhs))     # fold retired

        # Collect every index read inside the wrapped boundary regions (skip
        # region 0, whose reads are still symbolic in i). Each must resolve to a
        # concrete in-bounds integer — for BOTH u and U — proving the periodic
        # wrap covers every shaped variable, not just the LHS variable's.
        reads = Tuple{String,Any}[]
        function _collect_idx(node)
            node isa AbstractDict || return
            if get(node, "op", nothing) == "index"
                push!(reads, (String(node["args"][1]), node["args"][2]))
            end
            for a in get(node, "args", Any[])
                _collect_idx(a)
            end
        end
        for k in 2:length(ma["values"])
            _collect_idx(ma["values"][k])
        end
        @test !isempty(reads)
        for (target, idx) in reads
            @test target in ("u", "U")
            @test idx isa Integer
            @test 1 <= idx <= n
        end
        targets = Set(t for (t, _) in reads)
        @test "u" in targets
        @test "U" in targets
    end

    @testset "non-periodic BCs: makearray-region ghost lowering (ess-hjg)" begin
        # 1D bounded heat-like model: D(u) = grad(u) rewritten to the centered
        # stencil -u[i-1] + u[i+1]. The non-periodic BC ghost is now lowered
        # DECLARATIVELY: boundary-cell emission consumes the rewritten
        # `bc["value"]` ghost AST produced by the inline dirichlet/neumann/robin
        # rules and splices it into makearray boundary regions (ess-hjg), in
        # place of the retired imperative ghost shadow.
        #
        # The ghost rules mirror ESD's finite_difference/{dirichlet,neumann,
        # robin}_bc.json (local 0-based `index($u,0)` = first interior cell;
        # `$h` from bind_side_spacing). Robin coefficients ride as trailing args.
        _dirichlet_rule() = Dict{String,Any}(
            "name" => "dirichlet_bc",
            "pattern" => Dict{String,Any}("op"=>"bc","kind"=>"dirichlet","side"=>"\$side",
                "args"=>Any["\$u","\$value"]),
            "replacement" => Dict{String,Any}("op"=>"-","args"=>Any[
                Dict{String,Any}("op"=>"*","args"=>Any[2,"\$value"]),
                Dict{String,Any}("op"=>"index","args"=>Any["\$u",0])]))
        _neumann_rule() = Dict{String,Any}(
            "name" => "neumann_bc",
            "pattern" => Dict{String,Any}("op"=>"bc","kind"=>"neumann","side"=>"\$side",
                "args"=>Any["\$u","\$value"]),
            "where" => Any[
                Dict{String,Any}("guard"=>"var_has_grid","pvar"=>"\$u","grid"=>"\$g"),
                Dict{String,Any}("guard"=>"bind_side_spacing","pvar"=>"\$h","side"=>"\$side","grid"=>"\$g")],
            "replacement" => Dict{String,Any}("op"=>"+","args"=>Any[
                Dict{String,Any}("op"=>"index","args"=>Any["\$u",0]),
                Dict{String,Any}("op"=>"*","args"=>Any["\$h","\$value"])]))
        _robin_rule() = Dict{String,Any}(
            "name" => "robin_bc",
            "pattern" => Dict{String,Any}("op"=>"bc","kind"=>"robin","side"=>"\$side",
                "args"=>Any["\$u","\$a","\$b","\$g"]),
            "where" => Any[
                Dict{String,Any}("guard"=>"var_has_grid","pvar"=>"\$u","grid"=>"\$gr"),
                Dict{String,Any}("guard"=>"bind_side_spacing","pvar"=>"\$h","side"=>"\$side","grid"=>"\$gr")],
            "replacement" => Dict{String,Any}("op"=>"/","args"=>Any[
                Dict{String,Any}("op"=>"+","args"=>Any[
                    Dict{String,Any}("op"=>"*","args"=>Any[Dict{String,Any}("op"=>"*","args"=>Any[2,"\$h"]),"\$g"]),
                    Dict{String,Any}("op"=>"*","args"=>Any[
                        Dict{String,Any}("op"=>"-","args"=>Any[Dict{String,Any}("op"=>"*","args"=>Any[2,"\$b"]),
                            Dict{String,Any}("op"=>"*","args"=>Any["\$a","\$h"])]),
                        Dict{String,Any}("op"=>"index","args"=>Any["\$u",0])])]),
                Dict{String,Any}("op"=>"+","args"=>Any[Dict{String,Any}("op"=>"*","args"=>Any["\$a","\$h"]),
                    Dict{String,Any}("op"=>"*","args"=>Any[2,"\$b"])])]))

        function _bounded_1d_esm(; bcs=true, right=Dict{String,Any}(
                    "variable"=>"u","kind"=>"neumann","side"=>"xmax","value"=>0),
                    extra_rules=Any[])
            esm = _heat_1d_esm(; with_rule=true)
            esm["grids"]["gx"]["dimensions"][1]["periodic"] = false
            append!(esm["rules"], Any[_dirichlet_rule(), _neumann_rule(), _robin_rule()])
            append!(esm["rules"], extra_rules)
            if bcs
                esm["models"]["M"]["boundary_conditions"] = Dict{String,Any}(
                    "left" => Dict{String,Any}(
                        "variable" => "u", "kind" => "dirichlet",
                        "side" => "xmin", "value" => 3),
                    "right" => right)
            end
            return esm
        end

        out = discretize(_bounded_1d_esm(); lift_1d_arrayop=true)
        eqs = out["models"]["M"]["equations"]
        # ONE arrayop equation over the full grid; the boundary ghosts ride in a
        # makearray body (the retired path shrank the range + emitted 2 extra
        # scalar equations).
        @test length(eqs) == 1
        eqn = eqs[1]
        @test eqn["lhs"]["op"] == "arrayop"
        @test eqn["lhs"]["ranges"] == Dict{String,Any}("i" => Any[1, 8])
        @test eqn["rhs"]["ranges"] == Dict{String,Any}("i" => Any[1, 8])
        # RHS body is index(makearray(regions, values), i): full grid + the two
        # boundary single cells (reach 1, both sides bounded).
        body = eqn["rhs"]["expr"]
        @test body["op"] == "index"
        ma = body["args"][1]
        @test ma["op"] == "makearray"
        @test ma["regions"] == Any[Any[Any[1,8]], Any[Any[1,1]], Any[Any[8,8]]]
        # No periodic folding on a bounded dim.
        @test !occursin("ifelse", JSON3.write(eqn["rhs"]))

        # xmin region: dirichlet ghost u[0] → 2*value − u[1] (2nd-order; consumes
        # the rule output, supersedes the retired 1st-order `value` ghost).
        s_xmin = replace(JSON3.write(ma["values"][2]), " " => "")
        @test !occursin("[\"u\",0]", s_xmin)   # no out-of-range read survives
        @test occursin("[\"u\",1]", s_xmin)    # reflected interior cell
        @test occursin("[\"u\",2]", s_xmin)    # interior neighbour
        # xmax region: zero-flux neumann ghost u[9] → u[8] (byte-identical to the
        # retired mirror; the rule's `+ h*0` folds away).
        s_xmax = replace(JSON3.write(ma["values"][3]), " " => "")
        @test occursin("[\"u\",8]", s_xmax)
        @test occursin("[\"u\",7]", s_xmax)
        @test !occursin("[\"u\",9]", s_xmax)

        # Numeric byte-identity anchor: u[k] = k, interior -u[i-1]+u[i+1] = 2;
        # dirichlet i=1 → -(2*3 - u[1]) + u[2] = -3; zero-neumann i=8 → -u[7]+u[8] = 1.
        f!, u0, p, _, vmap = build_evaluator(out; initial_conditions=Dict("u[$k]"=>Float64(k) for k in 1:8))
        du = similar(u0); f!(du, u0, p, 0.0)
        @test isapprox(du[vmap["u[1]"]], -3.0; rtol=1e-12)
        for k in 2:7
            @test isapprox(du[vmap["u[$k]"]], 2.0; rtol=1e-12)
        end
        @test isapprox(du[vmap["u[8]"]], 1.0; rtol=1e-12)   # zero-neumann mirror

        # Backward compat: bounded dim WITHOUT declared BCs is unchanged
        # (full range, single arrayop, zero-ghost convention).
        out0 = discretize(_bounded_1d_esm(bcs=false); lift_1d_arrayop=true)
        eqs0 = out0["models"]["M"]["equations"]
        @test length(eqs0) == 1
        @test eqs0[1]["lhs"]["ranges"] == Dict{String,Any}("i" => Any[1, 8])
        @test !occursin("makearray", JSON3.write(eqs0[1]["rhs"]))

        # nonzero-Neumann now flows through (retired path threw E_BC_UNSUPPORTED).
        # ghost u[8] + h*value, h = 1/8 → i=8: -u[7] + u[8] + 0.25 = 1.25.
        outn = discretize(_bounded_1d_esm(; right=Dict{String,Any}(
            "variable"=>"u","kind"=>"neumann","side"=>"xmax","value"=>2)); lift_1d_arrayop=true)
        fn!, u0n, pn, _, vmn = build_evaluator(outn; initial_conditions=Dict("u[$k]"=>Float64(k) for k in 1:8))
        dun = similar(u0n); fn!(dun, u0n, pn, 0.0)
        @test isapprox(dun[vmn["u[8]"]], 1.25; rtol=1e-12)

        # Robin now flows through (retired path threw E_BC_UNSUPPORTED). a=1,b=1,
        # g=0, h=1/8 → ghost (2-h)*u[8]/(h+2); i=8: -u[7] + that.
        outr = discretize(_bounded_1d_esm(; right=Dict{String,Any}(
            "variable"=>"u","kind"=>"robin","side"=>"xmax",
            "robin_alpha"=>1,"robin_beta"=>1,"robin_gamma"=>0)); lift_1d_arrayop=true)
        fr!, u0r, pr, _, vmr = build_evaluator(outr; initial_conditions=Dict("u[$k]"=>Float64(k) for k in 1:8))
        dur = similar(u0r); fr!(dur, u0r, pr, 0.0)
        h = 1/8; robin_ghost = (2-h)*8 / (h+2)
        @test isapprox(dur[vmr["u[8]"]], -7 + robin_ghost; rtol=1e-12)
    end

    @testset "_scan_stencil_reach! detects canonicalized constant-first offsets (ess-wg0)" begin
        # `canonicalize` reorders the commutative `+` so the literal leads: the
        # laplacian neighbour read `index(u, i + (-1), j)` becomes
        # `index(u, {+,[-1,"i"]}, j)` — a CONSTANT-first offset. The reach scan
        # used to match only the VARIABLE-first form `[v,k]`, so multi-dim
        # additive stencils computed per-axis reach 0; `_apply_makearray_bcs!`
        # then found no bounded side and silently dropped EVERY declarative BC
        # ghost (periodic/Dirichlet/Neumann/Robin) in 2-D. 1-D `d2` rules escaped
        # the bug only because they author one neighbour as a non-commutative
        # subtraction `index(u, i - 1)`, whose arg order canonicalize preserves.
        scan! = EarthSciSerialization._scan_stencil_reach!

        # --- Full authentic path: author variable-first, canonicalize, scan. ---
        # `index(u, i + (-1), j)` exactly as a laplacian rule authors it.
        raw = Dict{String,Any}("op" => "index", "args" => Any["u",
            Dict{String,Any}("op" => "+", "args" => Any["i", -1]), "j"])
        canon = EarthSciSerialization._canonicalize_value(raw)
        # Premise: canonicalize emitted the constant-first offset `[-1, "i"]`.
        off = canon["args"][2]
        @test off["op"] == "+"
        @test off["args"][1] == -1 && off["args"][2] == "i"
        # The fix: the canonicalized constant-first offset is detected (was 0).
        reach = Dict{String,Int}("i" => 0, "j" => 0)
        scan!(reach, canon)
        @test reach["i"] == 1
        @test reach["j"] == 0

        # --- Both arg orderings agree (the symmetry the fix restores). ---
        cf = Dict{String,Any}("op" => "index", "args" => Any["u",   # constant-first
            Dict{String,Any}("op" => "+", "args" => Any[-1, "i"]), "j"])
        vf = Dict{String,Any}("op" => "index", "args" => Any["u",   # variable-first
            Dict{String,Any}("op" => "+", "args" => Any["i", -1]), "j"])
        rcf = Dict{String,Int}("i" => 0, "j" => 0); scan!(rcf, cf)
        rvf = Dict{String,Int}("i" => 0, "j" => 0); scan!(rvf, vf)
        @test rcf == rvf == Dict("i" => 1, "j" => 0)

        # --- Full 2-D laplacian: constant-first offsets on BOTH axes detected. ---
        # The canonicalized four-neighbour reads: i±1 and j±1, all const-first.
        _nbr(di, dj) = Dict{String,Any}("op" => "index", "args" => Any["u",
            di == 0 ? "i" : Dict{String,Any}("op" => "+", "args" => Any[di, "i"]),
            dj == 0 ? "j" : Dict{String,Any}("op" => "+", "args" => Any[dj, "j"])])
        lap = Dict{String,Any}("op" => "+",
            "args" => Any[_nbr(-1, 0), _nbr(1, 0), _nbr(0, -1), _nbr(0, 1)])
        rlap = Dict{String,Int}("i" => 0, "j" => 0); scan!(rlap, lap)
        @test rlap == Dict("i" => 1, "j" => 1)   # both axes bounded ⇒ makearray BC emitted
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
