"""
Authentication and security models for Infoblox Mock Server

This module defines models for security-related objects such as:
- Users
- User Groups
- Admin Roles
- Authentication Settings
- Permissions
"""

import re
import hashlib
import os
from datetime import datetime, timedelta
from infoblox_mock.models.base import BaseInfobloxObject

class AdminUser(BaseInfobloxObject):
    """Model for Infoblox admin user object"""
    
    obj_type = "adminuser"
    required_fields = ["name", "password"]
    default_fields = {
        "admin_type": "REGULAR",
        "disable_concurrent_login": False,
        "password_expiry_days": 90,
        "authentication_type": "LOCAL",
        "comment": ""
    }
    
    def __init__(self, **kwargs):
        """Initialize with password hashing"""
        # Hash the password before storing
        if 'password' in kwargs:
            kwargs['password_hash'] = self._hash_password(kwargs['password'])
            del kwargs['password']
        
        super().__init__(**kwargs)
    
    def _hash_password(self, password):
        """Hash a password with salt"""
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        # Store salt with the hash
        return salt.hex() + ':' + key.hex()
    
    def verify_password(self, password):
        """Verify a password against the stored hash"""
        if not hasattr(self, 'password_hash'):
            return False
        
        # Split salt and hash
        salt_hex, key_hex = self.password_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        
        # Hash the provided password with the same salt
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        
        # Compare the keys
        return key == stored_key
    
    def validate(self):
        """Validate admin user object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate username format
        name_pattern = r'^[a-zA-Z0-9_\.-]+$'
        if not re.match(name_pattern, self.name):
            return False, f"Invalid username format: {self.name}. Must contain only alphanumeric characters, underscores, dots, and hyphens"
        
        # Validate admin type
        valid_types = ['SUPER', 'REGULAR', 'RESTRICTED']
        if hasattr(self, 'admin_type') and self.admin_type not in valid_types:
            return False, f"Invalid admin type: {self.admin_type}. Must be one of {valid_types}"
        
        # Validate authentication type
        valid_auth_types = ['LOCAL', 'RADIUS', 'LDAP', 'AD', 'TACACS+']
        if hasattr(self, 'authentication_type') and self.authentication_type not in valid_auth_types:
            return False, f"Invalid authentication type: {self.authentication_type}. Must be one of {valid_auth_types}"
        
        # Ensure password hash exists
        if not hasattr(self, 'password_hash'):
            return False, "Password hash is required"
        
        return True, None

class AdminGroup(BaseInfobloxObject):
    """Model for Infoblox admin group object"""
    
    obj_type = "admingroup"
    required_fields = ["name"]
    default_fields = {
        "comment": "",
        "roles": [],
        "disable_concurrent_login": False,
        "access_via": ["GUI"]
    }
    
    def validate(self):
        """Validate admin group object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate group name format
        name_pattern = r'^[a-zA-Z0-9_\.-]+$'
        if not re.match(name_pattern, self.name):
            return False, f"Invalid group name format: {self.name}. Must contain only alphanumeric characters, underscores, dots, and hyphens"
        
        # Validate access methods
        valid_access = ['GUI', 'API', 'CLI']
        if hasattr(self, 'access_via'):
            for access in self.access_via:
                if access not in valid_access:
                    return False, f"Invalid access method: {access}. Must be one of {valid_access}"
        
        return True, None

class AdminRole(BaseInfobloxObject):
    """Model for Infoblox admin role object"""
    
    obj_type = "adminrole"
    required_fields = ["name"]
    default_fields = {
        "comment": "",
        "permissions": []
    }
    
    def validate(self):
        """Validate admin role object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate role name format
        name_pattern = r'^[a-zA-Z0-9_\.-]+$'
        if not re.match(name_pattern, self.name):
            return False, f"Invalid role name format: {self.name}. Must contain only alphanumeric characters, underscores, dots, and hyphens"
        
        return True, None

class AdminSession(BaseInfobloxObject):
    """Model for Infoblox admin session object"""
    
    obj_type = "session"
    required_fields = ["username", "client_ip"]
    
    def __init__(self, **kwargs):
        """Initialize session with expiration"""
        # Set session creation and expiration times
        kwargs['create_time'] = datetime.now().isoformat()
        kwargs['expire_time'] = (datetime.now() + timedelta(hours=1)).isoformat()
        
        # Generate session token
        if 'token' not in kwargs:
            kwargs['token'] = self._generate_token()
        
        super().__init__(**kwargs)
    
    def _generate_token(self):
        """Generate a random session token"""
        return os.urandom(16).hex()
    
    def is_expired(self):
        """Check if the session has expired"""
        if not hasattr(self, 'expire_time'):
            return True
        
        expire = datetime.fromisoformat(self.expire_time)
        return datetime.now() > expire
    
    def extend(self, hours=1):
        """Extend the session by the specified number of hours"""
        new_expire = datetime.now() + timedelta(hours=hours)
        self.expire_time = new_expire.isoformat()
    
    def validate(self):
        """Validate session object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate username format
        name_pattern = r'^[a-zA-Z0-9_\.-]+$'
        if not re.match(name_pattern, self.username):
            return False, f"Invalid username format: {self.username}"
        
        # Validate IP address format
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, self.client_ip):
            return False, f"Invalid IP address format: {self.client_ip}"
        
        return True, None

class AuthSettings(BaseInfobloxObject):
    """Model for Infoblox authentication settings"""
    
    obj_type = "authsettings"
    required_fields = []
    default_fields = {
        "password_strength": "MEDIUM",
        "min_password_length": 8,
        "lockout_enabled": True,
        "lockout_threshold": 5,
        "lockout_duration": 30,  # minutes
        "inactive_timeout": 60,  # minutes
        "auth_methods": ["LOCAL"],
        "auth_method_priority": ["LOCAL"]
    }
    
    def validate(self):
        """Validate authentication settings"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate password strength
        valid_strengths = ['LOW', 'MEDIUM', 'HIGH']
        if hasattr(self, 'password_strength') and self.password_strength not in valid_strengths:
            return False, f"Invalid password strength: {self.password_strength}. Must be one of {valid_strengths}"
        
        # Validate min password length
        if hasattr(self, 'min_password_length'):
            try:
                length = int(self.min_password_length)
                if length < 1 or length > 64:
                    return False, f"Invalid minimum password length: {length}. Must be between 1 and 64"
            except (ValueError, TypeError):
                return False, f"Invalid minimum password length format: {self.min_password_length}"
        
        # Validate authentication methods
        valid_methods = ['LOCAL', 'RADIUS', 'LDAP', 'AD', 'TACACS+']
        if hasattr(self, 'auth_methods'):
            for method in self.auth_methods:
                if method not in valid_methods:
                    return False, f"Invalid authentication method: {method}. Must be one of {valid_methods}"
        
        # Validate method priority - must be subset of auth_methods
        if hasattr(self, 'auth_method_priority') and hasattr(self, 'auth_methods'):
            for method in self.auth_method_priority:
                if method not in self.auth_methods:
                    return False, f"Authentication method priority {method} not in auth_methods"
        
        return True, None

class Permission(BaseInfobloxObject):
    """Model for Infoblox permission object"""
    
    obj_type = "permission"
    required_fields = ["resource", "permission"]
    default_fields = {}
    
    def validate(self):
        """Validate permission object"""
        # Check parent validation first
        valid, msg = super().validate()
        if not valid:
            return valid, msg
        
        # Validate permission type
        valid_permissions = ['READ', 'WRITE', 'CREATE', 'DELETE', 'ADMIN', 'DENY']
        if self.permission not in valid_permissions:
            return False, f"Invalid permission type: {self.permission}. Must be one of {valid_permissions}"
        
        # Validate resource format
        resource_pattern = r'^[a-zA-Z0-9_\.:/-]+$'
        if not re.match(resource_pattern, self.resource):
            return False, f"Invalid resource format: {self.resource}"
        
        return True, None