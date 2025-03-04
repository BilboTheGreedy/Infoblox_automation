"""
Data validation functions for Infoblox Mock Server
"""

import re
import ipaddress
import base64
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def validate_network(network):
    """Validate network CIDR format"""
    try:
        ipaddress.ip_network(network, strict=False)
        return True
    except ValueError:
        return False

def validate_ipv4(ip):
    """Validate IPv4 address format"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.version == 4
    except ValueError:
        return False

def validate_ipv6(ip):
    """Validate IPv6 address format"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.version == 6
    except ValueError:
        return False

def validate_ip(ip):
    """Validate IP address format (either IPv4 or IPv6)"""
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

def validate_mac_address(mac):
    """Validate MAC address format"""
    # Pattern matches: 00:11:22:33:44:55, 00-11-22-33-44-55, or 001122334455
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$'
    return bool(re.match(pattern, mac))

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
    time_now = datetime.now().isoformat()
    
    # Common timestamps
    validated_data["_create_time"] = time_now
    validated_data["_modify_time"] = time_now
    
    # Validate by object type
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
            
            if not validate_ipv4(addr["ipv4addr"]):
                return None, "Invalid IPv4 address format"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    elif obj_type == "record:a":
        if "name" not in data:
            return None, "Missing required field 'name'"
        
        if not validate_hostname(data["name"]):
            return None, "Invalid hostname format"
        
        if "ipv4addr" not in data:
            return None, "Missing required field 'ipv4addr'"
        
        if not validate_ipv4(data["ipv4addr"]):
            return None, "Invalid IPv4 address format"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    elif obj_type == "record:aaaa":
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
    
    elif obj_type == "record:ptr":
        if "ptrdname" not in data:
            return None, "Missing required field 'ptrdname'"
        
        if not validate_hostname(data["ptrdname"]):
            return None, "Invalid hostname format for ptrdname"
        
        if ("ipv4addr" not in data and "ipv6addr" not in data):
            return None, "Missing required field 'ipv4addr' or 'ipv6addr'"
        
        if "ipv4addr" in data and not validate_ipv4(data["ipv4addr"]):
            return None, "Invalid IPv4 address format"
        
        if "ipv6addr" in data and not validate_ipv6(data["ipv6addr"]):
            return None, "Invalid IPv6 address format"
        
        if "view" not in data:
            validated_data["view"] = "default"
    
    elif obj_type == "fixedaddress":
        if "ipv4addr" not in data:
            return None, "Missing required field 'ipv4addr'"
        
        if not validate_ipv4(data["ipv4addr"]):
            return None, "Invalid IPv4 address format"
        
        if "mac" not in data:
            return None, "Missing required field 'mac'"
        
        if not validate_mac_address(data["mac"]):
            return None, "Invalid MAC address format"
    
    # Additional record types validation will be similar
    
    return validated_data, None