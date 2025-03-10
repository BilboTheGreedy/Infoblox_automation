/**
 * Console UI behaviors and interactions
 */

// Console manager
const consoleManager = {
    /**
     * Initialize the console
     */
    init: function() {
        // Setup responsive behaviors
        this.setupResponsive();
        
        // Setup theme handling
        this.setupTheme();
        
        // Setup endpoint suggestions
        this.setupEndpointSuggestions();
        
        // Setup notifications
        this.setupNotifications();
        
        console.log('Console manager initialized');
    },
    
    /**
     * Setup responsive behaviors
     */
    setupResponsive: function() {
        // Sidebar toggle button for mobile
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('show');
            });
            
            // Close button inside sidebar
            const sidebarClose = document.getElementById('sidebar-close');
            if (sidebarClose) {
                sidebarClose.addEventListener('click', () => {
                    sidebar.classList.remove('show');
                });
            }
            
            // Close sidebar when clicking outside on mobile
            document.addEventListener('click', (e) => {
                if (window.innerWidth < 768 && 
                    sidebar.classList.contains('show') && 
                    !sidebar.contains(e.target) && 
                    e.target !== sidebarToggle) {
                    sidebar.classList.remove('show');
                }
            });
        }
        
        // Apply proper spacing for footer
        if (mainContent) {
            const footer = document.querySelector('.footer');
            if (footer) {
                const footerHeight = footer.offsetHeight;
                mainContent.style.paddingBottom = footerHeight + 'px';
            }
        }
    },
    
    /**
     * Setup theme handling
     */
    setupTheme: function() {
        // Theme toggle button
        const themeToggle = document.getElementById('theme-toggle');
        const html = document.documentElement;
        
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const currentTheme = html.getAttribute('data-bs-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                
                html.setAttribute('data-bs-theme', newTheme);
                localStorage.setItem('theme', newTheme);
                
                // Update toggle icon
                themeToggle.innerHTML = newTheme === 'dark' ? 
                    '<i class="fas fa-sun"></i>' : 
                    '<i class="fas fa-moon"></i>';
            });
            
            // Load saved theme or use system preference
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                html.setAttribute('data-bs-theme', savedTheme);
                themeToggle.innerHTML = savedTheme === 'dark' ? 
                    '<i class="fas fa-sun"></i>' : 
                    '<i class="fas fa-moon"></i>';
            } else {
                // Use system preference
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (prefersDark) {
                    html.setAttribute('data-bs-theme', 'dark');
                    themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                }
            }
        }
    },
    
    /**
     * Setup endpoint suggestions
     */
    setupEndpointSuggestions: function() {
        // Fetch available endpoints
        fetch('/api/available-endpoints')
            .then(response => response.json())
            .then(endpoints => {
                this.populateEndpointSuggestions(endpoints);
            })
            .catch(error => {
                console.error('Error fetching endpoints:', error);
            });
            
        // Handle endpoint input
        const endpointInput = document.getElementById('endpoint-url');
        if (endpointInput) {
            endpointInput.addEventListener('input', this.handleEndpointInput.bind(this));
        }
    },
    
    /**
     * Populate endpoint suggestions
     */
    populateEndpointSuggestions: function(endpoints) {
        if (!endpoints || !Array.isArray(endpoints)) return;
        
        const suggestionsContainer = document.getElementById('endpoint-suggestions');
        if (!suggestionsContainer) return;
        
        // Clear existing suggestions
        suggestionsContainer.innerHTML = '';
        
        // Add new suggestions (limit to 8 for performance)
        const limitedEndpoints = endpoints.slice(0, 8);
        limitedEndpoints.forEach(endpoint => {
            const suggestion = document.createElement('span');
            suggestion.className = 'endpoint-suggestion';
            suggestion.textContent = endpoint.path;
            suggestion.dataset.methods = endpoint.methods.join(',');
            suggestion.title = `${endpoint.methods.join(', ')} - ${endpoint.description || ''}`;
            
            suggestion.addEventListener('click', () => {
                // Set the endpoint in the input
                const endpointInput = document.getElementById('endpoint-url');
                if (endpointInput) {
                    endpointInput.value = endpoint.path;
                }
                
                // Set appropriate method if available
                const methodSelect = document.getElementById('http-method');
                if (methodSelect && endpoint.methods && endpoint.methods.length > 0) {
                    // Try to set the first supported method
                    const method = endpoint.methods[0];
                    if (Array.from(methodSelect.options).some(opt => opt.value === method)) {
                        methodSelect.value = method;
                    }
                }
                
                // If schema is available, pre-fill the request body
                if (endpoint.schema && endpoint.schema.request) {
                    const bodyEditor = document.getElementById('request-body');
                    if (bodyEditor) {
                        bodyEditor.value = JSON.stringify(endpoint.schema.request, null, 2);
                    }
                }
            });
            
            suggestionsContainer.appendChild(suggestion);
        });
    },
    
    /**
     * Handle endpoint input for suggestions
     */
    handleEndpointInput: function(event) {
        const input = event.target.value.toLowerCase();
        const suggestions = document.querySelectorAll('.endpoint-suggestion');
        
        if (!input) {
            // Show all suggestions
            suggestions.forEach(suggestion => {
                suggestion.style.display = '';
            });
            return;
        }
        
        // Filter suggestions
        suggestions.forEach(suggestion => {
            const endpointPath = suggestion.textContent.toLowerCase();
            if (endpointPath.includes(input)) {
                suggestion.style.display = '';
            } else {
                suggestion.style.display = 'none';
            }
        });
    },
    
    /**
     * Setup browser notifications
     */
    setupNotifications: function() {
        // Request notifications permission if enabled
        const enableNotifications = document.getElementById('enable-notifications');
        if (enableNotifications && enableNotifications.checked) {
            this.requestNotificationsPermission();
        }
        
        // Listen for changes to the notifications checkbox
        if (enableNotifications) {
            enableNotifications.addEventListener('change', () => {
                if (enableNotifications.checked) {
                    this.requestNotificationsPermission();
                }
            });
        }
    },
    
    /**
     * Request permission for browser notifications
     */
    requestNotificationsPermission: function() {
        if (!('Notification' in window)) {
            console.warn('This browser does not support notifications');
            return;
        }
        
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    },
    
    /**
     * Show a notification in the browser
     */
    showNotification: function(title, options = {}) {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }
        
        const notification = new Notification(title, options);
        
        // Auto-close after 5 seconds
        setTimeout(() => {
            notification.close();
        }, 5000);
        
        return notification;
    },
    
    /**
     * Show a toast message
     */
    showToast: function(message, type = 'info', duration = 3000) {
        // Create the toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast show bg-${type} text-white`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">
                    <i class="fas fa-${type === 'info' ? 'info-circle' : 
                                       type === 'success' ? 'check-circle' : 
                                       type === 'warning' ? 'exclamation-triangle' : 
                                       'exclamation-circle'} me-2"></i>
                    ${type.charAt(0).toUpperCase() + type.slice(1)}
                </strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        // Add to container
        toastContainer.appendChild(toast);
        
        // Auto-remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, duration);
        
        // Close button
        const closeButton = toast.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                toast.classList.remove('show');
                setTimeout(() => {
                    toast.remove();
                }, 300);
            });
        }
    }
};

// Initialize console manager when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    consoleManager.init();
    
    // Setup additional global UI behaviors
    
    // Refresh button
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            location.reload();
        });
    }
    
    // Clear history button
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all request history?')) {
                fetch('/api/clear-history', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Clear history UI components
                        const recentList = document.getElementById('recent-requests-list');
                        if (recentList) {
                            recentList.innerHTML = `
                                <div class="text-center p-4 text-muted">
                                    <i class="fas fa-history fa-2x mb-2"></i>
                                    <p>No recent requests</p>
                                </div>
                            `;
                        }
                        
                        // Show success message
                        consoleManager.showToast('Request history cleared successfully', 'success');
                    }
                })
                .catch(error => {
                    console.error('Error clearing history:', error);
                    consoleManager.showToast('Failed to clear history', 'danger');
                });
            }
        });
    }
    
    // About button
    const aboutBtn = document.getElementById('about-btn');
    if (aboutBtn) {
        aboutBtn.addEventListener('click', () => {
            // Navigate to about tab in settings
            window.location.href = '/settings#about';
        });
    }
});

// Ensure code highlighting is applied to any code blocks
document.addEventListener('DOMContentLoaded', () => {
    if (typeof hljs !== 'undefined') {
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });
    }
});