package esm

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strings"
)

// chemicalElements contains all 118 chemical element symbols for element-aware tokenizer
var chemicalElements = map[string]bool{
	// Period 1
	"H": true, "He": true,
	// Period 2
	"Li": true, "Be": true, "B": true, "C": true, "N": true, "O": true, "F": true, "Ne": true,
	// Period 3
	"Na": true, "Mg": true, "Al": true, "Si": true, "P": true, "S": true, "Cl": true, "Ar": true,
	// Period 4
	"K": true, "Ca": true, "Sc": true, "Ti": true, "V": true, "Cr": true, "Mn": true, "Fe": true,
	"Co": true, "Ni": true, "Cu": true, "Zn": true, "Ga": true, "Ge": true, "As": true, "Se": true,
	"Br": true, "Kr": true,
	// Period 5
	"Rb": true, "Sr": true, "Y": true, "Zr": true, "Nb": true, "Mo": true, "Tc": true, "Ru": true,
	"Rh": true, "Pd": true, "Ag": true, "Cd": true, "In": true, "Sn": true, "Sb": true, "Te": true,
	"I": true, "Xe": true,
	// Period 6
	"Cs": true, "Ba": true, "La": true, "Ce": true, "Pr": true, "Nd": true, "Pm": true, "Sm": true,
	"Eu": true, "Gd": true, "Tb": true, "Dy": true, "Ho": true, "Er": true, "Tm": true, "Yb": true,
	"Lu": true, "Hf": true, "Ta": true, "W": true, "Re": true, "Os": true, "Ir": true, "Pt": true,
	"Au": true, "Hg": true, "Tl": true, "Pb": true, "Bi": true, "Po": true, "At": true, "Rn": true,
	// Period 7
	"Fr": true, "Ra": true, "Ac": true, "Th": true, "Pa": true, "U": true, "Np": true, "Pu": true,
	"Am": true, "Cm": true, "Bk": true, "Cf": true, "Es": true, "Fm": true, "Md": true, "No": true,
	"Lr": true, "Rf": true, "Db": true, "Sg": true, "Bh": true, "Hs": true, "Mt": true, "Ds": true,
	"Rg": true, "Cn": true, "Nh": true, "Fl": true, "Mc": true, "Lv": true, "Ts": true, "Og": true,
}

// ToUnicode converts an expression to Unicode string with chemical subscripts and operator precedence
func ToUnicode(target interface{}) string {
	return formatExpression(target, "unicode")
}

// ToLatex converts an expression to LaTeX string with chemical subscripts and operator precedence
func ToLatex(target interface{}) string {
	return formatExpression(target, "latex")
}

// formatExpression is the internal function that handles different output formats
func formatExpression(target interface{}, format string) string {
	switch expr := target.(type) {
	case float64:
		return formatNumber(expr, format)
	case int:
		return formatNumber(float64(expr), format)
	case string:
		return formatVariable(expr, format)
	case ExprNode:
		return formatExprNode(expr, format, 0)
	case *ExprNode:
		return formatExprNode(*expr, format, 0)
	default:
		return fmt.Sprintf("%v", target)
	}
}

// formatNumber formats numeric values with scientific notation when appropriate
func formatNumber(num float64, format string) string {
	if num == 0 {
		return "0"
	}

	// Handle scientific notation for very large or very small numbers
	abs := math.Abs(num)
	if abs >= 1e4 || abs < 1e-3 {
		// Calculate exponent manually for better control
		exp := int(math.Floor(math.Log10(abs)))
		mantissa := num / math.Pow(10, float64(exp))

		switch format {
		case "unicode":
			expStr := formatSuperscript(exp)
			mantissaStr := fmt.Sprintf("%.3g", mantissa)
			// Replace regular minus with unicode minus for negative mantissa
			if strings.HasPrefix(mantissaStr, "-") {
				mantissaStr = "−" + mantissaStr[1:]
			}
			return fmt.Sprintf("%s×10%s", mantissaStr, expStr)
		case "latex":
			return fmt.Sprintf("%.3g \\times 10^{%d}", mantissa, exp)
		default:
			return fmt.Sprintf("%.2g", num)
		}
	}

	result := fmt.Sprintf("%g", num)
	// Replace regular minus with unicode minus in unicode format
	if format == "unicode" && strings.HasPrefix(result, "-") {
		result = "−" + result[1:]
	}
	return result
}

// formatVariable formats variable names with chemical subscripts
func formatVariable(varName string, format string) string {
	switch format {
	case "unicode":
		return formatChemicalSubscripts(varName, format)
	case "latex":
		// In LaTeX, put chemical variables in \mathrm{}
		formatted := formatChemicalSubscripts(varName, format)
		if isChemicalSpecies(varName) {
			return "\\mathrm{" + formatted + "}"
		}
		return formatted
	default:
		return varName
	}
}

// isChemicalSpecies detects if a variable name represents a chemical species using element-aware tokenizer
func isChemicalSpecies(name string) bool {
	return hasElementPattern(name)
}

// hasElementPattern checks if a variable has element patterns for chemical formula detection
func hasElementPattern(variable string) bool {
	i := 0
	hasElement := false

	for i < len(variable) {
		// Skip non-alphabetic characters at the start
		for i < len(variable) && !isAlpha(variable[i]) {
			i++
		}

		if i >= len(variable) {
			break
		}

		// Try 2-character element first (greedy matching)
		if i+1 < len(variable) {
			twoChar := variable[i : i+2]
			if chemicalElements[twoChar] {
				hasElement = true
				i += 2
				// Skip digits
				for i < len(variable) && isDigit(variable[i]) {
					i++
				}
				continue
			}
		}

		// Try 1-character element
		oneChar := string(variable[i])
		if chemicalElements[oneChar] {
			hasElement = true
			i++
			// Skip digits
			for i < len(variable) && isDigit(variable[i]) {
				i++
			}
			continue
		}

		// Not an element, move to next character
		i++
	}

	return hasElement
}

// Helper functions for character classification
func isAlpha(c byte) bool {
	return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')
}

func isDigit(c byte) bool {
	return c >= '0' && c <= '9'
}

// formatChemicalSubscripts converts numbers in chemical formulas to subscripts using element-aware tokenizer
func formatChemicalSubscripts(name string, format string) string {
	// Check if variable looks like a chemical formula
	hasElements := hasElementPattern(name)

	// Handle LaTeX format first
	if format == "latex" {
		if hasElements {
			// Chemical formula: convert digits to subscripts using regex
			re := regexp.MustCompile(`([A-Za-z])([0-9]+)`)
			result := re.ReplaceAllString(name, `${1}_{${2}}`)
			return result
		}
		// Regular variable: return as-is
		return name
	}

	// For unicode format, only apply subscript conversion if it has element patterns
	if !hasElements {
		return name
	}

	// Element-aware subscript conversion for unicode format
	result := strings.Builder{}
	i := 0

	for i < len(name) {
		matched := false

		// Try 2-character element first (greedy matching)
		if i+1 < len(name) {
			twoChar := name[i : i+2]
			if chemicalElements[twoChar] {
				result.WriteString(twoChar)
				i += 2
				// Convert following digits to subscripts
				for i < len(name) && isDigit(name[i]) {
					result.WriteString(formatSubscript(string(name[i])))
					i++
				}
				matched = true
			}
		}

		// Try 1-character element if 2-char didn't match
		if !matched && i < len(name) {
			oneChar := string(name[i])
			if chemicalElements[oneChar] {
				result.WriteString(oneChar)
				i++
				// Convert following digits to subscripts
				for i < len(name) && isDigit(name[i]) {
					result.WriteString(formatSubscript(string(name[i])))
					i++
				}
				matched = true
			}
		}

		// If not an element, copy character as-is
		if !matched {
			result.WriteByte(name[i])
			i++
		}
	}

	return result.String()
}

// formatSubscript converts numbers to Unicode subscript characters
func formatSubscript(num string) string {
	subscripts := map[rune]rune{
		'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
		'5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
	}

	result := strings.Builder{}
	for _, char := range num {
		if sub, ok := subscripts[char]; ok {
			result.WriteRune(sub)
		} else {
			result.WriteRune(char)
		}
	}
	return result.String()
}

// formatSuperscript converts numbers to Unicode superscript characters
func formatSuperscript(num int) string {
	superscripts := map[rune]rune{
		'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
		'5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
		'-': '⁻', '+': '⁺',
	}

	numStr := fmt.Sprintf("%d", num)
	result := strings.Builder{}
	for _, char := range numStr {
		if sup, ok := superscripts[char]; ok {
			result.WriteRune(sup)
		} else {
			result.WriteRune(char)
		}
	}
	return result.String()
}

// Operator precedence levels (higher number = higher precedence)
func getOperatorPrecedence(op string) int {
	switch op {
	case "or":
		return 1
	case "and":
		return 2
	case "==", "!=", "<", ">", "<=", ">=":
		return 3
	case "+", "-":
		return 4
	case "*", "/":
		return 5
	case "^":
		return 6
	case "exp", "log", "log10", "sqrt", "abs", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sign":
		return 7
	case "D", "grad", "div", "laplacian":
		return 8
	default:
		return 9 // Functions and other operators
	}
}

// needsParentheses determines if an expression needs parentheses based on operator precedence
func needsParentheses(childOp string, parentOp string, isRightChild bool) bool {
	childPrec := getOperatorPrecedence(childOp)
	parentPrec := getOperatorPrecedence(parentOp)

	if childPrec < parentPrec {
		return true
	}

	// Right-associative operators (like ^) need special handling
	if childPrec == parentPrec && isRightChild && (parentOp == "^" || parentOp == "/") {
		return false
	}

	// Same precedence on the right side of non-associative operators needs parentheses
	if childPrec == parentPrec && isRightChild && (parentOp == "-" || parentOp == "/") {
		return true
	}

	return false
}

// formatExprNode formats an expression node with proper precedence and parentheses
func formatExprNode(node ExprNode, format string, parentPrecedence int) string {
	op := node.Op
	args := node.Args

	switch op {
	case "+":
		if len(args) < 2 {
			return op + "(...)"
		}

		parts := make([]string, len(args))
		for i, arg := range args {
			parts[i] = formatExpression(arg, format)
		}

		return strings.Join(parts, " + ")

	case "-":
		if len(args) == 1 {
			// Unary minus
			arg := formatExpression(args[0], format)
			switch format {
			case "unicode":
				return "−" + arg
			case "latex":
				return "-" + arg
			default:
				return "-" + arg
			}
		}
		// Binary subtraction - format as a + (-b)
		if len(args) == 2 {
			left := formatExpression(args[0], format)
			right := formatExpression(args[1], format)

			// Check if we need to add parentheses around the right argument
			if node, ok := args[1].(ExprNode); ok && needsParenthesesForSubtraction(node) {
				right = "(" + right + ")"
			}

			switch format {
			case "unicode":
				return left + " − " + right
			case "latex":
				return left + " - " + right
			default:
				return left + " - " + right
			}
		}

	case "*":
		return formatMultiplication(args, format)

	case "/":
		return formatDivision(args, format)

	case "^":
		return formatExponentiation(args, format)

	case "D":
		return formatDerivative(args, node.Wrt, format)

	case "grad":
		return formatGradient(args, node.Dim, format)

	case "exp":
		arg := formatExpression(args[0], format)
		switch format {
		case "unicode":
			return "exp(" + arg + ")"
		case "latex":
			if shouldUseExpLeft(args[0]) {
				return "\\exp\\left(" + arg + "\\right)"
			}
			return "\\exp(" + arg + ")"
		default:
			return "exp(" + arg + ")"
		}

	case "ifelse":
		if len(args) >= 3 {
			condition := formatExpression(args[0], format)
			trueVal := formatExpression(args[1], format)
			falseVal := formatExpression(args[2], format)

			switch format {
			case "latex":
				return fmt.Sprintf("\\begin{cases} %s & \\text{if } %s \\\\ %s & \\text{otherwise} \\end{cases}",
					trueVal, condition, falseVal)
			default:
				return fmt.Sprintf("ifelse(%s, %s, %s)", condition, trueVal, falseVal)
			}
		}

	case "Pre":
		arg := formatExpression(args[0], format)
		switch format {
		case "latex":
			return "\\mathrm{Pre}(" + arg + ")"
		default:
			return "Pre(" + arg + ")"
		}

	// Comparison operators
	case ">", "<", ">=", "<=", "==", "!=":
		if len(args) >= 2 {
			left := formatExpression(args[0], format)
			right := formatExpression(args[1], format)
			return left + " " + op + " " + right
		}

	// Other functions
	default:
		if len(args) == 1 {
			arg := formatExpression(args[0], format)
			return op + "(" + arg + ")"
		} else if len(args) > 1 {
			argStrs := make([]string, len(args))
			for i, arg := range args {
				argStrs[i] = formatExpression(arg, format)
			}
			return op + "(" + strings.Join(argStrs, ", ") + ")"
		}
	}

	// Fallback
	return op + "(...)"
}

// Helper functions for specific formatting cases

func formatBinaryOp(op string, args []interface{}, format string, unicodeOp, latexOp, asciiOp string) string {
	if len(args) < 2 {
		return op + "(...)"
	}

	parts := make([]string, len(args))
	for i, arg := range args {
		parts[i] = formatExpression(arg, format)
	}

	switch format {
	case "unicode":
		return strings.Join(parts, " " + unicodeOp + " ")
	case "latex":
		return strings.Join(parts, latexOp)
	default:
		return strings.Join(parts, asciiOp)
	}
}

func formatMultiplication(args []interface{}, format string) string {
	if len(args) < 2 {
		return "*(...)"
	}

	parts := make([]string, len(args))
	for i, arg := range args {
		formatted := formatExpression(arg, format)

		// Add parentheses if needed for addition/subtraction terms
		if node, ok := arg.(ExprNode); ok {
			if node.Op == "+" || (node.Op == "-" && len(node.Args) == 2) {
				formatted = "(" + formatted + ")"
			}
		}

		parts[i] = formatted
	}

	switch format {
	case "unicode":
		return strings.Join(parts, "·")
	case "latex":
		return strings.Join(parts, " \\cdot ")
	default:
		return strings.Join(parts, " * ")
	}
}

func formatDivision(args []interface{}, format string) string {
	if len(args) != 2 {
		return "/(...)"
	}

	left := formatExpression(args[0], format)
	right := formatExpression(args[1], format)

	switch format {
	case "latex":
		return "\\frac{" + left + "}{" + right + "}"
	default:
		// Add parentheses if the right side is complex
		if node, ok := args[1].(ExprNode); ok {
			if node.Op == "+" || node.Op == "-" || node.Op == "*" || node.Op == "/" {
				right = "(" + right + ")"
			}
		}
		return left + "/" + right
	}
}

func formatExponentiation(args []interface{}, format string) string {
	if len(args) != 2 {
		return "^(...)"
	}

	base := formatExpression(args[0], format)
	exp := formatExpression(args[1], format)

	// Add parentheses to base if it's a complex expression
	if node, ok := args[0].(ExprNode); ok {
		if node.Op == "+" || node.Op == "-" || node.Op == "*" || node.Op == "/" {
			base = "(" + base + ")"
		}
	}

	switch format {
	case "unicode":
		if exp == "2" {
			return base + "²"
		} else if exp == "3" {
			return base + "³"
		} else if numExp, ok := args[1].(float64); ok {
			return base + formatSuperscript(int(numExp))
		}
		return base + "^" + exp
	case "latex":
		return base + "^{" + exp + "}"
	default:
		return base + "^" + exp
	}
}

// ToUnicodeSpaced converts an expression to Unicode string with spaced multiplication
// for better readability in model summary displays
func ToUnicodeSpaced(target interface{}) string {
	result := formatExpression(target, "unicode")
	// Replace "·" with " · " for better readability in model summaries
	return strings.ReplaceAll(result, "·", " · ")
}

// ModelSummary returns a structured model summary display showing all models,
// reaction systems, data loaders, coupling, domain, and solver as specified in Section 6.3
func ModelSummary(esm *EsmFile) string {
	result := strings.Builder{}

	// Header: ESM version and metadata
	result.WriteString(fmt.Sprintf("ESM v%s: %s\n", esm.Esm, esm.Metadata.Name))
	if esm.Metadata.Description != nil {
		result.WriteString(fmt.Sprintf("  \"%s\"\n", *esm.Metadata.Description))
	}
	if len(esm.Metadata.Authors) > 0 {
		result.WriteString(fmt.Sprintf("  Authors: %s\n", strings.Join(esm.Metadata.Authors, ", ")))
	}
	result.WriteString("\n")

	// Reaction Systems
	if len(esm.ReactionSystems) > 0 {
		result.WriteString("  Reaction Systems:\n")
		for name, rs := range esm.ReactionSystems {
			speciesCount := len(rs.Species)
			paramCount := len(rs.Parameters)
			reactionCount := len(rs.Reactions)
			result.WriteString(fmt.Sprintf("    %s (%d species, %d parameters, %d reactions)\n",
				name, speciesCount, paramCount, reactionCount))

			// Display reactions
			for _, reaction := range rs.Reactions {
				result.WriteString("      ")
				result.WriteString(reaction.ID)
				result.WriteString(": ")

				// Format substrates
				substrateNames := make([]string, len(reaction.Substrates))
				for i, substrate := range reaction.Substrates {
					if substrate.Stoichiometry == 1 {
						substrateNames[i] = ToUnicode(substrate.Species)
					} else {
						substrateNames[i] = fmt.Sprintf("%d%s", substrate.Stoichiometry, ToUnicode(substrate.Species))
					}
				}
				result.WriteString(strings.Join(substrateNames, " + "))

				result.WriteString(" → ")

				// Format products
				productNames := make([]string, len(reaction.Products))
				for i, product := range reaction.Products {
					if product.Stoichiometry == 1 {
						productNames[i] = ToUnicode(product.Species)
					} else {
						productNames[i] = fmt.Sprintf("%d%s", product.Stoichiometry, ToUnicode(product.Species))
					}
				}
				result.WriteString(strings.Join(productNames, " + "))

				// Format rate
				result.WriteString("    rate: ")
				result.WriteString(ToUnicodeSpaced(reaction.Rate))
				result.WriteString("\n")
			}
		}
		result.WriteString("\n")
	}

	// Models
	if len(esm.Models) > 0 {
		result.WriteString("  Models:\n")
		for name, model := range esm.Models {
			// Count parameters vs other variable types
			paramCount := 0
			for _, variable := range model.Variables {
				if variable.Type == "parameter" {
					paramCount++
				}
			}
			equationCount := len(model.Equations)
			result.WriteString(fmt.Sprintf("    %s (%d parameters, %d equation", name, paramCount, equationCount))
			if equationCount != 1 {
				result.WriteString("s")
			}
			result.WriteString(")\n")

			// Display equations
			for _, equation := range model.Equations {
				result.WriteString("      ")
				result.WriteString(ToUnicodeSpaced(equation.LHS))
				result.WriteString(" = ")
				result.WriteString(ToUnicodeSpaced(equation.RHS))
				result.WriteString("\n")
			}
		}
		result.WriteString("\n")
	}

	// Data Loaders
	if len(esm.DataLoaders) > 0 {
		result.WriteString("  Data Loaders:\n")
		for name, loader := range esm.DataLoaders {
			providedVars := make([]string, 0, len(loader.Provides))
			for varName := range loader.Provides {
				providedVars = append(providedVars, varName)
			}
			// Sort for deterministic output
			sort.Strings(providedVars)
			result.WriteString(fmt.Sprintf("    %s: %s (%s)\n", name,
				strings.Join(providedVars, ", "), loader.Type))
		}
		result.WriteString("\n")
	}

	// Coupling
	if len(esm.Coupling) > 0 {
		result.WriteString("  Coupling:\n")
		for i, coupling := range esm.Coupling {
			result.WriteString(fmt.Sprintf("    %d. ", i+1))

			// Type switch to handle different coupling types
			switch c := coupling.(type) {
			case OperatorComposeCoupling:
				result.WriteString(fmt.Sprintf("operator_compose: %s + %s", c.Systems[0], c.Systems[1]))
			case VariableMapCoupling:
				result.WriteString(fmt.Sprintf("variable_map: %s → %s", c.From, c.To))
			case Couple2Coupling:
				result.WriteString(fmt.Sprintf("couple2: %s ↔ %s", c.Systems[0], c.Systems[1]))
			case OperatorApplyCoupling:
				result.WriteString(fmt.Sprintf("operator_apply: %s", c.Operator))
			case CallbackCoupling:
				result.WriteString(fmt.Sprintf("callback: %s", c.CallbackID))
			case EventCoupling:
				result.WriteString(fmt.Sprintf("event: %s (%s)", c.Name, c.EventType))
			default:
				result.WriteString("unknown coupling type")
			}
			result.WriteString("\n")
		}
		result.WriteString("\n")
	}

	// Domain
	if esm.Domain != nil {
		result.WriteString("  Domain: ")
		parts := make([]string, 0)

		// Spatial dimensions
		if len(esm.Domain.Spatial) > 0 {
			for dimName, dim := range esm.Domain.Spatial {
				// Use minus signs for negative numbers and degree symbol for degrees
				minStr := formatNumber(dim.Min, "unicode")
				maxStr := formatNumber(dim.Max, "unicode")
				spacingStr := formatNumber(dim.GridSpacing, "unicode")

				unitStr := dim.Units
				if unitStr == "degrees" {
					unitStr = "°"
				}

				parts = append(parts, fmt.Sprintf("%s [%s, %s] (Δ%s%s)",
					dimName, minStr, maxStr, spacingStr, unitStr))
			}
		}

		// Temporal domain
		if esm.Domain.Temporal != nil {
			temporal := esm.Domain.Temporal
			// Extract just the date parts for brevity
			start := strings.Split(temporal.Start, "T")[0]
			end := strings.Split(temporal.End, "T")[0]
			parts = append(parts, fmt.Sprintf("%s to %s", start, end))
		}

		result.WriteString(strings.Join(parts, ", "))
		result.WriteString("\n")
	}

	// Solver
	if esm.Solver != nil {
		result.WriteString("  Solver: ")
		result.WriteString(esm.Solver.Strategy)

		if esm.Solver.Config != nil {
			configParts := make([]string, 0)

			// Handle specific known config keys with appropriate naming and order
			if stiffAlg, ok := esm.Solver.Config["stiff_algorithm"]; ok {
				configParts = append(configParts, fmt.Sprintf("%v", stiffAlg))
			}
			if timestep, ok := esm.Solver.Config["timestep"]; ok {
				configParts = append(configParts, fmt.Sprintf("dt=%v", timestep))
			}

			// Handle any other config keys
			for key, value := range esm.Solver.Config {
				if key != "stiff_algorithm" && key != "timestep" {
					configParts = append(configParts, fmt.Sprintf("%s=%v", key, value))
				}
			}
			if len(configParts) > 0 {
				result.WriteString(" (")
				result.WriteString(strings.Join(configParts, ", "))
				result.WriteString(")")
			}
		}
		result.WriteString("\n")
	}

	return strings.TrimSpace(result.String())
}

func formatDerivative(args []interface{}, wrt *string, format string) string {
	if len(args) != 1 || wrt == nil {
		return "D(...)"
	}

	variable := formatExpression(args[0], format)
	timeVar := *wrt

	switch format {
	case "unicode":
		return "∂" + variable + "/∂" + timeVar
	case "latex":
		formattedVar := formatExpression(args[0], format)
		return "\\frac{\\partial " + formattedVar + "}{\\partial " + timeVar + "}"
	default:
		return "D(" + variable + ")/D" + timeVar
	}
}

func formatGradient(args []interface{}, dim *string, format string) string {
	if len(args) != 1 || dim == nil {
		return "grad(...)"
	}

	variable := formatExpression(args[0], format)
	dimension := *dim

	switch format {
	case "unicode":
		return "∂" + variable + "/∂" + dimension
	case "latex":
		return "\\frac{\\partial " + variable + "}{\\partial " + dimension + "}"
	default:
		return "d(" + variable + ")/d" + dimension
	}
}

// Helper functions for specific formatting decisions

func needsParenthesesForSubtraction(node ExprNode) bool {
	return node.Op == "+" || (node.Op == "-" && len(node.Args) == 2)
}

func shouldUseExpLeft(arg interface{}) bool {
	// Use \left( \right) for complex expressions in exp()
	if node, ok := arg.(ExprNode); ok {
		return node.Op == "/" || node.Op == "+" || node.Op == "-"
	}
	return false
}