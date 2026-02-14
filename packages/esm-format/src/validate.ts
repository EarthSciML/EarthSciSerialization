/**
 * ESM Format validation wrapper for cross-language conformance testing.
 *
 * Provides a standardized validation interface that matches the format expected
 * by the conformance test runner across all language implementations.
 */

import { validateSchema, load, type SchemaError } from './parse.js';

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
}

/**
 * Convert a SchemaError to our ValidationError format
 */
function convertSchemaError(error: SchemaError): ValidationError {
    return {
        path: error.path,
        message: error.message,
        code: error.keyword,
        details: {
            keyword: error.keyword
        }
    };
}

/**
 * Validate ESM data and return structured validation result.
 *
 * @param data - ESM data as JSON string or object
 * @returns ValidationResult with validation status and errors
 */
export function validate(data: string | object): ValidationResult {
    const schema_errors: ValidationError[] = [];
    const structural_errors: ValidationError[] = [];

    try {
        let parsedData: object;

        // Parse JSON if string
        if (typeof data === 'string') {
            try {
                parsedData = JSON.parse(data);
            } catch (e: unknown) {
                const error = e as Error;
                return {
                    is_valid: false,
                    schema_errors: [{
                        path: '$',
                        message: `Invalid JSON: ${error.message}`,
                        code: 'json_parse_error',
                        details: { error: error.message }
                    }],
                    structural_errors: []
                };
            }
        } else {
            parsedData = data;
        }

        // Validate against schema
        const schemaErrors = validateSchema(parsedData);
        schema_errors.push(...schemaErrors.map(convertSchemaError));

        // Try structural validation by loading the data
        if (schema_errors.length === 0) {
            try {
                load(parsedData);
                // If load succeeds, structural validation passed
            } catch (e: unknown) {
                const error = e as Error;
                structural_errors.push({
                    path: '$',
                    message: error.message || String(e),
                    code: error.constructor.name.toLowerCase().replace('error', ''),
                    details: {
                        exception_type: error.constructor.name,
                        error: error.message || String(e)
                    }
                });
            }
        }

    } catch (e: unknown) {
        // Unexpected error
        const error = e as Error;
        return {
            is_valid: false,
            schema_errors: [{
                path: '$',
                message: `Validation failed with unexpected error: ${error.message || String(e)}`,
                code: 'unexpected_error',
                details: {
                    exception_type: error.constructor.name,
                    error: error.message || String(e)
                }
            }],
            structural_errors: []
        };
    }

    return {
        is_valid: schema_errors.length === 0 && structural_errors.length === 0,
        schema_errors,
        structural_errors
    };
}