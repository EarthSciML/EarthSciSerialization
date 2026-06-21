/**
 * Schema-validation conformance tests for the additive M4 geometry-kernel
 * fixtures (bead ess-my4.4.2; RFC semiring-faq-unified-ir §8.1 / §A.8;
 * CONFORMANCE_SPEC.md §5.8). Exercises the additive schema deltas — the
 * `intersect_polygon` leaf op, its required `manifold` flag (planar /
 * spherical / geodesic), and the bin-Skolem spatial-join representation
 * composed from the existing `floor` / `skolem` / `join.on` ops — through the
 * TypeScript binding's validate + parse/serialize path. The TS binding does no
 * numeric polygon clipping, so this is validation / round-trip only; the
 * tolerance-based cross-binding clip conformance is asserted by the
 * Julia / Rust / Python evaluator suites (ess-my4.4.3/.4/.11/.12, gated by
 * §5.8). Mirrors aggregate-fixtures.test.ts.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { join, basename } from 'path';
import { load, save, validate, validateSchema } from './index.js';

const testsDir = join(__dirname, '../../../tests');

function esmFilesIn(dir: string): string[] {
  return readdirSync(dir)
    .filter((e) => e.endsWith('.esm'))
    .map((e) => join(dir, e))
    .sort();
}

describe('Geometry kernel (intersect_polygon) fixtures', () => {
  describe('tests/valid/geometry', () => {
    const validFiles = esmFilesIn(join(testsDir, 'valid', 'geometry'));

    it('has fixtures to test', () => {
      expect(validFiles.length).toBeGreaterThan(0);
    });

    it.each(validFiles)('validates and round-trips %s', (filePath) => {
      const content = readFileSync(filePath, 'utf-8');

      // Schema-valid: the additive intersect_polygon op + manifold flag, the
      // derived-index-set ring (from_faq), and the floor/skolem/join.on
      // bin-Skolem composition all satisfy the embedded JSON schema.
      expect(validateSchema(JSON.parse(content))).toHaveLength(0);

      // Structurally valid too: the structural pass is intersect_polygon-aware
      // — the clip leaf is walked like any other op (its two polygon operands
      // are ordinary sub-expression references), and polygon_area / the
      // bin-Skolem join ride the existing aggregate-aware reference + balance
      // machinery, so nothing is flagged as undefined.
      const result = validate(content);
      expect(result.schema_errors).toHaveLength(0);
      expect(result.structural_errors).toHaveLength(0);
      expect(result.is_valid).toBe(true);

      // parse -> serialize -> parse is a fixed point on the typed view
      // (the `manifold` flag survives the typed round-trip).
      const original = load(content);
      const reloaded = load(save(original));
      expect(reloaded).toEqual(original);
    });
  });

  describe('tests/invalid/geometry', () => {
    const invalidFiles = esmFilesIn(join(testsDir, 'invalid', 'geometry'));

    it('has fixtures to test', () => {
      expect(invalidFiles.length).toBeGreaterThan(0);
    });

    // Each geometry invalid fixture is a pure SCHEMA violation isolated to the
    // intersect_polygon node — a missing `manifold`, a third operand (the op is
    // strictly binary), or a `manifold` outside the closed enum — so the schema
    // validator alone rejects them.
    it.each(invalidFiles)('rejects %s', (filePath) => {
      const parsed = JSON.parse(readFileSync(filePath, 'utf-8'));
      expect(validateSchema(parsed).length).toBeGreaterThan(0);
    });
  });
});
