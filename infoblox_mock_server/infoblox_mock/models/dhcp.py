"""
DHCP-related models for Infoblox Mock Server

This module defines models for DHCP objects such as:
- Fixed Addresses
- DHCP Leases
- DHCP Options
"""

import ipaddress
import re
from datetime import datetime
from infoblox_mock.models.base import BaseInfobloxObject

class FixedAddress(BaseInfobloxObject):
    """Model for Infoblox fixed address objects"""
    
    obj_type = "fixedaddress"
    required_fields = ["ipv4addr", "mac"]
    default_fields = {
        "network_view": "default",
        "extattrs": {}
    }
    
    def validate(self):
        """Validate fixed address object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate IPv4 address format
        try:
            ipaddress.IPv4Address(self.ipv4addr)
        except ValueError:
            return False, f"Invalid IPv4 address: {self.ipv4addr}"
        
        # Validate MAC address format
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$'
        if not re.match(mac_pattern, self.mac):
            return False, f"Invalid MAC address format: {self.mac}"
        
        # Validate hostname if provided
        if hasattr(self, 'name') and self.name:
            hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
            if not re.match(hostname_pattern, self.name):
                return False, f"Invalid hostname format: {self.name}"
        
        return True, None
    
    def generate_ref(self):
        """Generate reference ID for fixed address"""
        encoded = "ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA"
        return f"{self.obj_type}/{encoded}:{self.ipv4addr}"

class Lease(BaseInfobloxObject):
    """Model for Infoblox DHCP lease objects"""
    
    obj_type = "lease"
    required_fields = ["ipv4addr", "mac", "binding_state"]
    default_fields = {
        "network_view": "default",
        "binding_state": "active",
        "hardware": "Ethernet"
    }
    
    def validate(self):
        """Validate lease object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate IPv4 address format
        try:
            ipaddress.IPv4Address(self.ipv4addr)
        except ValueError:
            return False, f"Invalid IPv4 address: {self.ipv4addr}"
        
        # Validate MAC address format
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$'
        if not re.match(mac_pattern, self.mac):
            return False, f"Invalid MAC address format: {self.mac}"
        
        # Validate binding state (active, free, backup, etc.)
        valid_states = ['active', 'free', 'backup', 'abandoned', 'released']
        if self.binding_state not in valid_states:
            return False, f"Invalid binding state: {self.binding_state}. Must be one of {valid_states}"
        
        # Validate client hostname if provided
        if hasattr(self, 'client_hostname') and self.client_hostname:
            hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
            if not re.match(hostname_pattern, self.client_hostname):
                return False, f"Invalid hostname format: {self.client_hostname}"
        
        # Validate date formats if provided
        datetime_fields = ['starts', 'ends', 'last_seen']
        for field in datetime_fields:
            if hasattr(self, field) and getattr(self, field):
                try:
                    # Simple validation - could be enhanced to check format more specifically
                    datetime.fromisoformat(getattr(self, field).replace(' ', 'T'))
                except ValueError:
                    return False, f"Invalid datetime format for {field}: {getattr(self, field)}"
        
        return True, None
    
    def generate_ref(self):
        """Generate reference ID for lease"""
        encoded = "ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA"
        return f"{self.obj_type}/{encoded}:{self.ipv4addr}"

class DHCPOption(BaseInfobloxObject):
    """Model for Infoblox DHCP option objects"""
    
    obj_type = "option"
    required_fields = ["name", "code", "value"]
    default_fields = {
        "option_space": "DHCP",
        "value_type": "STRING"
    }
    
    def validate(self):
        """Validate DHCP option object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate option code (1-255)
        try:
            code = int(self.code)
            if code < 1 or code > 255:
                return False, f"Invalid option code: {code}. Must be between 1 and 255"
        except (ValueError, TypeError):
            return False, f"Invalid option code format: {self.code}"
        
        # Validate value type
        valid_types = ['STRING', 'BYTE', 'INTEGER', 'BOOLEAN', 'ENCAPSULATED', 'BINARY', 'IP', 'IP_MAC']
        if hasattr(self, 'value_type') and self.value_type not in valid_types:
            return False, f"Invalid value type: {self.value_type}. Must be one of {valid_types}"
        
        # Validate value based on value_type
        if hasattr(self, 'value_type'):
            value_type = self.value_type
            if value_type == 'IP':
                try:
                    ipaddress.ip_address(self.value)
                except ValueError:
                    return False, f"Invalid IP address format for option value: {self.value}"
            elif value_type == 'INTEGER':
                try:
                    int(self.value)
                except (ValueError, TypeError):
                    return False, f"Invalid integer format for option value: {self.value}"
            elif value_type == 'BOOLEAN':
                if self.value not in ['true', 'false', True, False]:
                    return False, f"Invalid boolean value: {self.value}"
        
        return True, None

class DHCPOptionSpace(BaseInfobloxObject):
    """Model for Infoblox DHCP option space objects"""
    
    obj_type = "optionspace"
    required_fields = ["name"]
    
    def validate(self):
        """Validate DHCP option space object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate name format (alphanumeric with underscores)
        name_pattern = r'^[a-zA-Z0-9_]+$'
        if not re.match(name_pattern, self.name):
            return False, f"Invalid option space name: {self.name}. Must be alphanumeric with underscores"
        
        return True, None