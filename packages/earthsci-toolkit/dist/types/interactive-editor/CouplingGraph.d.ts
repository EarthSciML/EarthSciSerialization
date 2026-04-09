/**
 * CouplingGraph - SolidJS component for visualizing ESM coupling relationships
 *
 * This component renders a visual directed graph of model components and their
 * coupling relationships using d3-force for layout and SolidJS for DOM rendering.
 *
 * Features:
 * - Nodes represent models, reaction systems, data loaders, operators
 * - Edges represent coupling entries from ESM file
 * - Click edges to edit coupling rules
 * - Drag nodes to reposition
 * - Zoom and pan support
 * - Responsive layout with collision detection
 */
import { Component } from 'solid-js';
import type { EsmFile, CouplingEntry } from '../types.js';
import type { ComponentNode } from '../graph.js';
import './CouplingGraph.css';
export interface CouplingGraphProps {
    /** The ESM file to visualize */
    esmFile: EsmFile;
    /** Callback when a coupling edge is clicked for editing */
    onEditCoupling?: (coupling: CouplingEntry, edgeId: string) => void;
    /** Callback when a component node is clicked */
    onSelectComponent?: (componentId: string) => void;
    /** Width of the visualization area */
    width?: number;
    /** Height of the visualization area */
    height?: number;
    /** Whether the visualization should be interactive */
    interactive?: boolean;
    /** Callback when graph is exported */
    onExport?: (format: 'svg' | 'png' | 'pdf', data: string) => void;
    /** Layout algorithm to use */
    layoutAlgorithm?: 'force-directed' | 'hierarchical' | 'circular' | 'grid';
    /** Filter settings for what to show */
    filters?: {
        couplingTypes?: string[];
        componentTypes?: ComponentNode['type'][];
        searchTerm?: string;
    };
    /** Whether to show analysis overlays */
    showAnalysis?: {
        circularDependencies?: boolean;
        criticalPath?: boolean;
        centrality?: boolean;
    };
}
/**
 * CouplingGraph component for visualizing ESM system coupling
 */
export declare const CouplingGraph: Component<CouplingGraphProps>;
//# sourceMappingURL=CouplingGraph.d.ts.map