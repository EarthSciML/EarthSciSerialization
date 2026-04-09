/**
 * Advanced expression analysis and manipulation types
 *
 * This module defines the core types for advanced expression analysis,
 * including dependency graphs, complexity metrics, and manipulation utilities.
 */

import type { Expr, Model, EsmFile, ComponentNode, VariableNode, Graph } from '../types.js';

/** Node representing a variable in a dependency graph */
export interface DependencyNode {
  /** Variable name */
  name: string;
  /** Type of variable (state, parameter, observed, species) */
  kind: 'state' | 'parameter' | 'observed' | 'species';
  /** System/model this variable belongs to */
  system: string;
  /** Units if specified */
  units?: string;
  /** Definition expression if available */
  definition?: Expr;
  /** Nesting level in the dependency graph */
  depth: number;
}

/** Edge representing a dependency relationship between variables */
export interface DependencyRelation {
  /** Source variable */
  source: string;
  /** Target variable */
  target: string;
  /** Type of dependency */
  type: 'direct' | 'indirect' | 'circular' | 'parameter_dependency' | 'definition_dependency';
  /** Strength/weight of dependency (0-1) */
  weight: number;
  /** Expression that creates this dependency */
  expression?: Expr;
}

/** Graph representing variable dependencies */
export interface DependencyGraph extends Graph<DependencyNode, DependencyRelation> {
  /** Check for circular dependencies */
  hasCircularDependencies(): boolean;
  /** Get strongly connected components */
  getStronglyConnectedComponents(): DependencyNode[][];
  /** Topological sort of dependencies */
  topologicalSort(): DependencyNode[];
}

/** Complexity metrics for an expression */
export interface ComplexityMetrics {
  /** Total depth of the expression tree */
  depth: number;
  /** Total number of operations */
  operationCount: number;
  /** Number of unique variables */
  variableCount: number;
  /** Number of constants */
  constantCount: number;
  /** Distribution of operation types */
  operationTypes: Record<string, number>;
  /** Estimated computational cost (arbitrary units) */
  computationalCost: number;
  /** Memory usage estimate (arbitrary units) */
  memoryUsage: number;
}

/** Common subexpression identification result */
export interface CommonSubexpression {
  /** The common subexpression */
  expression: Expr;
  /** Locations where this subexpression appears */
  locations: ExpressionLocation[];
  /** Number of occurrences */
  count: number;
  /** Estimated cost savings from factoring out */
  savings: number;
}

/** Location of an expression within a larger structure */
export interface ExpressionLocation {
  /** Path to the expression (e.g., ['models', 'Transport', 'equations', 0, 'rhs']) */
  path: string[];
  /** Human-readable description */
  description: string;
  /** Parent expression context */
  context?: Expr;
}

/** Pattern for expression template matching */
export interface ExpressionPattern {
  /** Template expression with placeholders */
  template: Expr;
  /** Variable bindings for pattern matching */
  bindings: Record<string, Expr>;
  /** Constraints on pattern variables */
  constraints?: Record<string, (expr: Expr) => boolean>;
}

/** Result of expression template matching */
export interface MatchResult {
  /** Whether the pattern matched */
  matched: boolean;
  /** Variable bindings if matched */
  bindings: Record<string, Expr>;
  /** Confidence score (0-1) */
  confidence: number;
}

/** Optimization transformation for expressions */
export interface Optimization {
  /** Name of the optimization */
  name: string;
  /** Description of what it does */
  description: string;
  /** Pattern to match */
  pattern: ExpressionPattern;
  /** Replacement expression template */
  replacement: Expr;
  /** Estimated performance improvement */
  improvement: number;
}

/** Result of symbolic differentiation */
export interface DerivativeResult {
  /** The derivative expression */
  derivative: Expr;
  /** Variable with respect to which we differentiated */
  variable: string;
  /** Simplified form if different from derivative */
  simplified?: Expr;
  /** Chain rule components if applicable */
  chainComponents?: Array<{
    expression: Expr;
    derivative: Expr;
  }>;
}

/** Layout algorithm for graph visualization */
export interface LayoutAlgorithm {
  /** Name of the algorithm */
  name: string;
  /** Apply layout to graph nodes */
  layout<N, E>(graph: Graph<N, E>): LayoutResult<N>;
}

/** Result of graph layout algorithm */
export interface LayoutResult<N> {
  /** Node positions */
  positions: Map<string, { x: number; y: number }>;
  /** Bounding box of the layout */
  bounds: { width: number; height: number };
  /** Layout-specific metadata */
  metadata?: Record<string, any>;
}

/** Export format for graphs */
export type GraphExportFormat = 'dot' | 'mermaid' | 'json' | 'd3' | 'cytoscape';

/** Export options for graphs */
export interface GraphExportOptions {
  /** Format to export */
  format: GraphExportFormat;
  /** Include metadata in export */
  includeMetadata?: boolean;
  /** Styling options */
  styling?: {
    nodeColor?: string | ((node: any) => string);
    edgeColor?: string | ((edge: any) => string);
    nodeShape?: string | ((node: any) => string);
    fontSize?: number;
  };
  /** Layout algorithm to use */
  layout?: LayoutAlgorithm;
}