import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import json from '@rollup/plugin-json';
import dts from 'rollup-plugin-dts';
import { readFileSync } from 'fs';

const external = [
  'ajv',
  'ajv-formats',
  'd3-force',
  'solid-js',
  'solid-js/web'
];

export default [
  // ESM Build - core functionality only
  {
    input: 'dist/core.js',
    output: {
      file: 'dist/esm/index.js',
      format: 'esm',
      sourcemap: true
    },
    external,
    plugins: [
      resolve({ preferBuiltins: true }),
      commonjs(),
      json()
    ]
  },
  // CommonJS Build - core functionality only
  {
    input: 'dist/core.js',
    output: {
      file: 'dist/cjs/index.js',
      format: 'cjs',
      sourcemap: true,
      exports: 'named'
    },
    external,
    plugins: [
      resolve({ preferBuiltins: true }),
      commonjs(),
      json()
    ]
  }
];