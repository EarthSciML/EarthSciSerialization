package esm

// Load-time rejection of pre-0.7.0 data-loader shapes removed by the
// pure-I/O data-loaders hard break (RFC pure-io-data-loaders §4.1, bead
// ess-v9a.7).
//
// In esm 0.7.0 the DataLoader became pure I/O: the `regridding` block was
// removed (regridding is now a per-variable Model.regrid concern) and the
// `spatial` block was removed (the loader's native grid is now a GDD Grid
// under `grid`). A file that still declares `esm` < 0.7.0 while carrying
// either block is rejected at load with a named, version-keyed diagnostic,
// mirroring RejectExpressionTemplatesPreV04 and the equivalent
// TS / Python / Julia / Rust checks.
//
// Operates on the pre-deserialization `map[string]interface{}` view so the
// user sees the version hint instead of a generic schema error.

import (
	"fmt"
	"strconv"
	"strings"
)

// LegacyDataLoaderError is the error type raised by the legacy data-loader
// rejection pass. The Code field carries one of the stable diagnostic codes:
//
//   - data_loader_regridding_removed
//   - data_loader_spatial_removed
type LegacyDataLoaderError struct {
	Code    string
	Message string
}

func (e *LegacyDataLoaderError) Error() string {
	return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

func newLegacyLoaderErr(code, msg string) *LegacyDataLoaderError {
	return &LegacyDataLoaderError{Code: code, Message: msg}
}

// RejectLegacyDataLoaderShapes rejects `data_loaders.<name>.regridding` and
// `data_loaders.<name>.spatial` blocks in files declaring `esm` < 0.7.0.
// Both blocks were removed in esm 0.7.0 (RFC pure-io-data-loaders §4.1).
// Mirrors the equivalent TS / Python / Julia / Rust checks. Reuses the
// package-level semverRe and sortedKeys helpers.
func RejectLegacyDataLoaderShapes(view map[string]interface{}) error {
	if view == nil {
		return nil
	}
	esmRaw, ok := view["esm"].(string)
	if !ok {
		return nil
	}
	m := semverRe.FindStringSubmatch(esmRaw)
	if m == nil {
		return nil
	}
	major, _ := strconv.Atoi(m[1])
	minor, _ := strconv.Atoi(m[2])
	// Version gate: only pre-0.7.0 files carry the removed blocks.
	if !(major == 0 && minor < 7) {
		return nil
	}
	loaders, ok := view["data_loaders"].(map[string]interface{})
	if !ok {
		return nil
	}
	regriddingPaths := []string{}
	spatialPaths := []string{}
	for _, name := range sortedKeys(loaders) {
		loader, ok := loaders[name].(map[string]interface{})
		if !ok {
			continue
		}
		if _, has := loader["regridding"]; has {
			regriddingPaths = append(regriddingPaths, fmt.Sprintf("/data_loaders/%s/regridding", name))
		}
		if _, has := loader["spatial"]; has {
			spatialPaths = append(spatialPaths, fmt.Sprintf("/data_loaders/%s/spatial", name))
		}
	}
	if len(regriddingPaths) > 0 {
		return newLegacyLoaderErr(
			"data_loader_regridding_removed",
			fmt.Sprintf("DataLoader `regridding` was removed in esm 0.7.0 (regridding is now a per-variable model concern — see `Model.regrid`; RFC pure-io-data-loaders §4.1); file declares %s. Migrate by deleting the block and moving the per-variable regridding choice to the owning model. Offending paths: %s", esmRaw, strings.Join(regriddingPaths, ", ")),
		)
	}
	if len(spatialPaths) > 0 {
		return newLegacyLoaderErr(
			"data_loader_spatial_removed",
			fmt.Sprintf("DataLoader `spatial` was removed in esm 0.7.0 (the native grid is now a GDD `Grid` under `grid`; RFC pure-io-data-loaders §4.1); file declares %s. Migrate by replacing the block with a `grid` GDD Grid. Offending paths: %s", esmRaw, strings.Join(spatialPaths, ", ")),
		)
	}
	return nil
}
