package esm

import (
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// ESMFile represents the main ESM file structure
type ESMFile struct {
	Version string `json:"version" validate:"required"`
	Model   Model  `json:"model" validate:"required"`
}

// Model represents an ESM model
type Model struct {
	Name        string       `json:"name" validate:"required"`
	Description string       `json:"description,omitempty"`
	Expressions []Expression `json:"expressions"`
	Solvers     []Solver     `json:"solvers,omitempty"`
}

// Expression represents a mathematical expression
type Expression struct {
	Name        string                 `json:"name" validate:"required"`
	Expression  string                 `json:"expression" validate:"required"`
	Variables   map[string]Variable    `json:"variables,omitempty"`
	Parameters  map[string]Parameter   `json:"parameters,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// Variable represents a model variable
type Variable struct {
	Name        string                 `json:"name" validate:"required"`
	Units       string                 `json:"units,omitempty"`
	Description string                 `json:"description,omitempty"`
	InitialValue float64               `json:"initial_value,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// Parameter represents a model parameter
type Parameter struct {
	Name        string                 `json:"name" validate:"required"`
	Value       float64                `json:"value" validate:"required"`
	Units       string                 `json:"units,omitempty"`
	Description string                 `json:"description,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// Solver represents a solver configuration
type Solver struct {
	Name        string                 `json:"name" validate:"required"`
	Strategy    string                 `json:"strategy" validate:"required"`
	Config      map[string]interface{} `json:"config,omitempty"`
}

// Validate validates the ESM file structure
func (e *ESMFile) Validate() error {
	validate := validator.New()
	return validate.Struct(e)
}

// ToJSON converts the ESM file to JSON
func (e *ESMFile) ToJSON() ([]byte, error) {
	return json.MarshalIndent(e, "", "  ")
}

// FromJSON creates an ESM file from JSON data
func FromJSON(data []byte) (*ESMFile, error) {
	var esm ESMFile
	if err := json.Unmarshal(data, &esm); err != nil {
		return nil, fmt.Errorf("failed to unmarshal JSON: %w", err)
	}

	if err := esm.Validate(); err != nil {
		return nil, fmt.Errorf("validation failed: %w", err)
	}

	return &esm, nil
}