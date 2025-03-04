from flask import Flask, request, jsonify, abort, make_response, render_template, redirect, url_for, flash, session
import json
import ipaddress
import re
import uuid
import time
import random
from datetime import datetime
import logging
import threading
from functools import wraps
import os
import requests

# Import the existing mock server code (assuming it's in a module)
# This allows us to reuse the database and functions
from infoblox_mock_server import db, CONFIG, db_lock, initialize_db, save_db_to_file, load_db_from_file
from infoblox_mock_server import find_objects_by_query, find_object_by_ref, validate_and_prepare_data, generate_ref

# Configure logging
log_format = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("infoblox_web_ui.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'infoblox_web_ui_secret_key')

# Initialize database when starting
load_db_from_file()
if not db.get('network'):
    initialize_db()

# Authentication functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper functions for the web UI
def get_statistics():
    """Get statistics about the mock server database"""
    stats = {}
    for obj_type in db:
        if isinstance(db[obj_type], list):
            stats[obj_type] = len(db[obj_type])
    return stats

def get_object_types():
    """Get all available object types"""
    return [obj_type for obj_type in db if isinstance(db[obj_type], list)]

def make_api_request(method, path, params=None, data=None):
    """Make a request to the Infoblox mock API"""
    base_url = "http://localhost:8080/wapi/v2.11"
    url = f"{base_url}/{path}"
    
    auth = (session.get('username', 'admin'), session.get('password', 'infoblox'))
    
    try:
        if method.lower() == 'get':
            response = requests.get(url, params=params, auth=auth)
        elif method.lower() == 'post':
            response = requests.post(url, json=data, auth=auth)
        elif method.lower() == 'put':
            response = requests.put(url, json=data, auth=auth)
        elif method.lower() == 'delete':
            response = requests.delete(url, auth=auth)
        else:
            return {"error": "Invalid method"}, 400
        
        if response.status_code == 200:
            return response.json(), 200
        else:
            return {"error": response.text}, response.status_code
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, 500

# Routes for web UI
@app.route('/')
@login_required
def dashboard():
    """Main dashboard page"""
    stats = get_statistics()
    
    # Get grid info
    grid_info = db.get('grid', [{}])[0] if db.get('grid') else {}
    
    # Get some recent networks
    networks = db.get('network', [])[:5]
    
    # Get some recent hosts
    hosts = db.get('record:host', [])[:5]
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          grid_info=grid_info,
                          networks=networks,
                          hosts=hosts,
                          config=CONFIG)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple authentication (would use the actual API in production)
        if username == 'admin' and password == 'infoblox':
            session['logged_in'] = True
            session['username'] = username
            session['password'] = password
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/networks')
@login_required
def networks():
    """Networks page"""
    # Get all networks using the API function
    networks = find_objects_by_query('network', {})
    return render_template('networks.html', networks=networks)

@app.route('/networks/new', methods=['GET', 'POST'])
@login_required
def new_network():
    """Create new network page"""
    if request.method == 'POST':
        network_data = {
            'network': request.form.get('network'),
            'comment': request.form.get('comment', ''),
            'network_view': request.form.get('network_view', 'default')
        }
        
        # Validate network
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$', network_data['network']):
            flash('Invalid network format. Use CIDR notation (e.g., 192.168.1.0/24)', 'danger')
            return render_template('network_form.html', network=network_data)
        
        # Create the network using the existing functions
        with db_lock:
            validated_data, error = validate_and_prepare_data('network', network_data)
            if error:
                flash(f'Validation error: {error}', 'danger')
                return render_template('network_form.html', network=network_data)
            
            # Create the object reference
            validated_data["_ref"] = generate_ref('network', validated_data)
            
            # Check for duplicate network
            for existing in db.get('network', []):
                if existing.get("network") == validated_data.get("network") and \
                   existing.get("network_view") == validated_data.get("network_view"):
                    flash(f'Network already exists: {validated_data.get("network")}', 'danger')
                    return render_template('network_form.html', network=network_data)
            
            # Save to database
            if 'network' not in db:
                db['network'] = []
            
            db['network'].append(validated_data)
            save_db_to_file()
            
            flash(f'Network {validated_data["network"]} created successfully', 'success')
            return redirect(url_for('networks'))
    
    return render_template('network_form.html', network={})

@app.route('/networks/<path:ref>')
@login_required
def view_network(ref):
    """View network details"""
    network = find_object_by_ref(ref)
    if not network:
        flash('Network not found', 'danger')
        return redirect(url_for('networks'))
    
    return render_template('network_details.html', network=network)

@app.route('/networks/<path:ref>/edit', methods=['GET', 'POST'])
@login_required
def edit_network(ref):
    """Edit network page"""
    network = find_object_by_ref(ref)
    if not network:
        flash('Network not found', 'danger')
        return redirect(url_for('networks'))
    
    if request.method == 'POST':
        # Update fields that are allowed to be changed
        update_data = {
            'comment': request.form.get('comment', ''),
            # Add other fields that can be updated
        }
        
        with db_lock:
            # Update the network
            for key, value in update_data.items():
                network[key] = value
            
            # Update timestamp
            network["_modify_time"] = datetime.now().isoformat()
            save_db_to_file()
            
            flash('Network updated successfully', 'success')
            return redirect(url_for('view_network', ref=ref))
    
    return render_template('network_form.html', network=network, edit=True)

@app.route('/networks/<path:ref>/delete', methods=['POST'])
@login_required
def delete_network(ref):
    """Delete network"""
    network = find_object_by_ref(ref)
    if not network:
        flash('Network not found', 'danger')
        return redirect(url_for('networks'))
    
    with db_lock:
        # Remove from database
        db['network'] = [n for n in db['network'] if n["_ref"] != ref]
        save_db_to_file()
        
        flash('Network deleted successfully', 'success')
        return redirect(url_for('networks'))

@app.route('/hosts')
@login_required
def hosts():
    """Host records page"""
    hosts = find_objects_by_query('record:host', {})
    return render_template('hosts.html', hosts=hosts)

@app.route('/hosts/new', methods=['GET', 'POST'])
@login_required
def new_host():
    """Create new host record page"""
    if request.method == 'POST':
        host_data = {
            'name': request.form.get('name'),
            'ipv4addrs': [{'ipv4addr': request.form.get('ipv4addr')}],
            'comment': request.form.get('comment', ''),
            'view': request.form.get('view', 'default')
        }
        
        # Create the host record
        with db_lock:
            validated_data, error = validate_and_prepare_data('record:host', host_data)
            if error:
                flash(f'Validation error: {error}', 'danger')
                return render_template('host_form.html', host=host_data)
            
            # Create the object reference
            validated_data["_ref"] = generate_ref('record:host', validated_data)
            
            # Check for duplicate
            for existing in db.get('record:host', []):
                if existing.get("name") == validated_data.get("name") and \
                   existing.get("view") == validated_data.get("view"):
                    flash(f'Host record already exists: {validated_data.get("name")}', 'danger')
                    return render_template('host_form.html', host=host_data)
            
            # Save to database
            if 'record:host' not in db:
                db['record:host'] = []
            
            db['record:host'].append(validated_data)
            save_db_to_file()
            
            flash(f'Host record {validated_data["name"]} created successfully', 'success')
            return redirect(url_for('hosts'))
    
    return render_template('host_form.html', host={})

@app.route('/hosts/<path:ref>')
@login_required
def view_host(ref):
    """View host details"""
    host = find_object_by_ref(ref)
    if not host:
        flash('Host record not found', 'danger')
        return redirect(url_for('hosts'))
    
    return render_template('host_details.html', host=host)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Server settings page"""
    if request.method == 'POST':
        # Update configuration settings
        with db_lock:
            for key in CONFIG:
                if key in request.form:
                    # Handle boolean values
                    if isinstance(CONFIG[key], bool):
                        CONFIG[key] = request.form.get(key) == 'on'
                    # Handle numeric values
                    elif isinstance(CONFIG[key], (int, float)):
                        try:
                            CONFIG[key] = int(request.form.get(key))
                        except ValueError:
                            pass
                    # Handle string values
                    else:
                        CONFIG[key] = request.form.get(key)
            
            flash('Settings updated successfully', 'success')
            return redirect(url_for('settings'))
    
    return render_template('settings.html', config=CONFIG)

@app.route('/database')
@login_required
def database():
    """Database page - view all object types and counts"""
    stats = get_statistics()
    return render_template('database.html', stats=stats)

@app.route('/database/<obj_type>')
@login_required
def object_list(obj_type):
    """List objects of a specific type"""
    if obj_type not in db or not isinstance(db[obj_type], list):
        flash(f'Invalid object type: {obj_type}', 'danger')
        return redirect(url_for('database'))
    
    objects = find_objects_by_query(obj_type, {})
    return render_template('object_list.html', obj_type=obj_type, objects=objects)

@app.route('/database/export', methods=['POST'])
@login_required
def export_database():
    """Export the database as JSON"""
    response = make_response(json.dumps(db, indent=2))
    response.headers["Content-Disposition"] = "attachment; filename=infoblox_mock_db.json"
    response.headers["Content-Type"] = "application/json"
    return response

@app.route('/database/reset', methods=['POST'])
@login_required
def reset_database():
    """Reset the database to defaults"""
    with db_lock:
        # Clear all object types
        for obj_type in db:
            if isinstance(db[obj_type], list):
                db[obj_type] = []
        
        # Reinitialize with default data
        initialize_db()
        save_db_to_file()
        
        flash('Database reset to default values', 'success')
        return redirect(url_for('database'))

@app.route('/api_console', methods=['GET', 'POST'])
@login_required
def api_console():
    """API console for testing API requests"""
    result = None
    
    if request.method == 'POST':
        method = request.form.get('method', 'GET')
        path = request.form.get('path', '')
        params = request.form.get('params', '')
        data = request.form.get('data', '')
        
        # Parse parameters
        try:
            params_dict = json.loads(params) if params.strip() else None
        except json.JSONDecodeError:
            flash('Invalid JSON in parameters', 'danger')
            return render_template('api_console.html', method=method, path=path, params=params, data=data)
        
        # Parse data
        try:
            data_dict = json.loads(data) if data.strip() else None
        except json.JSONDecodeError:
            flash('Invalid JSON in request body', 'danger')
            return render_template('api_console.html', method=method, path=path, params=params, data=data)
        
        # Make the API request
        result, status_code = make_api_request(method, path, params_dict, data_dict)
        
        if 'error' in result and status_code != 200:
            flash(f'API error: {result["error"]}', 'danger')
    
    return render_template('api_console.html', result=result)

# Run the web UI app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081, debug=True)