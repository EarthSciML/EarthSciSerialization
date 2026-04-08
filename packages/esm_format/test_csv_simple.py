#!/usr/bin/env python3
"""Simple test to understand CSV integration issue."""

import sys
sys.path.insert(0, 'src')

print("Testing step 1: Direct import of CSV module")
try:
    from esm_format.csv_loader import CSVLoader, load_csv_data, CSVValidationError
    print("✓ Direct CSV import successful")
except Exception as e:
    print(f"❌ Direct CSV import failed: {e}")
    sys.exit(1)

print("\nTesting step 2: Import esm_types")
try:
    from esm_format.esm_types import DataLoader, DataLoaderType
    print("✓ esm_types import successful")
except Exception as e:
    print(f"❌ esm_types import failed: {e}")
    sys.exit(1)

print("\nTesting step 3: Test CSV functionality")
try:
    import tempfile
    csv_content = "time,value\n0.0,1.5\n1.0,2.5"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_csv = f.name

    data_loader = DataLoader(
        name="test",
        type=DataLoaderType.STATIC,
        source=temp_csv,
        variables=['time', 'value']
    )

    df = load_csv_data(data_loader)
    print(f"✓ CSV loading successful: {df.shape}")

    import os
    os.unlink(temp_csv)
except Exception as e:
    print(f"❌ CSV functionality test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nTesting step 4: Full esm_format import")
try:
    from esm_format import CSVLoader, CSVValidationError, load_csv_data
    print("✓ Full esm_format CSV import successful")
except ImportError as e:
    print(f"❌ Full esm_format CSV import failed: {e}")
    print("This indicates the CSV components are not properly exported from the main package")
except Exception as e:
    print(f"❌ Full esm_format CSV import failed with other error: {e}")
    import traceback
    traceback.print_exc()

print("\nAll tests completed!")
