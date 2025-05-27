#!/usr/bin/env python3
"""
Multicast listener that prints received messages and calculates latency.
"""
import socket
import struct
import argparse
import sys
import time
import json
from statistics import mean, stdev
from collections import deque


class LatencyStats:
    """Class to track latency statistics."""
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.latencies = deque(maxlen=window_size)
        self.start_time = time.time_ns()
        self.message_count = 0
    
    def add_latency(self, latency_ns):
        """Add a new latency measurement."""
        self.latencies.append(latency_ns)
        self.message_count += 1
    
    def get_stats(self):
        """Get current latency statistics."""
        if not self.latencies:
            return "No messages received yet"
        
        current = self.latencies[-1]
        avg = mean(self.latencies)
        std = stdev(self.latencies) if len(self.latencies) > 1 else 0
        min_lat = min(self.latencies)
        max_lat = max(self.latencies)
        
        return (f"Latency: {current:,}ns (current) | "
                f"{avg:,.0f}ns (avg) | "
                f"{std:,.0f}ns (std) | "
                f"{min_lat:,}ns (min) | "
                f"{max_lat:,}ns (max) | "
                f"Messages: {self.message_count}")


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


def create_multicast_socket(group: str, port: int, interface: str = None) -> socket.socket:
    """Create and configure a socket for multicast listening."""
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    
    # Allow multiple sockets to use the same port
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to the server address
    sock.bind(('', port))
    
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
    
    # Tell the kernel to join a multicast group
    try:
        mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton('0.0.0.0'))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except socket.error as e:
        print(f"\nError joining multicast group: {e}")
        print(f"Group: {group}")
        print(f"Port: {port}")
        if interface:
            print(f"Interface: {interface}")
        raise
    
    return sock


def decode_binary_message(data: bytes) -> dict:
    """Decode binary message using struct."""
    # Format matches the producer's encode_binary_message function
    # Format: 
    # - 8 bytes: timestamp (Q - unsigned long long)
    # - 4 bytes: counter (I - unsigned int)
    # - 4 bytes: temperature (f - float)
    # - 4 bytes: humidity (f - float)
    # - 1 byte: status (B - unsigned char, 1 for active, 0 for inactive)
    send_time, counter, temperature, humidity, status = struct.unpack('!QIffB', data)
    return {
        "send_time": send_time,
        "counter": counter,
        "data": {
            "temperature": temperature,
            "humidity": humidity,
            "status": "active" if status == 1 else "inactive"
        }
    }


def listen_for_multicast(group: str, port: int, format_type: str = 'json', interface: str = None) -> None:
    """Listen for multicast messages and process them according to format."""
    try:
        sock = create_multicast_socket(group, port, interface)
        stats = LatencyStats()
        
        print(f"Listening for multicast messages on {group}:{port}")
        print(f"Format: {format_type}")
        if interface:
            print(f"Interface: {interface}")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        while True:
            # Measure network receive time
            recv_start = time.time_ns()
            data, addr = sock.recvfrom(1024)
            recv_time = time.time_ns() - recv_start
            
            try:
                if format_type == 'json':
                    # Measure decoding time
                    decode_start = time.time_ns()
                    decoded_data = data.decode('utf-8')
                    decode_time = time.time_ns() - decode_start
                    
                    # Measure JSON parsing time
                    json_start = time.time_ns()
                    message = json.loads(decoded_data)
                    json_time = time.time_ns() - json_start
                    
                    # Calculate latency if send_time is present
                    if 'send_time' in message:
                        send_time_ns = int(message['send_time'] * 1_000_000_000) if isinstance(message['send_time'], float) else message['send_time']
                        latency_ns = time.time_ns() - send_time_ns
                        stats.add_latency(latency_ns)
                        
                        print(f"\nReceived from {addr[0]}:{addr[1]}")
                        print(f"Message: {json.dumps(message, indent=2)}")
                        print(f"Timing (ns):")
                        print(f"  Network receive: {recv_time:,}")
                        print(f"  UTF-8 decoding: {decode_time:,}")
                        print(f"  JSON parsing: {json_time:,}")
                        print(f"  Total processing: {recv_time + decode_time + json_time:,}")
                        print(f"  End-to-end latency: {latency_ns:,}")
                        print(f"Stats: {stats.get_stats()}")
                
                elif format_type == 'binary':
                    # Measure binary decoding time
                    decode_start = time.time_ns()
                    message = decode_binary_message(data)
                    decode_time = time.time_ns() - decode_start
                    
                    # Calculate latency
                    latency_ns = time.time_ns() - message['send_time']
                    stats.add_latency(latency_ns)
                    
                    print(f"\nReceived from {addr[0]}:{addr[1]}")
                    print(f"Message: {json.dumps(message, indent=2)}")
                    print(f"Timing (ns):")
                    print(f"  Network receive: {recv_time:,}")
                    print(f"  Binary decoding: {decode_time:,}")
                    print(f"  Total processing: {recv_time + decode_time:,}")
                    print(f"  End-to-end latency: {latency_ns:,}")
                    print(f"Stats: {stats.get_stats()}")
                
            except (json.JSONDecodeError, struct.error) as e:
                print(f"\nReceived from {addr[0]}:{addr[1]}")
                print(f"Error decoding message: {e}")
                print(f"Raw data: {' '.join(f'{b:02x}' for b in data)}")
                print(f"Length: {len(data)} bytes")
                print(f"Timing (ns):")
                print(f"  Network receive: {recv_time:,}")
            
            print("-" * 50)
            
    except KeyboardInterrupt:
        print("\nStopping multicast listener...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        sock.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Multicast listener that processes messages')
    parser.add_argument('group', help='Multicast group address (e.g., 239.0.0.1)')
    parser.add_argument('port', type=int, help='Port number to listen on')
    parser.add_argument('--format', choices=['json', 'binary'], default='json',
                       help='Message format (default: json)')
    parser.add_argument('--interface', type=str,
                       help='Interface to listen for multicast packets on (IP address or interface name)')
    # parser.add_argument('--list-interfaces', action='store_true',
    #                    help='List available network interfaces and exit')
    
    args = parser.parse_args()
    
    # if args.list_interfaces:
    #     list_available_interfaces()
    #     sys.exit(0)
    
    listen_for_multicast(args.group, args.port, args.format, args.interface)


if __name__ == '__main__':
    main() 