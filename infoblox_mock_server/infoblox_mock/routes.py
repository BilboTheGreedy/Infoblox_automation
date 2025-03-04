"""
API routes for Infoblox Mock Server
"""

from flask import request, jsonify
import logging

from infoblox_mock.config import CONFIG, update_config
from infoblox_mock.db import (db, initialize_db, find_object_by_ref, 
                              find_objects_by_query, add_object, 
                              update_object, delete_object, 
                              reset_db, export_db)
from infoblox_mock.middleware import api_route
from infoblox_mock.validators import validate_and_prepare_data
from infoblox_mock.utils import generate_ref, find_next_available_ip, get_used_ips_in_db

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all API routes"""
    
    # Handler for object collections (GET, POST)
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/<obj_type>', methods=['GET', 'POST'])
    @api_route
    def handle_objects(obj_type):
        """Handle object collections: search or create"""
        # Handle GET (search)
        if request.method == 'GET':
            query_params = request.args.to_dict()
            results = find_objects_by_query(obj_type, query_params)
            
            logger.info(f"GET {obj_type}: Found {len(results)} objects matching query")
            return jsonify(results)
        
        # Handle POST (create)
        elif request.method == 'POST':
            try:
                data = request.json
                
                # Validate and prepare data
                validated_data, error = validate_and_prepare_data(obj_type, data)
                if error:
                    logger.warning(f"Validation error for {obj_type}: {error}")
                    return jsonify({"Error": error}), 400
                
                # Create the object reference
                validated_data["_ref"] = generate_ref(obj_type, validated_data)
                
                # Check for duplicate (exact match on key fields)
                if obj_type == "network" or obj_type == "network_container":
                    # Check for duplicate network
                    for existing in db[obj_type]:
                        if existing.get("network") == validated_data.get("network") and \
                           existing.get("network_view") == validated_data.get("network_view"):
                            logger.warning(f"Duplicate network: {validated_data.get('network')}")
                            return jsonify({"Error": f"Network already exists: {validated_data.get('network')}"}), 400
                
                elif obj_type.startswith("record:"):
                    # Check for duplicate DNS record
                    for existing in db[obj_type]:
                        if existing.get("name") == validated_data.get("name") and \
                           existing.get("view") == validated_data.get("view"):
                            logger.warning(f"Duplicate DNS record: {validated_data.get('name')}")
                            return jsonify({"Error": f"DNS record already exists: {validated_data.get('name')}"}), 400
                
                # Save to database
                ref = add_object(obj_type, validated_data)
                logger.info(f"Created new {obj_type}: {ref}")
                
                # Return reference as per Infoblox API
                return jsonify(ref)
            
            except Exception as e:
                logger.error(f"Error creating {obj_type}: {str(e)}")
                return jsonify({"Error": str(e)}), 400
    
    # Handler for individual objects (GET, PUT, DELETE)
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/<path:ref>', methods=['GET', 'PUT', 'DELETE'])
    @api_route
    def handle_object(ref):
        """Handle individual object: get, update, or delete"""
        # Extract object type from reference
        obj_type = ref.split('/')[0]
        
        # Handle GET (read)
        if request.method == 'GET':
            obj = find_object_by_ref(ref)
            if not obj:
                logger.warning(f"Object not found: {ref}")
                return jsonify({"Error": "Object not found"}), 404
            
            logger.info(f"GET object: {ref}")
            return jsonify(obj)
        
        # Handle PUT (update)
        elif request.method == 'PUT':
            obj = find_object_by_ref(ref)
            if not obj:
                logger.warning(f"Object not found for update: {ref}")
                return jsonify({"Error": "Object not found"}), 404
            
            data = request.json
            
            # Update the object
            ref = update_object(ref, data)
            logger.info(f"Updated object: {ref}")
            return jsonify(ref)
        
        # Handle DELETE
        elif request.method == 'DELETE':
            obj = find_object_by_ref(ref)
            if not obj:
                logger.warning(f"Object not found for deletion: {ref}")
                return jsonify({"Error": "Object not found"}), 404
            
            # Delete the object
            ref = delete_object(ref)
            logger.info(f"Deleted object: {ref}")
            return jsonify(ref)
    
    # Next available IP
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/network/<path:network>/next_available_ip', methods=['POST'])
    @api_route
    def next_available_ip(network):
        """Get next available IP in a network"""
        # Find network
        network_obj = None
        for net in db["network"]:
            if net["network"] == network:
                network_obj = net
                break
        
        if not network_obj:
            logger.warning(f"Network not found: {network}")
            return jsonify({"Error": "Network not found"}), 404
        
        # Find used IPs
        used_ips = get_used_ips_in_db(db)
        
        # Find next available IP
        ip_str = find_next_available_ip(network_obj["network"], used_ips)
        
        if ip_str:
            logger.info(f"Found next available IP in {network}: {ip_str}")
            return jsonify({"ips": [ip_str]})
        else:
            logger.warning(f"No available IPs in network: {network}")
            return jsonify({"Error": "No available IPs in network"}), 400
    
    # Grid information
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/grid', methods=['GET'])
    @api_route
    def get_grid():
        """Get grid information"""
        logger.info("GET grid info")
        return jsonify(db["grid"])
    
    # Grid session (login)
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/grid/session', methods=['POST', 'DELETE'])
    def grid_session():
        """Handle grid session (login/logout)"""
        client_ip = request.remote_addr
        
        # Login
        if request.method == 'POST':
            auth = request.authorization
            if not auth:
                logger.warning(f"Login attempt without credentials from {client_ip}")
                return jsonify({"Error": "Authentication required"}), 401
            
            # In a real system, we would validate credentials here
            username = auth.username
            
            # Add session
            if username not in db["activeuser"]:
                db["activeuser"][username] = []
            
            if client_ip not in db["activeuser"][username]:
                db["activeuser"][username].append(client_ip)
            
            logger.info(f"User {username} logged in from {client_ip}")
            return jsonify({"username": username})
        
        # Logout
        elif request.method == 'DELETE':
            # Remove session
            for username, sessions in db["activeuser"].items():
                if client_ip in sessions:
                    sessions.remove(client_ip)
                    logger.info(f"User {username} logged out from {client_ip}")
            
            # No content response for successful logout
            return "", 204
    
    # Configuration endpoints
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/config', methods=['GET', 'PUT'])
    @api_route
    def handle_config():
        """Get or update server configuration"""
        if request.method == 'GET':
            logger.info("GET server configuration")
            return jsonify(CONFIG)
        
        elif request.method == 'PUT':
            data = request.json
            updated_config = update_config(data)
            logger.info(f"Updated server configuration: {data}")
            return jsonify(updated_config)
    
    # Database management endpoints
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/db/reset', methods=['POST'])
    @api_route
    def handle_db_reset():
        """Reset the database to initial state"""
        if reset_db():
            logger.info("Database reset to initial state")
            return jsonify({"status": "success", "message": "Database reset to initial state"})
        else:
            logger.error("Failed to reset database")
            return jsonify({"Error": "Failed to reset database"}), 500
    
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/db/export', methods=['GET'])
    @api_route
    def handle_db_export():
        """Export the current database state"""
        db_export = export_db()
        logger.info("Database exported")
        return jsonify(db_export)

    # Return 404 for undefined routes
    @app.errorhandler(404)
    def handle_404(error):
        logger.warning(f"404 error: {request.path}")
        return jsonify({"Error": "Not Found", "text": f"Resource not found: {request.path}"}), 404
    
    # Return 500 for server errors
    @app.errorhandler(500)
    def handle_500(error):
        logger.error(f"500 error: {str(error)}")
        return jsonify({"Error": "Internal Server Error", "text": str(error)}), 500