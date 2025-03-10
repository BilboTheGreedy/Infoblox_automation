#!/usr/bin/env python3
"""
Infoblox API Mock Console - Main Application
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from utils.api_client import InfobloxApiClient
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize API client with mock server URL from config
api_client = InfobloxApiClient(app.config['MOCK_SERVER_URL'])

# Store recent API requests/responses for history
request_history = []

# ----- Routes -----

@app.route('/')
def index():
    """Render the main dashboard page."""
    server_status = api_client.get_server_status()
    return render_template('index.html', 
                           server_status=server_status,
                           api_url=app.config['MOCK_SERVER_URL'])

@app.route('/requests')
def requests_page():
    """Render the request history page."""
    return render_template('requests.html', 
                           requests=request_history)

@app.route('/settings')
def settings():
    """Render the settings page."""
    return render_template('settings.html', 
                           config=app.config)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    """Update application settings."""
    if request.method == 'POST':
        app.config['MOCK_SERVER_URL'] = request.form.get('server_url')
        api_client.base_url = app.config['MOCK_SERVER_URL']
        # Additional settings can be updated here
        return redirect(url_for('settings'))

# ----- API Proxy Routes -----

@app.route('/api/execute', methods=['POST'])
def execute_request():
    """Execute a request to the mock server."""
    data = request.json
    method = data.get('method', 'GET')
    endpoint = data.get('endpoint', '/')
    request_body = data.get('body', {})
    headers = data.get('headers', {})
    
    try:
        # Execute the request via our API client
        response = api_client.execute_request(
            method=method,
            endpoint=endpoint,
            data=request_body,
            headers=headers
        )
        
        # Create a record of this request
        request_record = {
            'id': len(request_history) + 1,
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'endpoint': endpoint,
            'request': request_body,
            'response': response,
            'status': response.get('status', 'Unknown')
        }
        
        # Add to history and limit to latest 100 requests
        request_history.insert(0, request_record)
        if len(request_history) > 100:
            request_history.pop()
        
        # Emit the new request via Socket.IO
        socketio.emit('new_request', request_record)
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error executing request: {str(e)}")
        error_response = {
            'status': 'error',
            'message': str(e)
        }
        return jsonify(error_response), 500

@app.route('/api/server-status')
def server_status():
    """Get current mock server status."""
    try:
        status = api_client.get_server_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting server status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/available-endpoints')
def available_endpoints():
    """Get available mock server endpoints."""
    try:
        endpoints = api_client.get_available_endpoints()
        return jsonify(endpoints)
    except Exception as e:
        logger.error(f"Error getting endpoints: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear the request history."""
    global request_history
    request_history = []
    return jsonify({'status': 'success', 'message': 'History cleared'})

# ----- Socket.IO Events -----

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")

# ----- Error Handlers -----

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500

# ----- Main -----

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Infoblox API Console on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)