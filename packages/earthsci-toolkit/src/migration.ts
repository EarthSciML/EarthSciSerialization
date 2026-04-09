/**
 * Migration utilities for ESM format version upgrades.
 *
 * Provides functions to migrate ESM files between schema versions.
 */

import type { EsmFile } from './types.js'

/**
 * Error thrown when migration fails.
 */
export class MigrationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'MigrationError'
  }
}

/**
 * Check if migration is possible from the source version to target version.
 */
export function canMigrate(sourceVersion: string, targetVersion: string): boolean {
  const supported = getSupportedMigrationTargets(sourceVersion)
  return supported.includes(targetVersion)
}

/**
 * Get the list of schema versions that a given source version can migrate to.
 */
export function getSupportedMigrationTargets(sourceVersion: string): string[] {
  const migrations: Record<string, string[]> = {
    '0.0.5': ['0.1.0'],
  }
  return migrations[sourceVersion] || []
}

/**
 * Migrate an ESM file from its current schema version to the target version.
 */
export function migrate(file: EsmFile, targetVersion: string): EsmFile {
  const sourceVersion = file.metadata?.schema_version || file.metadata?.version
  if (!sourceVersion) {
    throw new MigrationError('Source file has no schema_version in metadata')
  }

  if (!canMigrate(sourceVersion, targetVersion)) {
    throw new MigrationError(
      `Migration from ${sourceVersion} to ${targetVersion} is not supported`
    )
  }

  // Return a copy — actual migration logic is version-pair specific
  return { ...file }
}
