/**
 * ESM Format validation wrapper for cross-language conformance testing.
 *
 * Provides a standardized validation interface that matches the format expected
 * by the conformance test runner across all language implementations.
 */
import { type UnitWarning } from './units.js';
/**
 * Validation error with structured details
 */
export interface ValidationError {
    path: string;
    message: string;
    code: string;
    details: Record<string, any>;
}
/**
 * Structured validation result
 */
export interface ValidationResult {
    is_valid: boolean;
    schema_errors: ValidationError[];
    structural_errors: ValidationError[];
    unit_warnings: UnitWarning[];
}
/**
 * Structural error type matching the format specification
 */
export interface StructuralError {
    path: string;
    message: string;
    code: string;
    details: Record<string, any>;
}
/**
 * Validate ESM data and return structured validation result.
 *
 * @param data - ESM data as JSON string or object
 * @returns ValidationResult with validation status and errors
 */
export declare function validate(data: string | object): ValidationResult;
//# sourceMappingURL=validate.d.ts.map