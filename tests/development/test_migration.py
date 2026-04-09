#!/usr/bin/env python3
"""
Simple test script to verify migration functionality
"""

import sys
import os

# Add the Python package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/earthsci_toolkit/src'))

try:
    from earthsci_toolkit import migrate, can_migrate, get_supported_migration_targets, MigrationError
    from earthsci_toolkit.esm_types import EsmFile, Metadata, Species, ReactionSystem

    print("Testing migration functionality...\n")

    # Create a simple test file that needs migration
    metadata = Metadata(title="Test Model", description="Test migration functionality")

    # Create species for testing
    ch4_species = Species(units="ppbv", default=1900.0, description="Methane")
    co_species = Species(units="ppmv", default=0.2, description="Carbon monoxide")

    # Create reaction system
    test_system = ReactionSystem(
        species={"CH4": ch4_species, "CO": co_species}
    )

    # Create the ESM file
    test_file = EsmFile(
        esm="0.0.5",
        metadata=metadata,
        reaction_systems={"TestSystem": test_system}
    )

    # Test 1: Basic migration
    try:
        print("Test 1: Migrate from 0.0.5 to 0.1.0")
        migrated = migrate(test_file, "0.1.0")

        print("✓ Migration succeeded")
        print(f"Original version: {test_file.esm}")
        print(f"Migrated version: {migrated.esm}")

        # Check if CH4 units were converted
        original_ch4 = test_file.reaction_systems["TestSystem"].species["CH4"]
        migrated_ch4 = migrated.reaction_systems["TestSystem"].species["CH4"]

        print(f"CH4 units conversion: {original_ch4.units} ({original_ch4.default}) → {migrated_ch4.units} ({migrated_ch4.default})")

        if migrated_ch4.units == "mol/mol" and abs(migrated_ch4.default - 1.9e-6) < 1e-10:
            print("✓ Unit conversion worked correctly")
        else:
            print("✗ Unit conversion failed")

        # Check migration notes
        if hasattr(migrated.metadata, 'migration_notes') and "Migrated from version 0.0.5" in str(migrated.metadata.migration_notes):
            print("✓ Migration notes added")
        elif "Migration notes: Migrated from version 0.0.5" in migrated.metadata.description:
            print("✓ Migration notes added to description")
        else:
            print("✗ Migration notes missing")

        print()
    except Exception as error:
        print(f"✗ Migration failed: {error}\n")

    # Test 2: Check migration capability
    print("Test 2: Check migration capabilities")
    print(f"Can migrate 0.0.5 → 0.1.0: {can_migrate('0.0.5', '0.1.0')}")
    print(f"Can migrate 1.0.0 → 0.1.0: {can_migrate('1.0.0', '0.1.0')}")
    print(f"Can migrate 0.1.0 → 0.0.5: {can_migrate('0.1.0', '0.0.5')}")

    # Test 3: Get supported targets
    print("\nTest 3: Supported migration targets")
    print(f"From 0.0.5: {', '.join(get_supported_migration_targets('0.0.5'))}")
    print(f"From 0.1.0: {', '.join(get_supported_migration_targets('0.1.0'))}")

    # Test 4: Error handling
    print("\nTest 4: Error handling")
    try:
        migrate(test_file, "1.0.0")
        print("✗ Should have failed for major version change")
    except MigrationError as e:
        print(f"✓ Correctly rejected major version change: {e}")

    print("\nMigration functionality test completed!")

except ImportError as e:
    print(f"Failed to import migration functions: {e}")
    print("Make sure the ESM format package is properly installed.")