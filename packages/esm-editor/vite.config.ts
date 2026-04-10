import { defineConfig } from 'vite';
import solid from 'vite-plugin-solid';
import { resolve } from 'path';

export default defineConfig({
  plugins: [solid()],

  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'ESMEditor',
      fileName: 'index',
      formats: ['es']
    },
    rollupOptions: {
      external: ['solid-js', 'solid-element', 'earthsci-toolkit', 'd3-force'],
      output: {
        globals: {
          'solid-js': 'SolidJS',
          'solid-element': 'SolidElement',
          'earthsci-toolkit': 'ESMFormat',
          'd3-force': 'D3Force'
        }
      }
    }
  },

  test: {
    environment: 'jsdom',
    deps: {
      optimizer: {
        web: {
          include: ['solid-js', 'solid-element', '@solidjs/testing-library']
        }
      }
    }
  }
});