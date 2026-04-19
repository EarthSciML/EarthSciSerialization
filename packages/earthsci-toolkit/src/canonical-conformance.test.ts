import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { canonicalJson } from './canonicalize.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
// packages/earthsci-toolkit/src/ -> repo root is 3 levels up.
const REPO_ROOT = resolve(__dirname, '..', '..', '..')
const FIXTURES_DIR = resolve(REPO_ROOT, 'tests', 'conformance', 'canonical')

interface ManifestEntry {
  id: string
  path: string
  ts_skip?: string
}

interface Manifest {
  fixtures: ManifestEntry[]
}

interface Fixture {
  id: string
  input: unknown
  expected: string
}

const manifest: Manifest = JSON.parse(
  readFileSync(resolve(FIXTURES_DIR, 'manifest.json'), 'utf-8'),
)

describe('canonical-form cross-binding conformance', () => {
  for (const entry of manifest.fixtures) {
    const fixture: Fixture = JSON.parse(
      readFileSync(resolve(FIXTURES_DIR, entry.path), 'utf-8'),
    )
    const test = entry.ts_skip ? it.skip : it
    test(`${entry.id}${entry.ts_skip ? ' (TS skip: ' + entry.ts_skip + ')' : ''}`, () => {
      const got = canonicalJson(fixture.input as never)
      expect(got).toBe(fixture.expected)
    })
  }
})
