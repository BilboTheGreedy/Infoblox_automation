"""
Advanced network features for Infoblox Mock Server
Implements network templates, discovery, compartments, and extensible attributes
"""

import logging
import ipaddress
import re
import json
import random
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

# Network data structures
network_templates = {}
network_containers = {}
network_discoveries = {}
network_compartments = {}

class NetworkTemplateManager:
    """Manager for network templates"""
    
    @staticmethod
    def create_template(data):
        """Create a new network template"""
        if not data.get("name"):
            return None, "Template name is required"
        
        # Generate a unique ID
        template_id = str(uuid.uuid4())
        
        # Create the template
        template_data = {
            "_ref": f"networktemplate/{template_id}",
            "name": data["name"],
            "comment": data.get("comment", ""),
            "network_view": data.get("network_view", "default"),
            "options": {
                "subnet_mask": data.get("subnet_mask", "255.255.255.0"),
                "gateway": data.get("gateway", ""),
                "domain_name": data.get("domain_name", ""),
                "domain_name_servers": data.get("domain_name_servers", []),
                "ipv6_prefix_length": data.get("ipv6_prefix_length", 64)
            },
            "authority": {
                "primary": data.get("primary", True),
                "auto_create_reversezone": data.get("auto_create_reversezone", True)
            },
            "dhcp": {
                "enabled": data.get("dhcp_enabled", True),
                "range_start_offset": data.get("range_start_offset", 10),
                "range_end_offset": data.get("range_end_offset", -10)
            },
            "dns": {
                "enabled": data.get("dns_enabled", True),
                "zone_format": data.get("zone_format", "{network}.in-addr.arpa"),
                "ns_group": data.get("ns_group", ""),
                "view": data.get("dns_view", "default")
            },
            "ipam": {
                "auto_create_reversezone": data.get("auto_create_reversezone", True),
                "network_template": data.get("ipam_network_template", "")
            },
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to templates
        network_templates[template_id] = template_data
        
        return template_data["_ref"], None
    
    @staticmethod
    def get_template(template_id):
        """Get a network template by ID"""
        if template_id not in network_templates:
            return None, f"Template not found: {template_id}"
        
        return network_templates[template_id], None
    
    @staticmethod
    def get_all_templates():
        """Get all network templates"""
        return list(network_templates.values())
    
    @staticmethod
    def update_template(template_id, data):
        """Update a network template"""
        if template_id not in network_templates:
            return None, f"Template not found: {template_id}"
        
        template = network_templates[template_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time"]:
                if key in ["options", "authority", "dhcp", "dns", "ipam"] and isinstance(value, dict):
                    # Merge dictionaries for nested objects
                    for sub_key, sub_value in value.items():
                        template[key][sub_key] = sub_value
                else:
                    template[key] = value
        
        template["_modify_time"] = datetime.now().isoformat()
        
        return template["_ref"], None
    
    @staticmethod
    def delete_template(template_id):
        """Delete a network template"""
        if template_id not in network_templates:
            return None, f"Template not found: {template_id}"
        
        # Delete the template
        del network_templates[template_id]
        
        return template_id, None
    
    @staticmethod
    def apply_template(network_data, template_id):
        """Apply a template to network data"""
        if template_id not in network_templates:
            return network_data, f"Template not found: {template_id}"
        
        template = network_templates[template_id]
        result = dict(network_data)
        
        # Apply template values if not explicitly provided
        if "network_view" not in result:
            result["network_view"] = template.get("network_view", "default")
        
        if "comment" not in result and "comment" in template:
            result["comment"] = template["comment"]
        
        # Apply DHCP settings
        if template["dhcp"]["enabled"] and "network" in result:
            # Calculate range based on network and offsets
            try:
                network_obj = ipaddress.ip_network(result["network"])
                hosts = list(network_obj.hosts())
                
                start_offset = template["dhcp"]["range_start_offset"]
                end_offset = template["dhcp"]["range_end_offset"]
                
                if len(hosts) > abs(start_offset) + abs(end_offset):
                    start_index = start_offset if start_offset >= 0 else 0
                    end_index = end_offset if end_offset < 0 else -1
                    
                    start_addr = str(hosts[start_index])
                    end_addr = str(hosts[end_index])
                    
                    # Add DHCP range
                    result["dhcp_range"] = {
                        "start_addr": start_addr,
                        "end_addr": end_addr
                    }
            except Exception as e:
                logger.error(f"Error calculating DHCP range: {str(e)}")
        
        # Apply DNS settings
        if template["dns"]["enabled"]:
            result["dns_view"] = template["dns"]["view"]
            
            # Apply zone format if network is provided
            if "network" in result:
                try:
                    network_obj = ipaddress.ip_network(result["network"])
                    
                    # Format the zone name
                    zone_format = template["dns"]["zone_format"]
                    if zone_format and "{network}" in zone_format:
                        # For IPv4, use the first three octets
                        if network_obj.version == 4:
                            network_part = ".".join(str(network_obj.network_address).split(".")[:3])
                            zone_name = zone_format.replace("{network}", network_part)
                        else:
                            # For IPv6, use the expanded form with colons replaced by dots
                            network_part = str(network_obj.network_address).replace(":", ".")
                            zone_name = zone_format.replace("{network}", network_part)
                        
                        result["zone_name"] = zone_name
                except Exception as e:
                    logger.error(f"Error formatting zone name: {str(e)}")
        
        # Apply extensible attributes if not explicitly provided
        if "extattrs" not in result:
            result["extattrs"] = template.get("extattrs", {})
        else:
            # Merge with template extattrs
            for key, value in template.get("extattrs", {}).items():
                if key not in result["extattrs"]:
                    result["extattrs"][key] = value
        
        return result, None

class NetworkDiscoveryManager:
    """Manager for network discovery operations"""
    
    @staticmethod
    def create_discovery(data):
        """Create a new network discovery task"""
        if not data.get("name"):
            return None, "Discovery name is required"
        
        if not data.get("network_view"):
            data["network_view"] = "default"
        
        # Validate either CIDR or address range
        if not data.get("network_cidr") and not (data.get("start_addr") and data.get("end_addr")):
            return None, "Either network CIDR or start/end address range is required"
        
        # Generate a unique ID
        discovery_id = str(uuid.uuid4())
        
        # Create the discovery task
        discovery_data = {
            "_ref": f"discovery/{discovery_id}",
            "name": data["name"],
            "network_view": data["network_view"],
            "status": "PENDING",
            "discovery_type": data.get("discovery_type", "PING"),  # PING, ARP, SYN, DNS, SNMP
            "network_cidr": data.get("network_cidr", ""),
            "start_addr": data.get("start_addr", ""),
            "end_addr": data.get("end_addr", ""),
            "exclude_list": data.get("exclude_list", []),
            "port_list": data.get("port_list", []),
            "discovery_ports": data.get("discovery_ports", [22, 23, 80, 443, 445]),
            "ping_count": data.get("ping_count", 3),
            "timeout": data.get("timeout", 1000),  # ms
            "retry_count": data.get("retry_count", 2),
            "comment": data.get("comment", ""),
            "schedule": data.get("schedule", {
                "run_now": True,
                "recurring": False
            }),
            "results": {
                "discovered_hosts": 0,
                "discovered_networks": 0,
                "completed_percent": 0,
                "start_time": None,
                "end_time": None,
                "hosts": []
            },
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to discoveries
        network_discoveries[discovery_id] = discovery_data
        
        # Schedule the discovery
        if discovery_data["schedule"]["run_now"]:
            import threading
            def run_discovery():
                NetworkDiscoveryManager.run_discovery(discovery_id)
            
            threading.Thread(target=run_discovery).start()
        
        return discovery_data["_ref"], None
    
    @staticmethod
    def get_discovery(discovery_id):
        """Get a network discovery by ID"""
        if discovery_id not in network_discoveries:
            return None, f"Discovery not found: {discovery_id}"
        
        return network_discoveries[discovery_id], None
    
    @staticmethod
    def get_all_discoveries():
        """Get all network discoveries"""
        return list(network_discoveries.values())
    
    @staticmethod
    def update_discovery(discovery_id, data):
        """Update a network discovery"""
        if discovery_id not in network_discoveries:
            return None, f"Discovery not found: {discovery_id}"
        
        discovery = network_discoveries[discovery_id]
        
        # Can't update a running discovery
        if discovery["status"] in ["RUNNING", "COMPLETING"]:
            return None, "Cannot update a running discovery"
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time", "status", "results"]:
                discovery[key] = value
        
        discovery["_modify_time"] = datetime.now().isoformat()
        
        return discovery["_ref"], None
    
    @staticmethod
    def delete_discovery(discovery_id):
        """Delete a network discovery"""
        if discovery_id not in network_discoveries:
            return None, f"Discovery not found: {discovery_id}"
        
        discovery = network_discoveries[discovery_id]
        
        # Can't delete a running discovery
        if discovery["status"] in ["RUNNING", "COMPLETING"]:
            return None, "Cannot delete a running discovery"
        
        # Delete the discovery
        del network_discoveries[discovery_id]
        
        return discovery_id, None
    
    @staticmethod
    def run_discovery(discovery_id):
        """Run a network discovery task"""
        if discovery_id not in network_discoveries:
            return None, f"Discovery not found: {discovery_id}"
        
        discovery = network_discoveries[discovery_id]
        
        # Update status
        discovery["status"] = "RUNNING"
        discovery["results"]["start_time"] = datetime.now().isoformat()
        discovery["results"]["completed_percent"] = 0
        discovery["_modify_time"] = datetime.now().isoformat()
        
        # Determine network range to scan
        network_range = []
        try:
            if discovery["network_cidr"]:
                # Use the CIDR
                network_obj = ipaddress.ip_network(discovery["network_cidr"])
                if network_obj.version == 4:
                    # For IPv4, use all hosts
                    network_range = list(network_obj.hosts())
                else:
                    # For IPv6, limit to a subset for simulation
                    hosts = list(network_obj.hosts())
                    network_range = hosts[:min(100, len(hosts))]
            elif discovery["start_addr"] and discovery["end_addr"]:
                # Use the address range
                start_ip = ipaddress.ip_address(discovery["start_addr"])
                end_ip = ipaddress.ip_address(discovery["end_addr"])
                
                # Generate range
                if start_ip.version == 4:
                    # For IPv4, use all addresses
                    current = int(start_ip)
                    end = int(end_ip)
                    while current <= end:
                        network_range.append(ipaddress.ip_address(current))
                        current += 1
                else:
                    # For IPv6, limit to a subset for simulation
                    current = int(start_ip)
                    end = int(end_ip)
                    step = max(1, (end - current) // 100)  # Sample up to 100 addresses
                    while current <= end:
                        network_range.append(ipaddress.ip_address(current))
                        current += step
            
            # Apply exclude list
            exclude_ips = []
            for exclude in discovery["exclude_list"]:
                try:
                    if "/" in exclude:
                        # CIDR notation
                        exclude_net = ipaddress.ip_network(exclude)
                        exclude_ips.extend(list(exclude_net.hosts()))
                    else:
                        # Single IP
                        exclude_ips.append(ipaddress.ip_address(exclude))
                except Exception as e:
                    logger.error(f"Error processing exclude item {exclude}: {str(e)}")
            
            # Remove excluded IPs
            network_range = [ip for ip in network_range if ip not in exclude_ips]
            
            # Simulate discovery progress
            discovery["results"]["discovered_networks"] = 1
            total_hosts = len(network_range)
            discovered_hosts = []
            
            # Generate a subset of "discovered" hosts
            discovery_count = random.randint(max(1, total_hosts // 10), max(2, total_hosts // 2))
            for i in range(discovery_count):
                # Update progress periodically
                if i % max(1, discovery_count // 10) == 0:
                    discovery["results"]["completed_percent"] = min(99, int((i / discovery_count) * 100))
                    discovery["_modify_time"] = datetime.now().isoformat()
                
                # Simulate discovery delay
                import time
                time.sleep(0.05)  # 50ms per host on average
                
                # Select a random host from the range
                if network_range:
                    ip = random.choice(network_range)
                    network_range.remove(ip)
                    
                    # Create host entry
                    host_entry = {
                        "ip_address": str(ip),
                        "is_ipv6": ip.version == 6,
                        "status": "UP",
                        "discovery_methods": [],
                        "mac_address": ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)]),
                        "hostname": f"host-{ip}".replace(".", "-").replace(":", "-"),
                        "first_discovered": datetime.now().isoformat(),
                        "last_seen": datetime.now().isoformat(),
                        "os_type": random.choice(["LINUX", "WINDOWS", "MACOS", "UNKNOWN"]),
                        "ports": [],
                        "response_time": random.randint(1, 1000)  # ms
                    }
                    
                    # Add discovery methods based on type
                    if discovery["discovery_type"] == "PING" or random.random() < 0.8:
                        host_entry["discovery_methods"].append("PING")
                    
                    if discovery["discovery_type"] == "ARP" or random.random() < 0.6:
                        host_entry["discovery_methods"].append("ARP")
                    
                    if discovery["discovery_type"] == "SNMP" or random.random() < 0.3:
                        host_entry["discovery_methods"].append("SNMP")
                        # Add SNMP system info
                        host_entry["snmp_info"] = {
                            "system_description": f"Sample SNMP System {ip}",
                            "system_name": f"snmp-{ip}".replace(".", "-").replace(":", "-"),
                            "system_location": "Server Room",
                            "system_contact": "admin@example.com"
                        }
                    
                    if discovery["discovery_type"] == "DNS" or random.random() < 0.5:
                        host_entry["discovery_methods"].append("DNS")
                        # Add DNS info
                        host_entry["dns_info"] = {
                            "hostname": f"host-{ip}".replace(".", "-").replace(":", "-") + ".example.com",
                            "domain": "example.com",
                            "aliases": []
                        }
                    
                    # Add open ports
                    if discovery["discovery_type"] == "SYN" or random.random() < 0.7:
                        host_entry["discovery_methods"].append("SYN")
                        
                        # Add some common ports
                        common_ports = [
                            {"port": 22, "service": "SSH", "proto": "TCP"},
                            {"port": 23, "service": "TELNET", "proto": "TCP"},
                            {"port": 25, "service": "SMTP", "proto": "TCP"},
                            {"port": 80, "service": "HTTP", "proto": "TCP"},
                            {"port": 443, "service": "HTTPS", "proto": "TCP"},
                            {"port": 445, "service": "SMB", "proto": "TCP"},
                            {"port": 3389, "service": "RDP", "proto": "TCP"},
                            {"port": 8080, "service": "HTTP-ALT", "proto": "TCP"}
                        ]
                        
                        # Randomly select some ports
                        num_ports = random.randint(0, 5)
                        selected_ports = random.sample(common_ports, min(num_ports, len(common_ports)))
                        
                        # Add custom ports from discovery_ports
                        for port in discovery["discovery_ports"]:
                            if random.random() < 0.3:  # 30% chance to have the port open
                                selected_ports.append({
                                    "port": port,
                                    "service": f"SERVICE-{port}",
                                    "proto": "TCP"
                                })
                        
                        host_entry["ports"] = selected_ports
                    
                    # Add to discovered hosts
                    discovered_hosts.append(host_entry)
            
            # Complete the discovery
            discovery["status"] = "COMPLETED"
            discovery["results"]["end_time"] = datetime.now().isoformat()
            discovery["results"]["completed_percent"] = 100
            discovery["results"]["discovered_hosts"] = len(discovered_hosts)
            discovery["results"]["hosts"] = discovered_hosts
            discovery["_modify_time"] = datetime.now().isoformat()
            
            logger.info(f"Discovery completed for {discovery_id}: found {len(discovered_hosts)} hosts")
            
            return discovery["_ref"], None
            
        except Exception as e:
            logger.error(f"Error running discovery: {str(e)}")
            discovery["status"] = "FAILED"
            discovery["results"]["end_time"] = datetime.now().isoformat()
            discovery["_modify_time"] = datetime.now().isoformat()
            return None, f"Discovery failed: {str(e)}"
    
    @staticmethod
    def get_discovery_results(discovery_id):
        """Get the results of a network discovery"""
        if discovery_id not in network_discoveries:
            return None, f"Discovery not found: {discovery_id}"
        
        discovery = network_discoveries[discovery_id]
        
        return discovery["results"], None

class NetworkCompartmentManager:
    """Manager for network compartments (multi-tenancy)"""
    
    @staticmethod
    def create_compartment(data):
        """Create a new network compartment"""
        if not data.get("name"):
            return None, "Compartment name is required"
        
        # Generate a unique ID
        compartment_id = str(uuid.uuid4())
        
        # Create the compartment
        compartment_data = {
            "_ref": f"networkcompartment/{compartment_id}",
            "name": data["name"],
            "description": data.get("description", ""),
            "parent_compartment": data.get("parent_compartment", ""),
            "networks": data.get("networks", []),
            "members": data.get("members", []),
            "permissions": data.get("permissions", []),
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to compartments
        network_compartments[compartment_id] = compartment_data
        
        return compartment_data["_ref"], None
    
    @staticmethod
    def get_compartment(compartment_id):
        """Get a network compartment by ID"""
        if compartment_id not in network_compartments:
            return None, f"Compartment not found: {compartment_id}"
        
        return network_compartments[compartment_id], None
    
    @staticmethod
    def get_all_compartments():
        """Get all network compartments"""
        return list(network_compartments.values())
    
    @staticmethod
    def update_compartment(compartment_id, data):
        """Update a network compartment"""
        if compartment_id not in network_compartments:
            return None, f"Compartment not found: {compartment_id}"
        
        compartment = network_compartments[compartment_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time"]:
                compartment[key] = value
        
        compartment["_modify_time"] = datetime.now().isoformat()
        
        return compartment["_ref"], None
    
    @staticmethod
    def delete_compartment(compartment_id):
        """Delete a network compartment"""
        if compartment_id not in network_compartments:
            return None, f"Compartment not found: {compartment_id}"
        
        compartment = network_compartments[compartment_id]
        
        # Check if this is a parent of other compartments
        for other_id, other in network_compartments.items():
            if other["parent_compartment"] == compartment_id:
                return None, f"Cannot delete compartment: it is a parent of compartment {other['name']}"
        
        # Delete the compartment
        del network_compartments[compartment_id]
        
        return compartment_id, None
    
    @staticmethod
    def add_network_to_compartment(compartment_id, network_ref):
        """Add a network to a compartment"""
        if compartment_id not in network_compartments:
            return None, f"Compartment not found: {compartment_id}"
        
        compartment = network_compartments[compartment_id]
        
        # Add network if not already present
        if network_ref not in compartment["networks"]:
            compartment["networks"].append(network_ref)
            compartment["_modify_time"] = datetime.now().isoformat()
        
        return compartment["_ref"], None
    
    @staticmethod
    def remove_network_from_compartment(compartment_id, network_ref):
        """Remove a network from a compartment"""
        if compartment_id not in network_compartments:
            return None, f"Compartment not found: {compartment_id}"
        
        compartment = network_compartments[compartment_id]
        
        # Remove network if present
        if network_ref in compartment["networks"]:
            compartment["networks"].remove(network_ref)
            compartment["_modify_time"] = datetime.now().isoformat()
        
        return compartment["_ref"], None

class ExtensibleAttributeManager:
    """Manager for extensible attributes and inheritance"""
    
    @staticmethod
    def set_attribute_inheritance(object_ref, attribute_name, inheritance=True):
        """Set inheritance for an extensible attribute"""
        from infoblox_mock.db import db
        
        # Parse object type and ID from ref
        parts = object_ref.split('/')
        if len(parts) < 2:
            return None, "Invalid object reference"
        
        obj_type = parts[0]
        
        # Find the object
        obj = None
        if obj_type in db:
            for obj_candidate in db[obj_type]:
                if obj_candidate.get("_ref") == object_ref:
                    obj = obj_candidate
                    break
        
        if not obj:
            return None, f"Object not found: {object_ref}"
        
        # Ensure extattrs exists
        if "extattrs" not in obj:
            obj["extattrs"] = {}
        
        # Create or update the attribute inheritance
        if attribute_name in obj["extattrs"]:
            if isinstance(obj["extattrs"][attribute_name], dict):
                obj["extattrs"][attribute_name]["inheritance"] = inheritance
            else:
                obj["extattrs"][attribute_name] = {
                    "value": obj["extattrs"][attribute_name],
                    "inheritance": inheritance
                }
        else:
            obj["extattrs"][attribute_name] = {
                "value": "",
                "inheritance": inheritance
            }
        
        return object_ref, None
    
    @staticmethod
    def get_inherited_attributes(object_ref):
        """Get all inherited attributes for an object"""
        from infoblox_mock.db import db
        
        # Parse object type and ID from ref
        parts = object_ref.split('/')
        if len(parts) < 2:
            return None, "Invalid object reference"
        
        obj_type = parts[0]
        
        # Find the object
        obj = None
        if obj_type in db:
            for obj_candidate in db[obj_type]:
                if obj_candidate.get("_ref") == object_ref:
                    obj = obj_candidate
                    break
        
        if not obj:
            return None, f"Object not found: {object_ref}"
        
        # For networks, inherit from parent network container
        if obj_type == "network" or obj_type == "ipv6network":
            network = obj.get("network", "")
            network_view = obj.get("network_view", "default")
            
            # Try to find parent container
            parent_container = None
            container_type = "network_container" if obj_type == "network" else "ipv6networkcontainer"
            
            for container in db.get(container_type, []):
                if container.get("network_view") != network_view:
                    continue
                
                try:
                    container_network = ipaddress.ip_network(container["network"])
                    child_network = ipaddress.ip_network(network)
                    
                    if child_network.subnet_of(container_network) and child_network != container_network:
                        # Found a parent container
                        if parent_container is None or ipaddress.ip_network(parent_container["network"]).subnet_of(container_network):
                            parent_container = container
                except Exception as e:
                    logger.error(f"Error checking subnet relationship: {str(e)}")
            
            # If we found a parent, check for inheritable attributes
            inherited_attrs = {}
            
            if parent_container and "extattrs" in parent_container:
                for attr_name, attr_value in parent_container["extattrs"].items():
                    # Check if attribute is inheritable
                    if isinstance(attr_value, dict) and attr_value.get("inheritance", False):
                        inherited_attrs[attr_name] = {
                            "value": attr_value.get("value", ""),
                            "inherited_from": parent_container["_ref"]
                        }
            
            return inherited_attrs, None
        
        # For other object types, no inheritance
        return {}, None
    
    @staticmethod
    def get_all_attributes():
        """Get all defined extensible attributes"""
        from infoblox_mock.db import db
        
        all_attrs = {}
        
        # Scan all objects for unique extensible attributes
        for obj_type, objects in db.items():
            for obj in objects:
                if "extattrs" in obj:
                    for attr_name, attr_value in obj["extattrs"].items():
                        if attr_name not in all_attrs:
                            all_attrs[attr_name] = {
                                "name": attr_name,
                                "type": "STRING",  # Default type
                                "allowed_values": [],
                                "default_value": "",
                                "required": False,
                                "list": False,
                                "searchable": True,
                                "comment": ""
                            }
                            
                            # Try to determine type
                            if isinstance(attr_value, dict) and "value" in attr_value:
                                value = attr_value["value"]
                            else:
                                value = attr_value
                            
                            if isinstance(value, bool):
                                all_attrs[attr_name]["type"] = "BOOLEAN"
                            elif isinstance(value, int):
                                all_attrs[attr_name]["type"] = "INTEGER"
                            elif isinstance(value, list):
                                all_attrs[attr_name]["list"] = True
        
        return list(all_attrs.values())

# Initialize with default templates
def init_network_features():
    """Initialize network features with default configurations"""
    # Add default network template
    if not network_templates:
        template_id = str(uuid.uuid4())
        network_templates[template_id] = {
            "_ref": f"networktemplate/{template_id}",
            "name": "Default Network Template",
            "comment": "Default template for new networks",
            "network_view": "default",
            "options": {
                "subnet_mask": "255.255.255.0",
                "gateway": "",
                "domain_name": "example.com",
                "domain_name_servers": [],
                "ipv6_prefix_length": 64
            },
            "authority": {
                "primary": True,
                "auto_create_reversezone": True
            },
            "dhcp": {
                "enabled": True,
                "range_start_offset": 10,
                "range_end_offset": -10
            },
            "dns": {
                "enabled": True,
                "zone_format": "{network}.in-addr.arpa",
                "ns_group": "",
                "view": "default"
            },
            "ipam": {
                "auto_create_reversezone": True,
                "network_template": ""
            },
            "extattrs": {
                "Location": {
                    "value": "Default",
                    "inheritance": True
                },
                "Department": {
                    "value": "IT",
                    "inheritance": True
                }
            },
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }

# Initialize network features
init_network_features()