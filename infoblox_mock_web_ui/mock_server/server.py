"""
Core functionality for the Infoblox Mock Server.
"""

import threading
import logging
from flask import request, jsonify, abort
from mock_server.initialize_db import initialize_db
from mock_server.helpers import (
    simulate_delay, 
    simulate_failures, 
    rate_limit, 
    require_auth, 
    db_transaction, 
    log_request,
    find_objects_by_query,
    find_object_by_ref,
    validate_and_prepare_data,
    generate_ref
)

logger = logging.getLogger(__name__)

# Global variables
db = {}
db_lock = threading.RLock()

# Configuration options
CONFIG = {
    'simulate_delay': False,  # Add random delay to responses
    'min_delay_ms': 50,       # Minimum delay in milliseconds
    'max_delay_ms': 300,      # Maximum delay in milliseconds
    'simulate_failures': False,  # Randomly simulate server failures
    'failure_rate': 0.05,     # 5% chance of failure if simulation enabled
    'detailed_logging': True,  # Enable detailed request/response logging
    'persistent_storage': False,  # Enable file-based persistent storage
    'storage_file': 'infoblox_mock_db.json',  # File to use for persistent storage
    'auth_required': True,    # Require authentication
    'rate_limit': True,       # Enable rate limiting
    'rate_limit_requests': 100,  # Number of requests allowed per minute
    'simulate_db_lock': False,  # Simulate database locks
    'lock_probability': 0.01  # 1% chance of a lock per operation
}

# Rate limiting data
rate_limit_data = {
    'counters': {},  # Keeps track of requests by IP
    'windows': {}    # Keeps track of time windows by IP
}

def setup_mock_server(app):
    """
    Setup the mock server routes and initialize the database
    """
    global db, CONFIG
    
    # Initialize the database with default data
    initialize_db(db)
    
    # Routes for object collections
    @app.route('/wapi/v2.11/<obj_type>', methods=['GET', 'POST'])
    @log_request
    @rate_limit
    @require_auth
    @simulate_failures
    @simulate_delay
    @db_transaction
    def handle_objects(obj_type):
        """Handle object collections: search or create"""
        # Handle GET (search)
        if request.method == 'GET':
            query_params = request.args.to_dict()
            results = find_objects_by_query(obj_type, query_params, db)
            
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
                
                # Check for duplicate
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
                if obj_type not in db:
                    db[obj_type] = []
                
                db[obj_type].append(validated_data)
                
                logger.info(f"Created new {obj_type}: {validated_data['_ref']}")
                
                # Return reference as per Infoblox API
                return jsonify(validated_data["_ref"])
            
            except Exception as e:
                logger.error(f"Error creating {obj_type}: {str(e)}")
                return jsonify({"Error": str(e)}), 400
    
    # Routes for individual objects
    @app.route('/wapi/v2.11/<path:ref>', methods=['GET', 'PUT', 'DELETE'])
    @log_request
    @rate_limit
    @require_auth
    @simulate_failures
    @simulate_delay
    @db_transaction
    def handle_object(ref):
        """Handle individual object: get, update, or delete"""
        # Extract object type from reference
        obj_type = ref.split('/')[0]
        
        # Handle GET (read)
        if request.method == 'GET':
            obj = find_object_by_ref(ref, db)
            if not obj:
                logger.warning(f"Object not found: {ref}")
                return jsonify({"Error": "Object not found"}), 404
            
            logger.info(f"GET object: {ref}")
            return jsonify(obj)
        
        # Handle PUT (update)
        elif request.method == 'PUT':
            obj = find_object_by_ref(ref, db)
            if not obj:
                logger.warning(f"Object not found for update: {ref}")
                return jsonify({"Error": "Object not found"}), 404
            
            data = request.json
            
            # Update object with new data
            for key, value in data.items():
                # Skip reserved fields
                if key.startswith('_'):
                    continue
                obj[key] = value
            
            logger.info(f"Updated object: {ref}")
            return jsonify(ref)
        
        # Handle DELETE
        elif request.method == 'DELETE':
            obj = find_object_by_ref(ref, db)
            if not obj:
                logger.warning(f"Object not found for deletion: {ref}")
                return jsonify({"Error": "Object not found"}), 404
            
            # Remove object from database
            db[obj_type] = [o for o in db[obj_type] if o["_ref"] != ref]
            
            logger.info(f"Deleted object: {ref}")
            return jsonify(ref)
    
    # Return the database and config objects so they can be used by the UI
    return db, CONFIG