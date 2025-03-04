"""
Main Flask application for Infoblox Mock Server
"""

from flask import Flask
import logging
import os

from infoblox_mock.config import load_config, CONFIG
from infoblox_mock.db import initialize_db, load_db_from_file
from infoblox_mock import routes

logger = logging.getLogger(__name__)

def create_app(config_file=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    if config_file and os.path.exists(config_file):
        load_config(config_file)
        logger.info(f"Loaded configuration from {config_file}")
    
    # Initialize database
    if CONFIG['persistent_storage'] and os.path.exists(CONFIG['storage_file']):
        load_db_from_file()
    else:
        initialize_db()
    
    # Register routes
    routes.register_routes(app)
    
    logger.info(f"Infoblox Mock Server initialized with config: {CONFIG}")
    return app
