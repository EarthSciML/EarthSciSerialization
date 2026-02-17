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
import { createSignal, createMemo, onMount, onCleanup, For, Show } from 'solid-js';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
import { component_graph } from '../graph.js';
import './CouplingGraph.css';
/**
 * CouplingGraph component for visualizing ESM system coupling
 */
export const CouplingGraph = (props) => {
    // Signals for interactive state
    const [selectedNode, setSelectedNode] = createSignal(null);
    const [hoveredEdge, setHoveredEdge] = createSignal(null);
    const [draggedNode, setDraggedNode] = createSignal(null);
    // Canvas dimensions
    const width = () => props.width ?? 800;
    const height = () => props.height ?? 600;
    // Extract graph data from ESM file
    const graph = createMemo(() => {
        return component_graph(props.esmFile);
    });
    // Transform graph data for d3-force
    const simulation = createMemo(() => {
        const graphData = graph();
        // Create nodes with initial positions and radii based on type
        const nodes = graphData.nodes.map(component => ({
            id: component.id,
            component,
            radius: getNodeRadius(component.type),
            x: Math.random() * width(),
            y: Math.random() * height()
        }));
        // Create links between nodes
        const links = graphData.edges.map(edge => ({
            source: edge.from,
            target: edge.to,
            edge
        }));
        return { nodes, links };
    });
    // D3 force simulation
    let forceSimulationInstance = null;
    onMount(() => {
        const { nodes, links } = simulation();
        // Create force simulation
        forceSimulationInstance = forceSimulation(nodes)
            .force('link', forceLink(links).id(d => d.id).distance(100))
            .force('charge', forceManyBody().strength(-300))
            .force('center', forceCenter(width() / 2, height() / 2))
            .force('collision', forceCollide().radius(d => d.radius + 10));
        // Update positions on each tick
        forceSimulationInstance.on('tick', () => {
            // Trigger reactivity - the positions are updated by reference
            setSelectedNode(selectedNode()); // Force re-render
        });
    });
    onCleanup(() => {
        if (forceSimulationInstance) {
            forceSimulationInstance.stop();
        }
    });
    // Node drag handlers
    const handleNodeMouseDown = (nodeId, event) => {
        if (!props.interactive)
            return;
        setDraggedNode(nodeId);
        const node = simulation().nodes.find(n => n.id === nodeId);
        if (node && forceSimulationInstance) {
            node.fx = node.x;
            node.fy = node.y;
            forceSimulationInstance.alphaTarget(0.3).restart();
        }
        event.preventDefault();
    };
    const handleMouseMove = (event) => {
        const draggedId = draggedNode();
        if (!draggedId || !props.interactive)
            return;
        const rect = event.currentTarget.getBoundingClientRect();
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
        if (!draggedId)
            return;
        const node = simulation().nodes.find(n => n.id === draggedId);
        if (node && forceSimulationInstance) {
            node.fx = null;
            node.fy = null;
            forceSimulationInstance.alphaTarget(0);
        }
        setDraggedNode(null);
    };
    // Node click handler
    const handleNodeClick = (nodeId) => {
        if (props.onSelectComponent) {
            props.onSelectComponent(nodeId);
        }
        setSelectedNode(nodeId === selectedNode() ? null : nodeId);
    };
    // Edge click handler
    const handleEdgeClick = (edge) => {
        if (props.onEditCoupling) {
            props.onEditCoupling(edge.coupling, edge.id);
        }
    };
    return (<div class="coupling-graph-container">
      <svg class="coupling-graph-svg" width={width()} height={height()} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
        {/* Define arrow markers for directed edges */}
        <defs>
          <marker id="arrowhead" viewBox="0 -5 10 10" refX={8} refY={0} markerWidth={6} markerHeight={6} orient="auto" class="edge-arrow">
            <path d="M0,-5L10,0L0,5"/>
          </marker>
          <marker id="arrowhead-highlighted" viewBox="0 -5 10 10" refX={8} refY={0} markerWidth={6} markerHeight={6} orient="auto" class="edge-arrow-highlighted">
            <path d="M0,-5L10,0L0,5"/>
          </marker>
        </defs>

        {/* Render edges */}
        <g class="edges">
          <For each={simulation().links}>
            {(link) => (<g class="edge-group">
                <line class={`edge edge-${link.edge.type} ${hoveredEdge() === link.edge.id ? 'hovered' : ''}`} x1={link.source.x} y1={link.source.y} x2={link.target.x} y2={link.target.y} marker-end={hoveredEdge() === link.edge.id ? 'url(#arrowhead-highlighted)' : 'url(#arrowhead)'} onClick={() => handleEdgeClick(link.edge)} onMouseEnter={() => setHoveredEdge(link.edge.id)} onMouseLeave={() => setHoveredEdge(null)} style={{ cursor: props.onEditCoupling ? 'pointer' : 'default' }}/>

                {/* Edge label */}
                <Show when={link.edge.label}>
                  <text class="edge-label" x={(link.source.x + link.target.x) / 2} y={(link.source.y + link.target.y) / 2} text-anchor="middle" dy="0.35em">
                    {link.edge.label}
                  </text>
                </Show>
              </g>)}
          </For>
        </g>

        {/* Render nodes */}
        <g class="nodes">
          <For each={simulation().nodes}>
            {(node) => (<g class={`node node-${node.component.type} ${selectedNode() === node.id ? 'selected' : ''} ${draggedNode() === node.id ? 'dragging' : ''}`} transform={`translate(${node.x},${node.y})`} onMouseDown={(e) => handleNodeMouseDown(node.id, e)} onClick={() => handleNodeClick(node.id)} style={{ cursor: props.interactive ? 'pointer' : 'default' }}>
                {/* Node circle */}
                <circle r={node.radius} class="node-circle"/>

                {/* Node label */}
                <text class="node-label" text-anchor="middle" dy="0.35em">
                  {node.component.name}
                </text>

                {/* Type indicator */}
                <text class="node-type" text-anchor="middle" dy={node.radius + 15}>
                  {node.component.type.replace('_', ' ')}
                </text>
              </g>)}
          </For>
        </g>
      </svg>

      {/* Component details panel */}
      <Show when={selectedNode()}>
        {(nodeId) => {
            const node = simulation().nodes.find(n => n.id === nodeId);
            return node && (<div class="component-details-panel">
              <h3>{node.component.name}</h3>
              <p class="component-type">{node.component.type.replace('_', ' ')}</p>
              <Show when={node.component.description}>
                <p class="component-description">{node.component.description}</p>
              </Show>
              <button class="close-button" onClick={() => setSelectedNode(null)}>
                ×
              </button>
            </div>);
        }}
      </Show>
    </div>);
};
/**
 * Get node radius based on component type
 */
function getNodeRadius(type) {
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
//# sourceMappingURL=CouplingGraph.jsx.map