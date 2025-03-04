"""
Grid and member models for Infoblox Mock Server

This module defines models for grid-related objects such as:
- Grid
- Grid Members
- Grid Services
"""

import re
import ipaddress
from infoblox_mock.models.base import BaseInfobloxObject

class Grid(BaseInfobloxObject):
    """Model for Infoblox grid object"""
    
    obj_type = "grid"
    required_fields = ["name"]
    default_fields = {
        "version": "NIOS 8.6.0",
        "status": "ONLINE",
        "license_type": "ENTERPRISE",
        "allow_recursive_deletion": True,
        "support_email": "support@example.com",
        "restart_status": {
            "restart_required": False
        }
    }
    
    def validate(self):
        """Validate grid object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate status values
        valid_status = ['ONLINE', 'OFFLINE', 'WARNING', 'MAINTENANCE']
        if hasattr(self, 'status') and self.status not in valid_status:
            return False, f"Invalid grid status: {self.status}. Must be one of {valid_status}"
        
        # Validate license type
        valid_licenses = ['ENTERPRISE', 'STANDARD', 'CP', 'CLOUD']
        if hasattr(self, 'license_type') and self.license_type not in valid_licenses:
            return False, f"Invalid license type: {self.license_type}. Must be one of {valid_licenses}"
        
        # Validate email format if provided
        if hasattr(self, 'support_email') and self.support_email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, self.support_email):
                return False, f"Invalid email format: {self.support_email}"
        
        return True, None
    
    def generate_ref(self):
        """Generate reference ID for grid"""
        return f"{self.obj_type}/1"

class Member(BaseInfobloxObject):
    """Model for Infoblox grid member object"""
    
    obj_type = "member"
    required_fields = ["host_name", "config_addr_type"]
    default_fields = {
        "config_addr_type": "IPV4",
        "platform": "PHYSICAL",
        "service_status": "WORKING",
        "node_status": "ONLINE",
        "ha_status": "ACTIVE"
    }
    
    def validate(self):
        """Validate member object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate hostname format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.host_name):
            return False, f"Invalid hostname format: {self.host_name}"
        
        # Validate config address type
        valid_addr_types = ['IPV4', 'IPV6', 'BOTH']
        if self.config_addr_type not in valid_addr_types:
            return False, f"Invalid config address type: {self.config_addr_type}. Must be one of {valid_addr_types}"
        
        # Validate IP address if provided
        if hasattr(self, 'ip_address') and self.ip_address:
            try:
                ipaddress.ip_address(self.ip_address)
            except ValueError:
                return False, f"Invalid IP address format: {self.ip_address}"
        
        # Validate platform type
        valid_platforms = ['PHYSICAL', 'VIRTUAL', 'CLOUD', 'CONTAINER']
        if hasattr(self, 'platform') and self.platform not in valid_platforms:
            return False, f"Invalid platform type: {self.platform}. Must be one of {valid_platforms}"
        
        # Validate service status
        valid_service_status = ['WORKING', 'FAILED', 'PARTIALLY_WORKING', 'UNKNOWN']
        if hasattr(self, 'service_status') and self.service_status not in valid_service_status:
            return False, f"Invalid service status: {self.service_status}. Must be one of {valid_service_status}"
        
        # Validate node status
        valid_node_status = ['ONLINE', 'OFFLINE', 'WARNING', 'UNKNOWN']
        if hasattr(self, 'node_status') and self.node_status not in valid_node_status:
            return False, f"Invalid node status: {self.node_status}. Must be one of {valid_node_status}"
        
        # Validate HA status
        valid_ha_status = ['ACTIVE', 'PASSIVE', 'TRANSITIONING', 'N/A']
        if hasattr(self, 'ha_status') and self.ha_status not in valid_ha_status:
            return False, f"Invalid HA status: {self.ha_status}. Must be one of {valid_ha_status}"
        
        return True, None

class GridService(BaseInfobloxObject):
    """Model for Infoblox grid service object"""
    
    obj_type = "grid:service"
    required_fields = ["name", "type"]
    default_fields = {
        "status": "WORKING",
        "enabled": True
    }
    
    def validate(self):
        """Validate grid service object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate service type
        valid_types = ['DNS', 'DHCP', 'DHCPV6', 'NTP', 'TFTP', 'HTTP', 'FTP', 'TAXII']
        if self.type not in valid_types:
            return False, f"Invalid service type: {self.type}. Must be one of {valid_types}"
        
        # Validate service status
        valid_status = ['WORKING', 'FAILED', 'PARTIALLY_WORKING', 'UNKNOWN']
        if hasattr(self, 'status') and self.status not in valid_status:
            return False, f"Invalid service status: {self.status}. Must be one of {valid_status}"
        
        return True, None

class GridHA(BaseInfobloxObject):
    """Model for Infoblox grid HA (High Availability) configuration"""
    
    obj_type = "grid:ha"
    required_fields = ["mode"]
    default_fields = {
        "mode": "ACTIVE_PASSIVE",
        "status": "SYNCED"
    }
    
    def validate(self):
        """Validate grid HA configuration"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate HA mode
        valid_modes = ['ACTIVE_PASSIVE', 'ACTIVE_ACTIVE', 'NONE']
        if self.mode not in valid_modes:
            return False, f"Invalid HA mode: {self.mode}. Must be one of {valid_modes}"
        
        # Validate status
        valid_status = ['SYNCED', 'SYNCING', 'NOT_SYNCED', 'ERROR']
        if hasattr(self, 'status') and self.status not in valid_status:
            return False, f"Invalid HA status: {self.status}. Must be one of {valid_status}"
        
        return True, None

class GridDNSView(BaseInfobloxObject):
    """Model for Infoblox DNS view object"""
    
    obj_type = "view"
    required_fields = ["name"]
    default_fields = {
        "is_default": False
    }
    
    def validate(self):
        """Validate DNS view object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate name format
        name_pattern = r'^[a-zA-Z0-9_\.-]+$'
        if not re.match(name_pattern, self.name):
            return False, f"Invalid view name: {self.name}. Must contain only alphanumeric characters, underscores, dots, and hyphens"
        
        return True, None