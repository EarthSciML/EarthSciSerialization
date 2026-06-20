/**
 * Schema-validation conformance tests for the additive aggregate / semiring /
 * index_sets fixtures (bead ess-my4.1.5; RFC semiring-faq-unified-ir §5.1 /
 * §5.2). Exercises the additive schema deltas — op:"aggregate", the closed
 * `semiring` enum, `ranges` { "from": <index-set> } references, and the
 * model-level `index_sets` registry — through the TypeScript binding's
 * validate + parse/serialize path. The TS binding does no numeric evaluation,
 * so this is validation / round-trip only (the numeric cross-binding
 * equivalence is asserted by the Julia / Rust / Python evaluator suites).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { load, save, validate, validateSchema } from './index.js';

const testsDir = join(__dirname, '../../../tests');

function esmFilesIn(dir: string): string[] {
  return readdirSync(dir)
    .filter((e) => e.endsWith('.esm'))
    .map((e) => join(dir, e))
    .sort();
}

describe('Aggregate / semiring fixtures', () => {
  describe('tests/valid/aggregate', () => {
    const validFiles = esmFilesIn(join(testsDir, 'valid', 'aggregate'));

    it('has fixtures to test', () => {
      expect(validFiles.length).toBeGreaterThan(0);
    });

    it.each(validFiles)('validates and round-trips %s', (filePath) => {
      const content = readFileSync(filePath, 'utf-8');

      // Schema-valid: the additive aggregate/semiring/index_sets fields all
      // satisfy the embedded JSON schema.
      expect(validateSchema(JSON.parse(content))).toHaveLength(0);

      // Structurally valid too: the structural pass is aggregate-aware
      // (ess-my4.1.7). It recognises an LHS-aggregate equation (and the
      // relational `index(v, i) = aggregate(...)` form) as an equation for its
      // output variable, and binds aggregate range / `index` element symbols so
      // contracted indices are not flagged as undefined references.
      const result = validate(content);
      expect(result.schema_errors).toHaveLength(0);
      expect(result.structural_errors).toHaveLength(0);
      expect(result.is_valid).toBe(true);

      // parse -> serialize -> parse is a fixed point on the typed view.
      const original = load(content);
      const reloaded = load(save(original));
      expect(reloaded).toEqual(original);
    });
  });

  describe('tests/invalid/aggregate', () => {
    const invalidFiles = esmFilesIn(join(testsDir, 'invalid', 'aggregate'));

    it('has fixtures to test', () => {
      expect(invalidFiles.length).toBeGreaterThan(0);
    });

    it.each(invalidFiles)('rejects %s', (filePath) => {
      const content = readFileSync(filePath, 'utf-8');

      // Every invalid/aggregate fixture is a pure schema violation
      // (unregistered semiring, ragged missing offsets/values, discrete
      // missing shape, join not an array / wrong `on` arity, refresh on a
      // non-discrete variable), so the schema validator alone rejects them.
      expect(validateSchema(JSON.parse(content)).length).toBeGreaterThan(0);
    });
  });
});
