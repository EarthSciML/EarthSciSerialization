/**
 * Tests for the v0.7.0 pure-I/O hard break load-time rejection
 * (RFC pure-io-data-loaders §4.1, bead ess-v9a.7).
 *
 * Drives the shared cross-binding migration fixtures at
 * tests/conformance/migration/0_6_to_0_7/, resolved relative to the repo
 * root the same way src/conformance.test.ts does.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { load, rejectLegacyDataLoaderShapes, LegacyDataLoaderError } from './index.js';

const testsDir = join(__dirname, '../../../tests');
const migrationDir = join(testsDir, 'conformance/migration/0_6_to_0_7');

function loadFixture(name: string): string {
  return readFileSync(join(migrationDir, name), 'utf-8');
}

/** Run fn and return whatever it throws (or undefined if it doesn't). */
function capture(fn: () => unknown): unknown {
  try {
    fn();
  } catch (e) {
    return e;
  }
  return undefined;
}

describe('rejectLegacyDataLoaderShapes — v0.7.0 pure-I/O hard break', () => {
  it('rejects a pre-0.7.0 loader carrying DataLoader.regridding', () => {
    const caught = capture(() => load(loadFixture('loader_regridding_removed.esm')));
    expect(caught).toBeInstanceOf(LegacyDataLoaderError);
    expect((caught as LegacyDataLoaderError).code).toBe('data_loader_regridding_removed');
  });

  it('rejects a pre-0.7.0 loader carrying DataLoader.spatial', () => {
    const caught = capture(() => load(loadFixture('loader_spatial_removed.esm')));
    expect(caught).toBeInstanceOf(LegacyDataLoaderError);
    expect((caught as LegacyDataLoaderError).code).toBe('data_loader_spatial_removed');
  });

  it('accepts the migrated 0.7.0 loader shape (GDD Grid under `grid`)', () => {
    expect(() => load(loadFixture('loader_migrated.esm'))).not.toThrow();
  });

  it('is a no-op on a 0.7.0 object with a stray regridding block', () => {
    const view = {
      esm: '0.7.0',
      data_loaders: {
        weather: { regridding: { method: 'conservative' } },
      },
    };
    expect(() => rejectLegacyDataLoaderShapes(view)).not.toThrow();
  });
});
