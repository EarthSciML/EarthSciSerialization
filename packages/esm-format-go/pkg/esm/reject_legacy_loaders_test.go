package esm

// Tests for the v0.7.0 pure-I/O data-loaders hard break: pre-0.7.0 loader
// files carrying the removed DataLoader.regridding / .spatial blocks are
// rejected at load with named, version-keyed diagnostics
// (RFC pure-io-data-loaders §4.1, bead ess-v9a.7).
//
// Drives the cross-binding tests/conformance/migration/0_6_to_0_7 fixtures.
// Repo-root tests/ is reached via the same "../../../../tests/..." relative
// path used by the other conformance tests in this package.

import (
	"errors"
	"os"
	"testing"
)

const migrationFixtureDir = "../../../../tests/conformance/migration/0_6_to_0_7/"

func TestRejectLegacyLoaders_RegriddingRemovedFixture(t *testing.T) {
	b, err := os.ReadFile(migrationFixtureDir + "loader_regridding_removed.esm")
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	_, err = LoadString(string(b))
	if err == nil {
		t.Fatalf("expected LoadString to reject the legacy regridding loader, got nil error")
	}
	var lerr *LegacyDataLoaderError
	if !errors.As(err, &lerr) {
		t.Fatalf("expected *LegacyDataLoaderError, got %T (%v)", err, err)
	}
	if lerr.Code != "data_loader_regridding_removed" {
		t.Errorf("code = %s; want data_loader_regridding_removed", lerr.Code)
	}
}

func TestRejectLegacyLoaders_SpatialRemovedFixture(t *testing.T) {
	b, err := os.ReadFile(migrationFixtureDir + "loader_spatial_removed.esm")
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	_, err = LoadString(string(b))
	if err == nil {
		t.Fatalf("expected LoadString to reject the legacy spatial loader, got nil error")
	}
	var lerr *LegacyDataLoaderError
	if !errors.As(err, &lerr) {
		t.Fatalf("expected *LegacyDataLoaderError, got %T (%v)", err, err)
	}
	if lerr.Code != "data_loader_spatial_removed" {
		t.Errorf("code = %s; want data_loader_spatial_removed", lerr.Code)
	}
}

func TestRejectLegacyLoaders_MigratedFixtureLoads(t *testing.T) {
	b, err := os.ReadFile(migrationFixtureDir + "loader_migrated.esm")
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	if _, err := LoadString(string(b)); err != nil {
		t.Fatalf("expected migrated 0.7.0 loader to load without error, got %v", err)
	}
}

func TestRejectLegacyLoaders_VersionGatedNoOp(t *testing.T) {
	// A 0.7.0 file may legitimately carry a key named "regridding" only if
	// the schema allows it; regardless, the version-gated check is a no-op
	// for esm >= 0.7.0 and must not raise.
	view := map[string]interface{}{
		"esm": "0.7.0",
		"data_loaders": map[string]interface{}{
			"w": map[string]interface{}{
				"regridding": map[string]interface{}{},
			},
		},
	}
	if err := RejectLegacyDataLoaderShapes(view); err != nil {
		t.Fatalf("expected version-gated no-op for esm 0.7.0, got %v", err)
	}
}
