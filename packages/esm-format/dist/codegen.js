/**
 * Code generation for the ESM format
 *
 * This module provides functions to generate self-contained scripts
 * from ESM files in multiple target languages:
 * - Julia: compatible with ModelingToolkit, Catalyst, EarthSciMLBase, and OrdinaryDiffEq
 * - Python: compatible with SymPy, esm_format, and SciPy
 */
/**
 * Generate a self-contained Julia script from an ESM file
 * @param file ESM file to generate Julia code for
 * @returns Julia script as a string
 */
export function toJuliaCode(file) {
    const lines = [];
    // Header comment
    lines.push(`# Generated Julia script from ESM file`);
    lines.push(`# ESM version: ${file.esm}`);
    if (file.metadata?.title) {
        lines.push(`# Title: ${file.metadata.title}`);
    }
    if (file.metadata?.description) {
        lines.push(`# Description: ${file.metadata.description}`);
    }
    lines.push('');
    // Using statements
    lines.push('# Package imports');
    lines.push('using ModelingToolkit');
    lines.push('using Catalyst');
    lines.push('using EarthSciMLBase');
    lines.push('using OrdinaryDiffEq');
    lines.push('using Unitful');
    lines.push('');
    // Generate models
    if (file.models && Object.keys(file.models).length > 0) {
        lines.push('# Models');
        for (const [name, model] of Object.entries(file.models)) {
            lines.push(...generateModelCode(name, model));
            lines.push('');
        }
    }
    // Generate reaction systems
    if (file.reaction_systems && Object.keys(file.reaction_systems).length > 0) {
        lines.push('# Reaction Systems');
        for (const [name, reactionSystem] of Object.entries(file.reaction_systems)) {
            lines.push(...generateReactionSystemCode(name, reactionSystem));
            lines.push('');
        }
    }
    // Generate events
    if (file.events && Object.keys(file.events).length > 0) {
        lines.push('# Events');
        for (const [name, event] of Object.entries(file.events)) {
            lines.push(...generateEventCode(name, event));
            lines.push('');
        }
    }
    // Generate coupling as TODO comments
    if (file.coupling && file.coupling.length > 0) {
        lines.push('# Coupling (TODO)');
        for (const coupling of file.coupling) {
            lines.push(...generateCouplingComment(coupling));
        }
        lines.push('');
    }
    // Generate domain as TODO comment
    if (file.domain) {
        lines.push('# Domain (TODO)');
        lines.push(...generateDomainComment(file.domain));
        lines.push('');
    }
    // Generate solver as TODO comment
    if (file.solver) {
        lines.push('# Solver (TODO)');
        lines.push(...generateSolverComment(file.solver));
        lines.push('');
    }
    // Generate data loaders as TODO comments
    if (file.data_loaders && Object.keys(file.data_loaders).length > 0) {
        lines.push('# Data Loaders (TODO)');
        for (const [name, dataLoader] of Object.entries(file.data_loaders)) {
            lines.push(...generateDataLoaderComment(name, dataLoader));
        }
        lines.push('');
    }
    return lines.join('\n');
}
/**
 * Generate a self-contained Python script from an ESM file
 * @param file ESM file to generate Python code for
 * @returns Python script as a string
 */
export function toPythonCode(file) {
    const lines = [];
    // Header comment
    lines.push(`# Generated Python script from ESM file`);
    lines.push(`# ESM version: ${file.esm}`);
    if (file.metadata?.title) {
        lines.push(`# Title: ${file.metadata.title}`);
    }
    if (file.metadata?.description) {
        lines.push(`# Description: ${file.metadata.description}`);
    }
    lines.push('');
    // Import statements
    lines.push('# Package imports');
    lines.push('import sympy as sp');
    lines.push('import esm_format as esm');
    lines.push('import scipy');
    lines.push('from sympy import Function');
    lines.push('');
    // Generate models
    if (file.models && Object.keys(file.models).length > 0) {
        lines.push('# Models');
        for (const [name, model] of Object.entries(file.models)) {
            lines.push(...generatePythonModelCode(name, model));
            lines.push('');
        }
    }
    // Generate reaction systems
    if (file.reaction_systems && Object.keys(file.reaction_systems).length > 0) {
        lines.push('# Reaction Systems');
        for (const [name, reactionSystem] of Object.entries(file.reaction_systems)) {
            lines.push(...generatePythonReactionSystemCode(name, reactionSystem));
            lines.push('');
        }
    }
    // Generate simulation stub
    lines.push('# Simulation setup (TODO: Configure parameters)');
    lines.push('tspan = (0, 10)  # time span');
    lines.push('parameters = {}  # parameter values');
    lines.push('initial_conditions = {}  # initial values');
    lines.push('');
    lines.push('# result = esm.simulate(tspan=tspan, parameters=parameters, initial_conditions=initial_conditions)');
    lines.push('');
    // Generate TODO comments for other features
    if (file.coupling && file.coupling.length > 0) {
        lines.push('# Coupling (TODO)');
        for (const coupling of file.coupling) {
            lines.push(...generatePythonCouplingComment(coupling));
        }
        lines.push('');
    }
    if (file.domain) {
        lines.push('# Domain (TODO)');
        lines.push(...generatePythonDomainComment(file.domain));
        lines.push('');
    }
    if (file.solver) {
        lines.push('# Solver (TODO)');
        lines.push(...generatePythonSolverComment(file.solver));
        lines.push('');
    }
    return lines.join('\n');
}
/**
 * Generate Julia code for a model
 */
function generateModelCode(name, model) {
    const lines = [];
    lines.push(`# Model: ${name}`);
    // Collect state variables and parameters
    const stateVars = [];
    const parameters = [];
    if (model.variables) {
        for (const [varName, variable] of Object.entries(model.variables)) {
            if (variable.type === 'state') {
                stateVars.push({ ...variable, name: varName });
            }
            else if (variable.type === 'parameter') {
                parameters.push({ ...variable, name: varName });
            }
        }
    }
    // Generate @variables declaration
    if (stateVars.length > 0) {
        const varDecls = stateVars.map(v => formatVariableDeclaration(v, v.name)).join(' ');
        lines.push(`@variables t ${varDecls}`);
    }
    // Generate @parameters declaration
    if (parameters.length > 0) {
        const paramDecls = parameters.map(v => formatVariableDeclaration(v, v.name)).join(' ');
        lines.push(`@parameters ${paramDecls}`);
    }
    // Generate equations
    if (model.equations && model.equations.length > 0) {
        lines.push('');
        lines.push('eqs = [');
        for (const equation of model.equations) {
            lines.push(`    ${formatEquation(equation)},`);
        }
        lines.push(']');
    }
    // Generate @named ODESystem
    lines.push('');
    lines.push(`@named ${name}_system = ODESystem(eqs)`);
    return lines;
}
/**
 * Generate Julia code for a reaction system
 */
function generateReactionSystemCode(name, reactionSystem) {
    const lines = [];
    lines.push(`# Reaction System: ${name}`);
    // Generate @species declaration
    if (reactionSystem.species && Object.keys(reactionSystem.species).length > 0) {
        const speciesDecls = Object.entries(reactionSystem.species)
            .map(([name, s]) => formatSpeciesDeclaration(s, name)).join(' ');
        lines.push(`@species ${speciesDecls}`);
    }
    // Generate @parameters for reaction parameters
    const reactionParams = new Set();
    if (reactionSystem.reactions) {
        for (const reaction of Object.values(reactionSystem.reactions)) {
            // Extract parameter names from rate expressions
            if (reaction.rate) {
                const paramNames = extractParameterNames(reaction.rate);
                paramNames.forEach(p => reactionParams.add(p));
            }
        }
    }
    if (reactionParams.size > 0) {
        lines.push(`@parameters ${Array.from(reactionParams).join(' ')}`);
    }
    // Generate reactions
    if (reactionSystem.reactions && Object.keys(reactionSystem.reactions).length > 0) {
        lines.push('');
        lines.push('rxs = [');
        for (const reaction of Object.values(reactionSystem.reactions)) {
            lines.push(`    ${formatReaction(reaction)},`);
        }
        lines.push(']');
    }
    // Generate @named ReactionSystem
    lines.push('');
    lines.push(`@named ${name}_system = ReactionSystem(rxs)`);
    return lines;
}
/**
 * Generate Julia code for events
 */
function generateEventCode(name, event) {
    const lines = [];
    if ('condition' in event) {
        // Continuous event
        lines.push(`# Continuous Event: ${name}`);
        const condition = formatExpression(event.condition);
        const affect = formatAffect(event.affect);
        lines.push(`${name}_event = SymbolicContinuousCallback(${condition}, ${affect})`);
    }
    else {
        // Discrete event
        lines.push(`# Discrete Event: ${name}`);
        const trigger = formatDiscreteTrigger(event.trigger);
        const affect = formatAffect(event.affect);
        lines.push(`${name}_event = DiscreteCallback(${trigger}, ${affect})`);
    }
    return lines;
}
/**
 * Generate coupling TODO comments
 */
function generateCouplingComment(coupling) {
    const lines = [];
    lines.push(`# TODO: Implement coupling ${coupling.type}`);
    lines.push(`#   From: ${coupling.from}`);
    lines.push(`#   To: ${coupling.to}`);
    if (coupling.variables && coupling.variables.length > 0) {
        lines.push(`#   Variables: ${coupling.variables.join(', ')}`);
    }
    return lines;
}
/**
 * Generate domain TODO comments
 */
function generateDomainComment(domain) {
    const lines = [];
    lines.push(`# TODO: Implement domain`);
    if (domain.spatial_coordinates && domain.spatial_coordinates.length > 0) {
        lines.push(`#   Spatial coordinates: ${domain.spatial_coordinates.join(', ')}`);
    }
    if (domain.temporal_coordinates && domain.temporal_coordinates.length > 0) {
        lines.push(`#   Temporal coordinates: ${domain.temporal_coordinates.join(', ')}`);
    }
    return lines;
}
/**
 * Generate solver TODO comments
 */
function generateSolverComment(solver) {
    const lines = [];
    lines.push(`# TODO: Implement solver`);
    if (solver.algorithm) {
        lines.push(`#   Algorithm: ${solver.algorithm}`);
    }
    if (solver.tolerances) {
        lines.push(`#   Tolerances: ${JSON.stringify(solver.tolerances)}`);
    }
    return lines;
}
/**
 * Generate data loader TODO comments
 */
function generateDataLoaderComment(name, dataLoader) {
    const lines = [];
    lines.push(`# TODO: Implement data loader ${name}`);
    if (dataLoader.source) {
        lines.push(`#   Source: ${dataLoader.source}`);
    }
    if (dataLoader.format) {
        lines.push(`#   Format: ${dataLoader.format}`);
    }
    return lines;
}
/**
 * Format a variable declaration with defaults and units
 */
function formatVariableDeclaration(variable, name) {
    let decl = name;
    // Add default value and units if present
    if (variable.default !== undefined || variable.units) {
        decl += '(';
        const parts = [];
        if (variable.default !== undefined) {
            // Ensure decimal point for floating point numbers
            const defaultVal = variable.default;
            if (typeof defaultVal === 'number' && Number.isInteger(defaultVal)) {
                parts.push(`${defaultVal}.0`);
            }
            else {
                parts.push(`${defaultVal}`);
            }
        }
        if (variable.units) {
            parts.push(`u"${variable.units}"`);
        }
        decl += parts.join(', ');
        decl += ')';
    }
    return decl;
}
/**
 * Format a species declaration
 */
function formatSpeciesDeclaration(species, name) {
    let decl = name;
    // Add default value if present
    if (species.default !== undefined) {
        // Ensure decimal point for floating point numbers
        const initialVal = species.default;
        if (typeof initialVal === 'number' && Number.isInteger(initialVal)) {
            decl += `(${initialVal}.0)`;
        }
        else {
            decl += `(${initialVal})`;
        }
    }
    return decl;
}
/**
 * Format an equation using ~ syntax
 */
function formatEquation(equation) {
    const lhs = formatExpression(equation.lhs);
    const rhs = formatExpression(equation.rhs);
    return `${lhs} ~ ${rhs}`;
}
/**
 * Format a reaction
 */
function formatReaction(reaction) {
    const rate = reaction.rate ? formatExpression(reaction.rate) : '1.0';
    // Format substrates (reactants)
    const reactants = reaction.substrates ?
        reaction.substrates.map(r => r.stoichiometry && r.stoichiometry !== 1 ?
            `${r.stoichiometry}*${r.species}` : r.species).join(' + ') :
        '∅';
    // Format products
    const products = reaction.products ?
        reaction.products.map(p => p.stoichiometry && p.stoichiometry !== 1 ?
            `${p.stoichiometry}*${p.species}` : p.species).join(' + ') :
        '∅';
    return `Reaction(${rate}, [${reactants}], [${products}])`;
}
/**
 * Format an expression for Julia code generation
 */
function formatExpression(expr) {
    if (typeof expr === 'number') {
        return expr.toString();
    }
    if (typeof expr === 'string') {
        return expr;
    }
    if (typeof expr === 'object' && expr.op) {
        return formatExpressionNode(expr);
    }
    throw new Error(`Unsupported expression type: ${typeof expr}`);
}
/**
 * Format an expression node for Julia, applying operator mappings
 */
function formatExpressionNode(node) {
    const { op, args, wrt } = node;
    // Apply expression mappings as specified in task description
    switch (op) {
        case '+':
            return args.map(formatExpression).join(' + ');
        case '*':
            return args.map(formatExpression).join(' * ');
        case 'D':
            // D(x,t) → D(x) (remove time parameter)
            if (args.length >= 1) {
                return `D(${formatExpression(args[0])})`;
            }
            return 'D()';
        case 'exp':
            return `exp(${args.map(formatExpression).join(', ')})`;
        case 'ifelse':
            return `ifelse(${args.map(formatExpression).join(', ')})`;
        case 'Pre':
            return `Pre(${args.map(formatExpression).join(', ')})`;
        case '^':
            return args.map(formatExpression).join(' ^ ');
        case 'grad':
            // grad(x,y) → Differential(y)(x)
            if (args.length >= 2) {
                return `Differential(${formatExpression(args[1])})(${formatExpression(args[0])})`;
            }
            else if (args.length === 1) {
                // Default to x if dimension not specified
                return `Differential(x)(${formatExpression(args[0])})`;
            }
            return 'Differential(x)()';
        case '-':
            if (args.length === 1) {
                return `-${formatExpression(args[0])}`;
            }
            else {
                return args.map(formatExpression).join(' - ');
            }
        case '/':
            return args.map(formatExpression).join(' / ');
        case '<':
        case '>':
        case '<=':
        case '>=':
        case '==':
        case '!=':
            return args.map(formatExpression).join(` ${op} `);
        case 'and':
            return args.map(formatExpression).join(' && ');
        case 'or':
            return args.map(formatExpression).join(' || ');
        case 'not':
            return `!(${formatExpression(args[0])})`;
        default:
            // For other operators, use function call syntax
            return `${op}(${args.map(formatExpression).join(', ')})`;
    }
}
/**
 * Format affect clause for events
 */
function formatAffect(affect) {
    if (Array.isArray(affect)) {
        return `[${affect.map(formatAffectEquation).join(', ')}]`;
    }
    else if (affect && typeof affect === 'object' && (affect.lhs || affect.rhs)) {
        return formatAffectEquation(affect);
    }
    else {
        return 'nothing';
    }
}
/**
 * Format a single affect equation
 */
function formatAffectEquation(affect) {
    if (affect.lhs && affect.rhs) {
        return `${formatExpression(affect.lhs)} ~ ${formatExpression(affect.rhs)}`;
    }
    return 'nothing';
}
/**
 * Format discrete event trigger
 */
function formatDiscreteTrigger(trigger) {
    if (trigger.condition) {
        return formatExpression(trigger.condition);
    }
    return 'true';
}
/**
 * Extract parameter names from an expression
 */
function extractParameterNames(expr) {
    const params = new Set();
    if (typeof expr === 'string') {
        // Simple heuristic: single letters or names starting with k/K are likely parameters
        if (expr.length === 1 || expr.startsWith('k') || expr.startsWith('K')) {
            params.add(expr);
        }
    }
    else if (typeof expr === 'object' && expr.op) {
        // Recursively extract from arguments
        for (const arg of expr.args) {
            const childParams = extractParameterNames(arg);
            childParams.forEach(p => params.add(p));
        }
    }
    return params;
}
/**
 * Generate Python code for a model
 */
function generatePythonModelCode(name, model) {
    const lines = [];
    lines.push(`# Model: ${name}`);
    // Collect state variables and parameters
    const stateVars = [];
    const parameters = [];
    if (model.variables) {
        for (const [varName, variable] of Object.entries(model.variables)) {
            if (variable.type === 'state') {
                stateVars.push({ ...variable, name: varName });
            }
            else if (variable.type === 'parameter') {
                parameters.push({ ...variable, name: varName });
            }
        }
    }
    // Generate time symbol if needed
    const hasDerivatives = model.equations && model.equations.some(eq => hasDerivativeInExpression(eq.lhs) || hasDerivativeInExpression(eq.rhs));
    if (hasDerivatives) {
        lines.push('# Time variable');
        lines.push('t = sp.Symbol(\'t\')');
        lines.push('');
    }
    // Generate symbol/function definitions
    if (stateVars.length > 0) {
        lines.push('# State variables');
        for (const variable of stateVars) {
            const comment = variable.units ? `  # ${variable.units}` : '';
            if (variable.name && variable.name.includes('(')) {
                // Function symbol (e.g., contains parentheses)
                lines.push(`${variable.name} = sp.Function('${variable.name.split('(')[0]}')${comment}`);
            }
            else {
                // Regular symbol - but make it a function if derivatives are present
                if (hasDerivatives) {
                    lines.push(`${variable.name} = sp.Function('${variable.name}')${comment}`);
                }
                else {
                    lines.push(`${variable.name} = sp.Symbol('${variable.name}')${comment}`);
                }
            }
        }
        lines.push('');
    }
    if (parameters.length > 0) {
        lines.push('# Parameters');
        for (const parameter of parameters) {
            const comment = parameter.units ? `  # ${parameter.units}` : '';
            lines.push(`${parameter.name} = sp.Symbol('${parameter.name}')${comment}`);
        }
        lines.push('');
    }
    // Generate equations
    if (model.equations && model.equations.length > 0) {
        lines.push('# Equations');
        for (const [i, equation] of model.equations.entries()) {
            const lhs = formatPythonExpression(equation.lhs);
            const rhs = formatPythonExpression(equation.rhs);
            lines.push(`eq${i + 1} = sp.Eq(${lhs}, ${rhs})`);
        }
    }
    return lines;
}
/**
 * Generate Python code for a reaction system
 */
function generatePythonReactionSystemCode(name, reactionSystem) {
    const lines = [];
    lines.push(`# Reaction System: ${name}`);
    // Generate species symbols
    if (reactionSystem.species && Object.keys(reactionSystem.species).length > 0) {
        lines.push('# Species');
        for (const [name, species] of Object.entries(reactionSystem.species)) {
            lines.push(`${name} = sp.Symbol('${name}')`);
        }
        lines.push('');
    }
    // Generate reaction rate expressions
    if (reactionSystem.reactions && Object.keys(reactionSystem.reactions).length > 0) {
        lines.push('# Rate expressions');
        for (const [reactionName, reaction] of Object.entries(reactionSystem.reactions)) {
            if (reaction.rate) {
                const rateExpr = formatPythonExpression(reaction.rate);
                lines.push(`${reactionName}_rate = ${rateExpr}`);
            }
        }
        lines.push('');
        lines.push('# Stoichiometry setup (TODO: Implement reaction network)');
        for (const [reactionName, reaction] of Object.entries(reactionSystem.reactions)) {
            lines.push(`# Reaction: ${reactionName}`);
            if (reaction.substrates) {
                const reactantStr = reaction.substrates
                    .map(r => r.stoichiometry && r.stoichiometry !== 1 ? `${r.stoichiometry}*${r.species}` : r.species)
                    .join(' + ');
                lines.push(`#   Reactants: ${reactantStr}`);
            }
            if (reaction.products) {
                const productStr = reaction.products
                    .map(p => p.stoichiometry && p.stoichiometry !== 1 ? `${p.stoichiometry}*${p.species}` : p.species)
                    .join(' + ');
                lines.push(`#   Products: ${productStr}`);
            }
        }
    }
    return lines;
}
/**
 * Generate coupling TODO comments for Python
 */
function generatePythonCouplingComment(coupling) {
    const lines = [];
    lines.push(`# TODO: Implement coupling ${coupling.type}`);
    lines.push(`#   From: ${coupling.from}`);
    lines.push(`#   To: ${coupling.to}`);
    if (coupling.variables && coupling.variables.length > 0) {
        lines.push(`#   Variables: ${coupling.variables.join(', ')}`);
    }
    return lines;
}
/**
 * Generate domain TODO comments for Python
 */
function generatePythonDomainComment(domain) {
    const lines = [];
    lines.push(`# TODO: Implement domain`);
    if (domain.spatial_coordinates && domain.spatial_coordinates.length > 0) {
        lines.push(`#   Spatial coordinates: ${domain.spatial_coordinates.join(', ')}`);
    }
    if (domain.temporal_coordinates && domain.temporal_coordinates.length > 0) {
        lines.push(`#   Temporal coordinates: ${domain.temporal_coordinates.join(', ')}`);
    }
    return lines;
}
/**
 * Generate solver TODO comments for Python
 */
function generatePythonSolverComment(solver) {
    const lines = [];
    lines.push(`# TODO: Implement solver`);
    if (solver.algorithm) {
        lines.push(`#   Algorithm: ${solver.algorithm}`);
    }
    if (solver.tolerances) {
        lines.push(`#   Tolerances: ${JSON.stringify(solver.tolerances)}`);
    }
    return lines;
}
/**
 * Format an expression for Python code generation
 */
function formatPythonExpression(expr) {
    if (typeof expr === 'number') {
        return expr.toString();
    }
    if (typeof expr === 'string') {
        return expr;
    }
    if (typeof expr === 'object' && expr.op) {
        return formatPythonExpressionNode(expr);
    }
    throw new Error(`Unsupported expression type: ${typeof expr}`);
}
/**
 * Format an expression node for Python, applying operator mappings
 */
function formatPythonExpressionNode(node) {
    const { op, args } = node;
    // Apply expression mappings as specified in task description
    switch (op) {
        case '+':
            return args.map(formatPythonExpression).join(' + ');
        case '*':
            return args.map(formatPythonExpression).join(' * ');
        case 'D':
            // D(x,t) → Derivative(x(t), t)
            if (args.length >= 1) {
                const varName = formatPythonExpression(args[0]);
                // Assume time variable t
                return `sp.Derivative(${varName}(t), t)`;
            }
            return 'sp.Derivative()';
        case 'exp':
            return `sp.exp(${args.map(formatPythonExpression).join(', ')})`;
        case 'ifelse':
            // ifelse(condition, true_val, false_val) → sp.Piecewise((true_val, condition), (false_val, True))
            if (args.length >= 3) {
                const condition = formatPythonExpression(args[0]);
                const trueVal = formatPythonExpression(args[1]);
                const falseVal = formatPythonExpression(args[2]);
                return `sp.Piecewise((${trueVal}, ${condition}), (${falseVal}, True))`;
            }
            return `sp.Piecewise((0, True))`;
        case 'Pre':
            // Pre → Function('Pre')
            return `Function('Pre')(${args.map(formatPythonExpression).join(', ')})`;
        case '^':
            // ^ → **
            return args.map(formatPythonExpression).join(' ** ');
        case 'grad':
            // grad(x,y) → sp.Derivative(x, y)
            if (args.length >= 2) {
                const func = formatPythonExpression(args[0]);
                const var_ = formatPythonExpression(args[1]);
                return `sp.Derivative(${func}, ${var_})`;
            }
            else if (args.length === 1) {
                // Default to x if dimension not specified
                return `sp.Derivative(${formatPythonExpression(args[0])}, x)`;
            }
            return 'sp.Derivative()';
        case '-':
            if (args.length === 1) {
                return `-${formatPythonExpression(args[0])}`;
            }
            else {
                return args.map(formatPythonExpression).join(' - ');
            }
        case '/':
            return args.map(formatPythonExpression).join(' / ');
        case '<':
        case '>':
        case '<=':
        case '>=':
        case '==':
        case '!=':
            return args.map(formatPythonExpression).join(` ${op} `);
        case 'and':
            return args.map(formatPythonExpression).join(' & ');
        case 'or':
            return args.map(formatPythonExpression).join(' | ');
        case 'not':
            return `~(${formatPythonExpression(args[0])})`;
        default:
            // For other operators, use function call syntax
            return `${op}(${args.map(formatPythonExpression).join(', ')})`;
    }
}
/**
 * Check if an expression contains derivatives
 */
function hasDerivativeInExpression(expr) {
    if (typeof expr === 'object' && expr.op) {
        if (expr.op === 'D') {
            return true;
        }
        return expr.args.some(arg => hasDerivativeInExpression(arg));
    }
    return false;
}
