#!/usr/bin/env node

// Test script to identify TypeScript code generation issues
const { toJuliaCode, toPythonCode } = require('./packages/esm-format/dist/cjs/index.js');

// Create a test ESM file that exercises units, defaults, and expression mapping
const testFile = {
  esm: '0.1.0',
  metadata: {
    title: 'Code Generation Test',
    description: 'Testing units, defaults, and expression mapping'
  },
  models: {
    atmospheric: {
      variables: {
        O3: {
          name: 'O3',
          type: 'state',
          default: 50.0,
          units: 'ppb',  // Test units
          unit: 'ppb'    // Test both property names
        },
        NO: {
          name: 'NO',
          type: 'state',
          default: 10.0,
          unit: 'ppb'
        },
        k1: {
          name: 'k1',
          type: 'parameter',
          default: 1e-3,
          units: 's^-1'
        }
      },
      equations: [
        {
          lhs: { op: 'D', args: ['O3'], wrt: 't' },
          rhs: { op: '*', args: ['k1', 'O3'] }
        },
        {
          lhs: { op: 'D', args: ['NO'], wrt: 't' },
          rhs: { op: '+', args: [
            { op: '*', args: ['k1', 'O3'] },
            { op: 'grad', args: ['NO', 'x'] }  // Test grad expression mapping
          ]}
        }
      ]
    }
  },
  reaction_systems: {
    chemistry: {
      species: {
        O3: { name: 'O3', initial_value: 4e-8 },
        NO2: { name: 'NO2', initial_value: 1e-9, default: 2e-9 }
      },
      reactions: {
        r1: {
          substrates: [{ species: 'O3', stoichiometry: 1 }],
          products: [{ species: 'NO2', stoichiometry: 1 }],
          rate: { op: 'exp', args: [{ op: '/', args: ['-E_a', 'R_T'] }] }
        }
      }
    }
  }
};

console.log('='.repeat(60));
console.log('JULIA CODE GENERATION:');
console.log('='.repeat(60));
try {
  const juliaCode = toJuliaCode(testFile);
  console.log(juliaCode);
} catch (e) {
  console.error('Julia code generation failed:', e.message);
  console.error(e.stack);
}

console.log('\n' + '='.repeat(60));
console.log('PYTHON CODE GENERATION:');
console.log('='.repeat(60));
try {
  const pythonCode = toPythonCode(testFile);
  console.log(pythonCode);
} catch (e) {
  console.error('Python code generation failed:', e.message);
  console.error(e.stack);
}

console.log('\n' + '='.repeat(60));
console.log('ANALYSIS:');
console.log('='.repeat(60));

// Test for specific issues mentioned in the task
try {
  const juliaCode = toJuliaCode(testFile);
  const pythonCode = toPythonCode(testFile);

  console.log('Julia units handling:', juliaCode.includes('ppb') ? '✓ GOOD' : '✗ MISSING');
  console.log('Julia defaults handling:', juliaCode.includes('50.0') && juliaCode.includes('0.001') ? '✓ GOOD' : '✗ MISSING');
  console.log('Julia grad mapping:', juliaCode.includes('Differential(x)(NO)') ? '✓ GOOD' : '✗ MISSING');

  console.log('\nPython units handling:', pythonCode.includes('ppb') ? '✓ GOOD' : '✗ MISSING');
  console.log('Python defaults handling:', pythonCode.includes('50.0') && pythonCode.includes('0.001') ? '✓ GOOD' : '✗ MISSING');
  console.log('Python grad mapping:', pythonCode.includes('sp.Derivative(NO, x)') ? '✓ GOOD' : '✗ MISSING');

} catch (e) {
  console.error('Analysis failed:', e.message);
}