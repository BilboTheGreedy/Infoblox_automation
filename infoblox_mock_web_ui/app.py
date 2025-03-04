#!/usr/bin/env python3
"""
Infoblox Mock Server with Web UI
Main application entry point
"""

import os
import logging
from flask import Flask
from mock_server.server import setup_mock_server
from web_ui.routes import setup_web_ui

# Configure logging
log_format = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("infoblox_mock_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Load configuration
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'infoblox_mock_db.json'),
    )
    
    # Setup mock server functionality
    db, CONFIG = setup_mock_server(app)
    
    # Setup web UI functionality
    setup_web_ui(app, db, CONFIG)
    
    logger.info("Infoblox Mock Server initialized with Web UI")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)