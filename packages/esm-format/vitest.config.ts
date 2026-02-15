import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/tests/interactive/**', // Exclude Playwright tests from Vitest
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*'
    ]
  },
  esbuild: {
    jsx: 'automatic',
    jsxImportSource: 'solid-js',
    target: 'esnext'
  },
  define: {
    'import.meta.vitest': 'undefined'
  },
  resolve: {
    conditions: ['browser', 'development']
  }
})