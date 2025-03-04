"""
DNS record models for Infoblox Mock Server

This module defines models for various DNS record types:
- A Records
- AAAA Records
- CNAME Records
- MX Records
- TXT Records
- SRV Records
- PTR Records
- NS Records
- SOA Records
- DNSSEC Records
"""

import ipaddress
import re
import base64
from infoblox_mock.models.base import BaseInfobloxObject

class DNSRecordBase(BaseInfobloxObject):
    """Base class for all DNS record types"""
    
    default_fields = {
        "view": "default",
        "ttl": 3600,
        "extattrs": {},
        "use_ttl": False,
    }
    
    def validate(self):
        """Common validation for DNS records"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate hostname format for name field
        if hasattr(self, 'name'):
            hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
            if not re.match(hostname_pattern, self.name):
                return False, f"Invalid hostname format for name: {self.name}"
        
        return True, None

class ARecord(DNSRecordBase):
    """Model for A records"""
    
    obj_type = "record:a"
    required_fields = ["name", "ipv4addr"]
    
    def validate(self):
        """Validate A record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate IPv4 format
        try:
            ip = ipaddress.IPv4Address(self.ipv4addr)
        except ValueError:
            return False, f"Invalid IPv4 address: {self.ipv4addr}"
        
        return True, None

class AAAARecord(DNSRecordBase):
    """Model for AAAA records"""
    
    obj_type = "record:aaaa"
    required_fields = ["name", "ipv6addr"]
    
    def validate(self):
        """Validate AAAA record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate IPv6 format
        try:
            ip = ipaddress.IPv6Address(self.ipv6addr)
        except ValueError:
            return False, f"Invalid IPv6 address: {self.ipv6addr}"
        
        return True, None

class CNAMERecord(DNSRecordBase):
    """Model for CNAME records"""
    
    obj_type = "record:cname"
    required_fields = ["name", "canonical"]
    
    def validate(self):
        """Validate CNAME record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate canonical format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.canonical):
            return False, f"Invalid hostname format for canonical: {self.canonical}"
        
        return True, None

class MXRecord(DNSRecordBase):
    """Model for MX records"""
    
    obj_type = "record:mx"
    required_fields = ["name", "mail_exchanger", "preference"]
    
    def validate(self):
        """Validate MX record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate mail_exchanger format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.mail_exchanger):
            return False, f"Invalid hostname format for mail_exchanger: {self.mail_exchanger}"
        
        # Validate preference (0-65535)
        try:
            pref = int(self.preference)
            if pref < 0 or pref > 65535:
                return False, f"Preference must be between 0 and 65535, got: {pref}"
        except (ValueError, TypeError):
            return False, f"Invalid preference value: {self.preference}"
        
        return True, None

class TXTRecord(DNSRecordBase):
    """Model for TXT records"""
    
    obj_type = "record:txt"
    required_fields = ["name", "text"]
    
    def validate(self):
        """Validate TXT record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate text length (Infoblox typically limits to 255 chars per TXT record)
        if len(self.text) > 255:
            return False, f"TXT record text exceeds 255 characters: {len(self.text)}"
        
        return True, None

class PTRRecord(DNSRecordBase):
    """Model for PTR records"""
    
    obj_type = "record:ptr"
    required_fields = ["ptrdname"]
    
    def validate(self):
        """Validate PTR record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate ptrdname format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.ptrdname):
            return False, f"Invalid hostname format for ptrdname: {self.ptrdname}"
        
        # Require either ipv4addr or ipv6addr
        if not hasattr(self, 'ipv4addr') and not hasattr(self, 'ipv6addr'):
            return False, "PTR record must have either ipv4addr or ipv6addr"
        
        # Validate IP address format
        if hasattr(self, 'ipv4addr'):
            try:
                ipaddress.IPv4Address(self.ipv4addr)
            except ValueError:
                return False, f"Invalid IPv4 address: {self.ipv4addr}"
        
        if hasattr(self, 'ipv6addr'):
            try:
                ipaddress.IPv6Address(self.ipv6addr)
            except ValueError:
                return False, f"Invalid IPv6 address: {self.ipv6addr}"
        
        return True, None

class SRVRecord(DNSRecordBase):
    """Model for SRV records"""
    
    obj_type = "record:srv"
    required_fields = ["name", "target", "priority", "weight", "port"]
    
    def validate(self):
        """Validate SRV record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate SRV name format (_service._proto.name format)
        srv_pattern = r'^_[a-zA-Z0-9-]+\._[a-zA-Z0-9-]+\.(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(srv_pattern, self.name) and not self.name.startswith('_'):
            return False, f"Invalid SRV record name format: {self.name}"
        
        # Validate target format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.target) and self.target != '.':
            return False, f"Invalid hostname format for target: {self.target}"
        
        # Validate numeric fields
        try:
            priority = int(self.priority)
            weight = int(self.weight)
            port = int(self.port)
            
            if priority < 0 or priority > 65535:
                return False, f"Priority must be between 0 and 65535, got: {priority}"
            
            if weight < 0 or weight > 65535:
                return False, f"Weight must be between 0 and 65535, got: {weight}"
            
            if port < 0 or port > 65535:
                return False, f"Port must be between 0 and 65535, got: {port}"
            
        except (ValueError, TypeError):
            return False, "Invalid numeric value for priority, weight, or port"
        
        return True, None

class NSRecord(DNSRecordBase):
    """Model for NS records"""
    
    obj_type = "record:ns"
    required_fields = ["name", "nameserver"]
    
    def validate(self):
        """Validate NS record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate nameserver format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.nameserver):
            return False, f"Invalid hostname format for nameserver: {self.nameserver}"
        
        return True, None

class SOARecord(DNSRecordBase):
    """Model for SOA records"""
    
    obj_type = "record:soa"
    required_fields = ["name", "primary", "email"]
    default_fields = {
        "view": "default",
        "ttl": 3600,
        "extattrs": {},
        "refresh": 10800,
        "retry": 3600,
        "expire": 604800,
        "minimum": 86400,
        "use_ttl": False,
    }
    
    def validate(self):
        """Validate SOA record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate primary format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.primary):
            return False, f"Invalid hostname format for primary: {self.primary}"
        
        # Validate email format (in domain format, not with @)
        if not re.match(hostname_pattern, self.email):
            return False, f"Invalid email format for SOA: {self.email}"
        
        # Validate numeric fields if present
        numeric_fields = ['serial', 'refresh', 'retry', 'expire', 'minimum']
        for field in numeric_fields:
            if hasattr(self, field):
                try:
                    value = int(getattr(self, field))
                    if value < 0:
                        return False, f"{field} must be positive, got: {value}"
                except (ValueError, TypeError):
                    return False, f"Invalid numeric value for {field}: {getattr(self, field)}"
        
        return True, None

class CAARecord(DNSRecordBase):
    """Model for CAA records"""
    
    obj_type = "record:caa"
    required_fields = ["name", "flag", "tag", "ca_value"]
    
    def validate(self):
        """Validate CAA record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate flag (0-255)
        try:
            flag = int(self.flag)
            if flag < 0 or flag > 255:
                return False, f"Flag must be between 0 and 255, got: {flag}"
        except (ValueError, TypeError):
            return False, f"Invalid flag value: {self.flag}"
        
        # Validate tag (must be one of: issue, issuewild, iodef)
        valid_tags = ["issue", "issuewild", "iodef"]
        if self.tag not in valid_tags:
            return False, f"Tag must be one of {valid_tags}, got: {self.tag}"
        
        return True, None

class DNSKEYRecord(DNSRecordBase):
    """Model for DNSKEY records"""
    
    obj_type = "record:dnskey"
    required_fields = ["name", "algorithm", "flags", "public_key"]
    
    def validate(self):
        """Validate DNSKEY record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate algorithm (1-255)
        try:
            algo = int(self.algorithm)
            if algo < 1 or algo > 255:
                return False, f"Algorithm must be between 1 and 255, got: {algo}"
        except (ValueError, TypeError):
            return False, f"Invalid algorithm value: {self.algorithm}"
        
        # Validate flags (0, 256, or 257)
        try:
            flags = int(self.flags)
            if flags not in [0, 256, 257]:
                return False, f"Flags must be 0, 256, or 257, got: {flags}"
        except (ValueError, TypeError):
            return False, f"Invalid flags value: {self.flags}"
        
        # Validate public_key (base64 format)
        try:
            if isinstance(self.public_key, str):
                # Add padding if needed
                key = self.public_key
                padding_needed = len(key) % 4
                if padding_needed:
                    key += '=' * (4 - padding_needed)
                
                # Attempt to decode
                base64.b64decode(key)
            else:
                return False, "public_key must be a string"
        except Exception:
            return False, f"Invalid base64 format for public_key"
        
        return True, None

class RRSIGRecord(DNSRecordBase):
    """Model for RRSIG records"""
    
    obj_type = "record:rrsig"
    required_fields = ["name", "record_type", "algorithm", "key_tag", 
                       "signer_name", "signature", "inception", "expiration"]
    
    def validate(self):
        """Validate RRSIG record"""
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate algorithm (1-255)
        try:
            algo = int(self.algorithm)
            if algo < 1 or algo > 255:
                return False, f"Algorithm must be between 1 and 255, got: {algo}"
        except (ValueError, TypeError):
            return False, f"Invalid algorithm value: {self.algorithm}"
        
        # Validate key_tag (1-65535)
        try:
            tag = int(self.key_tag)
            if tag < 1 or tag > 65535:
                return False, f"Key tag must be between 1 and 65535, got: {tag}"
        except (ValueError, TypeError):
            return False, f"Invalid key_tag value: {self.key_tag}"
        
        # Validate signer_name format
        hostname_pattern = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        if not re.match(hostname_pattern, self.signer_name):
            return False, f"Invalid hostname format for signer_name: {self.signer_name}"
        
        # Validate signature (base64 format)
        try:
            if isinstance(self.signature, str):
                # Add padding if needed
                sig = self.signature
                padding_needed = len(sig) % 4
                if padding_needed:
                    sig += '=' * (4 - padding_needed)
                
                # Attempt to decode
                base64.b64decode(sig)
            else:
                return False, "signature must be a string"
        except Exception:
            return False, f"Invalid base64 format for signature"
        
        # Validate inception and expiration (YYYYMMDDHHmmSS format)
        timestamp_pattern = r'^\d{14}$'
        if not re.match(timestamp_pattern, self.inception):
            return False, f"Invalid timestamp format for inception: {self.inception}"
        
        if not re.match(timestamp_pattern, self.expiration):
            return False, f"Invalid timestamp format for expiration: {self.expiration}"
        
        return True, None