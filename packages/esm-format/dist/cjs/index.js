'use strict';

var Ajv = require('ajv');
var addFormats = require('ajv-formats');
var fs = require('fs');
var url = require('url');
var path = require('path');

var _documentCurrentScript = typeof document !== 'undefined' ? document.currentScript : null;
/**
 * ESM Format JSON Parsing
 *
 * Provides functionality to load and validate ESM files from JSON strings or objects.
 * Separates concerns: JSON parsing → schema validation → type coercion.
 */
// Get the directory of this module for schema loading
const __filename$1 = url.fileURLToPath((typeof document === 'undefined' ? require('u' + 'rl').pathToFileURL(__filename).href : (_documentCurrentScript && _documentCurrentScript.tagName.toUpperCase() === 'SCRIPT' && _documentCurrentScript.src || new URL('index.js', document.baseURI).href)));
const __dirname$1 = path.dirname(__filename$1);
/**
 * Parse error - thrown when JSON parsing fails
 */
class ParseError extends Error {
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
class SchemaValidationError extends Error {
    errors;
    constructor(message, errors) {
        super(message);
        this.errors = errors;
        this.name = 'SchemaValidationError';
    }
}
// Load and compile the schema at module load time
const schemaPath = path.join(__dirname$1, '..', 'schema', 'esm-schema.json');
let schema;
let validator;
try {
    const schemaText = fs.readFileSync(schemaPath, 'utf-8');
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
function validateSchema(data) {
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
function load(input) {
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

/**
 * ESM Format JSON Serialization
 *
 * Provides functionality to serialize EsmFile objects to JSON strings.
 */
/**
 * Serialize an EsmFile object to a formatted JSON string
 *
 * @param file - The EsmFile object to serialize
 * @returns Formatted JSON string representation
 */
function save(file) {
    // Use JSON.stringify with formatting for readable output
    // 2 spaces for indentation to match common formatting conventions
    return JSON.stringify(file, null, 2);
}

/**
 * ESM Format validation wrapper for cross-language conformance testing.
 *
 * Provides a standardized validation interface that matches the format expected
 * by the conformance test runner across all language implementations.
 */
/**
 * Extract all variable references from an expression
 */
function extractVariableReferences(expr) {
    const variables = [];
    function visit(node) {
        if (typeof node === 'string') {
            // String references are variable names
            variables.push(node);
        }
        else if (typeof node === 'number') {
            // Numbers are literals, no variables
            return;
        }
        else if (node && typeof node === 'object' && 'op' in node) {
            // Expression node - recursively visit arguments
            const exprNode = node;
            if (exprNode.args) {
                for (const arg of exprNode.args) {
                    visit(arg);
                }
            }
        }
    }
    visit(expr);
    return Array.from(new Set(variables)); // Remove duplicates
}
/**
 * Count D(var, t) derivatives in an expression
 */
function countDerivatives(expr) {
    const derivatives = {};
    function visit(node) {
        if (typeof node === 'object' && node && 'op' in node) {
            const exprNode = node;
            if (exprNode.op === 'D' && exprNode.args.length >= 1) {
                const firstArg = exprNode.args[0];
                if (typeof firstArg === 'string') {
                    derivatives[firstArg] = (derivatives[firstArg] || 0) + 1;
                }
            }
            // Recursively visit all arguments
            if (exprNode.args) {
                for (const arg of exprNode.args) {
                    visit(arg);
                }
            }
        }
    }
    visit(expr);
    return derivatives;
}
/**
 * Resolve scoped variable reference like "Model.Subsystem.var"
 */
function resolveScopedReference(reference, esmFile) {
    const parts = reference.split('.');
    if (parts.length < 2) {
        return false; // Not a scoped reference
    }
    const [systemName, ...pathParts] = parts;
    const variableName = pathParts.pop();
    // Try to find in models
    if (esmFile.models && esmFile.models[systemName]) {
        let current = esmFile.models[systemName];
        // Navigate through subsystems
        for (const pathPart of pathParts) {
            if (!current.subsystems || !current.subsystems[pathPart]) {
                return false;
            }
            current = current.subsystems[pathPart];
        }
        // Check if variable exists
        return current.variables && variableName in current.variables;
    }
    // Try to find in reaction systems
    if (esmFile.reaction_systems && esmFile.reaction_systems[systemName]) {
        let current = esmFile.reaction_systems[systemName];
        // Navigate through subsystems
        for (const pathPart of pathParts) {
            if (!current.subsystems || !current.subsystems[pathPart]) {
                return false;
            }
            current = current.subsystems[pathPart];
        }
        // Check if species or parameter exists
        return (current.species && variableName in current.species) ||
            (current.parameters && variableName in current.parameters);
    }
    return false;
}
/**
 * Check equation-unknown balance for a model
 */
function validateEquationBalance(model, modelPath) {
    const errors = [];
    // Count state variables
    const stateVariables = Object.entries(model.variables || {})
        .filter(([_, variable]) => variable.type === 'state')
        .map(([name, _]) => name);
    // Count D(var,t) equations by looking at all equation LHS expressions
    const derivativeCounts = {};
    for (const equation of model.equations || []) {
        const lhsDerivatives = countDerivatives(equation.lhs);
        for (const [variable, count] of Object.entries(lhsDerivatives)) {
            derivativeCounts[variable] = (derivativeCounts[variable] || 0) + count;
        }
    }
    const odeEquationCount = Object.values(derivativeCounts).reduce((sum, count) => sum + count, 0);
    if (stateVariables.length !== odeEquationCount) {
        const missingEquations = stateVariables.filter(varName => !(varName in derivativeCounts));
        errors.push({
            path: modelPath,
            code: 'equation_count_mismatch',
            message: `Number of ODE equations (${odeEquationCount}) does not match number of state variables (${stateVariables.length})`,
            details: {
                state_variables: stateVariables,
                ode_equations: odeEquationCount,
                missing_equations_for: missingEquations
            }
        });
    }
    return errors;
}
/**
 * Check reference integrity for a model
 */
function validateReferenceIntegrity(model, modelPath, esmFile) {
    const errors = [];
    const declaredVariables = new Set(Object.keys(model.variables || {}));
    // Check equations
    for (let i = 0; i < (model.equations || []).length; i++) {
        const equation = model.equations[i];
        const equationPath = `${modelPath}/equations/${i}`;
        // Check LHS variables
        const lhsVars = extractVariableReferences(equation.lhs);
        for (const varRef of lhsVars) {
            if (varRef.includes('.')) {
                // Scoped reference
                if (!resolveScopedReference(varRef, esmFile)) {
                    errors.push({
                        path: `${equationPath}/lhs`,
                        code: 'unresolved_scoped_ref',
                        message: `Scoped reference "${varRef}" cannot be resolved`,
                        details: { reference: varRef }
                    });
                }
            }
            else {
                // Local reference
                if (!declaredVariables.has(varRef)) {
                    errors.push({
                        path: `${equationPath}/lhs`,
                        code: 'undefined_variable',
                        message: `Variable "${varRef}" referenced in equation is not declared`,
                        details: { variable: varRef }
                    });
                }
            }
        }
        // Check RHS variables
        const rhsVars = extractVariableReferences(equation.rhs);
        for (const varRef of rhsVars) {
            if (varRef.includes('.')) {
                // Scoped reference
                if (!resolveScopedReference(varRef, esmFile)) {
                    errors.push({
                        path: `${equationPath}/rhs`,
                        code: 'unresolved_scoped_ref',
                        message: `Scoped reference "${varRef}" cannot be resolved`,
                        details: { reference: varRef }
                    });
                }
            }
            else {
                // Local reference
                if (!declaredVariables.has(varRef)) {
                    errors.push({
                        path: `${equationPath}/rhs`,
                        code: 'undefined_variable',
                        message: `Variable "${varRef}" referenced in equation is not declared`,
                        details: { variable: varRef }
                    });
                }
            }
        }
    }
    // Check observed variables have expressions
    for (const [varName, variable] of Object.entries(model.variables || {})) {
        if (variable.type === 'observed' && !variable.expression) {
            errors.push({
                path: `${modelPath}/variables/${varName}`,
                code: 'missing_observed_expr',
                message: `Observed variable "${varName}" is missing its expression field`,
                details: { variable: varName }
            });
        }
    }
    return errors;
}
/**
 * Check discrete parameters in events
 */
function validateEventConsistency(model, modelPath) {
    const errors = [];
    const declaredVariables = new Set(Object.keys(model.variables || {}));
    const declaredParameters = new Set(Object.entries(model.variables || {})
        .filter(([_, variable]) => variable.type === 'parameter')
        .map(([name, _]) => name));
    // Check discrete events
    for (let i = 0; i < (model.discrete_events || []).length; i++) {
        const event = model.discrete_events[i];
        const eventPath = `${modelPath}/discrete_events/${i}`;
        // Check discrete_parameters entries
        if (event.discrete_parameters) {
            for (const paramName of event.discrete_parameters) {
                if (!declaredParameters.has(paramName)) {
                    errors.push({
                        path: `${eventPath}/discrete_parameters`,
                        code: 'invalid_discrete_param',
                        message: `discrete_parameters entry "${paramName}" does not match a declared parameter`,
                        details: { parameter: paramName }
                    });
                }
            }
        }
        // Check affects variables
        if (event.affects) {
            for (let j = 0; j < event.affects.length; j++) {
                const affect = event.affects[j];
                if (!declaredVariables.has(affect.lhs)) {
                    errors.push({
                        path: `${eventPath}/affects/${j}/lhs`,
                        code: 'event_var_undeclared',
                        message: `Variable "${affect.lhs}" in event affects is not declared`,
                        details: { variable: affect.lhs }
                    });
                }
            }
        }
        // Check functional affect variables
        if (event.functional_affect) {
            for (const varName of event.functional_affect.read_vars || []) {
                if (!declaredVariables.has(varName)) {
                    errors.push({
                        path: `${eventPath}/functional_affect/read_vars`,
                        code: 'event_var_undeclared',
                        message: `Variable "${varName}" in functional_affect read_vars is not declared`,
                        details: { variable: varName }
                    });
                }
            }
            for (const paramName of event.functional_affect.read_params || []) {
                if (!declaredParameters.has(paramName)) {
                    errors.push({
                        path: `${eventPath}/functional_affect/read_params`,
                        code: 'event_var_undeclared',
                        message: `Parameter "${paramName}" in functional_affect read_params is not declared`,
                        details: { variable: paramName }
                    });
                }
            }
        }
    }
    return errors;
}
/**
 * Check reaction consistency for a reaction system
 */
function validateReactionConsistency(reactionSystem, systemPath) {
    const errors = [];
    const declaredSpecies = new Set(Object.keys(reactionSystem.species || {}));
    const declaredParameters = new Set(Object.keys(reactionSystem.parameters || {}));
    for (let i = 0; i < (reactionSystem.reactions || []).length; i++) {
        const reaction = reactionSystem.reactions[i];
        const reactionPath = `${systemPath}/reactions/${i}`;
        // Check for null-null reactions
        if (reaction.substrates === null && reaction.products === null) {
            errors.push({
                path: reactionPath,
                code: 'null_reaction',
                message: `Reaction "${reaction.id}" has both substrates: null and products: null`,
                details: { reaction_id: reaction.id }
            });
        }
        // Check substrates
        if (reaction.substrates && Array.isArray(reaction.substrates)) {
            for (let j = 0; j < reaction.substrates.length; j++) {
                const substrate = reaction.substrates[j];
                if (substrate && !declaredSpecies.has(substrate.species)) {
                    errors.push({
                        path: `${reactionPath}/substrates/${j}/species`,
                        code: 'undefined_species',
                        message: `Species "${substrate.species}" in reaction substrates is not declared`,
                        details: { species: substrate.species, reaction_id: reaction.id }
                    });
                }
                // Check stoichiometry is positive integer
                if (substrate && (!Number.isInteger(substrate.stoichiometry) || substrate.stoichiometry <= 0)) {
                    errors.push({
                        path: `${reactionPath}/substrates/${j}/stoichiometry`,
                        code: 'invalid_stoichiometry',
                        message: `Stoichiometry must be a positive integer, got ${substrate.stoichiometry}`,
                        details: { stoichiometry: substrate.stoichiometry, reaction_id: reaction.id }
                    });
                }
            }
        }
        // Check products
        if (reaction.products && Array.isArray(reaction.products)) {
            for (let j = 0; j < reaction.products.length; j++) {
                const product = reaction.products[j];
                if (product && !declaredSpecies.has(product.species)) {
                    errors.push({
                        path: `${reactionPath}/products/${j}/species`,
                        code: 'undefined_species',
                        message: `Species "${product.species}" in reaction products is not declared`,
                        details: { species: product.species, reaction_id: reaction.id }
                    });
                }
                // Check stoichiometry is positive integer
                if (product && (!Number.isInteger(product.stoichiometry) || product.stoichiometry <= 0)) {
                    errors.push({
                        path: `${reactionPath}/products/${j}/stoichiometry`,
                        code: 'invalid_stoichiometry',
                        message: `Stoichiometry must be a positive integer, got ${product.stoichiometry}`,
                        details: { stoichiometry: product.stoichiometry, reaction_id: reaction.id }
                    });
                }
            }
        }
        // Check rate expression references
        const rateVars = extractVariableReferences(reaction.rate);
        for (const varRef of rateVars) {
            if (!declaredSpecies.has(varRef) && !declaredParameters.has(varRef)) {
                errors.push({
                    path: `${reactionPath}/rate`,
                    code: 'undefined_parameter',
                    message: `Variable "${varRef}" in rate expression is not declared as species or parameter`,
                    details: { variable: varRef, reaction_id: reaction.id }
                });
            }
        }
    }
    return errors;
}
/**
 * Check coupling entries reference integrity
 */
function validateCouplingIntegrity(esmFile) {
    const errors = [];
    if (!esmFile.coupling)
        return errors;
    // Collect all available systems
    const availableSystems = new Set([
        ...Object.keys(esmFile.models || {}),
        ...Object.keys(esmFile.reaction_systems || {}),
        ...Object.keys(esmFile.data_loaders || {}),
        ...Object.keys(esmFile.operators || {})
    ]);
    for (let i = 0; i < esmFile.coupling.length; i++) {
        const coupling = esmFile.coupling[i];
        const couplingPath = `/coupling/${i}`;
        if (coupling.type === 'operator_compose') {
            // Check systems exist
            const composeEntry = coupling;
            for (const systemName of composeEntry.systems) {
                if (!availableSystems.has(systemName)) {
                    errors.push({
                        path: `${couplingPath}/systems`,
                        code: 'undefined_system',
                        message: `Coupling entry references nonexistent system "${systemName}"`,
                        details: { system: systemName }
                    });
                }
            }
        }
        else if (coupling.type === 'couple2') {
            // Check systems exist
            const couple2Entry = coupling;
            for (const systemName of couple2Entry.systems) {
                if (!availableSystems.has(systemName)) {
                    errors.push({
                        path: `${couplingPath}/systems`,
                        code: 'undefined_system',
                        message: `Coupling entry references nonexistent system "${systemName}"`,
                        details: { system: systemName }
                    });
                }
            }
        }
        else if (coupling.type === 'operator_apply') {
            // Check operator exists
            const applyEntry = coupling;
            if (applyEntry.operator && !availableSystems.has(applyEntry.operator)) {
                errors.push({
                    path: `${couplingPath}/operator`,
                    code: 'undefined_operator',
                    message: `operator_apply references nonexistent operator "${applyEntry.operator}"`,
                    details: { operator: applyEntry.operator }
                });
            }
        }
    }
    return errors;
}
/**
 * Main structural validation function
 */
function performStructuralValidation(esmFile) {
    const errors = [];
    // Validate models
    if (esmFile.models) {
        for (const [modelName, model] of Object.entries(esmFile.models)) {
            const modelPath = `/models/${modelName}`;
            errors.push(...validateEquationBalance(model, modelPath));
            errors.push(...validateReferenceIntegrity(model, modelPath, esmFile));
            errors.push(...validateEventConsistency(model, modelPath));
            // Recursively validate subsystems
            if (model.subsystems) {
                for (const [subsystemName, subsystem] of Object.entries(model.subsystems)) {
                    const subsystemPath = `${modelPath}/subsystems/${subsystemName}`;
                    errors.push(...validateEquationBalance(subsystem, subsystemPath));
                    errors.push(...validateReferenceIntegrity(subsystem, subsystemPath, esmFile));
                    errors.push(...validateEventConsistency(subsystem, subsystemPath));
                }
            }
        }
    }
    // Validate reaction systems
    if (esmFile.reaction_systems) {
        for (const [systemName, reactionSystem] of Object.entries(esmFile.reaction_systems)) {
            const systemPath = `/reaction_systems/${systemName}`;
            errors.push(...validateReactionConsistency(reactionSystem, systemPath));
            // Recursively validate subsystems
            if (reactionSystem.subsystems) {
                for (const [subsystemName, subsystem] of Object.entries(reactionSystem.subsystems)) {
                    const subsystemPath = `${systemPath}/subsystems/${subsystemName}`;
                    errors.push(...validateReactionConsistency(subsystem, subsystemPath));
                }
            }
        }
    }
    // Validate coupling integrity
    errors.push(...validateCouplingIntegrity(esmFile));
    return errors;
}
/**
 * Convert a SchemaError to our ValidationError format
 */
function convertSchemaError(error) {
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
function validate(data) {
    const schema_errors = [];
    const structural_errors = [];
    try {
        let parsedData;
        // Parse JSON if string
        if (typeof data === 'string') {
            try {
                parsedData = JSON.parse(data);
            }
            catch (e) {
                const error = e;
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
        }
        else {
            parsedData = data;
        }
        // Validate against schema
        const schemaErrors = validateSchema(parsedData);
        schema_errors.push(...schemaErrors.map(convertSchemaError));
        // Try structural validation by loading the data
        if (schema_errors.length === 0) {
            try {
                const esmFile = load(parsedData);
                // Perform structural validation
                const structuralErrors = performStructuralValidation(esmFile);
                structural_errors.push(...structuralErrors.map(err => ({
                    path: err.path,
                    message: err.message,
                    code: err.code,
                    details: err.details
                })));
            }
            catch (e) {
                const error = e;
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
    }
    catch (e) {
        // Unexpected error
        const error = e;
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

/**
 * Graph generation utilities for ESM files
 *
 * Provides functions to extract different graph representations from ESM files,
 * as specified in the ESM Libraries Specification Section 4.8.
 */
/**
 * Extract the system graph from an ESM file.
 * Returns a directed graph where nodes are model components and edges are coupling rules.
 */
function component_graph(esmFile) {
    const nodes = [];
    const edges = [];
    // Extract nodes from different component types
    // Models
    if (esmFile.models) {
        for (const [id, model] of Object.entries(esmFile.models)) {
            nodes.push({
                id,
                name: id,
                type: 'model',
                description: model.reference?.notes,
                reference: model.reference
            });
        }
    }
    // Reaction systems
    if (esmFile.reaction_systems) {
        for (const [id, reactionSystem] of Object.entries(esmFile.reaction_systems)) {
            nodes.push({
                id,
                name: id,
                type: 'reaction_system',
                description: reactionSystem.reference?.notes,
                reference: reactionSystem.reference
            });
        }
    }
    // Data loaders
    if (esmFile.data_loaders) {
        for (const [id, dataLoader] of Object.entries(esmFile.data_loaders)) {
            nodes.push({
                id,
                name: id,
                type: 'data_loader',
                description: dataLoader.reference?.notes,
                reference: dataLoader.reference
            });
        }
    }
    // Operators
    if (esmFile.operators) {
        for (const [id, operator] of Object.entries(esmFile.operators)) {
            nodes.push({
                id,
                name: id,
                type: 'operator',
                description: operator.reference?.notes,
                reference: operator.reference
            });
        }
    }
    // Extract edges from coupling entries
    if (esmFile.coupling) {
        esmFile.coupling.forEach((coupling, index) => {
            const edgeId = `coupling-${index}`;
            switch (coupling.type) {
                case 'operator_compose':
                    // operator_compose connects multiple systems
                    if (coupling.systems && coupling.systems.length >= 2) {
                        // Create edges between consecutive systems
                        for (let i = 0; i < coupling.systems.length - 1; i++) {
                            edges.push({
                                id: `${edgeId}-${i}`,
                                from: coupling.systems[i],
                                to: coupling.systems[i + 1],
                                type: 'operator_compose',
                                label: 'compose',
                                description: coupling.description,
                                coupling
                            });
                        }
                    }
                    break;
                case 'couple2':
                    // couple2 connects exactly two systems
                    if (coupling.systems && coupling.systems.length === 2) {
                        edges.push({
                            id: edgeId,
                            from: coupling.systems[0],
                            to: coupling.systems[1],
                            type: 'couple2',
                            label: 'couple',
                            description: coupling.description,
                            coupling
                        });
                    }
                    break;
                case 'variable_map':
                    // variable_map connects two variables from different components
                    if (coupling.from && coupling.to) {
                        const fromParts = coupling.from.split('.');
                        const toParts = coupling.to.split('.');
                        if (fromParts.length >= 2 && toParts.length >= 2) {
                            const fromComponent = fromParts[0];
                            const toComponent = toParts[0];
                            const variable = fromParts.slice(1).join('.');
                            edges.push({
                                id: edgeId,
                                from: fromComponent,
                                to: toComponent,
                                type: 'variable_map',
                                label: variable,
                                description: coupling.description || `${coupling.from} → ${coupling.to}`,
                                coupling
                            });
                        }
                    }
                    break;
                case 'operator_apply':
                    // operator_apply applies an operator to a system
                    if (coupling.operator && coupling.system) {
                        edges.push({
                            id: edgeId,
                            from: coupling.operator,
                            to: coupling.system,
                            type: 'operator_apply',
                            label: 'apply',
                            description: coupling.description,
                            coupling
                        });
                    }
                    break;
                case 'callback':
                    // callback connects a source to a target via a callback function
                    if (coupling.source && coupling.target) {
                        edges.push({
                            id: edgeId,
                            from: coupling.source,
                            to: coupling.target,
                            type: 'callback',
                            label: coupling.callback || 'callback',
                            description: coupling.description,
                            coupling
                        });
                    }
                    break;
                default:
                    console.warn(`Unknown coupling type: ${coupling.type}`);
                    break;
            }
        });
    }
    return { nodes, edges };
}
/**
 * Utility to check if a component exists in the ESM file
 */
function componentExists(esmFile, componentId) {
    return !!(esmFile.models?.[componentId] ||
        esmFile.reaction_systems?.[componentId] ||
        esmFile.data_loaders?.[componentId] ||
        esmFile.operators?.[componentId]);
}
/**
 * Get the type of a component by its ID
 */
function getComponentType(esmFile, componentId) {
    if (esmFile.models?.[componentId])
        return 'model';
    if (esmFile.reaction_systems?.[componentId])
        return 'reaction_system';
    if (esmFile.data_loaders?.[componentId])
        return 'data_loader';
    if (esmFile.operators?.[componentId])
        return 'operator';
    return null;
}

/**
 * Pretty-printing formatters for ESM format expressions, equations, models, and files.
 *
 * Implements three output formats:
 * - toUnicode(): Unicode mathematical notation with chemical subscripts
 * - toLatex(): LaTeX mathematical notation
 * - toAscii(): Plain text representation
 *
 * Based on ESM Format Specification Section 6.1
 */
// Element lookup table for chemical subscript detection (118 elements)
const ELEMENTS = new Set([
    // Period 1
    'H', 'He',
    // Period 2
    'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
    // Period 3
    'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
    // Period 4
    'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
    // Period 5
    'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe',
    // Period 6
    'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
    'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
    // Period 7
    'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr',
    'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'
]);
// Unicode subscripts for digits 0-9
const SUBSCRIPT_DIGITS = '₀₁₂₃₄₅₆₇₈₉';
// Unicode superscripts for digits 0-9 and signs
const SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻'
};
function toSuperscript(text) {
    return text.split('').map(c => SUPERSCRIPT_MAP[c] || c).join('');
}
/**
 * Apply element-aware chemical subscript formatting to a variable name.
 * Uses greedy 2-char-before-1-char matching for element detection.
 */
function formatChemicalSubscripts(variable, format) {
    // Check if variable looks like a chemical formula (starts with element and has digits)
    const hasElements = hasElementPattern(variable);
    if (format === 'latex') {
        if (hasElements) {
            // Chemical formula: wrap in \mathrm{} and convert digits to subscripts
            let result = variable;
            result = result.replace(/(\d+)/g, (match, digits) => {
                // Single digits don't need braces in LaTeX subscripts
                return digits.length === 1 ? `_${digits}` : `_{${digits}}`;
            });
            return `\\mathrm{${result}}`;
        }
        else {
            // Regular variable: return as-is
            return variable;
        }
    }
    if (!hasElements) {
        // No element pattern found, return as-is
        return variable;
    }
    // For unicode: element-aware subscript detection
    let result = '';
    let i = 0;
    while (i < variable.length) {
        let matched = false;
        // Try 2-character element first
        if (i + 1 < variable.length) {
            const twoChar = variable.slice(i, i + 2);
            if (ELEMENTS.has(twoChar)) {
                result += twoChar;
                i += 2;
                // Convert following digits to subscripts
                while (i < variable.length && /\d/.test(variable[i])) {
                    result += SUBSCRIPT_DIGITS[parseInt(variable[i])];
                    i++;
                }
                matched = true;
            }
        }
        // Try 1-character element if 2-char didn't match
        if (!matched && i < variable.length) {
            const oneChar = variable[i];
            if (ELEMENTS.has(oneChar)) {
                result += oneChar;
                i++;
                // Convert following digits to subscripts
                while (i < variable.length && /\d/.test(variable[i])) {
                    result += SUBSCRIPT_DIGITS[parseInt(variable[i])];
                    i++;
                }
                matched = true;
            }
        }
        // If not an element, copy character as-is
        if (!matched) {
            result += variable[i];
            i++;
        }
    }
    return result;
}
/**
 * Check if a variable has element patterns (for chemical formula detection)
 */
function hasElementPattern(variable) {
    let i = 0;
    let hasElement = false;
    while (i < variable.length) {
        // Skip non-alphabetic characters at the start
        while (i < variable.length && !/[A-Za-z]/.test(variable[i])) {
            i++;
        }
        if (i >= variable.length)
            break;
        // Try 2-character element first
        if (i + 1 < variable.length) {
            const twoChar = variable.slice(i, i + 2);
            if (ELEMENTS.has(twoChar)) {
                hasElement = true;
                i += 2;
                // Skip digits
                while (i < variable.length && /\d/.test(variable[i])) {
                    i++;
                }
                continue;
            }
        }
        // Try 1-character element
        const oneChar = variable[i];
        if (ELEMENTS.has(oneChar)) {
            hasElement = true;
            i++;
            // Skip digits
            while (i < variable.length && /\d/.test(variable[i])) {
                i++;
            }
            continue;
        }
        // Not an element, move to next character
        i++;
    }
    return hasElement;
}
/**
 * Format a number in scientific notation with appropriate formatting
 */
function formatNumber(num, format) {
    if (Number.isInteger(num) && Math.abs(num) < 1e6) {
        return num.toString();
    }
    const str = num.toExponential();
    const [mantissa, exponent] = str.split('e');
    const exp = parseInt(exponent);
    if (format === 'unicode') {
        return `${mantissa}×10${toSuperscript(exp.toString())}`;
    }
    else if (format === 'latex') {
        return `${mantissa} \\times 10^{${exp}}`;
    }
    else {
        return str; // Plain scientific notation for ASCII
    }
}
/**
 * Get operator precedence for proper parenthesization
 */
function getOperatorPrecedence(op) {
    switch (op) {
        case 'or': return 1;
        case 'and': return 2;
        case '==':
        case '!=':
        case '<':
        case '>':
        case '<=':
        case '>=': return 3;
        case '+':
        case '-': return 4;
        case '*':
        case '/': return 5;
        case 'not': return 6; // Unary
        case '^': return 7;
        default: return 8; // Functions get highest precedence
    }
}
/**
 * Check if parentheses are needed around a subexpression
 */
function needsParentheses(parent, child, isRightOperand = false) {
    if (typeof child === 'number' || typeof child === 'string') {
        return false;
    }
    const parentPrec = getOperatorPrecedence(parent.op);
    const childPrec = getOperatorPrecedence(child.op);
    if (childPrec < parentPrec)
        return true;
    if (childPrec > parentPrec)
        return false;
    // Same precedence: need parens if child is right operand and operator is not associative
    if (isRightOperand && (parent.op === '-' || parent.op === '/' || parent.op === '^')) {
        return true;
    }
    // Special cases for function arguments - no parens needed for simple expressions
    if (['sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'abs'].includes(parent.op)) {
        // Only parenthesize for very low precedence operators
        return childPrec <= 2;
    }
    return false;
}
/**
 * Format an expression as Unicode mathematical notation
 */
function toUnicode(expr) {
    if (typeof expr === 'number') {
        return formatNumber(expr, 'unicode');
    }
    if (typeof expr === 'string') {
        return formatChemicalSubscripts(expr, 'unicode');
    }
    if ('op' in expr && 'args' in expr) {
        return formatExpressionNode(expr, 'unicode');
    }
    if ('lhs' in expr && 'rhs' in expr) {
        // Equation
        const equation = expr;
        return `${toUnicode(equation.lhs)} = ${toUnicode(equation.rhs)}`;
    }
    if ('models' in expr || 'metadata' in expr) {
        // EsmFile - model summary display (spec Section 6.3)
        return formatEsmFileSummary(expr);
    }
    if ('variables' in expr && 'equations' in expr) {
        // Model summary
        return formatModelSummary(expr);
    }
    if ('species' in expr && 'reactions' in expr) {
        // ReactionSystem summary
        return formatReactionSystemSummary(expr);
    }
    throw new Error(`Unsupported expression type: ${typeof expr}`);
}
/**
 * Format an expression as LaTeX mathematical notation
 */
function toLatex(expr) {
    if (typeof expr === 'number') {
        return formatNumber(expr, 'latex');
    }
    if (typeof expr === 'string') {
        return formatChemicalSubscripts(expr, 'latex');
    }
    if ('op' in expr && 'args' in expr) {
        return formatExpressionNode(expr, 'latex');
    }
    if ('lhs' in expr && 'rhs' in expr) {
        // Equation
        const equation = expr;
        return `${toLatex(equation.lhs)} = ${toLatex(equation.rhs)}`;
    }
    if ('models' in expr || 'metadata' in expr) {
        // EsmFile - not typically formatted as LaTeX, return plain text
        return formatEsmFileSummary(expr);
    }
    if ('variables' in expr && 'equations' in expr) {
        // Model - not typically formatted as LaTeX, return plain text
        return formatModelSummary(expr);
    }
    if ('species' in expr && 'reactions' in expr) {
        // ReactionSystem - not typically formatted as LaTeX, return plain text
        return formatReactionSystemSummary(expr);
    }
    throw new Error(`Unsupported expression type: ${typeof expr}`);
}
/**
 * Format an expression as plain ASCII text
 */
function toAscii(expr) {
    if (typeof expr === 'number') {
        return formatNumber(expr, 'ascii');
    }
    if (typeof expr === 'string') {
        return expr; // No special formatting for ASCII
    }
    if ('op' in expr && 'args' in expr) {
        return formatExpressionNode(expr, 'ascii');
    }
    if ('lhs' in expr && 'rhs' in expr) {
        // Equation
        const equation = expr;
        return `${toAscii(equation.lhs)} = ${toAscii(equation.rhs)}`;
    }
    if ('models' in expr || 'metadata' in expr) {
        // EsmFile
        return formatEsmFileSummary(expr);
    }
    if ('variables' in expr && 'equations' in expr) {
        // Model
        return formatModelSummary(expr);
    }
    if ('species' in expr && 'reactions' in expr) {
        // ReactionSystem
        return formatReactionSystemSummary(expr);
    }
    throw new Error(`Unsupported expression type: ${typeof expr}`);
}
/**
 * Format an ExpressionNode (operator with arguments)
 */
function formatExpressionNode(node, format) {
    const { op, args, wrt } = node;
    // Helper to format arguments with proper parenthesization
    const formatArg = (arg, isRightOperand = false) => {
        let result;
        if (format === 'unicode')
            result = toUnicode(arg);
        else if (format === 'latex')
            result = toLatex(arg);
        else
            result = toAscii(arg);
        if (needsParentheses(node, arg, isRightOperand)) {
            if (format === 'latex')
                return `\\left(${result}\\right)`;
            else
                return `(${result})`;
        }
        return result;
    };
    // Binary operators
    if (args.length === 2) {
        const [left, right] = args;
        switch (op) {
            case '+':
                return `${formatArg(left)} + ${formatArg(right, true)}`;
            case '-':
                if (format === 'unicode') {
                    return `${formatArg(left)} − ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} - ${formatArg(right, true)}`;
            case '*':
                if (format === 'unicode') {
                    return `${formatArg(left)}·${formatArg(right, true)}`;
                }
                else if (format === 'latex') {
                    return `${formatArg(left)} \\cdot ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} * ${formatArg(right, true)}`;
            case '/':
                if (format === 'latex') {
                    return `\\frac{${toLatex(left)}}{${toLatex(right)}}`;
                }
                else if (format === 'unicode') {
                    return `${formatArg(left)}/${formatArg(right, true)}`;
                }
                return `${formatArg(left)} / ${formatArg(right, true)}`;
            case '^':
                if (format === 'latex') {
                    return `${formatArg(left)}^{${toLatex(right)}}`;
                }
                // For unicode, try to use superscript digits
                if (format === 'unicode' && typeof right === 'number' && Number.isInteger(right)) {
                    return `${formatArg(left)}${toSuperscript(right.toString())}`;
                }
                return `${formatArg(left)}^${formatArg(right, true)}`;
            case '>':
            case '<':
                return `${formatArg(left)} ${op} ${formatArg(right, true)}`;
            case '>=':
                if (format === 'unicode') {
                    return `${formatArg(left)} ≥ ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} ${op} ${formatArg(right, true)}`;
            case '<=':
                if (format === 'unicode') {
                    return `${formatArg(left)} ≤ ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} ${op} ${formatArg(right, true)}`;
            case '==':
                if (format === 'unicode') {
                    return `${formatArg(left)} = ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} ${op} ${formatArg(right, true)}`;
            case '!=':
                if (format === 'unicode') {
                    return `${formatArg(left)} ≠ ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} ${op} ${formatArg(right, true)}`;
            case 'and':
                if (format === 'unicode') {
                    return `${formatArg(left)} ∧ ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} and ${formatArg(right, true)}`;
            case 'or':
                if (format === 'unicode') {
                    return `${formatArg(left)} ∨ ${formatArg(right, true)}`;
                }
                return `${formatArg(left)} or ${formatArg(right, true)}`;
            case 'atan2':
                if (format === 'latex') {
                    return `\\mathrm{atan2}(${toLatex(left)}, ${toLatex(right)})`;
                }
                return `atan2(${formatArg(left)}, ${formatArg(right)})`;
            case 'min':
            case 'max':
                if (format === 'latex') {
                    return `\\${op}(${toLatex(left)}, ${toLatex(right)})`;
                }
                return `${op}(${formatArg(left)}, ${formatArg(right)})`;
        }
    }
    // Unary operators
    if (args.length === 1) {
        const [arg] = args;
        switch (op) {
            case '-':
                // Unary minus
                if (format === 'unicode') {
                    return `−${formatArg(arg)}`;
                }
                return `-${formatArg(arg)}`;
            case 'not':
                if (format === 'unicode') {
                    return `¬${formatArg(arg)}`;
                }
                return `not ${formatArg(arg)}`;
            case 'exp':
            case 'sin':
            case 'cos':
            case 'tan':
                if (format === 'latex') {
                    return `\\${op}\\left(${toLatex(arg)}\\right)`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'log':
                if (format === 'unicode') {
                    return `ln(${formatArg(arg)})`;
                }
                else if (format === 'latex') {
                    return `\\${op}\\left(${toLatex(arg)}\\right)`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'log10':
                if (format === 'unicode') {
                    return `log₁₀(${formatArg(arg)})`;
                }
                else if (format === 'latex') {
                    return `\\log_{10}\\left(${toLatex(arg)}\\right)`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'sqrt':
                if (format === 'unicode') {
                    return `√${formatArg(arg)}`;
                }
                else if (format === 'latex') {
                    return `\\sqrt{${toLatex(arg)}}`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'abs':
                if (format === 'unicode') {
                    return `|${formatArg(arg)}|`;
                }
                else if (format === 'latex') {
                    return `|${toLatex(arg)}|`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'floor':
                if (format === 'unicode') {
                    return `⌊${formatArg(arg)}⌋`;
                }
                else if (format === 'latex') {
                    return `\\lfloor ${toLatex(arg)} \\rfloor`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'ceil':
                if (format === 'unicode') {
                    return `⌈${formatArg(arg)}⌉`;
                }
                else if (format === 'latex') {
                    return `\\lceil ${toLatex(arg)} \\rceil`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'sign':
                if (format === 'unicode') {
                    return `sgn(${formatArg(arg)})`;
                }
                else if (format === 'latex') {
                    return `\\text{sgn}\\left(${toLatex(arg)}\\right)`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'asin':
            case 'acos':
            case 'atan':
                const arcName = op.replace('a', 'arc');
                if (format === 'unicode') {
                    return `${arcName}(${formatArg(arg)})`;
                }
                else if (format === 'latex') {
                    return `\\${op}\\left(${toLatex(arg)}\\right)`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'grad':
                const dim = node.dim || 'x'; // dim is not in ExprNode type yet
                if (format === 'unicode') {
                    const variable2 = formatArg(arg);
                    return `∂${variable2}/∂${dim}`;
                }
                else if (format === 'latex') {
                    return `\\frac{\\partial ${toLatex(arg)}}{\\partial ${dim}}`;
                }
                return `d(${toAscii(arg)})/d${dim}`;
            case 'div':
                if (format === 'unicode') {
                    return `∇·${formatArg(arg)}`;
                }
                else if (format === 'latex') {
                    return `\\nabla \\cdot ${toLatex(arg)}`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'laplacian':
                if (format === 'unicode') {
                    return `∇²${formatArg(arg)}`;
                }
                else if (format === 'latex') {
                    return `\\nabla^2 ${toLatex(arg)}`;
                }
                return `${op}(${formatArg(arg)})`;
            case 'Pre':
                if (format === 'latex') {
                    return `\\mathrm{Pre}(${toLatex(arg)})`;
                }
                return `Pre(${formatArg(arg)})`;
            case 'D':
                // Derivative operator
                const wrtVar = wrt || 't';
                if (format === 'unicode') {
                    const variable = toUnicode(arg);
                    return `∂${variable}/∂${wrtVar}`;
                }
                else if (format === 'latex') {
                    return `\\frac{\\partial ${toLatex(arg)}}{\\partial ${wrtVar}}`;
                }
                return `D(${toAscii(arg)})/D${wrtVar}`;
        }
    }
    // Ternary and n-ary operators
    if (args.length >= 3) {
        switch (op) {
            case 'ifelse':
                if (args.length === 3) {
                    const [cond, thenExpr, elseExpr] = args;
                    return `ifelse(${formatArg(cond)}, ${formatArg(thenExpr)}, ${formatArg(elseExpr)})`;
                }
                break;
            case '+':
                // N-ary addition
                return args.map(arg => formatArg(arg)).join(' + ');
            case '*':
                // N-ary multiplication
                const sep = format === 'unicode' ? '·' : format === 'latex' ? ' \\cdot ' : ' * ';
                return args.map(arg => formatArg(arg)).join(sep);
            case 'or':
                // N-ary or
                if (format === 'unicode') {
                    return args.map(arg => formatArg(arg)).join(' ∨ ');
                }
                return args.map(arg => formatArg(arg)).join(' or ');
            case 'max':
                // N-ary max
                const maxArgList = args.map(arg => {
                    if (format === 'unicode')
                        return toUnicode(arg);
                    else if (format === 'latex')
                        return toLatex(arg);
                    else
                        return toAscii(arg);
                }).join(', ');
                if (format === 'latex') {
                    return `\\max(${maxArgList})`;
                }
                return `max(${maxArgList})`;
        }
    }
    // Fallback: function call notation
    const argList = args.map(arg => {
        if (format === 'unicode')
            return toUnicode(arg);
        else if (format === 'latex')
            return toLatex(arg);
        else
            return toAscii(arg);
    }).join(', ');
    if (format === 'latex') {
        return `\\text{${op}}\\left(${argList}\\right)`;
    }
    return `${op}(${argList})`;
}
/**
 * Format model summary (implementation placeholder)
 */
function formatModelSummary(model, format) {
    // This is a placeholder - full implementation would need to format
    // the model according to spec Section 6.3
    const name = model.name || 'unnamed'; // name might not be in Model type yet
    return `Model: ${name} (${model.variables?.length || 0} variables, ${model.equations?.length || 0} equations)`;
}
/**
 * Format reaction system summary (implementation placeholder)
 */
function formatReactionSystemSummary(reactionSystem, format) {
    const name = reactionSystem.name || 'unnamed'; // name might not be in ReactionSystem type yet
    return `ReactionSystem: ${name} (${reactionSystem.species?.length || 0} species, ${reactionSystem.reactions?.length || 0} reactions)`;
}
/**
 * Format ESM file summary (implementation placeholder)
 */
function formatEsmFileSummary(esmFile, format) {
    const models = Object.keys(esmFile.models || {}).length;
    const reactionSystems = Object.keys(esmFile.reaction_systems || {}).length;
    const dataLoaders = Object.keys(esmFile.data_loaders || {}).length;
    const title = esmFile.metadata?.title || 'Untitled'; // title might not be in Metadata type yet
    return `ESM v${esmFile.esm}: ${title} (${models} models, ${reactionSystems} reaction systems, ${dataLoaders} data loaders)`;
}

/**
 * Expression substitution functionality for the ESM format
 *
 * Provides immutable substitution operations that replace variable references
 * with bound expressions throughout ESM structures.
 */
/**
 * Recursively substitute variable references in an expression with bound expressions.
 * Handles scoped references (Model.Subsystem.var) by splitting on '.' and matching
 * path through system hierarchy per format spec Section 4.3.
 *
 * @param expr - Expression to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New expression with substitutions applied (immutable)
 */
function substitute(expr, bindings) {
    // Base cases: numbers remain unchanged
    if (typeof expr === 'number') {
        return expr;
    }
    // String case: variable reference
    if (typeof expr === 'string') {
        // Check for direct binding
        if (bindings.hasOwnProperty(expr)) {
            return bindings[expr];
        }
        // Check for scoped reference (e.g., "Model.Subsystem.var")
        // For now, treat as direct lookup - full scoped resolution would require
        // access to the model hierarchy context
        return expr;
    }
    // ExpressionNode case: recursively substitute arguments
    const node = expr;
    const substitutedArgs = node.args.map(arg => substitute(arg, bindings));
    // Return new node with substituted arguments
    return {
        ...node,
        args: substitutedArgs
    };
}
/**
 * Apply substitution across all equations in a model.
 * Returns a new model with substitutions applied (immutable).
 *
 * @param model - Model to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New model with substitutions applied
 */
function substituteInModel(model, bindings) {
    // Substitute in all equations
    const equations = model.equations.map(eq => ({
        ...eq,
        lhs: substitute(eq.lhs, bindings),
        rhs: substitute(eq.rhs, bindings)
    }));
    // Substitute in variable expressions (for observed variables)
    const variables = Object.fromEntries(Object.entries(model.variables).map(([name, variable]) => [
        name,
        {
            ...variable,
            ...(variable.expression && {
                expression: substitute(variable.expression, bindings)
            })
        }
    ]));
    // Substitute in subsystems recursively
    const subsystems = model.subsystems
        ? Object.fromEntries(Object.entries(model.subsystems).map(([name, subsystem]) => [
            name,
            substituteInModel(subsystem, bindings)
        ]))
        : undefined;
    return {
        ...model,
        equations,
        variables,
        ...(subsystems && { subsystems })
    };
}
/**
 * Apply substitution across all rate expressions in a reaction system.
 * Returns a new reaction system with substitutions applied (immutable).
 *
 * @param system - ReactionSystem to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New reaction system with substitutions applied
 */
function substituteInReactionSystem(system, bindings) {
    // Substitute in all reaction rate expressions
    const reactions = system.reactions.map(reaction => ({
        ...reaction,
        rate: substitute(reaction.rate, bindings)
    }));
    // Substitute in constraint equations if present
    const constraint_equations = system.constraint_equations?.map(eq => ({
        ...eq,
        lhs: substitute(eq.lhs, bindings),
        rhs: substitute(eq.rhs, bindings)
    }));
    // Substitute in subsystems recursively
    const subsystems = system.subsystems
        ? Object.fromEntries(Object.entries(system.subsystems).map(([name, subsystem]) => [
            name,
            substituteInReactionSystem(subsystem, bindings)
        ]))
        : undefined;
    return {
        ...system,
        reactions,
        ...(constraint_equations && { constraint_equations }),
        ...(subsystems && { subsystems })
    };
}

/**
 * Expression structural operations for the ESM format
 *
 * This module provides utilities for analyzing and manipulating mathematical
 * expressions in the ESM format AST.
 */
/**
 * Extract all variable references from an expression
 * @param expr Expression to analyze
 * @returns Set of variable names referenced in the expression
 */
function freeVariables(expr) {
    const variables = new Set();
    if (typeof expr === 'string') {
        variables.add(expr);
    }
    else if (typeof expr === 'number') {
        // Numbers contain no variables
        return variables;
    }
    else if (typeof expr === 'object' && expr.op) {
        // ExpressionNode - recursively analyze arguments
        for (const arg of expr.args) {
            const childVars = freeVariables(arg);
            childVars.forEach(v => variables.add(v));
        }
    }
    return variables;
}
/**
 * Extract free parameters from an expression within a model context
 * @param expr Expression to analyze
 * @param model Model context to determine parameter vs state variables
 * @returns Set of parameter names referenced in the expression
 */
function freeParameters(expr, model) {
    const allVars = freeVariables(expr);
    const parameters = new Set();
    for (const varName of allVars) {
        const variable = model.variables[varName];
        if (variable && variable.type === 'parameter') {
            parameters.add(varName);
        }
    }
    return parameters;
}
/**
 * Check if an expression contains a specific variable
 * @param expr Expression to search
 * @param varName Variable name to look for
 * @returns True if the variable appears in the expression
 */
function contains(expr, varName) {
    if (typeof expr === 'string') {
        return expr === varName;
    }
    else if (typeof expr === 'number') {
        return false;
    }
    else if (typeof expr === 'object' && expr.op) {
        // ExpressionNode - recursively check arguments
        return expr.args.some(arg => contains(arg, varName));
    }
    return false;
}
/**
 * Evaluate an expression numerically with variable bindings
 * @param expr Expression to evaluate
 * @param bindings Map of variable names to their numeric values
 * @returns Numeric result
 * @throws Error if variables are unbound or evaluation fails
 */
function evaluate(expr, bindings) {
    if (typeof expr === 'number') {
        return expr;
    }
    else if (typeof expr === 'string') {
        if (bindings.has(expr)) {
            return bindings.get(expr);
        }
        else {
            throw new Error(`Unbound variable: ${expr}`);
        }
    }
    else if (typeof expr === 'object' && expr.op) {
        // ExpressionNode - evaluate based on operator
        const args = expr.args.map(arg => evaluate(arg, bindings));
        switch (expr.op) {
            case '+':
                return args.reduce((sum, val) => sum + val, 0);
            case '-':
                if (args.length === 1)
                    return -args[0];
                return args.reduce((diff, val, idx) => idx === 0 ? val : diff - val);
            case '*':
                return args.reduce((prod, val) => prod * val, 1);
            case '/':
                if (args.length !== 2)
                    throw new Error('Division requires exactly 2 arguments');
                if (args[1] === 0)
                    throw new Error('Division by zero');
                return args[0] / args[1];
            case '^':
                if (args.length !== 2)
                    throw new Error('Exponentiation requires exactly 2 arguments');
                return Math.pow(args[0], args[1]);
            case 'exp':
                if (args.length !== 1)
                    throw new Error('exp requires exactly 1 argument');
                return Math.exp(args[0]);
            case 'log':
                if (args.length !== 1)
                    throw new Error('log requires exactly 1 argument');
                if (args[0] <= 0)
                    throw new Error('log argument must be positive');
                return Math.log(args[0]);
            case 'log10':
                if (args.length !== 1)
                    throw new Error('log10 requires exactly 1 argument');
                if (args[0] <= 0)
                    throw new Error('log10 argument must be positive');
                return Math.log10(args[0]);
            case 'sqrt':
                if (args.length !== 1)
                    throw new Error('sqrt requires exactly 1 argument');
                if (args[0] < 0)
                    throw new Error('sqrt argument must be non-negative');
                return Math.sqrt(args[0]);
            case 'abs':
                if (args.length !== 1)
                    throw new Error('abs requires exactly 1 argument');
                return Math.abs(args[0]);
            case 'sin':
                if (args.length !== 1)
                    throw new Error('sin requires exactly 1 argument');
                return Math.sin(args[0]);
            case 'cos':
                if (args.length !== 1)
                    throw new Error('cos requires exactly 1 argument');
                return Math.cos(args[0]);
            case 'tan':
                if (args.length !== 1)
                    throw new Error('tan requires exactly 1 argument');
                return Math.tan(args[0]);
            case 'asin':
                if (args.length !== 1)
                    throw new Error('asin requires exactly 1 argument');
                if (args[0] < -1 || args[0] > 1)
                    throw new Error('asin argument must be in [-1, 1]');
                return Math.asin(args[0]);
            case 'acos':
                if (args.length !== 1)
                    throw new Error('acos requires exactly 1 argument');
                if (args[0] < -1 || args[0] > 1)
                    throw new Error('acos argument must be in [-1, 1]');
                return Math.acos(args[0]);
            case 'atan':
                if (args.length !== 1)
                    throw new Error('atan requires exactly 1 argument');
                return Math.atan(args[0]);
            case 'atan2':
                if (args.length !== 2)
                    throw new Error('atan2 requires exactly 2 arguments');
                return Math.atan2(args[0], args[1]);
            case 'min':
                if (args.length === 0)
                    throw new Error('min requires at least 1 argument');
                return Math.min(...args);
            case 'max':
                if (args.length === 0)
                    throw new Error('max requires at least 1 argument');
                return Math.max(...args);
            case 'floor':
                if (args.length !== 1)
                    throw new Error('floor requires exactly 1 argument');
                return Math.floor(args[0]);
            case 'ceil':
                if (args.length !== 1)
                    throw new Error('ceil requires exactly 1 argument');
                return Math.ceil(args[0]);
            case 'sign':
                if (args.length !== 1)
                    throw new Error('sign requires exactly 1 argument');
                return Math.sign(args[0]);
            case '>':
                if (args.length !== 2)
                    throw new Error('> requires exactly 2 arguments');
                return args[0] > args[1] ? 1 : 0;
            case '<':
                if (args.length !== 2)
                    throw new Error('< requires exactly 2 arguments');
                return args[0] < args[1] ? 1 : 0;
            case '>=':
                if (args.length !== 2)
                    throw new Error('>= requires exactly 2 arguments');
                return args[0] >= args[1] ? 1 : 0;
            case '<=':
                if (args.length !== 2)
                    throw new Error('<= requires exactly 2 arguments');
                return args[0] <= args[1] ? 1 : 0;
            case '==':
                if (args.length !== 2)
                    throw new Error('== requires exactly 2 arguments');
                return args[0] === args[1] ? 1 : 0;
            case '!=':
                if (args.length !== 2)
                    throw new Error('!= requires exactly 2 arguments');
                return args[0] !== args[1] ? 1 : 0;
            case 'and':
                return args.every(x => x !== 0) ? 1 : 0;
            case 'or':
                return args.some(x => x !== 0) ? 1 : 0;
            case 'not':
                if (args.length !== 1)
                    throw new Error('not requires exactly 1 argument');
                return args[0] === 0 ? 1 : 0;
            case 'ifelse':
                if (args.length !== 3)
                    throw new Error('ifelse requires exactly 3 arguments');
                return args[0] !== 0 ? args[1] : args[2];
            default:
                throw new Error(`Unsupported operator: ${expr.op}`);
        }
    }
    throw new Error('Invalid expression type');
}
/**
 * Simplify an expression using basic algebraic rules
 * @param expr Expression to simplify
 * @returns Simplified expression
 */
function simplify(expr) {
    if (typeof expr === 'number' || typeof expr === 'string') {
        return expr;
    }
    if (typeof expr === 'object' && expr.op) {
        // First simplify all arguments recursively
        const simplifiedArgs = expr.args.map(arg => simplify(arg));
        // Apply simplification rules based on operator
        switch (expr.op) {
            case '+':
                // Remove zeros: x + 0 -> x
                const nonZeroTerms = simplifiedArgs.filter(arg => arg !== 0);
                if (nonZeroTerms.length === 0)
                    return 0;
                if (nonZeroTerms.length === 1)
                    return nonZeroTerms[0];
                // Separate constants and variables for partial constant folding
                const constants = nonZeroTerms.filter(arg => typeof arg === 'number');
                const variables = nonZeroTerms.filter(arg => typeof arg !== 'number');
                // If all terms are constants, return the sum
                if (variables.length === 0) {
                    return constants.reduce((sum, val) => sum + val, 0);
                }
                // If there are constants to fold, combine them
                if (constants.length > 1) {
                    const constantSum = constants.reduce((sum, val) => sum + val, 0);
                    if (constantSum === 0) {
                        // If constant sum is zero, just return variables
                        return variables.length === 1 ? variables[0] : { ...expr, args: variables };
                    }
                    else {
                        // Include the folded constant with variables
                        const finalTerms = [...variables, constantSum];
                        return { ...expr, args: finalTerms };
                    }
                }
                return { ...expr, args: nonZeroTerms };
            case '*':
                // Zero multiplication: x * 0 -> 0
                if (simplifiedArgs.some(arg => arg === 0))
                    return 0;
                // Remove ones: x * 1 -> x
                const nonOneFactors = simplifiedArgs.filter(arg => arg !== 1);
                if (nonOneFactors.length === 0)
                    return 1;
                if (nonOneFactors.length === 1)
                    return nonOneFactors[0];
                // Separate constants and variables for partial constant folding
                const constantFactors = nonOneFactors.filter(arg => typeof arg === 'number');
                const variableFactors = nonOneFactors.filter(arg => typeof arg !== 'number');
                // If all factors are constants, return the product
                if (variableFactors.length === 0) {
                    return constantFactors.reduce((prod, val) => prod * val, 1);
                }
                // If there are constants to fold, combine them
                if (constantFactors.length > 1) {
                    const constantProd = constantFactors.reduce((prod, val) => prod * val, 1);
                    if (constantProd === 0) {
                        return 0;
                    }
                    else if (constantProd === 1) {
                        // If constant product is one, just return variables
                        return variableFactors.length === 1 ? variableFactors[0] : { ...expr, args: variableFactors };
                    }
                    else {
                        // Include the folded constant with variables
                        const finalFactors = [...variableFactors, constantProd];
                        return { ...expr, args: finalFactors };
                    }
                }
                return { ...expr, args: nonOneFactors };
            case '-':
                if (simplifiedArgs.length === 1) {
                    // Unary minus: -(-x) -> x would need deeper analysis
                    if (typeof simplifiedArgs[0] === 'number') {
                        return -simplifiedArgs[0];
                    }
                }
                else if (simplifiedArgs.length === 2) {
                    // Binary subtraction: x - 0 -> x
                    if (simplifiedArgs[1] === 0)
                        return simplifiedArgs[0];
                    // Constant folding
                    if (typeof simplifiedArgs[0] === 'number' && typeof simplifiedArgs[1] === 'number') {
                        return simplifiedArgs[0] - simplifiedArgs[1];
                    }
                }
                return { ...expr, args: simplifiedArgs };
            case '/':
                if (simplifiedArgs.length === 2) {
                    // x / 1 -> x
                    if (simplifiedArgs[1] === 1)
                        return simplifiedArgs[0];
                    // 0 / x -> 0 (assuming x != 0)
                    if (simplifiedArgs[0] === 0)
                        return 0;
                    // Constant folding
                    if (typeof simplifiedArgs[0] === 'number' && typeof simplifiedArgs[1] === 'number') {
                        if (simplifiedArgs[1] === 0)
                            throw new Error('Division by zero');
                        return simplifiedArgs[0] / simplifiedArgs[1];
                    }
                }
                return { ...expr, args: simplifiedArgs };
            case '^':
                if (simplifiedArgs.length === 2) {
                    // x^0 -> 1
                    if (simplifiedArgs[1] === 0)
                        return 1;
                    // x^1 -> x
                    if (simplifiedArgs[1] === 1)
                        return simplifiedArgs[0];
                    // 0^x -> 0 (assuming x > 0)
                    if (simplifiedArgs[0] === 0)
                        return 0;
                    // 1^x -> 1
                    if (simplifiedArgs[0] === 1)
                        return 1;
                    // Constant folding
                    if (typeof simplifiedArgs[0] === 'number' && typeof simplifiedArgs[1] === 'number') {
                        return Math.pow(simplifiedArgs[0], simplifiedArgs[1]);
                    }
                }
                return { ...expr, args: simplifiedArgs };
            default:
                // For other operators, just apply constant folding if all args are numeric
                if (simplifiedArgs.every(arg => typeof arg === 'number')) {
                    try {
                        // Create a temporary bindings map for evaluation
                        const tempBindings = new Map();
                        return evaluate({ ...expr, args: simplifiedArgs }, tempBindings);
                    }
                    catch {
                        // If evaluation fails, return the expression with simplified args
                        return { ...expr, args: simplifiedArgs };
                    }
                }
                return { ...expr, args: simplifiedArgs };
        }
    }
    return expr;
}

/**
 * ESM Format TypeScript Package - Core Only
 *
 * Entry point for core esm-format functionality without interactive components.
 * This build excludes SolidJS components to provide a lighter bundle.
 *
 * @example
 * ```typescript
 * import { EsmFile, Model, Expr } from 'esm-format/core';
 * ```
 */
// Re-export all types from types.ts (which includes generated types and augmentations)
// Package metadata
const VERSION = '0.1.0';
const SCHEMA_VERSION = '0.1.0';

exports.ParseError = ParseError;
exports.SCHEMA_VERSION = SCHEMA_VERSION;
exports.SchemaValidationError = SchemaValidationError;
exports.VERSION = VERSION;
exports.componentExists = componentExists;
exports.component_graph = component_graph;
exports.contains = contains;
exports.evaluate = evaluate;
exports.freeParameters = freeParameters;
exports.freeVariables = freeVariables;
exports.getComponentType = getComponentType;
exports.load = load;
exports.save = save;
exports.simplify = simplify;
exports.substitute = substitute;
exports.substituteInModel = substituteInModel;
exports.substituteInReactionSystem = substituteInReactionSystem;
exports.toAscii = toAscii;
exports.toLatex = toLatex;
exports.toUnicode = toUnicode;
exports.validate = validate;
exports.validateSchema = validateSchema;
//# sourceMappingURL=index.js.map
