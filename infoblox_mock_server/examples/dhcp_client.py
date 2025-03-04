#!/usr/bin/env python3
"""
DHCP client example for Infoblox Mock Server
Demonstrates working with DHCP-related functionality
"""

import sys
import json
import logging
from examples.basic_client import InfobloxClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))

def demo_dhcp_operations(client):
    """Demonstrate DHCP operations"""
    print("\n=== Infoblox Mock Server DHCP Operations Demo ===\n")
    
    # Create a network for DHCP
    print("Creating a network for DHCP...")
    network_data = {
        "network": "172.16.0.0/24",
        "comment": "DHCP network created by DHCP client example",
        "extattrs": {
            "Department": {"value": "IT"},
            "Purpose": {"value": "DHCP Testing"}
        }
    }
    network_ref = client.create_object("network", network_data)
    if network_ref:
        print(f"Created network with reference: {network_ref}")
    
    # Get the network
    if network_ref:
        print("\nGetting the newly created network...")
        network = client.get_object(network_ref)
        if network:
            print_json(network)
    
    # Create DHCP range
    print("\nCreating DHCP range...")
    range_data = {
        "network": "172.16.0.0/24",
        "start_addr": "172.16.0.100",
        "end_addr": "172.16.0.200",
        "comment": "DHCP range created by DHCP client example"
    }
    range_ref = client.create_object("range", range_data)
    if range_ref:
        print(f"Created DHCP range with reference: {range_ref}")
    
    # Get the DHCP range
    if range_ref:
        print("\nGetting the DHCP range...")
        range_obj = client.get_object(range_ref)
        if range_obj:
            print_json(range_obj)
    
    # Create fixed addresses (reservations)
    print("\nCreating fixed address (DHCP reservation)...")
    fixed_address_data = [
        {
            "ipv4addr": "172.16.0.50",
            "mac": "00:11:22:33:44:55",
            "name": "printer.example.com",
            "comment": "Network printer"
        },
        {
            "ipv4addr": "172.16.0.51",
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "scanner.example.com",
            "comment": "Network scanner"
        }
    ]
    
    fixed_refs = []
    for data in fixed_address_data:
        fixed_ref = client.create_object("fixedaddress", data)
        if fixed_ref:
            print(f"Created fixed address with reference: {fixed_ref}")
            fixed_refs.append(fixed_ref)
    
    # Get all fixed addresses
    print("\nGetting all fixed addresses...")
    fixed_addresses = client.get_objects("fixedaddress")
    if fixed_addresses:
        print_json(fixed_addresses)
    
    # Create DHCP lease (normally done by the DHCP server, but for demo purposes)
    print("\nCreating DHCP lease...")
    lease_data = {
        "ipv4addr": "172.16.0.150",
        "mac": "11:22:33:44:55:66",
        "binding_state": "active",
        "client_hostname": "laptop.example.com",
        "starts": "2023-01-01 00:00:00",
        "ends": "2023-01-02 00:00:00",
        "hardware": "Ethernet",
        "client_id": "01:11:22:33:44:55:66"
    }
    lease_ref = client.create_object("lease", lease_data)
    if lease_ref:
        print(f"Created DHCP lease with reference: {lease_ref}")
    
    # Get all leases
    print("\nGetting all DHCP leases...")
    leases = client.get_objects("lease")
    if leases:
        print_json(leases)
    
    # Get next available IP from the DHCP range
    print("\nGetting next available IP from the network...")
    next_ip = client.next_available_ip("172.16.0.0/24")
    if next_ip:
        print_json(next_ip)
    
    # Update a fixed address
    if fixed_refs:
        print("\nUpdating a fixed address...")
        update_data = {
            "comment": "Updated network printer comment",
            "extattrs": {
                "Location": {"value": "Main Office"},
                "Model": {"value": "HP LaserJet Pro"}
            }
        }
        update_result = client.update_object(fixed_refs[0], update_data)
        if update_result:
            print(f"Updated fixed address: {update_result}")
        
        # Get the updated fixed address
        updated_fixed = client.get_object(fixed_refs[0])
        if updated_fixed:
            print("Updated fixed address:")
            print_json(updated_fixed)
    
    # Delete a fixed address
    if len(fixed_refs) > 1:
        print("\nDeleting a fixed address...")
        delete_result = client.delete_object(fixed_refs[1])
        if delete_result:
            print(f"Deleted fixed address: {delete_result}")
    
    # Check if deletion was successful
    print("\nVerifying fixed address deletion...")
    remaining_fixed = client.get_objects("fixedaddress")
    if remaining_fixed:
        print(f"Remaining fixed addresses: {len(remaining_fixed)}")
    
    print("\nDHCP Operations demo completed!")

def main():
    # Default server URL
    server_url = "http://localhost:8080/wapi/v2.11"
    
    # Check for command line argument
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"Using Infoblox server: {server_url}")
    
    # Create client
    client = InfobloxClient(base_url=server_url)
    
    # Login
    if not client.login():
        print("Login failed. Exiting.")
        sys.exit(1)
    
    try:
        # Run demo operations
        demo_dhcp_operations(client)
    except Exception as e:
        logger.error(f"Error during demo: {str(e)}")
    finally:
        # Logout
        client.logout()

if __name__ == "__main__":
    main()