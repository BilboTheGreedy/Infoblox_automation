"""
Route definitions for the web UI.
This file handles UI routes, renders templates, and processes form submissions.
"""

import os
import json
import logging
from flask import render_template, redirect, url_for, request, flash, session, send_file
from flask import Response, make_response
from datetime import datetime
import ipaddress
from io import BytesIO

logger = logging.getLogger(__name__)

def setup_ui_routes(app):
    """
    Setup UI routes for the web interface
    """
    # Create template directories if needed
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Generate template files if they don't exist
    create_template_files()
    create_static_files()
    
    # Login/Logout Routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle login page and form submission"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Simple authentication check (in a real app this would be more secure)
            if username == 'admin' and password == 'infoblox':
                session['logged_in'] = True
                session['username'] = username
                
                # Create session in the mock server
                response = make_grid_session(app)
                
                if response.status_code == 200:
                    flash('Login successful!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Login failed: Could not create grid session', 'danger')
            else:
                flash('Invalid credentials!', 'danger')
        
        return render_template('login.html', username='admin')
    
    @app.route('/logout')
    def logout():
        """Handle logout"""
        # Delete grid session
        if session.get('logged_in'):
            try:
                response = app.test_client().delete('/wapi/v2.11/grid/session')
            except Exception as e:
                logger.error(f"Error during logout: {str(e)}")
        
        # Clear session
        session.clear()
        flash('You have been logged out!', 'info')
        return redirect(url_for('login'))
    
    # Main Routes
    @app.route('/')
    def index():
        """Main dashboard page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get database from app context
        from mock_server.server import db
        
        # Count objects for dashboard
        network_count = len(db.get("network", []))
        host_count = len(db.get("record:host", []))
        record_count = len(db.get("record:a", []))
        fixed_count = len(db.get("fixedaddress", []))
        
        # Get grid info
        grid = db.get("grid", [{}])[0] if "grid" in db else {}
        
        return render_template(
            'index.html',
            active_tab='dashboard',
            network_count=network_count,
            host_count=host_count,
            record_count=record_count,
            fixed_count=fixed_count,
            grid=grid
        )
    
    # Networks Routes
    @app.route('/networks')
    def networks():
        """Networks management page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get database from app context
        from mock_server.server import db
        
        # Get all networks
        networks = db.get("network", [])
        
        return render_template(
            'networks.html',
            active_tab='networks',
            networks=networks
        )
    
    @app.route('/networks/create', methods=['POST'])
    def networks_create():
        """Create a new network"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get form data
        network = request.form.get('network')
        comment = request.form.get('comment')
        
        # Create network via API
        try:
            # Validate network
            ipaddress.ip_network(network, strict=False)
            
            data = {
                "network": network,
                "comment": comment
            }
            
            response = app.test_client().post(
                '/api/networks',
                json=data,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                flash(f'Network {network} created successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error creating network: {response_data.get("error", "Unknown error")}', 'danger')
        
        except ValueError:
            flash('Invalid network format!', 'danger')
        except Exception as e:
            flash(f'Error creating network: {str(e)}', 'danger')
        
        return redirect(url_for('networks'))
    
    @app.route('/networks/delete', methods=['POST'])
    def networks_delete():
        """Delete a network"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get network reference
        ref = request.form.get('ref')
        
        # Delete network via API
        try:
            response = app.test_client().delete(f'/api/networks/{ref}')
            
            if response.status_code == 200:
                flash('Network deleted successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error deleting network: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error deleting network: {str(e)}', 'danger')
        
        return redirect(url_for('networks'))
    
    # Host Records Routes
    @app.route('/hosts')
    def hosts():
        """Host records management page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get database from app context
        from mock_server.server import db
        
        # Get all host records
        hosts = db.get("record:host", [])
        
        # Check if a next_ip was provided
        next_ip = request.args.get('next_ip', '')
        
        return render_template(
            'hosts.html',
            active_tab='hosts',
            hosts=hosts,
            next_ip=next_ip
        )
    
    @app.route('/hosts/create', methods=['POST'])
    def hosts_create():
        """Create a new host record"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get form data
        name = request.form.get('name')
        ipv4addr = request.form.get('ipv4addr')
        comment = request.form.get('comment')
        
        # Create host record via API
        try:
            # Validate IP
            ipaddress.ip_address(ipv4addr)
            
            data = {
                "name": name,
                "ipv4addr": ipv4addr,
                "comment": comment
            }
            
            response = app.test_client().post(
                '/api/hosts',
                json=data,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                flash(f'Host record {name} created successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error creating host record: {response_data.get("error", "Unknown error")}', 'danger')
        
        except ValueError:
            flash('Invalid IP address format!', 'danger')
        except Exception as e:
            flash(f'Error creating host record: {str(e)}', 'danger')
        
        return redirect(url_for('hosts'))
    
    @app.route('/hosts/delete', methods=['POST'])
    def hosts_delete():
        """Delete a host record"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get host reference
        ref = request.form.get('ref')
        
        # Delete host record via API
        try:
            response = app.test_client().delete(f'/api/hosts/{ref}')
            
            if response.status_code == 200:
                flash('Host record deleted successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error deleting host record: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error deleting host record: {str(e)}', 'danger')
        
        return redirect(url_for('hosts'))
    
    # A Records Routes
    @app.route('/records')
    def records():
        """A records management page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get database from app context
        from mock_server.server import db
        
        # Get all A records
        records = db.get("record:a", [])
        
        # Check if a next_ip was provided
        next_ip = request.args.get('next_ip', '')
        
        return render_template(
            'records.html',
            active_tab='records',
            records=records,
            next_ip=next_ip
        )
    
    @app.route('/records/create', methods=['POST'])
    def records_create():
        """Create a new A record"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get form data
        name = request.form.get('name')
        ipv4addr = request.form.get('ipv4addr')
        comment = request.form.get('comment')
        
        # Create A record via API
        try:
            # Validate IP
            ipaddress.ip_address(ipv4addr)
            
            data = {
                "name": name,
                "ipv4addr": ipv4addr,
                "comment": comment
            }
            
            response = app.test_client().post(
                '/api/records',
                json=data,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                flash(f'A record {name} created successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error creating A record: {response_data.get("error", "Unknown error")}', 'danger')
        
        except ValueError:
            flash('Invalid IP address format!', 'danger')
        except Exception as e:
            flash(f'Error creating A record: {str(e)}', 'danger')
        
        return redirect(url_for('records'))
    
    @app.route('/records/delete', methods=['POST'])
    def records_delete():
        """Delete an A record"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get record reference
        ref = request.form.get('ref')
        
        # Delete A record via API
        try:
            response = app.test_client().delete(f'/api/records/{ref}')
            
            if response.status_code == 200:
                flash('A record deleted successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error deleting A record: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error deleting A record: {str(e)}', 'danger')
        
        return redirect(url_for('records'))
    
    # Fixed Addresses Routes
    @app.route('/fixed')
    def fixed():
        """Fixed addresses management page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get database from app context
        from mock_server.server import db
        
        # Get all fixed addresses
        fixed_addresses = db.get("fixedaddress", [])
        
        # Check if a next_ip was provided
        next_ip = request.args.get('next_ip', '')
        
        return render_template(
            'fixed.html',
            active_tab='fixed',
            fixed_addresses=fixed_addresses,
            next_ip=next_ip
        )
    
    @app.route('/fixed/create', methods=['POST'])
    def fixed_create():
        """Create a new fixed address"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get form data
        ipv4addr = request.form.get('ipv4addr')
        mac = request.form.get('mac')
        name = request.form.get('name')
        comment = request.form.get('comment')
        
        # Create fixed address via API
        try:
            # Validate IP
            ipaddress.ip_address(ipv4addr)
            
            data = {
                "ipv4addr": ipv4addr,
                "mac": mac,
                "name": name,
                "comment": comment
            }
            
            response = app.test_client().post(
                '/api/fixedaddresses',
                json=data,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                flash(f'Fixed address {ipv4addr} created successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error creating fixed address: {response_data.get("error", "Unknown error")}', 'danger')
        
        except ValueError:
            flash('Invalid IP address format!', 'danger')
        except Exception as e:
            flash(f'Error creating fixed address: {str(e)}', 'danger')
        
        return redirect(url_for('fixed'))
    
    @app.route('/fixed/delete', methods=['POST'])
    def fixed_delete():
        """Delete a fixed address"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get fixed address reference
        ref = request.form.get('ref')
        
        # Delete fixed address via API
        try:
            response = app.test_client().delete(f'/api/fixedaddresses/{ref}')
            
            if response.status_code == 200:
                flash('Fixed address deleted successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error deleting fixed address: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error deleting fixed address: {str(e)}', 'danger')
        
        return redirect(url_for('fixed'))
    
    # Configuration Routes
    @app.route('/config', methods=['GET', 'POST'])
    def config():
        """Server configuration page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get configuration from app context
        from mock_server.server import CONFIG
        
        if request.method == 'POST':
            # Update configuration via API
            try:
                # Process configuration updates
                updated_config = {}
                
                # Boolean fields
                boolean_fields = [
                    'simulate_delay', 'simulate_failures', 'simulate_db_lock',
                    'auth_required', 'rate_limit', 'detailed_logging', 'persistent_storage'
                ]
                
                for field in boolean_fields:
                    updated_config[field] = field in request.form
                
                # Numeric fields
                numeric_fields = [
                    'min_delay_ms', 'max_delay_ms', 'failure_rate',
                    'lock_probability', 'rate_limit_requests'
                ]
                
                for field in numeric_fields:
                    if field in request.form and request.form[field]:
                        try:
                            value = float(request.form[field])
                            if field in ['failure_rate', 'lock_probability']:
                                # Ensure values are between 0 and 1
                                value = max(0, min(1, value))
                            else:
                                # Ensure values are positive integers for other fields
                                value = max(0, int(value))
                            updated_config[field] = value
                        except ValueError:
                            pass  # Skip invalid values
                
                # String fields
                string_fields = ['storage_file']
                
                for field in string_fields:
                    if field in request.form:
                        updated_config[field] = request.form[field]
                
                # Update CONFIG
                for key, value in updated_config.items():
                    if key in CONFIG:
                        CONFIG[key] = value
                
                flash('Configuration updated successfully!', 'success')
                
            except Exception as e:
                flash(f'Error updating configuration: {str(e)}', 'danger')
        
        return render_template(
            'config.html',
            active_tab='config',
            config=CONFIG
        )
    
    # Tools Routes
    @app.route('/tools')
    def tools():
        """Tools and utilities page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get database from app context
        from mock_server.server import db
        
        # Get all networks
        networks = db.get("network", [])
        
        # Get grid info
        grid = db.get("grid", [{}])[0] if "grid" in db else {}
        
        # Check if a next_ip was provided
        next_ip = request.args.get('next_ip', '')
        
        return render_template(
            'tools.html',
            active_tab='tools',
            networks=networks,
            grid=grid,
            next_ip=next_ip
        )
    
    @app.route('/tools/next-ip', methods=['POST'])
    def next_available_ip_find():
        """Find next available IP in a network"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get network from form
        network = request.form.get('network')
        
        if not network:
            flash('Please select a network!', 'danger')
            return redirect(url_for('tools'))
        
        # Get next available IP via API
        try:
            response = app.test_client().get(f'/api/nextavailableip/{network}')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                next_ip = data.get('ipv4addr', '')
                flash(f'Next available IP found: {next_ip}', 'success')
                
                # Redirect to tools page with next_ip parameter
                return redirect(url_for('tools', next_ip=next_ip))
            else:
                response_data = json.loads(response.data)
                flash(f'Error finding next available IP: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error finding next available IP: {str(e)}', 'danger')
        
        return redirect(url_for('tools'))
    
    @app.route('/nextip/<path:network>')
    def next_available_ip(network):
        """Get next available IP and redirect to the referrer page"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Get next available IP via API
        try:
            response = app.test_client().get(f'/api/nextavailableip/{network}')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                next_ip = data.get('ipv4addr', '')
                
                # Determine which page to redirect to based on the referer
                referer = request.referrer
                if referer:
                    if 'hosts' in referer:
                        return redirect(url_for('hosts', next_ip=next_ip))
                    elif 'records' in referer:
                        return redirect(url_for('records', next_ip=next_ip))
                    elif 'fixed' in referer:
                        return redirect(url_for('fixed', next_ip=next_ip))
                
                # Default to tools page
                return redirect(url_for('tools', next_ip=next_ip))
            else:
                response_data = json.loads(response.data)
                flash(f'Error finding next available IP: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error finding next available IP: {str(e)}', 'danger')
        
        # Default to tools page
        return redirect(url_for('tools'))
    
    @app.route('/tools/reset', methods=['POST'])
    def reset_database():
        """Reset the database"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Reset database via API
        try:
            response = app.test_client().post('/api/reset')
            
            if response.status_code == 200:
                flash('Database reset successfully!', 'success')
            else:
                response_data = json.loads(response.data)
                flash(f'Error resetting database: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error resetting database: {str(e)}', 'danger')
        
        return redirect(url_for('tools'))
    
    @app.route('/tools/export')
    def export_database():
        """Export the database"""
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        # Export database via API
        try:
            response = app.test_client().get('/api/export')
            
            if response.status_code == 200:
                # Convert JSON to pretty-printed format
                data = json.loads(response.data)
                json_str = json.dumps(data, indent=2)
                
                # Create a file-like object
                mem = BytesIO()
                mem.write(json_str.encode('utf-8'))
                mem.seek(0)
                
                # Return file for download
                return send_file(
                    mem,
                    mimetype='application/json',
                    as_attachment=True,
                    download_name='infoblox_mock_db.json'
                )
            else:
                response_data = json.loads(response.data)
                flash(f'Error exporting database: {response_data.get("error", "Unknown error")}', 'danger')
        except Exception as e:
            flash(f'Error exporting database: {str(e)}', 'danger')
        
        return redirect(url_for('tools'))
    
    # Helper function to create a grid session
    def make_grid_session(app):
        """Create a grid session in the mock server"""
        try:
            # Make a POST request to the grid session endpoint
            response = app.test_client().post(
                '/wapi/v2.11/grid/session',
                headers={
                    'Authorization': 'Basic ' + 'YWRtaW46aW5mb2Jsb3g='  # admin:infoblox in base64
                }
            )
            return response
        except Exception as e:
            logger.error(f"Error creating grid session: {str(e)}")
            return None
    
    logger.info("UI routes initialized")
    return app

def create_template_files():
    """Create all the template files for the web UI"""
    # Only create files if they don't exist - implementation omitted for brevity
    pass

def create_static_files():
    """Create all static files for the web UI"""
    # Only create files if they don't exist - implementation omitted for brevity
    pass