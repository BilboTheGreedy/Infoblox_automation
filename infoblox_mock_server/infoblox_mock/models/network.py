"""
Network-related models for Infoblox Mock Server

This module defines models for network objects such as:
- Networks
- Network Containers
- DHCP Ranges
"""

from datetime import datetime
import ipaddress
from infoblox_mock.models.base import BaseInfobloxObject

class Network(BaseInfobloxObject):
    """Model for Infoblox network objects"""
    
    obj_type = "network"
    required_fields = ["network"]
    default_fields = {
        "network_view": "default",
        "extattrs": {}
    }
    
    def validate(self):
        """Validate network object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate network CIDR format
        try:
            ipaddress.ip_network(self.network, strict=False)
        except ValueError:
            return False, f"Invalid network format: {self.network}"
        
        return True, None

class NetworkContainer(BaseInfobloxObject):
    """Model for Infoblox network container objects"""
    
    obj_type = "network_container"
    required_fields = ["network"]
    default_fields = {
        "network_view": "default",
        "extattrs": {}
    }
    
    def validate(self):
        """Validate network container object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate network CIDR format
        try:
            ipaddress.ip_network(self.network, strict=False)
        except ValueError:
            return False, f"Invalid network format: {self.network}"
        
        return True, None

class Range(BaseInfobloxObject):
    """Model for Infoblox DHCP range objects"""
    
    obj_type = "range"
    required_fields = ["start_addr", "end_addr"]
    default_fields = {
        "network_view": "default",
        "extattrs": {}
    }
    
    def validate(self):
        """Validate range object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate IP address formats
        try:
            start = ipaddress.ip_address(self.start_addr)
            end = ipaddress.ip_address(self.end_addr)
            
            # Ensure start address is less than or equal to end address
            if start > end:
                return False, f"Start address {self.start_addr} is greater than end address {self.end_addr}"
            
            # If network is specified, ensure IPs are within the network
            if hasattr(self, 'network') and self.network:
                net = ipaddress.ip_network(self.network, strict=False)
                if start not in net or end not in net:
                    return False, f"IP range {self.start_addr}-{self.end_addr} not contained in network {self.network}"
            
        except ValueError as e:
            return False, f"Invalid IP address format: {str(e)}"
        
        return True, None
    
    def generate_ref(self):
        """Generate reference ID for range"""
        encoded = "ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA"
        return f"{self.obj_type}/{encoded}:{self.start_addr}-{self.end_addr}"