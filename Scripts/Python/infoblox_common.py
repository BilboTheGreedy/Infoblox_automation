"""
infoblox_common.py
Common functions for Infoblox API interaction
"""

import os
import json
import logging
import requests
import getpass
import urllib.parse
import re
from datetime import datetime
import ipaddress

# Module-scoped variables
infoblox_session = None
base_url = None
log_file = None
username = None
password = None
verbose_logging = False

# Configure SSL verification (similar to PowerShell's TLS 1.2 setting)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

#region Logging Functions

def initialize_infoblox_logging(log_file_path=None, verbose_logging_param=False):
    """
    Initialize logging for Infoblox operations
    
    Args:
        log_file_path (str, optional): Path to log file. Defaults to script directory/InfobloxOperations.log.
        verbose_logging_param (bool, optional): Whether to enable verbose logging. Defaults to False.
    """
    global log_file, verbose_logging
    
    # Set default log path if not provided
    if not log_file_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(script_dir, "InfobloxOperations.log")
    
    log_file = log_file_path
    verbose_logging = verbose_logging_param
    
    # Initialize log file with header if it doesn't exist
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            log_header = f"""#########################################################
# Infoblox Operations Log File
# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#########################################################

"""
            f.write(log_header)
    
    # Configure logging
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    write_infoblox_log("Logging initialized to " + log_file)

def write_infoblox_log(message, level="INFO"):
    """
    Write a log entry to the Infoblox log file
    
    Args:
        message (str): Message to log
        level (str, optional): Log level. Defaults to "INFO".
    """
    # Only proceed if logging is initialized
    if not log_file:
        return
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    # Write to log file using Python's logging module
    if level == "INFO":
        logging.info(message)
        if verbose_logging:
            print(log_entry)
    elif level == "WARNING":
        logging.warning(message)
        print(f"\033[93m{log_entry}\033[0m")  # Yellow text
    elif level == "ERROR":
        logging.error(message)
        print(f"\033[91m{log_entry}\033[0m")  # Red text
    elif level == "SUCCESS":
        logging.info(message)  # SUCCESS maps to INFO in standard logging
        print(f"\033[92m{log_entry}\033[0m")  # Green text

#endregion

#region Connection Functions

def connect_infoblox(server, port=8080, api_version="v2.11", use_ssl=False, credentials=None):
    """
    Connect to Infoblox Grid
    
    Args:
        server (str): Infoblox server hostname or IP
        port (int, optional): Port to connect on. Defaults to 8080.
        api_version (str, optional): API version to use. Defaults to "v2.11".
        use_ssl (bool, optional): Use HTTPS. Defaults to False.
        credentials (tuple, optional): Tuple of (username, password). Defaults to None.
    
    Returns:
        dict: Connection info
    
    Raises:
        Exception: If connection fails
    """
    global base_url, infoblox_session, username, password
    
    try:
        # Build the base URL
        protocol = "https" if use_ssl else "http"
        base_url = f"{protocol}://{server}:{port}/wapi/{api_version}"
        write_infoblox_log(f"Connecting to Infoblox at {base_url}")
        
        # Store credentials
        if credentials:
            username, password = credentials
        else:
            username = input("Enter Infoblox username: ")
            password = getpass.getpass("Enter Infoblox password: ")
        
        # Initialize session
        infoblox_session = requests.Session()
        infoblox_session.auth = (username, password)
        infoblox_session.verify = False  # Equivalent to -SkipCertificateCheck in PowerShell
        
        # Test connection with grid info request
        response = infoblox_session.post(f"{base_url}/grid/session")
        response.raise_for_status()
        
        write_infoblox_log(f"Successfully connected to Infoblox as {username}", "SUCCESS")
        
        # Return connection info
        return {
            "BaseUrl": base_url,
            "Username": username,
            "Connected": True
        }
    except Exception as e:
        write_infoblox_log(f"Failed to connect to Infoblox: {str(e)}", "ERROR")
        raise Exception(f"Failed to connect to Infoblox: {str(e)}")

def disconnect_infoblox():
    """
    Disconnect from Infoblox Grid
    
    Returns:
        bool: True if successful, False otherwise
    """
    global base_url, infoblox_session
    
    try:
        if base_url and infoblox_session:
            write_infoblox_log("Disconnecting from Infoblox")
            
            response = infoblox_session.delete(f"{base_url}/grid/session")
            response.raise_for_status()
            
            infoblox_session = None
            write_infoblox_log("Successfully disconnected from Infoblox", "SUCCESS")
            return True
        else:
            write_infoblox_log("No active Infoblox session to disconnect", "WARNING")
            return False
    except Exception as e:
        write_infoblox_log(f"Error disconnecting from Infoblox: {str(e)}", "ERROR")
        return False

def test_infoblox_connection():
    """
    Test if the Infoblox connection is active
    
    Returns:
        bool: True if connected, False otherwise
    """
    global base_url, infoblox_session
    
    if not base_url or not infoblox_session:
        write_infoblox_log("No active Infoblox connection", "WARNING")
        return False
    
    try:
        # Attempt to get grid info as a connection test
        response = infoblox_session.get(f"{base_url}/grid")
        response.raise_for_status()
        
        write_infoblox_log("Infoblox connection is active")
        return True
    except Exception as e:
        write_infoblox_log(f"Infoblox connection test failed: {str(e)}", "ERROR")
        return False

#endregion

#region API Helper Functions

def invoke_infoblox_request(endpoint_url, method="GET", body=None, query_params=None, return_ref=False):
    """
    Make a request to the Infoblox API
    
    Args:
        endpoint_url (str): API endpoint URL
        method (str, optional): HTTP method. Defaults to "GET".
        body (dict, optional): Request body. Defaults to None.
        query_params (dict, optional): Query parameters. Defaults to None.
        return_ref (bool, optional): Return reference string if available. Defaults to False.
    
    Returns:
        object: Response from API
    
    Raises:
        Exception: If connection fails or API request fails
    """
    global base_url, infoblox_session
    
    # Verify connection
    if not test_infoblox_connection():
        raise Exception("No active Infoblox connection. Please run connect_infoblox first.")
    
    # Build full URL
    uri = f"{base_url}/{endpoint_url}"
    
    # Add query parameters if specified
    if query_params and len(query_params) > 0:
        query_string = []
        for key, value in query_params.items():
            query_string.append(f"{key}={urllib.parse.quote(str(value))}")
        uri += "?" + "&".join(query_string)
    
    write_infoblox_log(f"Sending {method} request to {uri}")
    
    try:
        # Prepare request
        headers = {"Content-Type": "application/json"}
        
        # Add body for POST and PUT requests
        json_data = None
        if method in ["POST", "PUT"] and body:
            json_data = body
            
            # Log the body (truncate if too long)
            log_body = json.dumps(body)
            if len(log_body) > 500:
                log_body = log_body[:497] + "..."
            write_infoblox_log(f"Request body: {log_body}")
        
        # Send request
        response = infoblox_session.request(
            method=method,
            url=uri,
            json=json_data,
            headers=headers
        )
        
        # Handle HTTP errors
        response.raise_for_status()
        
        # Parse response
        if response.content:
            # Try to parse as JSON
            try:
                result = response.json()
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                result = response.text
        else:
            result = None
        
        # Log response (truncate if too long)
        log_response = json.dumps(result) if result else "No content"
        if len(log_response) > 500:
            log_response = log_response[:497] + "..."
        write_infoblox_log(f"Response: {log_response}")
        
        # If ReturnRef is specified and response is a reference string, return it
        if return_ref and isinstance(result, str) and re.match(r"^[a-zA-Z0-9_]+/[^:]+:.+$", result):
            return result
        
        return result
    except requests.exceptions.HTTPError as e:
        # Try to extract error details from response
        error_details = str(e)
        try:
            if e.response.content:
                error_json = e.response.json()
                if "text" in error_json:
                    error_details = error_json["text"]
                elif "Error" in error_json:
                    error_details = error_json["Error"]
        except:
            pass
        
        write_infoblox_log(f"Infoblox API request failed: {error_details}", "ERROR")
        raise Exception(f"Infoblox API request failed: {error_details}")
    except Exception as e:
        write_infoblox_log(f"Infoblox API request failed: {str(e)}", "ERROR")
        raise Exception(f"Infoblox API request failed: {str(e)}")

def format_infoblox_result(input_object, title=None):
    """
    Format and display Infoblox result
    
    Args:
        input_object: Result object from Infoblox
        title (str, optional): Title for the result. Defaults to None.
    """
    # Display title if provided
    if title:
        print(f"\n\033[96m{title}\033[0m")
        print("\033[96m" + "=" * len(title) + "\033[0m")
    
    # Handle None
    if input_object is None:
        print("\033[93mNo results found.\033[0m")
        return
    
    # Handle string
    if isinstance(input_object, str):
        # Handle reference strings
        if re.match(r"^[a-zA-Z0-9_]+/[^:]+:.+$", input_object):
            print(f"\033[92mReference: {input_object}\033[0m")
        else:
            print(input_object)
        return
    
    # Handle list
    if isinstance(input_object, list):
        print(f"\033[96mFound {len(input_object)} results:\033[0m")
        
        for item in input_object:
            if isinstance(item, str):
                print(f"- {item}")
            else:
                print(json.dumps(item, indent=2))
                print("------------------------")
        return
    
    # Default to JSON dump for objects
    print(json.dumps(input_object, indent=2))

#endregion

#region Validation Functions

def test_infoblox_ip_address(ip_address):
    """
    Test if a string is a valid IP address
    
    Args:
        ip_address (str): IP address to test
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        ipaddress.ip_address(ip_address)
        write_infoblox_log(f"Validated IP address format: {ip_address}")
        return True
    except ValueError:
        write_infoblox_log(f"Invalid IP address format: {ip_address}", "ERROR")
        return False

def test_infoblox_hostname(hostname):
    """
    Test if a string is a valid hostname
    
    Args:
        hostname (str): Hostname to test
    
    Returns:
        bool: True if valid, False otherwise
    """
    # RFC 1123 compliant hostname regex pattern
    pattern = r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"
    
    is_valid = bool(re.match(pattern, hostname))
    
    if is_valid:
        write_infoblox_log(f"Validated hostname format: {hostname}")
    else:
        write_infoblox_log(f"Invalid hostname format: {hostname}", "ERROR")
    
    return is_valid

def test_infoblox_network(network):
    """
    Test if a string is a valid network in CIDR notation
    
    Args:
        network (str): Network to test (e.g. "192.168.1.0/24")
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Split CIDR notation to extract IP and prefix
        parts = network.split('/')
        
        # Validate IP address
        if not test_infoblox_ip_address(parts[0]):
            return False
        
        # Validate prefix length if present
        if len(parts) > 1:
            prefix = int(parts[1])
            if prefix < 0 or prefix > 32:
                write_infoblox_log(f"Invalid network prefix: {prefix} (must be between 0 and 32)", "ERROR")
                return False
        
        # Additional validation with ipaddress module
        ipaddress.ip_network(network)
        
        write_infoblox_log(f"Validated network format: {network}")
        return True
    except Exception as e:
        write_infoblox_log(f"Invalid network format: {network}", "ERROR")
        return False

def test_infoblox_mac(mac_address):
    """
    Test if a string is a valid MAC address
    
    Args:
        mac_address (str): MAC address to test
    
    Returns:
        bool: True if valid, False otherwise
    """
    # Accept formats: 00:11:22:33:44:55, 00-11-22-33-44-55, or 001122334455
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$'
    
    is_valid = bool(re.match(pattern, mac_address))
    
    if is_valid:
        write_infoblox_log(f"Validated MAC address format: {mac_address}")
    else:
        write_infoblox_log(f"Invalid MAC address format: {mac_address}", "ERROR")
    
    return is_valid

def get_infoblox_host_record(hostname):
    """
    Get host record for a hostname
    
    Args:
        hostname (str): Hostname to lookup
    
    Returns:
        object: Host record if found, None otherwise
    
    Raises:
        Exception: If API request fails
    """
    try:
        params = {
            "endpoint_url": "record:host",
            "query_params": {
                "name": hostname
            }
        }
        
        result = invoke_infoblox_request(**params)
        
        if result and len(result) > 0:
            write_infoblox_log(f"Host record found for {hostname}", "INFO")
            return result
        else:
            write_infoblox_log(f"No host record found for {hostname}", "INFO")
            return None
    except Exception as e:
        write_infoblox_log(f"Error checking host record: {str(e)}", "ERROR")
        raise Exception(f"Error checking host record: {str(e)}")

def get_infoblox_a_record(hostname):
    """
    Get A record for a hostname
    
    Args:
        hostname (str): Hostname to lookup
    
    Returns:
        object: A record if found, None otherwise
    
    Raises:
        Exception: If API request fails
    """
    try:
        params = {
            "endpoint_url": "record:a",
            "query_params": {
                "name": hostname
            }
        }
        
        result = invoke_infoblox_request(**params)
        
        if result and len(result) > 0:
            write_infoblox_log(f"A record found for {hostname}", "INFO")
            return result
        else:
            write_infoblox_log(f"No A record found for {hostname}", "INFO")
            return None
    except Exception as e:
        write_infoblox_log(f"Error checking A record: {str(e)}", "ERROR")
        raise Exception(f"Error checking A record: {str(e)}")

def get_infoblox_ip_address(ip_address):
    """
    Get information about an IP address
    
    Args:
        ip_address (str): IP address to lookup
    
    Returns:
        object: IP address info if found, None otherwise
    
    Raises:
        Exception: If API request fails
    """
    try:
        params = {
            "endpoint_url": "ipv4address",
            "query_params": {
                "ip_address": ip_address
            }
        }
        
        result = invoke_infoblox_request(**params)
        
        if result and len(result) > 0 and result[0].get("status") == "USED":
            write_infoblox_log(f"IP address {ip_address} is already in use", "INFO")
            return result
        else:
            write_infoblox_log(f"IP address {ip_address} is available", "INFO")
            return None
    except Exception as e:
        write_infoblox_log(f"Error checking IP address: {str(e)}", "ERROR")
        raise Exception(f"Error checking IP address: {str(e)}")

def get_infoblox_network(network):
    """
    Get information about a network
    
    Args:
        network (str): Network to lookup
    
    Returns:
        object: Network info if found, None otherwise
    
    Raises:
        Exception: If API request fails
    """
    try:
        params = {
            "endpoint_url": "network",
            "query_params": {
                "network": network
            }
        }
        
        result = invoke_infoblox_request(**params)
        
        if result and len(result) > 0:
            write_infoblox_log(f"Network {network} found", "INFO")
            return result[0]
        else:
            write_infoblox_log(f"Network {network} not found", "INFO")
            return None
    except Exception as e:
        write_infoblox_log(f"Error checking network: {str(e)}", "ERROR")
        raise Exception(f"Error checking network: {str(e)}")

#endregion