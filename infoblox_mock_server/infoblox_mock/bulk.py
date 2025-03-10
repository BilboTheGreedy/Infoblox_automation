"""
Bulk operations functionality for Infoblox Mock Server
"""

import logging
from infoblox_mock.validators import validate_and_prepare_data
from infoblox_mock.db import add_object, update_object, delete_object

logger = logging.getLogger(__name__)

def process_bulk_operation(objects, operation="create"):
    """Process a bulk operation (create, update, delete)"""
    results = []
    
    for i, obj_data in enumerate(objects):
        # Object must have a type
        if "_object" not in obj_data:
            results.append({
                "index": i,
                "status": "ERROR",
                "error": "Missing _object field"
            })
            continue
        
        obj_type = obj_data["_object"]
        data = {k: v for k, v in obj_data.items() if not k.startswith('_')}
        
        try:
            if operation == "create":
                # Validate and prepare data
                validated_data, error = validate_and_prepare_data(obj_type, data)
                if error:
                    results.append({
                        "index": i,
                        "status": "ERROR",
                        "error": error
                    })
                    continue
                
                # Create the object
                ref = add_object(obj_type, validated_data)
                if ref:
                    results.append({
                        "index": i,
                        "status": "SUCCESS",
                        "ref": ref
                    })
                else:
                    results.append({
                        "index": i,
                        "status": "ERROR",
                        "error": "Failed to create object"
                    })
            
            elif operation == "update":
                # Object must have a reference
                if "_ref" not in obj_data:
                    results.append({
                        "index": i,
                        "status": "ERROR",
                        "error": "Missing _ref field for update operation"
                    })
                    continue
                
                # Update the object
                ref = update_object(obj_data["_ref"], data)
                if ref:
                    results.append({
                        "index": i,
                        "status": "SUCCESS",
                        "ref": ref
                    })
                else:
                    results.append({
                        "index": i,
                        "status": "ERROR",
                        "error": "Failed to update object, it may not exist"
                    })
            
            elif operation == "delete":
                # Object must have a reference
                if "_ref" not in obj_data:
                    results.append({
                        "index": i,
                        "status": "ERROR",
                        "error": "Missing _ref field for delete operation"
                    })
                    continue
                
                # Delete the object
                ref = delete_object(obj_data["_ref"])
                if ref:
                    results.append({
                        "index": i,
                        "status": "SUCCESS",
                        "ref": ref
                    })
                else:
                    results.append({
                        "index": i,
                        "status": "ERROR",
                        "error": "Failed to delete object, it may not exist"
                    })
            
            else:
                results.append({
                    "index": i,
                    "status": "ERROR",
                    "error": f"Unsupported operation: {operation}"
                })
        
        except Exception as e:
            logger.error(f"Error in bulk operation: {str(e)}")
            results.append({
                "index": i,
                "status": "ERROR",
                "error": str(e)
            })
    
    return results