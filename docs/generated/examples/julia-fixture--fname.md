# fixture $fname (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/data_loader_fixtures_test.jl`

```julia
# 1. Parse.
            original = EarthSciSerialization.load(fpath)
            @test original isa EarthSciSerialization.EsmFile
            @test original.data_loaders !== nothing
            @test !isempty(original.data_loaders)

            # 2. Schema-validate.
            result = EarthSciSerialization.validate(original)
            if !result.is_valid
                @info "Validation errors for $fname" errors=result.schema_errors structural=result.structural_errors
```

