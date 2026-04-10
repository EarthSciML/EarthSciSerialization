import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import json from '@rollup/plugin-json';
import typescript from '@rollup/plugin-typescript';
import dts from 'rollup-plugin-dts';

const external = [
  'ajv',
  'ajv-formats',
  'd3-force',
  'solid-js',
  'solid-js/web'
];

const tsPlugin = () =>
  typescript({
    tsconfig: './tsconfig.rollup.json',
    declaration: false,
    declarationMap: false,
    sourceMap: true
  });

export default [
  // ESM Build - core functionality only (no JSX)
  {
    input: 'src/core.ts',
    output: {
      file: 'dist/esm/index.js',
      format: 'esm',
      sourcemap: true
    },
    external,
    plugins: [
      tsPlugin(),
      resolve({ preferBuiltins: true }),
      commonjs(),
      json()
    ]
  },
  // CommonJS Build - core functionality only (no JSX)
  {
    input: 'src/core.ts',
    output: {
      file: 'dist/cjs/index.js',
      format: 'cjs',
      sourcemap: true,
      exports: 'named'
    },
    external,
    plugins: [
      tsPlugin(),
      resolve({ preferBuiltins: true }),
      commonjs(),
      json()
    ]
  },
  // Bundled type declarations
  {
    input: 'src/core.ts',
    output: {
      file: 'dist/core.d.ts',
      format: 'esm'
    },
    external,
    plugins: [dts({ tsconfig: './tsconfig.rollup.json' })]
  }
];
