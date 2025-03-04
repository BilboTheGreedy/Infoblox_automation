from flask import Flask, request, jsonify, abort, make_response
import json
import base64
import ipaddress
import re
import uuid
import time
import random
from datetime import datetime
import logging
import threading
from functools import wraps
import os

# Configure logging
log_format = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("infoblox_mock_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration options
CONFIG = {
    'simulate_delay': False,  # Add random delay to responses
    'min_delay_ms': 50,       # Minimum delay in milliseconds
    'max_delay_ms': 300,      # Maximum delay in milliseconds
    'simulate_failures': False,  # Randomly simulate server failures
    'failure_rate': 0.05,     # 5% chance of failure if simulation enabled
    'detailed_logging': True,  # Enable detailed request/response logging
    'persistent_storage': False,  # Enable file-based persistent storage
    'storage_file': 'infoblox_mock_db.json',  # File to use for persistent storage
    'auth_required': True,    # Require authentication
    'rate_limit': True,       # Enable rate limiting
    'rate_limit_requests': 100,  # Number of requests allowed per minute
    'simulate_db_lock': False,  # Simulate database locks
    'lock_probability': 0.01  # 1% chance of a lock per operation
}

# Mutex for thread safety
db_lock = threading.RLock()

# In-memory database to store our objects with more structure
db = {
    "network": [],
    "network_container": [],
    "record:host": [],
    "record:a": [],
    "record:ptr": [],
    "record:cname": [],
    "record:mx": [],
    "record:srv": [],
    "record:txt": [],
    "range": [],
    "lease": [],
    "fixedaddress": [],
    "grid": [{
        "_ref": "grid/1",
        "name": "Infoblox Mock Grid",
        "version": "NIOS 8.6.0",
        "status": "ONLINE",
        "license_type": "ENTERPRISE",
        "allow_recursive_deletion": True,
        "support_email": "support@example.com",
        "restart_status": {
            "restart_required": False
        }
    }],
    "member": [{
        "_ref": "member/1",
        "host_name": "infoblox.example.com",
        "config_addr_type": "IPV4",
        "platform": "PHYSICAL",
        "service_status": "WORKING",
        "node_status": "ONLINE",
        "ha_status": "ACTIVE",
        "ip_address": "192.168.1.2"
    }],
    "activeuser": {}  # Keep track of current sessions
}

# Rate limiting data
rate_limit_data = {
    'counters': {},  # Keeps track of requests by IP
    'windows': {}    # Keeps track of time windows by IP
}

# Helper for persistence
def save_db_to_file():
    """Save the current database state to a file"""
    if not CONFIG['persistent_storage']:
        return
    
    with open(CONFIG['storage_file'], 'w') as f:
        json.dump(db, f, indent=2)
        logger.info(f"Database saved to {CONFIG['storage_file']}")

def load_db_from_file():
    """Load the database state from a file if it exists"""
    global db
    if not CONFIG['persistent_storage'] or not os.path.exists(CONFIG['storage_file']):
        return
    
    try:
        with open(CONFIG['storage_file'], 'r') as f:
            db = json.load(f)
            logger.info(f"Database loaded from {CONFIG['storage_file']}")
    except Exception as e:
        logger.error(f"Error loading database from file: {e}")

# Initialize with default data
def initialize_db():
    """Initialize the database with default data"""
    # Existing initialization code...
    
    # Initialize new record types if they don't exist
    record_types = [
        "record:aaaa", "record:ns", "record:soa", 
        "record:dnskey", "record:rrsig", "record:ds",
        "record:nsec", "record:nsec3", "record:caa"
    ]
    
    for record_type in record_types:
        if record_type not in db:
            db[record_type] = []
    
    # Add example records if not already present
    if not db["record:aaaa"]:
        db["record:aaaa"].append({
            "_ref": f"record:aaaa/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:ipv6.example.com",
            "name": "ipv6.example.com",
            "view": "default",
            "ipv6addr": "2001:db8::1",
            "comment": "Example IPv6 host",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    if not db["record:ns"]:
        db["record:ns"].append({
            "_ref": f"record:ns/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:example.com",
            "name": "example.com",
            "view": "default",
            "nameserver": "ns1.example.com",
            "comment": "Primary nameserver",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    if not db["record:soa"]:
        db["record:soa"].append({
            "_ref": f"record:soa/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:example.com",
            "name": "example.com",
            "view": "default",
            "primary": "ns1.example.com",
            "email": "admin.example.com",
            "serial": 2023010101,
            "refresh": 10800,
            "retry": 3600,
            "expire": 604800,
            "minimum": 86400,
            "comment": "SOA record",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    if not db["record:caa"]:
        db["record:caa"].append({
            "_ref": f"record:caa/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:example.com",
            "name": "example.com",
            "view": "default",
            "flag": 0,
            "tag": "issue",
            "ca_value": "letsencrypt.org",
            "comment": "CAA record for Let's Encrypt",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    # Add DNSSEC example records
    if not db["record:dnskey"]:
        db["record:dnskey"].append({
            "_ref": f"record:dnskey/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:example.com",
            "name": "example.com",
            "view": "default",
            "algorithm": 8,  # RSA/SHA-256
            "flags": 257,    # KSK
            "key_tag": 12345,
            "public_key": "Base64EncodedKeyData==",
            "comment": "DNSKEY record",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    if not db["record:rrsig"]:
        db["record:rrsig"].append({
            "_ref": f"record:rrsig/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:example.com/A",
            "name": "example.com",
            "view": "default",
            "record_type": "A",
            "algorithm": 8,  # RSA/SHA-256
            "key_tag": 12345,
            "signer_name": "example.com",
            "signature": "Base64EncodedSignatureData==",
            "inception": "20230101000000",
            "expiration": "20230201000000",
            "comment": "RRSIG record for A record",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    save_db_to_file()

# Middleware and decorators
def simulate_delay(func):
    """Decorator to simulate network delay"""
    @wraps(func)
    def wrapper(*args, **kwargs):
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

def find_object_by_ref(ref):
    """Find an object by its reference ID"""
    obj_type = ref.split('/')[0]
    if obj_type not in db:
        return None
    
    for obj in db[obj_type]:
        if obj["_ref"] == ref:
            return obj
    return None

def find_objects_by_query(obj_type, query_params):
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

def validate_ipv6(ipv6):
    """Validate IPv6 address format"""
    try:
        ipaddress.IPv6Address(ipv6)
        return True
    except ValueError:
        return False

def validate_base64(data):
    """Validate if string is valid base64"""
    try:
        if isinstance(data, str):
            # Add padding if needed
            padding_needed = len(data) % 4
            if padding_needed:
                data += '=' * (4 - padding_needed)
            
            # Check if it can be decoded
            base64.b64decode(data)
            return True
        return False
    except Exception:
        return False

def validate_algorithm_number(algo):
    """Validate DNSSEC algorithm number (1-255)"""
    try:
        algo_num = int(algo)
        return 1 <= algo_num <= 255
    except (ValueError, TypeError):
        return False

def validate_key_tag(tag):
    """Validate DNSSEC key tag (1-65535)"""
    try:
        tag_num = int(tag)
        return 1 <= tag_num <= 65535
    except (ValueError, TypeError):
        return False

def validate_and_prepare_data(obj_type, data):
    """Validate and prepare data based on object type"""
    validated_data = dict(data)
    
    # Existing validation code...
    
    # Handle AAAA record validation
    if obj_type == "record:aaaa":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid hostname format"
        
        if "ipv6addr" not in data:
            return None, "Missing required field 'ipv6addr'"
        
        if not validate_ipv6(data["ipv6addr"]):
            return None, "Invalid IPv6 address format"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    # Handle NS record validation
    elif obj_type == "record:ns":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid domain name format"
        
        if "nameserver" not in data:
            return None, "Missing required field 'nameserver'"
        
        if not validate_hostname(data["nameserver"]):
            return None, "Invalid nameserver hostname format"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    # Handle SOA record validation
    elif obj_type == "record:soa":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid domain name format"
        
        if "primary" not in data:
            return None, "Missing required field 'primary'"
        
        if not validate_hostname(data["primary"]):
            return None, "Invalid primary nameserver format"
        
        if "email" not in data:
            return None, "Missing required field 'email'"
        
        # Email in SOA is actually in domain name format (dots instead of @)
        if not validate_hostname(data["email"]):
            return None, "Invalid email format for SOA record"
        
        # Set defaults for SOA values if not provided
        if "serial" not in data:
            # Use current date + 01 as default serial (YYYYMMDD01)
            today = datetime.now().strftime('%Y%m%d')
            validated_data["serial"] = int(f"{today}01")
        
        if "refresh" not in data:
            validated_data["refresh"] = 10800  # 3 hours
        
        if "retry" not in data:
            validated_data["retry"] = 3600  # 1 hour
        
        if "expire" not in data:
            validated_data["expire"] = 604800  # 1 week
        
        if "minimum" not in data:
            validated_data["minimum"] = 86400  # 1 day
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    # Handle DNSKEY record validation
    elif obj_type == "record:dnskey":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid domain name format"
        
        if "algorithm" not in data:
            return None, "Missing required field 'algorithm'"
        
        if not validate_algorithm_number(data["algorithm"]):
            return None, "Invalid algorithm number (must be 1-255)"
        
        if "flags" not in data:
            return None, "Missing required field 'flags'"
        
        # Flags can only be 0, 256, or 257
        try:
            flags = int(data["flags"])
            if flags not in [0, 256, 257]:
                return None, "Invalid flags value (must be 0, 256, or 257)"
        except (ValueError, TypeError):
            return None, "Invalid flags format (must be integer)"
        
        if "public_key" not in data:
            return None, "Missing required field 'public_key'"
        
        if not validate_base64(data["public_key"]):
            return None, "Invalid public_key format (must be base64)"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    # Handle RRSIG record validation
    elif obj_type == "record:rrsig":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid domain name format"
        
        if "record_type" not in data:
            return None, "Missing required field 'record_type'"
        
        if "algorithm" not in data:
            return None, "Missing required field 'algorithm'"
        
        if not validate_algorithm_number(data["algorithm"]):
            return None, "Invalid algorithm number (must be 1-255)"
        
        if "key_tag" not in data:
            return None, "Missing required field 'key_tag'"
        
        if not validate_key_tag(data["key_tag"]):
            return None, "Invalid key_tag (must be 1-65535)"
        
        if "signer_name" not in data:
            return None, "Missing required field 'signer_name'"
        
        if not validate_hostname(data["signer_name"]):
            return None, "Invalid signer_name format"
        
        if "signature" not in data:
            return None, "Missing required field 'signature'"
        
        if not validate_base64(data["signature"]):
            return None, "Invalid signature format (must be base64)"
        
        if "inception" not in data or "expiration" not in data:
            return None, "Missing required field 'inception' or 'expiration'"
        
        # Simple validation for inception/expiration timestamp format (YYYYMMDDHHmmSS)
        timestamp_pattern = r'^\d{14}$'
        if not re.match(timestamp_pattern, data["inception"]) or not re.match(timestamp_pattern, data["expiration"]):
            return None, "Invalid timestamp format (must be YYYYMMDDHHmmSS)"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    # Handle CAA record validation
    elif obj_type == "record:caa":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid domain name format"
        
        if "flag" not in data:
            return None, "Missing required field 'flag'"
        
        try:
            flag = int(data["flag"])
            if not (0 <= flag <= 255):
                return None, "Invalid flag value (must be 0-255)"
        except (ValueError, TypeError):
            return None, "Invalid flag format (must be integer)"
        
        if "tag" not in data:
            return None, "Missing required field 'tag'"
        
        # CAA tags must be one of: issue, issuewild, iodef
        valid_tags = ["issue", "issuewild", "iodef"]
        if data["tag"] not in valid_tags:
            return None, f"Invalid tag value (must be one of: {', '.join(valid_tags)})"
        
        if "ca_value" not in data:
            return None, "Missing required field 'ca_value'"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    # Add timestamps
    validated_data["_create_time"] = datetime.now().isoformat()
    validated_data["_modify_time"] = datetime.now().isoformat()
    
    return validated_data, None

# Routes with unified decorators
@app.route('/wapi/v2.11/<obj_type>', methods=['GET', 'POST'])
@log_request
@rate_limit
@require_auth
@simulate_failures
@simulate_delay
@db_transaction
def handle_objects(obj_type):
    """Handle object collections: search or create"""
    # Handle GET (search)
    if request.method == 'GET':
        query_params = request.args.to_dict()
        results = find_objects_by_query(obj_type, query_params)
        
        logger.info(f"GET {obj_type}: Found {len(results)} objects matching query")
        return jsonify(results)
    
    # Handle POST (create)
    elif request.method == 'POST':
        try:
            data = request.json
            
            # Validate and prepare data
            validated_data, error = validate_and_prepare_data(obj_type, data)
            if error:
                logger.warning(f"Validation error for {obj_type}: {error}")
                return jsonify({"Error": error}), 400
            
            # Create the object reference
            validated_data["_ref"] = generate_ref(obj_type, validated_data)
            
            # Check for duplicate (exact match on key fields)
            if obj_type == "network" or obj_type == "network_container":
                # Check for duplicate network
                for existing in db[obj_type]:
                    if existing.get("network") == validated_data.get("network") and \
                       existing.get("network_view") == validated_data.get("network_view"):
                        logger.warning(f"Duplicate network: {validated_data.get('network')}")
                        return jsonify({"Error": f"Network already exists: {validated_data.get('network')}"}), 400
            
            elif obj_type.startswith("record:"):
                # Check for duplicate DNS record
                for existing in db[obj_type]:
                    if existing.get("name") == validated_data.get("name") and \
                       existing.get("view") == validated_data.get("view"):
                        logger.warning(f"Duplicate DNS record: {validated_data.get('name')}")
                        return jsonify({"Error": f"DNS record already exists: {validated_data.get('name')}"}), 400
            
            # Save to database
            if obj_type not in db:
                db[obj_type] = []
            
            db[obj_type].append(validated_data)
            save_db_to_file()
            
            logger.info(f"Created new {obj_type}: {validated_data['_ref']}")
            
            # Return reference as per Infoblox API
            return jsonify(validated_data["_ref"])
        
        except Exception as e:
            logger.error(f"Error creating {obj_type}: {str(e)}")
            return jsonify({"Error": str(e)}), 400

@app.route('/wapi/v2.11/<path:ref>', methods=['GET', 'PUT', 'DELETE'])
@log_request
@rate_limit
@require_auth
@simulate_failures
@simulate_delay
@db_transaction
def handle_object(ref):
    """Handle individual object: get, update, or delete"""
    # Extract object type from reference
    obj_type = ref.split('/')[0]
    
    # Handle GET (read)
    if request.method == 'GET':
        obj = find_object_by_ref(ref)
        if not obj:
            logger.warning(f"Object not found: {ref}")
            return jsonify({"Error": "Object not found"}), 404
        
        # Handle _return_fields
        if '_return_fields' in request.args:
            result = process_return_fields([obj], request.args['_return_fields'])[0]
            return jsonify(result)
        
        logger.info(f"GET object: {ref}")
        return jsonify(obj)
    
    # Handle PUT (update)
    elif request.method == 'PUT':
        obj = find_object_by_ref(ref)
        if not obj:
            logger.warning(f"Object not found for update: {ref}")
            return jsonify({"Error": "Object not found"}), 404
        
        data = request.json
        
        # Update object with new data
        for key, value in data.items():
            # Skip reserved fields
            if key.startswith('_'):
                continue
            obj[key] = value
        
        # Update timestamp
        obj["_modify_time"] = datetime.now().isoformat()
        save_db_to_file()
        
        logger.info(f"Updated object: {ref}")
        return jsonify(ref)
    
    # Handle DELETE
    elif request.method == 'DELETE':
        obj = find_object_by_ref(ref)
        if not obj:
            logger.warning(f"Object not found for deletion: {ref}")
            return jsonify({"Error": "Object not found"}), 404
        
        # Remove object from database
        db[obj_type] = [o for o in db[obj_type] if o["_ref"] != ref]
        save_db_to_file()
        
        logger.info(f"Deleted object: {ref}")
        return jsonify(ref)

# Functions for grid operations
@app.route('/wapi/v2.11/grid', methods=['GET'])
@log_request
@rate_limit
@require_auth
@simulate_failures
@simulate_delay
def get_grid():
    """Get grid information"""
    logger.info("GET grid info")
    return jsonify(db["grid"])

@app.route('/wapi/v2.11/grid/1', methods=['GET'])
@log_request
@rate_limit
@require_auth
@simulate_failures
@simulate_delay
def get_grid_info():
    """Get detailed grid information"""
    logger.info("GET detailed grid info")
    return jsonify(db["grid"][0])

# Grid member operations
@app.route('/wapi/v2.11/member', methods=['GET'])
@log_request
@rate_limit
@require_auth
@simulate_failures
@simulate_delay
def get_members():
    """Get grid members"""
    logger.info("GET grid members")
    return jsonify(db["member"])

# Function for next available IP
@app.route('/wapi/v2.11/network/<path:network>/next_available_ip', methods=['POST'])
@log_request
@rate_limit
@require_auth
@simulate_failures
@simulate_delay
@db_transaction
def next_available_ip(network):
    """Get next available IP in a network"""
    # Find network
    network_obj = None
    for net in db["network"]:
        if net["network"] == network:
            network_obj = net
            break
    
    if not network_obj:
        logger.warning(f"Network not found: {network}")
        return jsonify({"Error": "Network not found"}), 404
    
    # Parse network to generate next IP
    try:
        net = ipaddress.ip_network(network_obj["network"], strict=False)
        
        # Find used IPs
        used_ips = set()
        for obj_type in ["record:host", "record:a", "fixedaddress", "lease"]:
            for obj in db.get(obj_type, []):
                if obj_type == "record:host":
                    for addr in obj.get("ipv4addrs", []):
                        used_ips.add(addr["ipv4addr"])
                elif obj_type == "record:a":
                    used_ips.add(obj.get("ipv4addr", ""))
                else:
                    used_ips.add(obj.get("ipv4addr", ""))
        
        # Find next available IP
        for ip in net.hosts():
            ip_str = str(ip)
            if ip_str not in used_ips:
                # Skip network address, broadcast address, and gateway
                if ip == net.network_address or ip == net.broadcast_address or ip_str.endswith(".0") or ip_str.endswith(".1") or ip_str.endswith(".255"):
                    continue
                
                logger.info(f"Found next available IP in {network}: {ip_str}")
                return jsonify({"ips": [ip_str]})
        
        # No available IPs
        logger.warning(f"No available IPs in network: {network}")
        return jsonify({"Error": "No available IPs in network"}), 400
    
    except Exception as e:
        logger.error(f"Error finding next available IP: {str(e)}")
        return jsonify({"Error": str(e)}), 400

# Function for search by CIDR or IP
@app.route('/wapi/v2.11/ipv4address', methods=['GET'])
@log_request
@rate_limit
@require_auth
@simulate_failures
@simulate_delay
def search_ipv4address():
    """Search for IP address or network information"""
    ip_addr = request.args.get('ip_address')
    network = request.args.get('network')
    
    if not ip_addr and not network:
        logger.warning("Missing required parameters for ipv4address search")
        return jsonify({"Error": "Missing required parameters. Provide either ip_address or network."}), 400
    
    results = []
    
    if ip_addr:
        # Validate IP format
        if not validate_ip(ip_addr):
            return jsonify({"Error": "Invalid IP address format"}), 400
            
        logger.info(f"Searching for IP address: {ip_addr}")
        
        # Find all objects with this IP
        ip_found = False
        for obj_type in ["record:host", "record:a", "fixedaddress", "lease"]:
            for obj in db.get(obj_type, []):
                if obj_type == "record:host":
                    if any(addr.get("ipv4addr") == ip_addr for addr in obj.get("ipv4addrs", [])):
                        ip_found = True
                        results.append({
                            "objects": [obj["_ref"]],
                            "ip_address": ip_addr,
                            "status": "USED",
                            "names": [obj["name"]],
                            "types": [obj_type]
                        })
                elif obj_type == "record:a" and obj.get("ipv4addr") == ip_addr:
                    ip_found = True
                    results.append({
                        "objects": [obj["_ref"]],
                        "ip_address": ip_addr,
                        "status": "USED",
                        "names": [obj["name"]],
                        "types": [obj_type]
                    })
                elif (obj_type in ["fixedaddress", "lease"]) and obj.get("ipv4addr") == ip_addr:
                    ip_found = True
                    result_obj = {
                        "objects": [obj["_ref"]],
                        "ip_address": ip_addr,
                        "status": "USED",
                        "types": [obj_type]
                    }
                    if "name" in obj:
                        result_obj["names"] = [obj["name"]]
                    results.append(result_obj)
        
        # If IP not found in any object, return UNUSED status
        if not ip_found:
            results.append({
                "ip_address": ip_addr,
                "status": "UNUSED",
                "types": []
            })
    
    if network:
        # Validate network format
        if not validate_network(network):
            return jsonify({"Error": "Invalid network format"}), 400
            
        logger.info(f"Searching for IPs in network: {network}")
        
        try:
            net = ipaddress.ip_network(network, strict=False)
            
            # Check if we have network objects for this network
            for net_obj in db.get("network", []):
                if ipaddress.ip_network(net_obj["network"]).overlaps(net):
                    results.append({
                        "objects": [net_obj["_ref"]],
                        "network": net_obj["network"],
                        "status": "USED",
                        "types": ["network"]
                    })
            
            # Find all IPs in the network
            for obj_type in ["record:host", "record:a", "fixedaddress", "lease"]:
                for obj in db.get(obj_type, []):
                    ips = []
                    if obj_type == "record:host":
                        ips = [addr.get("ipv4addr") for addr in obj.get("ipv4addrs", [])]
                    elif obj_type == "record:a":
                        if obj.get("ipv4addr"):
                            ips = [obj.get("ipv4addr")]
                    else:
                        if obj.get("ipv4addr"):
                            ips = [obj.get("ipv4addr")]
                    
                    for ip in ips:
                        try:
                            if ip and ipaddress.ip_address(ip) in net:
                                result = {
                                    "objects": [obj["_ref"]],
                                    "ip_address": ip,
                                    "status": "USED",
                                    "types": [obj_type],
                                    "network": network
                                }
                                if obj_type in ["record:host", "record:a"] and "name" in obj:
                                    result["names"] = [obj["name"]]
                                results.append(result)
                        except ValueError:
                            # Skip invalid IPs
                            pass
        
        except Exception as e:
            logger.error(f"Error processing network search: {str(e)}")
            return jsonify({"Error": str(e)}), 400
    
    logger.info(f"Found {len(results)} results")
    return jsonify(results)

# Authentication endpoints
@app.route('/wapi/v2.11/grid/session', methods=['POST', 'DELETE'])
@log_request
@rate_limit
@simulate_failures
@simulate_delay
def handle_session():
    """Handle authentication sessions"""
    client_ip = request.remote_addr
    
    # Handle login (POST)
    if request.method == 'POST':
        auth = request.authorization
        if not auth:
            logger.warning("Authentication attempt with no credentials")
            return jsonify({"Error": "Missing credentials"}), 401
        
        # In a real system we would verify credentials here
        # For mock, accept any non-empty username/password
        if not auth.username or not auth.password:
            logger.warning("Authentication attempt with empty credentials")
            return jsonify({"Error": "Invalid credentials"}), 401
        
        # Create or update session for user
        if auth.username not in db['activeuser']:
            db['activeuser'][auth.username] = []
        
        if client_ip not in db['activeuser'][auth.username]:
            db['activeuser'][auth.username].append(client_ip)
        
        logger.info(f"User {auth.username} logged in from {client_ip}")
        return jsonify({"username": auth.username})
    
    # Handle logout (DELETE)
    elif request.method == 'DELETE':
        # Remove client IP from all user sessions
        for username, sessions in db['activeuser'].items():
            if client_ip in sessions:
                sessions.remove(client_ip)
                logger.info(f"User {username} logged out from {client_ip}")
        
        # Return empty response with 204 status
        response = make_response('', 204)
        return response

# Configuration management
@app.route('/wapi/v2.11/config', methods=['GET', 'PUT'])
@log_request
@require_auth
def manage_config():
    """Get or update mock server configuration"""
    # Handle GET (read config)
    if request.method == 'GET':
        return jsonify(CONFIG)
    
    # Handle PUT (update config)
    elif request.method == 'PUT':
        try:
            data = request.json
            
            # Update configuration
            for key, value in data.items():
                if key in CONFIG:
                    CONFIG[key] = value
            
            logger.info(f"Updated configuration: {data}")
            return jsonify(CONFIG)
        
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            return jsonify({"Error": str(e)}), 400

# Restart the mock server (simulation only)
@app.route('/wapi/v2.11/grid/restart', methods=['POST'])
@log_request
@require_auth
def restart_grid():
    """Simulate grid restart"""
    logger.info("Simulating grid restart")
    
    # Update grid restart status
    db["grid"][0]["restart_status"]["restart_required"] = False
    
    # Simulate a delay
    time.sleep(2)
    
    return jsonify({"status": "Restart completed successfully"})

# Database management
@app.route('/wapi/v2.11/db/reset', methods=['POST'])
@log_request
def reset_database():
    """Reset the database to default values"""
    global db
    
    with db_lock:
        # Clear all data except grid and member
        for obj_type in db:
            if obj_type not in ['grid', 'member']:
                db[obj_type] = []
        
        # Reinitialize the database
        initialize_db()
        
        # Clear active users
        db['activeuser'] = {}
    
    logger.info("Database reset to default values")
    return jsonify({"status": "Database reset successfully"})

@app.route('/wapi/v2.11/db/export', methods=['GET'])
@log_request
@require_auth
def export_database():
    """Export the database as JSON"""
    return jsonify(db)

# Health check endpoint (no auth required)
@app.route('/wapi/v2.11/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "uptime": time.time() - start_time
    })

# Application setup
# In newer Flask versions, before_first_request is deprecated
# Using a different approach to initialize the server
def initialize_server():
    """Initialize the server"""
    # Load database from file if persistence is enabled
    if CONFIG['persistent_storage']:
        load_db_from_file()
    
    # Initialize the database with default data
    initialize_db()
    
    logger.info("Infoblox mock server initialized")

# Start the server
if __name__ == '__main__':
    # Record the start time for uptime reporting
    start_time = time.time()
    
    # Add command line argument parsing
    import argparse
    parser = argparse.ArgumentParser(description='Infoblox Mock Server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind the server to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--persistence', action='store_true', help='Enable database persistence')
    parser.add_argument('--storage-file', help='Path to database storage file')
    parser.add_argument('--delay', action='store_true', help='Simulate network delay')
    parser.add_argument('--failures', action='store_true', help='Simulate random failures')
    
    args = parser.parse_args()
    
    # Update configuration based on command line arguments
    if args.persistence:
        CONFIG['persistent_storage'] = True
    
    if args.storage_file:
        CONFIG['storage_file'] = args.storage_file
    
    if args.delay:
        CONFIG['simulate_delay'] = True
    
    if args.failures:
        CONFIG['simulate_failures'] = True
    
    # Initialize the server
    initialize_server()
    
    logger.info(f"Starting Infoblox mock server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)