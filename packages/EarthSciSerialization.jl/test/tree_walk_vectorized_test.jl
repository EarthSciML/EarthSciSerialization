# Vectorized array-kernel RHS property tests (ess-dhq).
#
# Verifies that the tree-walk runner evaluates discretized `arrayop` derivative
# equations as WHOLE-ARRAY kernels whose compiled-node count is independent of
# the grid size N (no per-cell scalarization), while preserving numeric results
# identical to the analytic stencil/reduction.
#
# Property under test (the "no scalarization" hard requirement): for the same
# equation at different grid sizes, the number of compiled array kernels and the
# total number of `_VecNode`s are EQUAL — only the embedded slot/value vectors
# grow with N. Contrast the previous behaviour, where the compiled RHS held one
# scalar `_Node` per cell (an O(N) node list).

using Test
using EarthSciSerialization

const ESM = EarthSciSerialization

# ---- builder helpers (mirror tree_walk_arrayop_test.jl) ----
_n(x)  = NumExpr(Float64(x))
_i(x)  = IntExpr(Int64(x))
_v(n)  = VarExpr(String(n))
_op(o, a...; k...) = OpExpr(String(o), ESM.Expr[a...]; k...)
_idx(v, is...)  = _op("index", _v(v), is...)
_Didx(v, is...) = _op("D", _idx(v, is...); wrt="t")
_ao1(body, idx, lo, hi) = OpExpr("arrayop", ESM.Expr[];
    output_idx=Any[idx], expr_body=body, ranges=Dict(idx => [lo, hi]))

# 1-D second-difference stencil arrayop over the FULL range, so the two end
# cells gather an out-of-range (ghost) neighbour and form their own boundary
# kernels — the canonical "interior kernel + boundary kernels" decomposition.
function _stencil_model(N)
    vars = Dict("u" => ModelVariable(StateVariable))
    body = _op("+",
        _idx("u", _op("-", _v("i"), _i(1))),
        _op("*", _n(-2.0), _idx("u", _v("i"))),
        _idx("u", _op("+", _v("i"), _i(1))))
    ESM.Model(vars, [ESM.Equation(_ao1(_Didx("u", _v("i")), "i", 1, N),
                                  _ao1(body, "i", 1, N))])
end

@testset "tree_walk vectorized array-kernel RHS (ess-dhq)" begin

    @testset "N-independent compiled-kernel count (two+ grid sizes)" begin
        diags = map((8, 16, 64)) do N
            ics = Dict("u[$k]" => 0.0 for k in 1:N)
            _, u0, _, _, _, d = ESM._build_evaluator_impl(_stencil_model(N);
                                                          initial_conditions=ics)
            @test length(u0) == N                 # state DOES grow with N …
            d
        end
        # … but the compiled array-kernel structure does NOT.
        @test diags[1].n_vec_kernels == diags[2].n_vec_kernels == diags[3].n_vec_kernels
        @test diags[1].template_node_count ==
              diags[2].template_node_count == diags[3].template_node_count
        @test diags[1].n_vec_kernels >= 1
        # The array equation produced ZERO per-cell scalar RHS entries: it is a
        # whole-array kernel, not an O(N) scalar node list.
        @test all(d -> d.n_scalar_entries == 0, diags)
    end

    @testset "numeric identity vs analytic stencil (rtol 1e-12)" begin
        for N in (8, 32)
            ics = Dict("u[$k]" => sin(0.3k) + 0.1k for k in 1:N)
            f!, u0, p, _, vmap = build_evaluator(_stencil_model(N);
                                                 initial_conditions=ics)
            du = similar(u0); f!(du, u0, p, 0.0)
            uv(k) = (1 <= k <= N) ? (sin(0.3k) + 0.1k) : 0.0   # ghost → 0
            for i in 1:N
                expected = uv(i - 1) - 2 * uv(i) + uv(i + 1)
                @test isapprox(du[vmap["u[$i]"]], expected; rtol=1e-12, atol=1e-12)
            end
        end
    end

    @testset "contraction (reduction) arrayop vectorizes + stays correct" begin
        # D(y[i]) = Σ_{k=1..3} A[i,k]·x[k]  (sum_product semiring)
        vars = Dict("y" => ModelVariable(StateVariable),
                    "x" => ModelVariable(StateVariable))
        body = _op("*", _idx("A", _v("i"), _v("k")), _idx("x", _v("k")))
        rhs = OpExpr("arrayop", ESM.Expr[]; output_idx=Any["i"], expr_body=body,
                     ranges=Dict("i" => [1, 2], "k" => [1, 3]), reduce="+")
        m = ESM.Model(vars, [ESM.Equation(_ao1(_Didx("y", _v("i")), "i", 1, 2), rhs)])
        A = [1.0 2.0 3.0; 4.0 5.0 6.0]
        ics = Dict("y[1]" => 0.0, "y[2]" => 0.0,
                   "x[1]" => 1.0, "x[2]" => 1.0, "x[3]" => 1.0)
        f!, u0, p, _, vmap = build_evaluator(m; initial_conditions=ics,
                                             const_arrays=Dict("A" => A))
        _, _, _, _, _, d = ESM._build_evaluator_impl(m; initial_conditions=ics,
                                                     const_arrays=Dict("A" => A))
        @test d.n_vec_kernels >= 1
        @test d.n_scalar_entries == 0
        du = similar(u0); f!(du, u0, p, 0.0)
        @test isapprox(du[vmap["y[1]"]], 6.0;  rtol=1e-12)
        @test isapprox(du[vmap["y[2]"]], 15.0; rtol=1e-12)
    end
end
