import { validateSchema, load, SchemaValidationError } from './src/index.js'

const wrongVersion = {
  esm: "0.2.0", // Wrong version
  metadata: { name: "test" },
  models: {
    "test": {
      variables: {},
      equations: []
    }
  }
}

console.log('Testing validateSchema first:')
const errors = validateSchema(wrongVersion)
console.log('Errors found:', errors.length)

const versionError = errors.find(error =>
  error.keyword === 'const' && error.path.includes('esm')
)
console.log('Version error found:', !!versionError)
console.log('Version error:', versionError)

console.log('\nTesting load function:')
try {
  const result = load(wrongVersion)
  console.log('Load SUCCESS - no exception thrown')
  console.log('Result esm version:', result.esm)
} catch (error) {
  console.log('Load FAILED with error:', error.constructor.name)
  console.log('Error message:', error.message)
  console.log('Is SchemaValidationError:', error instanceof SchemaValidationError)
}