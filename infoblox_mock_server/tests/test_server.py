#!/usr/bin/env python3
"""
Basic tests for the Infoblox Mock Server
"""

import pytest
import requests
import json
import os
import sys

# Add parent directory to path to allow importing from the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infoblox_mock.server import create_app
from infoblox_mock.config import CONFIG
from infoblox_mock.db import db, reset_db

# Test configuration
TEST_HOST = "localhost"
TEST_PORT = 8081
TEST_URL = f"http://{TEST_HOST}:{TEST_PORT}/wapi/{CONFIG['wapi_version']}"
TEST_USER = "admin"
TEST_PASS = "infoblox"

@pytest.fixture(scope="session")
def app_server():
    """
    Fixture to set up and start the Flask app for testing
    """
    app = create_app()
    
    # Configure for testing
    app.config.update({
        "TESTING": True,
    })
    
    # Start the server in a separate thread
    import threading
    server_thread = threading.Thread(target=lambda: app.run(host=TEST_HOST, port=TEST_PORT, debug=False))
    server_thread.daemon = True
    server_thread.start()
    
    # Wait a moment for the server to start
    import time
    time.sleep(1)
    
    # Reset the database to ensure a clean state
    reset_db()
    
    yield app

@pytest.fixture
def client(app_server):
    """
    Create a test client with authentication
    """
    session = requests.Session()
    session.auth = (TEST_USER, TEST_PASS)
    
    # Login
    session.post(f"{TEST_URL}/grid/session")
    
    yield session
    
    # Logout
    session.delete(f"{TEST_URL}/grid/session")

def test_server_running(client):
    """Test if server is running and accessible"""
    response = client.get(f"{TEST_URL}/grid")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]['name'] == "Infoblox Mock Grid"

def test_network_operations(client):
    """Test network CRUD operations"""
    # Create a network
    network_data = {
        "network": "10.20.30.0/24",
        "comment": "Test network",
        "extattrs": {
            "Location": {"value": "Test Lab"}
        }
    }
    response = client.post(f"{TEST_URL}/network", json=network_data)
    assert response.status_code == 200
    network_ref = response.json()
    
    # Get the network
    response = client.get(f"{TEST_URL}/{network_ref}")
    assert response.status_code == 200
    network = response.json()
    assert network["network"] == "10.20.30.0/24"
    assert network["comment"] == "Test network"
    
    # Update the network
    update_data = {
        "comment": "Updated test network"
    }
    response = client.put(f"{TEST_URL}/{network_ref}", json=update_data)
    assert response.status_code == 200
    
    # Get updated network
    response = client.get(f"{TEST_URL}/{network_ref}")
    assert response.status_code == 200
    updated_network = response.json()
    assert updated_network["comment"] == "Updated test network"
    
    # Delete the network
    response = client.delete(f"{TEST_URL}/{network_ref}")
    assert response.status_code == 200
    
    # Verify deletion
    response = client.get(f"{TEST_URL}/{network_ref}")
    assert response.status_code == 404

def test_dns_record_operations(client):
    """Test DNS record operations"""
    # Create an A record
    a_record_data = {
        "name": "test.example.com",
        "ipv4addr": "192.168.1.100",
        "comment": "Test A record"
    }
    response = client.post(f"{TEST_URL}/record:a", json=a_record_data)
    assert response.status_code == 200
    a_record_ref = response.json()
    
    # Get the A record
    response = client.get(f"{TEST_URL}/{a_record_ref}")
    assert response.status_code == 200
    a_record = response.json()
    assert a_record["name"] == "test.example.com"
    assert a_record["ipv4addr"] == "192.168.1.100"
    
    # Search for the A record
    response = client.get(f"{TEST_URL}/record:a", params={"name": "test.example.com"})
    assert response.status_code == 200
    search_results = response.json()
    assert len(search_results) > 0
    assert search_results[0]["name"] == "test.example.com"
    
    # Delete the A record
    response = client.delete(f"{TEST_URL}/{a_record_ref}")
    assert response.status_code == 200

def test_next_available_ip(client):
    """Test next available IP functionality"""
    # Create a network
    network_data = {
        "network": "10.50.60.0/24",
        "comment": "Test network for next IP"
    }
    response = client.post(f"{TEST_URL}/network", json=network_data)
    assert response.status_code == 200
    
    # Get next available IP
    response = client.post(f"{TEST_URL}/network/10.50.60.0/24/next_available_ip")
    assert response.status_code == 200
    next_ip_data = response.json()
    assert "ips" in next_ip_data
    assert len(next_ip_data["ips"]) > 0
    ip = next_ip_data["ips"][0]
    assert ip.startswith("10.50.60.")

def test_error_handling(client):
    """Test error handling"""
    # Try to get a non-existent object
    response = client.get(f"{TEST_URL}/network/nonexistent")
    assert response.status_code == 404
    
    # Try to create an invalid network
    invalid_data = {
        "network": "invalid-network",
        "comment": "This should fail"
    }
    response = client.post(f"{TEST_URL}/network", json=invalid_data)
    assert response.status_code == 400
    
    # Try to update a non-existent object
    response = client.put(f"{TEST_URL}/network/nonexistent", json={"comment": "Updated"})
    assert response.status_code == 404

if __name__ == "__main__":
    # This allows running the tests directly with Python
    # (Instead of using pytest command)
    pytest.main(["-v", __file__])