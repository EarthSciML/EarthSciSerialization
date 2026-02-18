#!/usr/bin/env julia

# Test script to verify Species struct fix

# Add the package to the path
push!(LOAD_PATH, "/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/src")
include("/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/src/types.jl")
include("/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/src/serialize.jl")
include("/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/src/parse.jl")

function test_species_struct()
    println("Testing Species struct with new fields...")

    # Create a Species with the new fields
    species = Species("CO2", units="mol/m^3", default=1e-6, description="Carbon dioxide")

    println("Created species: $(species.name)")
    println("  Units: $(species.units)")
    println("  Default: $(species.default)")
    println("  Description: $(species.description)")

    # Test serialization
    serialized = serialize_species(species)
    println("\nSerialized Species:")
    println(serialized)

    # Test parsing back from serialized data - create a NamedTuple to simulate JSON data
    json_like = (name=serialized["name"],
                 units=get(serialized, "units", nothing),
                 default=get(serialized, "default", nothing),
                 description=get(serialized, "description", nothing))
    parsed_species = coerce_species(json_like)
    println("\nParsed back species:")
    println("  Name: $(parsed_species.name)")
    println("  Units: $(parsed_species.units)")
    println("  Default: $(parsed_species.default)")
    println("  Description: $(parsed_species.description)")

    # Verify fields match
    @assert species.name == parsed_species.name
    @assert species.units == parsed_species.units
    @assert species.default == parsed_species.default
    @assert species.description == parsed_species.description

    println("\n✅ Species struct test passed! All fields correctly preserved through serialization/deserialization.")

    return true
end

if abspath(PROGRAM_FILE) == @__FILE__
    test_species_struct()
end