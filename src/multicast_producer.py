#!/usr/bin/env python3
"""
Multicast producer that sends messages in various formats to a multicast group.
"""
import socket
import json
import struct
import argparse
import sys
import time
from datetime import datetime


def list_available_interfaces():
    """List all available network interfaces and their IP addresses."""
    print("\nAvailable network interfaces:")
    try:
        import netifaces
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    print(f"  {iface}: {addr['addr']}")
    except ImportError:
        print("  Install netifaces package for detailed interface information:")
        print("  pip install netifaces")
        # Fallback to basic interface listing
        import subprocess
        try:
            if sys.platform == 'win32':
                subprocess.run(['ipconfig'], check=True)
            else:
                subprocess.run(['ifconfig'], check=True)
        except subprocess.CalledProcessError:
            print("  Could not list interfaces. Please install netifaces package.")


def create_multicast_sender(group: str, port: int, ttl: int = 1, interface: str = None) -> socket.socket:
    """Create and configure a socket for multicast sending."""
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    
    # Set TTL
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    
    # Set interface if specified
    if interface:
        try:
            # Convert interface name to IP address
            interface_ip = socket.gethostbyname(interface)
            print(f"Using interface {interface} with IP {interface_ip}")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface_ip))
        except socket.gaierror as e:
            # If interface is already an IP address, use it directly
            try:
                print(f"Using interface IP {interface}")
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
            except socket.error as e:
                print(f"\nError setting multicast interface: {e}")
                list_available_interfaces()
                raise
    
    return sock


def encode_binary_message(message: dict) -> bytes:
    """Encode message in binary format using struct."""
    # Format: 
    # - 8 bytes: timestamp (Q - unsigned long long)
    # - 4 bytes: counter (I - unsigned int)
    # - 4 bytes: temperature (f - float)
    # - 4 bytes: humidity (f - float)
    # - 1 byte: status (B - unsigned char, 1 for active, 0 for inactive)
    return struct.pack(
        '!QIffB',  # Network byte order (!), unsigned long long, int, float, float, unsigned char
        message['send_time'],
        message['counter'],
        message['data']['temperature'],
        message['data']['humidity'],
        1 if message['data']['status'] == 'active' else 0
    )


def send_message(sock: socket.socket, group: str, port: int, message: dict, format_type: str) -> None:
    """Send a message to the multicast group in the specified format."""
    try:
        if format_type == 'json':
            # Measure JSON serialization time
            json_start = time.time_ns()
            json_str = json.dumps(message)
            json_time = time.time_ns() - json_start
            
            # Measure encoding time
            encode_start = time.time_ns()
            data = json_str.encode('utf-8')
            encode_time = time.time_ns() - encode_start
            
            # Measure network send time
            send_start = time.time_ns()
            sock.sendto(data, (group, port))
            send_time = time.time_ns() - send_start
            
            # Print timing information
            print(f"Timing (ns):")
            print(f"  JSON serialization: {json_time:,}")
            print(f"  UTF-8 encoding: {encode_time:,}")
            print(f"  Network send: {send_time:,}")
            print(f"  Total processing: {json_time + encode_time + send_time:,}")
            
        elif format_type == 'binary':
            # Measure binary encoding time
            encode_start = time.time_ns()
            data = encode_binary_message(message)
            encode_time = time.time_ns() - encode_start
            
            # Measure network send time
            send_start = time.time_ns()
            sock.sendto(data, (group, port))
            send_time = time.time_ns() - send_start
            
            # Print timing information
            print(f"Timing (ns):")
            print(f"  Binary encoding: {encode_time:,}")
            print(f"  Network send: {send_time:,}")
            print(f"  Total processing: {encode_time + send_time:,}")
        
        print(f"Message length: {len(data)} bytes")
        print("-" * 50)
        
    except Exception as e:
        print(f"Error sending message: {e}", file=sys.stderr)
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Multicast producer that sends messages')
    parser.add_argument('group', help='Multicast group address (e.g., 239.0.0.1)')
    parser.add_argument('port', type=int, help='Port number to send to')
    parser.add_argument('--interval', type=float, default=1.0,
                       help='Interval between messages in seconds (default: 1.0)')
    parser.add_argument('--ttl', type=int, default=1,
                       help='Time-to-live for multicast packets (default: 1)')
    parser.add_argument('--format', choices=['json', 'binary'], default='json',
                       help='Message format (default: json)')
    parser.add_argument('--interface', type=str,
                       help='Interface to send multicast packets from (IP address or interface name)')
    # parser.add_argument('--list-interfaces', action='store_true',
    #                    help='List available network interfaces and exit')
    
    args = parser.parse_args()
    
    # if args.list_interfaces:
    #     list_available_interfaces()
    #     sys.exit(0)
    
    try:
        sock = create_multicast_sender(args.group, args.port, args.ttl, args.interface)
        print(f"Sending multicast messages to {args.group}:{args.port}")
        print(f"Format: {args.format}")
        print(f"Interval: {args.interval} seconds")
        if args.interface:
            print(f"Interface: {args.interface}")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        message_count = 0
        while True:
            # Get precise timestamp in nanoseconds
            send_time = time.time_ns()
            
            # Create message
            message = {
                "timestamp": datetime.now().isoformat(),
                "send_time": send_time,  # Nanosecond timestamp
                "counter": message_count,
                "data": {
                    "temperature": 25.5 + (message_count % 10),
                    "humidity": 60 + (message_count % 20),
                    "status": "active"
                }
            }
            
            send_message(sock, args.group, args.port, message, args.format)
            message_count += 1
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\nStopping multicast producer...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        sock.close()


if __name__ == '__main__':
    main() 