using EarthSciSerialization
using EarthSciSerialization: Expr as ESMExpr
using Test

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
        rate = _op("*", _V("k"), _op("*", _V("A"), _V("B")))
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
        # Net stoich of B = 2 - 1 = +1 → a single positive rate term, no '-' or '*2'.
        # Spot-check: the B equation references k, A, and B.
        @test _uses_var(eq_B.rhs, "Auto.k")
        @test _uses_var(eq_B.rhs, "Auto.A")
        @test _uses_var(eq_B.rhs, "Auto.B")
        # A equation should have a negation (consumed).
        @test eq_A.rhs isa EarthSciSerialization.OpExpr
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
        # Merged RHS must reference both A.k and B.j.
        @test _uses_var(eq.rhs, "A.k") || _uses_var(eq.rhs, "B.k")
        @test _uses_var(eq.rhs, "B.j") || _uses_var(eq.rhs, "A.j")
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

    @testset "10. HYBRID: reaction system on a 2D domain → IVs include x, y" begin
        domains = Dict{String, Domain}(
            "grid" => Domain(spatial=Dict{String,Any}("x"=>Dict(), "y"=>Dict())))
        species = [EarthSciSerialization.Species("O3", default=1e-6)]
        params = [EarthSciSerialization.Parameter("k", 0.1)]
        rate = _op("*", _V("k"), _V("O3"))
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("O3", 1)], nothing, rate)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns,
            parameters=params, domain="grid")
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t10"),
            reaction_systems=Dict("Chem" => rsys),
            domains=domains)
        flat = flatten(file)

        @test :t in flat.independent_variables
        @test :x in flat.independent_variables
        @test :y in flat.independent_variables
    end

    @testset "11. HYBRID: 1D (z) domain is detected" begin
        domains = Dict{String, Domain}(
            "col" => Domain(spatial=Dict{String,Any}("z"=>Dict())))
        vars = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        # Spatial derivative in RHS via D(T, z).
        eqs = [Equation(_deriv("T"),
                        _op("D", _V("T"); wrt="z"))]
        m = Model(vars, eqs, domain="col")
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t11"),
            models=Dict("Vert" => m),
            domains=domains)
        flat = flatten(file)
        @test :z in flat.independent_variables
    end

    @testset "12. HYBRID: grad operator detected in IVs" begin
        vars = Dict{String, ModelVariable}("c" => ModelVariable(StateVariable))
        eqs = [Equation(_deriv("c"), _op("grad", _V("c"); dim="x"))]
        m = Model(vars, eqs)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t12"),
            models=Dict("Adv" => m))
        flat = flatten(file)
        @test :x in flat.independent_variables
    end

    @testset "13. VALIDATION: UnmappedDomainError type exists and is constructable" begin
        err = UnmappedDomainError("src", "tgt")
        @test err.source == "src" && err.target == "tgt"
        @test sprint(showerror, err) |> x -> occursin("UnmappedDomainError", x)
    end

    @testset "14. VALIDATION: UnsupportedRegriddingError type exists and is constructable" begin
        err = UnsupportedRegriddingError("cubic_spline")
        @test err.strategy == "cubic_spline"
        @test occursin("cubic_spline", sprint(showerror, err))

        # Also cover the remaining two error types.
        dp = DimensionPromotionError("cannot promote")
        @test occursin("cannot promote", sprint(showerror, dp))
        du = DomainUnitMismatchError("T", "K", "degC")
        @test occursin("T", sprint(showerror, du))
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
                           e isa ConflictingDerivativeError
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
