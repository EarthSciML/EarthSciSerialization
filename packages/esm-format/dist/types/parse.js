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
 * Parse a semantic version string and return its components
 */
function parseSemanticVersion(versionString) {
    const match = versionString.match(/^(\d+)\.(\d+)\.(\d+)$/);
    if (!match) {
        return null;
    }
    return {
        major: parseInt(match[1], 10),
        minor: parseInt(match[2], 10),
        patch: parseInt(match[3], 10)
    };
}
/**
 * Check version compatibility for an ESM file
 */
function checkVersionCompatibility(data) {
    if (typeof data !== 'object' || data === null) {
        return; // Let schema validation handle this
    }
    const version = data.esm;
    if (typeof version !== 'string') {
        return; // Let schema validation handle this
    }
    const versionComponents = parseSemanticVersion(version);
    if (versionComponents === null) {
        return; // Let schema validation handle invalid version format
    }
    const { major } = versionComponents;
    const CURRENT_MAJOR = 0; // Current supported major version
    // Reject unsupported major versions
    if (major !== CURRENT_MAJOR) {
        throw new ParseError(`Unsupported major version ${major}. This parser supports major version ${CURRENT_MAJOR}.`);
    }
}
/**
 * Version-aware schema validation that handles backward/forward compatibility
 */
function validateSchemaWithVersionCompatibility(data) {
    if (typeof data !== 'object' || data === null) {
        return validateSchema(data);
    }
    const version = data.esm;
    if (typeof version !== 'string') {
        return validateSchema(data);
    }
    const versionComponents = parseSemanticVersion(version);
    if (versionComponents === null) {
        // If version parsing fails, use normal validation
        return validateSchema(data);
    }
    const { major, minor, patch } = versionComponents;
    const CURRENT_VERSION = { major: 0, minor: 1, patch: 0 };
    // If it's the exact current version, use normal validation
    if (major === CURRENT_VERSION.major && minor === CURRENT_VERSION.minor && patch === CURRENT_VERSION.patch) {
        return validateSchema(data);
    }
    // For backward/forward compatibility within the same major version,
    // first check if there are actual compatibility issues that need to be ignored
    if (major === CURRENT_VERSION.major) {
        // Try validation with original version first to see if version is the only issue
        const originalErrors = validateSchema(data);
        // If there are no additional properties errors, then version mismatch should fail
        const hasAdditionalPropsErrors = originalErrors.some(error => error.keyword === 'additionalProperties');
        // If only version error and no additional properties, enforce strict version matching
        if (!hasAdditionalPropsErrors && (minor !== CURRENT_VERSION.minor || patch !== CURRENT_VERSION.patch)) {
            return originalErrors;
        }
        // Generate forward compatibility warnings for actual compatibility cases
        if (minor > CURRENT_VERSION.minor) {
            console.warn(`Forward compatibility: Version ${version} is newer than current ${CURRENT_VERSION.major}.${CURRENT_VERSION.minor}.${CURRENT_VERSION.patch}. Some features may not be fully supported.`);
        }
        const tempData = { ...data, esm: '0.1.0' };
        const errors = validateSchema(tempData);
        // Filter out additionalProperties errors for forward compatibility
        const filteredErrors = errors.filter(error => {
            // Allow additional properties for newer versions (forward compatibility)
            if (error.keyword === 'additionalProperties' &&
                (minor > CURRENT_VERSION.minor || patch > CURRENT_VERSION.patch)) {
                console.warn(`Forward compatibility: Ignoring unknown field at ${error.path}`);
                return false;
            }
            return true;
        });
        return filteredErrors;
    }
    // This shouldn't happen due to checkVersionCompatibility, but fallback to normal validation
    return validateSchema(data);
}
/**
 * Remove unknown fields for forward compatibility
 */
function removeUnknownFields(data) {
    if (typeof data !== 'object' || data === null) {
        return data;
    }
    const version = data.esm;
    if (typeof version !== 'string') {
        return data;
    }
    const versionComponents = parseSemanticVersion(version);
    if (versionComponents === null) {
        return data;
    }
    const { major, minor } = versionComponents;
    const CURRENT_VERSION = { major: 0, minor: 1, patch: 0 };
    // Only clean up for forward compatible versions (newer minor versions in the same major)
    if (major === CURRENT_VERSION.major && minor > CURRENT_VERSION.minor) {
        // Create a copy of the data and remove fields that would cause schema validation errors
        const cleanedData = { ...data };
        // Remove known forward compatibility fields that aren't in the current schema
        const unknownRootFields = ['performance_hints', 'validation_metadata', 'extended_metadata'];
        unknownRootFields.forEach(field => {
            if (field in cleanedData) {
                delete cleanedData[field];
            }
        });
        // Recursively clean model and reaction system objects
        if (cleanedData.models) {
            cleanedData.models = cleanModels(cleanedData.models);
        }
        if (cleanedData.reaction_systems) {
            cleanedData.reaction_systems = cleanReactionSystems(cleanedData.reaction_systems);
        }
        return cleanedData;
    }
    return data;
}
/**
 * Clean unknown fields from models
 */
function cleanModels(models) {
    if (typeof models !== 'object' || models === null) {
        return models;
    }
    const cleaned = {};
    for (const [key, model] of Object.entries(models)) {
        if (typeof model === 'object' && model !== null) {
            const cleanedModel = { ...model };
            // Remove known forward compatibility fields
            const unknownModelFields = ['solver_hints', 'optimization_flags'];
            unknownModelFields.forEach(field => {
                if (field in cleanedModel) {
                    delete cleanedModel[field];
                }
            });
            cleaned[key] = cleanedModel;
        }
        else {
            cleaned[key] = model;
        }
    }
    return cleaned;
}
/**
 * Clean unknown fields from reaction systems
 */
function cleanReactionSystems(reactionSystems) {
    if (typeof reactionSystems !== 'object' || reactionSystems === null) {
        return reactionSystems;
    }
    const cleaned = {};
    for (const [key, system] of Object.entries(reactionSystems)) {
        if (typeof system === 'object' && system !== null) {
            const cleanedSystem = { ...system };
            // Clean reactions array
            if (Array.isArray(cleanedSystem.reactions)) {
                cleanedSystem.reactions = cleanedSystem.reactions.map((reaction) => {
                    if (typeof reaction === 'object' && reaction !== null) {
                        const cleanedReaction = { ...reaction };
                        // Remove known forward compatibility fields from reactions
                        const unknownReactionFields = ['kinetics_metadata', 'thermodynamic_data'];
                        unknownReactionFields.forEach(field => {
                            if (field in cleanedReaction) {
                                delete cleanedReaction[field];
                            }
                        });
                        return cleanedReaction;
                    }
                    return reaction;
                });
            }
            cleaned[key] = cleanedSystem;
        }
        else {
            cleaned[key] = system;
        }
    }
    return cleaned;
}
/**
 * Load an ESM file from a JSON string or pre-parsed object
 *
 * @param input - JSON string or pre-parsed JavaScript object
 * @returns Typed EsmFile object
 * @throws {ParseError} When JSON parsing fails or version is incompatible
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
    // Step 2: Version compatibility check (before schema validation)
    checkVersionCompatibility(data);
    // Step 3: Schema validation with version compatibility
    const schemaErrors = validateSchemaWithVersionCompatibility(data);
    if (schemaErrors.length > 0) {
        throw new SchemaValidationError(`Schema validation failed with ${schemaErrors.length} error(s)`, schemaErrors);
    }
    // Step 4: Clean up unknown fields for forward compatibility and type coercion
    const cleanedData = removeUnknownFields(data);
    const typedData = coerceTypes(cleanedData);
    return typedData;
}
//# sourceMappingURL=parse.js.map