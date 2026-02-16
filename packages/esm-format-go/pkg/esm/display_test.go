package esm

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestToUnicodeBasic(t *testing.T) {
	tests := []struct {
		name     string
		input    interface{}
		expected string
	}{
		{
			name:     "simple number",
			input:    3.14,
			expected: "3.14",
		},
		{
			name:     "simple variable",
			input:    "x",
			expected: "x",
		},
		{
			name:     "chemical species",
			input:    "O3",
			expected: "O₃",
		},
		{
			name:     "scientific notation small",
			input:    1.8e-12,
			expected: "1.8×10⁻¹²",
		},
		{
			name:     "scientific notation large",
			input:    2.46e19,
			expected: "2.46×10¹⁹",
		},
		{
			name: "simple addition",
			input: ExprNode{
				Op:   "+",
				Args: []interface{}{"a", "b"},
			},
			expected: "a + b",
		},
		{
			name: "multiplication",
			input: ExprNode{
				Op:   "*",
				Args: []interface{}{"a", "b"},
			},
			expected: "a·b",
		},
		{
			name: "power of 2",
			input: ExprNode{
				Op:   "^",
				Args: []interface{}{"x", 2},
			},
			expected: "x²",
		},
		{
			name: "derivative",
			input: ExprNode{
				Op:   "D",
				Args: []interface{}{"O3"},
				Wrt:  strPtr("t"),
			},
			expected: "∂O₃/∂t",
		},
		{
			name: "gradient",
			input: ExprNode{
				Op:   "grad",
				Args: []interface{}{"x"},
				Dim:  strPtr("y"),
			},
			expected: "∂x/∂y",
		},
		{
			name: "unary minus",
			input: ExprNode{
				Op:   "-",
				Args: []interface{}{"x"},
			},
			expected: "−x",
		},
		{
			name: "binary subtraction",
			input: ExprNode{
				Op:   "-",
				Args: []interface{}{"a", "b"},
			},
			expected: "a − b",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ToUnicode(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestToLatexBasic(t *testing.T) {
	tests := []struct {
		name     string
		input    interface{}
		expected string
	}{
		{
			name:     "simple variable",
			input:    "x",
			expected: "x",
		},
		{
			name:     "chemical species",
			input:    "O3",
			expected: "\\mathrm{O_{3}}",
		},
		{
			name: "simple addition",
			input: ExprNode{
				Op:   "+",
				Args: []interface{}{"a", "b"},
			},
			expected: "a + b",
		},
		{
			name: "multiplication",
			input: ExprNode{
				Op:   "*",
				Args: []interface{}{"a", "b"},
			},
			expected: "a \\cdot b",
		},
		{
			name: "division",
			input: ExprNode{
				Op:   "/",
				Args: []interface{}{"a", "b"},
			},
			expected: "\\frac{a}{b}",
		},
		{
			name: "power",
			input: ExprNode{
				Op:   "^",
				Args: []interface{}{"x", 2},
			},
			expected: "x^{2}",
		},
		{
			name: "derivative",
			input: ExprNode{
				Op:   "D",
				Args: []interface{}{"O3"},
				Wrt:  strPtr("t"),
			},
			expected: "\\frac{\\partial \\mathrm{O_{3}}}{\\partial t}",
		},
		{
			name: "exponential simple",
			input: ExprNode{
				Op:   "exp",
				Args: []interface{}{"x"},
			},
			expected: "\\exp(x)",
		},
		{
			name: "exponential complex",
			input: ExprNode{
				Op: "exp",
				Args: []interface{}{
					ExprNode{
						Op:   "/",
						Args: []interface{}{-1370, "T"},
					},
				},
			},
			expected: "\\exp\\left(\\frac{-1370}{T}\\right)",
		},
		{
			name: "Pre function",
			input: ExprNode{
				Op:   "Pre",
				Args: []interface{}{"x"},
			},
			expected: "\\mathrm{Pre}(x)",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ToLatex(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestOperatorPrecedence(t *testing.T) {
	tests := []struct {
		name     string
		input    interface{}
		unicode  string
		latex    string
	}{
		{
			name: "addition with multiplication (no parens needed)",
			input: ExprNode{
				Op: "+",
				Args: []interface{}{
					ExprNode{Op: "*", Args: []interface{}{"a", "b"}},
					"c",
				},
			},
			unicode: "a·b + c",
			latex:   "a \\cdot b + c",
		},
		{
			name: "multiplication with addition (parens needed)",
			input: ExprNode{
				Op: "*",
				Args: []interface{}{
					ExprNode{Op: "+", Args: []interface{}{"a", "b"}},
					"c",
				},
			},
			unicode: "(a + b)·c",
			latex:   "(a + b) \\cdot c",
		},
		{
			name: "exponentiation with addition (parens needed for base)",
			input: ExprNode{
				Op: "^",
				Args: []interface{}{
					ExprNode{Op: "+", Args: []interface{}{"x", "y"}},
					2,
				},
			},
			unicode: "(x + y)²",
			latex:   "(x + y)^{2}",
		},
		{
			name: "complex expression",
			input: ExprNode{
				Op: "+",
				Args: []interface{}{
					ExprNode{Op: "^", Args: []interface{}{"x", 2}},
					ExprNode{Op: "*", Args: []interface{}{2, "x"}},
				},
			},
			unicode: "x² + 2·x",
			latex:   "x^{2} + 2 \\cdot x",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name+" unicode", func(t *testing.T) {
			result := ToUnicode(tt.input)
			assert.Equal(t, tt.unicode, result)
		})

		t.Run(tt.name+" latex", func(t *testing.T) {
			result := ToLatex(tt.input)
			assert.Equal(t, tt.latex, result)
		})
	}
}

func TestFormatChemicalSpecies(t *testing.T) {
	tests := []struct {
		species string
		unicode string
		latex   string
	}{
		{"O3", "O₃", "\\mathrm{O_{3}}"},
		{"NO2", "NO₂", "\\mathrm{NO_{2}}"},
		{"H2O", "H₂O", "\\mathrm{H_{2}O}"},
		{"CO2", "CO₂", "\\mathrm{CO_{2}}"},
		{"CH4", "CH₄", "\\mathrm{CH_{4}}"},
		{"SO4", "SO₄", "\\mathrm{SO_{4}}"},
	}

	for _, tt := range tests {
		t.Run("unicode "+tt.species, func(t *testing.T) {
			result := ToUnicode(tt.species)
			assert.Equal(t, tt.unicode, result)
		})

		t.Run("latex "+tt.species, func(t *testing.T) {
			result := ToLatex(tt.species)
			assert.Equal(t, tt.latex, result)
		})
	}
}

func TestIfElse(t *testing.T) {
	input := ExprNode{
		Op: "ifelse",
		Args: []interface{}{
			ExprNode{Op: ">", Args: []interface{}{"x", 0}},
			"x",
			0,
		},
	}

	unicode := ToUnicode(input)
	latex := ToLatex(input)

	assert.Equal(t, "ifelse(x > 0, x, 0)", unicode)
	assert.Equal(t, "\\begin{cases} x & \\text{if } x > 0 \\\\ 0 & \\text{otherwise} \\end{cases}", latex)
}

func TestComplexChemicalExpression(t *testing.T) {
	input := ExprNode{
		Op:   "*",
		Args: []interface{}{1.8e-12, "O3", "NO", "M"},
	}

	unicode := ToUnicode(input)
	latex := ToLatex(input)

	assert.Equal(t, "1.8×10⁻¹²·O₃·NO·M", unicode)
	assert.Equal(t, "1.8 \\times 10^{-12} \\cdot \\mathrm{O_{3}} \\cdot \\mathrm{NO} \\cdot M", latex)
}