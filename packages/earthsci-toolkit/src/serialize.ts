/**
 * ESM Format JSON Serialization
 *
 * Provides functionality to serialize EsmFile objects to JSON strings.
 */

import type { EsmFile } from './types.js'

/**
 * Serialize an EsmFile object to a formatted JSON string
 *
 * @param file - The EsmFile object to serialize
 * @returns Formatted JSON string representation
 */
export function save(file: EsmFile): string {
  // Use JSON.stringify with formatting for readable output
  // 2 spaces for indentation to match common formatting conventions
  return JSON.stringify(file, null, 2)
}