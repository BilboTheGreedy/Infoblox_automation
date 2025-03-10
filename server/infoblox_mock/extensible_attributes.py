"""
Extensible attributes configuration and management for Infoblox Mock Server
Implements custom extensible attributes with validation and definition
"""

import logging
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Extensible attributes definitions
ea_definitions = {}

class ExtensibleAttributeDefinitionManager:
    """Manager for extensible attribute definitions"""
    
    @staticmethod
    def create_definition(data):
        """Create a new extensible attribute definition"""
        if not data.get("name"):
            return None, "Attribute name is required"
        
        name = data["name"]
        
        # Check if already exists
        if name in ea_definitions:
            return None, f"Attribute definition already exists: {name}"
        
        # Create the definition
        definition = {
            "_ref": f"extensibleattributedef/{name}",
            "name": name,
            "type": data.get("type", "STRING"),  # STRING, INTEGER, BOOLEAN, DATE, EMAIL, URL, ENUM
            "flags": data.get("flags", ""),
            "list_values": data.get("list_values", False),
            "comment": data.get("comment", ""),
            "allowed_values": data.get("allowed_values", []),
            "default_value": data.get("default_value", ""),
            "max_value": data.get("max_value", 0),
            "min_value": data.get("min_value", 0),
            "object_types": data.get("object_types", []),
            "required": data.get("required", False),
            "searchable": data.get("searchable", True),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Validate type
        valid_types = ["STRING", "INTEGER", "BOOLEAN", "DATE", "EMAIL", "URL", "ENUM"]
        if definition["type"] not in valid_types:
            return None, f"Invalid attribute type: {definition['type']}. Must be one of {valid_types}"
        
        # For ENUM type, allowed_values is required
        if definition["type"] == "ENUM" and not definition["allowed_values"]:
            return None, "ENUM type requires allowed_values"
        
        # Add to definitions
        ea_definitions[name] = definition
        
        return definition["_ref"], None
    
    @staticmethod
    def get_definition(name):
        """Get an extensible attribute definition by name"""
        if name not in ea_definitions:
            return None, f"Attribute definition not found: {name}"
        
        return ea_definitions[name], None
    
    @staticmethod
    def get_all_definitions():
        """Get all extensible attribute definitions"""
        return list(ea_definitions.values())
    
    @staticmethod
    def update_definition(name, data):
        """Update an extensible attribute definition"""
        if name not in ea_definitions:
            return None, f"Attribute definition not found: {name}"
        
        definition = ea_definitions[name]
        
        # Update fields (excluding immutable ones)
        immutable_fields = ["_ref", "_create_time", "name", "type"]
        for key, value in data.items():
            if key not in immutable_fields:
                definition[key] = value
        
        definition["_modify_time"] = datetime.now().isoformat()
        
        return definition["_ref"], None
    
    @staticmethod
    def delete_definition(name):
        """Delete an extensible attribute definition"""
        if name not in ea_definitions:
            return None, f"Attribute definition not found: {name}"
        
        # Delete the definition
        del ea_definitions[name]
        
        # In a real implementation, this would also update objects with this EA
        
        return name, None
    
    @staticmethod
    def validate_value(name, value):
        """Validate a value against its attribute definition"""
        if name not in ea_definitions:
            return False, f"Attribute definition not found: {name}"
        
        definition = ea_definitions[name]
        
        # Check if value is allowed to be empty
        if value is None or value == "":
            if definition["required"]:
                return False, f"Attribute {name} is required"
            return True, None
        
        # Validate based on type
        attr_type = definition["type"]
        
        if attr_type == "STRING":
            if not isinstance(value, str):
                return False, f"Attribute {name} must be a string"
        
        elif attr_type == "INTEGER":
            try:
                int_value = int(value)
                
                # Check min/max if defined
                if definition["min_value"] and int_value < definition["min_value"]:
                    return False, f"Attribute {name} must be at least {definition['min_value']}"
                
                if definition["max_value"] and int_value > definition["max_value"]:
                    return False, f"Attribute {name} must be at most {definition['max_value']}"
                
            except (ValueError, TypeError):
                return False, f"Attribute {name} must be an integer"
        
        elif attr_type == "BOOLEAN":
            if not isinstance(value, bool) and value not in ["true", "false", "True", "False"]:
                return False, f"Attribute {name} must be a boolean"
        
        elif attr_type == "DATE":
            try:
                # Try to parse as ISO date
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return False, f"Attribute {name} must be a valid date (ISO format)"
        
        elif attr_type == "EMAIL":
            if not isinstance(value, str):
                return False, f"Attribute {name} must be a string"
            
            # Simple email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return False, f"Attribute {name} must be a valid email address"
        
        elif attr_type == "URL":
            if not isinstance(value, str):
                return False, f"Attribute {name} must be a string"
            
            # Simple URL validation
            url_pattern = r'^(http|https)://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
            if not re.match(url_pattern, value):
                return False, f"Attribute {name} must be a valid URL"
        
        elif attr_type == "ENUM":
            if value not in definition["allowed_values"]:
                return False, f"Attribute {name} must be one of {definition['allowed_values']}"
        
        return True, None
    
    @staticmethod
    def get_applicable_definitions(obj_type):
        """Get all EA definitions applicable to an object type"""
        applicable = []
        
        for name, definition in ea_definitions.items():
            object_types = definition.get("object_types", [])
            if not object_types or obj_type in object_types:
                applicable.append(definition)
        
        return applicable
    
    @staticmethod
    def validate_extattrs(obj_type, extattrs):
        """Validate all extensible attributes for an object"""
        if not extattrs:
            return True, None
        
        # Get applicable definitions
        applicable_defs = ExtensibleAttributeDefinitionManager.get_applicable_definitions(obj_type)
        applicable_names = [d["name"] for d in applicable_defs]
        
        # Check each attribute
        for name, value in extattrs.items():
            # Skip internal attributes
            if name.startswith('_'):
                continue
            
            # Check if this attribute is applicable
            if name not in applicable_names:
                return False, f"Attribute {name} is not applicable to {obj_type}"
            
            # Extract the actual value from EA format
            actual_value = value
            if isinstance(value, dict) and "value" in value:
                actual_value = value["value"]
            
            # Validate the value
            valid, error = ExtensibleAttributeDefinitionManager.validate_value(name, actual_value)
            if not valid:
                return False, error
        
        # Check for required attributes
        for definition in applicable_defs:
            if definition["required"] and definition["name"] not in extattrs:
                return False, f"Required attribute {definition['name']} is missing"
        
        return True, None

# Initialize with some default EA definitions
def init_ea_definitions():
    """Initialize extensible attribute definitions with defaults"""
    defaults = [
        {
            "name": "Location",
            "type": "STRING",
            "comment": "Physical location",
            "searchable": True
        },
        {
            "name": "Department",
            "type": "STRING",
            "comment": "Department owner",
            "searchable": True
        },
        {
            "name": "Owner",
            "type": "STRING",
            "comment": "Person or team owner",
            "searchable": True
        },
        {
            "name": "Environment",
            "type": "ENUM",
            "allowed_values": ["Production", "Development", "Test", "Staging"],
            "comment": "Deployment environment",
            "searchable": True
        },
        {
            "name": "CostCenter",
            "type": "STRING",
            "comment": "Cost center code",
            "searchable": True
        }
    ]
    
    for default in defaults:
        if default["name"] not in ea_definitions:
            ExtensibleAttributeDefinitionManager.create_definition(default)

# Initialize extensible attribute definitions
init_ea_definitions()

# Function to validate EA inheritance
def process_ea_inheritance(parent_obj, child_obj):
    """Process EA inheritance from parent to child object"""
    # Skip if either object doesn't have EAs
    if not parent_obj.get("extattrs") or not child_obj.get("extattrs"):
        return child_obj
    
    # Process each parent EA
    for name, value in parent_obj["extattrs"].items():
        # Only inherit if the attribute is marked for inheritance
        if isinstance(value, dict) and value.get("inheritance", False):
            # Only inherit if child doesn't already have this EA
            if name not in child_obj["extattrs"]:
                child_obj["extattrs"][name] = {
                    "value": value.get("value", ""),
                    "inheritance": True,
                    "inherited_from": parent_obj.get("_ref", "")
                }
    
    return child_obj

# Add validation hook to database operations
def validate_extattrs_hook(obj_type, data):
    """Hook to validate EAs before storing"""
    if "extattrs" in data:
        valid, error = ExtensibleAttributeDefinitionManager.validate_extattrs(obj_type, data["extattrs"])
        if not valid:
            return False, error
    
    return True, None

# Add hooks for inheritance
def process_inheritance_hooks():
    """Register hooks for EA inheritance"""
    from infoblox_mock.db import db_hooks
    
    # Add validation hook
    db_hooks["pre_create"] = validate_extattrs_hook
    db_hooks["pre_update"] = validate_extattrs_hook
    
    # Add inheritance hook
    db_hooks["post_get"] = process_ea_inheritance