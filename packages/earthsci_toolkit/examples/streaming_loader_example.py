#!/usr/bin/env python3
"""
Example demonstrating the StreamingLoader functionality for real-time data ingestion.

This example shows how to use the StreamingLoader to handle real-time data from
various sources including WebSocket streams, HTTP streaming endpoints, message queues,
and TCP connections.
"""

import time
import json
from esm_format.types import DataLoader, DataLoaderType
from esm_format.data_loaders import StreamingLoader


def example_websocket_streaming():
    """Demonstrate WebSocket streaming data loader."""
    print("=== WebSocket Streaming Example ===")

    # Configure WebSocket streaming loader
    config = DataLoader(
        name="weather_websocket",
        type=DataLoaderType.TIMESERIES,
        source="ws://localhost:8080/weather-stream",
        format_options={
            'buffer_size': 100,
            'reconnect_attempts': 3,
            'reconnect_delay': 2.0,
            'timeout': 30.0
        }
    )

    # Create and start streaming loader
    loader = StreamingLoader(config)
    print(f"Source type detected: {loader.source_type}")

    try:
        # Start streaming (in real implementation, this would connect to actual WebSocket)
        loader.start_streaming()
        print("Streaming started")

        # Simulate receiving streaming data
        weather_data = [
            {"timestamp": "2023-12-01T12:00:00Z", "temperature": 25.5, "humidity": 60.0},
            {"timestamp": "2023-12-01T12:01:00Z", "temperature": 25.7, "humidity": 59.8},
            {"timestamp": "2023-12-01T12:02:00Z", "temperature": 25.9, "humidity": 59.5},
        ]

        for data in weather_data:
            loader.add_mock_data(data)
            print(f"Added data: {data}")

        # Get streaming status
        status = loader.get_status()
        print(f"Status: {json.dumps(status, indent=2)}")

        # Read buffered data
        buffered_data = loader.read_data(max_items=2)
        print(f"Read {len(buffered_data)} items:")
        for item in buffered_data:
            print(f"  {item}")

        # Check remaining data
        remaining = loader.read_data()
        print(f"Remaining {len(remaining)} items: {remaining}")

    finally:
        loader.close()
        print("Streaming stopped and resources cleaned up")


def example_http_streaming():
    """Demonstrate HTTP streaming data loader."""
    print("\n=== HTTP Streaming Example ===")

    # Configure HTTP streaming loader (Server-Sent Events)
    config = DataLoader(
        name="sensor_stream",
        type=DataLoaderType.TIMESERIES,
        source="https://api.example.com/sensor-stream",
        format_options={
            'buffer_size': 500,
            'timeout': 60.0
        }
    )

    loader = StreamingLoader(config)
    print(f"Source type detected: {loader.source_type}")

    try:
        loader.start_streaming()

        # Simulate sensor data stream
        sensor_readings = [
            {"sensor_id": "temp_01", "value": 22.3, "unit": "celsius"},
            {"sensor_id": "pressure_01", "value": 1013.25, "unit": "hPa"},
            {"sensor_id": "temp_01", "value": 22.5, "unit": "celsius"},
        ]

        for reading in sensor_readings:
            loader.add_mock_data(reading)

        # Demonstrate backpressure handling
        print("Testing backpressure handling...")
        original_buffer_size = loader.buffer_size
        loader.configure_backpressure(2)  # Reduce buffer size

        # Add more data to trigger backpressure
        for i in range(3):
            loader.add_mock_data({"sensor_id": f"test_{i}", "value": i})

        print(f"Buffer size after backpressure: {len(loader.buffer)} (max: {loader.buffer_size})")

        # Read all data
        all_data = loader.read_data()
        print(f"All buffered data: {all_data}")

    finally:
        loader.close()


def example_message_queue_streaming():
    """Demonstrate message queue streaming data loader."""
    print("\n=== Message Queue Streaming Example ===")

    # Configure Kafka streaming loader
    config = DataLoader(
        name="kafka_events",
        type=DataLoaderType.TIMESERIES,
        source="kafka://localhost:9092/sensor-events",
        format_options={
            'buffer_size': 1000,
            'reconnect_attempts': 10,
            'reconnect_delay': 5.0
        }
    )

    loader = StreamingLoader(config)
    print(f"Source type detected: {loader.source_type}")

    try:
        loader.start_streaming()

        # Simulate message queue events
        events = [
            {"event_type": "measurement", "device": "sensor_A", "value": 15.2},
            {"event_type": "alert", "device": "sensor_B", "message": "Temperature high"},
            {"event_type": "measurement", "device": "sensor_C", "value": 98.6},
        ]

        for event in events:
            loader.add_mock_data(event)

        # Demonstrate partial reading
        partial_data = loader.read_data(max_items=1)
        print(f"Read 1 item: {partial_data}")

        remaining_data = loader.read_data()
        print(f"Remaining items: {remaining_data}")

    finally:
        loader.close()


def example_tcp_streaming():
    """Demonstrate TCP streaming data loader."""
    print("\n=== TCP Streaming Example ===")

    # Configure TCP streaming loader
    config = DataLoader(
        name="tcp_data_feed",
        type=DataLoaderType.TIMESERIES,
        source="tcp://localhost:9999",
        format_options={
            'buffer_size': 200,
            'timeout': 30.0
        }
    )

    loader = StreamingLoader(config)
    print(f"Source type detected: {loader.source_type}")

    try:
        loader.start_streaming()

        # Simulate TCP data feed
        tcp_data = [
            {"feed_id": "market_data", "symbol": "AAPL", "price": 150.25},
            {"feed_id": "market_data", "symbol": "GOOGL", "price": 2500.50},
            {"feed_id": "news_feed", "headline": "Tech stocks rally"},
        ]

        for data in tcp_data:
            loader.add_mock_data(data)

        # Clear buffer demonstration
        initial_count = len(loader.buffer)
        cleared_count = loader.clear_buffer()

        print(f"Cleared {cleared_count} items from buffer")
        print(f"Buffer size now: {len(loader.buffer)}")

    finally:
        loader.close()


def example_connection_resilience():
    """Demonstrate connection resilience features."""
    print("\n=== Connection Resilience Example ===")

    config = DataLoader(
        name="resilient_stream",
        type=DataLoaderType.TIMESERIES,
        source="ws://unreliable-server:8080/stream",
        format_options={
            'buffer_size': 50,
            'reconnect_attempts': 5,
            'reconnect_delay': 1.0,
            'timeout': 10.0
        }
    )

    loader = StreamingLoader(config)

    try:
        loader.start_streaming()
        print(f"Configured with {loader.reconnect_attempts} reconnection attempts")
        print(f"Reconnection delay: {loader.reconnect_delay} seconds")

        # Simulate some successful data
        for i in range(5):
            loader.add_mock_data({"sequence": i, "data": f"message_{i}"})

        status = loader.get_status()
        print(f"Final status: {json.dumps(status, indent=2)}")

    finally:
        loader.close()


if __name__ == "__main__":
    print("StreamingLoader Examples")
    print("=" * 50)

    # Run all examples
    example_websocket_streaming()
    example_http_streaming()
    example_message_queue_streaming()
    example_tcp_streaming()
    example_connection_resilience()

    print("\n" + "=" * 50)
    print("All examples completed successfully!")