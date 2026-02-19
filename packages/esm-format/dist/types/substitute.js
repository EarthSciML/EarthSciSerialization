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
 * @param context - Optional context for resolving scoped references
 * @returns New expression with substitutions applied (immutable)
 */
export function substitute(expr, bindings, context) {
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
        if (context && expr.includes('.')) {
            const resolvedValue = resolveScopedReference(expr, context.esmFile);
            if (resolvedValue !== null) {
                return resolvedValue;
            }
        }
        return expr;
    }
    // ExpressionNode case: recursively substitute arguments
    const node = expr;
    const substitutedArgs = node.args.map(arg => substitute(arg, bindings, context));
    // Return new node with substituted arguments
    return {
        ...node,
        args: substitutedArgs
    };
}
/**
 * Resolve scoped variable reference like "Model.Subsystem.var" by navigating
 * through the system hierarchy as specified in Section 4.3 of the spec.
 *
 * @param reference - Scoped reference string (e.g., "SuperFast.GasPhase.O3")
 * @param esmFile - ESM file containing the model hierarchy
 * @returns The default value of the referenced variable, or null if not found
 */
function resolveScopedReference(reference, esmFile) {
    const parts = reference.split('.');
    if (parts.length < 2) {
        return null; // Not a scoped reference
    }
    const [systemName, ...pathParts] = parts;
    const variableName = pathParts.pop();
    // Try to find in models
    if (esmFile.models && esmFile.models[systemName]) {
        let current = esmFile.models[systemName];
        // Navigate through subsystems
        for (const pathPart of pathParts) {
            if (!current.subsystems || !current.subsystems[pathPart]) {
                return null;
            }
            current = current.subsystems[pathPart];
        }
        // Check if variable exists and return its default value
        const variable = current.variables?.[variableName];
        if (variable && variable.default !== undefined) {
            return variable.default;
        }
    }
    // Try to find in reaction systems
    if (esmFile.reaction_systems && esmFile.reaction_systems[systemName]) {
        let current = esmFile.reaction_systems[systemName];
        // Navigate through subsystems
        for (const pathPart of pathParts) {
            if (!current.subsystems || !current.subsystems[pathPart]) {
                return null;
            }
            current = current.subsystems[pathPart];
        }
        // Check if species exists and return its default value
        const species = current.species?.[variableName];
        if (species && species.default !== undefined) {
            return species.default;
        }
        // Check if parameter exists and return its default value
        const parameter = current.parameters?.[variableName];
        if (parameter && parameter.default !== undefined) {
            return parameter.default;
        }
    }
    // Try to find in data loaders
    if (esmFile.data_loaders && esmFile.data_loaders[systemName]) {
        const dataLoader = esmFile.data_loaders[systemName];
        if (dataLoader.provides && dataLoader.provides[variableName]) {
            // Data loaders don't have default values, return the variable name as a placeholder
            return reference;
        }
    }
    return null;
}
/**
 * Apply substitution across all equations in a model.
 * Returns a new model with substitutions applied (immutable).
 *
 * @param model - Model to substitute into
 * @param bindings - Variable name to expression mappings
 * @param context - Optional context for resolving scoped references
 * @returns New model with substitutions applied
 */
export function substituteInModel(model, bindings, context) {
    // Substitute in all equations
    const equations = model.equations.map(eq => ({
        ...eq,
        lhs: substitute(eq.lhs, bindings, context),
        rhs: substitute(eq.rhs, bindings, context)
    }));
    // Substitute in variable expressions (for observed variables)
    const variables = Object.fromEntries(Object.entries(model.variables).map(([name, variable]) => [
        name,
        {
            ...variable,
            ...(variable.expression && {
                expression: substitute(variable.expression, bindings, context)
            })
        }
    ]));
    // Substitute in subsystems recursively
    const subsystems = model.subsystems
        ? Object.fromEntries(Object.entries(model.subsystems).map(([name, subsystem]) => [
            name,
            substituteInModel(subsystem, bindings, context)
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
 * @param context - Optional context for resolving scoped references
 * @returns New reaction system with substitutions applied
 */
export function substituteInReactionSystem(system, bindings, context) {
    // Substitute in all reaction rate expressions
    const reactions = system.reactions.map(reaction => ({
        ...reaction,
        rate: substitute(reaction.rate, bindings, context)
    }));
    // Substitute in constraint equations if present
    const constraint_equations = system.constraint_equations?.map(eq => ({
        ...eq,
        lhs: substitute(eq.lhs, bindings, context),
        rhs: substitute(eq.rhs, bindings, context)
    }));
    // Substitute in subsystems recursively
    const subsystems = system.subsystems
        ? Object.fromEntries(Object.entries(system.subsystems).map(([name, subsystem]) => [
            name,
            substituteInReactionSystem(subsystem, bindings, context)
        ]))
        : undefined;
    return {
        ...system,
        reactions,
        ...(constraint_equations && { constraint_equations }),
        ...(subsystems && { subsystems })
    };
}
//# sourceMappingURL=substitute.js.map