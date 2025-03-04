"""
Middleware and decorators for Infoblox Mock Server
"""

import time
import random
import logging
from functools import wraps
from flask import request, jsonify

from infoblox_mock.config import CONFIG
from infoblox_mock.db import db, db_lock, rate_limit_data

logger = logging.getLogger(__name__)

def simulate_delay(func):
    """Decorator to simulate network delay"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if CONFIG['simulate_delay']:
            delay = random.randint(CONFIG['min_delay_ms'], CONFIG['max_delay_ms']) / 1000.0
            time.sleep(delay)
            logger.debug(f"Simulated delay of {delay:.2f} seconds")
        return func(*args, **kwargs)
    return wrapper

def simulate_failures(func):
    """Decorator to simulate random server failures"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if CONFIG['simulate_failures'] and random.random() < CONFIG['failure_rate']:
            status_codes = [500, 502, 503, 504]
            status = random.choice(status_codes)
            error_msg = {
                500: "Internal Server Error",
                502: "Bad Gateway",
                503: "Service Unavailable",
                504: "Gateway Timeout"
            }
            logger.debug(f"Simulating server failure with {status} status code")
            response = jsonify({"Error": error_msg[status]})
            response.status_code = status
            return response
        return func(*args, **kwargs)
    return wrapper

def rate_limit(func):
    """Decorator to implement rate limiting"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not CONFIG['rate_limit']:
            return func(*args, **kwargs)
        
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Initialize if this is a new client
        if client_ip not in rate_limit_data['counters']:
            rate_limit_data['counters'][client_ip] = 0
            rate_limit_data['windows'][client_ip] = current_time + 60  # 1 minute window
        
        # Reset counter if the window has expired
        if current_time > rate_limit_data['windows'][client_ip]:
            rate_limit_data['counters'][client_ip] = 0
            rate_limit_data['windows'][client_ip] = current_time + 60
        
        # Check the rate limit
        if rate_limit_data['counters'][client_ip] >= CONFIG['rate_limit_requests']:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            response = jsonify({"Error": "Too many requests", "text": "Rate limit exceeded"})
            response.status_code = 429
            return response
        
        # Increment the counter
        rate_limit_data['counters'][client_ip] += 1
        return func(*args, **kwargs)
    return wrapper

def require_auth(func):
    """Decorator to check if authentication is required"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not CONFIG['auth_required']:
            return func(*args, **kwargs)
        
        # Basic auth header check
        auth = request.authorization
        client_ip = request.remote_addr
        
        # Skip auth check for session endpoints
        if request.path.endswith('/grid/session'):
            return func(*args, **kwargs)
        
        # Check if user has an active session
        session_found = False
        for username, sessions in db['activeuser'].items():
            if client_ip in sessions:
                session_found = True
                break
        
        if not session_found:
            logger.warning(f"Unauthorized access attempt from {client_ip}")
            response = jsonify({"Error": "Unauthorized", "text": "Authentication required"})
            response.status_code = 401
            return response
        
        return func(*args, **kwargs)
    return wrapper

def db_transaction(func):
    """Decorator to handle database transactions with locking"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if CONFIG['simulate_db_lock'] and random.random() < CONFIG['lock_probability']:
            logger.warning("Simulating a database lock")
            response = jsonify({"Error": "Database is locked", "text": "Try again later"})
            response.status_code = 503
            return response
        
        with db_lock:
            return func(*args, **kwargs)
    return wrapper

def log_request(func):
    """Decorator to log request details"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if CONFIG['detailed_logging']:
            logger.info(f"Request: {request.method} {request.path}")
            logger.info(f"Headers: {dict(request.headers)}")
            logger.info(f"Query Params: {request.args}")
            if request.is_json and request.data:
                logger.info(f"Body: {request.json}")
        return func(*args, **kwargs)
    return wrapper

# Combined decorator for common route handling
def api_route(func):
    """Combined decorator for standard API route handling"""
    @wraps(func)
    @log_request
    @rate_limit
    @require_auth
    @simulate_failures
    @simulate_delay
    @db_transaction
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
