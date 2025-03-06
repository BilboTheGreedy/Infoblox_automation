"""
Database operations for Infoblox Mock Server
"""

import json
import os
import logging
import threading
from datetime import datetime

from infoblox_mock.config import CONFIG

logger = logging.getLogger(__name__)

# Mutex for thread safety
db_lock = threading.RLock()

# In-memory database
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
    "record:aaaa": [],
    "record:ns": [],
    "record:soa": [],
    "record:dnskey": [],
    "record:rrsig": [],
    "record:ds": [],
    "record:nsec": [],
    "record:nsec3": [],
    "record:caa": [],
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

def save_db_to_file():
    """Save the current database state to a file"""
    if not CONFIG['persistent_storage']:
        return
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(CONFIG['storage_file']), exist_ok=True)
    
    with db_lock:
        try:
            with open(CONFIG['storage_file'], 'w') as f:
                json.dump(db, f, indent=2)
                logger.info(f"Database saved to {CONFIG['storage_file']}")
            return True
        except Exception as e:
            logger.error(f"Error saving database to file: {e}")
            return False

def load_db_from_file():
    """Load the database state from a file if it exists"""
    global db
    if not CONFIG['persistent_storage'] or not os.path.exists(CONFIG['storage_file']):
        return False
    
    with db_lock:
        try:
            with open(CONFIG['storage_file'], 'r') as f:
                db = json.load(f)
                logger.info(f"Database loaded from {CONFIG['storage_file']}")
            return True
        except Exception as e:
            logger.error(f"Error loading database from file: {e}")
            return False

def initialize_db():
    """Initialize the database with default data"""
    with db_lock:
        # Add IPv6 networks if they don't exist
        if not db.get("ipv6network", None):
            db["ipv6network"] = []
        
        # Add IPv6 network container if they don't exist
        if not db.get("ipv6networkcontainer", None):
            db["ipv6networkcontainer"] = []
        
        # Add IPv6 range if they don't exist
        if not db.get("ipv6range", None):
            db["ipv6range"] = []
        
        # Add IPv6 fixed address if they don't exist
        if not db.get("ipv6fixedaddress", None):
            db["ipv6fixedaddress"] = []
        
        # Add example IPv6 data
        if not db["ipv6network"]:
            db["ipv6network"].append({
                "_ref": f"ipv6network/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:2001:db8::/64",
                "network": "2001:db8::/64",
                "network_view": "default",
                "comment": "Example IPv6 network",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
        
        if not db["ipv6networkcontainer"]:
            db["ipv6networkcontainer"].append({
                "_ref": f"ipv6networkcontainer/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:2001:db8::/48",
                "network": "2001:db8::/48",
                "network_view": "default",
                "comment": "Example IPv6 network container",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
        
        if not db["ipv6range"]:
            db["ipv6range"].append({
                "_ref": f"ipv6range/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:2001:db8::1-2001:db8::100",
                "network": "2001:db8::/64",
                "network_view": "default",
                "start_addr": "2001:db8::1",
                "end_addr": "2001:db8::100",
                "comment": "Example IPv6 range",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })        
        # Add a network container if none exists
        if not db["network_container"]:
            db["network_container"].append({
                "_ref": f"networkcontainer/ZG5zLm5ldHdvcmtfY29udGFpbmVyJDEwLjAuMC4wLzg:10.0.0.0/8",
                "network": "10.0.0.0/8",
                "network_view": "default",
                "comment": "Default network container",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
        
        # Add default networks if none exist
        if not db["network"]:
            db["network"].append({
                "_ref": f"network/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:10.10.10.0/24",
                "network": "10.10.10.0/24",
                "network_view": "default",
                "comment": "Development network",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
            
            db["network"].append({
                "_ref": f"network/ZG5zLm5ldHdvcmskMTkyLjE2OC4xLjAvMjQ:192.168.1.0/24",
                "network": "192.168.1.0/24",
                "network_view": "default",
                "comment": "Management network",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
        
        # Add a DHCP range if none exists
        if not db["range"]:
            db["range"].append({
                "_ref": f"range/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:10.10.10.100-10.10.10.200",
                "network": "10.10.10.0/24",
                "network_view": "default",
                "start_addr": "10.10.10.100",
                "end_addr": "10.10.10.200",
                "comment": "DHCP range for development",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
        
        # Add some host records if none exist
        if not db["record:host"]:
            db["record:host"].append({
                "_ref": f"record:host/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:server1.example.com",
                "name": "server1.example.com",
                "view": "default",
                "ipv4addrs": [{"ipv4addr": "10.10.10.5"}],
                "comment": "Application server",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
        
        # Add some A records if none exist
        if not db["record:a"]:
            db["record:a"].append({
                "_ref": f"record:a/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:www.example.com",
                "name": "www.example.com",
                "view": "default",
                "ipv4addr": "10.10.10.6",
                "comment": "Web server",
                "extattrs": {},
                "_create_time": datetime.now().isoformat(),
                "_modify_time": datetime.now().isoformat()
            })
        
        # Initialize new record types with example data
        # AAAA Record (IPv6)
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
        
        # SOA Record
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
        
        # NS Records
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
        
        save_db_to_file()
        logger.info("Database initialized with default data")
        return True

def find_object_by_ref(ref):
    """Find an object by its reference ID"""
    obj_type = ref.split('/')[0]
    if obj_type not in db:
        return None
    
    with db_lock:
        for obj in db[obj_type]:
            if obj["_ref"] == ref:
                return obj
    return None

def find_objects_by_query(obj_type, query_params):
    """Find objects matching query parameters"""
    results = []
    
    if obj_type not in db:
        return results
    
    # Copy query params and remove special params
    actual_query = dict(query_params)
    special_params = ['_max_results', '_return_fields', '_paging', '_return_as_object']
    
    for param in special_params:
        if param in actual_query:
            actual_query.pop(param)
    
    with db_lock:
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
        results = process_return_fields(results, query_params['_return_fields'])
    
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

def add_object(obj_type, data):
    """Add a new object to the database"""
    with db_lock:
        if obj_type not in db:
            db[obj_type] = []
        
        db[obj_type].append(data)
        save_db_to_file()
        return data["_ref"]

def update_object(ref, data):
    """Update an existing object"""
    obj = find_object_by_ref(ref)
    if not obj:
        return None
    
    with db_lock:
        # Update object with new data
        for key, value in data.items():
            # Skip reserved fields
            if key.startswith('_'):
                continue
            obj[key] = value
        
        # Update timestamp
        obj["_modify_time"] = datetime.now().isoformat()
        save_db_to_file()
        return ref

def delete_object(ref):
    """Delete an object from the database"""
    obj_type = ref.split('/')[0]
    if obj_type not in db:
        return None
    
    with db_lock:
        # Find the object
        obj = None
        for o in db[obj_type]:
            if o["_ref"] == ref:
                obj = o
                break
        
        if not obj:
            return None
        
        # Remove from database
        db[obj_type] = [o for o in db[obj_type] if o["_ref"] != ref]
        save_db_to_file()
        return ref

def reset_db():
    """Reset the database to initial state"""
    with db_lock:
        for key in db:
            db[key] = []
        
        initialize_db()
        return True

def export_db():
    """Export the current database state"""
    with db_lock:
        return dict(db)
