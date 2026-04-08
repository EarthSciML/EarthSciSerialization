#!/usr/bin/env node

// Quick test to verify migration functionality works
import { migrate, canMigrate, getSupportedMigrationTargets, MigrationError } from './packages/esm-format/dist/esm/index.js';

console.log('Testing migration functionality...\n');

// Create a simple test file that needs migration
const testFile = {
    esm: "0.0.5",
    metadata: {
        name: "Test Model",
        description: "Test migration functionality"
    },
    reaction_systems: {
        TestSystem: {
            species: {
                CH4: {
                    units: "ppbv",
                    default: 1900.0,
                    description: "Methane"
                },
                CO: {
                    units: "ppmv",
                    default: 0.2,
                    description: "Carbon monoxide"
                }
            }
        }
    }
};

try {
    // Test 1: Basic migration
    console.log("Test 1: Migrate from 0.0.5 to 0.1.0");
    const migrated = migrate(testFile, "0.1.0");

    console.log("✓ Migration succeeded");
    console.log(`Original version: ${testFile.esm}`);
    console.log(`Migrated version: ${migrated.esm}`);

    // Check if CH4 units were converted
    const originalCH4 = testFile.reaction_systems.TestSystem.species.CH4;
    const migratedCH4 = migrated.reaction_systems.TestSystem.species.CH4;

    console.log(`CH4 units conversion: ${originalCH4.units} (${originalCH4.default}) → ${migratedCH4.units} (${migratedCH4.default})`);

    if (migratedCH4.units === "mol/mol" && Math.abs(migratedCH4.default - 1.9e-6) < 1e-10) {
        console.log("✓ Unit conversion worked correctly");
    } else {
        console.log("✗ Unit conversion failed");
    }

    console.log();
} catch (error) {
    console.log(`✗ Migration failed: ${error}\n`);
}

// Test 2: Check migration capability
console.log("Test 2: Check migration capabilities");
console.log(`Can migrate 0.0.5 → 0.1.0: ${canMigrate('0.0.5', '0.1.0')}`);
console.log(`Can migrate 1.0.0 → 0.1.0: ${canMigrate('1.0.0', '0.1.0')}`);
console.log(`Can migrate 0.1.0 → 0.0.5: ${canMigrate('0.1.0', '0.0.5')}`);

// Test 3: Get supported targets
console.log("\nTest 3: Supported migration targets");
console.log(`From 0.0.5: ${getSupportedMigrationTargets('0.0.5').join(', ')}`);
console.log(`From 0.1.0: ${getSupportedMigrationTargets('0.1.0').join(', ')}`);

// Test 4: Error handling
console.log("\nTest 4: Error handling");
try {
    migrate(testFile, "1.0.0");
    console.log("✗ Should have failed for major version change");
} catch (e) {
    if (e instanceof MigrationError) {
        console.log(`✓ Correctly rejected major version change: ${e.message}`);
    } else {
        console.log(`✗ Wrong error type: ${e}`);
    }
}

console.log("\nMigration functionality test completed!");