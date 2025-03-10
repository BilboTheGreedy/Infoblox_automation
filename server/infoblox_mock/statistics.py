"""
API usage statistics for Infoblox Mock Server
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class APIStatistics:
    """Class for tracking API usage statistics"""
    
    def __init__(self):
        """Initialize statistics tracking"""
        self.lock = threading.RLock()
        self.reset_time = datetime.now()
        
        # Overall statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        
        # Detailed statistics
        self.requests_by_endpoint = defaultdict(int)
        self.requests_by_method = defaultdict(int)
        self.requests_by_user = defaultdict(int)
        self.requests_by_status = defaultdict(int)
        self.requests_by_hour = defaultdict(int)
        
        # Current hour tracking
        self.current_hour = datetime.now().hour
        self.hourly_stats = {}
        
        # Request timing data
        self.request_times = {}
        
        # Top 10 longest requests
        self.slowest_requests = []
        
        # Last 50 errors
        self.recent_errors = []
    
    def start_request(self, request_id, method, endpoint, username='anonymous'):
        """Record the start of a request"""
        with self.lock:
            self.request_times[request_id] = {
                'start_time': time.time(),
                'method': method,
                'endpoint': endpoint,
                'username': username
            }
    
    def end_request(self, request_id, status_code):
        """Record the end of a request"""
        with self.lock:
            # Skip if the request wasn't recorded at start
            if request_id not in self.request_times:
                return
            
            # Get request data
            req_data = self.request_times[request_id]
            end_time = time.time()
            duration = end_time - req_data['start_time']
            
            # Update overall statistics
            self.total_requests += 1
            
            # Check if hour changed
            hour = datetime.now().hour
            if hour != self.current_hour:
                # Archive the stats for the previous hour
                self.hourly_stats[self.current_hour] = {
                    'total': self.requests_by_hour[self.current_hour],
                    'by_endpoint': Counter({k: v for k, v in self.requests_by_endpoint.items()}),
                    'by_method': Counter({k: v for k, v in self.requests_by_method.items()}),
                    'by_status': Counter({k: v for k, v in self.requests_by_status.items()})
                }
                self.current_hour = hour
            
            # Update detailed statistics
            self.requests_by_endpoint[req_data['endpoint']] += 1
            self.requests_by_method[req_data['method']] += 1
            self.requests_by_user[req_data['username']] += 1
            self.requests_by_status[status_code] += 1
            self.requests_by_hour[hour] += 1
            
            # Update response times
            self.response_times.append(duration)
            
            # Update success/failure counts
            if 200 <= status_code < 400:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                
                # Add to recent errors
                error_data = {
                    'time': datetime.now().isoformat(),
                    'method': req_data['method'],
                    'endpoint': req_data['endpoint'],
                    'username': req_data['username'],
                    'status': status_code,
                    'duration': duration
                }
                self.recent_errors.append(error_data)
                # Keep only the last 50 errors
                if len(self.recent_errors) > 50:
                    self.recent_errors.pop(0)
            
            # Update slowest requests
            slow_req = {
                'method': req_data['method'],
                'endpoint': req_data['endpoint'],
                'username': req_data['username'],
                'status': status_code,
                'duration': duration,
                'time': datetime.now().isoformat()
            }
            
            self.slowest_requests.append(slow_req)
            # Sort and keep only the 10 slowest
            self.slowest_requests.sort(key=lambda x: x['duration'], reverse=True)
            if len(self.slowest_requests) > 10:
                self.slowest_requests.pop()
            
            # Remove the request from tracking
            del self.request_times[request_id]
    
    def get_stats(self):
        """Get the current statistics"""
        with self.lock:
            stats = {
                'overall': {
                    'total_requests': self.total_requests,
                    'successful_requests': self.successful_requests,
                    'failed_requests': self.failed_requests,
                    'success_rate': 0 if self.total_requests == 0 else (self.successful_requests / self.total_requests) * 100,
                    'avg_response_time': 0 if not self.response_times else sum(self.response_times) / len(self.response_times)
                },
                'by_endpoint': dict(self.requests_by_endpoint),
                'by_method': dict(self.requests_by_method),
                'by_user': dict(self.requests_by_user),
                'by_status': dict(self.requests_by_status),
                'by_hour': dict(self.requests_by_hour),
                'hourly_stats': self.hourly_stats,
                'slowest_requests': self.slowest_requests,
                'recent_errors': self.recent_errors,
                'uptime': str(datetime.now() - self.reset_time)
            }
            
            return stats
    
    def reset_stats(self):
        """Reset all statistics"""
        with self.lock:
            self.__init__()
            return True

# Create a global instance
api_stats = APIStatistics()