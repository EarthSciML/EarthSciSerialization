import { describe, it, expect } from 'vitest'

/**
 * Test fixtures for real-time validation and error highlighting in SolidJS interactive editor
 *
 * These tests define the expected behavior for:
 * - Real-time validation and error highlighting
 * - Error recovery and suggestions
 * - Warning systems for potential issues
 * - Context-sensitive validation rules
 */

describe('Interactive Editor - Validation and Error Highlighting', () => {

  describe('Real-time Syntax Validation', () => {
    it('should provide fixtures for expression syntax validation', () => {
      const syntaxValidationFixtures = {
        validExpressions: [
          {
            input: "k1 * O3",
            tokens: [
              { type: "parameter", value: "k1", valid: true },
              { type: "operator", value: "*", valid: true },
              { type: "variable", value: "O3", valid: true }
            ],
            result: { valid: true, errors: [] }
          },
          {
            input: "exp(-k1 / temperature) * O3",
            tokens: [
              { type: "function", value: "exp", valid: true },
              { type: "operator", value: "(", valid: true },
              { type: "operator", value: "-", valid: true },
              { type: "parameter", value: "k1", valid: true },
              { type: "operator", value: "/", valid: true },
              { type: "variable", value: "temperature", valid: true },
              { type: "operator", value: ")", valid: true },
              { type: "operator", value: "*", valid: true },
              { type: "variable", value: "O3", valid: true }
            ],
            result: { valid: true, errors: [] }
          }
        ],
        invalidExpressions: [
          {
            input: "k1 * O3 +",
            tokens: [
              { type: "parameter", value: "k1", valid: true },
              { type: "operator", value: "*", valid: true },
              { type: "variable", value: "O3", valid: true },
              { type: "operator", value: "+", valid: false, error: "Incomplete expression" }
            ],
            result: {
              valid: false,
              errors: [
                {
                  type: "syntax_error",
                  message: "Incomplete expression",
                  position: 7,
                  severity: "error"
                }
              ]
            }
          },
          {
            input: "k1 ** O3",
            tokens: [
              { type: "parameter", value: "k1", valid: true },
              { type: "operator", value: "**", valid: false, error: "Invalid operator" },
              { type: "variable", value: "O3", valid: true }
            ],
            result: {
              valid: false,
              errors: [
                {
                  type: "invalid_operator",
                  message: "Operator '**' not supported. Use 'pow(k1, O3)' for exponentiation.",
                  position: 3,
                  severity: "error",
                  suggestion: "pow(k1, O3)"
                }
              ]
            }
          }
        ]
      }

      expect(syntaxValidationFixtures.validExpressions[0].result.valid).toBe(true)
      expect(syntaxValidationFixtures.invalidExpressions[0].result.errors[0].type).toBe("syntax_error")
    })

    it('should provide fixtures for parentheses and bracket matching', () => {
      const parenthesesFixtures = {
        testCases: [
          {
            input: "(k1 + k2) * O3",
            brackets: { balanced: true, pairs: [[0, 8]] },
            result: { valid: true, errors: [] }
          },
          {
            input: "((k1 * O3) + (k2 * NO2))",
            brackets: {
              balanced: true,
              pairs: [[0, 24], [1, 9], [13, 23]]
            },
            result: { valid: true, errors: [] }
          },
          {
            input: "(k1 * O3",
            brackets: { balanced: false, unmatched: [0] },
            result: {
              valid: false,
              errors: [
                {
                  type: "unmatched_parenthesis",
                  message: "Unclosed parenthesis",
                  position: 0,
                  severity: "error"
                }
              ]
            }
          },
          {
            input: "k1 * O3)",
            brackets: { balanced: false, unmatched: [7] },
            result: {
              valid: false,
              errors: [
                {
                  type: "unmatched_parenthesis",
                  message: "Unexpected closing parenthesis",
                  position: 7,
                  severity: "error"
                }
              ]
            }
          }
        ]
      }

      expect(parenthesesFixtures.testCases[0].brackets.balanced).toBe(true)
      expect(parenthesesFixtures.testCases[2].result.errors[0].type).toBe("unmatched_parenthesis")
    })
  })

  describe('Semantic Validation', () => {
    it('should provide fixtures for undefined reference validation', () => {
      const semanticValidationFixtures = {
        undefinedVariables: [
          {
            expression: "k1 * undefined_var",
            variables: ["undefined_var"],
            availableVariables: ["O3", "NO2", "temperature"],
            result: {
              valid: false,
              errors: [
                {
                  type: "undefined_variable",
                  message: "Variable 'undefined_var' is not defined",
                  variable: "undefined_var",
                  suggestions: ["O3", "NO2", "temperature"],
                  severity: "error",
                  position: 5
                }
              ]
            }
          }
        ],
        undefinedParameters: [
          {
            expression: "undefined_k * O3",
            parameters: ["undefined_k"],
            availableParameters: ["k1"],
            result: {
              valid: false,
              errors: [
                {
                  type: "undefined_parameter",
                  message: "Parameter 'undefined_k' is not defined",
                  parameter: "undefined_k",
                  suggestions: ["k1", "define new parameter"],
                  severity: "error",
                  position: 0
                }
              ]
            }
          }
        ],
        undefinedFunctions: [
          {
            expression: "unknown_func(O3)",
            functions: ["unknown_func"],
            availableFunctions: ["exp", "log", "sin", "cos", "sqrt"],
            result: {
              valid: false,
              errors: [
                {
                  type: "undefined_function",
                  message: "Function 'unknown_func' is not defined",
                  function: "unknown_func",
                  suggestions: ["exp", "log"],
                  severity: "error",
                  position: 0
                }
              ]
            }
          }
        ]
      }

      expect(semanticValidationFixtures.undefinedVariables[0].result.errors[0].suggestions).toContain("O3")
      expect(semanticValidationFixtures.undefinedParameters[0].result.errors[0].type).toBe("undefined_parameter")
    })

    it('should provide fixtures for type checking and units validation', () => {
      const typeValidationFixtures = {
        unitConsistency: [
          {
            expression: "k1 * O3",
            operandUnits: ["s^-1", "mol/mol"],
            resultUnits: "mol/mol/s",
            result: { valid: true, warnings: [] }
          },
          {
            expression: "k1 + O3",
            operandUnits: ["s^-1", "mol/mol"],
            resultUnits: "incompatible",
            result: {
              valid: false,
              errors: [
                {
                  type: "unit_mismatch",
                  message: "Cannot add quantities with different units: s^-1 + mol/mol",
                  severity: "error",
                  operands: ["s^-1", "mol/mol"]
                }
              ]
            }
          }
        ],
        dimensionalAnalysis: [
          {
            expression: "exp(k1)",
            argument: "k1",
            argumentUnits: "s^-1",
            result: {
              valid: false,
              warnings: [
                {
                  type: "dimensional_warning",
                  message: "Exponential function expects dimensionless argument, got s^-1",
                  severity: "warning",
                  suggestion: "Consider k1 * dimensionless_factor"
                }
              ]
            }
          }
        ]
      }

      expect(typeValidationFixtures.unitConsistency[0].result.valid).toBe(true)
      expect(typeValidationFixtures.unitConsistency[1].result.errors[0].type).toBe("unit_mismatch")
    })
  })

  describe('Error Highlighting and Visual Feedback', () => {
    it('should provide error highlighting fixtures', () => {
      const highlightingFixtures = {
        errorStyles: {
          syntax: {
            backgroundColor: "#ffebee",
            border: "2px solid #f44336",
            textDecoration: "underline wavy #f44336"
          },
          semantic: {
            backgroundColor: "#fff3e0",
            border: "2px solid #ff9800",
            textDecoration: "underline wavy #ff9800"
          },
          warning: {
            backgroundColor: "#fffde7",
            border: "1px solid #ffc107",
            textDecoration: "underline wavy #ffc107"
          }
        },
        errorAnnotations: [
          {
            expression: "k1 * undefined_var + k2",
            annotations: [
              {
                start: 5,
                end: 17,
                type: "error",
                message: "Variable 'undefined_var' is not defined",
                severity: "error"
              },
              {
                start: 20,
                end: 22,
                type: "error",
                message: "Parameter 'k2' is not defined",
                severity: "error"
              }
            ],
            visualResult: {
              segments: [
                { text: "k1 * ", style: "normal" },
                { text: "undefined_var", style: "error" },
                { text: " + ", style: "normal" },
                { text: "k2", style: "error" }
              ]
            }
          }
        ],
        inlineErrorMessages: [
          {
            position: "below",
            content: "Variable 'undefined_var' is not defined",
            actions: ["Quick fix", "Add variable", "Ignore"],
            icon: "error",
            dismissible: true
          }
        ]
      }

      expect(highlightingFixtures.errorAnnotations[0].annotations).toHaveLength(2)
      expect(highlightingFixtures.inlineErrorMessages[0].actions).toContain("Quick fix")
    })

    it('should provide error tooltip fixtures', () => {
      const tooltipFixtures = {
        errorTooltips: [
          {
            trigger: "hover",
            target: "undefined_variable",
            content: {
              title: "Undefined Variable",
              message: "Variable 'undefined_var' is not defined in this model",
              suggestions: [
                { text: "Add variable 'undefined_var'", action: "add_variable" },
                { text: "Replace with 'O3'", action: "replace_with", value: "O3" },
                { text: "Replace with 'NO2'", action: "replace_with", value: "NO2" }
              ],
              learnMore: {
                text: "Learn about variable definitions",
                url: "/docs/variables"
              }
            }
          }
        ],
        warningTooltips: [
          {
            trigger: "hover",
            target: "dimensional_issue",
            content: {
              title: "Dimensional Analysis Warning",
              message: "This expression may have dimensional inconsistencies",
              details: "Exponential functions expect dimensionless arguments",
              severity: "warning",
              canIgnore: true
            }
          }
        ]
      }

      expect(tooltipFixtures.errorTooltips[0].content.suggestions).toHaveLength(3)
    })
  })

  describe('Auto-correction and Suggestions', () => {
    it('should provide auto-correction fixtures', () => {
      const autoCorrectionFixtures = {
        typoCorrection: [
          {
            input: "k1 * 03",  // Common typo: 03 instead of O3
            suggestions: [
              { text: "O3", confidence: 0.9, reason: "Similar variable name" },
              { text: "NO3", confidence: 0.3, reason: "Contains '3'" }
            ],
            autoCorrect: { enabled: true, threshold: 0.8, suggestion: "O3" }
          },
          {
            input: "k1 * NO",  // Partial variable name
            suggestions: [
              { text: "NO2", confidence: 0.8, reason: "Extends existing variable" },
              { text: "NO3", confidence: 0.6, reason: "Common chemical species" }
            ]
          }
        ],
        operatorCorrection: [
          {
            input: "k1 ^ O3",  // Wrong exponentiation operator
            correction: "pow(k1, O3)",
            message: "Did you mean exponentiation? Use pow(base, exponent)"
          },
          {
            input: "k1 && O3",  // Wrong logical operator
            correction: "k1 * O3",
            message: "Did you mean multiplication? Use * for arithmetic"
          }
        ],
        contextualSuggestions: [
          {
            context: "rate_expression",
            partialInput: "exp(-",
            suggestions: [
              { text: "exp(-Ea/(R*T))", description: "Arrhenius rate expression" },
              { text: "exp(-k1*t)", description: "First-order decay" }
            ]
          }
        ]
      }

      expect(autoCorrectionFixtures.typoCorrection[0].autoCorrect.suggestion).toBe("O3")
      expect(autoCorrectionFixtures.operatorCorrection[0].correction).toBe("pow(k1, O3)")
    })

    it('should provide smart completion fixtures', () => {
      const completionFixtures = {
        variableCompletion: [
          {
            prefix: "O",
            context: "Chemistry.equations",
            suggestions: [
              { text: "O3", description: "Ozone concentration", type: "variable" },
              { text: "O2", description: "Oxygen concentration", type: "variable", available: false }
            ]
          }
        ],
        functionCompletion: [
          {
            prefix: "ex",
            context: "expression",
            suggestions: [
              {
                text: "exp",
                description: "Exponential function",
                signature: "exp(x)",
                example: "exp(-k1/temperature)"
              }
            ]
          }
        ],
        parameterCompletion: [
          {
            prefix: "k",
            context: "Chemistry.equations",
            suggestions: [
              { text: "k1", description: "Rate constant", value: "1.2×10⁻⁵", units: "s⁻¹" }
            ]
          }
        ]
      }

      expect(completionFixtures.variableCompletion[0].suggestions[0].text).toBe("O3")
    })
  })

  describe('Validation Performance and Debouncing', () => {
    it('should provide performance fixtures for real-time validation', () => {
      const performanceFixtures = {
        debouncing: {
          delay: 300, // ms
          testScenarios: [
            {
              keystrokes: ["k", "1", " ", "*", " ", "O", "3"],
              timing: [0, 100, 200, 300, 400, 500, 600],
              expectedValidations: 1, // Only after final keystroke + delay
              description: "Fast typing should debounce validation"
            },
            {
              keystrokes: ["k", "1"],
              timing: [0, 100],
              pause: 500, // User pauses
              moreKeystrokes: [" ", "*", " ", "O", "3"],
              moreTiming: [600, 700, 800, 900, 1000],
              expectedValidations: 2, // After pause and after final sequence
              description: "Pause should trigger intermediate validation"
            }
          ]
        },
        throttling: {
          maxValidationsPerSecond: 5,
          testScenario: {
            continuousTyping: 60, // keystrokes per second
            duration: 2000, // ms
            expectedValidations: 10, // 5 per second * 2 seconds
            description: "Very fast typing should be throttled"
          }
        }
      }

      expect(performanceFixtures.debouncing.testScenarios[0].expectedValidations).toBe(1)
      expect(performanceFixtures.throttling.testScenario.expectedValidations).toBe(10)
    })
  })

  describe('Context-Sensitive Validation Rules', () => {
    it('should provide context-specific validation fixtures', () => {
      const contextValidationFixtures = {
        equationContext: {
          allowedElements: ["variables", "parameters", "functions", "operators"],
          forbiddenElements: ["species", "reactions"],
          validationRules: [
            {
              rule: "no_assignment_operators",
              invalid: ["=", ":=", "+="],
              message: "Assignment operators not allowed in equations"
            },
            {
              rule: "balanced_expressions",
              description: "Left and right sides must be dimensionally consistent"
            }
          ]
        },
        reactionContext: {
          allowedElements: ["species", "stoichiometry", "rate_parameters"],
          validationRules: [
            {
              rule: "valid_species_names",
              pattern: "^[A-Z][A-Za-z0-9_]*$",
              examples: ["O3", "NO2", "H2SO4"],
              invalid: ["o3", "2NO", "H+"]
            },
            {
              rule: "positive_stoichiometry",
              description: "Stoichiometric coefficients must be positive"
            }
          ]
        },
        parameterContext: {
          validationRules: [
            {
              rule: "numeric_values",
              allowedTypes: ["number", "scientific_notation"],
              invalid: ["string", "boolean", "array"]
            },
            {
              rule: "physical_constraints",
              description: "Rate constants should be non-negative"
            }
          ]
        }
      }

      expect(contextValidationFixtures.equationContext.allowedElements).toContain("variables")
      expect(contextValidationFixtures.reactionContext.validationRules[0].examples).toContain("O3")
    })
  })

  describe('Batch Validation and Error Reporting', () => {
    it('should provide batch validation fixtures', () => {
      const batchValidationFixtures = {
        modelWideValidation: {
          checks: [
            {
              name: "undefined_references",
              scope: "all_equations",
              errors: [
                {
                  equation: "invalid_eq",
                  issues: [
                    { type: "undefined_parameter", reference: "k2" },
                    { type: "undefined_variable", reference: "undefined_var" }
                  ]
                }
              ]
            },
            {
              name: "unit_consistency",
              scope: "all_equations",
              warnings: [
                {
                  equation: "temperature_dependent",
                  issue: "Dimensionless argument expected in exp()"
                }
              ]
            }
          ],
          summary: {
            totalErrors: 2,
            totalWarnings: 1,
            criticalIssues: 0,
            canSave: false
          }
        },
        progressiveValidation: {
          phases: [
            { name: "syntax", weight: 30, duration: "fast" },
            { name: "semantic", weight: 40, duration: "medium" },
            { name: "dimensional", weight: 30, duration: "slow" }
          ],
          progress: {
            current: "semantic",
            percent: 60,
            estimatedTimeRemaining: 150 // ms
          }
        }
      }

      expect(batchValidationFixtures.modelWideValidation.summary.canSave).toBe(false)
      expect(batchValidationFixtures.progressiveValidation.progress.percent).toBe(60)
    })
  })
})