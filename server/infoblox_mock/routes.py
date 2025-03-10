"""
API routes for Infoblox Mock Server
"""

from flask import request, jsonify, make_response, render_template_string
import logging

from infoblox_mock.config import CONFIG, update_config, is_feature_supported
from infoblox_mock.db import (db, initialize_db, find_object_by_ref, 
                              find_objects_by_query, add_object, 
                              update_object, delete_object, 
                              reset_db, export_db)
from infoblox_mock.middleware import api_route
from infoblox_mock.validators import validate_and_prepare_data
from infoblox_mock.utils import (generate_ref, find_next_available_ip, get_used_ips_in_db,
                                find_next_available_ipv6, get_used_ipv6_in_db, 
                                is_ipv6_in_network)
from infoblox_mock.mock_responses import find_mock_response
from infoblox_mock.bulk import process_bulk_operation
from infoblox_mock.statistics import api_stats
from infoblox_mock.backup import BackupManager
from infoblox_mock.swagger import generate_swagger_spec
import uuid

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all API routes"""
    
    # Add a middleware to handle mock responses
    @app.before_request
    def check_mock_response():
        """Check if a mock response exists for this request"""
        mock_response = find_mock_response()
        if mock_response:
            # Return the mock response
            status_code = mock_response.get('status_code', 200)
            headers = mock_response.get('headers', {})
            data = mock_response.get('data')
            
            # Create the response
            response = jsonify(data) if data else ('', 204)
            
            # Add headers
            if isinstance(response, tuple):
                response = make_response(response)
            
            for header, value in headers.items():
                response.headers[header] = value
                
            return response, status_code

    @app.route('/wapi/stats', methods=['GET', 'POST'])
    def api_statistics():
        """Get or reset API usage statistics"""
        # Require authentication
        auth = request.authorization
        if not auth or auth.username != 'admin':
            response = jsonify({"Error": "Administrator access required"})
            response.status_code = 401
            response.headers['WWW-Authenticate'] = 'Basic realm="Infoblox Mock Server Statistics"'
            return response
        
        # Handle reset request
        if request.method == 'POST':
            action = request.args.get('action', '')
            if action == 'reset':
                api_stats.reset_stats()
                return jsonify({"status": "success", "message": "Statistics reset successfully"})
            else:
                return jsonify({"Error": "Invalid action"}), 400
        
        # Get statistics
        stats = api_stats.get_stats()
        
        # Optional filtering
        if 'filter' in request.args:
            filter_key = request.args.get('filter')
            if filter_key in stats:
                return jsonify({filter_key: stats[filter_key]})
        
        return jsonify(stats)

    # Add webhook routes
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/webhook', methods=['POST', 'DELETE', 'GET'])
    @api_route
    def webhook_management():
        """Manage webhook registrations"""
        from infoblox_mock.webhooks import webhook_manager
        
        # Require authentication
        auth = request.authorization
        if not auth or auth.username != 'admin':
            response = jsonify({"Error": "Administrator access required"})
            response.status_code = 401
            response.headers['WWW-Authenticate'] = 'Basic realm="Infoblox Mock Server Webhooks"'
            return response
        
        # Handle GET (list webhooks)
        if request.method == 'GET':
            event_type = request.args.get('event_type')
            webhooks = webhook_manager.get_webhooks(event_type)
            return jsonify(webhooks)
        
        # Handle POST (register webhook)
        elif request.method == 'POST':
            data = request.json
            
            # Validate request
            if not data or 'event_type' not in data or 'url' not in data:
                return jsonify({"Error": "Missing required fields: event_type, url"}), 400
            
            # Register webhook
            result = webhook_manager.register_webhook(
                data['event_type'],
                data['url'],
                data.get('headers')
            )
            
            if result:
                return jsonify({"status": "success", "message": "Webhook registered successfully"})
            else:
                return jsonify({"Error": "Failed to register webhook"}), 400
        
        # Handle DELETE (unregister webhook)
        elif request.method == 'DELETE':
            data = request.json
            
            # Validate request
            if not data or 'event_type' not in data or 'url' not in data:
                return jsonify({"Error": "Missing required fields: event_type, url"}), 400
            
            # Unregister webhook
            result = webhook_manager.unregister_webhook(
                data['event_type'],
                data['url']
            )
            
            if result:
                return jsonify({"status": "success", "message": "Webhook unregistered successfully"})
            else:
                return jsonify({"Error": "Webhook not found"}), 404

    # Add certificate routes
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/certificate', methods=['POST', 'GET'])
    @api_route
    def certificate():
        """Handle certificate operations"""
        from infoblox_mock.certificates import CertificateManager
        
        # Handle GET (list certificates)
        if request.method == 'GET':
            certificates = CertificateManager.get_all_certificates()
            return jsonify(certificates)
        
        # Handle POST (create/import certificate)
        elif request.method == 'POST':
            data = request.json
            
            # Validate request
            if not data:
                return jsonify({"Error": "Request body is required"}), 400
            
            # Check operation
            operation = data.get('operation', 'generate')
            
            if operation == 'generate':
                # Generate self-signed certificate
                ref, error = CertificateManager.generate_self_signed_cert(
                    common_name=data.get('common_name', 'infoblox.example.com'),
                    days_valid=data.get('days_valid', 365),
                    organization=data.get('organization', 'Infoblox Mock'),
                    organizational_unit=data.get('organizational_unit', 'IT'),
                    locality=data.get('locality', 'San Francisco'),
                    state=data.get('state', 'CA'),
                    country=data.get('country', 'US'),
                    key_size=data.get('key_size', 2048)
                )
            elif operation == 'import':
                # Import certificate
                if 'certificate' not in data:
                    return jsonify({"Error": "Certificate data is required"}), 400
                
                ref, error = CertificateManager.import_certificate(
                    cert_data=data['certificate'],
                    private_key=data.get('private_key'),
                    passphrase=data.get('passphrase')
                )
            elif operation == 'import_ca':
                # Import CA certificate
                if 'certificate' not in data:
                    return jsonify({"Error": "Certificate data is required"}), 400
                
                ref, error = CertificateManager.import_ca_certificate(
                    cert_data=data['certificate']
                )
            else:
                return jsonify({"Error": f"Unsupported operation: {operation}"}), 400
            
            if error:
                return jsonify({"Error": error}), 400
            
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

    # Add new route handling for IPv6 next available IP
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/ipv6network/<path:network>/next_available_ip', methods=['POST'])
    @api_route
    def next_available_ipv6(network):
        """Get next available IPv6 in a network"""
        # Check if IPv6 support is available in this WAPI version
        if not is_feature_supported('ipv6_support'):
            return jsonify({"Error": "Function not available in this WAPI version"}), 400
        
        # Find network
        network_obj = None
        for net in db["ipv6network"]:
            if net["network"] == network:
                network_obj = net
                break
        
        if not network_obj:
            logger.warning(f"IPv6 network not found: {network}")
            return jsonify({"Error": "IPv6 network not found"}), 404
        
        # Find used IPv6 addresses
        used_ips = get_used_ipv6_in_db(db)
        
        # Find next available IPv6
        ip_str = find_next_available_ipv6(network_obj["network"], used_ips)
        
        if ip_str:
            logger.info(f"Found next available IPv6 in {network}: {ip_str}")
            return jsonify({"ips": [ip_str]})
        else:
            logger.warning(f"No available IPv6 addresses in network: {network}")
            return jsonify({"Error": "No available IPv6 addresses in network"}), 400

    # Add route for IPv6 address search
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/ipv6address', methods=['GET'])
    @api_route
    def search_ipv6():
        """Search for IPv6 addresses"""
        query_params = request.args.to_dict()
        
        # Handle search by specific IPv6 address
        if 'ip_address' in query_params:
            ip = query_params['ip_address']
            results = []
            
            # Search in all IPv6-related collections
            for collection_type in ["record:aaaa", "ipv6fixedaddress"]:
                for obj in db.get(collection_type, []):
                    if obj.get("ipv6addr") == ip:
                        results.append({
                            "objects": [obj["_ref"]],
                            "ip_address": ip,
                            "types": [collection_type]
                        })
            
            # Search in host records with IPv6 addresses
            for obj in db.get("record:host", []):
                for addr in obj.get("ipv6addrs", []):
                    if addr.get("ipv6addr") == ip:
                        results.append({
                            "objects": [obj["_ref"]],
                            "ip_address": ip,
                            "types": ["record:host"]
                        })
            
            return jsonify(results)
        
        # Handle search by network
        elif 'network' in query_params:
            network = query_params['network']
            results = []
            
            try:
                net = ipaddress.ip_network(network, strict=False)
                if net.version != 6:
                    return jsonify({"Error": "Not an IPv6 network"}), 400
                
                # Collect all IPv6 addresses in collections
                all_ips = []
                
                # From AAAA records
                for obj in db.get("record:aaaa", []):
                    ip = obj.get("ipv6addr", "")
                    if ip and is_ipv6_in_network(ip, network):
                        all_ips.append({
                            "objects": [obj["_ref"]],
                            "ip_address": ip,
                            "types": ["record:aaaa"]
                        })
                
                # From fixed addresses
                for obj in db.get("ipv6fixedaddress", []):
                    ip = obj.get("ipv6addr", "")
                    if ip and is_ipv6_in_network(ip, network):
                        all_ips.append({
                            "objects": [obj["_ref"]],
                            "ip_address": ip,
                            "types": ["ipv6fixedaddress"]
                        })
                
                # From host records
                for obj in db.get("record:host", []):
                    for addr in obj.get("ipv6addrs", []):
                        ip = addr.get("ipv6addr", "")
                        if ip and is_ipv6_in_network(ip, network):
                            all_ips.append({
                                "objects": [obj["_ref"]],
                                "ip_address": ip,
                                "types": ["record:host"]
                            })
                
                return jsonify(all_ips)
                
            except Exception as e:
                logger.error(f"Error searching IPv6 network: {str(e)}")
                return jsonify({"Error": str(e)}), 400
        
        else:
            return jsonify({"Error": "Missing search criteria"}), 400
    
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

    @app.route(f'/wapi/{CONFIG["wapi_version"]}/certificate/<cert_id>', methods=['GET', 'PUT', 'DELETE'])
    @api_route
    def certificate_by_id(cert_id):
        """Handle operations on a specific certificate"""
        from infoblox_mock.certificates import CertificateManager
        
        # Handle GET (get certificate)
        if request.method == 'GET':
            cert, error = CertificateManager.get_certificate(cert_id)
            if error:
                return jsonify({"Error": error}), 404
            
            return jsonify(cert)
        
        # Handle PUT (update certificate)
        elif request.method == 'PUT':
            data = request.json
            
            # Validate request
            if not data:
                return jsonify({"Error": "Request body is required"}), 400
            
            # Update certificate
            ref, error = CertificateManager.update_certificate(cert_id, data)
            if error:
                return jsonify({"Error": error}), 404
            
            return jsonify(ref)
        
        # Handle DELETE (delete certificate)
        elif request.method == 'DELETE':
            ref, error = CertificateManager.delete_certificate(cert_id)
            if error:
                return jsonify({"Error": error}), 404
            
            return jsonify(ref)

    @app.route(f'/wapi/{CONFIG["wapi_version"]}/smartfolder', methods=['POST', 'GET'])
    @api_route
    def smart_folder():
        """Handle Smart Folder operations"""
        from infoblox_mock.smart_folders import SmartFolderManager
        
        # Handle GET (list folders)
        if request.method == 'GET':
            # Get owner from query params
            owner = request.args.get('owner')
            # Get shared flag
            shared = request.args.get('shared', 'true').lower() != 'false'
            
            # Get all folders
            folders = SmartFolderManager.get_all_folders(owner, shared)
            return jsonify(folders)
        
        # Handle POST (create folder)
        elif request.method == 'POST':
            data = request.json
            
            # Validate request
            if not data:
                return jsonify({"Error": "Request body is required"}), 400
            
            # Create folder
            ref, error = SmartFolderManager.create_folder(data)
            if error:
                return jsonify({"Error": error}), 400
            
            return jsonify(ref)

    @app.route(f'/wapi/{CONFIG["wapi_version"]}/smartfolder/<folder_id>', methods=['GET', 'PUT', 'DELETE'])
    @api_route
    def smart_folder_by_id(folder_id):
        """Handle operations on a specific Smart Folder"""
        from infoblox_mock.smart_folders import SmartFolderManager
        
        # Handle GET (get folder)
        if request.method == 'GET':
            folder, error = SmartFolderManager.get_folder(folder_id)
            if error:
                return jsonify({"Error": error}), 404
            
            return jsonify(folder)
        
        # Handle PUT (update folder)
        elif request.method == 'PUT':
            data = request.json
            
            # Validate request
            if not data:
                return jsonify({"Error": "Request body is required"}), 400
            
            # Update folder
            ref, error = SmartFolderManager.update_folder(folder_id, data)
            if error:
                return jsonify({"Error": error}), 404
            
            return jsonify(ref)
        
        # Handle DELETE (delete folder)
        elif request.method == 'DELETE':
            ref, error = SmartFolderManager.delete_folder(folder_id)
            if error:
                return jsonify({"Error": error}), 404
            
            return jsonify(ref)

    @app.route(f'/wapi/{CONFIG["wapi_version"]}/smartfolder/<folder_id>/content', methods=['GET'])
    @api_route
    def smart_folder_content(folder_id):
        """Get the contents of a Smart Folder"""
        from infoblox_mock.smart_folders import SmartFolderManager
        
        # Get folder contents
        contents, error = SmartFolderManager.get_folder_contents(folder_id)
        if error:
            return jsonify({"Error": error}), 404
        
        return jsonify(contents)
        
    @app.route('/swagger', methods=['GET'])
    def swagger_ui():
        """Swagger UI for API documentation"""
        # Basic Swagger UI HTML template
        swagger_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Infoblox Mock Server API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.18.3/swagger-ui.css">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.18.3/swagger-ui-bundle.js"></script>
            <script>
                window.onload = function() {
                    const ui = SwaggerUIBundle({
                        url: "/swagger.json",
                        dom_id: "#swagger-ui",
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIBundle.SwaggerUIStandalonePreset
                        ],
                        layout: "BaseLayout",
                        deepLinking: true
                    });
                }
            </script>
        </body>
        </html>
        '''
        return render_template_string(swagger_html)

    @app.route('/swagger.json', methods=['GET'])
    def swagger_json():
        """Get Swagger/OpenAPI specification as JSON"""
        return jsonify(generate_swagger_spec())
    
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/grid/backup', methods=['POST', 'GET'])
    @api_route
    def grid_backup():
        """Handle grid backup operations"""
        # Handle GET (list backups)
        if request.method == 'GET':
            # Get backup ID from query params
            backup_id = request.args.get('id')
            if backup_id:
                # Get specific backup
                backup = BackupManager.get_backup(backup_id)
                if not backup:
                    return jsonify({"Error": "Backup not found"}), 404
                return jsonify(backup)
            else:
                # Get all backups
                backups = BackupManager.get_all_backups()
                return jsonify(list(backups.values()))
        
        # Handle POST (create backup)
        elif request.method == 'POST':
            data = request.json
            
            # Validate request
            if not data or 'name' not in data:
                return jsonify({"Error": "Missing required field: name"}), 400
            
            # Create backup
            backup_id = BackupManager.create_backup(
                name=data['name'],
                backup_type=data.get('type', 'full'),
                include_members=data.get('include_members'),
                comment=data.get('comment')
            )
            
            return jsonify({"id": backup_id})

    @app.route(f'/wapi/{CONFIG["wapi_version"]}/grid/restore', methods=['POST', 'GET'])
    @api_route
    def grid_restore():
        """Handle grid restore operations"""
        # Handle GET (list restores)
        if request.method == 'GET':
            # Get restore ID from query params
            restore_id = request.args.get('id')
            if restore_id:
                # Get specific restore
                restore = BackupManager.get_restore(restore_id)
                if not restore:
                    return jsonify({"Error": "Restore not found"}), 404
                return jsonify(restore)
            else:
                # Get all restores
                restores = BackupManager.get_all_restores()
                return jsonify(list(restores.values()))
        
        # Handle POST (restore backup)
        elif request.method == 'POST':
            data = request.json
            
            # Validate request
            if not data or 'backup_id' not in data:
                return jsonify({"Error": "Missing required field: backup_id"}), 400
            
            # Restore backup
            restore_id, error = BackupManager.restore_backup(
                backup_id=data['backup_id'],
                include_members=data.get('include_members')
            )
            
            if error:
                return jsonify({"Error": error}), 400
            
            return jsonify({"id": restore_id})
            
    @app.route(f'/wapi/{CONFIG["wapi_version"]}/bulkhost', methods=['POST'])
    @api_route
    def bulk_host():
        """Handle bulk host operations"""
        if not is_feature_supported('bulk_operations'):
            return jsonify({"Error": "Function not available in this WAPI version"}), 400
        
        try:
            data = request.json
            
            # Validate request
            if not isinstance(data, dict) or 'hosts' not in data:
                return jsonify({"Error": "Invalid request format, 'hosts' field required"}), 400
            
            hosts = data['hosts']
            if not isinstance(hosts, list):
                return jsonify({"Error": "'hosts' must be a list"}), 400
            
            # Add _object type to each host
            for host in hosts:
                host['_object'] = 'record:host'
            
            # Process the bulk operation
            results = process_bulk_operation(hosts, "create")
            
            return jsonify(results)
        
        except Exception as e:
            logger.error(f"Error in bulk host operation: {str(e)}")
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

    @app.route(f'/wapi/{CONFIG["wapi_version"]}/bulk', methods=['POST'])
    @api_route
    def bulk_operation():
        """Handle generic bulk operations"""
        if not is_feature_supported('bulk_operations'):
            return jsonify({"Error": "Function not available in this WAPI version"}), 400
        
        try:
            data = request.json
            
            # Validate request
            if not isinstance(data, dict) or 'objects' not in data:
                return jsonify({"Error": "Invalid request format, 'objects' field required"}), 400
            
            objects = data['objects']
            if not isinstance(objects, list):
                return jsonify({"Error": "'objects' must be a list"}), 400
            
            # Get operation type
            operation = data.get('operation', 'create').lower()
            if operation not in ['create', 'update', 'delete']:
                return jsonify({"Error": f"Unsupported operation: {operation}"}), 400
            
            # Process the bulk operation
            results = process_bulk_operation(objects, operation)
            
            return jsonify(results)
        
        except Exception as e:
            logger.error(f"Error in bulk operation: {str(e)}")
            return jsonify({"Error": str(e)}), 400