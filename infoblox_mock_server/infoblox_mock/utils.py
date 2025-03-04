"""
Utility functions for Infoblox Mock Server
"""

import uuid
import ipaddress
import logging

logger = logging.getLogger(__name__)

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

def find_next_available_ip(network_cidr, used_ips):
    """Find the next available IP in a network"""
    try:
        net = ipaddress.ip_network(network_cidr, strict=False)
        
        # Find next available IP
        for ip in net.hosts():
            ip_str = str(ip)
            if ip_str not in used_ips:
                # Skip network address, broadcast address, and gateway
                if ip == net.network_address or ip == net.broadcast_address or ip_str.endswith(".0") or ip_str.endswith(".1") or ip_str.endswith(".255"):
                    continue
                
                logger.debug(f"Found next available IP in {network_cidr}: {ip_str}")
                return ip_str
        
        # No available IPs
        logger.warning(f"No available IPs in network: {network_cidr}")
        return None
    
    except Exception as e:
        logger.error(f"Error finding next available IP: {str(e)}")
        return None

def get_used_ips_in_db(db):
    """Get all used IPs from the database"""
    used_ips = set()
    
    # Collect IPs from various record types
    for obj_type in ["record:host", "record:a", "fixedaddress", "lease"]:
        for obj in db.get(obj_type, []):
            if obj_type == "record:host":
                for addr in obj.get("ipv4addrs", []):
                    used_ips.add(addr["ipv4addr"])
            elif obj_type == "record:a":
                used_ips.add(obj.get("ipv4addr", ""))
            else:
                used_ips.add(obj.get("ipv4addr", ""))
    
    # Remove empty strings
    used_ips.discard("")
    
    return used_ips

def is_ip_in_network(ip, network):
    """Check if an IP is within a given network"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        net_obj = ipaddress.ip_network(network, strict=False)
        return ip_obj in net_obj
    except ValueError:
        return False

def is_network_in_container(network, container):
    """Check if a network is within a container"""
    try:
        net_obj = ipaddress.ip_network(network, strict=False)
        container_obj = ipaddress.ip_network(container, strict=False)
        return net_obj.subnet_of(container_obj)
    except ValueError:
        return False

def get_ptr_name_from_ip(ip):
    """Generate PTR record name from IP address"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.version == 4:  # IPv4
            # Reverse the octets and append in-addr.arpa
            octets = ip.split('.')
            return f"{'.'.join(reversed(octets))}.in-addr.arpa"
        else:  # IPv6
            # Expand the address, reverse nibbles, and append ip6.arpa
            expanded = ip_obj.exploded
            expanded = expanded.replace(':', '')
            nibbles = [expanded[i] for i in range(0, len(expanded))]
            return f"{'.'.join(reversed(nibbles))}.ip6.arpa"
    except Exception as e:
        logger.error(f"Error generating PTR name from IP {ip}: {str(e)}")
        return None