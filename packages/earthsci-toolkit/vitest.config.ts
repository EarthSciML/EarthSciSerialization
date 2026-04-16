import { defineConfig } from 'vitest/config'
import solidPlugin from 'vite-plugin-solid'

export default defineConfig({
  plugins: [solidPlugin()],
  test: {
    environment: 'jsdom',
    globals: true,
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/tests/interactive/**', // Exclude Playwright tests from Vitest
      '**/interactive-editor/**', // Exclude SolidJS-dependent interactive editor tests
      '**/layout/**', // Exclude SolidJS layout components
      '**/demo/**', // Exclude SolidJS demo components
      '**/web-components.test.*', // Exclude web components tests that use SolidJS
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*'
    ]
  },
  define: {
    'import.meta.vitest': 'undefined'
  },
  resolve: {
    conditions: ['browser', 'development']
  }
})