# Slice-derived surface source lowers to flux BC (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/real_mtk_integration_test.jl`

```julia
# Spec §4.7.6.13 Example B: 1D vertical diffusion + 0D surface
        # deposition coupled via a slice interface at z=0. The Julia
        # extension is required to lower the slice-ODE to a flux BC on the
        # diffusive PDE at z=0.
        ivs = Symbol[:t, :z]
        svars = OrderedDict{String, ModelVariable}(
            "VertDiff.C" => ModelVariable(StateVariable; default=1.0),
            "VertDiff.C.at_z" => ModelVariable(StateVariable; default=1.0),
        )
        ps = OrderedDict{String, ModelVariable}(
            "VertDiff.D" => ModelVariable(ParameterVariable; default=0.1),
            "SurfaceDep.v_dep" => ModelVariable(ParameterVariable; default=0.01),
        )
        obs = OrderedDict{String, ModelVariable}()

        # dC/dt = D * grad(grad(C, z), z)
        diff_eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("VertDiff.C")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("VertDiff.D"),
                OpExpr("grad", EarthSciSerialization.Expr[
                    OpExpr("grad", EarthSciSerialization.Expr[VarExpr("VertDiff.C")], dim="z"),
                ], dim="z"),
            ]),
        )
        # dC.at_z/dt = -v_dep * C.at_z   (slice-ODE — surface deposition)
        slice_eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("VertDiff.C.at_z")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                OpExpr("-", EarthSciSerialization.Expr[VarExpr("SurfaceDep.v_dep")]),
                VarExpr("VertDiff.C.at_z"),
            ]),
        )

        flat = FlattenedSystem(ivs, svars, ps, obs, [diff_eq, slice_eq],
            ContinuousEvent[], DiscreteEvent[],
            Domain(spatial=Dict{String,Any}("z" => [0.0, 1000.0])),
            FlattenMetadata())

        pde = ModelingToolkit.PDESystem(flat; name=:VertDep)
        @test !(pde isa MockPDESystem)
        @test occursin("PDESystem", string(typeof(pde)))
        @test length(pde.bcs) >= 1
        # The BC string should contain a z-derivative and reference the
        # deposition velocity — i.e. the slice-ODE rewritten as a flux BC
        # with the slice variable substituted by the base variable.
        bc_strs = [string(bc) for bc in pde.bcs]
        # Derivative w.r.t. z must appear. Symbolics r
```

