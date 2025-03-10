"""
Enhanced DNS features for Infoblox Mock Server
Implements DNS views, forwarding, Response Policy Zones (RPZ), DNSSEC, and more
"""

import logging
import re
import ipaddress
import json
import os
import random
from datetime import datetime, timedelta
import hashlib
import base64

logger = logging.getLogger(__name__)

# DNS data structures
dns_views = {
    "default": {
        "_ref": "view/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:default",
        "name": "default",
        "is_default": True,
        "comment": "Default DNS view",
        "extattrs": {},
        "_create_time": datetime.now().isoformat(),
        "_modify_time": datetime.now().isoformat()
    }
}

dns_forwarders = {}

dns_recursion = {
    "default": {
        "allow_recursion": True,
        "forwarders_only": False,
        "recursion_enabled": True
    }
}

rpz_zones = {}
rpz_rules = {}

dnssec_keys = {}
dnssec_trusted_keys = {}
dnssec_enabled_zones = set()

dns64_networks = {}

query_redirects = {}

class DNSViewManager:
    """Manager for DNS views"""
    
    @staticmethod
    def create_view(data):
        """Create a new DNS view"""
        if not data.get("name"):
            return None, "View name is required"
        
        name = data["name"]
        if name in dns_views:
            return None, f"View already exists: {name}"
        
        # Create the view
        view_data = {
            "_ref": f"view/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{name}",
            "name": name,
            "is_default": data.get("is_default", False),
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Only one view can be the default
        if view_data["is_default"]:
            for view_name, view in dns_views.items():
                if view["is_default"]:
                    view["is_default"] = False
        
        # Add to views
        dns_views[name] = view_data
        
        # Initialize recursion settings
        dns_recursion[name] = {
            "allow_recursion": data.get("allow_recursion", True),
            "forwarders_only": data.get("forwarders_only", False),
            "recursion_enabled": data.get("recursion_enabled", True)
        }
        
        return view_data["_ref"], None
    
    @staticmethod
    def get_view(name):
        """Get a DNS view by name"""
        return dns_views.get(name)
    
    @staticmethod
    def update_view(name, data):
        """Update a DNS view"""
        if name not in dns_views:
            return None, f"View not found: {name}"
        
        view = dns_views[name]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time", "name"]:
                view[key] = value
        
        view["_modify_time"] = datetime.now().isoformat()
        
        # Only one view can be the default
        if view.get("is_default"):
            for view_name, v in dns_views.items():
                if view_name != name and v.get("is_default"):
                    v["is_default"] = False
        
        return view["_ref"], None
    
    @staticmethod
    def delete_view(name):
        """Delete a DNS view"""
        if name not in dns_views:
            return None, f"View not found: {name}"
        
        if name == "default":
            return None, "Cannot delete the default view"
        
        # Delete the view
        del dns_views[name]
        
        # Delete associated recursion settings
        if name in dns_recursion:
            del dns_recursion[name]
        
        return name, None
    
    @staticmethod
    def get_all_views():
        """Get all DNS views"""
        return list(dns_views.values())

class DNSForwarderManager:
    """Manager for DNS forwarders"""
    
    @staticmethod
    def create_forwarder(data):
        """Create a DNS forwarder configuration"""
        if not data.get("name"):
            return None, "Forwarder name is required"
        
        if not data.get("view"):
            return None, "DNS view is required"
        
        if not data.get("forwarders") or not isinstance(data["forwarders"], list):
            return None, "Forwarders list is required"
        
        name = data["name"]
        view = data["view"]
        
        # Ensure view exists
        if view not in dns_views:
            return None, f"View not found: {view}"
        
        # Create a unique ID
        forwarder_id = f"{view}:{name}"
        
        if forwarder_id in dns_forwarders:
            return None, f"Forwarder already exists for this view: {name}"
        
        # Validate forwarder IPs
        for forwarder in data["forwarders"]:
            try:
                ipaddress.ip_address(forwarder)
            except ValueError:
                return None, f"Invalid IP address in forwarders: {forwarder}"
        
        # Create the forwarder configuration
        forwarder_data = {
            "_ref": f"forwarder/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{forwarder_id}",
            "name": name,
            "view": view,
            "forwarders": data["forwarders"],
            "forward_only": data.get("forward_only", False),
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to forwarders
        dns_forwarders[forwarder_id] = forwarder_data
        
        # Update recursion settings if forward_only is True
        if forwarder_data["forward_only"] and view in dns_recursion:
            dns_recursion[view]["forwarders_only"] = True
        
        return forwarder_data["_ref"], None
    
    @staticmethod
    def get_forwarder(forwarder_id):
        """Get a DNS forwarder configuration by ID"""
        return dns_forwarders.get(forwarder_id)
    
    @staticmethod
    def get_forwarders_by_view(view):
        """Get all forwarders for a specific view"""
        results = []
        for forwarder_id, forwarder in dns_forwarders.items():
            if forwarder["view"] == view:
                results.append(forwarder)
        return results
    
    @staticmethod
    def update_forwarder(forwarder_id, data):
        """Update a DNS forwarder configuration"""
        if forwarder_id not in dns_forwarders:
            return None, f"Forwarder not found: {forwarder_id}"
        
        forwarder = dns_forwarders[forwarder_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time", "name", "view"]:
                forwarder[key] = value
        
        forwarder["_modify_time"] = datetime.now().isoformat()
        
        # Update recursion settings if forward_only changed
        if "forward_only" in data and forwarder["view"] in dns_recursion:
            if data["forward_only"]:
                dns_recursion[forwarder["view"]]["forwarders_only"] = True
        
        return forwarder["_ref"], None
    
    @staticmethod
    def delete_forwarder(forwarder_id):
        """Delete a DNS forwarder configuration"""
        if forwarder_id not in dns_forwarders:
            return None, f"Forwarder not found: {forwarder_id}"
        
        # Delete the forwarder
        del dns_forwarders[forwarder_id]
        
        return forwarder_id, None

class RPZManager:
    """Manager for Response Policy Zones (RPZ)"""
    
    @staticmethod
    def create_zone(data):
        """Create a new RPZ zone"""
        if not data.get("name"):
            return None, "Zone name is required"
        
        if not data.get("view"):
            return None, "DNS view is required"
        
        name = data["name"]
        view = data["view"]
        
        # Ensure view exists
        if view not in dns_views:
            return None, f"View not found: {view}"
        
        # Create a unique ID
        zone_id = f"{view}:{name}"
        
        if zone_id in rpz_zones:
            return None, f"RPZ zone already exists for this view: {name}"
        
        # Create the RPZ zone
        zone_data = {
            "_ref": f"rpz/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{zone_id}",
            "name": name,
            "view": view,
            "policy": data.get("policy", "GIVEN"),  # GIVEN, NXDOMAIN, NODATA, PASSTHRU, DROP
            "priority": data.get("priority", 1),
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to RPZ zones
        rpz_zones[zone_id] = zone_data
        
        # Initialize rules
        rpz_rules[zone_id] = []
        
        return zone_data["_ref"], None
    
    @staticmethod
    def get_zone(zone_id):
        """Get an RPZ zone by ID"""
        return rpz_zones.get(zone_id)
    
    @staticmethod
    def get_zones_by_view(view):
        """Get all RPZ zones for a specific view"""
        results = []
        for zone_id, zone in rpz_zones.items():
            if zone["view"] == view:
                results.append(zone)
        return results
    
    @staticmethod
    def update_zone(zone_id, data):
        """Update an RPZ zone"""
        if zone_id not in rpz_zones:
            return None, f"RPZ zone not found: {zone_id}"
        
        zone = rpz_zones[zone_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time", "name", "view"]:
                zone[key] = value
        
        zone["_modify_time"] = datetime.now().isoformat()
        
        return zone["_ref"], None
    
    @staticmethod
    def delete_zone(zone_id):
        """Delete an RPZ zone"""
        if zone_id not in rpz_zones:
            return None, f"RPZ zone not found: {zone_id}"
        
        # Delete the zone
        del rpz_zones[zone_id]
        
        # Delete associated rules
        if zone_id in rpz_rules:
            del rpz_rules[zone_id]
        
        return zone_id, None
    
    @staticmethod
    def add_rule(zone_id, data):
        """Add a rule to an RPZ zone"""
        if zone_id not in rpz_zones:
            return None, f"RPZ zone not found: {zone_id}"
        
        if not data.get("name"):
            return None, "Rule name (pattern) is required"
        
        if not data.get("type"):
            return None, "Rule type is required"
        
        # Validate rule type
        valid_types = ["QNAME", "CLIENT-IP", "NSDNAME", "IP", "WILDCARD"]
        if data["type"] not in valid_types:
            return None, f"Invalid rule type: {data['type']}. Must be one of {valid_types}"
        
        # Create a unique ID
        rule_id = f"{zone_id}:{data['name']}"
        
        # Check if rule already exists
        for rule in rpz_rules[zone_id]:
            if rule["name"] == data["name"] and rule["type"] == data["type"]:
                return None, f"Rule already exists for this pattern: {data['name']}"
        
        # Create the rule
        rule_data = {
            "_ref": f"rpz:rule/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{rule_id}",
            "name": data["name"],
            "type": data["type"],
            "zone": zone_id,
            "action": data.get("action", rpz_zones[zone_id]["policy"]),  # Use zone policy if not specified
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Additional data based on action
        if rule_data["action"] == "GIVEN":
            if "canonical" in data:
                rule_data["canonical"] = data["canonical"]
            elif "ipv4addr" in data:
                rule_data["ipv4addr"] = data["ipv4addr"]
            elif "ipv6addr" in data:
                rule_data["ipv6addr"] = data["ipv6addr"]
        
        # Add to rules
        rpz_rules[zone_id].append(rule_data)
        
        return rule_data["_ref"], None
    
    @staticmethod
    def get_rules(zone_id):
        """Get all rules for an RPZ zone"""
        if zone_id not in rpz_zones:
            return None, f"RPZ zone not found: {zone_id}"
        
        return rpz_rules.get(zone_id, []), None
    
    @staticmethod
    def delete_rule(rule_ref):
        """Delete an RPZ rule"""
        # Parse the zone_id and rule name from the ref
        parts = rule_ref.split(":")
        zone_id = parts[0].replace("rpz:rule/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:", "").split(":")[0]
        rule_name = parts[1]
        
        if zone_id not in rpz_zones:
            return None, f"RPZ zone not found: {zone_id}"
        
        # Find and delete the rule
        for i, rule in enumerate(rpz_rules[zone_id]):
            if rule["_ref"] == rule_ref:
                del rpz_rules[zone_id][i]
                return rule_ref, None
        
        return None, f"Rule not found: {rule_ref}"

class DNSSECManager:
    """Manager for DNSSEC"""
    
    @staticmethod
    def create_key(data):
        """Create a DNSSEC key"""
        if not data.get("zone"):
            return None, "Zone name is required"
        
        if not data.get("view"):
            return None, "DNS view is required"
        
        if not data.get("algorithm"):
            return None, "Algorithm is required"
        
        zone = data["zone"]
        view = data["view"]
        algorithm = data["algorithm"]
        key_type = data.get("key_type", "KSK")  # KSK or ZSK
        
        # Ensure view exists
        if view not in dns_views:
            return None, f"View not found: {view}"
        
        # Create a unique ID
        key_id = f"{view}:{zone}:{key_type}"
        
        if key_id in dnssec_keys:
            return None, f"DNSSEC key already exists for this zone and type: {zone}/{key_type}"
        
        # Generate key data
        key_tag = random.randint(1000, 65535)
        private_key = base64.b64encode(os.urandom(32)).decode('utf-8')
        public_key = base64.b64encode(os.urandom(48)).decode('utf-8')
        
        # Create the key
        key_data = {
            "_ref": f"dnssec:key/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{key_id}",
            "zone": zone,
            "view": view,
            "algorithm": algorithm,
            "key_type": key_type,
            "key_tag": key_tag,
            "public_key": public_key,
            "private_key": private_key,
            "status": "ACTIVE",
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to keys
        dnssec_keys[key_id] = key_data
        
        # Mark zone as DNSSEC-enabled
        dnssec_enabled_zones.add(f"{view}:{zone}")
        
        return key_data["_ref"], None
    
    @staticmethod
    def get_key(key_id):
        """Get a DNSSEC key by ID"""
        return dnssec_keys.get(key_id)
    
    @staticmethod
    def get_keys_by_zone(zone, view):
        """Get all DNSSEC keys for a specific zone"""
        results = []
        zone_prefix = f"{view}:{zone}:"
        for key_id, key in dnssec_keys.items():
            if key_id.startswith(zone_prefix):
                results.append(key)
        return results
    
    @staticmethod
    def update_key(key_id, data):
        """Update a DNSSEC key"""
        if key_id not in dnssec_keys:
            return None, f"DNSSEC key not found: {key_id}"
        
        key = dnssec_keys[key_id]
        
        # Update fields
        for field in ["status", "comment", "extattrs"]:
            if field in data:
                key[field] = data[field]
        
        key["_modify_time"] = datetime.now().isoformat()
        
        return key["_ref"], None
    
    @staticmethod
    def delete_key(key_id):
        """Delete a DNSSEC key"""
        if key_id not in dnssec_keys:
            return None, f"DNSSEC key not found: {key_id}"
        
        # Delete the key
        key = dnssec_keys[key_id]
        del dnssec_keys[key_id]
        
        # Check if there are any keys left for this zone
        view_zone = f"{key['view']}:{key['zone']}"
        has_keys = False
        for k_id in dnssec_keys:
            if k_id.startswith(view_zone):
                has_keys = True
                break
        
        # If no keys left, mark zone as not DNSSEC-enabled
        if not has_keys and view_zone in dnssec_enabled_zones:
            dnssec_enabled_zones.remove(view_zone)
        
        return key_id, None
    
    @staticmethod
    def sign_zone(zone, view):
        """Sign a zone with DNSSEC"""
        view_zone = f"{view}:{zone}"
        
        # Check if the zone has keys
        has_keys = False
        for key_id in dnssec_keys:
            if key_id.startswith(view_zone):
                has_keys = True
                break
        
        if not has_keys:
            return None, f"No DNSSEC keys found for zone: {zone}"
        
        # Mark zone as DNSSEC-enabled
        dnssec_enabled_zones.add(view_zone)
        
        return view_zone, None
    
    @staticmethod
    def unsign_zone(zone, view):
        """Remove DNSSEC signing from a zone"""
        view_zone = f"{view}:{zone}"
        
        if view_zone in dnssec_enabled_zones:
            dnssec_enabled_zones.remove(view_zone)
        
        return view_zone, None
    
    @staticmethod
    def is_zone_signed(zone, view):
        """Check if a zone is signed with DNSSEC"""
        view_zone = f"{view}:{zone}"
        return view_zone in dnssec_enabled_zones
    
    @staticmethod
    def add_trusted_key(data):
        """Add a DNSSEC trusted key"""
        if not data.get("name"):
            return None, "Domain name is required"
        
        if not data.get("algorithm"):
            return None, "Algorithm is required"
        
        if not data.get("public_key"):
            return None, "Public key is required"
        
        name = data["name"]
        algorithm = data["algorithm"]
        public_key = data["public_key"]
        
        # Create a unique ID
        key_id = f"{name}:{algorithm}"
        
        if key_id in dnssec_trusted_keys:
            return None, f"Trusted key already exists: {key_id}"
        
        # Create the trusted key
        key_data = {
            "_ref": f"dnssec:trustedkey/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{key_id}",
            "name": name,
            "algorithm": algorithm,
            "public_key": public_key,
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to trusted keys
        dnssec_trusted_keys[key_id] = key_data
        
        return key_data["_ref"], None
    
    @staticmethod
    def get_trusted_key(key_id):
        """Get a DNSSEC trusted key by ID"""
        return dnssec_trusted_keys.get(key_id)
    
    @staticmethod
    def delete_trusted_key(key_id):
        """Delete a DNSSEC trusted key"""
        if key_id not in dnssec_trusted_keys:
            return None, f"Trusted key not found: {key_id}"
        
        # Delete the key
        del dnssec_trusted_keys[key_id]
        
        return key_id, None

class DNS64Manager:
    """Manager for DNS64 (IPv6-IPv4 translation for DNS)"""
    
    @staticmethod
    def create_dns64(data):
        """Create a DNS64 network configuration"""
        if not data.get("name"):
            return None, "Network name is required"
        
        if not data.get("view"):
            return None, "DNS view is required"
        
        if not data.get("prefix"):
            return None, "IPv6 prefix is required"
        
        name = data["name"]
        view = data["view"]
        prefix = data["prefix"]
        
        # Ensure view exists
        if view not in dns_views:
            return None, f"View not found: {view}"
        
        # Validate prefix is a valid IPv6 network
        try:
            ipaddress.IPv6Network(prefix)
        except ValueError:
            return None, f"Invalid IPv6 prefix: {prefix}"
        
        # Create a unique ID
        dns64_id = f"{view}:{name}"
        
        if dns64_id in dns64_networks:
            return None, f"DNS64 network already exists for this view: {name}"
        
        # Create the DNS64 configuration
        dns64_data = {
            "_ref": f"dns64/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{dns64_id}",
            "name": name,
            "view": view,
            "prefix": prefix,
            "enabled": data.get("enabled", True),
            "clients": data.get("clients", []),
            "excluded": data.get("excluded", []),
            "mapped": data.get("mapped", []),
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to DNS64 networks
        dns64_networks[dns64_id] = dns64_data
        
        return dns64_data["_ref"], None
    
    @staticmethod
    def get_dns64(dns64_id):
        """Get a DNS64 network configuration by ID"""
        return dns64_networks.get(dns64_id)
    
    @staticmethod
    def get_dns64_by_view(view):
        """Get all DNS64 networks for a specific view"""
        results = []
        for dns64_id, dns64 in dns64_networks.items():
            if dns64["view"] == view:
                results.append(dns64)
        return results
    
    @staticmethod
    def update_dns64(dns64_id, data):
        """Update a DNS64 network configuration"""
        if dns64_id not in dns64_networks:
            return None, f"DNS64 network not found: {dns64_id}"
        
        dns64 = dns64_networks[dns64_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time", "name", "view"]:
                dns64[key] = value
        
        dns64["_modify_time"] = datetime.now().isoformat()
        
        return dns64["_ref"], None
    
    @staticmethod
    def delete_dns64(dns64_id):
        """Delete a DNS64 network configuration"""
        if dns64_id not in dns64_networks:
            return None, f"DNS64 network not found: {dns64_id}"
        
        # Delete the DNS64 network
        del dns64_networks[dns64_id]
        
        return dns64_id, None

class QueryRedirectManager:
    """Manager for DNS query redirection"""
    
    @staticmethod
    def create_redirect(data):
        """Create a DNS query redirect rule"""
        if not data.get("name"):
            return None, "Rule name is required"
        
        if not data.get("view"):
            return None, "DNS view is required"
        
        if not data.get("pattern"):
            return None, "Pattern is required"
        
        if not data.get("target"):
            return None, "Target is required"
        
        name = data["name"]
        view = data["view"]
        pattern = data["pattern"]
        target = data["target"]
        
        # Ensure view exists
        if view not in dns_views:
            return None, f"View not found: {view}"
        
        # Create a unique ID
        redirect_id = f"{view}:{name}"
        
        if redirect_id in query_redirects:
            return None, f"Query redirect already exists for this view: {name}"
        
        # Create the redirect rule
        redirect_data = {
            "_ref": f"queryredirect/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{redirect_id}",
            "name": name,
            "view": view,
            "pattern": pattern,
            "target": target,
            "enabled": data.get("enabled", True),
            "comment": data.get("comment", ""),
            "extattrs": data.get("extattrs", {}),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to query redirects
        query_redirects[redirect_id] = redirect_data
        
        return redirect_data["_ref"], None
    
    @staticmethod
    def get_redirect(redirect_id):
        """Get a DNS query redirect rule by ID"""
        return query_redirects.get(redirect_id)
    
    @staticmethod
    def get_redirects_by_view(view):
        """Get all DNS query redirect rules for a specific view"""
        results = []
        for redirect_id, redirect in query_redirects.items():
            if redirect["view"] == view:
                results.append(redirect)
        return results
    
    @staticmethod
    def update_redirect(redirect_id, data):
        """Update a DNS query redirect rule"""
        if redirect_id not in query_redirects:
            return None, f"Query redirect not found: {redirect_id}"
        
        redirect = query_redirects[redirect_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time", "name", "view"]:
                redirect[key] = value
        
        redirect["_modify_time"] = datetime.now().isoformat()
        
        return redirect["_ref"], None
    
    @staticmethod
    def delete_redirect(redirect_id):
        """Delete a DNS query redirect rule"""
        if redirect_id not in query_redirects:
            return None, f"Query redirect not found: {redirect_id}"
        
        # Delete the query redirect
        del query_redirects[redirect_id]
        
        return redirect_id, None

# Initialize default configurations
def init_dns_features():
    """Initialize DNS features with default configurations"""
    # Add default view if it doesn't exist
    if "default" not in dns_views:
        dns_views["default"] = {
            "_ref": "view/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:default",
            "name": "default",
            "is_default": True,
            "comment": "Default DNS view",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
    
    # Initialize recursion settings for default view
    if "default" not in dns_recursion:
        dns_recursion["default"] = {
            "allow_recursion": True,
            "forwarders_only": False,
            "recursion_enabled": True
        }

# Initialize DNS features
init_dns_features()