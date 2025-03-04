#!/usr/bin/env python3
"""
Example client script to demonstrate how to use the improved Infoblox mock server.
This script shows various operations and can be used to test the mock server.
"""

import requests
import json
import sys
import time

class InfobloxClient:
    def __init__(self, base_url="http://localhost:8080/wapi/v2.11", username="admin", password="infoblox"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        
    def login(self):
        """Login to Infoblox grid"""
        response = self.session.post(f"{self.base_url}/grid/session")
        if response.status_code == 200:
            print(f"Successfully logged in as {self.username}")
            return True
        else:
            print(f"Login failed: {response.text}")
            return False

    def logout(self):
        """Logout from Infoblox grid"""
        response = self.session.delete(f"{self.base_url}/grid/session")
        if response.status_code == 204:
            print("Successfully logged out")
            return True
        else:
            print(f"Logout failed: {response.text}")
            return False
            
    def get_objects(self, obj_type, query_params=None, return_fields=None):
        """Get objects of specified type with query parameters"""
        params = query_params or {}
        if return_fields:
            params['_return_fields'] = ','.join(return_fields)
            
        response = self.session.get(f"{self.base_url}/{obj_type}", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting objects: {response.text}")
            return None
            
    def create_object(self, obj_type, data):
        """Create a new object"""
        response = self.session.post(f"{self.base_url}/{obj_type}", json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error creating object: {response.text}")
            return None
            
    def get_object(self, ref, return_fields=None):
        """Get a specific object by reference"""
        params = {}
        if return_fields:
            params['_return_fields'] = ','.join(return_fields)
            
        response = self.session.get(f"{self.base_url}/{ref}", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting object: {response.text}")
            return None
            
    def update_object(self, ref, data):
        """Update an existing object"""
        response = self.session.put(f"{self.base_url}/{ref}", json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error updating object: {response.text}")
            return None
            
    def delete_object(self, ref):
        """Delete an object"""
        response = self.session.delete(f"{self.base_url}/{ref}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error deleting object: {response.text}")
            return None
            
    def next_available_ip(self, network):
        """Get next available IP in a network"""
        response = self.session.post(f"{self.base_url}/network/{network}/next_available_ip")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting next available IP: {response.text}")
            return None
            
    def search_ip(self, ip_addr=None, network=None):
        """Search for an IP address or network"""
        params = {}
        if ip_addr:
            params['ip_address'] = ip_addr
        if network:
            params['network'] = network
            
        response = self.session.get(f"{self.base_url}/ipv4address", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error searching IP: {response.text}")
            return None
            
    def get_grid_info(self):
        """Get grid information"""
        response = self.session.get(f"{self.base_url}/grid")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting grid info: {response.text}")
            return None
            
    def get_config(self):
        """Get mock server configuration"""
        response = self.session.get(f"{self.base_url}/config")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting configuration: {response.text}")
            return None
            
    def update_config(self, config_data):
        """Update mock server configuration"""
        response = self.session.put(f"{self.base_url}/config", json=config_data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error updating configuration: {response.text}")
            return None
            
    def reset_database(self):
        """Reset the mock server database"""
        response = self.session.post(f"{self.base_url}/db/reset")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error resetting database: {response.text}")
            return None
            
    def export_database(self):
        """Export the mock server database"""
        response = self.session.get(f"{self.base_url}/db/export")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error exporting database: {response.text}")
            return None

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))

def demo_operations(client):
    """Run a demonstration of various operations"""
    
    # Reset the database to ensure clean state
    print("\n=== Resetting Database ===")
    result = client.reset_database()
    if result:
        print("Database reset successful")
    
    # Get grid information
    print("\n=== Grid Information ===")
    grid_info = client.get_grid_info()
    if grid_info:
        print_json(grid_info)
    
    # Get all networks
    print("\n=== Networks ===")
    networks = client.get_objects("network")
    if networks:
        print_json(networks)
    
    # Create a new network
    print("\n=== Creating Network ===")
    network_data = {
        "network": "192.168.50.0/24",
        "comment": "Test Network"
    }
    network_ref = client.create_object("network", network_data)
    if network_ref:
        print(f"Created network with reference: {network_ref}")
    
    # Search for the network we just created
    print("\n=== Search for Network ===")
    found_networks = client.get_objects("network", {"network": "192.168.50.0/24"})
    if found_networks:
        print_json(found_networks)
    
    # Get next available IP from the network
    print("\n=== Next Available IP ===")
    next_ip = client.next_available_ip("192.168.50.0/24")
    if next_ip:
        print_json(next_ip)
        ip_address = next_ip.get("ips", [""])[0]
        if ip_address:
            print(f"Next available IP is {ip_address}")
    
    # Create a host record
    print("\n=== Creating Host Record ===")
    host_data = {
        "name": "test-server.example.com",
        "ipv4addrs": [{"ipv4addr": "192.168.50.10"}],
        "comment": "Test server"
    }
    host_ref = client.create_object("record:host", host_data)
    if host_ref:
        print(f"Created host record with reference: {host_ref}")
    
    # Create an A record
    print("\n=== Creating A Record ===")
    a_record_data = {
        "name": "www.example.com",
        "ipv4addr": "192.168.50.20",
        "comment": "Web server"
    }
    a_record_ref = client.create_object("record:a", a_record_data)
    if a_record_ref:
        print(f"Created A record with reference: {a_record_ref}")
    
    # Search for DNS records
    print("\n=== Search for DNS Records ===")
    host_records = client.get_objects("record:host")
    if host_records:
        print("Host Records:")
        print_json(host_records)
    
    a_records = client.get_objects("record:a")
    if a_records:
        print("A Records:")
        print_json(a_records)
    
    # Update a record
    if a_record_ref:
        print("\n=== Updating A Record ===")
        update_data = {
            "comment": "Updated web server comment",
            "ipv4addr": "192.168.50.25"
        }
        update_result = client.update_object(a_record_ref, update_data)
        if update_result:
            print(f"Updated A record: {update_result}")
            
        # Verify the update
        updated_record = client.get_object(a_record_ref)
        if updated_record:
            print("Updated record:")
            print_json(updated_record)
    
    # Search for an IP address
    if ip_address:
        print("\n=== Search for IP Address ===")
        ip_result = client.search_ip(ip_addr=ip_address)
        if ip_result:
            print_json(ip_result)
    
    # Search for IPs in a network
    print("\n=== Search for IPs in Network ===")
    network_result = client.search_ip(network="192.168.50.0/24")
    if network_result:
        print_json(network_result)
    
    # Create a fixed address
    print("\n=== Creating Fixed Address ===")
    fixed_addr_data = {
        "ipv4addr": "192.168.50.50",
        "mac": "00:11:22:33:44:55",
        "name": "printer.example.com",
        "comment": "Network printer"
    }
    fixed_addr_ref = client.create_object("fixedaddress", fixed_addr_data)
    if fixed_addr_ref:
        print(f"Created fixed address with reference: {fixed_addr_ref}")
    
    # Delete a record
    if a_record_ref:
        print("\n=== Deleting A Record ===")
        delete_result = client.delete_object(a_record_ref)
        if delete_result:
            print(f"Deleted A record: {delete_result}")
    
    # Update server configuration
    print("\n=== Server Configuration ===")
    config = client.get_config()
    if config:
        print("Current configuration:")
        print_json(config)
        
        print("\nUpdating configuration to enable delay simulation")
        new_config = {
            "simulate_delay": True,
            "min_delay_ms": 100,
            "max_delay_ms": 300
        }
        config_result = client.update_config(new_config)
        if config_result:
            print("Configuration updated:")
            print_json(config_result)
    
    # Run an operation with delay enabled to demonstrate
    print("\n=== Operation with Delay ===")
    print("Getting grid info (should experience delay)...")
    start = time.time()
    grid_info = client.get_grid_info()
    end = time.time()
    print(f"Operation took {end - start:.2f} seconds")
    
    # Reset configuration
    print("\nResetting configuration")
    reset_config = {
        "simulate_delay": False
    }
    client.update_config(reset_config)

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
        demo_operations(client)
    finally:
        # Logout
        client.logout()

if __name__ == "__main__":
    main()