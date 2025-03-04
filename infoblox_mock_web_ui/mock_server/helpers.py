"""
Helper functions for the Infoblox Mock Server.
"""

import uuid
import time
import random
import re
import ipaddress
import logging
import threading
from datetime import datetime
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

# Mutex for thread safety
db_lock = threading.RLock()

# Rate limiting data
rate_limit_data = {
    'counters': {},  # Keeps track of requests by IP
    'windows': {}    # Keeps track of time windows by IP
}

# Middleware and decorators
def simulate_delay(func):
    """Decorator to simulate network delay"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from mock_server.server import CONFIG
        if CONFIG['simulate_delay']:
            delay = random.randint(CONFIG['min_delay_ms'], CONFIG['max_delay_ms']) / 1000.0
            time.sleep(delay)
            logger.debug(f"Simulated delay of {delay:.2f} seconds")
        return func(*args, **kwargs)
    return wrapper

def simulate_failures(func):
    """Decorator to simulate random server failures"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from mock_server.server import CONFIG
        if CONFIG['simulate_failures'] and random.random() < CONFIG['failure_rate']:
            status_codes = [500, 502, 503, 504]
            status = random.choice(status_codes)
            error_msg = {
                500: "Internal Server Error",
                502: "Bad Gateway",
                503: "Service Unavailable",
                504: "Gateway Timeout"
            }
            logger.debug(f"Simulating server failure with {status} status code")
            response = jsonify({"Error": error_msg[status]})
            response.status_code = status
            return response
        return func(*args, **kwargs)
    return wrapper

def rate_limit(func):
    """Decorator to implement rate limiting"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from mock_server.server import CONFIG
        if not CONFIG['rate_limit']:
            return func(*args, **kwargs)
        
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Initialize if this is a new client
        if client_ip not in rate_limit_data['counters']:
            rate_limit_data['counters'][client_ip] = 0
            rate_limit_data['windows'][client_ip] = current_time + 60  # 1 minute window
        
        # Reset counter if the window has expired
        if current_time > rate_limit_data['windows'][client_ip]:
            rate_limit_data['counters'][client_ip] = 0
            rate_limit_data['windows'][client_ip] = current_time + 60
        
        # Check the rate limit
        if rate_limit_data['counters'][client_ip] >= CONFIG['rate_limit_requests']:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            response = jsonify({"Error": "Too many requests", "text": "Rate limit exceeded"})
            response.status_code = 429
            return response
        
        # Increment the counter
        rate_limit_data['counters'][client_ip] += 1
        return func(*args, **kwargs)
    return wrapper

def require_auth(func):
    """Decorator to check if authentication is required"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from mock_server.server import CONFIG, db
        if not CONFIG['auth_required']:
            return func(*args, **kwargs)
        
        # Basic auth header check
        auth = request.authorization
        client_ip = request.remote_addr
        
        # Skip auth check for session endpoints
        if request.path.endswith('/grid/session'):
            return func(*args, **kwargs)
        
        # Check if user has an active session
        session_found = False
        for username, sessions in db['activeuser'].items():
            if client_ip in sessions:
                session_found = True
                break
        
        if not session_found:
            logger.warning(f"Unauthorized access attempt from {client_ip}")
            response = jsonify({"Error": "Unauthorized", "text": "Authentication required"})
            response.status_code = 401
            return response
        
        return func(*args, **kwargs)
    return wrapper

def db_transaction(func):
    """Decorator to handle database transactions with locking"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from mock_server.server import CONFIG
        if CONFIG['simulate_db_lock'] and random.random() < CONFIG['lock_probability']:
            logger.warning("Simulating a database lock")
            response = jsonify({"Error": "Database is locked", "text": "Try again later"})
            response.status_code = 503
            return response
        
        with db_lock:
            return func(*args, **kwargs)
    return wrapper

def log_request(func):
    """Decorator to log request details"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from mock_server.server import CONFIG
        if CONFIG['detailed_logging']:
            logger.info(f"Request: {request.method} {request.path}")
            logger.info(f"Headers: {dict(request.headers)}")
            logger.info(f"Query Params: {request.args}")
            if request.json:
                logger.info(f"Body: {request.json}")
        return func(*args, **kwargs)
    return wrapper

# Helper functions
def generate_ref(obj_type, obj_data):
    """Create a reference ID similar to what Infoblox generates"""
    if obj_type == "network" or obj_type == "network_container":
        network = obj_data.get("network")
        encoded = str(uuid.uuid4()).replace("-", "")[:24]
        return f"{obj_type}/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{network}"
    elif obj_type == "range":
        start = obj_data.get("start_addr")
        end = obj_data.get("end_addr")
        encoded = str(uuid.uuid4()).replace("-", "")[:24]
        return f"{obj_type}/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{start}-{end}"
    elif obj_type.startswith("record:"):
        name = obj_data.get("name")
        encoded = str(uuid.uuid4()).replace("-", "")[:24]
        return f"{obj_type}/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{name}"
    elif obj_type == "lease" or obj_type == "fixedaddress":
        ip = obj_data.get("ipv4addr") or obj_data.get("ip_address")
        encoded = str(uuid.uuid4()).replace("-", "")[:24]
        return f"{obj_type}/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{ip}"
    else:
        return f"{obj_type}/{str(uuid.uuid4())}"

def find_object_by_ref(ref, db):
    """Find an object by its reference ID"""
    obj_type = ref.split('/')[0]
    if obj_type not in db:
        return None
    
    for obj in db[obj_type]:
        if obj["_ref"] == ref:
            return obj
    return None

def find_objects_by_query(obj_type, query_params, db):
    """Find objects matching query parameters with improved handling"""
    results = []
    
    if obj_type not in db:
        return results
    
    # Copy query params and remove special params
    actual_query = dict(query_params)
    special_params = ['_max_results', '_return_fields', '_paging', '_return_as_object']
    
    for param in special_params:
        if param in actual_query:
            actual_query.pop(param)
    
    for obj in db[obj_type]:
        match = True
        for key, value in actual_query.items():
            # Handle nested attributes with '.'
            if '.' in key:
                parts = key.split('.')
                curr = obj
                for part in parts[:-1]:
                    if part in curr:
                        curr = curr[part]
                    else:
                        match = False
                        break
                if match and (parts[-1] not in curr or str(curr[parts[-1]]) != str(value)):
                    match = False
            # Handle special case for ipv4addrs which is a list
            elif key == "ipv4addr" and "ipv4addrs" in obj:
                # Handle lookup in ipv4addrs array
                if not any(addr["ipv4addr"] == value for addr in obj.get("ipv4addrs", [])):
                    match = False
            # Handle exact match with regular field
            elif key not in obj or str(obj[key]) != str(value):
                # Try case-insensitive match for string values
                if key in obj and isinstance(obj[key], str) and isinstance(value, str):
                    if obj[key].lower() != value.lower():
                        match = False
                else:
                    match = False
        
        if match:
            results.append(obj)
    
    # Apply paging if requested
    if '_max_results' in query_params:
        try:
            max_results = int(query_params['_max_results'])
            results = results[:max_results]
        except (ValueError, TypeError):
            pass
    
    # Process return fields if specified
    if '_return_fields' in query_params:
        return process_return_fields(results, query_params['_return_fields'])
    
    return results

def process_return_fields(results, return_fields):
    """Process return fields parameter"""
    if not return_fields:
        return results
    
    fields = return_fields.split(',')
    filtered_results = []
    
    for result in results:
        filtered_result = {"_ref": result["_ref"]}  # _ref is always included
        for field in fields:
            field = field.strip()
            if field in result:
                filtered_result[field] = result[field]
        filtered_results.append(filtered_result)
    
    return filtered_results

def validate_network(network):
    """Validate network CIDR format"""
    try:
        ipaddress.ip_network(network, strict=False)
        return True
    except ValueError:
        return False

def validate_ip(ip):
    """Validate IP address format"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_hostname(hostname):
    """Validate hostname format"""
    if not hostname:
        return False
    
    # Simple hostname validation
    pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
    return bool(re.match(pattern, hostname))

def validate_and_prepare_data(obj_type, data):
    """Validate and prepare data based on object type"""
    validated_data = dict(data)
    
    if obj_type == "network":
        if "network" not in data:
            return None, "Missing required field 'network'"
        
        if not validate_network(data["network"]):
            return None, "Invalid network format"
        
        if "network_view" not in data:
            validated_data["network_view"] = "default"
    
    elif obj_type == "network_container":
        if "network" not in data:
            return None, "Missing required field 'network'"
        
        if not validate_network(data["network"]):
            return None, "Invalid network format"
        
        if "network_view" not in data:
            validated_data["network_view"] = "default"
    
    elif obj_type == "record:host":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid hostname format"
        
        if "ipv4addrs" not in data or not data["ipv4addrs"]:
            return None, "Missing or empty ipv4addrs field"
        
        for addr in data["ipv4addrs"]:
            if "ipv4addr" not in addr:
                return None, "Missing ipv4addr in ipv4addrs"
            
            if not validate_ip(addr["ipv4addr"]):
                return None, "Invalid IP address format"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    elif obj_type == "record:a":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid hostname format"
        
        if "ipv4addr" not in data:
            return None, "Missing required field 'ipv4addr'"
        
        if not validate_ip(data["ipv4addr"]):
            return None, "Invalid IP address format"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    elif obj_type == "fixedaddress":
        if "ipv4addr" not in data:
            return None, "Missing required field 'ipv4addr'"
        
        if not validate_ip(data["ipv4addr"]):
            return None, "Invalid IP address format"
        
        if "mac" not in data:
            return None, "Missing required field 'mac'"
        
        # Simple MAC address validation
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$'
        if not re.match(mac_pattern, data["mac"]):
            return None, "Invalid MAC address format"
    
    # Add timestamps
    validated_data["_create_time"] = datetime.now().isoformat()
    validated_data["_modify_time"] = datetime.now().isoformat()
    
    return validated_data, None