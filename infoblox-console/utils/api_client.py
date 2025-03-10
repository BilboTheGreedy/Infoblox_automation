"""
API Client for interacting with the Infoblox Mock Server
"""

import json
import logging
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

class InfobloxApiClient:
    """Client for interacting with the Infoblox Mock API Server."""
    
    def __init__(self, base_url, api_key=None, timeout=10):
        """
        Initialize the API client.
        
        Args:
            base_url (str): Base URL of the mock server
            api_key (str, optional): API key for authentication
            timeout (int, optional): Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        # Default headers for all requests
        self.default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Add API key if provided
        if api_key:
            self.default_headers['Authorization'] = f'Token {api_key}'
    
    def execute_request(self, method, endpoint, data=None, headers=None):
        """
        Execute a request to the mock server.
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint
            data (dict, optional): Request payload
            headers (dict, optional): Additional headers
            
        Returns:
            dict: Response from the server
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'
            
        url = f"{self.base_url}{endpoint}"
        
        # Merge default headers with provided headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
            
        # Log the request
        logger.info(f"Executing {method} request to {url}")
        if data:
            logger.debug(f"Request data: {json.dumps(data)}")
            
        try:
            # Execute the appropriate request based on method
            if method.upper() == 'GET':
                response = requests.get(
                    url, 
                    headers=request_headers, 
                    timeout=self.timeout
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url, 
                    json=data, 
                    headers=request_headers, 
                    timeout=self.timeout
                )
            elif method.upper() == 'PUT':
                response = requests.put(
                    url, 
                    json=data, 
                    headers=request_headers, 
                    timeout=self.timeout
                )
            elif method.upper() == 'DELETE':
                response = requests.delete(
                    url, 
                    json=data, 
                    headers=request_headers, 
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            # Try to parse JSON response
            try:
                response_data = response.json()
            except ValueError:
                # Return text if not JSON
                response_data = {'text': response.text}
                
            # Add status code and headers to response
            response_data['status_code'] = response.status_code
            response_data['headers'] = dict(response.headers)
            
            return response_data
            
        except Timeout:
            logger.error(f"Request to {url} timed out after {self.timeout} seconds")
            return {
                'status': 'error',
                'message': f'Request timed out after {self.timeout} seconds',
                'status_code': 408
            }
            
        except RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'status_code': 500
            }
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Unexpected error: {str(e)}',
                'status_code': 500
            }
    
    def get_server_status(self):
        """
        Get the current status of the mock server.
        
        Returns:
            dict: Server status information
        """
        try:
            response = self.execute_request('GET', '/status')
            if response.get('status_code') == 200:
                return {
                    'status': 'online',
                    'version': response.get('version', 'unknown'),
                    'uptime': response.get('uptime', 'unknown'),
                    'endpoints': response.get('endpoint_count', 0)
                }
            return {'status': 'error', 'message': 'Could not fetch server status'}
        except Exception as e:
            logger.error(f"Error getting server status: {str(e)}")
            return {'status': 'offline', 'message': str(e)}
    
    def get_available_endpoints(self):
        """
        Get a list of available endpoints from the mock server.
        
        Returns:
            list: Available endpoints
        """
        try:
            response = self.execute_request('GET', '/endpoints')
            if response.get('status_code') == 200:
                return response.get('endpoints', [])
            return []
        except Exception as e:
            logger.error(f"Error getting available endpoints: {str(e)}")
            return []
            
    def get_endpoint_schema(self, endpoint):
        """
        Get the schema for a specific endpoint.
        
        Args:
            endpoint (str): Endpoint path
            
        Returns:
            dict: Endpoint schema
        """
        try:
            response = self.execute_request('GET', f'/schema{endpoint}')
            if response.get('status_code') == 200:
                return response
            return {'error': 'Schema not available'}
        except Exception as e:
            logger.error(f"Error getting endpoint schema: {str(e)}")
            return {'error': str(e)}