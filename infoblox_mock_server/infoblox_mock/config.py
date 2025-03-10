"""
Configuration management for Infoblox Mock Server
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# Default configuration
CONFIG = {
    'simulate_delay': False,      # Add random delay to responses
    'min_delay_ms': 50,           # Minimum delay in milliseconds
    'max_delay_ms': 300,          # Maximum delay in milliseconds
    'simulate_failures': False,   # Randomly simulate server failures
    'failure_rate': 0.05,         # 5% chance of failure if simulation enabled
    'detailed_logging': True,     # Enable detailed request/response logging
    'persistent_storage': False,  # Enable file-based persistent storage
    'storage_file': 'data/infoblox_mock_db.json',  # File for persistent storage
    'auth_required': True,        # Require authentication
    'rate_limit': True,           # Enable rate limiting
    'rate_limit_requests': 100,   # Number of requests allowed per minute
    'simulate_db_lock': False,    # Simulate database locks
    'lock_probability': 0.01,     # 1% chance of a lock per operation
    'wapi_version': 'v2.11',      # WAPI version to simulate
    'mock_responses_dir': None,   # Directory for mock responses (if None, feature is disabled)
    'record_mode': False          # Enable recording of API interactions
}

# Add to config.py
# Supported WAPI versions
SUPPORTED_WAPI_VERSIONS = ['v1.4', 'v2.0', 'v2.1', 'v2.5', 'v2.7', 'v2.11', 'v2.12']

# Feature flags based on versions
WAPI_FEATURES = {
    'v1.4': ['basic_dns', 'basic_dhcp', 'basic_ipam'],
    'v2.0': ['basic_dns', 'basic_dhcp', 'basic_ipam', 'extensible_attributes'],
    'v2.1': ['basic_dns', 'basic_dhcp', 'basic_ipam', 'extensible_attributes', 'bulk_operations'],
    'v2.5': ['basic_dns', 'basic_dhcp', 'basic_ipam', 'extensible_attributes', 'bulk_operations', 'dns_views'],
    'v2.7': ['basic_dns', 'basic_dhcp', 'basic_ipam', 'extensible_attributes', 'bulk_operations', 
             'dns_views', 'ipv6_support'],
    'v2.11': ['basic_dns', 'basic_dhcp', 'basic_ipam', 'extensible_attributes', 'bulk_operations', 
              'dns_views', 'ipv6_support', 'dnssec', 'rpz'],
    'v2.12': ['basic_dns', 'basic_dhcp', 'basic_ipam', 'extensible_attributes', 'bulk_operations', 
              'dns_views', 'ipv6_support', 'dnssec', 'rpz', 'cloud_api', 'dns64']
}

def is_feature_supported(feature):
    """Check if a feature is supported in the current WAPI version"""
    version = CONFIG.get('wapi_version', 'v2.11')
    return feature in WAPI_FEATURES.get(version, [])

def load_config(config_file):
    """Load configuration from a JSON file"""
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            
        # Update configuration with loaded values
        for key, value in config_data.items():
            if key in CONFIG:
                CONFIG[key] = value
                
        logger.info(f"Loaded configuration from {config_file}")
        return True
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return False

def save_config(config_file=None):
    """Save current configuration to a JSON file"""
    file_path = config_file or 'config.json'
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(CONFIG, f, indent=2)
            
        logger.info(f"Saved configuration to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False

def update_config(config_updates):
    """Update configuration with new values"""
    for key, value in config_updates.items():
        if key in CONFIG:
            CONFIG[key] = value
            
    logger.info(f"Updated configuration: {config_updates}")
    return CONFIG