"""
Tests for the multicast producer.
"""
import socket
import pytest
import struct
from unittest.mock import patch, MagicMock
from src.multicast_producer import create_multicast_sender, encode_binary_message, send_message


def test_create_multicast_sender():
    """Test that a multicast sender socket can be created and configured."""
    group = "239.0.0.1"
    port = 12345
    ttl = 1
    
    sock = create_multicast_sender(group, port, ttl)
    
    # Verify socket properties
    assert sock.family == socket.AF_INET
    assert sock.type == socket.SOCK_DGRAM
    assert sock.proto == socket.IPPROTO_UDP
    
    # Clean up
    sock.close()


def test_encode_binary_message():
    """Test binary message encoding."""
    message = {
        "send_time": 1234567890,
        "counter": 42,
        "data": {
            "temperature": 25.5,
            "humidity": 60.0,
            "status": "active"
        }
    }
    
    # Encode message
    binary_data = encode_binary_message(message)
    
    # Verify binary data length
    assert len(binary_data) == 21  # 8 + 4 + 4 + 4 + 1 bytes
    
    # Decode and verify values
    send_time, counter, temperature, humidity, status = struct.unpack('!QIffB', binary_data)
    assert send_time == 1234567890
    assert counter == 42
    assert temperature == 25.5
    assert humidity == 60.0
    assert status == 1  # active


@patch('socket.socket')
def test_send_json_message(mock_socket):
    """Test sending a JSON message."""
    group = "239.0.0.1"
    port = 12345
    ttl = 1
    
    # Configure the mock socket
    mock_sock = MagicMock()
    mock_socket.return_value = mock_sock
    mock_sock.sendto.side_effect = socket.error("Mock network error")
    
    sock = create_multicast_sender(group, port, ttl)
    
    # Test message
    message = {
        "send_time": 1234567890,
        "counter": 42,
        "data": {
            "temperature": 25.5,
            "humidity": 60.0,
            "status": "active"
        }
    }
    
    # This should now raise the mocked error
    with pytest.raises(socket.error):
        send_message(sock, group, port, message, 'json')
    
    # Clean up
    sock.close()


@patch('socket.socket')
def test_send_binary_message(mock_socket):
    """Test sending a binary message."""
    group = "239.0.0.1"
    port = 12345
    ttl = 1
    
    # Configure the mock socket
    mock_sock = MagicMock()
    mock_socket.return_value = mock_sock
    mock_sock.sendto.side_effect = socket.error("Mock network error")
    
    sock = create_multicast_sender(group, port, ttl)
    
    # Test message
    message = {
        "send_time": 1234567890,
        "counter": 42,
        "data": {
            "temperature": 25.5,
            "humidity": 60.0,
            "status": "active"
        }
    }
    
    # This should now raise the mocked error
    with pytest.raises(socket.error):
        send_message(sock, group, port, message, 'binary')
    
    # Clean up
    sock.close() 