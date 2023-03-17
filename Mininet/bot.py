import random
import socket
import struct
import time

# Destination IP address for the ICMP echo requests
DESTINATION = '10.0.0.2'

# Generate a random payload for the ICMP echo requests
PAYLOAD = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(64))

def checksum(data):
    """
    Calculate the checksum of a packet data.
    """
    if len(data) % 2 != 0:
        data += b'\x00'
    res = sum(struct.unpack('!%sH' % (len(data) // 2), data))
    res = (res >> 16) + (res & 0xffff)
    res = res + (res >> 16)
    return ~res & 0xffff

def send_icmp_echo_request(destination):
    """
    Send an ICMP echo request to the specified destination.
    """
    # Create a raw socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    
    # Set the time-to-live (TTL) of the packet to 64
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 64)
    
    # Generate the ICMP header and payload
    icmp_type = 8  # ICMP echo request
    icmp_code = 0
    icmp_checksum = 0
    icmp_id = random.randint(0, 0xffff)
    icmp_seq = 0
    icmp_header = struct.pack('!BBHHH', icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq)
    icmp_payload = PAYLOAD.encode()
    icmp_checksum = checksum(icmp_header + icmp_payload)
    icmp_header = struct.pack('!BBHHH', icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq)
    icmp_packet = icmp_header + icmp_payload
    
    # Send the ICMP packet
    sock.sendto(icmp_packet, (destination, 0))
    
    # Close the socket
    sock.close()

# Send ICMP echo requests indefinitely
while True:
    send_icmp_echo_request(DESTINATION)
    time.sleep(1)
