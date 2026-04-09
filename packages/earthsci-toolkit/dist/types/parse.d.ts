/**
 * ESM Format JSON Parsing
 *
 * Provides functionality to load and validate ESM files from JSON strings or objects.
 * Separates concerns: JSON parsing → schema validation → type coercion.
 */
import type { EsmFile } from './types.js';
/**
 * Schema validation error with JSON Pointer path
 */
export interface SchemaError {
    /** JSON Pointer path to the error location */
    path: string;
    /** Human-readable error message */
    message: string;
    /** AJV validation keyword that failed */
    keyword: string;
}
/**
 * Parse error - thrown when JSON parsing fails
 */
export declare class ParseError extends Error {
    originalError?: Error;
    constructor(message: string, originalError?: Error);
}
/**
 * Schema validation error - thrown when schema validation fails
 */
export declare class SchemaValidationError extends Error {
    errors: SchemaError[];
    constructor(message: string, errors: SchemaError[]);
}
/**
 * Validate data against the ESM schema
 */
export declare function validateSchema(data: unknown): SchemaError[];
/**
 * Load an ESM file from a JSON string or pre-parsed object
 *
 * @param input - JSON string or pre-parsed JavaScript object
 * @returns Typed EsmFile object
 * @throws {ParseError} When JSON parsing fails or version is incompatible
 * @throws {SchemaValidationError} When schema validation fails
 */
export declare function load(input: string | object): EsmFile;
//# sourceMappingURL=parse.d.ts.map