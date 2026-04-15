package esm

import (
	"fmt"
	"math"
	"strconv"
	"strings"
	"unicode"
)

// Dimension is a vector of exponents over the 7 SI base units plus radian.
// Index order: m, kg, s, mol, K, A, cd, rad.
type Dimension [8]int8

const (
	dimLength = iota
	dimMass
	dimTime
	dimAmount
	dimTemperature
	dimCurrent
	dimLuminosity
	dimAngle
)

// Dimensionless is the zero vector.
var Dimensionless = Dimension{}

// Multiply adds component-wise exponents.
func (d Dimension) Multiply(other Dimension) Dimension {
	var r Dimension
	for i := range d {
		r[i] = d[i] + other[i]
	}
	return r
}

// Divide subtracts component-wise exponents.
func (d Dimension) Divide(other Dimension) Dimension {
	var r Dimension
	for i := range d {
		r[i] = d[i] - other[i]
	}
	return r
}

// Power scales each exponent by n.
func (d Dimension) Power(n int) Dimension {
	var r Dimension
	for i := range d {
		r[i] = int8(int(d[i]) * n)
	}
	return r
}

// Equal reports whether two dimensions are identical.
func (d Dimension) Equal(other Dimension) bool {
	return d == other
}

// IsDimensionless reports whether every exponent is zero.
func (d Dimension) IsDimensionless() bool {
	return d == Dimensionless
}

// String renders a dimension vector in SI-base notation (e.g. "m*kg/s^2").
func (d Dimension) String() string {
	if d.IsDimensionless() {
		return "1"
	}
	symbols := [8]string{"m", "kg", "s", "mol", "K", "A", "cd", "rad"}
	var num, den []string
	for i, e := range d {
		switch {
		case e > 0:
			if e == 1 {
				num = append(num, symbols[i])
			} else {
				num = append(num, fmt.Sprintf("%s^%d", symbols[i], e))
			}
		case e < 0:
			if e == -1 {
				den = append(den, symbols[i])
			} else {
				den = append(den, fmt.Sprintf("%s^%d", symbols[i], -e))
			}
		}
	}
	var sb strings.Builder
	if len(num) == 0 {
		sb.WriteString("1")
	} else {
		sb.WriteString(strings.Join(num, "*"))
	}
	if len(den) > 0 {
		sb.WriteString("/")
		sb.WriteString(strings.Join(den, "/"))
	}
	return sb.String()
}

// Unit is a named physical unit with a dimension vector and a scale factor
// relative to the canonical SI combination represented by Dim.
type Unit struct {
	Dim    Dimension
	Scale  float64
	Symbol string
}

// Multiply returns the product of two units (dimensions add, scales multiply).
func (u Unit) Multiply(other Unit) Unit {
	return Unit{Dim: u.Dim.Multiply(other.Dim), Scale: u.Scale * other.Scale}
}

// Divide returns the quotient of two units.
func (u Unit) Divide(other Unit) Unit {
	return Unit{Dim: u.Dim.Divide(other.Dim), Scale: u.Scale / other.Scale}
}

// Power raises a unit to an integer power.
func (u Unit) Power(n int) Unit {
	return Unit{Dim: u.Dim.Power(n), Scale: math.Pow(u.Scale, float64(n))}
}

// baseUnit constructs a single-dimension unit with an explicit scale.
func baseUnit(idx int, scale float64) Unit {
	var d Dimension
	d[idx] = 1
	return Unit{Dim: d, Scale: scale}
}

// unitRegistry holds all symbols recognized by ParseUnit.
var unitRegistry = buildUnitRegistry()

func buildUnitRegistry() map[string]Unit {
	r := map[string]Unit{}

	// SI base units (scale 1).
	r["m"] = baseUnit(dimLength, 1.0)
	r["kg"] = baseUnit(dimMass, 1.0)
	r["s"] = baseUnit(dimTime, 1.0)
	r["mol"] = baseUnit(dimAmount, 1.0)
	r["K"] = baseUnit(dimTemperature, 1.0)
	r["A"] = baseUnit(dimCurrent, 1.0)
	r["cd"] = baseUnit(dimLuminosity, 1.0)
	r["rad"] = baseUnit(dimAngle, 1.0)

	// Mass (gram, because kg is the SI base but g/mg/ug are common).
	r["g"] = Unit{Dim: r["kg"].Dim, Scale: 1e-3}
	r["mg"] = Unit{Dim: r["kg"].Dim, Scale: 1e-6}
	r["ug"] = Unit{Dim: r["kg"].Dim, Scale: 1e-9}

	// Length scales.
	r["cm"] = Unit{Dim: r["m"].Dim, Scale: 1e-2}
	r["mm"] = Unit{Dim: r["m"].Dim, Scale: 1e-3}
	r["um"] = Unit{Dim: r["m"].Dim, Scale: 1e-6}
	r["nm"] = Unit{Dim: r["m"].Dim, Scale: 1e-9}
	r["km"] = Unit{Dim: r["m"].Dim, Scale: 1e3}

	// Time scales.
	r["ms"] = Unit{Dim: r["s"].Dim, Scale: 1e-3}
	r["us"] = Unit{Dim: r["s"].Dim, Scale: 1e-6}
	r["ns"] = Unit{Dim: r["s"].Dim, Scale: 1e-9}
	r["min"] = Unit{Dim: r["s"].Dim, Scale: 60}
	r["h"] = Unit{Dim: r["s"].Dim, Scale: 3600}
	r["hr"] = Unit{Dim: r["s"].Dim, Scale: 3600}
	r["day"] = Unit{Dim: r["s"].Dim, Scale: 86400}
	r["yr"] = Unit{Dim: r["s"].Dim, Scale: 365.25 * 86400}

	// Volume (derived length^3 shortcut).
	liter := Unit{Dim: r["m"].Dim.Power(3), Scale: 1e-3}
	r["L"] = liter
	r["l"] = liter
	r["mL"] = Unit{Dim: liter.Dim, Scale: 1e-6}

	// Temperature (Celsius shares the Kelvin dimension; offset is not modeled).
	r["degC"] = r["K"]
	r["C"] = r["K"] // NOTE: overloaded with coulomb below if needed — coulomb disabled

	// Derived coherent SI units (scale 1 except where noted).
	r["Hz"] = Unit{Dim: r["s"].Dim.Power(-1), Scale: 1}
	r["N"] = r["kg"].Multiply(r["m"]).Divide(r["s"].Power(2))
	r["Pa"] = r["N"].Divide(r["m"].Power(2))
	r["J"] = r["N"].Multiply(r["m"])
	r["W"] = r["J"].Divide(r["s"])

	// Concentration-ish.
	r["M"] = r["mol"].Divide(liter) // molarity

	// ESM / atmospheric chemistry units.
	// mol/mol, ppm, ppb, ppt are dimensionless mixing ratios; the scale is the
	// multiplier relative to 1 (mol/mol).
	r["ppm"] = Unit{Dim: Dimensionless, Scale: 1e-6}
	r["ppb"] = Unit{Dim: Dimensionless, Scale: 1e-9}
	r["ppt"] = Unit{Dim: Dimensionless, Scale: 1e-12}
	// "molec" is a count of molecules. ESM models treat it as dimensionless so
	// that e.g. "molec/cm^3" matches "1/cm^3" — avogadro folds into the scale.
	r["molec"] = Unit{Dim: Dimensionless, Scale: 1}
	// Dobson unit: 2.69e16 molec/cm^2 → dimension is length^-2.
	r["Dobson"] = Unit{Dim: r["m"].Dim.Power(-2), Scale: 2.69e20} // 2.69e16 * (1/cm^2 → 1/m^2 ×1e4)
	r["DU"] = r["Dobson"]

	return r
}

// ParseUnit parses a unit string into a Unit. Grammar:
//
//	unit    := term ( ('*'|'/') term )*
//	term    := atom ( '^' integer )?
//	atom    := number | symbol | '(' unit ')' | '1'
//
// Whitespace is ignored. Division is left-associative: "a/b/c" == "a/(b*c)".
// Examples that must parse:
//
//	"m", "m/s", "m/s^2", "kg*m^2/s^3", "cm^3/molec/s", "mol/mol",
//	"1/s", "Pa", "J/(mol*K)", "".
func ParseUnit(s string) (Unit, error) {
	s = strings.TrimSpace(s)
	if s == "" || s == "1" || s == "dimensionless" {
		return Unit{Scale: 1}, nil
	}
	p := &unitParser{src: s}
	u, err := p.parseUnit()
	if err != nil {
		return Unit{}, fmt.Errorf("parse %q: %w", s, err)
	}
	if p.pos != len(p.src) {
		return Unit{}, fmt.Errorf("parse %q: unexpected %q at position %d", s, s[p.pos:], p.pos)
	}
	u.Symbol = s
	return u, nil
}

type unitParser struct {
	src string
	pos int
}

func (p *unitParser) skipSpace() {
	for p.pos < len(p.src) && unicode.IsSpace(rune(p.src[p.pos])) {
		p.pos++
	}
}

func (p *unitParser) peek() byte {
	p.skipSpace()
	if p.pos >= len(p.src) {
		return 0
	}
	return p.src[p.pos]
}

func (p *unitParser) parseUnit() (Unit, error) {
	u, err := p.parseTerm()
	if err != nil {
		return Unit{}, err
	}
	for {
		c := p.peek()
		if c != '*' && c != '/' {
			break
		}
		p.pos++
		next, err := p.parseTerm()
		if err != nil {
			return Unit{}, err
		}
		if c == '*' {
			u = u.Multiply(next)
		} else {
			u = u.Divide(next)
		}
	}
	return u, nil
}

func (p *unitParser) parseTerm() (Unit, error) {
	u, err := p.parseAtom()
	if err != nil {
		return Unit{}, err
	}
	if p.peek() == '^' {
		p.pos++
		exp, err := p.parseInt()
		if err != nil {
			return Unit{}, err
		}
		u = u.Power(exp)
	}
	return u, nil
}

func (p *unitParser) parseAtom() (Unit, error) {
	p.skipSpace()
	if p.pos >= len(p.src) {
		return Unit{}, fmt.Errorf("unexpected end of input")
	}
	c := p.src[p.pos]
	if c == '(' {
		p.pos++
		u, err := p.parseUnit()
		if err != nil {
			return Unit{}, err
		}
		if p.peek() != ')' {
			return Unit{}, fmt.Errorf("missing ')'")
		}
		p.pos++
		return u, nil
	}
	// Bare integer "1" is dimensionless; any other bare number is a scalar factor.
	if c >= '0' && c <= '9' {
		start := p.pos
		for p.pos < len(p.src) && ((p.src[p.pos] >= '0' && p.src[p.pos] <= '9') || p.src[p.pos] == '.') {
			p.pos++
		}
		val, err := strconv.ParseFloat(p.src[start:p.pos], 64)
		if err != nil {
			return Unit{}, fmt.Errorf("invalid number %q", p.src[start:p.pos])
		}
		return Unit{Scale: val}, nil
	}
	// Identifier: letters followed by letters/digits/underscore.
	if !isIdentStart(c) {
		return Unit{}, fmt.Errorf("unexpected %q at position %d", c, p.pos)
	}
	start := p.pos
	p.pos++
	for p.pos < len(p.src) && isIdentCont(p.src[p.pos]) {
		p.pos++
	}
	sym := p.src[start:p.pos]
	u, ok := unitRegistry[sym]
	if !ok {
		return Unit{}, fmt.Errorf("unknown unit %q", sym)
	}
	return u, nil
}

func (p *unitParser) parseInt() (int, error) {
	p.skipSpace()
	start := p.pos
	if p.pos < len(p.src) && (p.src[p.pos] == '-' || p.src[p.pos] == '+') {
		p.pos++
	}
	for p.pos < len(p.src) && p.src[p.pos] >= '0' && p.src[p.pos] <= '9' {
		p.pos++
	}
	if start == p.pos || (p.pos-start == 1 && (p.src[start] == '-' || p.src[start] == '+')) {
		return 0, fmt.Errorf("expected integer exponent at position %d", start)
	}
	n, err := strconv.Atoi(p.src[start:p.pos])
	if err != nil {
		return 0, err
	}
	return n, nil
}

func isIdentStart(c byte) bool {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_'
}

func isIdentCont(c byte) bool {
	return isIdentStart(c) || (c >= '0' && c <= '9')
}

// PropagateDimension walks an Expression AST and returns the resulting Unit.
// It mirrors the Julia reference implementation (get_expression_dimensions):
//
//   - numeric literals → dimensionless
//   - variable names → looked up in env; unknown variables return nil, nil
//     (dimensional analysis is best-effort when unit annotations are missing)
//   - "+", "-" require all operands to share a dimension
//   - "*" multiplies dimensions, "/" divides
//   - "^" requires a dimensionless constant exponent
//   - transcendental functions (sin/cos/tan/exp/log/ln/sqrt) require a
//     dimensionless argument and return dimensionless
//   - "D" (derivative) divides by the wrt variable's unit (default "t")
//
// A non-nil error signals a dimensional inconsistency discovered during
// propagation. The caller decides whether to turn that into a UnitWarning.
func PropagateDimension(expr Expression, env map[string]Unit) (*Unit, error) {
	switch e := expr.(type) {
	case nil:
		return nil, nil
	case float64, int, int32, int64, float32:
		u := Unit{Scale: 1}
		return &u, nil
	case string:
		if u, ok := env[e]; ok {
			cp := u
			return &cp, nil
		}
		return nil, nil
	case ExprNode:
		return propagateExprNode(e, env)
	case *ExprNode:
		return propagateExprNode(*e, env)
	default:
		return nil, nil
	}
}

func propagateExprNode(node ExprNode, env map[string]Unit) (*Unit, error) {
	switch node.Op {
	case "+", "-":
		// Unary minus: propagate its single operand.
		if node.Op == "-" && len(node.Args) == 1 {
			return PropagateDimension(node.Args[0], env)
		}
		var first *Unit
		for i, arg := range node.Args {
			u, err := PropagateDimension(arg, env)
			if err != nil {
				return nil, err
			}
			if u == nil {
				continue
			}
			if first == nil {
				first = u
				continue
			}
			if !first.Dim.Equal(u.Dim) {
				return nil, fmt.Errorf("dimensional mismatch in %q: arg 0 has %s, arg %d has %s",
					node.Op, first.Dim, i, u.Dim)
			}
		}
		return first, nil

	case "*":
		result := Unit{Scale: 1}
		anyKnown := false
		for _, arg := range node.Args {
			u, err := PropagateDimension(arg, env)
			if err != nil {
				return nil, err
			}
			if u == nil {
				continue
			}
			result = result.Multiply(*u)
			anyKnown = true
		}
		if !anyKnown {
			return nil, nil
		}
		return &result, nil

	case "/":
		if len(node.Args) != 2 {
			return nil, fmt.Errorf("'/' requires exactly 2 arguments, got %d", len(node.Args))
		}
		num, err := PropagateDimension(node.Args[0], env)
		if err != nil {
			return nil, err
		}
		den, err := PropagateDimension(node.Args[1], env)
		if err != nil {
			return nil, err
		}
		if num == nil || den == nil {
			return nil, nil
		}
		r := num.Divide(*den)
		return &r, nil

	case "^", "**", "pow":
		if len(node.Args) != 2 {
			return nil, fmt.Errorf("'%s' requires exactly 2 arguments, got %d", node.Op, len(node.Args))
		}
		base, err := PropagateDimension(node.Args[0], env)
		if err != nil {
			return nil, err
		}
		expDim, err := PropagateDimension(node.Args[1], env)
		if err != nil {
			return nil, err
		}
		if expDim != nil && !expDim.Dim.IsDimensionless() {
			return nil, fmt.Errorf("exponent in '%s' must be dimensionless, got %s", node.Op, expDim.Dim)
		}
		if base == nil {
			return nil, nil
		}
		expVal, ok := toFloat64(node.Args[1])
		if !ok {
			// Non-constant exponent: cannot compute integer power; assume base dim.
			cp := *base
			return &cp, nil
		}
		if expVal != math.Trunc(expVal) {
			return nil, fmt.Errorf("non-integer exponent %v in '%s' not supported for dimensional analysis", expVal, node.Op)
		}
		r := base.Power(int(expVal))
		return &r, nil

	case "sin", "cos", "tan", "asin", "acos", "atan", "exp", "log", "log10", "ln", "sqrt":
		if node.Op == "sqrt" {
			if len(node.Args) != 1 {
				return nil, fmt.Errorf("sqrt requires 1 argument, got %d", len(node.Args))
			}
			base, err := PropagateDimension(node.Args[0], env)
			if err != nil {
				return nil, err
			}
			if base == nil {
				return nil, nil
			}
			// sqrt halves exponents — require each to be even.
			var r Dimension
			for i, e := range base.Dim {
				if e%2 != 0 {
					return nil, fmt.Errorf("sqrt of non-square dimension %s", base.Dim)
				}
				r[i] = e / 2
			}
			return &Unit{Dim: r, Scale: math.Sqrt(base.Scale)}, nil
		}
		if len(node.Args) != 1 {
			return nil, fmt.Errorf("'%s' requires 1 argument, got %d", node.Op, len(node.Args))
		}
		arg, err := PropagateDimension(node.Args[0], env)
		if err != nil {
			return nil, err
		}
		if arg != nil && !arg.Dim.IsDimensionless() {
			return nil, fmt.Errorf("argument of '%s' must be dimensionless, got %s", node.Op, arg.Dim)
		}
		return &Unit{Scale: 1}, nil

	case "abs", "sign":
		if len(node.Args) != 1 {
			return nil, fmt.Errorf("'%s' requires 1 argument, got %d", node.Op, len(node.Args))
		}
		return PropagateDimension(node.Args[0], env)

	case "D":
		if len(node.Args) != 1 {
			return nil, fmt.Errorf("'D' requires 1 argument, got %d", len(node.Args))
		}
		varDim, err := PropagateDimension(node.Args[0], env)
		if err != nil {
			return nil, err
		}
		wrt := "t"
		if node.Wrt != nil {
			wrt = *node.Wrt
		}
		wrtUnit, ok := env[wrt]
		if !ok {
			// Default: time in seconds.
			wrtUnit = unitRegistry["s"]
		}
		if varDim == nil {
			return nil, nil
		}
		r := varDim.Divide(wrtUnit)
		return &r, nil

	case "min", "max":
		// Return dimension of first operand; require others to match.
		var first *Unit
		for i, arg := range node.Args {
			u, err := PropagateDimension(arg, env)
			if err != nil {
				return nil, err
			}
			if u == nil {
				continue
			}
			if first == nil {
				first = u
				continue
			}
			if !first.Dim.Equal(u.Dim) {
				return nil, fmt.Errorf("dimensional mismatch in %q: arg 0 has %s, arg %d has %s",
					node.Op, first.Dim, i, u.Dim)
			}
		}
		return first, nil
	}
	// Unknown operator: propagate nothing rather than erroring, matching the
	// Julia reference which warns and returns nothing.
	return nil, nil
}

// BuildUnitEnv converts a map of name→unit-string into a map of name→Unit,
// silently skipping entries whose unit string fails to parse. The skipped
// entries are returned so callers can emit warnings.
func BuildUnitEnv(raw map[string]string) (map[string]Unit, map[string]error) {
	env := make(map[string]Unit, len(raw))
	bad := map[string]error{}
	for name, s := range raw {
		if s == "" {
			continue
		}
		u, err := ParseUnit(s)
		if err != nil {
			bad[name] = err
			continue
		}
		env[name] = u
	}
	return env, bad
}

// ValidateEquationDimensions checks that the LHS and RHS of an equation have
// the same dimension. It returns a non-nil UnitWarning iff a concrete
// inconsistency was detected. Missing annotations are treated as "unknown" and
// do NOT produce a warning (matching the Python/Julia best-effort semantics).
func ValidateEquationDimensions(eq *Equation, env map[string]Unit, path string) *UnitWarning {
	lhs, lhsErr := PropagateDimension(eq.LHS, env)
	rhs, rhsErr := PropagateDimension(eq.RHS, env)

	if lhsErr != nil {
		return &UnitWarning{
			Path:     path + ".lhs",
			Message:  "dimensional analysis failed on LHS: " + lhsErr.Error(),
			LhsUnits: "error",
			RhsUnits: dimString(rhs),
		}
	}
	if rhsErr != nil {
		return &UnitWarning{
			Path:     path + ".rhs",
			Message:  "dimensional analysis failed on RHS: " + rhsErr.Error(),
			LhsUnits: dimString(lhs),
			RhsUnits: "error",
		}
	}
	if lhs == nil || rhs == nil {
		return nil
	}
	if !lhs.Dim.Equal(rhs.Dim) {
		return &UnitWarning{
			Path:     path,
			Message:  fmt.Sprintf("LHS dimension %s does not match RHS dimension %s", lhs.Dim, rhs.Dim),
			LhsUnits: lhs.Dim.String(),
			RhsUnits: rhs.Dim.String(),
		}
	}
	return nil
}

func dimString(u *Unit) string {
	if u == nil {
		return "unknown"
	}
	return u.Dim.String()
}

// ValidateModelUnits runs dimensional analysis over every equation in a model
// and appends any warnings it finds to the result.
func validateModelUnits(modelName string, model *Model, basePath string, result *StructuralValidationResult) {
	raw := make(map[string]string, len(model.Variables))
	for name, v := range model.Variables {
		if v.Units != nil {
			raw[name] = *v.Units
		}
	}
	env, bad := BuildUnitEnv(raw)
	for name, err := range bad {
		result.UnitWarnings = append(result.UnitWarnings, UnitWarning{
			Path:    fmt.Sprintf("%s.variables.%s.units", basePath, name),
			Message: fmt.Sprintf("could not parse unit: %v", err),
		})
	}
	for i, eq := range model.Equations {
		eqPath := fmt.Sprintf("%s.equations[%d]", basePath, i)
		if w := ValidateEquationDimensions(&eq, env, eqPath); w != nil {
			result.UnitWarnings = append(result.UnitWarnings, *w)
		}
	}
}

// validateReactionSystemUnits runs dimensional analysis over a reaction
// system. Rate expressions whose dimensions cannot be determined are skipped;
// rate expressions that surface a concrete inconsistency produce a warning.
func validateReactionSystemUnits(systemName string, system *ReactionSystem, basePath string, result *StructuralValidationResult) {
	raw := make(map[string]string)
	for name, sp := range system.Species {
		if sp.Units != nil {
			raw[name] = *sp.Units
		}
	}
	for name, p := range system.Parameters {
		if p.Units != nil {
			raw[name] = *p.Units
		}
	}
	env, bad := BuildUnitEnv(raw)
	for name, err := range bad {
		result.UnitWarnings = append(result.UnitWarnings, UnitWarning{
			Path:    fmt.Sprintf("%s.%s.units", basePath, name),
			Message: fmt.Sprintf("could not parse unit: %v", err),
		})
	}
	for i, rx := range system.Reactions {
		rxPath := fmt.Sprintf("%s.reactions[%d].rate", basePath, i)
		if _, err := PropagateDimension(rx.Rate, env); err != nil {
			result.UnitWarnings = append(result.UnitWarnings, UnitWarning{
				Path:    rxPath,
				Message: "dimensional analysis failed: " + err.Error(),
			})
		}
	}
	for i, eq := range system.ConstraintEquations {
		eqPath := fmt.Sprintf("%s.constraint_equations[%d]", basePath, i)
		if w := ValidateEquationDimensions(&eq, env, eqPath); w != nil {
			result.UnitWarnings = append(result.UnitWarnings, *w)
		}
	}
}
