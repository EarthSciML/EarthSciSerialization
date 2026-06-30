# M2-1: promote_downstream_shapes — a scalar physics chain fed by an array source
# is promoted to the array shape, its equations rewritten to arrayops, and a real
# reduction (aggregate) stays a promotion BOUNDARY (scalar). Evaluates per-cell.
using Test
import EarthSciSerialization as ESS
const E = ESS

op(o, a...) = Dict{String,Any}("op"=>o, "args"=>collect(Any, a))
ix(a...)    = Dict{String,Any}("op"=>"index", "args"=>collect(Any, a))

# index set c (size 3); f[c] array param; a=f*2, b=a+f scalar-authored; s = Σ_c b.
function syn()
    agg = Dict{String,Any}("op"=>"aggregate","semiring"=>"sum_product","output_idx"=>Any[],
        "ranges"=>Dict{String,Any}("k"=>Dict{String,Any}("from"=>"c")),
        "args"=>Any[], "expr"=>ix("b","k"))
    Dict{String,Any}("esm"=>"0.5.0","metadata"=>Dict("name"=>"P"),
      "models"=>Dict{String,Any}("M"=>Dict{String,Any}(
        "index_sets"=>Dict{String,Any}("c"=>Dict{String,Any}("kind"=>"interval","size"=>3)),
        "variables"=>Dict{String,Any}(
            "f"=>Dict{String,Any}("type"=>"parameter","shape"=>Any["c"]),
            "a"=>Dict{String,Any}("type"=>"observed","expression"=>op("*","f",2)),
            "b"=>Dict{String,Any}("type"=>"observed","expression"=>op("+","a","f")),
            "s"=>Dict{String,Any}("type"=>"state")),
        "equations"=>Any[Dict{String,Any}(
            "lhs"=>Dict{String,Any}("op"=>"D","args"=>Any["s"],"wrt"=>"t"),"rhs"=>agg)])))
end

@testset "M2-1: promote_downstream_shapes" begin
    flat = E.flatten(ESS.coerce_esm_file(ESS.JSON3.read(ESS.JSON3.write(syn()))))
    prom = E.promote_downstream_shapes(flat)

    @testset "shape inference: scalar chain promoted, reduction stays scalar" begin
        sh(n) = (v = get(prom.observed_variables, n, get(prom.state_variables, n, nothing));
                 v === nothing ? :absent : (v.shape === nothing ? String[] : v.shape))
        @test sh("M.a") == ["M.c"]            # promoted (downstream of array f)
        @test sh("M.b") == ["M.c"]            # promoted
        @test sh("M.s") == String[]           # reduction boundary — stays scalar
    end

    @testset "equations rewritten to arrayops; evaluates per-cell" begin
        doc = E.flattened_to_esm(prom)
        f!, u0, p, _t, vmap = E.build_evaluator(doc;
            const_arrays=Dict("M.f"=>[1.0,2.0,3.0]), initial_conditions=Dict("M.s"=>0.0))
        du = similar(u0); f!(du, u0, p, 0.0)
        # f=[1,2,3] → a=[2,4,6], b=[3,6,9], s=Σb=18
        @test du[vmap["M.s"]] ≈ 18.0
        println("  D(M.s) = ", du[vmap["M.s"]], "  (expected 18 = Σ(2a... b=a+f))")
    end

    @testset "transform is a no-op for an all-scalar system" begin
        sc = Dict{String,Any}("esm"=>"0.5.0","metadata"=>Dict("name"=>"S"),
            "models"=>Dict{String,Any}("M"=>Dict{String,Any}("variables"=>Dict{String,Any}(
                "x"=>Dict{String,Any}("type"=>"parameter","default"=>2.0),
                "y"=>Dict{String,Any}("type"=>"observed","expression"=>op("*","x",3)),
                "z"=>Dict{String,Any}("type"=>"state")),
              "equations"=>Any[Dict{String,Any}("lhs"=>Dict{String,Any}("op"=>"D","args"=>Any["z"],"wrt"=>"t"),"rhs"=>"y")])))
        f2 = E.flatten(ESS.coerce_esm_file(ESS.JSON3.read(ESS.JSON3.write(sc))))
        p2 = E.promote_downstream_shapes(f2)
        @test all(v -> v.shape === nothing || isempty(v.shape), values(p2.observed_variables))
        f!, u0, p, _t, vmap = E.build_evaluator(E.flattened_to_esm(p2); initial_conditions=Dict("M.z"=>0.0))
        du = similar(u0); f!(du, u0, p, 0.0)
        @test du[vmap["M.z"]] ≈ 6.0           # y = x*3 = 6, unchanged
    end

    @testset "algebraic_states_to_observeds reclassifies bare-eq states" begin
        # `a` is a STATE defined by a bare algebraic eq (a = x*2); `z` is a real ODE
        # state (D(z,t)=a). Reclassify `a` → observed; leave `z` a state.
        d = Dict{String,Any}("esm"=>"0.5.0","metadata"=>Dict("name"=>"S"),
            "models"=>Dict{String,Any}("M"=>Dict{String,Any}("variables"=>Dict{String,Any}(
                "x"=>Dict{String,Any}("type"=>"parameter","default"=>3.0),
                "a"=>Dict{String,Any}("type"=>"state"),
                "z"=>Dict{String,Any}("type"=>"state")),
              "equations"=>Any[
                Dict{String,Any}("lhs"=>"a","rhs"=>op("*","x",2)),
                Dict{String,Any}("lhs"=>Dict{String,Any}("op"=>"D","args"=>Any["z"],"wrt"=>"t"),"rhs"=>"a")])))
        flat = E.flatten(ESS.coerce_esm_file(ESS.JSON3.read(ESS.JSON3.write(d))))
        norm = E.algebraic_states_to_observeds(flat)
        @test haskey(norm.observed_variables, "M.a")    # algebraic state → observed
        @test !haskey(norm.state_variables, "M.a")
        @test haskey(norm.state_variables, "M.z")        # ODE state preserved
        # runs: a = x*2 = 6, D(z) = a = 6
        f!, u0, p, _t, vmap = E.build_evaluator(E.flattened_to_esm(norm); initial_conditions=Dict("M.z"=>0.0))
        du = similar(u0); f!(du, u0, p, 0.0)
        @test du[vmap["M.z"]] ≈ 6.0
    end
end
