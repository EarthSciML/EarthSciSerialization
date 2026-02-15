/**
 * Test Setup for SolidJS Components in Vitest
 *
 * Configures the testing environment to properly handle SolidJS components
 * in a jsdom environment with proper cleanup and browser-like behavior.
 */

import '@testing-library/jest-dom'

// Configure SolidJS for testing environment
globalThis.IS_SOLID_TESTING = true;

// Mock browser APIs that SolidJS components might use
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// Mock ResizeObserver for d3-force and other components
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock SVG path methods used by d3-force
const mockPath = {
  getBBox: () => ({ width: 100, height: 50, x: 0, y: 0 }),
  getComputedTextLength: () => 100,
  getTotalLength: () => 100,
  getPointAtLength: () => ({ x: 0, y: 0 }),
};

Object.defineProperty(SVGElement.prototype, 'getBBox', {
  value: () => mockPath.getBBox(),
});

Object.defineProperty(SVGElement.prototype, 'getComputedTextLength', {
  value: () => mockPath.getComputedTextLength(),
});

Object.defineProperty(SVGElement.prototype, 'getTotalLength', {
  value: () => mockPath.getTotalLength(),
});

Object.defineProperty(SVGElement.prototype, 'getPointAtLength', {
  value: () => mockPath.getPointAtLength(),
});

// Set up proper DOM environment
Object.defineProperty(window, 'getComputedStyle', {
  value: () => ({
    getPropertyValue: () => '',
  }),
});