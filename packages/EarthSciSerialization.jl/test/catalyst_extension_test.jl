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
end
