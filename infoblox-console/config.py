"""
Configuration settings for the Infoblox API Console
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Application configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
    
    # Mock Server settings
    MOCK_SERVER_URL = os.environ.get('MOCK_SERVER_URL', 'http://localhost:8000')
    MOCK_SERVER_API_KEY = os.environ.get('MOCK_SERVER_API_KEY', '')
    
    # UI Settings
    DEFAULT_THEME = os.environ.get('DEFAULT_THEME', 'light')
    MAX_HISTORY_ITEMS = int(os.environ.get('MAX_HISTORY_ITEMS', 100))
    REFRESH_INTERVAL = int(os.environ.get('REFRESH_INTERVAL', 5000))  # ms
    
    # Feature flags
    ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'True').lower() in ('true', '1', 't')
    ENABLE_NOTIFICATIONS = os.environ.get('ENABLE_NOTIFICATIONS', 'True').lower() in ('true', '1', 't')
    
    # Default headers for API requests
    DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    # API categories for organization in UI
    API_CATEGORIES = [
        {'id': 'dns', 'name': 'DNS Records', 'icon': 'fa-globe'},
        {'id': 'ipam', 'name': 'IP Address Management', 'icon': 'fa-network-wired'},
        {'id': 'dhcp', 'name': 'DHCP', 'icon': 'fa-exchange-alt'},
        {'id': 'users', 'name': 'Users & Groups', 'icon': 'fa-users'},
        {'id': 'grid', 'name': 'Grid Management', 'icon': 'fa-server'},
    ]