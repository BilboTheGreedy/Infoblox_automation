"""
Mock response management for Infoblox Mock Server
Allows loading and playing back pre-recorded API responses
"""

import os
import json
import logging
import re
from flask import request

logger = logging.getLogger(__name__)

# Dictionary to store mock responses
mock_responses = {}

# Flag to enable/disable mock response mode
mock_response_mode = False

def load_mock_responses(directory):
    """Load pre-recorded API responses for integration testing"""
    global mock_responses, mock_response_mode
    
    if not os.path.exists(directory):
        logger.warning(f"Mock response directory not found: {directory}")
        return False
    
    # Clear existing responses
    mock_responses = {}
    
    # Walk through directory and load all JSON files
    files = [f for f in os.listdir(directory) if f.endswith('.json')]
    
    for filename in files:
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'r') as f:
                response_data = json.load(f)
                
            # Validate response data structure
            if not isinstance(response_data, dict) or 'request' not in response_data or 'response' not in response_data:
                logger.warning(f"Invalid mock response format in {filename}")
                continue
                
            # Extract request information
            req_info = response_data['request']
            if 'method' not in req_info or 'path' not in req_info:
                logger.warning(f"Missing required request fields in {filename}")
                continue
            
            # Create a key for this response
            req_method = req_info['method']
            req_path = req_info['path']
            req_params = req_info.get('params', {})
            req_body = req_info.get('body', '')
            
            # Create a unique key based on method, path, and optionally query params and body
            key = f"{req_method}:{req_path}"
            
            # Add to mock responses
            if key not in mock_responses:
                mock_responses[key] = []
            
            mock_responses[key].append({
                'query_params': req_params,
                'body': req_body,
                'response': response_data['response']
            })
            
            logger.info(f"Loaded mock response for {key}")
            
        except Exception as e:
            logger.error(f"Error loading mock response from {filename}: {str(e)}")
    
    # Enable mock response mode if we loaded at least one response
    if mock_responses:
        mock_response_mode = True
        logger.info(f"Mock response mode enabled with {len(mock_responses)} unique endpoints")
        return True
    else:
        logger.warning("No valid mock responses found, mock response mode not enabled")
        return False

def find_mock_response():
    """Find a matching mock response for the current request"""
    if not mock_response_mode:
        return None
    
    # Get request information
    req_method = request.method
    req_path = request.path
    
    # Extract WAPI version from path
    path_without_version = re.sub(r'/wapi/v[0-9.]+', '', req_path)
    
    # Create key
    key = f"{req_method}:{path_without_version}"
    
    if key not in mock_responses:
        logger.debug(f"No mock response found for {key}")
        return None
    
    # Get query parameters
    req_params = request.args.to_dict()
    
    # Get body if it exists
    req_body = ''
    if request.is_json and request.data:
        req_body = request.get_json()
    
    # Try to find a matching response
    for mock in mock_responses[key]:
        # Check if query params match
        params_match = True
        mock_params = mock['query_params']
        
        for param, value in mock_params.items():
            if param not in req_params or req_params[param] != value:
                params_match = False
                break
        
        # Check if body matches (if specified in mock)
        body_match = True
        if mock['body'] and req_body != mock['body']:
            body_match = False
        
        # If both match, return this response
        if params_match and body_match:
            logger.info(f"Found matching mock response for {key}")
            return mock['response']
    
    logger.debug(f"No matching mock response found for {key} with given params/body")
    return None

def record_interaction(response):
    """Record an API interaction for later playback"""
    if not request.path.startswith('/wapi/'):
        return
    
    # Create the record directory if it doesn't exist
    record_dir = os.path.join('data', 'recorded_responses')
    os.makedirs(record_dir, exist_ok=True)
    
    # Extract request information
    req_method = request.method
    req_path = request.path
    
    # Extract WAPI version from path
    match = re.search(r'/wapi/(v[0-9.]+)', req_path)
    if match:
        wapi_version = match.group(1)
        path_without_version = re.sub(r'/wapi/v[0-9.]+', '', req_path)
    else:
        wapi_version = "unknown"
        path_without_version = req_path
    
    # Get query parameters
    req_params = request.args.to_dict()
    
    # Get body if it exists
    req_body = None
    if request.is_json and request.data:
        req_body = request.get_json()
    
    # Create unique filename
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    filename = f"{req_method}_{path_without_version.replace('/', '_')}_{timestamp}.json"
    filepath = os.path.join(record_dir, filename)
    
    # Create response data
    response_data = {
        'request': {
            'method': req_method,
            'path': path_without_version,
            'wapi_version': wapi_version,
            'params': req_params,
            'body': req_body
        },
        'response': {
            'status_code': response.status_code,
            'data': response.get_json() if response.is_json else None,
            'headers': dict(response.headers)
        }
    }
    
    # Save to file
    try:
        with open(filepath, 'w') as f:
            json.dump(response_data, f, indent=2)
        logger.info(f"Recorded API interaction to {filepath}")
    except Exception as e:
        logger.error(f"Error recording API interaction: {str(e)}")