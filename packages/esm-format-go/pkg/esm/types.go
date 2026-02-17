package esm

import (
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// ========================================
// 1. Expression Types
// ========================================

// ExprNode represents an operator node in the expression tree
type ExprNode struct {
	Op   string        `json:"op"`
	Args []interface{} `json:"args"`
	Wrt  *string       `json:"wrt,omitempty"`  // for derivatives
	Dim  *string       `json:"dim,omitempty"`  // for grad
}

// Expression represents the union type: number | string | ExprNode
// In Go, this is handled by using interface{} and custom unmarshaling
type Expression interface{}

// Equation represents a mathematical equation with LHS and RHS
type Equation struct {
	LHS Expression `json:"lhs"`
	RHS Expression `json:"rhs"`
}

// AffectEquation represents an equation that affects a variable (for events)
type AffectEquation struct {
	LHS string     `json:"lhs"` // variable name
	RHS Expression `json:"rhs"` // expression
}

// ========================================
// 2. Model Components
// ========================================

// ModelVariable represents a variable in a mathematical model
type ModelVariable struct {
	Type        string      `json:"type"` // "state", "parameter", or "observed"
	Units       *string     `json:"units,omitempty"`
	Default     interface{} `json:"default,omitempty"`
	Description *string     `json:"description,omitempty"`
	Expression  Expression  `json:"expression,omitempty"` // for observed variables
}

// Model represents an ODE system
type Model struct {
	CoupleType        *string                   `json:"coupletype,omitempty"`
	Reference         *Reference                `json:"reference,omitempty"`
	Variables         map[string]ModelVariable  `json:"variables"`
	Equations         []Equation                `json:"equations"`
	DiscreteEvents    []DiscreteEvent           `json:"discrete_events,omitempty"`
	ContinuousEvents  []ContinuousEvent         `json:"continuous_events,omitempty"`
	Subsystems        map[string]interface{}    `json:"subsystems,omitempty"`
}

// ========================================
// 3. Reaction System Components
// ========================================

// Species represents a chemical species
type Species struct {
	Units       *string `json:"units,omitempty"`
	Default     interface{} `json:"default,omitempty"`
	Description *string `json:"description,omitempty"`
}

// Parameter represents a model parameter
type Parameter struct {
	Units       *string `json:"units,omitempty"`
	Default     interface{} `json:"default,omitempty"`
	Description *string `json:"description,omitempty"`
}

// SubstrateProduct represents a substrate or product in a reaction
type SubstrateProduct struct {
	Species       string `json:"species"`
	Stoichiometry int    `json:"stoichiometry"`
}

// Reaction represents a chemical reaction
type Reaction struct {
	ID         string             `json:"id"`
	Name       *string            `json:"name,omitempty"`
	Substrates []SubstrateProduct `json:"substrates"`
	Products   []SubstrateProduct `json:"products"`
	Rate       Expression         `json:"rate"`
	Reference  *Reference         `json:"reference,omitempty"`
}

// ReactionSystem represents a chemical reaction network
type ReactionSystem struct {
	CoupleType          *string                   `json:"coupletype,omitempty"`
	Reference           *Reference                `json:"reference,omitempty"`
	Species             map[string]Species        `json:"species"`
	Parameters          map[string]Parameter      `json:"parameters"`
	Reactions           []Reaction                `json:"reactions"`
	ConstraintEquations []Equation                `json:"constraint_equations,omitempty"`
	DiscreteEvents      []DiscreteEvent           `json:"discrete_events,omitempty"`
	ContinuousEvents    []ContinuousEvent         `json:"continuous_events,omitempty"`
	Subsystems          map[string]interface{}    `json:"subsystems,omitempty"`
}

// ========================================
// 4. Events
// ========================================

// DiscreteEventTrigger represents different trigger types for discrete events
type DiscreteEventTrigger struct {
	Type          string      `json:"type"` // "condition", "periodic", "preset_times"
	Expression    Expression  `json:"expression,omitempty"`    // for condition
	Interval      *float64    `json:"interval,omitempty"`      // for periodic
	InitialOffset *float64    `json:"initial_offset,omitempty"` // for periodic
	Times         []float64   `json:"times,omitempty"`         // for preset_times
}

// DiscreteEvent represents a discrete event
type DiscreteEvent struct {
	Name                string                `json:"name,omitempty"`
	Trigger             DiscreteEventTrigger  `json:"trigger"`
	Affects             []AffectEquation      `json:"affects"`
	DiscreteParameters  []string              `json:"discrete_parameters,omitempty"`
	Reinitialize        *bool                 `json:"reinitialize,omitempty"`
	Description         *string               `json:"description,omitempty"`
}

// ContinuousEvent represents a continuous event
type ContinuousEvent struct {
	Name         *string          `json:"name,omitempty"`
	Conditions   []Expression     `json:"conditions"`
	Affects      []AffectEquation `json:"affects"`
	AffectNeg    []AffectEquation `json:"affect_neg,omitempty"`
	RootFind     *string          `json:"root_find,omitempty"` // "left", "right", "all"
	Reinitialize *bool            `json:"reinitialize,omitempty"`
	Description  *string          `json:"description,omitempty"`
}

// ========================================
// 5. Data Loaders and Operators
// ========================================

// DataLoader represents an external data source
type DataLoader struct {
	Type                string                 `json:"type"` // "gridded_data", "emissions", etc.
	LoaderID            string                 `json:"loader_id"`
	Config              map[string]interface{} `json:"config,omitempty"`
	Reference           *Reference             `json:"reference,omitempty"`
	Provides            map[string]ProvidedVar `json:"provides"`
	TemporalResolution  *string                `json:"temporal_resolution,omitempty"`
	SpatialResolution   map[string]float64     `json:"spatial_resolution,omitempty"`
	Interpolation       *string                `json:"interpolation,omitempty"`
}

// ProvidedVar represents a variable provided by a data loader
type ProvidedVar struct {
	Units       string  `json:"units"`
	Description *string `json:"description,omitempty"`
}

// Operator represents a runtime-specific operator
type Operator struct {
	OperatorID  string                 `json:"operator_id"`
	Reference   *Reference             `json:"reference,omitempty"`
	Config      map[string]interface{} `json:"config,omitempty"`
	NeededVars  []string               `json:"needed_vars"`
	Modifies    []string               `json:"modifies,omitempty"`
	Description *string                `json:"description,omitempty"`
}

// ========================================
// 6. Coupling
// ========================================

// CouplingEntry represents different types of coupling rules
// This is a discriminated union based on the "type" field
type CouplingEntry interface {
	GetType() string
}

// OperatorComposeCoupling represents operator composition
type OperatorComposeCoupling struct {
	Type        string                       `json:"type"` // "operator_compose"
	Systems     [2]string                    `json:"systems"`
	Translate   map[string]interface{}       `json:"translate,omitempty"`
	Description *string                      `json:"description,omitempty"`
}

func (o OperatorComposeCoupling) GetType() string { return o.Type }

// Couple2Coupling represents couple2-style coupling
type Couple2Coupling struct {
	Type           string                 `json:"type"` // "couple2"
	Systems        [2]string              `json:"systems"`
	CoupleTypePair [2]string              `json:"coupletype_pair"`
	Connector      Connector              `json:"connector"`
	Description    *string                `json:"description,omitempty"`
}

func (c Couple2Coupling) GetType() string { return c.Type }

// VariableMapCoupling represents variable mapping
type VariableMapCoupling struct {
	Type        string   `json:"type"` // "variable_map"
	From        string   `json:"from"`
	To          string   `json:"to"`
	Transform   string   `json:"transform"`
	Factor      *float64 `json:"factor,omitempty"`
	Description *string  `json:"description,omitempty"`
}

func (v VariableMapCoupling) GetType() string { return v.Type }

// OperatorApplyCoupling represents operator application
type OperatorApplyCoupling struct {
	Type        string  `json:"type"` // "operator_apply"
	Operator    string  `json:"operator"`
	Description *string `json:"description,omitempty"`
}

func (o OperatorApplyCoupling) GetType() string { return o.Type }

// Connector represents the connector system for couple2
type Connector struct {
	Equations []ConnectorEquation `json:"equations"`
}

// ConnectorEquation represents a single equation in a connector
type ConnectorEquation struct {
	From       string     `json:"from"`
	To         string     `json:"to"`
	Transform  string     `json:"transform"` // "additive", "multiplicative", "replacement"
	Expression Expression `json:"expression"`
}

// ========================================
// 7. Domain and Solver
// ========================================

// Domain represents the spatiotemporal domain
type Domain struct {
	IndependentVariable   *string                      `json:"independent_variable,omitempty"`
	Temporal              *TemporalDomain              `json:"temporal,omitempty"`
	Spatial               map[string]SpatialDimension  `json:"spatial,omitempty"`
	CoordinateTransforms  []CoordinateTransform        `json:"coordinate_transforms,omitempty"`
	SpatialRef            *string                      `json:"spatial_ref,omitempty"`
	InitialConditions     InitialConditions            `json:"initial_conditions,omitempty"`
	BoundaryConditions    []BoundaryCondition          `json:"boundary_conditions,omitempty"`
	ElementType           *string                      `json:"element_type,omitempty"`
	ArrayType             *string                      `json:"array_type,omitempty"`
}

// TemporalDomain represents temporal bounds
type TemporalDomain struct {
	Start         string  `json:"start"`
	End           string  `json:"end"`
	ReferenceTime *string `json:"reference_time,omitempty"`
}

// SpatialDimension represents a spatial dimension
type SpatialDimension struct {
	Min         float64 `json:"min"`
	Max         float64 `json:"max"`
	Units       string  `json:"units"`
	GridSpacing float64 `json:"grid_spacing"`
}

// CoordinateTransform represents a coordinate system transformation
type CoordinateTransform struct {
	ID          string   `json:"id"`
	Description *string  `json:"description,omitempty"`
	Dimensions  []string `json:"dimensions"`
}

// InitialConditions represents initial conditions specification
type InitialConditions struct {
	Type   string                 `json:"type"` // "constant", "per_variable", "from_file"
	Value  interface{}            `json:"value,omitempty"`
	Values map[string]interface{} `json:"values,omitempty"`
	Path   *string                `json:"path,omitempty"`
	Format *string                `json:"format,omitempty"`
}

// BoundaryCondition represents boundary condition specification
type BoundaryCondition struct {
	Type       string   `json:"type"` // "constant", "zero_gradient", "periodic"
	Dimensions []string `json:"dimensions"`
	Value      interface{} `json:"value,omitempty"`
}

// Solver represents solver configuration
type Solver struct {
	Strategy string                 `json:"strategy"`
	Config   map[string]interface{} `json:"config,omitempty"`
}

// ========================================
// 8. Metadata and References
// ========================================

// Reference represents a scientific reference
type Reference struct {
	DOI      *string `json:"doi,omitempty"`
	Citation *string `json:"citation,omitempty"`
	URL      *string `json:"url,omitempty"`
	Notes    *string `json:"notes,omitempty"`
}

// Metadata represents file metadata
type Metadata struct {
	Name        string      `json:"name"`
	Description *string     `json:"description,omitempty"`
	Authors     []string    `json:"authors"`
	License     *string     `json:"license,omitempty"`
	Created     *string     `json:"created,omitempty"`
	Modified    *string     `json:"modified,omitempty"`
	Tags        []string    `json:"tags,omitempty"`
	References  []Reference `json:"references,omitempty"`
}

// ========================================
// 9. Main ESM File Structure
// ========================================

// EsmFile represents the top-level ESM file structure
type EsmFile struct {
	Esm             string                    `json:"esm" validate:"required"`
	Metadata        Metadata                  `json:"metadata" validate:"required"`
	Models          map[string]Model          `json:"models,omitempty"`
	ReactionSystems map[string]ReactionSystem `json:"reaction_systems,omitempty"`
	DataLoaders     map[string]DataLoader     `json:"data_loaders,omitempty"`
	Operators       map[string]Operator       `json:"operators,omitempty"`
	Coupling        []interface{}             `json:"coupling,omitempty"` // Will need custom unmarshaling
	Domain          *Domain                   `json:"domain,omitempty"`
	Solver          *Solver                   `json:"solver,omitempty"`
}

// ========================================
// 10. Validation and Utility Methods
// ========================================

// Validate validates the ESM file structure
func (e *EsmFile) Validate() error {
	validate := validator.New()
	if err := validate.Struct(e); err != nil {
		return err
	}

	// At least one of models or reaction_systems must be present
	if len(e.Models) == 0 && len(e.ReactionSystems) == 0 {
		return fmt.Errorf("at least one of 'models' or 'reaction_systems' must be present")
	}

	return nil
}

// ToJSON converts the ESM file to JSON
func (e *EsmFile) ToJSON() ([]byte, error) {
	return json.MarshalIndent(e, "", "  ")
}

// FromJSON creates an ESM file from JSON data
func FromJSON(data []byte) (*EsmFile, error) {
	var esm EsmFile
	if err := json.Unmarshal(data, &esm); err != nil {
		return nil, fmt.Errorf("failed to unmarshal JSON: %w", err)
	}

	if err := esm.Validate(); err != nil {
		return nil, fmt.Errorf("validation failed: %w", err)
	}

	return &esm, nil
}

// ========================================
// 11. Helper Functions for Expression Handling
// ========================================

// UnmarshalExpression handles the custom unmarshaling for Expression union type
func UnmarshalExpression(data []byte) (Expression, error) {
	// Try to unmarshal as number first
	var num float64
	if err := json.Unmarshal(data, &num); err == nil {
		return num, nil
	}

	// Try to unmarshal as string
	var str string
	if err := json.Unmarshal(data, &str); err == nil {
		return str, nil
	}

	// Must be an object (ExprNode)
	var node ExprNode
	if err := json.Unmarshal(data, &node); err != nil {
		return nil, fmt.Errorf("expression must be number, string, or object: %w", err)
	}

	// Recursively unmarshal Args if they contain expressions
	if node.Args != nil {
		for i, arg := range node.Args {
			if argMap, ok := arg.(map[string]interface{}); ok {
				// This is likely another ExprNode that needs to be unmarshaled properly
				argBytes, err := json.Marshal(argMap)
				if err != nil {
					return nil, fmt.Errorf("failed to marshal arg for re-processing: %w", err)
				}
				unmarshaledArg, err := UnmarshalExpression(argBytes)
				if err != nil {
					return nil, fmt.Errorf("failed to unmarshal nested expression in args: %w", err)
				}
				node.Args[i] = unmarshaledArg
			}
		}
	}

	return node, nil
}

// Custom JSON unmarshaling for Equation
func (e *Equation) UnmarshalJSON(data []byte) error {
	// Define a temporary struct with the same structure but using json.RawMessage
	type TempEquation struct {
		LHS json.RawMessage `json:"lhs"`
		RHS json.RawMessage `json:"rhs"`
	}

	var temp TempEquation
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	// Unmarshal LHS
	lhs, err := UnmarshalExpression(temp.LHS)
	if err != nil {
		return fmt.Errorf("failed to unmarshal LHS: %w", err)
	}
	e.LHS = lhs

	// Unmarshal RHS
	rhs, err := UnmarshalExpression(temp.RHS)
	if err != nil {
		return fmt.Errorf("failed to unmarshal RHS: %w", err)
	}
	e.RHS = rhs

	return nil
}

// Custom JSON unmarshaling for AffectEquation
func (ae *AffectEquation) UnmarshalJSON(data []byte) error {
	type TempAffectEquation struct {
		LHS string          `json:"lhs"`
		RHS json.RawMessage `json:"rhs"`
	}

	var temp TempAffectEquation
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	ae.LHS = temp.LHS

	// Unmarshal RHS
	rhs, err := UnmarshalExpression(temp.RHS)
	if err != nil {
		return fmt.Errorf("failed to unmarshal RHS: %w", err)
	}
	ae.RHS = rhs

	return nil
}

// Custom JSON unmarshaling for Reaction
func (r *Reaction) UnmarshalJSON(data []byte) error {
	type TempReaction struct {
		ID         string             `json:"id"`
		Name       *string            `json:"name,omitempty"`
		Substrates []SubstrateProduct `json:"substrates"`
		Products   []SubstrateProduct `json:"products"`
		Rate       json.RawMessage    `json:"rate"`
		Reference  *Reference         `json:"reference,omitempty"`
	}

	var temp TempReaction
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	r.ID = temp.ID
	r.Name = temp.Name
	r.Substrates = temp.Substrates
	r.Products = temp.Products
	r.Reference = temp.Reference

	// Unmarshal Rate
	rate, err := UnmarshalExpression(temp.Rate)
	if err != nil {
		return fmt.Errorf("failed to unmarshal rate: %w", err)
	}
	r.Rate = rate

	return nil
}

// Custom JSON unmarshaling for ModelVariable
func (mv *ModelVariable) UnmarshalJSON(data []byte) error {
	type TempModelVariable struct {
		Type        string          `json:"type"`
		Units       *string         `json:"units,omitempty"`
		Default     interface{}     `json:"default,omitempty"`
		Description *string         `json:"description,omitempty"`
		Expression  json.RawMessage `json:"expression,omitempty"`
	}

	var temp TempModelVariable
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	mv.Type = temp.Type
	mv.Units = temp.Units
	mv.Default = temp.Default
	mv.Description = temp.Description

	// Unmarshal Expression if present
	if len(temp.Expression) > 0 && string(temp.Expression) != "null" {
		expr, err := UnmarshalExpression(temp.Expression)
		if err != nil {
			return fmt.Errorf("failed to unmarshal expression: %w", err)
		}
		mv.Expression = expr
	}

	return nil
}