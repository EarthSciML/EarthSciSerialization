# Allocation tests for the tree-walk PDE RHS (ess-9cc).
#
# The codebase's FIRST allocation test. It pins the hard property that the
# in-place RHS `f!(du, u, p, t)` built by `build_evaluator` allocates NOTHING per
# call in steady state — at two+ grid sizes, so the property is N-independent
# (no per-cell allocation hiding behind a small absolute number). This guards the
# zero-allocation discipline of the vectorized array-kernel runner (ess-dhq +
# ess-9cc): `@views`/gather slices, preallocated per-node scratch buffers, fused
# in-place broadcasts, in-place semiring folds, and an explicit `du` scatter
# (never `du[slots] .= …`, whose `dotview` allocates a SubArray).
#
# Reuses the `zero_alloc_harness.jl` helpers — `built_rhs_alloc_bytes(model;…)`
# and `rhs_alloc_bytes(f!,du,u0,p,t)` — which any future evaluator work can call.

using Test
using EarthSciSerialization

include("zero_alloc_harness.jl")

const ESM = EarthSciSerialization

# ---- builder helpers (mirror tree_walk_vectorized_test.jl) ----
_n(x)  = NumExpr(Float64(x))
_i(x)  = IntExpr(Int64(x))
_v(n)  = VarExpr(String(n))
_op(o, a...; k...) = OpExpr(String(o), ESM.Expr[a...]; k...)
_idx(v, is...)  = _op("index", _v(v), is...)
_Didx(v, is...) = _op("D", _idx(v, is...); wrt="t")
_ao1(body, idx, lo, hi) = OpExpr("arrayop", ESM.Expr[];
    output_idx=Any[idx], expr_body=body, ranges=Dict(idx => [lo, hi]))

# 1-D second-difference stencil over the FULL range (end cells gather an
# out-of-range ghost → their own boundary kernels): exercises GATHER + the
# elementwise `+`/`*`/literal OP arms + the interior/boundary kernel split.
function _stencil_model(N)
    vars = Dict("u" => ModelVariable(StateVariable))
    body = _op("+",
        _idx("u", _op("-", _v("i"), _i(1))),
        _op("*", _n(-2.0), _idx("u", _v("i"))),
        _idx("u", _op("+", _v("i"), _i(1))))
    ESM.Model(vars, [ESM.Equation(_ao1(_Didx("u", _v("i")), "i", 1, N),
                                  _ao1(body, "i", 1, N))])
end

# D(y[i]) = Σ_{k=1..M} A[i,k]·x[k] (sum_product) — exercises the VK_REDUCE axis
# fold + CONSTVEC (A[i,k]) + GATHER (x[k]).
function _contraction_model(M)
    vars = Dict("y" => ModelVariable(StateVariable),
                "x" => ModelVariable(StateVariable))
    body = _op("*", _idx("A", _v("i"), _v("k")), _idx("x", _v("k")))
    rhs = OpExpr("arrayop", ESM.Expr[]; output_idx=Any["i"], expr_body=body,
                 ranges=Dict("i" => [1, 2], "k" => [1, M]), reduce="+")
    ESM.Model(vars, [ESM.Equation(_ao1(_Didx("y", _v("i")), "i", 1, 2), rhs)])
end

# 1-D periodic centered-advection document: discretizes to an arrayop whose RHS
# is (u[i+1]-u[i-1])/(2·dx) — exercises PARAM (dx) + the `/` and `-` OP arms in a
# REALISTIC parse→discretize→build_evaluator pipeline.
function _advection_esm(n)
    dx = 1.0 / n
    Dict{String,Any}(
        "esm" => "0.4.0",
        "metadata" => Dict{String,Any}("name" => "advection_1d_alloc"),
        "grids" => Dict{String,Any}("gx" => Dict{String,Any}(
            "family" => "cartesian",
            "dimensions" => Any[Dict{String,Any}(
                "name" => "i", "size" => n, "periodic" => true, "spacing" => "uniform")])),
        "rules" => Any[Dict{String,Any}(
            "name" => "centered_grad",
            "pattern" => Dict{String,Any}("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
            "replacement" => Dict{String,Any}("op" => "/", "args" => Any[
                Dict{String,Any}("op" => "-", "args" => Any[
                    Dict{String,Any}("op" => "index", "args" => Any[
                        "\$u", Dict{String,Any}("op" => "+", "args" => Any["\$x", 1])]),
                    Dict{String,Any}("op" => "index", "args" => Any[
                        "\$u", Dict{String,Any}("op" => "-", "args" => Any["\$x", 1])])]),
                Dict{String,Any}("op" => "*", "args" => Any[2, "dx"])]))],
        "models" => Dict{String,Any}("M" => Dict{String,Any}(
            "grid" => "gx",
            "variables" => Dict{String,Any}(
                "u" => Dict{String,Any}("type" => "state", "default" => 0.0,
                    "units" => "1", "shape" => Any["i"], "location" => "cell_center"),
                "dx" => Dict{String,Any}("type" => "parameter", "default" => dx, "units" => "1")),
            "equations" => Any[Dict{String,Any}(
                "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                "rhs" => Dict{String,Any}("op" => "grad", "args" => Any["u"], "dim" => "i"))])))
end

@testset "tree_walk PDE RHS is allocation-free (ess-9cc)" begin

    @testset "vectorized stencil RHS: 0 bytes, N-independent" begin
        # Two+ grid sizes — the steady-state allocation must be EXACTLY 0 at every
        # size (a per-cell leak would grow the byte count with N).
        for N in (64, 256, 1024)
            ics = Dict("u[$k]" => sin(0.3k) + 0.1k for k in 1:N)
            @test built_rhs_alloc_bytes(_stencil_model(N); initial_conditions=ics) == 0
        end
    end

    @testset "vectorized reduction (sum_product) RHS: 0 bytes" begin
        for M in (3, 16, 64)
            A = reshape(collect(1.0:(2.0 * M)), 2, M)
            ics = Dict{String,Float64}("y[1]" => 0.0, "y[2]" => 0.0)
            for k in 1:M
                ics["x[$k]"] = 0.5k
            end
            @test built_rhs_alloc_bytes(_contraction_model(M);
                initial_conditions=ics, const_arrays=Dict("A" => A)) == 0
        end
    end

    @testset "discretized advection RHS (param + division): 0 bytes" begin
        for n in (8, 32, 128)
            disc = discretize(_advection_esm(n); lift_1d_arrayop=true)
            f!, u0, p, _tspan, vmap = build_evaluator(disc)
            dx = 1.0 / n
            for i in 1:n
                u0[vmap["u[$i]"]] = sin(2π * (i - 0.5) * dx)
            end
            du = similar(u0)
            @test rhs_alloc_bytes(f!, du, u0, p, 0.0) == 0
        end
    end

    @testset "scalar contraction :+ fold is allocation-free (line fix)" begin
        # Directly pin the scalar `_eval_contraction` `:+` arm (the old
        # `@tullio s = …` site, ~80 B/reduced cell): a hand-built
        # `_NK_CONTRACTION` node summed via `_eval_node` must be 0-alloc and
        # equal to the seeded fold, bit-identical to the prior Tullio sum.
        u = collect(1.0:6.0)
        p = (;)
        kids = ESM._Node[ESM._mknode(kind=ESM._NK_STATE, idx=k) for k in 1:6]
        cnode = ESM._mknode(kind=ESM._NK_CONTRACTION, op=:+, literal=0.0, children=kids)
        ESM._eval_node(cnode, u, p, 0.0)             # warmup/compile
        @test ESM._eval_node(cnode, u, p, 0.0) == sum(u)
        @test (@allocated ESM._eval_node(cnode, u, p, 0.0)) == 0
    end
end
