/**
 * Simple test script to verify migration functionality across languages
 */

import { migrate, canMigrate, getSupportedMigrationTargets } from './packages/esm-format/src/migration.js';

// Test data - simple ESM file that needs migration
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

console.log("Testing migration functionality...\n");

// Test 1: Basic migration
try {
  console.log("Test 1: Migrate from 0.0.5 to 0.1.0");
  const migrated = migrate(testFile, "0.1.0");

  console.log("✓ Migration succeeded");
  console.log(`Original version: ${testFile.esm}`);
  console.log(`Migrated version: ${migrated.esm}`);

  // Check if CH4 units were converted
  const originalCH4 = testFile.reaction_systems.TestSystem.species.CH4;
  const migratedCH4 = migrated.reaction_systems.TestSystem.species.CH4;

  console.log(`CH4 units conversion: ${originalCH4.units} (${originalCH4.default}) → ${migratedCH4.units} (${migratedCH4.default})`);

  if (migratedCH4.units === "mol/mol" && migratedCH4.default === 1.9e-6) {
    console.log("✓ Unit conversion worked correctly");
  } else {
    console.log("✗ Unit conversion failed");
  }

  // Check migration notes
  if (migrated.metadata.migration_notes && migrated.metadata.migration_notes.includes("Migrated from version 0.0.5")) {
    console.log("✓ Migration notes added");
  } else {
    console.log("✗ Migration notes missing");
  }

  console.log();
} catch (error) {
  console.log(`✗ Migration failed: ${error.message}\n`);
}

// Test 2: Check migration capability
console.log("Test 2: Check migration capabilities");
console.log(`Can migrate 0.0.5 → 0.1.0: ${canMigrate("0.0.5", "0.1.0")}`);
console.log(`Can migrate 1.0.0 → 0.1.0: ${canMigrate("1.0.0", "0.1.0")}`);
console.log(`Can migrate 0.1.0 → 0.0.5: ${canMigrate("0.1.0", "0.0.5")}`);

// Test 3: Get supported targets
console.log("\nTest 3: Supported migration targets");
console.log(`From 0.0.5: ${getSupportedMigrationTargets("0.0.5").join(", ")}`);
console.log(`From 0.1.0: ${getSupportedMigrationTargets("0.1.0").join(", ")}`);

console.log("\nMigration functionality test completed!");