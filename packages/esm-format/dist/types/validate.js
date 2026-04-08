/**
 * ESM Format validation wrapper for cross-language conformance testing.
 *
 * Provides a standardized validation interface that matches the format expected
 * by the conformance test runner across all language implementations.
 */
import { validateSchema, load } from './parse.js';
import { validateUnits } from './units.js';
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
export function validate(data) {
    const schema_errors = [];
    const structural_errors = [];
    let unit_warnings = [];
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
                    structural_errors: [],
                    unit_warnings: []
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
                // Perform unit validation
                unit_warnings = validateUnits(esmFile);
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
            structural_errors: [],
            unit_warnings: []
        };
    }
    return {
        is_valid: schema_errors.length === 0 && structural_errors.length === 0,
        schema_errors,
        structural_errors,
        unit_warnings
    };
}
//# sourceMappingURL=validate.js.map