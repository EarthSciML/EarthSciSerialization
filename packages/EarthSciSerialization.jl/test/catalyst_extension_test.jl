using Test
using EarthSciSerialization
# Import both MTK and Catalyst qualified to avoid name collisions with
# EarthSciSerialization exports (e.g. `Equation`, `Reaction`).
import ModelingToolkit
import Symbolics
import Catalyst

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
end
