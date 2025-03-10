#!/usr/bin/env python3
"""
Infoblox Mock Server - Main entry point
Run this script to start the mock server
"""

import argparse
import logging
from infoblox_mock.server import create_app

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Infoblox Mock Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--log-file', default='infoblox_mock_server.log', help='Log file path')
    parser.add_argument('--config', help='Path to config file')
    
    args = parser.parse_args()
    
    # Configure logging
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(args.log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create and run the application
    app = create_app(config_file=args.config)
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()