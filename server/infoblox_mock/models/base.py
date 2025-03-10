"""
Base model functionality for Infoblox Mock Server

This module defines the base classes and functionality for all models.
"""

from datetime import datetime
import uuid
import json

class BaseInfobloxObject:
    """Base class for all Infoblox objects"""
    
    # Object type (to be defined by subclasses)
    obj_type = None
    
    # Required fields (to be defined by subclasses)
    required_fields = []
    
    # Fields with default values
    default_fields = {}
    
    def __init__(self, **kwargs):
        """Initialize the object with provided attributes"""
        # Set default values
        for field, value in self.default_fields.items():
            setattr(self, field, value)
        
        # Set provided values
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # Add timestamps if not provided
        if not hasattr(self, '_create_time'):
            self._create_time = datetime.now().isoformat()
        
        if not hasattr(self, '_modify_time'):
            self._modify_time = self._create_time
        
        # Generate reference if not provided
        if not hasattr(self, '_ref'):
            self._ref = self.generate_ref()
    
    def validate(self):
        """Validate the object"""
        # Check required fields
        for field in self.required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                return False, f"Missing required field: {field}"
        
        return True, None
    
    def generate_ref(self):
        """Generate a reference ID for this object"""
        if not self.obj_type:
            raise ValueError("Object type not defined")
        
        encoded = str(uuid.uuid4()).replace("-", "")[:24]
        
        # Different reference formats based on object type
        if hasattr(self, 'name'):
            return f"{self.obj_type}/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{self.name}"
        elif hasattr(self, 'network'):
            return f"{self.obj_type}/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:{self.network}"
        else:
            return f"{self.obj_type}/{encoded}"
    
    def to_dict(self):
        """Convert the object to a dictionary"""
        result = {}
        for key, value in self.__dict__.items():
            # Skip private attributes (except _ref)
            if key.startswith('_') and key != '_ref':
                continue
            result[key] = value
        return result
    
    def update(self, **kwargs):
        """Update the object with new values"""
        for key, value in kwargs.items():
            if key != '_ref':  # Don't allow changing the reference
                setattr(self, key, value)
        
        # Update modification time
        self._modify_time = datetime.now().isoformat()
    
    def __str__(self):
        """String representation of the object"""
        return json.dumps(self.to_dict(), indent=2)

# This file would normally contain more base classes and functionality,
# but this provides a starting point for the model-based architecture.