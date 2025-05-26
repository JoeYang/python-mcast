# Multicast Producer and Listener

This project implements a multicast producer and listener in Python, supporting both JSON and binary message formats. The implementation includes precise timestamping for latency measurements and comprehensive test coverage.

## Features

- Support for both JSON and binary message formats
- Precise nanosecond-level timestamping for latency measurements
- Detailed timing statistics for message processing
- Comprehensive test coverage
- Configurable multicast group and port

## Requirements

- Python 3.6+
- Required packages (install via `pip install -r requirements.txt`):
  - pytest
  - black
  - flake8

## Usage

### Running the Listener

The listener can be started with either JSON (default) or binary format:

```bash
# JSON format (default)
python src/multicast_listener.py 239.0.0.1 12345

# Binary format
python src/multicast_listener.py 239.0.0.1 12345 --format binary
```

### Running the Producer

The producer can be started with either JSON (default) or binary format:

```bash
# JSON format (default)
python src/multicast_producer.py 239.0.0.1 12345

# Binary format
python src/multicast_producer.py 239.0.0.1 12345 --format binary
```

### Additional Options

Both scripts support additional command-line options:

```bash
# Producer options
python src/multicast_producer.py 239.0.0.1 12345 --interval 0.5 --ttl 2 --format binary

# Listener options
python src/multicast_listener.py 239.0.0.1 12345 --format binary
```

Options:
- `--interval`: Time between messages in seconds (producer only, default: 1.0)
- `--ttl`: Time-to-live for multicast packets (producer only, default: 1)
- `--format`: Message format, either 'json' or 'binary' (default: json)

## Message Format

### JSON Format
```json
{
    "timestamp": "2024-03-14T12:00:00.000000",
    "send_time": 1234567890,
    "counter": 42,
    "data": {
        "temperature": 25.5,
        "humidity": 60.0,
        "status": "active"
    }
}
```

### Binary Format
The binary format uses Python's struct module with the following layout:
- 8 bytes: timestamp (unsigned long long)
- 4 bytes: counter (unsigned int)
- 4 bytes: temperature (float)
- 4 bytes: humidity (float)
- 1 byte: status (unsigned char)
Total size: 21 bytes

## Running Tests

Run the test suite using pytest:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_multicast_producer.py

# Run specific test
pytest tests/test_multicast_producer.py::test_encode_binary_message
```

## Performance

The binary format offers several advantages over JSON:
- Fixed-size fields (21 bytes vs ~200-300 bytes for JSON)
- No string encoding/decoding
- Direct binary representation of numbers
- Simpler parsing

The listener provides detailed timing information for:
- Network receive time
- Message decoding time
- JSON parsing time (for JSON format)
- End-to-end latency
- Statistical analysis of latencies 