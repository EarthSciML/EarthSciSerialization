"""
Tests for database data loader functionality.
"""

import pytest
import tempfile
import sqlite3
import os
from pathlib import Path

# Import the database loading functionality
from esm_format.data_loaders import DatabaseLoader
from esm_format.types import DataLoader, DataLoaderType


@pytest.fixture
def sample_sqlite_db():
    """Create a sample SQLite database for testing."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name

    # Create database schema and sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE climate_data (
            id INTEGER PRIMARY KEY,
            station_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            location TEXT,
            elevation REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE stations (
            station_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            country TEXT
        )
    """)

    # Insert sample data
    climate_data = [
        (1, 'ST001', '2023-01-01T00:00:00', 15.5, 65.2, 1013.25, 'Seattle', 56.0),
        (2, 'ST001', '2023-01-01T01:00:00', 15.2, 66.1, 1013.15, 'Seattle', 56.0),
        (3, 'ST001', '2023-01-01T02:00:00', 14.8, 67.0, 1013.05, 'Seattle', 56.0),
        (4, 'ST002', '2023-01-01T00:00:00', 22.1, 45.3, 1015.80, 'Phoenix', 331.0),
        (5, 'ST002', '2023-01-01T01:00:00', 21.9, 44.8, 1015.75, 'Phoenix', 331.0),
        (6, 'ST003', '2023-01-01T00:00:00', -5.2, 78.5, 1020.45, 'Anchorage', 40.0),
    ]

    cursor.executemany("""
        INSERT INTO climate_data
        (id, station_id, timestamp, temperature, humidity, pressure, location, elevation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, climate_data)

    stations_data = [
        ('ST001', 'Seattle Weather Station', 47.6062, -122.3321, 'USA'),
        ('ST002', 'Phoenix Weather Station', 33.4484, -112.0740, 'USA'),
        ('ST003', 'Anchorage Weather Station', 61.2181, -149.9003, 'USA'),
    ]

    cursor.executemany("""
        INSERT INTO stations (station_id, name, latitude, longitude, country)
        VALUES (?, ?, ?, ?, ?)
    """, stations_data)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_sqlite_data_loader_config(sample_sqlite_db):
    """Create a sample SQLite DataLoader configuration."""
    return DataLoader(
        name="test_climate_db",
        type=DataLoaderType.DATABASE,
        source=sample_sqlite_db,
        format_options={
            "table": "climate_data",
            "timeout": 10.0
        },
        variables=["station_id", "timestamp", "temperature", "humidity", "pressure"]
    )


@pytest.fixture
def sample_sqlite_url_config(sample_sqlite_db):
    """Create a sample SQLite DataLoader configuration with URL format."""
    return DataLoader(
        name="test_climate_db_url",
        type=DataLoaderType.DATABASE,
        source=f"sqlite://{sample_sqlite_db}",
        format_options={"query": "SELECT * FROM climate_data WHERE temperature > 15.0"}
    )


class TestDatabaseLoaderSQLite:
    """Tests for SQLite database loader."""

    def test_database_loader_initialization(self, sample_sqlite_data_loader_config):
        """Test database loader initialization with SQLite."""
        loader = DatabaseLoader(sample_sqlite_data_loader_config)
        assert loader.config == sample_sqlite_data_loader_config
        assert loader.db_type == 'sqlite'
        assert loader.data is None
        loader.close()

    def test_database_loader_wrong_type(self):
        """Test database loader with wrong data loader type."""
        wrong_config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,  # Wrong type
            source="test.db"
        )

        with pytest.raises(ValueError, match="Expected DataLoaderType.DATABASE"):
            DatabaseLoader(wrong_config)

    def test_connection_string_parsing_sqlite_file(self, sample_sqlite_db):
        """Test parsing SQLite file path connection strings."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source=sample_sqlite_db
        )

        loader = DatabaseLoader(config)
        assert loader.db_type == 'sqlite'
        assert loader.db_path == sample_sqlite_db
        loader.close()

    def test_connection_string_parsing_sqlite_url(self, sample_sqlite_db):
        """Test parsing SQLite URL connection strings."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source=f"sqlite://{sample_sqlite_db}"
        )

        loader = DatabaseLoader(config)
        assert loader.db_type == 'sqlite'
        assert loader.db_path == sample_sqlite_db
        loader.close()

    def test_load_nonexistent_database(self):
        """Test loading from a database that doesn't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source="/nonexistent/path/database.db"
        )

        with pytest.raises(OSError, match="Cannot connect to SQLite database"):
            DatabaseLoader(config)

    def test_load_with_table_specification(self, sample_sqlite_data_loader_config):
        """Test loading data by specifying a table name."""
        loader = DatabaseLoader(sample_sqlite_data_loader_config)
        data = loader.load()

        # Check that data was loaded
        assert loader.data is not None
        assert data is not None
        assert isinstance(data, list)
        assert len(data) == 6  # Should have 6 records

        # Check expected columns are present
        first_record = data[0]
        assert "station_id" in first_record
        assert "timestamp" in first_record
        assert "temperature" in first_record
        assert "humidity" in first_record
        assert "pressure" in first_record

        # Check data values
        assert first_record["station_id"] == "ST001"
        assert first_record["temperature"] == 15.5

        loader.close()

    def test_load_with_custom_query(self, sample_sqlite_url_config):
        """Test loading data with a custom SQL query."""
        loader = DatabaseLoader(sample_sqlite_url_config)
        data = loader.load()

        # Should only get records where temperature > 15.0
        assert len(data) > 0
        assert all(record["temperature"] > 15.0 for record in data)

        # Should have Seattle and Phoenix data, but not Anchorage
        station_ids = {record["station_id"] for record in data}
        assert "ST001" in station_ids  # Seattle
        assert "ST002" in station_ids  # Phoenix
        assert "ST003" not in station_ids  # Anchorage (too cold)

        loader.close()

    def test_load_with_variable_filtering(self, sample_sqlite_db):
        """Test loading with specific variables only."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source=sample_sqlite_db,
            format_options={"table": "climate_data"},
            variables=["station_id", "temperature"]
        )

        loader = DatabaseLoader(config)
        data = loader.load()

        # Should only have requested columns
        first_record = data[0]
        assert "station_id" in first_record
        assert "temperature" in first_record
        assert "humidity" not in first_record
        assert "pressure" not in first_record
        assert "timestamp" not in first_record

        loader.close()

    def test_load_with_missing_variables(self, sample_sqlite_db):
        """Test loading with variables that don't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source=sample_sqlite_db,
            format_options={"table": "climate_data"},
            variables=["nonexistent_column"]
        )

        loader = DatabaseLoader(config)
        with pytest.raises(ValueError, match="Requested variables not found"):
            loader.load()

        loader.close()

    def test_load_with_where_clause(self, sample_sqlite_db):
        """Test loading with WHERE clause in format options."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source=sample_sqlite_db,
            format_options={
                "table": "climate_data",
                "where": "station_id = 'ST001'",
                "order_by": "timestamp",
                "limit": 2
            }
        )

        loader = DatabaseLoader(config)
        data = loader.load()

        # Should only have ST001 data, limited to 2 records
        assert len(data) == 2
        assert all(record["station_id"] == "ST001" for record in data)

        # Should be ordered by timestamp
        assert data[0]["timestamp"] <= data[1]["timestamp"]

        loader.close()

    def test_execute_custom_query(self, sample_sqlite_data_loader_config):
        """Test executing custom queries."""
        loader = DatabaseLoader(sample_sqlite_data_loader_config)

        # Test SELECT query
        results = loader.execute_query("SELECT COUNT(*) as total FROM climate_data")
        assert len(results) == 1
        assert results[0]["total"] == 6

        # Test parameterized query
        results = loader.execute_query(
            "SELECT * FROM climate_data WHERE station_id = ? AND temperature > ?",
            ["ST001", 15.0]
        )
        assert len(results) == 2  # ST001 records with temp > 15.0

        loader.close()

    def test_get_table_info(self, sample_sqlite_data_loader_config):
        """Test getting table structure information."""
        loader = DatabaseLoader(sample_sqlite_data_loader_config)

        # Get info for specific table
        table_info = loader.get_table_info("climate_data")
        assert "climate_data" in table_info

        climate_table = table_info["climate_data"]
        assert "columns" in climate_table
        assert "row_count" in climate_table
        assert climate_table["row_count"] == 6

        # Check column information
        columns = climate_table["columns"]
        column_names = [col["name"] for col in columns]
        assert "id" in column_names
        assert "station_id" in column_names
        assert "temperature" in column_names

        # Get info for all tables
        all_tables_info = loader.get_table_info()
        assert "climate_data" in all_tables_info
        assert "stations" in all_tables_info

        loader.close()

    def test_transaction_handling(self, sample_sqlite_data_loader_config):
        """Test database transaction support."""
        loader = DatabaseLoader(sample_sqlite_data_loader_config)

        # Begin transaction
        loader.begin_transaction()

        # Insert new record in transaction
        loader.execute_transaction_query(
            "INSERT INTO climate_data (station_id, timestamp, temperature) VALUES (?, ?, ?)",
            ["ST999", "2023-01-01T12:00:00", 25.0]
        )

        # Check record exists in transaction
        results = loader.execute_transaction_query(
            "SELECT COUNT(*) as count FROM climate_data WHERE station_id = ?",
            ["ST999"]
        )
        assert results[0]["count"] == 1

        # Rollback transaction
        loader.rollback_transaction()

        # Check record doesn't exist after rollback
        results = loader.execute_query(
            "SELECT COUNT(*) as count FROM climate_data WHERE station_id = ?",
            ["ST999"]
        )
        assert results[0]["count"] == 0

        loader.close()

    def test_transaction_commit(self, sample_sqlite_data_loader_config):
        """Test committing database transactions."""
        loader = DatabaseLoader(sample_sqlite_data_loader_config)

        # Begin transaction
        loader.begin_transaction()

        # Insert new record
        loader.execute_transaction_query(
            "INSERT INTO climate_data (station_id, timestamp, temperature) VALUES (?, ?, ?)",
            ["ST888", "2023-01-01T12:00:00", 30.0]
        )

        # Commit transaction
        loader.commit_transaction()

        # Check record persists after commit
        results = loader.execute_query(
            "SELECT COUNT(*) as count FROM climate_data WHERE station_id = ?",
            ["ST888"]
        )
        assert results[0]["count"] == 1

        loader.close()

    def test_no_query_or_table_specified(self, sample_sqlite_db):
        """Test error when neither query nor table is specified."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source=sample_sqlite_db,
            format_options={}  # No query or table
        )

        loader = DatabaseLoader(config)
        with pytest.raises(ValueError, match="Either 'query' or 'table' must be specified"):
            loader.load()

        loader.close()

    def test_close_cleanup(self, sample_sqlite_data_loader_config):
        """Test that close() properly cleans up resources."""
        loader = DatabaseLoader(sample_sqlite_data_loader_config)
        loader.load()

        assert loader.data is not None

        loader.close()
        assert loader.data is None


class TestDatabaseLoaderPostgreSQL:
    """Tests for PostgreSQL database loader (mock-based since we may not have a real PostgreSQL instance)."""

    def test_postgresql_connection_parsing(self):
        """Test parsing PostgreSQL connection strings."""
        # Mock the PostgreSQL availability
        import esm_format.data_loaders
        original_available = esm_format.data_loaders.POSTGRESQL_AVAILABLE
        esm_format.data_loaders.POSTGRESQL_AVAILABLE = True

        try:
            config = DataLoader(
                name="test",
                type=DataLoaderType.DATABASE,
                source="postgresql://user:pass@localhost:5432/testdb"
            )

            # This will fail at connection time, but we can test the parsing
            with pytest.raises(OSError, match="Cannot create PostgreSQL connection pool"):
                loader = DatabaseLoader(config)

        finally:
            # Restore original availability
            esm_format.data_loaders.POSTGRESQL_AVAILABLE = original_available

    def test_postgresql_import_error(self):
        """Test proper error when psycopg2 is not available."""
        import esm_format.data_loaders

        config = DataLoader(
            name="test",
            type=DataLoaderType.DATABASE,
            source="postgresql://user:pass@localhost:5432/testdb"
        )

        # This should raise ImportError if psycopg2 is not available
        if not esm_format.data_loaders.POSTGRESQL_AVAILABLE:
            with pytest.raises(ImportError, match="psycopg2 is required for PostgreSQL"):
                DatabaseLoader(config)


class TestDatabaseLoaderFactory:
    """Tests for database loader integration with the factory system."""

    def test_create_database_loader(self, sample_sqlite_data_loader_config):
        """Test creating database loader through factory."""
        from esm_format.data_loaders import create_data_loader

        loader = create_data_loader(sample_sqlite_data_loader_config)
        assert isinstance(loader, DatabaseLoader)
        assert loader.config == sample_sqlite_data_loader_config
        loader.close()

    def test_database_loader_registry_integration(self, sample_sqlite_db):
        """Test database loader integration with registry."""
        from esm_format.data_loader_registry import detect_loader_type, create_auto_loader

        # Test auto-detection by file extension
        detected_type = detect_loader_type(sample_sqlite_db)
        assert detected_type == DataLoaderType.DATABASE

        # Test auto-loader creation
        loader = create_auto_loader(
            name="auto_db",
            source=sample_sqlite_db,
            format_options={"table": "climate_data"}
        )
        assert isinstance(loader, DatabaseLoader)
        loader.close()