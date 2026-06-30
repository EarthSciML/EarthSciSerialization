# M2 end-to-end: a discretized level-set PDE consuming a PROMOTED per-cell rate.
# `rate` is authored scalar = f(force[x,y]); promotion makes it rate[x,y]; the
# level-set D(psi,t) = -rate·|grad psi| then spreads at the per-cell rate. Proves
# promote_downstream_shapes + discretize(grad) + index_promoted_refs! compose into
# a spatially-varying front with no per-cell runner logic.
using Test
import EarthSciSerialization as ESS
const E = ESS

op(o,a...) = Dict{String,Any}("op"=>o,"args"=>collect(Any,a))
gradn(u,d) = Dict{String,Any}("op"=>"grad","args"=>Any[u],"dim"=>d)

# centered 2nd-order grad rules (the driver's grad_rules_2d, loop vars i,j).
function grad_rules()
    idx(di,dj) = Dict{String,Any}("op"=>"index","args"=>Any["\$u",
        di==0 ? "i" : op("+","i",di), dj==0 ? "j" : op("+","j",dj)])
    centered(a,b,h) = op("/", op("-",a,b), op("*",2,h))
    # the flattened/namespaced spacing param (the monolithic path discretizes the
    # NAMESPACED level-set, so the grad-rule spacing must name M.dx, not bare dx).
    [Dict{String,Any}("name"=>"gx","pattern"=>Dict{String,Any}("op"=>"grad","args"=>Any["\$u"],"dim"=>"x"),
        "replacement"=>centered(idx(1,0),idx(-1,0),"M.dx")),
     Dict{String,Any}("name"=>"gy","pattern"=>Dict{String,Any}("op"=>"grad","args"=>Any["\$u"],"dim"=>"y"),
        "replacement"=>centered(idx(0,1),idx(0,-1),"M.dx"))]
end

NX, NY = 5, 5
function spatial_esm()
    gm = op("sqrt", op("+", op("^",gradn("psi","x"),2), op("^",gradn("psi","y"),2)))
    Dict{String,Any}("esm"=>"0.5.0","metadata"=>Dict("name"=>"LS"),
      "domains"=>Dict{String,Any}("d"=>Dict{String,Any}(
         "spatial"=>Dict{String,Any}(
            "x"=>Dict{String,Any}("min"=>0,"max"=>NX-1,"grid_spacing"=>1),
            "y"=>Dict{String,Any}("min"=>0,"max"=>NY-1,"grid_spacing"=>1)),
         "temporal"=>Dict{String,Any}("start"=>0,"end"=>1))),
      "models"=>Dict{String,Any}("M"=>Dict{String,Any}(
         "domain"=>"d",
         "variables"=>Dict{String,Any}(
            "force"=>Dict{String,Any}("type"=>"parameter","shape"=>Any["x","y"]),
            "rate" =>Dict{String,Any}("type"=>"observed","expression"=>op("*","force",0.5)),
            "dx"   =>Dict{String,Any}("type"=>"parameter","default"=>1.0),
            "psi"  =>Dict{String,Any}("type"=>"state","shape"=>Any["x","y"])),
         "equations"=>Any[Dict{String,Any}(
            "lhs"=>Dict{String,Any}("op"=>"D","args"=>Any["psi"],"wrt"=>"t"),
            "rhs"=>op("*", op("-",0,"rate"), gm))])))
end

@testset "M2 end-to-end: per-cell promoted rate drives a discretized front" begin
    flat = E.flatten(ESS.coerce_esm_file(ESS.JSON3.read(ESS.JSON3.write(spatial_esm()))))
    prom = E.promote_downstream_shapes(flat)
    @test get(prom.observed_variables, "M.rate", nothing).shape == ["x","y"]   # promoted

    grids = Dict("g"=>Dict{String,Any}("family"=>"cartesian","dimensions"=>Any[
        Dict{String,Any}("name"=>"x","size"=>NX,"periodic"=>false,"spacing"=>"uniform"),
        Dict{String,Any}("name"=>"y","size"=>NY,"periodic"=>false,"spacing"=>"uniform")]))
    disc = E.discretize(prom; grids=grids, rules=grad_rules(), strict_unrewritten=false)
    promoted = E.promoted_array_names(flat, prom)
    E.index_promoted_refs!(disc, promoted)

    # Per-cell forcing: a west→east ramp, so rate (=0.5·force) varies across x.
    force = [Float64(i) for i in 1:NX, _ in 1:NY]          # force[i,j] = i

    f!, u0, p, _t, vmap = E.build_evaluator(disc;
        const_arrays=Dict("M.force"=>force), parameter_overrides=Dict("dx"=>1.0))
    # Seed a signed-distance-ish field so |grad psi|≈1 (a linear ramp in x).
    for i in 1:NX, j in 1:NY
        haskey(vmap, "M.psi[$i,$j]") && (u0[vmap["M.psi[$i,$j]"]] = Float64(i))
    end
    du = similar(u0); f!(du, u0, p, 0.0)
    # interior cell (i,j): grad psi ≈ (1,0), |grad|≈1, so D(psi) ≈ -rate[i,j] = -0.5·i.
    d(i,j) = du[vmap["M.psi[$i,$j]"]]
    println("  D(psi) interior row: ", [round(d(i,3);digits=3) for i in 2:NX-1])
    @test d(2,3) < 0 && d(4,3) < 0
    @test abs(d(4,3)) > abs(d(2,3)) + 1e-6        # faster where rate (force) is larger
    @test isapprox(d(2,3), -0.5*2; atol=0.2)      # ≈ -rate[2] = -1.0
    @test isapprox(d(4,3), -0.5*4; atol=0.2)      # ≈ -rate[4] = -2.0
    println("  ✓ promoted per-cell rate drives the front faster downwind (spatially varying)")
end
