"""
Tests for the multicast listener.
"""
import socket
import pytest
import struct
from src.multicast_listener import create_multicast_socket, decode_binary_message


def test_create_multicast_socket():
    """Test that a multicast socket can be created and configured."""
    group = "239.0.0.1"
    port = 12345
    
    sock = create_multicast_socket(group, port)
    
    # Verify socket properties
    assert sock.family == socket.AF_INET
    assert sock.type == socket.SOCK_DGRAM
    assert sock.proto == socket.IPPROTO_UDP
    
    # Clean up
    sock.close()


def test_decode_binary_message():
    """Test binary message decoding."""
    # Create test binary data
    send_time = 1234567890
    counter = 42
    temperature = 25.5
    humidity = 60.0
    status = 1  # active
    
    # Use the same format string as in the producer
    format_string = '!QIffB'  # Added extra 'f' for humidity
    print(f"\nFormat string: {format_string}")
    print(f"Expected fields: {len(format_string) - 1}")  # -1 for the '!' character
    
    binary_data = struct.pack(format_string, send_time, counter, temperature, humidity, status)
    print(f"Binary data length: {len(binary_data)} bytes")
    
    # Decode message
    message = decode_binary_message(binary_data)
    
    # Verify decoded values
    assert message['send_time'] == send_time
    assert message['counter'] == counter
    assert message['data']['temperature'] == temperature
    assert message['data']['humidity'] == humidity
    assert message['data']['status'] == 'active'


def test_decode_binary_message_inactive():
    """Test binary message decoding with inactive status."""
    # Create test binary data
    send_time = 1234567890
    counter = 42
    temperature = 25.5
    humidity = 60.0
    status = 0  # inactive
    
    # Use the same format string as in the producer
    binary_data = struct.pack('!QIffB', send_time, counter, temperature, humidity, status)
    
    # Decode message
    message = decode_binary_message(binary_data)
    
    # Verify decoded values
    assert message['data']['status'] == 'inactive'


def test_decode_binary_message_invalid():
    """Test binary message decoding with invalid data."""
    # Create invalid binary data (too short)
    binary_data = struct.pack('!QI', 1234567890, 42)  # Missing fields
    
    # Verify that decoding raises an error
    with pytest.raises(struct.error):
        decode_binary_message(binary_data)


def test_invalid_multicast_group():
    """Test that an invalid multicast group raises an error."""
    with pytest.raises(socket.error):
        create_multicast_socket("256.0.0.1", 12345)  # Invalid IP address 