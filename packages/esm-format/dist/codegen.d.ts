/**
 * Code generation for the ESM format
 *
 * This module provides functions to generate self-contained scripts
 * from ESM files in multiple target languages:
 * - Julia: compatible with ModelingToolkit, Catalyst, EarthSciMLBase, and OrdinaryDiffEq
 * - Python: compatible with SymPy, earthsci_toolkit, and SciPy
 */
import type { EsmFile } from './types.js';
/**
 * Generate a self-contained Julia script from an ESM file
 * @param file ESM file to generate Julia code for
 * @returns Julia script as a string
 */
export declare function toJuliaCode(file: EsmFile): string;
/**
 * Generate a self-contained Python script from an ESM file
 * @param file ESM file to generate Python code for
 * @returns Python script as a string
 */
export declare function toPythonCode(file: EsmFile): string;
