# GridAccessorError message surfaces the concrete type (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grid_accessor_test.jl`

```julia
g = _NotImplAccessor()
        try
            cell_centers(g, 0, 0)
            @test false  # unreachable
        catch e
            @test e isa EarthSciSerialization.GridAccessorError
            @test occursin("_NotImplAccessor", e.message)
            io = IOBuffer()
            showerror(io, e)
            @test occursin("GridAccessorError", String(take!(io)))
```

