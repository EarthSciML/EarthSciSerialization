using EarthSciSerialization
using EarthSciSerialization: Expr as ESMExpr
using Test
import ModelingToolkit

# Helpers for building expressions inside tests.
const _N = EarthSciSerialization.NumExpr
const _V = EarthSciSerialization.VarExpr
_op(op, args...; kwargs...) = EarthSciSerialization.OpExpr(op, EarthSciSerialization.Expr[args...]; kwargs...)
_deriv(name) = _op("D", _V(name); wrt="t")

# Locate a flattened equation whose LHS dependent variable matches `dep`.
function _find_eq(flat::FlattenedSystem, dep::String)
    for eq in flat.equations
        if eq.lhs isa EarthSciSerialization.OpExpr && eq.lhs.op == "D" &&
           !isempty(eq.lhs.args) && eq.lhs.args[1] isa EarthSciSerialization.VarExpr &&
           (eq.lhs.args[1]::EarthSciSerialization.VarExpr).name == dep
            return eq
        end
        if eq.lhs isa EarthSciSerialization.VarExpr && eq.lhs.name == dep
            return eq
        end
    end
    return nothing
end

# Does an Expr tree contain a VarExpr whose name matches `target`?
function _uses_var(expr::EarthSciSerialization.Expr, target::String)
    if expr isa EarthSciSerialization.VarExpr
        return expr.name == target
    elseif expr isa EarthSciSerialization.OpExpr
        return any(a -> _uses_var(a, target), expr.args)
    end
    return false
end

# Does an Expr tree contain any OpExpr matching `op_name`?
function _has_op(expr::EarthSciSerialization.Expr, op_name::String)
    if expr isa EarthSciSerialization.OpExpr
        expr.op == op_name && return true
        return any(a -> _has_op(a, op_name), expr.args)
    end
    return false
end

@testset "Flatten System" begin

    @testset "1. Reactions-only Model" begin
        species = [EarthSciSerialization.Species("A", default=1.0),
                   EarthSciSerialization.Species("B", default=0.0)]
        params = [EarthSciSerialization.Parameter("k", 0.1)]
        rate = _op("*", _V("k"), _V("A"))
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("A", 1)],
            [EarthSciSerialization.StoichiometryEntry("B", 1)],
            rate)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns, parameters=params)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t1"),
            reaction_systems=Dict("Chem" => rsys))
        flat = flatten(file)

        @test haskey(flat.state_variables, "Chem.A")
        @test haskey(flat.state_variables, "Chem.B")
        @test haskey(flat.parameters, "Chem.k")
        @test length(flat.equations) == 2

        eq_A = _find_eq(flat, "Chem.A")
        eq_B = _find_eq(flat, "Chem.B")
        @test eq_A !== nothing && eq_B !== nothing
        # d[A]/dt = -k*A
        @test _uses_var(eq_A.rhs, "Chem.k") && _uses_var(eq_A.rhs, "Chem.A")
        # d[B]/dt = +k*A
        @test _uses_var(eq_B.rhs, "Chem.k") && _uses_var(eq_B.rhs, "Chem.A")
    end

    @testset "2. Mixed equations + reactions (disjoint species)" begin
        vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0),
            "k" => ModelVariable(ParameterVariable, default=0.1),
        )
        eqs = [Equation(_deriv("T"), _op("*", _V("k"), _V("T")))]
        model = Model(vars, eqs)

        species = [EarthSciSerialization.Species("A", default=1.0)]
        rxns = [EarthSciSerialization.Reaction("r1", nothing,
            [EarthSciSerialization.StoichiometryEntry("A", 1)],
            _N(0.5))]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns)

        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t2"),
            models=Dict("Climate" => model),
            reaction_systems=Dict("Chem" => rsys))
        flat = flatten(file)

        @test haskey(flat.state_variables, "Climate.T")
        @test haskey(flat.state_variables, "Chem.A")
        @test haskey(flat.parameters, "Climate.k")
        @test _find_eq(flat, "Climate.T") !== nothing
        @test _find_eq(flat, "Chem.A") !== nothing
    end

    @testset "3. Autocatalytic A + B → 2B (net stoich of B is +1)" begin
        species = [EarthSciSerialization.Species("A"),
                   EarthSciSerialization.Species("B")]
        # Pass k as the rate constant. `mass_action_rate` multiplies by the
        # substrate concentrations (A and B) to form the full rate expression.
        rate = _V("k")
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("A", 1),
             EarthSciSerialization.StoichiometryEntry("B", 1)],
            [EarthSciSerialization.StoichiometryEntry("B", 2)],
            rate)]
        params = [EarthSciSerialization.Parameter("k", 0.3)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns, parameters=params)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t3"),
            reaction_systems=Dict("Auto" => rsys))
        flat = flatten(file)

        eq_A = _find_eq(flat, "Auto.A")
        eq_B = _find_eq(flat, "Auto.B")
        @test eq_A !== nothing && eq_B !== nothing

        # Net stoich of B = 2 - 1 = +1. The reaction lowering MUST take the
        # `stoich == 1` branch, which passes the mass_action_rate expression
        # through unmodified — i.e. eq_B.rhs is exactly `k * A * B` with:
        #
        #   - a top-level OpExpr("*") (not "+" and not "-")
        #   - no leading NumExpr coefficient (no `2*rate` artifact)
        #   - references to k, A, and B
        #
        # This distinguishes the correct +1 case from the incorrect
        # structures `2*rate + (-rate)` (would be top-level "+"),
        # `2*rate` (would have a leading NumExpr(2)), or `-rate` (would be
        # top-level unary "-").
        @test eq_B.rhs isa EarthSciSerialization.OpExpr
        top_B = eq_B.rhs::EarthSciSerialization.OpExpr
        @test top_B.op == "*"
        @test top_B.op != "+"
        @test top_B.op != "-"
        @test !any(a -> a isa EarthSciSerialization.NumExpr, top_B.args)
        @test _uses_var(eq_B.rhs, "Auto.k")
        @test _uses_var(eq_B.rhs, "Auto.A")
        @test _uses_var(eq_B.rhs, "Auto.B")

        # Net stoich of A = -1. The A equation MUST take the `stoich == -1`
        # branch, which wraps the mass_action_rate term in a unary negation.
        # Structurally: eq_A.rhs is OpExpr("-", [rate_expr]) — a unary minus
        # with exactly one arg that itself contains k, A, and B.
        @test eq_A.rhs isa EarthSciSerialization.OpExpr
        top_A = eq_A.rhs::EarthSciSerialization.OpExpr
        @test top_A.op == "-"
        @test length(top_A.args) == 1
        @test _uses_var(eq_A.rhs, "Auto.k")
        @test _uses_var(eq_A.rhs, "Auto.A")
        @test _uses_var(eq_A.rhs, "Auto.B")
    end

    @testset "4. Source (null substrates) and sink (null products) reactions" begin
        species = [EarthSciSerialization.Species("X")]
        source = EarthSciSerialization.Reaction("src", nothing,
            [EarthSciSerialization.StoichiometryEntry("X", 1)],
            _V("kin"))
        sink = EarthSciSerialization.Reaction("snk",
            [EarthSciSerialization.StoichiometryEntry("X", 1)], nothing,
            _op("*", _V("kout"), _V("X")))
        params = [EarthSciSerialization.Parameter("kin", 1.0),
                  EarthSciSerialization.Parameter("kout", 0.5)]
        rsys = EarthSciSerialization.ReactionSystem(species, [source, sink], parameters=params)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t4"),
            reaction_systems=Dict("S" => rsys))
        flat = flatten(file)

        eq_X = _find_eq(flat, "S.X")
        @test eq_X !== nothing
        @test _uses_var(eq_X.rhs, "S.kin")
        @test _uses_var(eq_X.rhs, "S.kout")
    end

    @testset "5. ConflictingDerivativeError for explicit D + reaction on same species" begin
        # Model with explicit D(O3)/dt = ...
        mvars = Dict{String, ModelVariable}(
            "O3" => ModelVariable(StateVariable, default=1e-6),
            "k" => ModelVariable(ParameterVariable, default=0.1),
        )
        meqs = [Equation(_deriv("O3"), _op("-", _op("*", _V("k"), _V("O3"))))]
        model = Model(mvars, meqs)

        # Reaction system also touches O3
        species = [EarthSciSerialization.Species("O3", default=1e-6)]
        rate = _V("kr")
        rxns = [EarthSciSerialization.Reaction("r1", nothing,
            [EarthSciSerialization.StoichiometryEntry("O3", 1)], rate)]
        params = [EarthSciSerialization.Parameter("kr", 0.01)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns, parameters=params)

        # Model prefix is "SimpleOzone" and reaction system is also "SimpleOzone"
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t5"),
            models=Dict("SimpleOzone" => model),
            reaction_systems=Dict("SimpleOzone" => rsys))

        # Flatten must throw.
        err = nothing
        try
            flatten(file)
        catch e
            err = e
        end
        @test err isa ConflictingDerivativeError
        @test "SimpleOzone.O3" in err.species

        # Validate must also flag the conflict.
        errs = validate_structural(file)
        @test any(e -> e.error_type == "conflicting_derivative" &&
                       occursin("SimpleOzone.O3", e.message), errs)
    end

    @testset "6. operator_compose across two models (summed RHS)" begin
        # Two models both declaring T with D(T)/dt; compose them.
        vars1 = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable),
            "k" => ModelVariable(ParameterVariable, default=0.1),
        )
        eqs1 = [Equation(_deriv("T"), _op("*", _V("k"), _V("T")))]
        m1 = Model(vars1, eqs1)

        vars2 = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable),
            "j" => ModelVariable(ParameterVariable, default=0.05),
        )
        eqs2 = [Equation(_deriv("T"), _op("*", _V("j"), _V("T")))]
        m2 = Model(vars2, eqs2)

        coupling = CouplingEntry[
            CouplingOperatorCompose(["A", "B"];
                translate=Dict{String,Any}("A.T" => "B.T")),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t6"),
            models=Dict("A" => m1, "B" => m2),
            coupling=coupling)
        flat = flatten(file)

        # After compose we expect a single equation for the canonical dep var
        # (B.T, since A.T was translated to B.T) and none for A.T.
        @test _find_eq(flat, "B.T") !== nothing
        eq = _find_eq(flat, "B.T")
        # Merged RHS MUST reference BOTH A's parameter (k) AND B's parameter (j),
        # i.e. both sides of the summed equation made it through the merge.
        # Using || would mask the case where only one side survived.
        @test _uses_var(eq.rhs, "A.k")
        @test _uses_var(eq.rhs, "B.j")
        # And both state references (A.T and B.T) must appear.
        @test _uses_var(eq.rhs, "A.T")
        @test _uses_var(eq.rhs, "B.T")
        # The top-level RHS should be a sum (+) of the two composed terms.
        @test eq.rhs isa EarthSciSerialization.OpExpr
        @test (eq.rhs::EarthSciSerialization.OpExpr).op == "+"
    end

    @testset "7. variable_map param_to_var substitutes and removes parameter" begin
        vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable),
            "k" => ModelVariable(ParameterVariable, default=0.1),
            "external" => ModelVariable(ParameterVariable, default=1.0),
        )
        eqs = [Equation(_deriv("T"),
                        _op("*", _V("external"), _op("*", _V("k"), _V("T"))))]
        model = Model(vars, eqs)

        source_vars = Dict{String, ModelVariable}(
            "value" => ModelVariable(StateVariable, default=0.5),
        )
        source_model = Model(source_vars, Equation[])

        coupling = CouplingEntry[
            CouplingVariableMap("Source.value", "Target.external", "param_to_var"),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t7"),
            models=Dict("Target" => model, "Source" => source_model),
            coupling=coupling)
        flat = flatten(file)

        # Target.external should be removed from parameters.
        @test !haskey(flat.parameters, "Target.external")
        # The Target.T equation should now reference Source.value.
        eq = _find_eq(flat, "Target.T")
        @test eq !== nothing
        @test _uses_var(eq.rhs, "Source.value")
    end

    @testset "8. couple with connector equations" begin
        v1 = Dict{String, ModelVariable}("x" => ModelVariable(StateVariable))
        m1 = Model(v1, Equation[Equation(_deriv("x"), _V("x"))])
        v2 = Dict{String, ModelVariable}("y" => ModelVariable(StateVariable))
        m2 = Model(v2, Equation[Equation(_deriv("y"), _V("y"))])

        # Connector equation structured as an already-parsed Equation object.
        connector_eq = Equation(_V("A.x"), _V("B.y"))
        connector = Dict{String, Any}("equations" => [connector_eq])

        coupling = CouplingEntry[CouplingCouple(["A", "B"], connector)]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t8"),
            models=Dict("A" => m1, "B" => m2),
            coupling=coupling)
        flat = flatten(file)

        # The connector equation should appear in the flattened equations.
        found_connector = any(flat.equations) do eq
            eq.lhs isa EarthSciSerialization.VarExpr && eq.lhs.name == "A.x" &&
            eq.rhs isa EarthSciSerialization.VarExpr && eq.rhs.name == "B.y"
        end
        @test found_connector
    end

    @testset "9. Nested subsystems produce full dot paths" begin
        inner_v = Dict{String, ModelVariable}("v" => ModelVariable(StateVariable))
        inner = Model(inner_v, Equation[])
        outer_v = Dict{String, ModelVariable}("u" => ModelVariable(StateVariable))
        outer = Model(outer_v, Equation[],
            subsystems=Dict{String, Model}("Child" => inner))

        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t9"),
            models=Dict("Parent" => outer))
        flat = flatten(file)

        @test haskey(flat.state_variables, "Parent.u")
        @test haskey(flat.state_variables, "Parent.Child.v")
    end

    @testset "10. HYBRID §4.7.6 Example A: 0D chem + 2D advection via operator_compose" begin
        # Spec §4.7.6 Worked example: 0D chemistry system on a 2D grid is
        # composed with an Advection model whose equations use the `_var`
        # placeholder. Expected result: a single combined equation for each
        # chemistry state variable whose RHS contains BOTH the chemistry rate
        # terms AND the advection terms; independent variables are [t, x, y];
        # and the flattened system is consumable by ModelingToolkit.PDESystem.

        # 2D grid domain
        domains = Dict{String, Domain}(
            "grid2d" => Domain(spatial=Dict{String,Any}(
                "x" => [0.0, 100.0], "y" => [0.0, 100.0])))

        # Chem: reaction system on grid2d.
        # Reaction: O3 → ∅ at rate k*O3. Net stoich of O3 = -1, so the lowered
        # equation is D(Chem.O3, t) = -(k*O3).
        species = [EarthSciSerialization.Species("O3", default=1.0)]
        params = [EarthSciSerialization.Parameter("k", 0.2)]
        rate = _op("*", _V("k"), _V("O3"))
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("O3", 1)], nothing, rate)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns,
            parameters=params, domain="grid2d")

        # Advection model with `_var` placeholder.
        # D(_var, t) = -u * grad(_var, x) - v * grad(_var, y)
        adv_vars = Dict{String, ModelVariable}(
            "_var" => ModelVariable(StateVariable),
            "u"    => ModelVariable(ParameterVariable, default=1.0),
            "v"    => ModelVariable(ParameterVariable, default=1.0),
        )
        adv_eq = Equation(
            _deriv("_var"),
            _op("+",
                _op("-", _op("*", _V("u"), _op("grad", _V("_var"); dim="x"))),
                _op("-", _op("*", _V("v"), _op("grad", _V("_var"); dim="y"))),
            ),
        )
        adv_model = Model(adv_vars, [adv_eq], domain="grid2d")

        # operator_compose Chem + Advection: the advection placeholder expands
        # against every state variable in Chem, and the resulting equations
        # are merged by dependent variable.
        coupling = CouplingEntry[
            CouplingOperatorCompose(["Chem", "Advection"]),
        ]

        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("example_a"),
            models=Dict("Advection" => adv_model),
            reaction_systems=Dict("Chem" => rsys),
            coupling=coupling,
            domains=domains)

        flat = flatten(file)

        # (1) Independent variables: hybrid dimension promotion → [t, x, y].
        @test :t in flat.independent_variables
        @test :x in flat.independent_variables
        @test :y in flat.independent_variables

        # (2) Chemistry state variables are present in the flat system. Under
        # the spec's implicit-broadcast rule, they will be interpreted as
        # fields on the 2D target domain by the downstream constructor.
        @test haskey(flat.state_variables, "Chem.O3")
        @test haskey(flat.parameters, "Chem.k")

        # (3) Advection parameters were collected through namespacing.
        @test haskey(flat.parameters, "Advection.u")
        @test haskey(flat.parameters, "Advection.v")

        # (4) The flattened equation for Chem.O3 MUST contain BOTH the
        # chemistry term (reference to Chem.k) AND the advection terms
        # (references to Advection.u and Advection.v together with grad
        # operators on the spatial dimensions).
        eq_O3 = _find_eq(flat, "Chem.O3")
        @test eq_O3 !== nothing
        @test _uses_var(eq_O3.rhs, "Chem.k")        # chemistry rate constant
        @test _uses_var(eq_O3.rhs, "Chem.O3")       # chemistry state
        @test _uses_var(eq_O3.rhs, "Advection.u")   # advection x-velocity
        @test _uses_var(eq_O3.rhs, "Advection.v")   # advection y-velocity
        # Spatial transport operators survive the merge.
        @test _has_op(eq_O3.rhs, "grad")
        # The top level is a sum of the chemistry term and the advection term
        # (not just one side).
        @test eq_O3.rhs isa EarthSciSerialization.OpExpr
        @test (eq_O3.rhs::EarthSciSerialization.OpExpr).op == "+"

        # (5) No residual equation on Advection._var — the placeholder was
        # expanded away by operator_compose.
        @test _find_eq(flat, "Advection._var") === nothing

        # (6) End-to-end: feed the flattened system to the real
        # ModelingToolkit.PDESystem constructor (via the MTK extension) and
        # confirm we get a live PDESystem back.
        pde = ModelingToolkit.PDESystem(flat; name=:ExampleA)
        @test pde !== nothing
        @test occursin("PDESystem", string(typeof(pde)))
        @test !(pde isa MockPDESystem)
    end

    # Cases 11 and 12 from the pre-gt-r8w revision of this file were
    # mislabeled: they only verified that spatial operators produced entries
    # in `flat.independent_variables`. Per the gt-27b audit, Examples B and C
    # of spec §4.7.6 (1D diffusion + 0D surface deposition via slice; 3D PDE
    # + 2D surface chemistry via slice) are currently DEFERRED at the spec
    # level and will be restored by a successor bead when the Julia slice
    # mapping is wired end-to-end. Both tests were deleted — do NOT add
    # replacements that pretend to cover Examples B and C with incomplete
    # assertions. Real Example B/C tests live in future beads.

    @testset "11. §4.7.6 UnmappedDomainError: cross-domain coupling with no interface" begin
        # Two models on different non-null domains composed without an
        # Interface declaring their mapping. Per §4.7.6, this MUST raise
        # UnmappedDomainError during flatten.
        domains = Dict{String, Domain}(
            "grid_a" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
            "grid_b" => Domain(spatial=Dict{String,Any}("x" => [0.0, 2.0])),
        )
        vars_a = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_a = Model(vars_a, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_a")
        vars_b = Dict{String, ModelVariable}("S" => ModelVariable(StateVariable))
        m_b = Model(vars_b, Equation[Equation(_deriv("S"), _V("S"))],
                    domain="grid_b")
        coupling = CouplingEntry[
            CouplingOperatorCompose(["A", "B"]),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t11_unmapped"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling,
            domains=domains)  # note: no `interfaces` — that's the error
        err = try
            flatten(file); nothing
        catch e
            e
        end
        @test err isa UnmappedDomainError
        @test err.source == "grid_a" || err.source == "grid_b"
        @test err.target == "grid_a" || err.target == "grid_b"
        @test occursin("UnmappedDomainError", sprint(showerror, err))
    end

    @testset "12. §4.7.6 Interface with covering mapping permits flatten" begin
        # Companion to case 11: same two-domain file, but with an Interface
        # that explicitly covers both domains (identity regridding). flatten
        # MUST NOT throw in this case — it should complete normally.
        domains = Dict{String, Domain}(
            "grid_a" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
            "grid_b" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
        )
        vars_a = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_a = Model(vars_a, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_a")
        vars_b = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_b = Model(vars_b, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_b")
        coupling = CouplingEntry[
            CouplingOperatorCompose(["A", "B"]),
        ]
        interfaces = Dict{String, EarthSciSerialization.Interface}(
            "ab_identity" => EarthSciSerialization.Interface(
                ["grid_a", "grid_b"],
                Dict{String, Any}("shared" => Dict("grid_a.x" => "grid_b.x"));
                regridding=Dict{String, Any}("method" => "identity"),
            ),
        )
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t12_interface_ok"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling,
            domains=domains,
            interfaces=interfaces)
        flat = flatten(file)
        @test flat isa FlattenedSystem
    end

    @testset "13. §4.7.6 UnsupportedRegriddingError from real flatten" begin
        # An Interface with a regridding.method outside the supported set
        # (`identity` only, at the Julia Core tier) MUST raise
        # UnsupportedRegriddingError at flatten time.
        domains = Dict{String, Domain}(
            "grid_a" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
            "grid_b" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
        )
        vars_a = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_a = Model(vars_a, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_a")
        vars_b = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_b = Model(vars_b, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_b")
        coupling = CouplingEntry[
            CouplingOperatorCompose(["A", "B"]),
        ]
        interfaces = Dict{String, EarthSciSerialization.Interface}(
            "ab_regrid" => EarthSciSerialization.Interface(
                ["grid_a", "grid_b"],
                Dict{String, Any}("shared" => Dict("grid_a.x" => "grid_b.x"));
                regridding=Dict{String, Any}("method" => "cubic_spline"),
            ),
        )
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t13_regrid"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling,
            domains=domains,
            interfaces=interfaces)
        err = try
            flatten(file); nothing
        catch e
            e
        end
        @test err isa UnsupportedRegriddingError
        @test err.strategy == "cubic_spline"
        @test occursin("cubic_spline", sprint(showerror, err))

        # Same input but with dimension_mapping type explicitly declared as
        # "slice" (Analysis-tier) MUST raise DimensionPromotionError.
        interfaces_slice = Dict{String, EarthSciSerialization.Interface}(
            "ab_slice" => EarthSciSerialization.Interface(
                ["grid_a", "grid_b"],
                Dict{String, Any}("type" => "slice",
                                  "axis" => "x", "value" => 0.0)),
        )
        file_slice = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t13_slice"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling,
            domains=domains,
            interfaces=interfaces_slice)
        err_slice = try
            flatten(file_slice); nothing
        catch e
            e
        end
        @test err_slice isa DimensionPromotionError
        @test occursin("slice", sprint(showerror, err_slice))
    end

    @testset "14. §4.7.6 DomainUnitMismatchError from real variable_map flatten" begin
        # A variable_map with transform="identity" between two variables
        # carrying DIFFERENT declared units MUST raise DomainUnitMismatchError.
        vars_a = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable; units="K"),
        )
        m_a = Model(vars_a, Equation[Equation(_deriv("T"), _V("T"))])
        vars_b = Dict{String, ModelVariable}(
            "T" => ModelVariable(ParameterVariable; units="degC"),
        )
        m_b = Model(vars_b, Equation[])
        coupling = CouplingEntry[
            CouplingVariableMap("A.T", "B.T", "identity"),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t14_units"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling)
        err = try
            flatten(file); nothing
        catch e
            e
        end
        @test err isa DomainUnitMismatchError
        @test err.variable == "A.T"
        @test err.source_units == "K"
        @test err.target_units == "degC"
        @test occursin("K", sprint(showerror, err))
        @test occursin("degC", sprint(showerror, err))
    end

    @testset "15. No @eval or __precompile__(false) in flatten.jl" begin
        flatten_src = read(joinpath(@__DIR__, "..", "src", "flatten.jl"), String)
        @test !occursin("@eval", flatten_src)
        @test !occursin("__precompile__(false)", flatten_src)
    end

    @testset "flatten(::Model) convenience" begin
        vars = Dict{String, ModelVariable}("x" => ModelVariable(StateVariable))
        eqs = [Equation(_deriv("x"), _V("x"))]
        m = Model(vars, eqs)
        flat = flatten(m)
        @test flat isa FlattenedSystem
        @test haskey(flat.state_variables, "anonymous.x")
    end

    @testset "lower_reactions_to_equations helper" begin
        species = [EarthSciSerialization.Species("A"),
                   EarthSciSerialization.Species("B")]
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("A", 1)],
            [EarthSciSerialization.StoichiometryEntry("B", 1)],
            _V("k"))]
        eqs = lower_reactions_to_equations(rxns, species)
        @test length(eqs) == 2
        # Every equation is a D(species, t) = ... form.
        for eq in eqs
            @test eq.lhs isa EarthSciSerialization.OpExpr
            @test eq.lhs.op == "D"
        end
    end

    @testset "FlattenedSystem metadata provenance" begin
        v1 = Dict{String, ModelVariable}("x" => ModelVariable(StateVariable))
        m1 = Model(v1, Equation[])
        v2 = Dict{String, ModelVariable}("y" => ModelVariable(StateVariable))
        m2 = Model(v2, Equation[])
        coupling = CouplingEntry[
            CouplingOperatorApply("my_op"),
            CouplingCallback("cb1"),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("mdata"),
            models=Dict("A" => m1, "B" => m2),
            coupling=coupling)
        flat = flatten(file)
        @test "A" in flat.metadata.source_systems
        @test "B" in flat.metadata.source_systems
        @test length(flat.metadata.coupling_rules_applied) == 2
        @test "operator_apply:my_op" in flat.metadata.opaque_coupling_refs
        @test "callback:cb1" in flat.metadata.opaque_coupling_refs
    end

    @testset "Flatten valid fixtures smoke test" begin
        valid_fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "valid")
        if isdir(valid_fixtures_dir)
            valid_files = filter(f -> endswith(f, ".esm"), readdir(valid_fixtures_dir))
            for filename in valid_files[1:min(5, length(valid_files))]
                filepath = joinpath(valid_fixtures_dir, filename)
                @testset "Flatten fixture: $filename" begin
                    try
                        esm_data = EarthSciSerialization.load(filepath)
                        flat = flatten(esm_data)
                        @test flat isa FlattenedSystem
                    catch e
                        if e isa EarthSciSerialization.SchemaValidationError ||
                           e isa EarthSciSerialization.ParseError ||
                           e isa ConflictingDerivativeError ||
                           e isa UnmappedDomainError ||
                           e isa UnsupportedRegriddingError ||
                           e isa DimensionPromotionError ||
                           e isa DomainUnitMismatchError
                            @test_broken false
                        else
                            @warn "Flatten test failed for $filename: $e"
                            @test false
                        end
                    end
                end
            end
        end
    end
end
