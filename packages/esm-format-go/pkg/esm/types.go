package esm

import (
	"bytes"
	"encoding/json"
	"fmt"

	"github.com/go-playground/validator/v10"
)

// ========================================
// 1. Expression Types
// ========================================

// ExprNode represents an operator node in the expression tree
type ExprNode struct {
	Op        string        `json:"op"`
	Args      []interface{} `json:"args"`
	Wrt       *string       `json:"wrt,omitempty"`        // for derivatives
	Dim       *string       `json:"dim,omitempty"`        // for grad
	HandlerID *string       `json:"handler_id,omitempty"` // for `call` (esm-spec §4.4)
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

// ModelVariable represents a variable in a mathematical model.
//
// Type "brownian" denotes a stochastic noise source (Wiener process); the
// presence of any brownian variable promotes the enclosing model from an ODE
// system to an SDE system. NoiseKind and CorrelationGroup apply only to
// brownian variables.
type ModelVariable struct {
	Type        string      `json:"type"` // "state", "parameter", "observed", or "brownian"
	Units       *string     `json:"units,omitempty"`
	Default     interface{} `json:"default,omitempty"`
	Description *string     `json:"description,omitempty"`
	Expression  Expression  `json:"expression,omitempty"` // for observed variables
	// Shape lists dimension names (drawn from the enclosing model's
	// domain.spatial) for arrayed variables. Nil means scalar.
	// See discretization RFC §10.2.
	Shape []string `json:"shape,omitempty"`
	// Location tags the variable's staggered-grid location
	// (e.g., "cell_center", "edge_normal", "vertex"). Empty means
	// no explicit staggering. See discretization RFC §10.2.
	Location string `json:"location,omitempty"`
	// NoiseKind is brownian-only: kind of stochastic process. Currently only
	// "wiener" is supported.
	NoiseKind string `json:"noise_kind,omitempty"`
	// CorrelationGroup is brownian-only: optional opaque tag grouping
	// correlated noise sources.
	CorrelationGroup string `json:"correlation_group,omitempty"`
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

// FunctionalAffect represents a registered functional affect handler for
// discrete events that require complex behavior beyond symbolic expressions
type FunctionalAffect struct {
	HandlerID       string                 `json:"handler_id"`
	ReadVars        []string               `json:"read_vars"`
	ReadParams      []string               `json:"read_params"`
	ModifiedParams  []string               `json:"modified_params,omitempty"`
	Config          map[string]interface{} `json:"config,omitempty"`
}

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
	Affects             []AffectEquation      `json:"affects,omitempty"`
	FunctionalAffect    *FunctionalAffect     `json:"functional_affect,omitempty"`
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

// DataLoader is a runtime-agnostic description of an external data source.
// It carries enough structural information to locate files, map timestamps
// to files, describe spatial and variable semantics, and regrid — rather
// than pointing at a runtime handler. Shape matches the schema under gt-q4k.
type DataLoader struct {
	Kind       string                        `json:"kind"` // "grid", "points", or "static"
	Source     DataLoaderSource              `json:"source"`
	Temporal   *DataLoaderTemporal           `json:"temporal,omitempty"`
	Spatial    *DataLoaderSpatial            `json:"spatial,omitempty"`
	Variables  map[string]DataLoaderVariable `json:"variables"`
	Regridding *DataLoaderRegridding         `json:"regridding,omitempty"`
	Reference  *Reference                    `json:"reference,omitempty"`
	Metadata   map[string]interface{}        `json:"metadata,omitempty"`
}

// DataLoaderSource describes file discovery for a data source. URL templates
// use Jinja-style substitutions for dates, variable names, and similar.
type DataLoaderSource struct {
	URLTemplate string   `json:"url_template"`
	Mirrors     []string `json:"mirrors,omitempty"`
}

// DataLoaderTemporal describes the temporal coverage and record layout.
// RecordsPerFile may be an int or the string "auto"; represented as interface{}.
type DataLoaderTemporal struct {
	Start          *string     `json:"start,omitempty"`
	End            *string     `json:"end,omitempty"`
	FilePeriod     *string     `json:"file_period,omitempty"`
	Frequency      *string     `json:"frequency,omitempty"`
	RecordsPerFile interface{} `json:"records_per_file,omitempty"`
	TimeVariable   *string     `json:"time_variable,omitempty"`
}

// DataLoaderSpatial describes the spatial grid of a data source.
type DataLoaderSpatial struct {
	CRS        string                `json:"crs"`
	GridType   string                `json:"grid_type"` // "latlon", "lambert_conformal", "mercator", "polar_stereographic", "rotated_pole", "unstructured"
	Staggering map[string]string     `json:"staggering,omitempty"`
	Resolution map[string]float64    `json:"resolution,omitempty"`
	Extent     map[string][2]float64 `json:"extent,omitempty"`
}

// DataLoaderVariable describes one variable exposed by a data loader.
// UnitConversion is either a number or an Expression AST node.
type DataLoaderVariable struct {
	FileVariable   string      `json:"file_variable"`
	Units          string      `json:"units"`
	UnitConversion interface{} `json:"unit_conversion,omitempty"`
	Description    *string     `json:"description,omitempty"`
	Reference      *Reference  `json:"reference,omitempty"`
}

// DataLoaderRegridding describes the structural regridding configuration.
type DataLoaderRegridding struct {
	FillValue     *float64 `json:"fill_value,omitempty"`
	Extrapolation *string  `json:"extrapolation,omitempty"` // "clamp", "nan", "periodic"
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

// RegisteredFunctionSignature describes the calling convention for a
// RegisteredFunction (esm-spec §9.2).
type RegisteredFunctionSignature struct {
	ArgCount   int      `json:"arg_count"`
	ArgTypes   []string `json:"arg_types,omitempty"`
	ReturnType *string  `json:"return_type,omitempty"`
}

// RegisteredFunction is a named pure callable invoked inside expressions via
// the `call` op (esm-spec §4.4 / §9.2). The serialized entry only declares
// the calling contract; the concrete implementation is bound at runtime.
type RegisteredFunction struct {
	ID          string                      `json:"id"`
	Signature   RegisteredFunctionSignature `json:"signature"`
	Units       *string                     `json:"units,omitempty"`
	ArgUnits    []*string                   `json:"arg_units,omitempty"`
	Description *string                     `json:"description,omitempty"`
	References  []Reference                 `json:"references,omitempty"`
	Config      map[string]interface{}      `json:"config,omitempty"`
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
	Interface   *string                      `json:"interface,omitempty"`
	Lifting     *string                      `json:"lifting,omitempty"`
	Description *string                      `json:"description,omitempty"`
}

func (o OperatorComposeCoupling) GetType() string { return o.Type }

// CouplingCouple represents bi-directional coupling via connector equations
type CouplingCouple struct {
	Type        string    `json:"type"` // "couple"
	Systems     [2]string `json:"systems"`
	Connector   Connector `json:"connector"`
	Interface   *string   `json:"interface,omitempty"`
	Lifting     *string   `json:"lifting,omitempty"`
	Description *string   `json:"description,omitempty"`
}

func (c CouplingCouple) GetType() string { return c.Type }

// VariableMapCoupling represents variable mapping
type VariableMapCoupling struct {
	Type        string   `json:"type"` // "variable_map"
	From        string   `json:"from"`
	To          string   `json:"to"`
	Transform   string   `json:"transform"`
	Factor      *float64 `json:"factor,omitempty"`
	Interface   *string  `json:"interface,omitempty"`
	Lifting     *string  `json:"lifting,omitempty"`
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

// CallbackCoupling represents callback-based coupling
type CallbackCoupling struct {
	Type        string                 `json:"type"` // "callback"
	CallbackID  string                 `json:"callback_id"`
	Config      map[string]interface{} `json:"config,omitempty"`
	Description *string                `json:"description,omitempty"`
}

func (c CallbackCoupling) GetType() string { return c.Type }

// EventCoupling represents event-based coupling
type EventCoupling struct {
	Type               string                `json:"type"` // "event"
	EventType          string                `json:"event_type"` // "continuous" or "discrete"
	Name               string                `json:"name"`
	Conditions         []Expression          `json:"conditions,omitempty"`          // for continuous events
	Trigger            *DiscreteEventTrigger  `json:"trigger,omitempty"`             // for discrete events
	Affects            []AffectEquation      `json:"affects,omitempty"`
	FunctionalAffect   *FunctionalAffect     `json:"functional_affect,omitempty"`
	AffectNeg          []AffectEquation      `json:"affect_neg,omitempty"`
	DiscreteParameters []string              `json:"discrete_parameters,omitempty"`
	RootFind           *string               `json:"root_find,omitempty"`
	Reinitialize       *bool                 `json:"reinitialize,omitempty"`
	Description        *string               `json:"description,omitempty"`
}

func (e EventCoupling) GetType() string { return e.Type }

// Connector represents the connector system for couple coupling
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
// 7. Domain
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

// ========================================
// 7b. Interfaces
// ========================================

// Interface represents a geometric connection between two domains
type Interface struct {
	Description      *string          `json:"description,omitempty"`
	Domains          [2]string        `json:"domains"`
	DimensionMapping DimensionMapping `json:"dimension_mapping"`
	Regridding       *Regridding      `json:"regridding,omitempty"`
}

// DimensionMapping specifies shared dimensions and constraints at an interface
type DimensionMapping struct {
	Shared      map[string]string              `json:"shared,omitempty"`
	Constraints map[string]InterfaceConstraint `json:"constraints,omitempty"`
}

// InterfaceConstraint represents a constraint on a non-shared dimension at the interface
type InterfaceConstraint struct {
	Value       interface{} `json:"value"` // string ("min", "max", "boundary") or number
	Description *string     `json:"description,omitempty"`
}

// Regridding represents the regridding strategy at an interface
type Regridding struct {
	Method      string  `json:"method"` // "bilinear", "conservative", "nearest", "patch"
	Description *string `json:"description,omitempty"`
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
	Esm                 string                        `json:"esm" validate:"required"`
	Metadata            Metadata                      `json:"metadata" validate:"required"`
	Models              map[string]Model              `json:"models,omitempty"`
	ReactionSystems     map[string]ReactionSystem     `json:"reaction_systems,omitempty"`
	DataLoaders         map[string]DataLoader         `json:"data_loaders,omitempty"`
	Operators           map[string]Operator           `json:"operators,omitempty"`
	RegisteredFunctions map[string]RegisteredFunction `json:"registered_functions,omitempty"`
	Coupling            []interface{}                 `json:"coupling,omitempty"` // Properly deserialized coupling entries
	Domains             map[string]Domain             `json:"domains,omitempty"`
	Interfaces          map[string]Interface          `json:"interfaces,omitempty"`
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

// UnmarshalExpression handles the custom unmarshaling for Expression union
// type. Numeric literals preserve the RFC §5.4.6 round-trip parse rule:
// a JSON-number token with '.', 'e', or 'E' parses to float64; otherwise to
// int64 (falling back to float64 if out of int64 range).
func UnmarshalExpression(data []byte) (Expression, error) {
	// Try to unmarshal as number first (via json.Number to preserve int/float
	// distinction).
	var num json.Number
	if err := json.Unmarshal(data, &num); err == nil {
		return normalizeJSONNumber(num), nil
	}

	// Try to unmarshal as string
	var str string
	if err := json.Unmarshal(data, &str); err == nil {
		return str, nil
	}

	// Must be an object (ExprNode). Decode via UseNumber so nested literals in
	// Args keep their int/float shape.
	var node ExprNode
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	if err := dec.Decode(&node); err != nil {
		return nil, fmt.Errorf("expression must be number, string, or object: %w", err)
	}

	// Recursively normalize Args, handling nested expressions and literals.
	if node.Args != nil {
		for i, arg := range node.Args {
			switch a := arg.(type) {
			case json.Number:
				node.Args[i] = normalizeJSONNumber(a)
			case map[string]interface{}:
				argBytes, err := json.Marshal(a)
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
		Type             string          `json:"type"`
		Units            *string         `json:"units,omitempty"`
		Default          interface{}     `json:"default,omitempty"`
		Description      *string         `json:"description,omitempty"`
		Expression       json.RawMessage `json:"expression,omitempty"`
		Shape            []string        `json:"shape,omitempty"`
		Location         string          `json:"location,omitempty"`
		NoiseKind        string          `json:"noise_kind,omitempty"`
		CorrelationGroup string          `json:"correlation_group,omitempty"`
	}

	var temp TempModelVariable
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	mv.Type = temp.Type
	mv.Units = temp.Units
	mv.Default = temp.Default
	mv.Description = temp.Description
	mv.Shape = temp.Shape
	mv.Location = temp.Location
	mv.NoiseKind = temp.NoiseKind
	mv.CorrelationGroup = temp.CorrelationGroup

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

// Custom JSON unmarshaling for EventCoupling
func (ec *EventCoupling) UnmarshalJSON(data []byte) error {
	type TempEventCoupling struct {
		Type               string                 `json:"type"`
		EventType          string                 `json:"event_type"`
		Name               string                 `json:"name"`
		Conditions         []json.RawMessage      `json:"conditions,omitempty"`
		Trigger            *DiscreteEventTrigger  `json:"trigger,omitempty"`
		Affects            []AffectEquation       `json:"affects"`
		DiscreteParameters []string               `json:"discrete_parameters,omitempty"`
		Description        *string                `json:"description,omitempty"`
	}

	var temp TempEventCoupling
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	ec.Type = temp.Type
	ec.EventType = temp.EventType
	ec.Name = temp.Name
	ec.Trigger = temp.Trigger
	ec.Affects = temp.Affects
	ec.DiscreteParameters = temp.DiscreteParameters
	ec.Description = temp.Description

	// Unmarshal Conditions if present
	if len(temp.Conditions) > 0 {
		ec.Conditions = make([]Expression, len(temp.Conditions))
		for i, conditionData := range temp.Conditions {
			condition, err := UnmarshalExpression(conditionData)
			if err != nil {
				return fmt.Errorf("failed to unmarshal condition at index %d: %w", i, err)
			}
			ec.Conditions[i] = condition
		}
	}

	return nil
}

// Custom JSON unmarshaling for DataLoaderVariable (handles Expression union
// in unit_conversion: number | ExpressionNode).
func (v *DataLoaderVariable) UnmarshalJSON(data []byte) error {
	type TempDataLoaderVariable struct {
		FileVariable   string          `json:"file_variable"`
		Units          string          `json:"units"`
		UnitConversion json.RawMessage `json:"unit_conversion,omitempty"`
		Description    *string         `json:"description,omitempty"`
		Reference      *Reference      `json:"reference,omitempty"`
	}
	var temp TempDataLoaderVariable
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}
	v.FileVariable = temp.FileVariable
	v.Units = temp.Units
	v.Description = temp.Description
	v.Reference = temp.Reference
	if len(temp.UnitConversion) > 0 && string(temp.UnitConversion) != "null" {
		expr, err := UnmarshalExpression(temp.UnitConversion)
		if err != nil {
			return fmt.Errorf("failed to unmarshal unit_conversion: %w", err)
		}
		v.UnitConversion = expr
	}
	return nil
}

// Custom JSON unmarshaling for EsmFile
func (esm *EsmFile) UnmarshalJSON(data []byte) error {
	// Define a temporary struct that matches EsmFile but uses json.RawMessage for coupling
	type TempEsmFile struct {
		Esm                 string                        `json:"esm"`
		Metadata            Metadata                      `json:"metadata"`
		Models              map[string]Model              `json:"models,omitempty"`
		ReactionSystems     map[string]ReactionSystem     `json:"reaction_systems,omitempty"`
		DataLoaders         map[string]DataLoader         `json:"data_loaders,omitempty"`
		Operators           map[string]Operator           `json:"operators,omitempty"`
		RegisteredFunctions map[string]RegisteredFunction `json:"registered_functions,omitempty"`
		Coupling            json.RawMessage               `json:"coupling,omitempty"`
		Domains             map[string]Domain             `json:"domains,omitempty"`
		Interfaces          map[string]Interface          `json:"interfaces,omitempty"`
	}

	var temp TempEsmFile
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	// Copy all fields except coupling
	esm.Esm = temp.Esm
	esm.Metadata = temp.Metadata
	esm.Models = temp.Models
	esm.ReactionSystems = temp.ReactionSystems
	esm.DataLoaders = temp.DataLoaders
	esm.Operators = temp.Operators
	esm.RegisteredFunctions = temp.RegisteredFunctions
	esm.Domains = temp.Domains
	esm.Interfaces = temp.Interfaces

	// Handle coupling array with proper type deserialization
	if len(temp.Coupling) > 0 && string(temp.Coupling) != "null" {
		couplingEntries, err := UnmarshalCouplingArray(temp.Coupling)
		if err != nil {
			return fmt.Errorf("failed to unmarshal coupling: %w", err)
		}
		esm.Coupling = couplingEntries
	}

	return nil
}

// UnmarshalCouplingArray handles the deserialization of the coupling array
func UnmarshalCouplingArray(data []byte) ([]interface{}, error) {
	// First unmarshal as a slice of raw messages
	var rawEntries []json.RawMessage
	if err := json.Unmarshal(data, &rawEntries); err != nil {
		return nil, fmt.Errorf("failed to unmarshal coupling array: %w", err)
	}

	var result []interface{}
	for i, rawEntry := range rawEntries {
		entry, err := UnmarshalCouplingEntry(rawEntry)
		if err != nil {
			return nil, fmt.Errorf("failed to unmarshal coupling entry at index %d: %w", i, err)
		}
		result = append(result, entry)
	}

	return result, nil
}

// UnmarshalCouplingEntry handles the deserialization of a single coupling entry
func UnmarshalCouplingEntry(data []byte) (CouplingEntry, error) {
	// First, determine the type by unmarshaling into a map
	var typeMap map[string]interface{}
	if err := json.Unmarshal(data, &typeMap); err != nil {
		return nil, fmt.Errorf("failed to unmarshal coupling entry as map: %w", err)
	}

	typeVal, ok := typeMap["type"]
	if !ok {
		return nil, fmt.Errorf("coupling entry missing required 'type' field")
	}

	typeStr, ok := typeVal.(string)
	if !ok {
		return nil, fmt.Errorf("coupling entry 'type' field must be a string, got %T", typeVal)
	}

	// Unmarshal into the appropriate concrete type based on the type field
	switch typeStr {
	case "operator_compose":
		var coupling OperatorComposeCoupling
		if err := json.Unmarshal(data, &coupling); err != nil {
			return nil, fmt.Errorf("failed to unmarshal OperatorComposeCoupling: %w", err)
		}
		return coupling, nil

	case "couple":
		var coupling CouplingCouple
		if err := json.Unmarshal(data, &coupling); err != nil {
			return nil, fmt.Errorf("failed to unmarshal CouplingCouple: %w", err)
		}
		return coupling, nil

	case "variable_map":
		var coupling VariableMapCoupling
		if err := json.Unmarshal(data, &coupling); err != nil {
			return nil, fmt.Errorf("failed to unmarshal VariableMapCoupling: %w", err)
		}
		return coupling, nil

	case "operator_apply":
		var coupling OperatorApplyCoupling
		if err := json.Unmarshal(data, &coupling); err != nil {
			return nil, fmt.Errorf("failed to unmarshal OperatorApplyCoupling: %w", err)
		}
		return coupling, nil

	case "callback":
		var coupling CallbackCoupling
		if err := json.Unmarshal(data, &coupling); err != nil {
			return nil, fmt.Errorf("failed to unmarshal CallbackCoupling: %w", err)
		}
		return coupling, nil

	case "event":
		var coupling EventCoupling
		if err := json.Unmarshal(data, &coupling); err != nil {
			return nil, fmt.Errorf("failed to unmarshal EventCoupling: %w", err)
		}
		return coupling, nil

	default:
		return nil, fmt.Errorf("unknown coupling type: %s", typeStr)
	}
}
