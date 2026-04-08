# ESM Format Web Components

Framework-agnostic web components for the EarthSciML Serialization Format, built with SolidJS and `solid-element`. These components provide interactive visualization and editing capabilities for ESM files that can be used in any web framework or vanilla HTML.

## Components Overview

### Core Components

| Component | Tag | Purpose |
|-----------|-----|---------|
| **ExpressionNode** | `<esm-expression-node>` | Interactive mathematical expression rendering |
| **ModelEditor** | `<esm-model-editor>` | Full model editing interface with validation |
| **CouplingGraph** | `<esm-coupling-graph>` | Visual component relationship graph |
| **ValidationPanel** | `<esm-validation-panel>` | Display validation errors and warnings |
| **FileSummary** | `<esm-file-summary>` | File overview and statistics |
| **SimulationControls** | `<esm-simulation-controls>` | Simulation execution controls |

## Installation & Setup

```bash
npm install esm-format
```

### Browser (ES Modules)
```html
<script type="module">
  import 'esm-format/dist/web-components.js';
</script>
```

### Node.js / Bundler
```typescript
import 'esm-format/web-components';
```

### CDN
```html
<script type="module" src="https://unpkg.com/esm-format/dist/web-components.js"></script>
```

## Component Usage

### ExpressionNode

Interactive mathematical expression rendering with click-to-edit functionality.

```html
<esm-expression-node
  expression='{"op": "+", "args": [{"op": "*", "args": ["k", "x"]}, "b"]}'
  path='["equation", 0]'
  allow-editing="true"
  is-selected="false">
</esm-expression-node>
```

**Properties:**
- `expression` (required): JSON string of the mathematical expression
- `path` (required): JSON array string representing the expression path
- `allow-editing` (optional): Enable inline editing (default: true)
- `is-selected` (optional): Whether this node is currently selected

**Events:**
- `variableHover`: Fired when hovering over a variable
- `expressionSelect`: Fired when expression is clicked
- `expressionReplace`: Fired when expression is edited

### ModelEditor

Comprehensive model editing interface with live validation and variable management.

```html
<esm-model-editor
  model='{"name": "my_model", "variables": {...}, "equations": [...]}'
  allow-editing="true"
  show-validation="true"
  validation-errors='[]'>
</esm-model-editor>
```

**Properties:**
- `model` (required): JSON string of the model to edit
- `allow-editing` (optional): Enable editing capabilities (default: true)
- `show-validation` (optional): Display validation errors (default: true)
- `validation-errors` (optional): JSON array of validation errors

**Events:**
- `modelChange`: Fired when model is modified

### CouplingGraph

Interactive visualization of component relationships and data flow.

```html
<esm-coupling-graph
  esm-file='{"components": [...], "coupling": [...]}'
  width="800"
  height="600"
  interactive="true">
</esm-coupling-graph>
```

**Properties:**
- `esm-file` (required): JSON string of the complete ESM file
- `width` (optional): Visualization width in pixels
- `height` (optional): Visualization height in pixels
- `interactive` (optional): Enable interaction (default: true)

**Events:**
- `componentSelect`: Fired when a component is selected
- `couplingEdit`: Fired when a coupling connection is edited

### ValidationPanel

Display validation results with expandable error details and filtering.

```html
<esm-validation-panel
  model='{"variables": {...}, "equations": [...]}'
  validation-errors='[{"message": "Error", "path": "...", "severity": "error"}]'
  validation-warnings='[{"message": "Warning", "severity": "warning"}]'
  show-details="true">
</esm-validation-panel>
```

**Properties:**
- `model` (required): JSON string of the model being validated
- `validation-errors` (required): JSON array of validation errors
- `validation-warnings` (optional): JSON array of validation warnings
- `auto-validate` (optional): Auto-update when model changes (default: true)
- `show-details` (optional): Show detailed error information (default: true)

**Events:**
- `errorClick`: Fired when a validation error is clicked

### FileSummary

High-level overview of ESM file structure and statistics.

```html
<esm-file-summary
  esm-file='{"components": [...], "coupling": [...], "metadata": {...}}'
  show-details="true"
  show-export-options="true">
</esm-file-summary>
```

**Properties:**
- `esm-file` (required): JSON string of the ESM file to summarize
- `show-details` (optional): Display detailed information (default: false)
- `show-export-options` (optional): Show export buttons (default: false)

**Events:**
- `componentTypeClick`: Fired when a component type is clicked
- `export`: Fired when export is requested

### SimulationControls

Control simulation execution with parameter adjustment and progress monitoring.

```html
<esm-simulation-controls
  esm-file='{"components": [...], "coupling": [...]}'
  is-running="false"
  progress="50"
  status-message="Running simulation..."
  available-backends='["julia", "python", "cpp"]'
  selected-backend="julia">
</esm-simulation-controls>
```

**Properties:**
- `esm-file` (required): JSON string of the ESM file to simulate
- `is-running` (optional): Whether simulation is currently running
- `progress` (optional): Current progress percentage (0-100)
- `status-message` (optional): Current status message
- `available-backends` (optional): JSON array of available backends
- `selected-backend` (optional): Currently selected backend
- `simulation-params` (optional): JSON string of simulation parameters

**Events:**
- `startSimulation`: Fired when simulation is started
- `stopSimulation`: Fired when simulation is stopped
- `pauseResume`: Fired when simulation is paused/resumed
- `parametersChange`: Fired when parameters are modified
- `backendChange`: Fired when backend is changed

## Framework Integration

### React

```jsx
import { useEffect, useRef } from 'react';
import 'esm-format/web-components';

function MyComponent() {
  const elementRef = useRef();

  useEffect(() => {
    const element = elementRef.current;

    const handleModelChange = (event) => {
      console.log('Model changed:', event.detail);
    };

    element.addEventListener('modelChange', handleModelChange);

    return () => {
      element.removeEventListener('modelChange', handleModelChange);
    };
  }, []);

  return (
    <esm-model-editor
      ref={elementRef}
      model={JSON.stringify(myModel)}
      allow-editing="true"
    />
  );
}
```

### Vue 3

```vue
<template>
  <esm-coupling-graph
    :esm-file="JSON.stringify(esmFile)"
    width="800"
    height="600"
    @componentSelect="handleComponentSelect"
  />
</template>

<script setup>
import { ref } from 'vue';
import 'esm-format/web-components';

const esmFile = ref({
  components: [],
  coupling: []
});

const handleComponentSelect = (event) => {
  console.log('Selected component:', event.detail.componentId);
};
</script>
```

### Angular

```typescript
// app.module.ts
import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import 'esm-format/web-components';

@NgModule({
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  // ... other config
})
export class AppModule {}
```

```html
<!-- component.html -->
<esm-validation-panel
  [model]="modelJson"
  [validation-errors]="errorsJson"
  (errorClick)="onErrorClick($event)">
</esm-validation-panel>
```

### Svelte

```svelte
<script>
  import 'esm-format/web-components';

  let simulationRunning = false;
  let progress = 0;

  function handleStartSimulation(event) {
    console.log('Starting simulation with params:', event.detail);
    simulationRunning = true;
  }
</script>

<esm-simulation-controls
  esm-file={JSON.stringify($esmFile)}
  is-running={simulationRunning}
  {progress}
  on:startSimulation={handleStartSimulation}
/>
```

## Styling & Theming

Components use CSS custom properties for theming:

```css
:root {
  /* Colors */
  --esm-primary-color: #3b82f6;
  --esm-success-color: #10b981;
  --esm-warning-color: #f59e0b;
  --esm-error-color: #ef4444;

  /* Backgrounds */
  --esm-bg-primary: white;
  --esm-bg-secondary: #f9fafb;
  --esm-hover-bg: rgba(59, 130, 246, 0.1);

  /* Text */
  --esm-text-primary: #1f2937;
  --esm-text-secondary: #6b7280;
  --esm-font-family: system-ui, sans-serif;
  --esm-font-size: 14px;

  /* Borders */
  --esm-border-color: #e5e7eb;
  --esm-border-radius: 6px;
}
```

### Dark Mode Support

```css
[data-theme="dark"] {
  --esm-bg-primary: #1f2937;
  --esm-bg-secondary: #111827;
  --esm-text-primary: #f9fafb;
  --esm-text-secondary: #d1d5db;
  --esm-border-color: #374151;
}
```

## Accessibility

All components support:
- **Keyboard Navigation**: Full keyboard accessibility with logical tab order
- **Screen Readers**: Proper ARIA labels and descriptions
- **High Contrast**: Respects `prefers-contrast: high` media query
- **Reduced Motion**: Respects `prefers-reduced-motion: reduce`
- **Focus Management**: Clear focus indicators and management

## Browser Support

- **Modern Browsers**: Chrome 61+, Firefox 63+, Safari 11+, Edge 79+
- **Polyfills**: Automatic polyfills for older browsers via solid-element
- **SSR**: Components can be pre-rendered for server-side rendering

## Performance

- **Bundle Size**: ~45KB gzipped (including SolidJS runtime)
- **Tree Shaking**: Only import components you use
- **Lazy Loading**: Components can be loaded on-demand
- **Memory**: Efficient reactive updates with minimal re-renders

## Error Handling

Components provide graceful error handling:

```html
<!-- Invalid JSON will show error state -->
<esm-model-editor model="invalid-json">
  <!-- Shows: "Component error: Unexpected token..." -->
</esm-model-editor>

<!-- Missing required attributes -->
<esm-coupling-graph>
  <!-- Shows: "Missing required attribute: esm-file" -->
</esm-coupling-graph>
```

## TypeScript Support

Full TypeScript definitions are included:

```typescript
import type {
  EsmModelEditorProps,
  EsmCouplingGraphProps,
  EsmValidationPanelProps
} from 'esm-format/web-components';
```

## Development & Testing

```bash
# Install dependencies
npm install

# Run tests
npm test

# Build components
npm run build

# Start demo server
npm run dev:demo
```

## License

MIT License - see [LICENSE](./LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

For issues and feature requests, please use the [GitHub Issues](https://github.com/EarthSciML/EarthSciSerialization/issues) page.