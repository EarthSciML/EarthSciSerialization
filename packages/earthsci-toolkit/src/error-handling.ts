/**
 * Comprehensive error handling and diagnostics system for ESM Format TypeScript.
 *
 * This module provides:
 * 1. Standardized error codes and messages
 * 2. User-friendly error reporting with fix suggestions
 * 3. Debugging aids for complex coupling issues
 * 4. Performance profiling tools
 * 5. Interactive error exploration helpers
 */

// Standardized error codes for consistent error handling across all libraries
export enum ErrorCode {
  // Schema and Parsing Errors (1000-1999)
  JSON_PARSE_ERROR = 'ESM1001',
  SCHEMA_VALIDATION_ERROR = 'ESM1002',
  UNSUPPORTED_VERSION = 'ESM1003',
  MISSING_REQUIRED_FIELD = 'ESM1004',
  INVALID_FIELD_TYPE = 'ESM1005',

  // Structural Validation Errors (2000-2999)
  EQUATION_UNKNOWN_IMBALANCE = 'ESM2001',
  UNDEFINED_REFERENCE = 'ESM2002',
  INVALID_SCOPE_PATH = 'ESM2003',
  CIRCULAR_DEPENDENCY = 'ESM2004',
  MISSING_COUPLING_TARGET = 'ESM2005',
  INVALID_REACTION_STOICHIOMETRY = 'ESM2006',
  UNDECLARED_SPECIES = 'ESM2007',
  UNDECLARED_PARAMETER = 'ESM2008',
  NULL_NULL_REACTION = 'ESM2009',

  // Expression and Mathematical Errors (3000-3999)
  EXPRESSION_PARSE_ERROR = 'ESM3001',
  UNDEFINED_VARIABLE = 'ESM3002',
  TYPE_MISMATCH = 'ESM3003',
  DIVISION_BY_ZERO = 'ESM3004',
  MATHEMATICAL_INCONSISTENCY = 'ESM3005',
  UNIT_MISMATCH = 'ESM3006',
  DIMENSION_ERROR = 'ESM3007',

  // Coupling and System Integration Errors (4000-4999)
  COUPLING_RESOLUTION_ERROR = 'ESM4001',
  SCOPE_BOUNDARY_VIOLATION = 'ESM4002',
  VARIABLE_SHADOWING = 'ESM4003',
  DEEP_NESTING_WARNING = 'ESM4004',
  UNUSED_VARIABLE = 'ESM4005',
  COUPLING_GRAPH_CYCLE = 'ESM4006',
  INCOMPATIBLE_DOMAINS = 'ESM4007',

  // Simulation and Runtime Errors (5000-5999)
  SIMULATION_CONVERGENCE_ERROR = 'ESM5001',
  SOLVER_CONFIGURATION_ERROR = 'ESM5002',
  BOUNDARY_CONDITION_ERROR = 'ESM5003',
  TIME_SYNCHRONIZATION_ERROR = 'ESM5004',
  DATA_LOADER_ERROR = 'ESM5005',
  OPERATOR_EXECUTION_ERROR = 'ESM5006',

  // Performance and Resource Errors (6000-6999)
  MEMORY_LIMIT_EXCEEDED = 'ESM6001',
  COMPUTATION_TIMEOUT = 'ESM6002',
  LARGE_SYSTEM_WARNING = 'ESM6003',
  INEFFICIENT_COUPLING = 'ESM6004',

  // User Interface and Interactive Errors (7000-7999)
  EDITOR_STATE_ERROR = 'ESM7001',
  INVALID_USER_INPUT = 'ESM7002',
  DISPLAY_RENDERING_ERROR = 'ESM7003'
}

// Error severity levels
export enum Severity {
  CRITICAL = 'critical',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
  DEBUG = 'debug'
}

// Additional context information for errors
export interface ErrorContext {
  filePath?: string
  lineNumber?: number
  column?: number
  componentName?: string
  operation?: string
  userInput?: any
  systemState?: Record<string, any>
  performanceMetrics?: Record<string, number>
}

// Actionable suggestion for fixing an error
export interface FixSuggestion {
  description: string
  codeExample?: string
  documentationLink?: string
  automatedFix?: () => void
  priority: number // 1 = highest priority
}

// Comprehensive error representation with diagnostics and suggestions
export interface ESMError {
  code: ErrorCode
  message: string
  severity: Severity
  path: string
  context?: ErrorContext
  fixSuggestions: FixSuggestion[]
  relatedErrors: ESMError[]
  timestamp: number
  debugInfo: Record<string, any>
}

// Collects and manages errors during ESM processing
export class ErrorCollector {
  private errors: ESMError[] = []
  private warnings: ESMError[] = []
  private performanceData: Record<string, number> = {}

  addError(error: ESMError): void {
    if (error.severity === Severity.CRITICAL || error.severity === Severity.ERROR) {
      this.errors.push(error)
    } else {
      this.warnings.push(error)
    }
  }

  hasErrors(): boolean {
    return this.errors.length > 0
  }

  hasWarnings(): boolean {
    return this.warnings.length > 0
  }

  getErrors(): ESMError[] {
    return [...this.errors]
  }

  getWarnings(): ESMError[] {
    return [...this.warnings]
  }

  getAllErrors(): ESMError[] {
    return [...this.errors, ...this.warnings]
  }

  getSummary(): string {
    if (this.errors.length === 0 && this.warnings.length === 0) {
      return '✅ No errors or warnings'
    }

    const parts: string[] = []
    if (this.errors.length > 0) {
      parts.push(`❌ ${this.errors.length} error(s)`)
    }
    if (this.warnings.length > 0) {
      parts.push(`⚠️  ${this.warnings.length} warning(s)`)
    }

    return parts.join(', ')
  }

  exportReport(format: 'json' | 'text' = 'json'): string {
    const allErrors = [...this.errors, ...this.warnings]

    if (format === 'json') {
      return JSON.stringify(allErrors.map(error => ({
        code: error.code,
        message: error.message,
        severity: error.severity,
        path: error.path,
        timestamp: error.timestamp,
        context: error.context || {},
        fixSuggestions: error.fixSuggestions.map(s => ({
          description: s.description,
          codeExample: s.codeExample,
          documentationLink: s.documentationLink,
          priority: s.priority
        })),
        debugInfo: error.debugInfo
      })), null, 2)
    } else {
      return allErrors.map(error => formatUserFriendly(error)).join('\n\n')
    }
  }

  clear(): void {
    this.errors = []
    this.warnings = []
    this.performanceData = {}
  }
}

// Format error message for end users
export function formatUserFriendly(error: ESMError): string {
  const lines: string[] = []

  // Header with severity and code
  const severityIcons = {
    [Severity.CRITICAL]: '🚫',
    [Severity.ERROR]: '❌',
    [Severity.WARNING]: '⚠️',
    [Severity.INFO]: 'ℹ️',
    [Severity.DEBUG]: '🔍'
  }

  const icon = severityIcons[error.severity] || '•'
  lines.push(`${icon} ${error.severity.toUpperCase()} [${error.code}]`)
  lines.push(`   ${error.message}`)

  if (error.path) {
    lines.push(`   Location: ${error.path}`)
  }

  if (error.context) {
    const contextParts: string[] = []
    if (error.context.filePath) {
      contextParts.push(error.context.filePath)
    }
    if (error.context.lineNumber !== undefined) {
      contextParts.push(`line ${error.context.lineNumber}`)
    }
    if (error.context.column !== undefined) {
      contextParts.push(`col ${error.context.column}`)
    }
    if (contextParts.length > 0) {
      lines.push(`   File: ${contextParts.join(':')}`)
    }
  }

  // Fix suggestions
  if (error.fixSuggestions.length > 0) {
    lines.push('')
    lines.push('💡 Suggested fixes:')
    const sortedSuggestions = [...error.fixSuggestions].sort((a, b) => a.priority - b.priority)
    sortedSuggestions.forEach((suggestion, index) => {
      lines.push(`   ${index + 1}. ${suggestion.description}`)
      if (suggestion.codeExample) {
        lines.push(`      Example: ${suggestion.codeExample}`)
      }
      if (suggestion.documentationLink) {
        lines.push(`      Docs: ${suggestion.documentationLink}`)
      }
    })
  }

  return lines.join('\n')
}

// Factory for creating standardized ESM errors with helpful suggestions
export class ESMErrorFactory {
  static createJsonParseError(message: string, filePath = '', lineNumber?: number): ESMError {
    const context: ErrorContext = {
      filePath,
      lineNumber,
      operation: 'json_parsing'
    }

    const suggestions: FixSuggestion[] = [
      {
        description: 'Check for missing commas, quotes, or brackets',
        codeExample: '{"valid": "json", "array": [1, 2, 3]}',
        priority: 1
      },
      {
        description: 'Validate JSON syntax using an online JSON validator',
        documentationLink: 'https://jsonlint.com/',
        priority: 2
      }
    ]

    return {
      code: ErrorCode.JSON_PARSE_ERROR,
      message: `Failed to parse JSON: ${message}`,
      severity: Severity.ERROR,
      path: filePath,
      context,
      fixSuggestions: suggestions,
      relatedErrors: [],
      timestamp: Date.now(),
      debugInfo: {}
    }
  }

  static createEquationImbalanceError(
    modelName: string,
    numEquations: number,
    numUnknowns: number,
    stateVariables: string[]
  ): ESMError {
    const context: ErrorContext = {
      componentName: modelName,
      operation: 'structural_validation'
    }

    const suggestions: FixSuggestion[] = []
    if (numEquations < numUnknowns) {
      const diff = numUnknowns - numEquations
      suggestions.push({
        description: `Add ${diff} more equation(s) to balance the system`,
        codeExample: `"equations": [{"lhs": "d${stateVariables[0]}/dt", "rhs": "expression"}]`,
        priority: 1
      })
    } else {
      const diff = numEquations - numUnknowns
      suggestions.push({
        description: `Remove ${diff} equation(s) or add ${diff} more state variable(s)`,
        priority: 1
      })
    }

    suggestions.push({
      description: 'Review the mathematical model to ensure proper formulation',
      documentationLink: 'https://docs.earthsciml.org/esm-format/models/#equation-balance',
      priority: 2
    })

    const message = `Model '${modelName}' has ${numEquations} equations but ${numUnknowns} unknowns (state variables: ${stateVariables.join(', ')})`

    return {
      code: ErrorCode.EQUATION_UNKNOWN_IMBALANCE,
      message,
      severity: Severity.ERROR,
      path: `/models[name='${modelName}']`,
      context,
      fixSuggestions: suggestions,
      relatedErrors: [],
      timestamp: Date.now(),
      debugInfo: {}
    }
  }

  static createUndefinedReferenceError(
    reference: string,
    availableVariables: string[] = [],
    scopePath = ''
  ): ESMError {
    const context: ErrorContext = {
      operation: 'reference_resolution'
    }

    const suggestions: FixSuggestion[] = []

    // Smart suggestions based on available variables
    if (availableVariables.length > 0) {
      // Find close matches using simple string similarity
      const closeMatches: string[] = []
      const refLower = reference.toLowerCase()
      for (const variable of availableVariables) {
        const varLower = variable.toLowerCase()
        if (varLower.includes(refLower) || refLower.includes(varLower)) {
          closeMatches.push(variable)
        }
      }

      if (closeMatches.length > 0) {
        suggestions.push({
          description: `Did you mean: ${closeMatches.slice(0, 3).join(', ')}?`,
          codeExample: `"reference": "${closeMatches[0]}"`,
          priority: 1
        })
      }
    }

    suggestions.push(
      {
        description: 'Check variable names and scopes for typos',
        priority: 2
      },
      {
        description: 'Ensure the variable is declared in the correct scope',
        documentationLink: 'https://docs.earthsciml.org/esm-format/scoping/',
        priority: 3
      }
    )

    const debugInfo = {
      reference,
      scopePath,
      availableVariables: availableVariables || []
    }

    return {
      code: ErrorCode.UNDEFINED_REFERENCE,
      message: `Reference '${reference}' is not defined in the current scope`,
      severity: Severity.ERROR,
      path: scopePath,
      context,
      fixSuggestions: suggestions,
      relatedErrors: [],
      timestamp: Date.now(),
      debugInfo
    }
  }

  static createPerformanceWarning(operation: string, duration: number, threshold = 1000): ESMError {
    const context: ErrorContext = {
      operation,
      performanceMetrics: {
        durationMs: duration,
        thresholdMs: threshold
      }
    }

    const suggestions: FixSuggestion[] = [
      {
        description: 'Consider simplifying complex expressions',
        priority: 1
      },
      {
        description: 'Check for inefficient coupling patterns',
        documentationLink: 'https://docs.earthsciml.org/esm-format/performance/',
        priority: 2
      },
      {
        description: 'Use performance profiling tools to identify bottlenecks',
        codeExample: 'import { PerformanceProfiler } from "earthsci-toolkit/error-handling"',
        priority: 3
      }
    ]

    return {
      code: ErrorCode.LARGE_SYSTEM_WARNING,
      message: `Operation '${operation}' took ${duration.toFixed(0)}ms (threshold: ${threshold.toFixed(0)}ms)`,
      severity: Severity.WARNING,
      path: '',
      context,
      fixSuggestions: suggestions,
      relatedErrors: [],
      timestamp: Date.now(),
      debugInfo: {}
    }
  }
}

// Performance profiling tool for ESM operations
export class PerformanceProfiler {
  private timings: Record<string, number[]> = {}
  private memoryUsage: Record<string, number[]> = {}
  private activeTimers: Record<string, number> = {}

  startTimer(operation: string): void {
    this.activeTimers[operation] = performance.now()
  }

  endTimer(operation: string): number {
    if (!(operation in this.activeTimers)) {
      return 0
    }

    const duration = performance.now() - this.activeTimers[operation]
    delete this.activeTimers[operation]

    if (!(operation in this.timings)) {
      this.timings[operation] = []
    }
    this.timings[operation].push(duration)

    return duration
  }

  getReport(): Record<string, any> {
    const report: Record<string, any> = {}
    for (const [operation, times] of Object.entries(this.timings)) {
      report[operation] = {
        count: times.length,
        totalTime: times.reduce((sum, time) => sum + time, 0),
        averageTime: times.length > 0 ? times.reduce((sum, time) => sum + time, 0) / times.length : 0,
        minTime: times.length > 0 ? Math.min(...times) : 0,
        maxTime: times.length > 0 ? Math.max(...times) : 0
      }
    }
    return report
  }

  clear(): void {
    this.timings = {}
    this.memoryUsage = {}
    this.activeTimers = {}
  }
}

// Global profiler instance
const globalProfiler = new PerformanceProfiler()

export function getProfiler(): PerformanceProfiler {
  return globalProfiler
}

// Decorator for profiling operations
export function profileOperation(operationName: string) {
  return function <T extends (...args: any[]) => any>(
    target: any,
    propertyKey: string,
    descriptor: TypedPropertyDescriptor<T>
  ) {
    const originalMethod = descriptor.value!

    descriptor.value = function (...args: any[]) {
      const profiler = getProfiler()
      profiler.startTimer(operationName)

      try {
        const result = originalMethod.apply(this, args)

        // Handle both sync and async operations
        if (result && typeof result.then === 'function') {
          return result.finally(() => {
            const duration = profiler.endTimer(operationName)
            if (duration > 1000) { // 1 second threshold
              const warning = ESMErrorFactory.createPerformanceWarning(operationName, duration, 1000)
              console.warn(formatUserFriendly(warning))
            }
          })
        } else {
          const duration = profiler.endTimer(operationName)
          if (duration > 1000) { // 1 second threshold
            const warning = ESMErrorFactory.createPerformanceWarning(operationName, duration, 1000)
            console.warn(formatUserFriendly(warning))
          }
          return result
        }
      } catch (error) {
        profiler.endTimer(operationName)
        throw error
      }
    } as T

    return descriptor
  }
}

// Interactive tools for exploring and understanding errors
export class InteractiveErrorExplorer {
  static analyzeCouplingIssues(esmFile: any, errorCollector: ErrorCollector): Record<string, any> {
    const analysis = {
      couplingGraphValid: true,
      circularDependencies: [] as string[],
      orphanedComponents: [] as string[],
      complexCouplingPaths: [] as string[],
      suggestions: [] as string[]
    }

    try {
      // Check for orphaned components
      const allComponents = new Set<string>()
      const coupledComponents = new Set<string>()

      // Collect all model and reaction system names
      if (esmFile.models) {
        for (const model of esmFile.models) {
          allComponents.add(model.name)
        }
      }
      if (esmFile.reactionSystems) {
        for (const rs of esmFile.reactionSystems) {
          allComponents.add(rs.name)
        }
      }

      // Collect coupled component names
      if (esmFile.couplings) {
        for (const coupling of esmFile.couplings) {
          coupledComponents.add(coupling.sourceModel)
          coupledComponents.add(coupling.targetModel)
        }
      }

      // Find orphaned components
      const orphaned = Array.from(allComponents).filter(comp => !coupledComponents.has(comp))
      if (orphaned.length > 0) {
        analysis.orphanedComponents = orphaned
        analysis.suggestions.push('Consider adding coupling entries for isolated components')
      }

    } catch (error) {
      analysis.couplingGraphValid = false
      analysis.suggestions.push(`Coupling analysis failed: ${error}`)
    }

    return analysis
  }

  static suggestModelImprovements(esmFile: any, errors: ESMError[]): string[] {
    const suggestions: string[] = []

    // Analyze error patterns
    const errorCodes = errors.map(error => error.code)

    if (errorCodes.includes(ErrorCode.EQUATION_UNKNOWN_IMBALANCE)) {
      suggestions.push('Review mathematical formulation - ensure ODEs are properly balanced')
    }

    if (errorCodes.includes(ErrorCode.UNDEFINED_REFERENCE)) {
      suggestions.push('Check variable scoping and naming conventions')
    }

    if (errorCodes.includes(ErrorCode.UNIT_MISMATCH)) {
      suggestions.push('Ensure dimensional consistency across equations')
    }

    // Check for complexity indicators
    const totalEquations = esmFile.models ?
      esmFile.models.reduce((sum: number, model: any) => sum + (model.equations?.length || 0), 0) : 0
    const totalVariables = esmFile.models ?
      esmFile.models.reduce((sum: number, model: any) => sum + (model.variables ? Object.keys(model.variables).length : 0), 0) : 0

    if (totalEquations > 100) {
      suggestions.push('Consider modularizing large models into smaller components')
    }

    if (esmFile.couplings && esmFile.couplings.length > 20) {
      suggestions.push('Review coupling architecture for potential simplification')
    }

    return suggestions
  }
}

// Setup error logging for development and debugging
export interface ErrorLoggerConfig {
  logLevel: 'debug' | 'info' | 'warn' | 'error'
  logToConsole: boolean
  logToFile?: string
  maxLogSize?: number
}

export function setupErrorLogging(config: ErrorLoggerConfig = { logLevel: 'info', logToConsole: true }) {
  // This would typically set up a logger like Winston or similar
  // For now, just configure console logging

  const logLevels = { debug: 0, info: 1, warn: 2, error: 3 }
  const currentLevel = logLevels[config.logLevel]

  return {
    debug: (message: string, ...args: any[]) => {
      if (currentLevel <= 0 && config.logToConsole) {
        console.debug(`[ESM DEBUG] ${message}`, ...args)
      }
    },
    info: (message: string, ...args: any[]) => {
      if (currentLevel <= 1 && config.logToConsole) {
        console.info(`[ESM INFO] ${message}`, ...args)
      }
    },
    warn: (message: string, ...args: any[]) => {
      if (currentLevel <= 2 && config.logToConsole) {
        console.warn(`[ESM WARN] ${message}`, ...args)
      }
    },
    error: (message: string, ...args: any[]) => {
      if (currentLevel <= 3 && config.logToConsole) {
        console.error(`[ESM ERROR] ${message}`, ...args)
      }
    }
  }
}