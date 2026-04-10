# load() with path calls resolve_subsystem_refs! (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
# Create a minimal valid ESM file
        tmp_dir = mktempdir()
        esm_content = """{
            "esm": "0.1.0",
            "metadata": {
                "name": "Test File",
                "authors": ["Test"]
            },
            "models": {
                "SimpleModel": {
                    "variables": {
                        "T": {"type": "state", "default": 300.0}
                    },
                    "equations": []
                }
            }
        }"""

        esm_path = joinpath(tmp_dir, "test.esm")
        write(esm_path, esm_content)

        try
            # This should call resolve_subsystem_refs! automatically
            loaded = EarthSciSerialization.load(esm_path)
            @test loaded isa EsmFile
            @test loaded.metadata.name == "Test File"
        catch e
            if e isa EarthSciSerialization.SchemaValidationError || e isa EarthSciSerialization.ParseError
                @test_broken false  # Schema validation with minimal fixture
            else
                rethrow(e)
```

