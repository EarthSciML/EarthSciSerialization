"""
Load-time rejection of legacy (pre-0.7.0) data-loader shapes
(esm-spec.md §8 / RFC pure-io-data-loaders §4.1, bead ess-v9a.7).

In v0.7.0 the `DataLoader` is reduced to pure I/O: the loader-level
`regridding` and `spatial` blocks were removed. Regridding/reprojection are
now per-variable `Model.regrid` concerns, and the native grid is a GDD `Grid`
under `grid`. A pre-0.7.0 loader file that still carries one of those blocks
is rejected at load with a named, version-keyed diagnostic, mirroring
`reject_expression_templates_pre_v04`.
"""

const DATA_LOADER_REGRIDDING_REMOVED = "data_loader_regridding_removed"
const DATA_LOADER_SPATIAL_REMOVED = "data_loader_spatial_removed"

"""
    LegacyDataLoaderError <: Exception

Exception raised when a loader carries a `DataLoader` block removed in the
v0.7.0 pure-I/O hard break. Carries a stable `code` matching one of:

- `data_loader_regridding_removed`
- `data_loader_spatial_removed`
"""
struct LegacyDataLoaderError <: Exception
    code::String
    message::String
end

Base.showerror(io::IO, e::LegacyDataLoaderError) =
    print(io, "[$(e.code)] $(e.message)")

"""
    reject_legacy_data_loader_shapes(raw_data)

Reject `data_loaders.<name>.regridding` / `.spatial` blocks in files declaring
`esm` < 0.7.0, with the named diagnostics `data_loader_regridding_removed` /
`data_loader_spatial_removed`. Surfaced before schema validation so the user
sees the migration hint instead of a generic "extra property" error. Mirrors
the equivalent TS / Python / Rust / Go checks for cross-binding-uniform
diagnostics.
"""
function reject_legacy_data_loader_shapes(raw_data)
    raw_data === nothing && return
    !_is_object(raw_data) && return
    esm_raw = get(raw_data, :esm, get(raw_data, "esm", nothing))
    esm_raw === nothing && return
    m = match(r"^(\d+)\.(\d+)\.(\d+)$", string(esm_raw))
    m === nothing && return
    major = parse(Int, m.captures[1])
    minor = parse(Int, m.captures[2])
    is_pre_v07 = (major == 0 && minor < 7)
    !is_pre_v07 && return

    loaders = get(raw_data, :data_loaders, get(raw_data, "data_loaders", nothing))
    (loaders === nothing || !_is_object(loaders)) && return

    regridding_paths = String[]
    spatial_paths = String[]
    for (lname, loader) in pairs(loaders)
        _is_object(loader) || continue
        if haskey(loader, "regridding") || haskey(loader, :regridding)
            push!(regridding_paths, "/data_loaders/$(string(lname))/regridding")
        end
        if haskey(loader, "spatial") || haskey(loader, :spatial)
            push!(spatial_paths, "/data_loaders/$(string(lname))/spatial")
        end
    end

    if !isempty(regridding_paths)
        throw(LegacyDataLoaderError(
            DATA_LOADER_REGRIDDING_REMOVED,
            "DataLoader `regridding` was removed in esm 0.7.0 (regridding is now a " *
            "per-variable model concern — see `Model.regrid`; RFC pure-io-data-loaders " *
            "§4.1); file declares $(string(esm_raw)). Migrate by deleting the block and " *
            "moving the per-variable regridding choice to the owning model. " *
            "Offending paths: $(join(regridding_paths, ", "))"))
    end
    if !isempty(spatial_paths)
        throw(LegacyDataLoaderError(
            DATA_LOADER_SPATIAL_REMOVED,
            "DataLoader `spatial` was removed in esm 0.7.0 (the native grid is now a GDD " *
            "`Grid` under `grid`; RFC pure-io-data-loaders §4.1); file declares " *
            "$(string(esm_raw)). Migrate by replacing the block with a `grid` GDD Grid. " *
            "Offending paths: $(join(spatial_paths, ", "))"))
    end
end
