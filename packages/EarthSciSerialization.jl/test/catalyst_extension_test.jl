using Test
using EarthSciSerialization
# Import both MTK and Catalyst qualified to avoid name collisions with
# EarthSciSerialization exports (e.g. `Equation`, `Reaction`).
import ModelingToolkit
import Symbolics
import Catalyst

# Helper: strip "(t)" suffix that Catalyst appends to species names.
_strip_time_suffix(s::AbstractString) = endswith(s, "(t)") ? s[1:end-3] : s

@testset "Catalyst Extension Integration" begin

    @testset "Loading Catalyst activates both extensions" begin
        mtk_ext = Base.get_extension(EarthSciSerialization,
                                     :EarthSciSerializationMTKExt)
        cat_ext = Base.get_extension(EarthSciSerialization,
                                     :EarthSciSerializationCatalystExt)
        @test mtk_ext !== nothing
        @test cat_ext !== nothing
        @test hasmethod(Catalyst.ReactionSystem,
                        Tuple{EarthSciSerialization.ReactionSystem})
    end

    @testset "Catalyst.ReactionSystem(::ESM ReactionSystem) builds a real ReactionSystem" begin
        species = [
            EarthSciSerialization.Species("NO"),
            EarthSciSerialization.Species("O3"),
            EarthSciSerialization.Species("NO2"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1.8e-12)]
        rxn_list = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("NO" => 1, "O3" => 1),
                                           Dict("NO2" => 1),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxn_list;
                                                        parameters=params)

        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:OzonePhoto)
        @test !(cat_rsys isa MockCatalystSystem)
        @test occursin("ReactionSystem", string(typeof(cat_rsys)))

        species_names = Set(string(Catalyst.getname(s))
                            for s in Catalyst.species(cat_rsys))
        @test "NO(t)" in species_names || "NO" in species_names
        @test "O3(t)" in species_names || "O3" in species_names

        param_names = Set(string(Catalyst.getname(p))
                          for p in Catalyst.parameters(cat_rsys))
        @test "k" in param_names
    end

    @testset "Round-trip: ESM ReactionSystem → Catalyst → ESM" begin
        species = [
            EarthSciSerialization.Species("A"),
            EarthSciSerialization.Species("B"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1.0)]
        rxns = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("A" => 1), Dict("B" => 1),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxns;
                                                        parameters=params)
        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:AB)
        recovered = EarthSciSerialization.ReactionSystem(cat_rsys)
        @test length(recovered.species) == 2
        @test length(recovered.parameters) == 1
        @test length(recovered.reactions) == 1
    end

    @testset "Fractional stoichiometry survives Catalyst → ESM reverse (gt-3ai5)" begin
        # Catalyst ReactionSystems with fractional stoichiometry (e.g.
        # CH3O2+CH3O2 -> 2.0 CH2O + 0.8 HO2) must reverse-convert without
        # Int() truncation. Prior to the fix, Int(0.8) raised InexactError.
        species = [
            EarthSciSerialization.Species("CH3O2"),
            EarthSciSerialization.Species("CH2O"),
            EarthSciSerialization.Species("HO2"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1.0e-13)]
        rxns = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("CH3O2" => 2.0),
                                           Dict("CH2O" => 2.0, "HO2" => 0.8),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxns;
                                                        parameters=params)
        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:FracStoich)
        recovered = EarthSciSerialization.ReactionSystem(cat_rsys)
        @test length(recovered.reactions) == 1
        rxn = recovered.reactions[1]
        # rxn.reactants / rxn.products return Dict{String,Float64} via the
        # backward-compatibility getproperty intercept.
        @test rxn.reactants["CH3O2"] ≈ 2.0
        @test rxn.products["CH2O"]  ≈ 2.0
        @test rxn.products["HO2"]   ≈ 0.8
    end

    @testset "Reservoir species (constant=true) maps to isconstantspecies (gt-ertm)" begin
        # Reservoir species must flow through Catalyst as parameters with the
        # isconstantspecies=true metadata (modern Catalyst rejects this
        # metadata on @species). The reverse direction recovers them as ESM
        # species with constant=true rather than as ordinary parameters.
        species = [
            EarthSciSerialization.Species("O2"; constant=true),
            EarthSciSerialization.Species("CH4"; constant=true),
            EarthSciSerialization.Species("OH"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1e-14)]
        rxns = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("CH4" => 1, "OH" => 1),
                                           Dict("O2" => 1),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxns;
                                                        parameters=params)
        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:Reservoir)

        # Check that O2 and CH4 are constant species (metadata-tagged
        # parameters in Catalyst), while OH remains a state species.
        constant_names = Set(String[])
        for p in Catalyst.parameters(cat_rsys)
            if Catalyst.isconstant(p)
                push!(constant_names, string(Catalyst.getname(p)))
            end
        end
        @test "O2" in constant_names
        @test "CH4" in constant_names
        species_names = Set(_strip_time_suffix(string(Catalyst.getname(s)))
                            for s in Catalyst.species(cat_rsys))
        @test "OH" in species_names
        @test !("O2" in species_names)
        @test !("CH4" in species_names)

        # Reverse: recover constant flag from Catalyst metadata.
        recovered = EarthSciSerialization.ReactionSystem(cat_rsys)
        by_name = Dict(s.name => s for s in recovered.species)
        @test haskey(by_name, "O2")  && by_name["O2"].constant  === true
        @test haskey(by_name, "CH4") && by_name["CH4"].constant === true
        @test haskey(by_name, "OH")  && by_name["OH"].constant  !== true
        @test length(recovered.parameters) == 1
    end

    @testset "Rate AST emission: species refs and numeric Constants (esm-edt)" begin
        # Regression for esm-edt: _catalyst_rate_to_esm previously emitted
        #   (1) a species `S` used inside a rate as {op: "S", args: ["t"]}
        #       (registered-function call shape), and
        #   (2) literal numeric values that surface as BasicSymbolic Const
        #       nodes (the same shape MTK Constants substitution produces)
        #       as STRING args like {op: "*", args: ["300.0", ...]}.
        # Both must round-trip through the AST as bare identifiers / NumExpr.
        local t = ModelingToolkit.t_nounits

        # Build species and parameters dynamically so the macro forms can
        # resolve `t` from local scope.
        Catalyst.@species A(t) B(t)
        ModelingToolkit.@parameters k = 1.0

        # Rate (1): k * A — A is a species reference inside the rate.
        # Rate (2): 300.0 * k — literal Float64 inside a multiplicative rate;
        # the 300.0 surfaces as a Const-tagged BasicSymbolic, the same shape
        # an `@constants` value lands in after MTK substitution.
        rxs = [
            Catalyst.Reaction(k * A, [A], [B]),
            Catalyst.Reaction(300.0 * k, [A], [B]),
        ]
        cat_rsys = Catalyst.ReactionSystem(rxs, t, [A, B], [k];
                                            name=:RateASTRegression)
        recovered = EarthSciSerialization.ReactionSystem(cat_rsys)
        @test length(recovered.reactions) == 2

        # --- Rate 1: k * A ---
        rate1 = recovered.reactions[1].rate
        @test rate1 isa OpExpr && rate1.op == "*"
        # Must contain a bare VarExpr("A"), NOT an OpExpr("A", [...]).
        function _has_species_ref(node, name)
            if node isa VarExpr
                return node.name == name
            elseif node isa OpExpr
                # Reject the bug shape {op:name, args:["t"]} explicitly.
                if node.op == name
                    return false
                end
                return any(a -> _has_species_ref(a, name), node.args)
            end
            return false
        end
        @test _has_species_ref(rate1, "A")
        # And no OpExpr with op == species name.
        function _no_species_call(node, name)
            if node isa OpExpr
                node.op == name && return false
                return all(a -> _no_species_call(a, name), node.args)
            end
            return true
        end
        @test _no_species_call(rate1, "A")

        # --- Rate 2: 300.0 * k ---
        rate2 = recovered.reactions[2].rate
        @test rate2 isa OpExpr && rate2.op == "*"
        # The literal 300.0 must be a NumExpr (not VarExpr("300.0")).
        function _find_num(node, target)
            if node isa NumExpr
                return node.value ≈ target
            elseif node isa OpExpr
                return any(a -> _find_num(a, target), node.args)
            end
            return false
        end
        @test _find_num(rate2, 300.0)
        # And no VarExpr whose name parses as a number.
        function _no_numeric_string_var(node)
            if node isa VarExpr
                # Numeric string would parse as Float64.
                return tryparse(Float64, node.name) === nothing
            elseif node isa OpExpr
                return all(_no_numeric_string_var, node.args)
            end
            return true
        end
        @test _no_numeric_string_var(rate2)

        # Sanity: full round-trip through serialize_reaction_system + JSON3
        # must keep numeric args as JSON numbers, not strings.
        rs_dict = EarthSciSerialization.serialize_reaction_system(recovered)
        json_str = JSON3.write(rs_dict)
        # The serialized rate2 should contain 300.0 as a JSON number, never
        # the quoted string "300.0". Use a substring check on the args slot.
        @test occursin("300", json_str)
        @test !occursin("\"300.0\"", json_str)
        @test !occursin("\"300\"", json_str)
    end
end
