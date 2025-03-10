"""
Import/Export functionality for Infoblox Mock Server
Implements bulk operations, CSV/file import/export, and data migration
"""

import logging
import json
import csv
import io
import re
import ipaddress
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Import/Export tasks
import_tasks = {}
export_tasks = {}

class ImportManager:
    """Manager for data import operations"""
    
    @staticmethod
    def create_import_task(data):
        """Create a new import task"""
        if not data.get("import_type"):
            return None, "Import type is required"
        
        # Generate a unique ID
        task_id = str(uuid.uuid4())
        
        # Create the import task
        task_data = {
            "_ref": f"importtask/{task_id}",
            "import_type": data["import_type"],
            "target_type": data.get("target_type", ""),
            "status": "PENDING",
            "csv_data": data.get("csv_data", ""),
            "csv_filename": data.get("csv_filename", ""),
            "json_data": data.get("json_data", ""),
            "json_filename": data.get("json_filename", ""),
            "options": data.get("options", {}),
            "result": {
                "total_records": 0,
                "imported_records": 0,
                "failed_records": 0,
                "warnings": [],
                "errors": []
            },
            "start_time": None,
            "end_time": None,
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to import tasks
        import_tasks[task_id] = task_data
        
        # Process the import asynchronously
        import threading
        def run_import():
            ImportManager.process_import(task_id)
        
        threading.Thread(target=run_import).start()
        
        return task_data["_ref"], None
    
    @staticmethod
    def get_import_task(task_id):
        """Get an import task by ID"""
        if task_id not in import_tasks:
            return None, f"Import task not found: {task_id}"
        
        return import_tasks[task_id], None
    
    @staticmethod
    def get_all_import_tasks():
        """Get all import tasks"""
        return list(import_tasks.values())
    
    @staticmethod
    def process_import(task_id):
        """Process an import task"""
        if task_id not in import_tasks:
            return None, f"Import task not found: {task_id}"
        
        task = import_tasks[task_id]
        
        # Update status
        task["status"] = "PROCESSING"
        task["start_time"] = datetime.now().isoformat()
        task["_modify_time"] = datetime.now().isoformat()
        
        try:
            # Process based on import type
            import_type = task["import_type"]
            
            if import_type == "CSV":
                result = ImportManager.process_csv_import(task)
            elif import_type == "JSON":
                result = ImportManager.process_json_import(task)
            else:
                task["status"] = "FAILED"
                task["result"]["errors"].append(f"Unsupported import type: {import_type}")
                task["end_time"] = datetime.now().isoformat()
                task["_modify_time"] = datetime.now().isoformat()
                return None, f"Unsupported import type: {import_type}"
            
            # Update task with results
            task["result"] = result
            task["status"] = "COMPLETED" if not result["errors"] else "COMPLETED_WITH_ERRORS"
            task["end_time"] = datetime.now().isoformat()
            task["_modify_time"] = datetime.now().isoformat()
            
            return task["_ref"], None
            
        except Exception as e:
            logger.error(f"Error processing import: {str(e)}")
            task["status"] = "FAILED"
            task["result"]["errors"].append(str(e))
            task["end_time"] = datetime.now().isoformat()
            task["_modify_time"] = datetime.now().isoformat()
            return None, f"Import failed: {str(e)}"
    
    @staticmethod
    def process_csv_import(task):
        """Process a CSV import"""
        csv_data = task["csv_data"]
        target_type = task["target_type"]
        
        # Initialize result
        result = {
            "total_records": 0,
            "imported_records": 0,
            "failed_records": 0,
            "warnings": [],
            "errors": [],
            "record_status": []
        }
        
        if not csv_data:
            result["errors"].append("No CSV data provided")
            return result
        
        try:
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            rows = list(csv_reader)
            result["total_records"] = len(rows)
            
            # Process each row
            for i, row in enumerate(rows):
                row_num = i + 2  # Adjust for header row and 0-based index
                
                try:
                    # Clean up row data
                    clean_row = {}
                    for key, value in row.items():
                        if key and value:
                            clean_row[key.strip()] = value.strip()
                    
                    # Skip empty rows
                    if not clean_row:
                        result["warnings"].append(f"Row {row_num}: Empty row, skipped")
                        continue
                    
                    # Process based on target type
                    if target_type == "network":
                        import_result = ImportManager.import_network(clean_row)
                    elif target_type == "network_container":
                        import_result = ImportManager.import_network_container(clean_row)
                    elif target_type == "record:host":
                        import_result = ImportManager.import_host_record(clean_row)
                    elif target_type == "record:a":
                        import_result = ImportManager.import_a_record(clean_row)
                    elif target_type.startswith("record:"):
                        import_result = ImportManager.import_dns_record(target_type, clean_row)
                    elif target_type == "fixedaddress":
                        import_result = ImportManager.import_fixed_address(clean_row)
                    else:
                        import_result = {"success": False, "error": f"Unsupported target type: {target_type}"}
                    
                    # Handle result
                    status = {
                        "row": row_num,
                        "success": import_result["success"],
                        "message": import_result.get("error", "Success")
                    }
                    
                    if import_result["success"]:
                        result["imported_records"] += 1
                        status["ref"] = import_result.get("ref", "")
                    else:
                        result["failed_records"] += 1
                        result["errors"].append(f"Row {row_num}: {import_result.get('error', 'Unknown error')}")
                    
                    result["record_status"].append(status)
                    
                except Exception as e:
                    logger.error(f"Error processing row {row_num}: {str(e)}")
                    result["failed_records"] += 1
                    result["errors"].append(f"Row {row_num}: {str(e)}")
                    result["record_status"].append({
                        "row": row_num,
                        "success": False,
                        "message": str(e)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            result["errors"].append(f"CSV parsing error: {str(e)}")
            return result
    
    @staticmethod
    def process_json_import(task):
        """Process a JSON import"""
        json_data = task["json_data"]
        
        # Initialize result
        result = {
            "total_records": 0,
            "imported_records": 0,
            "failed_records": 0,
            "warnings": [],
            "errors": [],
            "record_status": []
        }
        
        if not json_data:
            result["errors"].append("No JSON data provided")
            return result
        
        try:
            # Parse JSON
            data = json.loads(json_data)
            
            # Check if it's an array of objects or a single object
            if isinstance(data, list):
                objects = data
            elif isinstance(data, dict):
                objects = [data]
            else:
                result["errors"].append("Invalid JSON structure: must be an object or array of objects")
                return result
            
            result["total_records"] = len(objects)
            
            # Process each object
            for i, obj in enumerate(objects):
                try:
                    # Object must have an object type
                    if "_object" not in obj:
                        result["failed_records"] += 1
                        result["errors"].append(f"Object {i+1}: Missing _object field")
                        result["record_status"].append({
                            "index": i,
                            "success": False,
                            "message": "Missing _object field"
                        })
                        continue
                    
                    obj_type = obj["_object"]
                    obj_data = {k: v for k, v in obj.items() if not k.startswith('_')}
                    
                    # Import the object
                    from infoblox_mock.db import validate_and_prepare_data, add_object
                    
                    validated_data, error = validate_and_prepare_data(obj_type, obj_data)
                    if error:
                        result["failed_records"] += 1
                        result["errors"].append(f"Object {i+1}: {error}")
                        result["record_status"].append({
                            "index": i,
                            "success": False,
                            "message": error
                        })
                        continue
                    
                    ref = add_object(obj_type, validated_data)
                    
                    result["imported_records"] += 1
                    result["record_status"].append({
                        "index": i,
                        "success": True,
                        "message": "Success",
                        "ref": ref
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing object {i+1}: {str(e)}")
                    result["failed_records"] += 1
                    result["errors"].append(f"Object {i+1}: {str(e)}")
                    result["record_status"].append({
                        "index": i,
                        "success": False,
                        "message": str(e)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            result["errors"].append(f"JSON parsing error: {str(e)}")
            return result
    
    @staticmethod
    def import_network(row):
        """Import a network from CSV row"""
        from infoblox_mock.db import validate_and_prepare_data, add_object
        
        # Required fields
        if "network" not in row:
            return {"success": False, "error": "Missing required field: network"}
        
        # Create network data
        network_data = {
            "network": row["network"],
            "network_view": row.get("network_view", "default"),
            "comment": row.get("comment", "")
        }
        
        # Add extensible attributes if present
        extattrs = {}
        for key, value in row.items():
            if key.startswith("EA."):
                ea_name = key[3:]
                extattrs[ea_name] = {"value": value}
        
        if extattrs:
            network_data["extattrs"] = extattrs
        
        # Validate and create
        validated_data, error = validate_and_prepare_data("network", network_data)
        if error:
            return {"success": False, "error": error}
        
        ref = add_object("network", validated_data)
        return {"success": True, "ref": ref}
    
    @staticmethod
    def import_network_container(row):
        """Import a network container from CSV row"""
        from infoblox_mock.db import validate_and_prepare_data, add_object
        
        # Required fields
        if "network" not in row:
            return {"success": False, "error": "Missing required field: network"}
        
        # Create network container data
        container_data = {
            "network": row["network"],
            "network_view": row.get("network_view", "default"),
            "comment": row.get("comment", "")
        }
        
        # Add extensible attributes if present
        extattrs = {}
        for key, value in row.items():
            if key.startswith("EA."):
                ea_name = key[3:]
                extattrs[ea_name] = {"value": value}
        
        if extattrs:
            container_data["extattrs"] = extattrs
        
        # Validate and create
        validated_data, error = validate_and_prepare_data("network_container", container_data)
        if error:
            return {"success": False, "error": error}
        
        ref = add_object("network_container", validated_data)
        return {"success": True, "ref": ref}
    
    @staticmethod
    def import_host_record(row):
        """Import a host record from CSV row"""
        from infoblox_mock.db import validate_and_prepare_data, add_object
        
        # Required fields
        if "name" not in row:
            return {"success": False, "error": "Missing required field: name"}
        
        if "ipv4addr" not in row:
            return {"success": False, "error": "Missing required field: ipv4addr"}
        
        # Create host record data
        host_data = {
            "name": row["name"],
            "view": row.get("view", "default"),
            "ipv4addrs": [{"ipv4addr": row["ipv4addr"]}],
            "comment": row.get("comment", "")
        }
        
        # Add IPv6 if present
        if "ipv6addr" in row:
            host_data["ipv6addrs"] = [{"ipv6addr": row["ipv6addr"]}]
        
        # Add extensible attributes if present
        extattrs = {}
        for key, value in row.items():
            if key.startswith("EA."):
                ea_name = key[3:]
                extattrs[ea_name] = {"value": value}
        
        if extattrs:
            host_data["extattrs"] = extattrs
        
        # Validate and create
        validated_data, error = validate_and_prepare_data("record:host", host_data)
        if error:
            return {"success": False, "error": error}
        
        ref = add_object("record:host", validated_data)
        return {"success": True, "ref": ref}
    
    @staticmethod
    def import_a_record(row):
        """Import an A record from CSV row"""
        from infoblox_mock.db import validate_and_prepare_data, add_object
        
        # Required fields
        if "name" not in row:
            return {"success": False, "error": "Missing required field: name"}
        
        if "ipv4addr" not in row:
            return {"success": False, "error": "Missing required field: ipv4addr"}
        
        # Create A record data
        a_data = {
            "name": row["name"],
            "view": row.get("view", "default"),
            "ipv4addr": row["ipv4addr"],
            "comment": row.get("comment", "")
        }
        
        # Add TTL if present
        if "ttl" in row:
            try:
                a_data["ttl"] = int(row["ttl"])
                a_data["use_ttl"] = True
            except ValueError:
                return {"success": False, "error": f"Invalid TTL value: {row['ttl']}"}
        
        # Add extensible attributes if present
        extattrs = {}
        for key, value in row.items():
            if key.startswith("EA."):
                ea_name = key[3:]
                extattrs[ea_name] = {"value": value}
        
        if extattrs:
            a_data["extattrs"] = extattrs
        
        # Validate and create
        validated_data, error = validate_and_prepare_data("record:a", a_data)
        if error:
            return {"success": False, "error": error}
        
        ref = add_object("record:a", validated_data)
        return {"success": True, "ref": ref}
    
    @staticmethod
    def import_dns_record(record_type, row):
        """Import a generic DNS record from CSV row"""
        from infoblox_mock.db import validate_and_prepare_data, add_object
        
        # Create record data based on record type
        record_data = {}
        
        # Common fields
        if "name" in row:
            record_data["name"] = row["name"]
        
        if "view" in row:
            record_data["view"] = row["view"]
        else:
            record_data["view"] = "default"
        
        if "comment" in row:
            record_data["comment"] = row["comment"]
        
        # Add TTL if present
        if "ttl" in row:
            try:
                record_data["ttl"] = int(row["ttl"])
                record_data["use_ttl"] = True
            except ValueError:
                return {"success": False, "error": f"Invalid TTL value: {row['ttl']}"}
        
        # Record-specific fields
        if record_type == "record:cname":
            if "canonical" not in row:
                return {"success": False, "error": "Missing required field: canonical"}
            record_data["canonical"] = row["canonical"]
        
        elif record_type == "record:aaaa":
            if "ipv6addr" not in row:
                return {"success": False, "error": "Missing required field: ipv6addr"}
            record_data["ipv6addr"] = row["ipv6addr"]
        
        elif record_type == "record:ptr":
            if "ptrdname" not in row:
                return {"success": False, "error": "Missing required field: ptrdname"}
            record_data["ptrdname"] = row["ptrdname"]
            
            if "ipv4addr" in row:
                record_data["ipv4addr"] = row["ipv4addr"]
            elif "ipv6addr" in row:
                record_data["ipv6addr"] = row["ipv6addr"]
            else:
                return {"success": False, "error": "Missing required field: ipv4addr or ipv6addr"}
        
        elif record_type == "record:mx":
            if "mail_exchanger" not in row:
                return {"success": False, "error": "Missing required field: mail_exchanger"}
            record_data["mail_exchanger"] = row["mail_exchanger"]
            
            if "preference" not in row:
                return {"success": False, "error": "Missing required field: preference"}
            try:
                record_data["preference"] = int(row["preference"])
            except ValueError:
                return {"success": False, "error": f"Invalid preference value: {row['preference']}"}
        
        elif record_type == "record:txt":
            if "text" not in row:
                return {"success": False, "error": "Missing required field: text"}
            record_data["text"] = row["text"]
        
        elif record_type == "record:srv":
            required_fields = ["target", "priority", "weight", "port"]
            for field in required_fields:
                if field not in row:
                    return {"success": False, "error": f"Missing required field: {field}"}
            
            record_data["target"] = row["target"]
            
            try:
                record_data["priority"] = int(row["priority"])
                record_data["weight"] = int(row["weight"])
                record_data["port"] = int(row["port"])
            except ValueError:
                return {"success": False, "error": "Invalid numeric value for priority, weight, or port"}
        
        # Add extensible attributes if present
        extattrs = {}
        for key, value in row.items():
            if key.startswith("EA."):
                ea_name = key[3:]
                extattrs[ea_name] = {"value": value}
        
        if extattrs:
            record_data["extattrs"] = extattrs
        
        # Validate and create
        validated_data, error = validate_and_prepare_data(record_type, record_data)
        if error:
            return {"success": False, "error": error}
        
        ref = add_object(record_type, validated_data)
        return {"success": True, "ref": ref}
    
    @staticmethod
    def import_fixed_address(row):
        """Import a fixed address from CSV row"""
        from infoblox_mock.db import validate_and_prepare_data, add_object
        
        # Required fields
        if "ipv4addr" not in row:
            return {"success": False, "error": "Missing required field: ipv4addr"}
        
        if "mac" not in row:
            return {"success": False, "error": "Missing required field: mac"}
        
        # Create fixed address data
        fixed_data = {
            "ipv4addr": row["ipv4addr"],
            "mac": row["mac"],
            "comment": row.get("comment", "")
        }
        
        # Add hostname if present
        if "name" in row:
            fixed_data["name"] = row["name"]
        
        # Add network_view if present
        if "network_view" in row:
            fixed_data["network_view"] = row["network_view"]
        
        # Add extensible attributes if present
        extattrs = {}
        for key, value in row.items():
            if key.startswith("EA."):
                ea_name = key[3:]
                extattrs[ea_name] = {"value": value}
        
        if extattrs:
            fixed_data["extattrs"] = extattrs
        
        # Validate and create
        validated_data, error = validate_and_prepare_data("fixedaddress", fixed_data)
        if error:
            return {"success": False, "error": error}
        
        ref = add_object("fixedaddress", validated_data)
        return {"success": True, "ref": ref}

# Helper function for command-line interfaces
def export_data_to_file(object_type, format, query_params=None, filename=None):
    """
    Export data to a file for command-line usage
    
    Args:
        object_type (str): Type of object to export
        format (str): Export format (CSV, JSON)
        query_params (dict, optional): Query parameters to filter objects
        filename (str, optional): Output filename
        
    Returns:
        tuple: (success, message)
    """
    if not filename:
        filename = f"{object_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{format.lower()}"
    
    # Create an export task
    task_data = {
        "export_type": "DATA",
        "object_type": object_type,
        "format": format,
        "query_params": query_params or {},
        "filename": filename
    }
    
    ref, error = ExportManager.create_export_task(task_data)
    if error:
        return False, error
    
    # Get task ID from ref
    task_id = ref.split('/')[1]
    
    # Wait for task to complete
    import time
    max_wait = 60  # seconds
    wait_time = 0
    sleep_interval = 0.5
    
    while wait_time < max_wait:
        task, error = ExportManager.get_export_task(task_id)
        if error:
            return False, error
        
        if task["status"] in ["COMPLETED", "FAILED"]:
            break
        
        time.sleep(sleep_interval)
        wait_time += sleep_interval
    
    if task["status"] == "FAILED":
        return False, f"Export failed: {', '.join(task['result']['errors'])}"
    
    if task["status"] != "COMPLETED":
        return False, "Export timed out"
    
    # Write data to file
    try:
        with open(filename, 'w') as f:
            f.write(task["result"]["data"])
        return True, f"Data exported to {filename}"
    except Exception as e:
        return False, f"Error writing file: {str(e)}"


class ExportManager:
    """Manager for data export operations"""
    
    @staticmethod
    def create_export_task(data):
        """Create a new export task"""
        if not data.get("export_type"):
            return None, "Export type is required"
        
        if not data.get("object_type"):
            return None, "Object type is required"
        
        # Generate a unique ID
        task_id = str(uuid.uuid4())
        
        # Create the export task
        task_data = {
            "_ref": f"exporttask/{task_id}",
            "export_type": data["export_type"],
            "object_type": data["object_type"],
            "format": data.get("format", "CSV"),  # CSV, JSON
            "query_params": data.get("query_params", {}),
            "filename": data.get("filename", f"{data['object_type']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            "status": "PENDING",
            "result": {
                "total_records": 0,
                "exported_records": 0,
                "warnings": [],
                "errors": [],
                "data": None,
                "url": None
            },
            "start_time": None,
            "end_time": None,
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to export tasks
        export_tasks[task_id] = task_data
        
        # Process the export asynchronously
        import threading
        def run_export():
            ExportManager.process_export(task_id)
        
        threading.Thread(target=run_export).start()
        
        return task_data["_ref"], None
    
    @staticmethod
    def get_export_task(task_id):
        """Get an export task by ID"""
        if task_id not in export_tasks:
            return None, f"Export task not found: {task_id}"
        
        return export_tasks[task_id], None
    
    @staticmethod
    def get_all_export_tasks():
        """Get all export tasks"""
        return list(export_tasks.values())
    
    @staticmethod
    def process_export(task_id):
        """Process an export task"""
        if task_id not in export_tasks:
            return None, f"Export task not found: {task_id}"
        
        task = export_tasks[task_id]
        
        # Update status
        task["status"] = "PROCESSING"
        task["start_time"] = datetime.now().isoformat()
        task["_modify_time"] = datetime.now().isoformat()
        
        try:
            # Get objects
            from infoblox_mock.db import find_objects_by_query
            
            object_type = task["object_type"]
            query_params = task["query_params"]
            
            objects = find_objects_by_query(object_type, query_params)
            
            # Update result with total count
            task["result"]["total_records"] = len(objects)
            
            # Process based on export format
            export_format = task["format"]
            
            if export_format == "CSV":
                result = ExportManager.export_to_csv(objects, object_type)
            elif export_format == "JSON":
                result = ExportManager.export_to_json(objects, object_type)
            else:
                task["status"] = "FAILED"
                task["result"]["errors"].append(f"Unsupported export format: {export_format}")
                task["end_time"] = datetime.now().isoformat()
                task["_modify_time"] = datetime.now().isoformat()
                return None, f"Unsupported export format: {export_format}"
            
            # Update task with results
            task["result"]["exported_records"] = len(objects)
            task["result"]["data"] = result
            
            # Generate URL (in a real implementation, this would be a download URL)
            task["result"]["url"] = f"/export/{task_id}.{export_format.lower()}"
            
            task["status"] = "COMPLETED"
            task["end_time"] = datetime.now().isoformat()
            task["_modify_time"] = datetime.now().isoformat()
            
            return task["_ref"], None
            
        except Exception as e:
            logger.error(f"Error processing export: {str(e)}")
            task["status"] = "FAILED"
            task["result"]["errors"].append(str(e))
            task["end_time"] = datetime.now().isoformat()
            task["_modify_time"] = datetime.now().isoformat()
            return None, f"Export failed: {str(e)}"
    
    @staticmethod
    def export_to_csv(objects, object_type):
        """Export objects to CSV format"""
        if not objects:
            return ""
        
        # Determine fields to export based on object type
        fields = ExportManager.get_csv_fields(object_type, objects[0])
        
        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        
        # Process each object
        for obj in objects:
            row = {}
            
            # Process regular fields
            for field in fields:
                if field.startswith("EA."):
                    # Handle extensible attributes
                    ea_name = field[3:]
                    if "extattrs" in obj and ea_name in obj["extattrs"]:
                        ea_value = obj["extattrs"][ea_name]
                        if isinstance(ea_value, dict) and "value" in ea_value:
                            row[field] = ea_value["value"]
                        else:
                            row[field] = ea_value
                    else:
                        row[field] = ""
                elif field == "ipv4addrs":
                    # Handle host record IPv4 addresses
                    if "ipv4addrs" in obj and obj["ipv4addrs"]:
                        row[field] = ";".join(addr.get("ipv4addr", "") for addr in obj["ipv4addrs"] if "ipv4addr" in addr)
                    else:
                        row[field] = ""
                elif field == "ipv6addrs":
                    # Handle host record IPv6 addresses
                    if "ipv6addrs" in obj and obj["ipv6addrs"]:
                        row[field] = ";".join(addr.get("ipv6addr", "") for addr in obj["ipv6addrs"] if "ipv6addr" in addr)
                    else:
                        row[field] = ""
                else:
                    # Handle regular fields
                    row[field] = obj.get(field, "")
            
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def export_to_json(objects, object_type):
        """Export objects to JSON format"""
        if not objects:
            return "[]"
        
        # Add _object field to each object
        enhanced_objects = []
        for obj in objects:
            enhanced_obj = obj.copy()
            enhanced_obj["_object"] = object_type
            enhanced_objects.append(enhanced_obj)
        
        return json.dumps(enhanced_objects, indent=2)
    
    @staticmethod
    def get_csv_fields(object_type, sample_obj):
        """Get CSV fields for an object type"""
        # Default fields for all object types
        base_fields = ["comment"]
        ea_fields = []
        
        # Object-specific fields
        specific_fields = []
        if object_type == "network" or object_type == "network_container":
            specific_fields = ["network", "network_view"]
        elif object_type == "record:host":
            specific_fields = ["name", "view", "ipv4addrs", "ipv6addrs"]
        elif object_type == "record:a":
            specific_fields = ["name", "view", "ipv4addr", "ttl", "use_ttl"]
        elif object_type == "record:aaaa":
            specific_fields = ["name", "view", "ipv6addr", "ttl", "use_ttl"]
        elif object_type == "record:cname":
            specific_fields = ["name", "view", "canonical", "ttl", "use_ttl"]
        elif object_type == "record:ptr":
            specific_fields = ["name", "view", "ptrdname", "ttl", "use_ttl"]
        elif object_type == "record:mx":
            specific_fields = ["name", "view", "mail_exchanger", "preference", "ttl", "use_ttl"]
        elif object_type == "record:txt":
            specific_fields = ["name", "view", "text", "ttl", "use_ttl"]
        elif object_type == "record:srv":
            specific_fields = ["name", "view", "target", "priority", "weight", "port", "ttl", "use_ttl"]
        elif object_type == "fixedaddress":
            specific_fields = ["ipv4addr", "mac", "name", "network_view"]
        else:
            # For unknown object types, use all fields from the sample object
            specific_fields = [k for k in sample_obj.keys() if not k.startswith("_") and k != "comment" and k != "extattrs"]
        
        # Add extensible attributes as fields
        if "extattrs" in sample_obj:
            for ea_name in sample_obj["extattrs"].keys():
                ea_fields.append(f"EA.{ea_name}")
                
        # Combine all fields and return
        return base_fields + specific_fields + ea_fields