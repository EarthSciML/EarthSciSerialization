# Interactive ESM Editor Test Fixtures

This directory contains comprehensive test fixtures for the interactive ESM editor components built with SolidJS. The tests ensure that all interactive features work correctly across different browsers and accessibility scenarios.

## Test Structure

### Component Interaction Tests (`component-interaction/`)

Tests for the core interactive behaviors of ESM editor components:

- **ExpressionNode Interactions** (`expression-node-interactions.spec.ts`)
  - Click-to-select behavior
  - Variable hover highlighting and equivalence classes
  - Drag-and-drop for structural editing
  - Real-time validation feedback
  - Undo/redo operation sequences
  - Selection state management
  - Keyboard navigation (Tab, arrow keys)

### Expression Editing Tests (`expression-editing/`)

Tests for inline expression modification and mathematical notation:

- **Inline Expression Modification** (`inline-expression-modification.spec.ts`)
  - Direct editing of numbers and variables
  - Expression palette insertion and auto-completion
  - Syntax error recovery and correction suggestions
  - Precedence-aware parenthesis insertion
  - Mathematical notation rendering (fractions, superscripts, derivatives)
  - MathML/LaTeX output verification

### Model Editing Tests (`model-editing/`)

Tests for comprehensive model editing capabilities:

- **Full Model Editing** (`full-model-editing.spec.ts`)
  - Adding/removing variables interactively
  - Creating new equations via UI
  - Reaction editor drag-and-drop functionality
  - Species property modification
  - Coupling graph manipulation
  - Cross-reference updates when variables are renamed
  - Model validation and consistency checking

### Web Components Tests (`web-components/`)

Tests for SolidJS to web component export functionality:

- **SolidJS Web Component Export** (`solidjs-web-component-export.spec.ts`)
  - Component registration and custom element definition
  - Event handling across component boundaries
  - Props/attributes validation and conversion
  - CSS styling isolation using shadow DOM
  - Performance under rapid state changes
  - Cross-browser compatibility

### Performance Benchmarks (`performance/`)

Tests to ensure responsive user experience:

- **Editor Responsiveness Benchmarks** (`editor-responsiveness-benchmarks.spec.ts`)
  - Expression rendering performance (targeting 60fps for simple expressions)
  - Interaction response times (clicks, hovers, edits)
  - Large model loading efficiency
  - Memory usage monitoring and leak detection
  - Stress testing with rapid user interactions
  - Complex expression rendering without stack overflow

### Accessibility Compliance (`accessibility/`)

Tests to ensure WCAG 2.1 AA compliance:

- **WCAG Compliance** (`wcag-compliance.spec.ts`)
  - Keyboard navigation (Tab, Shift+Tab, Enter, Space, Escape)
  - Screen reader support with proper ARIA labels
  - Visual design and contrast requirements
  - Form controls and label associations
  - Dynamic content and live regions
  - Interactive elements accessibility
  - Error prevention and recovery

## Running Tests

### Prerequisites

```bash
npm install
npm run build
```

### Run All Tests

```bash
# Unit tests (Vitest)
npm run test

# End-to-end tests (Playwright)
npm run test:e2e

# All tests
npm run test:all
```

### Run Specific Test Suites

```bash
# Accessibility tests only
npm run test:accessibility

# Performance benchmarks only
npm run test:performance

# Interactive UI for debugging tests
npm run test:e2e:ui
```

### Browser Configuration

Tests run on multiple browsers by default:
- Chromium (Desktop)
- Firefox (Desktop)
- WebKit/Safari (Desktop)
- Chrome Mobile (Pixel 5)
- Safari Mobile (iPhone 12)

## Test Data and Fixtures

### Expression Test Cases

The tests use a variety of expression types:
- Simple numbers: `42`, `3.14159`, `1e6`
- Variables: `"temperature"`, `"pressure"`, `"concentration"`
- Basic operators: `+`, `-`, `*`, `/`, `^`
- Functions: `sin`, `cos`, `log`, `exp`, `sqrt`
- Complex nested structures with multiple levels

### Model Test Data

Models include:
- Variables with different types (state, parameter, observed)
- Differential and algebraic equations
- Reaction systems with species and stoichiometry
- Coupling entries between models
- Large models (200+ variables, 50+ equations)

### Performance Targets

- Simple expression rendering: < 16ms (60fps)
- Complex expression rendering: < 50ms
- User interaction response: < 100ms
- Large model loading: < 1 second
- 100 expressions on screen: < 500ms total render time

### Accessibility Requirements

- All interactive elements must be keyboard navigable
- ARIA labels required for screen reader support
- Minimum contrast ratio compliance (WCAG AA)
- Focus indicators must be visible
- Error messages must be announced to screen readers
- Dynamic content updates must use ARIA live regions

## Demo Pages

Demo pages for manual testing are available at:
- `/demo/expression-node` - Basic ExpressionNode interactions
- `/demo/expression-editor` - Expression editing and palette
- `/demo/model-editor` - Full model editing interface
- `/demo/coupling-editor` - Coupling graph manipulation
- `/demo/performance-test` - Performance testing environment
- `/demo/accessibility-test` - Accessibility compliance testing

Start demo server:
```bash
npm run dev:demo
```

## Contributing

When adding new interactive features:

1. Add corresponding Playwright tests to the appropriate category
2. Include accessibility tests for any new interactive elements
3. Add performance benchmarks for operations that could be slow
4. Update demo pages to showcase new functionality
5. Document any new ARIA patterns or keyboard interactions

Test files should follow the naming convention:
- `*.spec.ts` for Playwright end-to-end tests
- `*.test.ts` for Vitest unit tests
- Use descriptive `data-testid` attributes for reliable element selection
- Include both positive and negative test cases
- Test edge cases and error conditions

## Troubleshooting

### Common Issues

**SolidJS SSR Errors in Vitest:**
- Ensure components use `onMount` for client-only code
- Check that `test-setup.ts` is properly configured
- Verify browser conditions in vite config

**Playwright Timeouts:**
- Increase timeout for complex operations
- Use `page.waitForSelector` for dynamic content
- Ensure demo server is running for e2e tests

**Performance Test Flakiness:**
- Run performance tests in isolation
- Consider system load when setting benchmarks
- Use consistent test data sizes

**Accessibility Test Failures:**
- Verify ARIA attributes are properly set
- Test with actual screen readers when possible
- Check keyboard navigation thoroughly