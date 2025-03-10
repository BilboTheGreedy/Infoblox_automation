/**
 * Socket.IO integration for real-time updates
 */

// Socket manager
const socketManager = {
    // Socket.IO instance
    socket: null,
    
    // Connected state
    connected: false,
    
    // Reconnection attempts
    reconnectAttempts: 0,
    
    // Maximum reconnection attempts
    maxReconnectAttempts: 5,
    
    /**
     * Initialize the Socket.IO connection
     */
    init: function() {
        try {
            // Initialize Socket.IO
            this.socket = io();
            
            // Setup event handlers
            this.setupEventHandlers();
            
            console.log('Socket.IO initialized');
        } catch (error) {
            console.error('Error initializing Socket.IO:', error);
        }
    },
    
    /**
     * Setup Socket.IO event handlers
     */
    setupEventHandlers: function() {
        if (!this.socket) return;
        
        // Connection established
        this.socket.on('connect', () => {
            console.log('Socket.IO connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        });
        
        // Connection response
        this.socket.on('connection_response', (data) => {
            console.log('Socket.IO connection response:', data);
        });
        
        // Connection lost
        this.socket.on('disconnect', (reason) => {
            console.log('Socket.IO disconnected:', reason);
            this.connected = false;
            this.updateConnectionStatus(false);
            
            // Attempt to reconnect
            if (reason === 'io server disconnect') {
                // The server has forcefully disconnected the socket
                setTimeout(() => {
                    if (this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.reconnectAttempts++;
                        this.socket.connect();
                    }
                }, 5000);
            }
        });
        
        // Error event
        this.socket.on('error', (error) => {
            console.error('Socket.IO error:', error);
        });
        
        // New request event
        this.socket.on('new_request', (data) => {
            this.handleNewRequest(data);
        });
        
        // Server status update
        this.socket.on('server_status', (data) => {
            this.handleServerStatus(data);
        });
    },
    
    /**
     * Update the connection status in the UI
     */
    updateConnectionStatus: function(connected) {
        // This could update a UI element to indicate connection status
        const statusIndicator = document.getElementById('server-status-indicator');
        const statusText = document.getElementById('server-status-text');
        
        if (statusIndicator && statusText) {
            if (connected) {
                statusIndicator.classList.remove('status-offline');
                statusIndicator.classList.add('status-online');
                statusText.textContent = 'Online';
            } else {
                statusIndicator.classList.remove('status-online');
                statusIndicator.classList.add('status-offline');
                statusText.textContent = 'Offline';
            }
        }
        
        // Show notification if appropriate
        if (!connected && this.connected) {
            this.showNotification('Server connection lost. Attempting to reconnect...', 'warning');
        } else if (connected && !this.connected) {
            this.showNotification('Server connection restored.', 'success');
        }
    },
    
    /**
     * Handle a new request event
     */
    handleNewRequest: function(data) {
        console.log('New request received:', data);
        
        // Add to recent requests list
        this.addToRecentRequests(data);
        
        // Update metrics if needed
        this.updateMetrics();
        
        // Show notification if appropriate
        const enableNotifications = document.getElementById('enable-notifications') && 
            document.getElementById('enable-notifications').checked;
            
        if (enableNotifications) {
            const isSuccess = data.status >= 200 && data.status < 300;
            const notifySuccess = document.getElementById('notify-success') && 
                document.getElementById('notify-success').checked;
            const notifyError = document.getElementById('notify-error') && 
                document.getElementById('notify-error').checked;
                
            if ((isSuccess && notifySuccess) || (!isSuccess && notifyError)) {
                this.showBrowserNotification(
                    `${data.method} ${data.endpoint}`,
                    `Status: ${data.status} - ${isSuccess ? 'Success' : 'Error'}`
                );
            }
        }
    },
    
    /**
     * Handle server status update
     */
    handleServerStatus: function(data) {
        console.log('Server status update:', data);
        
        // Update status display
        const statusDisplay = document.getElementById('server-status-display');
        if (statusDisplay) {
            if (data.status === 'online') {
                statusDisplay.innerHTML = '<span class="text-success">Online</span>';
            } else if (data.status === 'offline') {
                statusDisplay.innerHTML = '<span class="text-danger">Offline</span>';
            } else {
                statusDisplay.innerHTML = '<span class="text-warning">Unknown</span>';
            }
        }
        
        // Update server details
        if (data.version) {
            const versionElement = document.querySelector('.server-details .version');
            if (versionElement) {
                versionElement.textContent = data.version;
            }
        }
        
        if (data.uptime) {
            const uptimeElement = document.querySelector('.server-details .uptime');
            if (uptimeElement) {
                uptimeElement.textContent = data.uptime;
            }
        }
    },
    
    /**
     * Add to recent requests list
     */
    addToRecentRequests: function(data) {
        const recentList = document.getElementById('recent-requests-list');
        if (!recentList) return;
        
        // Remove empty placeholder if present
        const emptyPlaceholder = recentList.querySelector('.text-center.p-4');
        if (emptyPlaceholder) {
            emptyPlaceholder.remove();
        }
        
        // Create item HTML
        const itemHtml = `
            <div class="recent-request-item" data-request-id="${data.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge rounded-pill bg-${this.getMethodColor(data.method)} me-2">${data.method}</span>
                        <span class="endpoint">${data.endpoint}</span>
                    </div>
                    <span class="badge rounded-pill bg-${this.getStatusColor(data.status)}">${data.status}</span>
                </div>
                <div class="small text-muted mt-1">${this.formatTimestamp(data.timestamp)}</div>
            </div>
        `;
        
        // Insert at the beginning
        recentList.insertAdjacentHTML('afterbegin', itemHtml);
        
        // Limit to 5 most recent
        const items = recentList.querySelectorAll('.recent-request-item');
        if (items.length > 5) {
            for (let i = 5; i < items.length; i++) {
                items[i].remove();
            }
        }
        
        // Set up click handler
        const newItem = recentList.querySelector('.recent-request-item');
        if (newItem) {
            newItem.addEventListener('click', () => {
                window.location.href = `/requests#${data.id}`;
            });
        }
    },
    
    /**
     * Update metrics display
     */
    updateMetrics: function() {
        // This would be more sophisticated in a real app,
        // but for demo purposes we'll just increment some counters
        const totalRequests = document.getElementById('total-requests-count');
        if (totalRequests) {
            const current = parseInt(totalRequests.textContent, 10) || 0;
            totalRequests.textContent = current + 1;
        }
        
        // Update success/error counts randomly for the demo
        const successRequests = document.getElementById('success-requests-count');
        const errorRequests = document.getElementById('error-requests-count');
        
        if (successRequests && errorRequests) {
            // Randomly decide if this was a success or error
            if (Math.random() > 0.2) {
                // 80% success rate
                const current = parseInt(successRequests.textContent, 10) || 0;
                successRequests.textContent = current + 1;
            } else {
                const current = parseInt(errorRequests.textContent, 10) || 0;
                errorRequests.textContent = current + 1;
            }
        }
    },
    
    /**
     * Format a timestamp for display
     */
    formatTimestamp: function(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    },
    
    /**
     * Get color class for HTTP method
     */
    getMethodColor: function(method) {
        switch (method.toUpperCase()) {
            case 'GET': return 'primary';
            case 'POST': return 'success';
            case 'PUT': return 'info';
            case 'DELETE': return 'danger';
            case 'PATCH': return 'warning';
            default: return 'secondary';
        }
    },
    
    /**
     * Get color class for status code
     */
    getStatusColor: function(statusCode) {
        if (statusCode >= 200 && statusCode < 300) return 'success';
        if (statusCode >= 300 && statusCode < 400) return 'info';
        if (statusCode >= 400 && statusCode < 500) return 'warning';
        if (statusCode >= 500) return 'danger';
        return 'secondary';
    },
    
    /**
     * Show a notification in the UI
     */
    showNotification: function(message, type = 'info') {
        const alertClass = `alert-${type}`;
        const alert = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        const contentContainer = document.querySelector('.content-container');
        if (contentContainer) {
            contentContainer.insertAdjacentHTML('afterbegin', alert);
            
            // Auto-dismiss after 5 seconds
            const alertElement = contentContainer.querySelector('.alert');
            setTimeout(() => {
                if (alertElement) {
                    alertElement.remove();
                }
            }, 5000);
        }
    },
    
    /**
     * Show a browser notification
     */
    showBrowserNotification: function(title, body) {
        // Check if browser notifications are supported
        if (!('Notification' in window)) {
            console.warn('Browser notifications not supported');
            return;
        }
        
        // Check if permission is granted
        if (Notification.permission === 'granted') {
            const notification = new Notification(title, {
                body: body,
                icon: '/static/img/favicon.ico'
            });
            
            // Close after 5 seconds
            setTimeout(() => {
                notification.close();
            }, 5000);
        } else if (Notification.permission !== 'denied') {
            // Request permission
            Notification.requestPermission().then((permission) => {
                if (permission === 'granted') {
                    this.showBrowserNotification(title, body);
                }
            });
        }
    },
    
    /**
     * Emit an event to the server
     */
    emit: function(event, data) {
        if (this.socket && this.connected) {
            this.socket.emit(event, data);
        } else {
            console.warn('Socket not connected, cannot emit:', event);
        }
    }
};

// Initialize Socket.IO when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    socketManager.init();
});