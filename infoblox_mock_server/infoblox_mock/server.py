"""
Main Flask application for Infoblox Mock Server
"""

from flask import Flask
import logging
import os

from infoblox_mock.config import load_config, CONFIG
from infoblox_mock.db import initialize_db, load_db_from_file
from infoblox_mock import routes
from infoblox_mock.mock_responses import load_mock_responses, find_mock_response, record_interaction
from infoblox_mock.statistics import api_stats

logger = logging.getLogger(__name__)

def create_app(config_file=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Add statistics tracking
    @app.before_request
    def track_request_start():
        request.stats_id = str(uuid.uuid4())
        username = 'anonymous'
        if request.authorization:
            username = request.authorization.username
        api_stats.start_request(request.stats_id, request.method, request.path, username)
    
    @app.after_request
    def track_request_end(response):
        if hasattr(request, 'stats_id'):
            api_stats.end_request(request.stats_id, response.status_code)
        return response
        
    # Load configuration
    if config_file and os.path.exists(config_file):
        load_config(config_file)
        logger.info(f"Loaded configuration from {config_file}")
    
    # Initialize database
    if CONFIG['persistent_storage'] and os.path.exists(CONFIG['storage_file']):
        load_db_from_file()
    else:
        initialize_db()
    
    # Load mock responses if configured
    if CONFIG.get('mock_responses_dir'):
        load_mock_responses(CONFIG.get('mock_responses_dir'))
    
    # Register routes
    routes.register_routes(app)
    
    # Add response recording if enabled
    if CONFIG.get('record_mode', False):
        @app.after_request
        def record_response(response):
            record_interaction(response)
            return response
    
    logger.info(f"Infoblox Mock Server initialized with config: {CONFIG}")
    return app