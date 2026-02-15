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

import { Component, createSignal, createMemo, onMount, onCleanup, For, Show } from 'solid-js';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, SimulationNodeDatum, SimulationLinkDatum } from 'd3-force';
import { zoom, zoomIdentity, ZoomBehavior } from 'd3-zoom';
import { select } from 'd3-selection';
import type { EsmFile, CouplingEntry } from '../types.js';
import type { ComponentGraph, ComponentNode, CouplingEdge } from '../graph.js';
import { component_graph } from '../graph.js';
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

// Extend d3 node/link types with our data
interface GraphNode extends SimulationNodeDatum {
  id: string;
  component: ComponentNode;
  radius: number;
}

interface GraphLink extends SimulationLinkDatum<GraphNode> {
  edge: CouplingEdge;
}

/**
 * CouplingGraph component for visualizing ESM system coupling
 */
export const CouplingGraph: Component<CouplingGraphProps> = (props) => {
  // Signals for interactive state
  const [selectedNode, setSelectedNode] = createSignal<string | null>(null);
  const [selectedNodes, setSelectedNodes] = createSignal<Set<string>>(new Set());
  const [hoveredEdge, setHoveredEdge] = createSignal<string | null>(null);
  const [draggedNode, setDraggedNode] = createSignal<string | null>(null);

  // Zoom and pan state
  const [transform, setTransform] = createSignal({ x: 0, y: 0, k: 1 });

  // Analysis state
  const [circularDependencies, setCircularDependencies] = createSignal<string[]>([]);
  const [criticalPath, setCriticalPath] = createSignal<string[]>([]);

  // Layout state
  const layoutAlgorithm = () => props.layoutAlgorithm ?? 'force-directed';

  // Canvas dimensions
  const width = () => props.width ?? 800;
  const height = () => props.height ?? 600;

  // Extract graph data from ESM file
  const graph = createMemo((): ComponentGraph => {
    return component_graph(props.esmFile);
  });

  // Transform graph data for d3-force with filtering
  const simulation = createMemo(() => {
    const graphData = graph();
    const filters = props.filters;

    // Filter nodes based on component types and search term
    let filteredNodes = graphData.nodes;
    if (filters?.componentTypes && filters.componentTypes.length > 0) {
      filteredNodes = filteredNodes.filter(node => filters.componentTypes!.includes(node.type));
    }
    if (filters?.searchTerm) {
      const searchLower = filters.searchTerm.toLowerCase();
      filteredNodes = filteredNodes.filter(node =>
        node.name.toLowerCase().includes(searchLower) ||
        node.description?.toLowerCase().includes(searchLower) ||
        node.type.toLowerCase().includes(searchLower)
      );
    }

    // Filter edges based on coupling types and whether both endpoints are visible
    let filteredEdges = graphData.edges;
    if (filters?.couplingTypes && filters.couplingTypes.length > 0) {
      filteredEdges = filteredEdges.filter(edge => filters.couplingTypes!.includes(edge.type));
    }

    const nodeIds = new Set(filteredNodes.map(node => node.id));
    filteredEdges = filteredEdges.filter(edge =>
      nodeIds.has(edge.from) && nodeIds.has(edge.to)
    );

    // Create nodes with initial positions and radii based on type
    const nodes: GraphNode[] = filteredNodes.map(component => ({
      id: component.id,
      component,
      radius: getNodeRadius(component.type),
      x: Math.random() * width(),
      y: Math.random() * height()
    }));

    // Create links between nodes
    const links: GraphLink[] = filteredEdges.map(edge => ({
      source: edge.from,
      target: edge.to,
      edge
    }));

    return { nodes, links };
  });

  // D3 force simulation and zoom behavior
  let forceSimulationInstance: ReturnType<typeof forceSimulation> | null = null;
  let zoomBehavior: ZoomBehavior<SVGSVGElement, unknown> | null = null;
  let svgRef: SVGSVGElement | undefined;

  onMount(() => {
    const { nodes, links } = simulation();

    // Setup layout based on algorithm
    if (layoutAlgorithm() === 'force-directed') {
      setupForceDirectedLayout(nodes, links);
    } else if (layoutAlgorithm() === 'hierarchical') {
      setupHierarchicalLayout(nodes, links);
    } else if (layoutAlgorithm() === 'circular') {
      setupCircularLayout(nodes);
    } else if (layoutAlgorithm() === 'grid') {
      setupGridLayout(nodes);
    }

    // Setup zoom and pan
    if (svgRef && props.interactive) {
      zoomBehavior = zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 10])
        .on('zoom', (event) => {
          setTransform({
            x: event.transform.x,
            y: event.transform.y,
            k: event.transform.k
          });
        });

      select(svgRef).call(zoomBehavior);
    }

    // Detect circular dependencies
    if (props.showAnalysis?.circularDependencies) {
      detectCircularDependencies();
    }

    // Calculate critical path
    if (props.showAnalysis?.criticalPath) {
      calculateCriticalPath();
    }
  });

  // Setup force-directed layout
  function setupForceDirectedLayout(nodes: GraphNode[], links: GraphLink[]) {
    forceSimulationInstance = forceSimulation(nodes)
      .force('link', forceLink(links).id(d => (d as GraphNode).id).distance(100))
      .force('charge', forceManyBody().strength(-300))
      .force('center', forceCenter(width() / 2, height() / 2))
      .force('collision', forceCollide().radius(d => (d as GraphNode).radius + 10));

    forceSimulationInstance.on('tick', () => {
      setSelectedNode(selectedNode()); // Force re-render
    });
  }

  // Setup hierarchical layout
  function setupHierarchicalLayout(nodes: GraphNode[], links: GraphLink[]) {
    // Simple hierarchical layout - position nodes in layers
    const layers = new Map<string, number>();
    const visited = new Set<string>();

    // Calculate layers using BFS
    function assignLayers(nodeId: string, layer: number) {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);
      layers.set(nodeId, layer);

      // Find children
      const children = links.filter(link => link.source === nodeId || (typeof link.source === 'object' && (link.source as GraphNode).id === nodeId));
      children.forEach(child => {
        const targetId = typeof child.target === 'string' ? child.target : (child.target as GraphNode).id;
        assignLayers(targetId, layer + 1);
      });
    }

    // Start from nodes with no incoming edges
    nodes.forEach(node => {
      const hasIncoming = links.some(link => {
        const targetId = typeof link.target === 'string' ? link.target : (link.target as GraphNode).id;
        return targetId === node.id;
      });
      if (!hasIncoming) {
        assignLayers(node.id, 0);
      }
    });

    // Position nodes
    const layerCounts = new Map<number, number>();
    layers.forEach(layer => {
      layerCounts.set(layer, (layerCounts.get(layer) || 0) + 1);
    });

    const layerIndices = new Map<number, number>();
    nodes.forEach(node => {
      const layer = layers.get(node.id) || 0;
      const index = layerIndices.get(layer) || 0;
      const count = layerCounts.get(layer) || 1;

      node.x = (width() / Math.max(...layerCounts.values())) * (index + 0.5);
      node.y = (height() / (layers.size || 1)) * (layer + 0.5);
      node.fx = node.x;
      node.fy = node.y;

      layerIndices.set(layer, index + 1);
    });
  }

  // Setup circular layout
  function setupCircularLayout(nodes: GraphNode[]) {
    const centerX = width() / 2;
    const centerY = height() / 2;
    const radius = Math.min(width(), height()) * 0.35;

    nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / nodes.length;
      node.x = centerX + radius * Math.cos(angle);
      node.y = centerY + radius * Math.sin(angle);
      node.fx = node.x;
      node.fy = node.y;
    });
  }

  // Setup grid layout
  function setupGridLayout(nodes: GraphNode[]) {
    const cols = Math.ceil(Math.sqrt(nodes.length));
    const cellWidth = width() / cols;
    const cellHeight = height() / Math.ceil(nodes.length / cols);

    nodes.forEach((node, index) => {
      const col = index % cols;
      const row = Math.floor(index / cols);
      node.x = cellWidth * (col + 0.5);
      node.y = cellHeight * (row + 0.5);
      node.fx = node.x;
      node.fy = node.y;
    });
  }

  // Detect circular dependencies using DFS
  function detectCircularDependencies() {
    const graph = simulation();
    const visiting = new Set<string>();
    const visited = new Set<string>();
    const cycles: string[] = [];

    function dfs(nodeId: string, path: string[]) {
      if (visiting.has(nodeId)) {
        // Found a cycle
        const cycleStart = path.indexOf(nodeId);
        if (cycleStart >= 0) {
          cycles.push(...path.slice(cycleStart));
        }
        return;
      }

      if (visited.has(nodeId)) return;

      visiting.add(nodeId);
      path.push(nodeId);

      // Follow outgoing edges
      graph.edges.forEach(edge => {
        if (edge.from === nodeId) {
          dfs(edge.to, [...path]);
        }
      });

      visiting.delete(nodeId);
      visited.add(nodeId);
    }

    graph.nodes.forEach(node => {
      if (!visited.has(node.id)) {
        dfs(node.id, []);
      }
    });

    setCircularDependencies(cycles);
  }

  // Calculate critical path (longest path through dependencies)
  function calculateCriticalPath() {
    const graph = simulation();
    const distances = new Map<string, number>();
    const predecessors = new Map<string, string | null>();

    // Initialize distances
    graph.nodes.forEach(node => {
      distances.set(node.id, -Infinity);
      predecessors.set(node.id, null);
    });

    // Find starting nodes (no incoming edges)
    const startNodes = graph.nodes.filter(node =>
      !graph.edges.some(edge => edge.to === node.id)
    );

    startNodes.forEach(node => {
      distances.set(node.id, 0);
    });

    // Relax edges (longest path variant of Bellman-Ford)
    for (let i = 0; i < graph.nodes.length - 1; i++) {
      graph.edges.forEach(edge => {
        const fromDist = distances.get(edge.from) || -Infinity;
        const toDist = distances.get(edge.to) || -Infinity;
        if (fromDist !== -Infinity && fromDist + 1 > toDist) {
          distances.set(edge.to, fromDist + 1);
          predecessors.set(edge.to, edge.from);
        }
      });
    }

    // Find the node with maximum distance
    let maxDist = -Infinity;
    let endNode: string | null = null;
    distances.forEach((dist, nodeId) => {
      if (dist > maxDist) {
        maxDist = dist;
        endNode = nodeId;
      }
    });

    // Reconstruct path
    const path: string[] = [];
    let current = endNode;
    while (current !== null) {
      path.unshift(current);
      current = predecessors.get(current) || null;
    }

    setCriticalPath(path);
  }

  onCleanup(() => {
    if (forceSimulationInstance) {
      forceSimulationInstance.stop();
    }
    if (zoomBehavior && svgRef) {
      select(svgRef).on('.zoom', null);
    }
  });

  // Node drag handlers
  const handleNodeMouseDown = (nodeId: string, event: MouseEvent) => {
    if (!props.interactive) return;

    setDraggedNode(nodeId);
    const node = simulation().nodes.find(n => n.id === nodeId);
    if (node && forceSimulationInstance) {
      node.fx = node.x;
      node.fy = node.y;
      forceSimulationInstance.alphaTarget(0.3).restart();
    }

    event.preventDefault();
  };

  const handleMouseMove = (event: MouseEvent) => {
    const draggedId = draggedNode();
    if (!draggedId || !props.interactive) return;

    const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const node = simulation().nodes.find(n => n.id === draggedId);
    if (node) {
      node.fx = x;
      node.fy = y;
    }
  };

  const handleMouseUp = () => {
    const draggedId = draggedNode();
    if (!draggedId) return;

    const node = simulation().nodes.find(n => n.id === draggedId);
    if (node && forceSimulationInstance) {
      node.fx = null;
      node.fy = null;
      forceSimulationInstance.alphaTarget(0);
    }

    setDraggedNode(null);
  };

  // Node click handler
  const handleNodeClick = (nodeId: string, event?: MouseEvent) => {
    if (!props.interactive) return;

    // Handle multi-select with Ctrl/Cmd key
    if (event && (event.ctrlKey || event.metaKey)) {
      const selected = selectedNodes();
      const newSelected = new Set(selected);
      if (selected.has(nodeId)) {
        newSelected.delete(nodeId);
      } else {
        newSelected.add(nodeId);
      }
      setSelectedNodes(newSelected);

      // Clear single selection when multi-selecting
      setSelectedNode(null);
    } else {
      // Single select
      if (props.onSelectComponent) {
        props.onSelectComponent(nodeId);
      }
      setSelectedNode(nodeId === selectedNode() ? null : nodeId);
      setSelectedNodes(new Set());
    }
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedNode(null);
    setSelectedNodes(new Set());
  };

  // Export functionality
  const handleExport = (format: 'svg' | 'png' | 'pdf') => {
    if (!props.onExport || !svgRef) return;

    if (format === 'svg') {
      // Export as SVG string
      const svgData = new XMLSerializer().serializeToString(svgRef);
      props.onExport(format, svgData);
    } else if (format === 'png') {
      // Export as PNG (requires canvas conversion)
      const svgData = new XMLSerializer().serializeToString(svgRef);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      img.onload = () => {
        canvas.width = width();
        canvas.height = height();
        ctx?.drawImage(img, 0, 0);
        const pngData = canvas.toDataURL('image/png');
        props.onExport!('png', pngData);
      };

      img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
    }
    // PDF export would require additional library like jsPDF
  };

  // Edge click handler
  const handleEdgeClick = (edge: CouplingEdge) => {
    if (props.onEditCoupling) {
      props.onEditCoupling(edge.coupling, edge.id);
    }
  };

  // Check if node should be highlighted for analysis
  const isNodeHighlighted = (nodeId: string) => {
    if (props.showAnalysis?.circularDependencies && circularDependencies().includes(nodeId)) {
      return 'circular';
    }
    if (props.showAnalysis?.criticalPath && criticalPath().includes(nodeId)) {
      return 'critical';
    }
    return null;
  };

  return (
    <div class="coupling-graph-container">
      {/* Toolbar */}
      <div class="coupling-graph-toolbar">
        <div class="toolbar-group">
          <button class="toolbar-btn" onClick={() => handleExport('svg')} title="Export as SVG">
            📄 SVG
          </button>
          <button class="toolbar-btn" onClick={() => handleExport('png')} title="Export as PNG">
            🖼️ PNG
          </button>
        </div>

        <div class="toolbar-group">
          <button
            class="toolbar-btn"
            onClick={() => {
              if (zoomBehavior && svgRef) {
                select(svgRef).transition().call(zoomBehavior.transform, zoomIdentity);
              }
            }}
            title="Reset zoom"
          >
            🔍 Reset
          </button>

          <button class="toolbar-btn" onClick={clearSelection} title="Clear selection">
            ❌ Clear
          </button>
        </div>

        <div class="toolbar-group">
          <select
            class="toolbar-select"
            value={layoutAlgorithm()}
            onChange={(e) => {
              // Layout algorithm change would require prop update from parent
              console.log('Layout change requested:', e.target.value);
            }}
          >
            <option value="force-directed">Force Directed</option>
            <option value="hierarchical">Hierarchical</option>
            <option value="circular">Circular</option>
            <option value="grid">Grid</option>
          </select>
        </div>
      </div>

      <svg
        ref={svgRef}
        class="coupling-graph-svg"
        data-testid="coupling-graph-svg"
        width={width()}
        height={height()}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Define arrow markers for directed edges */}
        <defs>
          <marker
            id="arrowhead"
            viewBox="0 -5 10 10"
            refX={8}
            refY={0}
            markerWidth={6}
            markerHeight={6}
            orient="auto"
            class="edge-arrow"
          >
            <path d="M0,-5L10,0L0,5" />
          </marker>
          <marker
            id="arrowhead-highlighted"
            viewBox="0 -5 10 10"
            refX={8}
            refY={0}
            markerWidth={6}
            markerHeight={6}
            orient="auto"
            class="edge-arrow-highlighted"
          >
            <path d="M0,-5L10,0L0,5" />
          </marker>
        </defs>

        {/* Main graph group with zoom/pan transform */}
        <g transform={`translate(${transform().x}, ${transform().y}) scale(${transform().k})`}>
          {/* Render edges */}
          <g class="edges">
            <For each={simulation().links}>
              {(link) => (
                <g class="edge-group">
                  <line
                    class={`edge edge-${link.edge.type} ${hoveredEdge() === link.edge.id ? 'hovered' : ''}`}
                    x1={(link.source as GraphNode).x}
                    y1={(link.source as GraphNode).y}
                    x2={(link.target as GraphNode).x}
                    y2={(link.target as GraphNode).y}
                    marker-end={hoveredEdge() === link.edge.id ? 'url(#arrowhead-highlighted)' : 'url(#arrowhead)'}
                    onClick={() => handleEdgeClick(link.edge)}
                    onMouseEnter={() => setHoveredEdge(link.edge.id)}
                    onMouseLeave={() => setHoveredEdge(null)}
                    style={{ cursor: props.onEditCoupling ? 'pointer' : 'default' }}
                  />

                  {/* Edge label */}
                  <Show when={link.edge.label}>
                    <text
                      class="edge-label"
                      x={((link.source as GraphNode).x + (link.target as GraphNode).x) / 2}
                      y={((link.source as GraphNode).y + (link.target as GraphNode).y) / 2}
                      text-anchor="middle"
                      dy="0.35em"
                    >
                      {link.edge.label}
                    </text>
                  </Show>
                </g>
              )}
            </For>
          </g>

          {/* Render nodes */}
          <g class="nodes">
            <For each={simulation().nodes}>
              {(node) => {
                // Define reactive state for this node
                const isSelected = () => selectedNode() === node.id;
                const isMultiSelected = () => selectedNodes().has(node.id);
                const isDragging = () => draggedNode() === node.id;
                const highlight = () => isNodeHighlighted(node.id);

                // Build reactive class list
                const classList = () => [
                  'node',
                  `node-${node.component.type}`,
                  isSelected() && 'selected',
                  isMultiSelected() && 'multi-selected',
                  isDragging() && 'dragging',
                  highlight() && `highlight-${highlight()}`
                ].filter(Boolean).join(' ');

                return (
                  <g
                    class={classList()}
                    transform={`translate(${node.x},${node.y})`}
                    onMouseDown={(e) => handleNodeMouseDown(node.id, e)}
                    onClick={(e) => handleNodeClick(node.id, e)}
                    style={{ cursor: props.interactive ? 'pointer' : 'default' }}
                  >
                    {/* Node circle */}
                    <circle
                      r={node.radius}
                      class="node-circle"
                    />

                    {/* Multi-select indicator */}
                    <Show when={isMultiSelected()}>
                      <circle
                        r={node.radius + 3}
                        class="multi-select-ring"
                        fill="none"
                        stroke="#007acc"
                        stroke-width="2"
                        stroke-dasharray="5,5"
                      />
                    </Show>

                    {/* Analysis highlight ring */}
                    <Show when={highlight()}>
                      <circle
                        r={node.radius + 5}
                        class={`analysis-ring analysis-${highlight()}`}
                        fill="none"
                        stroke-width="3"
                      />
                    </Show>

                    {/* Node label */}
                    <text
                      class="node-label"
                      text-anchor="middle"
                      dy="0.35em"
                    >
                      {node.component.name}
                    </text>

                    {/* Type indicator */}
                    <text
                      class="node-type"
                      text-anchor="middle"
                      dy={node.radius + 15}
                    >
                      {node.component.type.replace('_', ' ')}
                    </text>
                  </g>
                );
              }}
            </For>
          </g>
        </g>
      </svg>

      {/* Minimap */}
      <div class="minimap-container">
        <svg class="minimap" width="150" height="100" viewBox={`0 0 ${width()} ${height()}`}>
          <rect class="minimap-background" width="100%" height="100%" fill="#f9f9f9" stroke="#ddd" />

          {/* Minimap nodes */}
          <For each={simulation().nodes}>
            {(node) => (
              <circle
                cx={node.x}
                cy={node.y}
                r="2"
                class={`minimap-node minimap-node-${node.component.type}`}
                onClick={() => {
                  // Pan to this node
                  if (zoomBehavior && svgRef) {
                    const transform = zoomIdentity.translate(
                      width() / 2 - (node.x || 0),
                      height() / 2 - (node.y || 0)
                    );
                    select(svgRef).transition().duration(750).call(zoomBehavior.transform, transform);
                  }
                }}
              />
            )}
          </For>

          {/* Current viewport indicator */}
          <rect
            class="viewport-indicator"
            x={-transform().x / transform().k}
            y={-transform().y / transform().k}
            width={width() / transform().k}
            height={height() / transform().k}
            fill="none"
            stroke="#007acc"
            stroke-width="1"
          />
        </svg>
      </div>

      {/* Statistics panel */}
      <div class="statistics-panel">
        <h4>Graph Statistics</h4>
        <div class="stat-item">
          <span class="stat-label">Nodes:</span>
          <span class="stat-value">{simulation().nodes.length}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Edges:</span>
          <span class="stat-value">{simulation().links.length}</span>
        </div>
        <Show when={selectedNodes().size > 0}>
          <div class="stat-item">
            <span class="stat-label">Selected:</span>
            <span class="stat-value">{selectedNodes().size}</span>
          </div>
        </Show>
        <Show when={circularDependencies().length > 0}>
          <div class="stat-item warning">
            <span class="stat-label">Circular deps:</span>
            <span class="stat-value">{circularDependencies().length}</span>
          </div>
        </Show>
      </div>

      {/* Component details panel */}
      <Show when={selectedNode()}>
        <div class="component-details-panel">
          {(() => {
            const nodeId = selectedNode();
            const node = nodeId ? simulation().nodes.find(n => n.id === nodeId) : null;
            if (!node) return null;

            return (
              <>
                <h3>{node.component.name}</h3>
                <p class="component-type">{node.component.type.replace('_', ' ').toUpperCase()}</p>
                <Show when={node.component.description}>
                  <p class="component-description">{node.component.description}</p>
                </Show>
                <button
                  class="close-button"
                  onClick={() => setSelectedNode(null)}
                >
                  ×
                </button>
              </>
            );
          })()}
        </div>
      </Show>

      {/* Multi-selection panel */}
      <Show when={selectedNodes().size > 0}>
        <div class="multi-select-panel">
          <h4>Selected Components ({selectedNodes().size})</h4>
          <div class="selected-nodes-list">
            <For each={[...selectedNodes()]}>
              {(nodeId) => {
                const node = simulation().nodes.find(n => n.id === nodeId);
                return node && (
                  <div class="selected-node-item">
                    <span class={`node-type-badge badge-${node.component.type}`}>
                      {node.component.type}
                    </span>
                    <span class="node-name">{node.component.name}</span>
                  </div>
                );
              }}
            </For>
          </div>
          <div class="multi-select-actions">
            <button onClick={clearSelection} class="clear-selection-btn">
              Clear Selection
            </button>
          </div>
        </div>
      </Show>
    </div>
  );
};

/**
 * Get node radius based on component type
 */
function getNodeRadius(type: ComponentNode['type']): number {
  switch (type) {
    case 'model':
      return 30;
    case 'reaction_system':
      return 25;
    case 'data_loader':
      return 20;
    case 'operator':
      return 15;
    default:
      return 20;
  }
}