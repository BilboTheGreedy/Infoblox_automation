"""
Web UI package for the Infoblox Mock Server.
Provides a graphical interface for managing the mock server.
"""

from web_ui.routes import setup_ui_routes
from web_ui.api import setup_api_routes

def setup_web_ui(app, db, CONFIG):
    """
    Setup the web UI by initializing both UI routes and API endpoints
    
    Parameters:
    - app: Flask application instance
    - db: Database dictionary
    - CONFIG: Configuration dictionary
    
    Returns:
    - The configured Flask application
    """
    # Setup UI routes
    app = setup_ui_routes(app)
    
    # Setup API endpoints
    app = setup_api_routes(app, db, CONFIG)
    
    return app