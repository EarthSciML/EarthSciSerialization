/**
 * ESM Format JSON Parsing
 *
 * Provides functionality to load and validate ESM files from JSON strings or objects.
 * Separates concerns: JSON parsing → schema validation → type coercion.
 */
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
// Get the directory of this module for schema loading
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
/**
 * Parse error - thrown when JSON parsing fails
 */
export class ParseError extends Error {
    originalError;
    constructor(message, originalError) {
        super(message);
        this.originalError = originalError;
        this.name = 'ParseError';
    }
}
/**
 * Schema validation error - thrown when schema validation fails
 */
export class SchemaValidationError extends Error {
    errors;
    constructor(message, errors) {
        super(message);
        this.errors = errors;
        this.name = 'SchemaValidationError';
    }
}
// Load and compile the schema at module load time
const schemaPath = join(__dirname, '..', 'schema', 'esm-schema.json');
let schema;
let validator;
try {
    const schemaText = readFileSync(schemaPath, 'utf-8');
    schema = JSON.parse(schemaText);
    const ajv = new Ajv({
        allErrors: true,
        verbose: true,
        strict: false, // Allow unknown keywords for compatibility
        addUsedSchema: false, // Don't add the schema to cache
        validateSchema: false // Skip schema validation for now
    });
    addFormats(ajv);
    validator = ajv.compile(schema);
}
catch (error) {
    throw new Error(`Failed to load or compile ESM schema from ${schemaPath}: ${error}`);
}
/**
 * Validate data against the ESM schema
 */
export function validateSchema(data) {
    const isValid = validator(data);
    if (isValid || !validator.errors) {
        return [];
    }
    return validator.errors.map((error) => ({
        path: error.instancePath || '/',
        message: error.message || 'Unknown validation error',
        keyword: error.keyword
    }));
}
/**
 * Parse JSON string safely
 */
function parseJson(input) {
    try {
        return JSON.parse(input);
    }
    catch (error) {
        throw new ParseError(`Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`, error instanceof Error ? error : undefined);
    }
}
/**
 * Coerce types for better TypeScript compatibility
 * Handles Expression union types and discriminated unions
 */
function coerceTypes(data) {
    if (data === null || data === undefined) {
        return data;
    }
    if (Array.isArray(data)) {
        return data.map(coerceTypes);
    }
    if (typeof data === 'object') {
        const result = {};
        for (const [key, value] of Object.entries(data)) {
            // Handle Expression types - they can be number, string, or ExpressionNode
            // ExpressionNode has 'op' and 'args' properties
            if (key === 'expression' || key === 'args' || /expr/i.test(key)) {
                result[key] = coerceExpression(value);
            }
            else {
                result[key] = coerceTypes(value);
            }
        }
        return result;
    }
    return data;
}
/**
 * Coerce Expression union type (number | string | ExpressionNode)
 */
function coerceExpression(value) {
    if (typeof value === 'number' || typeof value === 'string') {
        return value;
    }
    // If it's an object with 'op' and 'args', treat as ExpressionNode
    if (value && typeof value === 'object' && 'op' in value && 'args' in value) {
        return {
            ...value,
            args: Array.isArray(value.args) ? value.args.map(coerceExpression) : value.args
        };
    }
    return value;
}
/**
 * Load an ESM file from a JSON string or pre-parsed object
 *
 * @param input - JSON string or pre-parsed JavaScript object
 * @returns Typed EsmFile object
 * @throws {ParseError} When JSON parsing fails
 * @throws {SchemaValidationError} When schema validation fails
 */
export function load(input) {
    // Step 1: JSON parsing
    let data;
    if (typeof input === 'string') {
        data = parseJson(input);
    }
    else {
        data = input;
    }
    // Step 2: Schema validation
    const schemaErrors = validateSchema(data);
    if (schemaErrors.length > 0) {
        throw new SchemaValidationError(`Schema validation failed with ${schemaErrors.length} error(s)`, schemaErrors);
    }
    // Step 3: Type coercion
    const typedData = coerceTypes(data);
    return typedData;
}
//# sourceMappingURL=parse.js.map