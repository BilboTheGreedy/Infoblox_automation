"""
Smart Folder implementation for Infoblox Mock Server
"""

import logging
import uuid
import re
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# Smart folder storage
smart_folders = {}

class SmartFolderManager:
    """Manager for Smart Folders"""
    
    @staticmethod
    def create_folder(data):
        """Create a new Smart Folder"""
        if not data.get("name"):
            return None, "Folder name is required"
        
        if not data.get("query_params") and not data.get("query"):
            return None, "Either query_params or query is required"
        
        # Generate a unique ID
        folder_id = str(uuid.uuid4())
        
        # Create the folder
        folder_data = {
            "_ref": f"smartfolder/{folder_id}",
            "name": data["name"],
            "query": data.get("query", ""),
            "query_params": data.get("query_params", {}),
            "object_types": data.get("object_types", []),
            "description": data.get("description", ""),
            "owner": data.get("owner", "admin"),
            "is_shared": data.get("is_shared", False),
            "is_default": data.get("is_default", False),
            "comment": data.get("comment", ""),
            "views": data.get("views", []),
            "tags": data.get("tags", []),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to folders
        smart_folders[folder_id] = folder_data
        
        return folder_data["_ref"], None
    
    @staticmethod
    def get_folder(folder_id):
        """Get a Smart Folder by ID"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        return smart_folders[folder_id], None
    
    @staticmethod
    def get_folder_by_name(name):
        """Get a Smart Folder by name"""
        for folder_id, folder in smart_folders.items():
            if folder["name"] == name:
                return folder, None
        
        return None, f"Smart Folder not found: {name}"
    
    @staticmethod
    def update_folder(folder_id, data):
        """Update a Smart Folder"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        folder = smart_folders[folder_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time"]:
                folder[key] = value
        
        folder["_modify_time"] = datetime.now().isoformat()
        
        return folder["_ref"], None
    
    @staticmethod
    def delete_folder(folder_id):
        """Delete a Smart Folder"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        # Delete the folder
        del smart_folders[folder_id]
        
        return folder_id, None
    
    @staticmethod
    def get_all_folders(owner=None, shared=True):
        """Get all Smart Folders, optionally filtered by owner"""
        result = []
        
        for folder in smart_folders.values():
            if owner is None or folder["owner"] == owner or (shared and folder["is_shared"]):
                result.append(folder)
        
        return result
    
    @staticmethod
    def get_folder_contents(folder_id):
        """Get the contents of a Smart Folder"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        folder = smart_folders[folder_id]
        
        # Get the search parameters
        query = folder["query"]
        query_params = folder["query_params"]
        object_types = folder["object_types"]
        
        from infoblox_mock.db import db, find_objects_by_query
        
        results = []
        
        # If no specific object types, search all types
        if not object_types:
            object_types = [obj_type for obj_type in db.keys() if not obj_type.startswith('_')]
        
        # Search for objects
        for obj_type in object_types:
            # Skip special collections
            if obj_type.startswith('_') or obj_type in ['activeuser', 'rate_limit_data']:
                continue
            
            # If there's a text query, do a manual search
            if query:
                for obj in db.get(obj_type, []):
                    if SmartFolderManager._matches_query(obj, query):
                        results.append({
                            "object_type": obj_type,
                            "ref": obj.get("_ref", ""),
                            "data": obj
                        })
            else:
                # Use the standard query mechanism
                objects = find_objects_by_query(obj_type, query_params)
                for obj in objects:
                    results.append({
                        "object_type": obj_type,
                        "ref": obj.get("_ref", ""),
                        "data": obj
                    })
        
        return results, None
    
    @staticmethod
    def _matches_query(obj, query):
        """Check if an object matches a text query"""
        # Convert query to lowercase for case-insensitive search
        query = query.lower()
        
        # Check common fields
        for field in ["name", "comment", "network", "ipv4addr", "ipv6addr", "host_name"]:
            if field in obj and isinstance(obj[field], str) and query in obj[field].lower():
                return True
        
        # Check nested fields
        if "ipv4addrs" in obj:
            for addr in obj["ipv4addrs"]:
                if "ipv4addr" in addr and query in addr["ipv4addr"].lower():
                    return True
        
        if "ipv6addrs" in obj:
            for addr in obj["ipv6addrs"]:
                if "ipv6addr" in addr and query in addr["ipv6addr"].lower():
                    return True
        
        # Check extensible attributes
        if "extattrs" in obj:
            for attr_name, attr_value in obj["extattrs"].items():
                if attr_name.lower() == query:
                    return True
                
                if isinstance(attr_value, dict) and "value" in attr_value:
                    if query in str(attr_value["value"]).lower():
                        return True
                elif query in str(attr_value).lower():
                    return True
        
        return False