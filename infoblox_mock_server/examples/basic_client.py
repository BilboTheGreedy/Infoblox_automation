#!/usr/bin/env python3
"""
Basic client example for Infoblox Mock Server
Demonstrates core functionality including authentication, object CRUD, and search
"""

import requests
import json
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class InfobloxClient:
    def __init__(self, base_url="http://localhost:8080/wapi/v2.11", username="admin", password="infoblox"):
        """Initialize the Infoblox client"""
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        
    def login(self):
        """Login to Infoblox grid"""
        response = self.session.post(f"{self.base_url}/grid/session")
        if response.status_code == 200:
            logger.info(f"Successfully logged in as {self.username}")
            return True
        else:
            logger.error(f"Login failed: {response.text}")
            return False

    def logout(self):
        """Logout from Infoblox grid"""
        response = self.session.delete(f"{self.base_url}/grid/session")
        if response.status_code == 204:
            logger.info("Successfully logged out")
            return True
        else:
            logger.error(f"Logout failed: {response.text}")
            return False
            
    def get_objects(self, obj_type, query_params=None, return_fields=None):
        """Get objects of specified type with query parameters"""
        params = query_params or {}
        if return_fields:
            params['_return_fields'] = ','.join(return_fields) if isinstance(return_fields, list) else return_fields
            
        response = self.session.get(f"{self.base_url}/{obj_type}", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting objects: {response.text}")
            return None
            
    def create_object(self, obj_type, data):
        """Create a new object"""
        response = self.session.post(f"{self.base_url}/{obj_type}", json=data)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error creating object: {response.text}")
            return None
            
    def get_object(self, ref, return_fields=None):
        """Get a specific object by reference"""
        params = {}
        if return_fields:
            params['_return_fields'] = ','.join(return_fields) if isinstance(return_fields, list) else return_fields
            
        response = self.session.get(f"{self.base_url}/{ref}", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting object: {response.text}")
            return None
            
    def update_object(self, ref, data):
        """Update an existing object"""
        response = self.session.put(f"{self.base_url}/{ref}", json=data)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error updating object: {response.text}")
            return None
            
    def delete_object(self, ref):
        """Delete an object"""
        response = self.session.delete(f"{self.base_url}/{ref}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error deleting object: {response.text}")
            return None
            
    def next_available_ip(self, network):
        """Get next available IP in a network"""
        response = self.session.post(f"{self.base_url}/network/{network}/next_available_ip")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting next available IP: {response.text}")
            return None
            
    def get_grid_info(self):
        """Get grid information"""
        response = self.session.get(f"{self.base_url}/grid")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting grid info: {response.text}")
            return None
            
    def get_config(self):
        """Get mock server configuration"""
        response = self.session.get(f"{self.base_url}/config")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting configuration: {response.text}")
            return None
            
    def update_config(self, config_data):
        """Update mock server configuration"""
        response = self.session.put(f"{self.base_url}/config", json=config_data)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error updating configuration: {response.text}")
            return None
            
    def reset_database(self):
        """Reset the mock server database"""
        response = self.session.post(f"{self.base_url}/db/reset")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error resetting database: {response.text}")
            return None

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))

def demo_basic_operations(client):
    """Demonstrate basic CRUD operations"""
    print("\n=== Infoblox Mock Server Basic Operations Demo ===\n")
    
    # Get grid information
    print("Getting grid information...")
    grid_info = client.get_grid_info()
    if grid_info:
        print_json(grid_info)
    
    # Get all networks
    print("\nGetting all networks...")
    networks = client.get_objects("network")
    if networks:
        print_json(networks)
    
    # Create a new network
    print("\nCreating a new network...")
    network_data = {
        "network": "192.168.100.0/24",
        "comment": "Test network created by basic client",
        "extattrs": {
            "Environment": {"value": "Development"},
            "Owner": {"value": "Test Team"}
        }
    }
    network_ref = client.create_object("network", network_data)
    if network_ref:
        print(f"Created network with reference: {network_ref}")
    
    # Get the network we just created
    if network_ref:
        print("\nGetting the newly created network...")
        network = client.get_object(network_ref)
        if network:
            print_json(network)
    
    # Get next available IP from the network
    print("\nGetting next available IP...")
    next_ip = client.next_available_ip("192.168.100.0/24")
    if next_ip:
        print_json(next_ip)
        ip_address = next_ip.get("ips", [""])[0]
        if ip_address:
            print(f"Next available IP is {ip_address}")
    
    # Create a host record
    print("\nCreating a host record...")
    if 'ip_address' in locals() and ip_address:
        host_data = {
            "name": "test-server.example.com",
            "ipv4addrs": [{"ipv4addr": ip_address}],
            "comment": "Test server created by basic client"
        }
        host_ref = client.create_object("record:host", host_data)
        if host_ref:
            print(f"Created host record with reference: {host_ref}")
    
    # Search for host records
    print("\nSearching for host records...")
    host_records = client.get_objects("record:host")
    if host_records:
        print_json(host_records)
    
    # Update a host record
    if 'host_ref' in locals() and host_ref:
        print("\nUpdating host record...")
        update_data = {
            "comment": "Updated test server comment"
        }
        update_result = client.update_object(host_ref, update_data)
        if update_result:
            print(f"Updated host record: {update_result}")
            
        # Get the updated host record
        updated_host = client.get_object(host_ref)
        if updated_host:
            print("Updated host record:")
            print_json(updated_host)
    
    # Create an A record
    print("\nCreating an A record...")
    a_record_data = {
        "name": "www.example.com",
        "ipv4addr": "192.168.100.50",
        "comment": "Web server A record"
    }
    a_record_ref = client.create_object("record:a", a_record_data)
    if a_record_ref:
        print(f"Created A record with reference: {a_record_ref}")
    
    # Get all A records
    print("\nGetting all A records...")
    a_records = client.get_objects("record:a")
    if a_records:
        print_json(a_records)
    
    # Delete the A record
    if 'a_record_ref' in locals() and a_record_ref:
        print("\nDeleting A record...")
        delete_result = client.delete_object(a_record_ref)
        if delete_result:
            print(f"Deleted A record: {delete_result}")
    
    # Verify deletion
    print("\nVerifying A record deletion...")
    a_records_after = client.get_objects("record:a", {"name": "www.example.com"})
    if not a_records_after:
        print("A record successfully deleted")
    else:
        print("A record still exists!")

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
        demo_basic_operations(client)
    except Exception as e:
        logger.error(f"Error during demo: {str(e)}")
    finally:
        # Logout
        client.logout()

if __name__ == "__main__":
    main()