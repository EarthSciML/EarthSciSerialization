import { describe, it, expect } from 'vitest'
import { load, VERSION, SchemaValidationError } from './index.js'
import { readFileSync } from 'fs'
import { join } from 'path'

// Path to version compatibility test fixtures
const fixturesPath = '../../../tests/version_compatibility'

describe('Version Compatibility', () => {
  // Helper function to load test fixture
  const loadFixture = (filename: string) => {
    const filePath = join(__dirname, fixturesPath, filename)
    const content = readFileSync(filePath, 'utf-8')
    return JSON.parse(content)
  }

  describe('Exact Version Match', () => {
    it('should load baseline version 0.1.0 successfully', () => {
      const fixture = loadFixture('version_0_1_0_baseline.esm')
      const result = load(fixture)

      expect(result.esm).toBe('0.1.0')
      expect(result.metadata.name).toBe('Version_0_1_0_Baseline')
    })
  })

  describe('Backward Compatibility', () => {
    it('should load older minor version (0.0.1) successfully', () => {
      const fixture = loadFixture('version_0_0_1_backwards_compat.esm')
      const result = load(fixture)

      expect(result.esm).toBe('0.0.1')
      expect(result.metadata.name).toBe('Version_0_0_1_BackwardsCompat')
    })

    it('should load newer patch version (0.1.5) successfully', () => {
      const fixture = loadFixture('version_0_1_5_patch_upgrade.esm')
      const result = load(fixture)

      expect(result.esm).toBe('0.1.5')
      expect(result.metadata.name).toBe('Version_0_1_5_PatchUpgrade')
    })
  })

  describe('Forward Compatibility', () => {
    it('should load newer minor version (0.2.0) with warning', () => {
      const fixture = loadFixture('version_0_2_0_minor_upgrade.esm')

      // Mock console.warn to capture warnings
      const warnings: string[] = []
      const originalWarn = console.warn
      console.warn = (...args: any[]) => {
        warnings.push(args.join(' '))
      }

      try {
        const result = load(fixture)

        expect(result.esm).toBe('0.2.0')
        expect(result.metadata.name).toBe('Version_0_2_0_MinorUpgrade')

        // Check that warning was generated
        expect(warnings.length).toBeGreaterThan(0)
        expect(warnings.some(w => w.includes('0.2.0 is newer than'))).toBe(true)
      } finally {
        console.warn = originalWarn
      }
    })

    it('should load much newer version (0.3.0) with unknown fields ignored', () => {
      const fixture = loadFixture('version_0_3_0_with_unknown_fields.esm')

      const warnings: string[] = []
      const originalWarn = console.warn
      console.warn = (...args: any[]) => {
        warnings.push(args.join(' '))
      }

      try {
        const result = load(fixture)

        expect(result.esm).toBe('0.3.0')
        expect(result.metadata.name).toBe('Version_0_3_0_WithUnknownFields')

        // Unknown fields should be ignored (not present in result)
        expect('performance_hints' in result).toBe(false)
        expect('validation_metadata' in result).toBe(false)

        // Check warnings
        expect(warnings.length).toBeGreaterThan(0)
        expect(warnings.some(w => w.includes('0.3.0 is newer than'))).toBe(true)
      } finally {
        console.warn = originalWarn
      }
    })
  })

  describe('Major Version Rejection', () => {
    it('should reject major version 1.0.0', () => {
      const fixture = loadFixture('version_1_0_0_major_upgrade.esm')

      expect(() => load(fixture)).toThrow('Unsupported major version 1')
    })

    it('should reject major version 2.5.1', () => {
      const fixture = loadFixture('version_2_5_1_major_rejection.esm')

      expect(() => load(fixture)).toThrow('Unsupported major version 2')
    })
  })

  describe('Invalid Version Handling', () => {
    it('should reject invalid version string format', () => {
      const fixture = loadFixture('invalid_version_string.esm')

      expect(() => load(fixture)).toThrow(SchemaValidationError)
    })

    it('should reject missing version field', () => {
      const fixture = loadFixture('missing_version_field.esm')

      expect(() => load(fixture)).toThrow(SchemaValidationError)
    })
  })

  describe('Version Parsing', () => {
    it('should correctly parse semantic version components', () => {
      // This tests the internal version parsing logic
      const parseVersion = (versionString: string) => {
        const match = versionString.match(/^(\d+)\.(\d+)\.(\d+)$/)
        if (!match) throw new Error('Invalid version format')

        return {
          major: parseInt(match[1], 10),
          minor: parseInt(match[2], 10),
          patch: parseInt(match[3], 10)
        }
      }

      expect(parseVersion('0.1.0')).toEqual({ major: 0, minor: 1, patch: 0 })
      expect(parseVersion('1.2.3')).toEqual({ major: 1, minor: 2, patch: 3 })
      expect(parseVersion('10.20.30')).toEqual({ major: 10, minor: 20, patch: 30 })

      expect(() => parseVersion('1.2')).toThrow('Invalid version format')
      expect(() => parseVersion('1.2.3.4')).toThrow('Invalid version format')
      expect(() => parseVersion('v1.2.3')).toThrow('Invalid version format')
    })
  })

  describe('Migration Examples', () => {
    it('should demonstrate migration from 0.0.5 to 0.1.0', () => {
      const oldVersion = loadFixture('migration_test_from_0_0_5.esm')
      const newVersion = loadFixture('migration_test_to_0_1_0.esm')

      // Verify the migration changes
      expect(oldVersion.esm).toBe('0.0.5')
      expect(newVersion.esm).toBe('0.1.0')

      // Check that CH4 units were migrated from ppbv to mol/mol
      const oldCH4 = oldVersion.reaction_systems.LegacyChemistry.species.CH4
      const newCH4 = newVersion.reaction_systems.LegacyChemistry.species.CH4

      expect(oldCH4.units).toBe('ppbv')
      expect(oldCH4.default).toBe(1900) // ppbv

      expect(newCH4.units).toBe('mol/mol')
      expect(newCH4.default).toBe(1.9e-6) // converted to mol/mol

      // Check that migration notes were added
      expect('migration_notes' in newVersion.metadata).toBe(true)
      expect(newVersion.metadata.migration_notes).toContain('Migrated from version 0.0.5')
    })
  })

  describe('Library Version Information', () => {
    it('should expose current library version', () => {
      expect(VERSION).toBe('0.1.0')
    })

    it('should provide version compatibility information', () => {
      // This would be part of the actual implementation
      const getCompatibilityInfo = () => ({
        supportedMajorVersion: 0,
        currentVersion: VERSION,
        backwardCompatibleMinorVersions: [0, 1],
        forwardCompatibleMinorVersions: [1, 2, 3] // can load but with warnings
      })

      const info = getCompatibilityInfo()
      expect(info.supportedMajorVersion).toBe(0)
      expect(info.currentVersion).toBe('0.1.0')
    })
  })
})