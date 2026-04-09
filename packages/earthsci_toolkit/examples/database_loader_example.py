#!/usr/bin/env python3
"""
Example demonstrating the DatabaseLoader functionality.

This example shows how to:
1. Create an SQLite database with sample atmospheric data
2. Use the DatabaseLoader to load data from the database
3. Execute custom queries and transactions
4. Work with the data loader registry for auto-detection
"""

import tempfile
import sqlite3
from pathlib import Path
from esm_format.types import DataLoader, DataLoaderType
from esm_format.data_loaders import DatabaseLoader
from esm_format.data_loader_registry import create_auto_loader, detect_loader_type


def create_sample_database():
    """Create a sample SQLite database with atmospheric chemistry data."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name

    # Connect and create schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create atmospheric chemistry measurement table
    cursor.execute("""
        CREATE TABLE measurements (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            temperature_k REAL,
            pressure_pa REAL,
            o3_ppbv REAL,
            no2_ppbv REAL,
            co_ppmv REAL,
            so2_ppbv REAL,
            pm25_ugm3 REAL
        )
    """)

    # Create species metadata table
    cursor.execute("""
        CREATE TABLE species_info (
            species_name TEXT PRIMARY KEY,
            molecular_formula TEXT,
            molecular_weight REAL,
            units TEXT,
            description TEXT
        )
    """)

    # Insert sample atmospheric measurements
    measurements_data = [
        (1, '2023-01-01T12:00:00Z', 'Seattle', 47.6062, -122.3321, 56.0, 278.15, 101325, 35.2, 18.5, 0.15, 2.1, 12.4),
        (2, '2023-01-01T13:00:00Z', 'Seattle', 47.6062, -122.3321, 56.0, 279.05, 101318, 36.8, 17.2, 0.14, 2.3, 13.1),
        (3, '2023-01-01T14:00:00Z', 'Seattle', 47.6062, -122.3321, 56.0, 280.12, 101310, 38.1, 16.9, 0.13, 2.0, 11.8),
        (4, '2023-01-01T12:00:00Z', 'Los Angeles', 34.0522, -118.2437, 71.0, 295.15, 101200, 85.6, 45.2, 0.89, 8.7, 35.2),
        (5, '2023-01-01T13:00:00Z', 'Los Angeles', 34.0522, -118.2437, 71.0, 296.85, 101195, 89.3, 47.8, 0.92, 9.1, 38.5),
        (6, '2023-01-01T14:00:00Z', 'Los Angeles', 34.0522, -118.2437, 71.0, 298.22, 101188, 91.7, 49.1, 0.95, 9.4, 40.1),
    ]

    cursor.executemany("""
        INSERT INTO measurements
        (id, timestamp, location, latitude, longitude, altitude_m, temperature_k, pressure_pa, o3_ppbv, no2_ppbv, co_ppmv, so2_ppbv, pm25_ugm3)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, measurements_data)

    # Insert species information
    species_data = [
        ('O3', 'O3', 48.0, 'ppbv', 'Ozone - ground-level pollutant and greenhouse gas'),
        ('NO2', 'NO2', 46.0055, 'ppbv', 'Nitrogen dioxide - traffic-related pollutant'),
        ('CO', 'CO', 28.01, 'ppmv', 'Carbon monoxide - incomplete combustion product'),
        ('SO2', 'SO2', 64.066, 'ppbv', 'Sulfur dioxide - industrial pollutant'),
        ('PM25', 'N/A', None, 'μg/m³', 'Fine particulate matter (≤2.5 μm diameter)'),
    ]

    cursor.executemany("""
        INSERT INTO species_info (species_name, molecular_formula, molecular_weight, units, description)
        VALUES (?, ?, ?, ?, ?)
    """, species_data)

    conn.commit()
    conn.close()

    return db_path


def example_basic_loading():
    """Demonstrate basic database loading functionality."""
    print("=== Basic Database Loading Example ===")

    # Create sample database
    db_path = create_sample_database()
    print(f"Created sample database: {db_path}")

    try:
        # Create database loader configuration
        config = DataLoader(
            name="atmospheric_measurements",
            type=DataLoaderType.STATIC,
            source=db_path,
            format_options={
                "table": "measurements",
                "order_by": "timestamp",
            },
            variables=["timestamp", "location", "temperature_k", "o3_ppbv", "no2_ppbv"]
        )

        # Create and use the loader
        loader = DatabaseLoader(config)
        data = loader.load()

        print(f"Loaded {len(data)} records")
        print("\nFirst few records:")
        for i, record in enumerate(data[:3]):
            print(f"  {i+1}: {record}")

        # Get table information
        table_info = loader.get_table_info("measurements")
        print(f"\nTable 'measurements' has {table_info['measurements']['row_count']} rows")
        print(f"Columns: {[col['name'] for col in table_info['measurements']['columns']]}")

        loader.close()

    finally:
        # Clean up
        Path(db_path).unlink()

    print()


def example_custom_queries():
    """Demonstrate custom query execution."""
    print("=== Custom Query Example ===")

    db_path = create_sample_database()
    print(f"Using database: {db_path}")

    try:
        # Create loader with custom query
        config = DataLoader(
            name="high_pollution_data",
            type=DataLoaderType.STATIC,
            source=f"sqlite://{db_path}",  # Using URL format
            format_options={
                "query": """
                    SELECT
                        m.location,
                        m.timestamp,
                        m.o3_ppbv,
                        m.no2_ppbv,
                        m.pm25_ugm3,
                        s1.description as o3_description,
                        s2.description as no2_description
                    FROM measurements m
                    LEFT JOIN species_info s1 ON s1.species_name = 'O3'
                    LEFT JOIN species_info s2 ON s2.species_name = 'NO2'
                    WHERE m.o3_ppbv > 50 OR m.no2_ppbv > 30 OR m.pm25_ugm3 > 20
                    ORDER BY m.o3_ppbv DESC
                """
            }
        )

        loader = DatabaseLoader(config)
        data = loader.load()

        print(f"Found {len(data)} high pollution measurements")
        print("\nHigh pollution records:")
        for record in data:
            print(f"  {record['location']} at {record['timestamp']}: O3={record['o3_ppbv']:.1f}ppbv, NO2={record['no2_ppbv']:.1f}ppbv, PM2.5={record['pm25_ugm3']:.1f}μg/m³")

        # Execute custom parameterized query
        results = loader.execute_query(
            "SELECT location, AVG(o3_ppbv) as avg_o3, MAX(pm25_ugm3) as max_pm25 FROM measurements WHERE location = ? GROUP BY location",
            ["Los Angeles"]
        )

        print(f"\nLos Angeles averages:")
        for result in results:
            print(f"  Average O3: {result['avg_o3']:.1f} ppbv")
            print(f"  Max PM2.5: {result['max_pm25']:.1f} μg/m³")

        loader.close()

    finally:
        Path(db_path).unlink()

    print()


def example_transactions():
    """Demonstrate transaction handling."""
    print("=== Transaction Handling Example ===")

    db_path = create_sample_database()
    print(f"Using database: {db_path}")

    try:
        config = DataLoader(
            name="transaction_demo",
            type=DataLoaderType.STATIC,
            source=db_path,
            format_options={"table": "measurements"}
        )

        loader = DatabaseLoader(config)

        # Check initial count
        initial_count = loader.execute_query("SELECT COUNT(*) as count FROM measurements")[0]['count']
        print(f"Initial record count: {initial_count}")

        # Demonstrate transaction rollback
        print("\n--- Testing Transaction Rollback ---")
        loader.begin_transaction()

        # Insert test record
        loader.execute_transaction_query(
            """INSERT INTO measurements
               (timestamp, location, latitude, longitude, altitude_m, temperature_k, pressure_pa, o3_ppbv, no2_ppbv, co_ppmv, so2_ppbv, pm25_ugm3)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ['2023-01-01T15:00:00Z', 'Denver', 39.7392, -104.9903, 1609.0, 285.15, 83400, 42.1, 22.3, 0.18, 3.2, 15.7]
        )

        # Check count in transaction
        tx_count = loader.execute_transaction_query("SELECT COUNT(*) as count FROM measurements")[0]['count']
        print(f"Count within transaction: {tx_count}")

        # Rollback transaction
        loader.rollback_transaction()

        # Check count after rollback
        final_count = loader.execute_query("SELECT COUNT(*) as count FROM measurements")[0]['count']
        print(f"Count after rollback: {final_count}")

        # Demonstrate transaction commit
        print("\n--- Testing Transaction Commit ---")
        loader.begin_transaction()

        # Insert test record
        loader.execute_transaction_query(
            """INSERT INTO measurements
               (timestamp, location, latitude, longitude, altitude_m, temperature_k, pressure_pa, o3_ppbv, no2_ppbv, co_ppmv, so2_ppbv, pm25_ugm3)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ['2023-01-01T15:00:00Z', 'Denver', 39.7392, -104.9903, 1609.0, 285.15, 83400, 42.1, 22.3, 0.18, 3.2, 15.7]
        )

        # Commit transaction
        loader.commit_transaction()

        # Check final count
        committed_count = loader.execute_query("SELECT COUNT(*) as count FROM measurements")[0]['count']
        print(f"Count after commit: {committed_count}")

        loader.close()

    finally:
        Path(db_path).unlink()

    print()


def example_registry_integration():
    """Demonstrate integration with the data loader registry."""
    print("=== Registry Integration Example ===")

    db_path = create_sample_database()
    print(f"Using database: {db_path}")

    try:
        # Auto-detect loader type
        detected_type = detect_loader_type(db_path)
        print(f"Auto-detected loader type: {detected_type}")

        # Create auto-loader
        auto_loader = create_auto_loader(
            name="auto_atmospheric_data",
            source=db_path,
            format_options={
                "table": "species_info"
            },
            variables=["species_name", "molecular_formula", "description"]
        )

        print(f"Created auto-loader: {type(auto_loader).__name__}")

        # Load data using auto-loader
        species_data = auto_loader.load()
        print(f"\nLoaded {len(species_data)} species records:")
        for species in species_data:
            print(f"  {species['species_name']} ({species['molecular_formula']}): {species['description']}")

        auto_loader.close()

    finally:
        Path(db_path).unlink()

    print()


def main():
    """Run all database loader examples."""
    print("Database Loader Example Demonstrations")
    print("=" * 50)

    example_basic_loading()
    example_custom_queries()
    example_transactions()
    example_registry_integration()

    print("All examples completed successfully!")


if __name__ == "__main__":
    main()