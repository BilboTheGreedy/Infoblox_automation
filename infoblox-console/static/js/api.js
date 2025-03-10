/**
 * API interaction module for Infoblox API Console
 */

// Global API client state
const apiClient = {
    // Base URL of the mock server - updates from the UI
    baseUrl: '',
    
    // API key if authentication is required
    apiKey: '',
    
    // Default request headers
    defaultHeaders: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    
    // Saved API requests
    savedRequests: [],
    
    // Request history (limited to most recent)
    requestHistory: [],
    
    /**
     * Initialize the API client
     */
    init: function() {
        // Load base URL from page
        const serverUrl = document.getElementById('base-url');
        if (serverUrl) {
            this.baseUrl = serverUrl.textContent.trim();
        }
        
        // Load saved requests from localStorage
        this.loadSavedRequests();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('API client initialized:', this.baseUrl);
    },
    
    /**
     * Load saved requests from localStorage
     */
    loadSavedRequests: function() {
        try {
            const saved = localStorage.getItem('savedRequests');
            if (saved) {
                this.savedRequests = JSON.parse(saved);
                this.updateSavedRequestsDropdown();
            }
        } catch (error) {
            console.error('Error loading saved requests:', error);
        }
    },
    
    /**
     * Save requests to localStorage
     */
    saveRequests: function() {
        try {
            localStorage.setItem('savedRequests', JSON.stringify(this.savedRequests));
        } catch (error) {
            console.error('Error saving requests:', error);
        }
    },
    
    /**
     * Update the saved requests dropdown
     */
    updateSavedRequestsDropdown: function() {
        const dropdown = document.querySelector('.saved-requests-dropdown');
        if (!dropdown) return;
        
        // Clear existing items except header and divider
        const emptyItem = dropdown.querySelector('.saved-requests-empty');
        const items = dropdown.querySelectorAll('li:not(.dropdown-header):not(.saved-requests-empty)');
        items.forEach(item => item.remove());
        
        // Hide/show empty message
        if (this.savedRequests.length === 0) {
            if (emptyItem) emptyItem.classList.remove('d-none');
        } else {
            if (emptyItem) emptyItem.classList.add('d-none');
            
            // Add saved requests
            this.savedRequests.forEach((request, index) => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <a class="dropdown-item d-flex align-items-center" href="#" data-index="${index}">
                        <span class="badge rounded-pill bg-${this.getMethodColor(request.method)} me-2">${request.method}</span>
                        <span class="flex-grow-1 text-truncate">${request.name || request.endpoint}</span>
                        <button class="btn btn-sm text-danger delete-saved-request" data-index="${index}">
                            <i class="fas fa-times"></i>
                        </button>
                    </a>
                `;
                dropdown.appendChild(li);
                
                // Setup event listeners for this item
                const link = li.querySelector('a');
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.loadSavedRequest(index);
                });
                
                const deleteBtn = li.querySelector('.delete-saved-request');
                deleteBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.deleteSavedRequest(index);
                });
            });
        }
    },
    
    /**
     * Setup event listeners
     */
    setupEventListeners: function() {
        // API Request form
        const form = document.getElementById('api-request-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.executeRequest();
            });
        }
        
        // Save request button
        const saveBtn = document.getElementById('save-request-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveCurrentRequest();
            });
        }
        
        // Reset console button
        const resetBtn = document.getElementById('reset-console-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetConsole();
            });
        }
        
        // Format JSON button
        const formatBtn = document.querySelector('.format-json-btn');
        if (formatBtn) {
            formatBtn.addEventListener('click', () => {
                this.formatJsonEditor();
            });
        }
        
        // Clear editor button
        const clearBtn = document.querySelector('.clear-editor-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearEditor();
            });
        }
        
        // Add header button
        const addHeaderBtn = document.querySelector('.add-header-btn');
        if (addHeaderBtn) {
            addHeaderBtn.addEventListener('click', () => {
                this.addHeaderRow();
            });
        }
        
        // Remove header buttons (delegated)
        const headersTable = document.querySelector('.headers-table');
        if (headersTable) {
            headersTable.addEventListener('click', (e) => {
                if (e.target.closest('.remove-header-btn')) {
                    e.target.closest('tr').remove();
                }
            });
        }
        
        // Authentication type select
        const authTypeSelect = document.querySelector('.auth-type-select');
        if (authTypeSelect) {
            authTypeSelect.addEventListener('change', () => {
                this.updateAuthForm(authTypeSelect.value);
            });
        }
        
        // Content-type select
        const contentTypeSelect = document.querySelector('.content-type-select');
        if (contentTypeSelect) {
            contentTypeSelect.addEventListener('change', () => {
                const headerInputs = document.querySelectorAll('.header-name');
                headerInputs.forEach(input => {
                    if (input.value.toLowerCase() === 'content-type') {
                        input.nextElementSibling.value = contentTypeSelect.value;
                    }
                });
            });
        }
        
        // Copy response button
        const copyBtn = document.querySelector('.copy-response-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const responseBody = document.querySelector('.response-body');
                navigator.clipboard.writeText(responseBody.textContent)
                    .then(() => {
                        copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                        setTimeout(() => {
                            copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy';
                        }, 2000);
                    })
                    .catch(err => {
                        console.error('Failed to copy: ', err);
                    });
            });
        }
        
        // Expand response button
        const expandBtn = document.querySelector('.expand-response-btn');
        if (expandBtn) {
            expandBtn.addEventListener('click', () => {
                const container = document.querySelector('.response-body').parentElement;
                container.classList.toggle('expanded');
                if (container.classList.contains('expanded')) {
                    expandBtn.innerHTML = '<i class="fas fa-compress-alt"></i> Collapse';
                    container.style.maxHeight = 'none';
                } else {
                    expandBtn.innerHTML = '<i class="fas fa-expand-alt"></i> Expand';
                    container.style.maxHeight = '';
                }
            });
        }
    },
    
    /**
     * Execute the API request
     */
    executeRequest: function() {
        // Get form values
        const method = document.getElementById('http-method').value;
        const endpoint = document.getElementById('endpoint-url').value;
        const requestBody = document.getElementById('request-body').value;
        
        // Validate endpoint
        if (!endpoint) {
            this.showError('Please enter an endpoint URL');
            return;
        }
        
        // Get headers
        const headers = this.getRequestHeaders();
        
        // Show loading state
        const sendButton = document.getElementById('send-request-btn');
        const originalButtonText = sendButton.innerHTML;
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        
        // Create request object
        const requestData = {
            method: method,
            endpoint: endpoint,
            body: this.parseRequestBody(requestBody, headers['Content-Type']),
            headers: headers
        };
        
        // Add authentication if needed
        this.addAuthToRequest(requestData);
        
        // Start timer
        const startTime = performance.now();
        
        // Make the API call
        fetch('/api/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(response => {
            // Calculate response time
            const endTime = performance.now();
            const responseTime = Math.round(endTime - startTime);
            
            // Display the response
            this.displayResponse(response, responseTime);
            
            // Auto-save to history if configured
            if (document.getElementById('auto-save') && document.getElementById('auto-save').checked) {
                this.addToHistory(requestData, response, responseTime);
            }
        })
        .catch(error => {
            this.showError('Error executing request: ' + error.message);
            console.error('Request error:', error);
        })
        .finally(() => {
            // Restore button state
            sendButton.disabled = false;
            sendButton.innerHTML = originalButtonText;
        });
    },
    
    /**
     * Get request headers from the form
     */
    getRequestHeaders: function() {
        const headers = {};
        const headerRows = document.querySelectorAll('.headers-table tbody tr');
        
        headerRows.forEach(row => {
            const nameInput = row.querySelector('.header-name');
            const valueInput = row.querySelector('.header-value');
            
            if (nameInput && valueInput && nameInput.value.trim()) {
                headers[nameInput.value.trim()] = valueInput.value.trim();
            }
        });
        
        return headers;
    },
    
    /**
     * Parse request body based on content type
     */
    parseRequestBody: function(body, contentType) {
        if (!body || !body.trim()) {
            return null;
        }
        
        if (contentType && contentType.includes('application/json')) {
            try {
                return JSON.parse(body);
            } catch (error) {
                this.showError('Invalid JSON in request body');
                console.error('JSON parse error:', error);
                return body;
            }
        }
        
        return body;
    },
    
    /**
     * Add authentication to request
     */
    addAuthToRequest: function(requestData) {
        const authType = document.querySelector('.auth-type-select') ? 
            document.querySelector('.auth-type-select').value : 'none';
        
        if (authType === 'basic') {
            const username = document.querySelector('.auth-username').value;
            const password = document.querySelector('.auth-password').value;
            
            if (username && password) {
                const base64Auth = btoa(`${username}:${password}`);
                requestData.headers['Authorization'] = `Basic ${base64Auth}`;
            }
        } else if (authType === 'bearer') {
            const token = document.querySelector('.auth-token').value;
            
            if (token) {
                requestData.headers['Authorization'] = token.startsWith('Bearer ') ? 
                    token : `Bearer ${token}`;
            }
        } else if (authType === 'apikey') {
            const keyName = document.querySelector('.auth-apikey-name').value;
            const keyValue = document.querySelector('.auth-apikey-value').value;
            const keyLocation = document.querySelector('.auth-apikey-location').value;
            
            if (keyName && keyValue) {
                if (keyLocation === 'header') {
                    requestData.headers[keyName] = keyValue;
                } else if (keyLocation === 'query') {
                    // Add to query parameters in the endpoint
                    const separator = requestData.endpoint.includes('?') ? '&' : '?';
                    requestData.endpoint += `${separator}${keyName}=${encodeURIComponent(keyValue)}`;
                }
            }
        }
    },
    
    /**
     * Display the API response
     */
    displayResponse: function(response, responseTime) {
        const responseCard = document.querySelector('.response-card');
        if (!responseCard) return;
        
        // Show the response card
        responseCard.classList.remove('d-none');
        
        // Set response time
        const responseTimeElement = document.querySelector('.response-time');
        if (responseTimeElement) {
            responseTimeElement.textContent = `${responseTime} ms`;
        }
        
        // Set status code
        const statusElement = document.querySelector('.response-status');
        if (statusElement) {
            const statusCode = response.status_code || 200;
            const statusText = this.getStatusText(statusCode);
            statusElement.textContent = `${statusCode} ${statusText}`;
            
            // Set badge color
            statusElement.className = 'response-status badge';
            if (statusCode >= 200 && statusCode < 300) {
                statusElement.classList.add('bg-success');
            } else if (statusCode >= 300 && statusCode < 400) {
                statusElement.classList.add('bg-info');
            } else if (statusCode >= 400 && statusCode < 500) {
                statusElement.classList.add('bg-warning');
            } else {
                statusElement.classList.add('bg-danger');
            }
        }
        
        // Format and set response body
        const responseBody = document.querySelector('.response-body');
        if (responseBody) {
            let formattedResponse = '';
            
            try {
                // If it's an object, pretty print it
                if (typeof response === 'object') {
                    formattedResponse = JSON.stringify(response, null, 2);
                } else {
                    formattedResponse = response.toString();
                }
            } catch (error) {
                formattedResponse = 'Error formatting response: ' + error.message;
            }
            
            responseBody.textContent = formattedResponse;
            
            // Highlight syntax
            if (hljs) {
                hljs.highlightBlock(responseBody);
            }
        }
        
        // Set response headers
        const headersTable = document.querySelector('.response-headers-table tbody');
        if (headersTable) {
            headersTable.innerHTML = '';
            
            if (response.headers) {
                Object.entries(response.headers).forEach(([name, value]) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${name}</td>
                        <td>${value}</td>
                    `;
                    headersTable.appendChild(row);
                });
            }
        }
    },
    
    /**
     * Get HTTP status text from code
     */
    getStatusText: function(code) {
        const statusTexts = {
            200: 'OK',
            201: 'Created',
            202: 'Accepted',
            204: 'No Content',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            405: 'Method Not Allowed',
            409: 'Conflict',
            422: 'Unprocessable Entity',
            500: 'Internal Server Error',
            502: 'Bad Gateway',
            503: 'Service Unavailable'
        };
        
        return statusTexts[code] || 'Unknown';
    },
    
    /**
     * Save the current request
     */
    saveCurrentRequest: function() {
        const method = document.getElementById('http-method').value;
        const endpoint = document.getElementById('endpoint-url').value;
        const body = document.getElementById('request-body').value;
        const headers = this.getRequestHeaders();
        
        if (!endpoint) {
            this.showError('Please enter an endpoint URL before saving');
            return;
        }
        
        // Prompt for a name
        const name = prompt('Enter a name for this request:', endpoint);
        if (!name) return;
        
        // Create request object
        const request = {
            name: name,
            method: method,
            endpoint: endpoint,
            body: body,
            headers: headers,
            createdAt: new Date().toISOString()
        };
        
        // Add authentication info if present
        const authType = document.querySelector('.auth-type-select') ? 
            document.querySelector('.auth-type-select').value : 'none';
        
        if (authType !== 'none') {
            request.auth = {
                type: authType
            };
            
            if (authType === 'basic') {
                request.auth.username = document.querySelector('.auth-username').value;
                request.auth.password = document.querySelector('.auth-password').value;
            } else if (authType === 'bearer') {
                request.auth.token = document.querySelector('.auth-token').value;
            } else if (authType === 'apikey') {
                request.auth.keyName = document.querySelector('.auth-apikey-name').value;
                request.auth.keyValue = document.querySelector('.auth-apikey-value').value;
                request.auth.keyLocation = document.querySelector('.auth-apikey-location').value;
            }
        }
        
        // Save to the list
        this.savedRequests.unshift(request);
        this.saveRequests();
        this.updateSavedRequestsDropdown();
        
        // Show confirmation
        this.showSuccess('Request saved successfully');
    },
    
    /**
     * Load a saved request
     */
    loadSavedRequest: function(index) {
        const request = this.savedRequests[index];
        if (!request) return;
        
        // Set form values
        document.getElementById('http-method').value = request.method;
        document.getElementById('endpoint-url').value = request.endpoint;
        document.getElementById('request-body').value = request.body || '';
        
        // Set headers
        const headerRows = document.querySelectorAll('.headers-table tbody tr');
        headerRows.forEach(row => row.remove());
        
        if (request.headers) {
            Object.entries(request.headers).forEach(([name, value]) => {
                this.addHeaderRow(name, value);
            });
        }
        
        // Set authentication if present
        if (request.auth) {
            const authTypeSelect = document.querySelector('.auth-type-select');
            if (authTypeSelect) {
                authTypeSelect.value = request.auth.type;
                this.updateAuthForm(request.auth.type);
                
                if (request.auth.type === 'basic') {
                    document.querySelector('.auth-username').value = request.auth.username || '';
                    document.querySelector('.auth-password').value = request.auth.password || '';
                } else if (request.auth.type === 'bearer') {
                    document.querySelector('.auth-token').value = request.auth.token || '';
                } else if (request.auth.type === 'apikey') {
                    document.querySelector('.auth-apikey-name').value = request.auth.keyName || '';
                    document.querySelector('.auth-apikey-value').value = request.auth.keyValue || '';
                    document.querySelector('.auth-apikey-location').value = request.auth.keyLocation || 'header';
                }
            }
        }
        
        // Format any JSON in the body
        this.formatJsonEditor();
        
        // Show confirmation
        this.showSuccess(`Loaded request: ${request.name}`);
    },
    
    /**
     * Delete a saved request
     */
    deleteSavedRequest: function(index) {
        if (confirm('Are you sure you want to delete this saved request?')) {
            this.savedRequests.splice(index, 1);
            this.saveRequests();
            this.updateSavedRequestsDropdown();
            this.showSuccess('Request deleted');
        }
    },
    
    /**
     * Reset the console
     */
    resetConsole: function() {
        document.getElementById('endpoint-url').value = '';
        document.getElementById('request-body').value = '';
        
        // Reset headers
        const headerRows = document.querySelectorAll('.headers-table tbody tr');
        headerRows.forEach(row => row.remove());
        this.addHeaderRow('Content-Type', 'application/json');
        
        // Reset auth
        const authTypeSelect = document.querySelector('.auth-type-select');
        if (authTypeSelect) {
            authTypeSelect.value = 'none';
            this.updateAuthForm('none');
        }
        
        // Hide response
        const responseCard = document.querySelector('.response-card');
        if (responseCard) {
            responseCard.classList.add('d-none');
        }
    },
    
    /**
     * Format JSON in the editor
     */
    formatJsonEditor: function() {
        const editor = document.getElementById('request-body');
        if (!editor || !editor.value.trim()) return;
        
        try {
            const json = JSON.parse(editor.value);
            editor.value = JSON.stringify(json, null, 2);
        } catch (error) {
            // Not valid JSON, ignore
            console.warn('Not valid JSON, skipping formatting');
        }
    },
    
    /**
     * Clear the editor
     */
    clearEditor: function() {
        const editor = document.getElementById('request-body');
        if (editor) {
            editor.value = '';
        }
    },
    
    /**
     * Add a header row to the headers table
     */
    addHeaderRow: function(name = '', value = '') {
        const tbody = document.querySelector('.headers-table tbody');
        if (!tbody) return;
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="text" class="form-control form-control-sm header-name" placeholder="Header Name" value="${name}">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm header-value" placeholder="Header Value" value="${value}">
            </td>
            <td>
                <button type="button" class="btn btn-sm btn-outline-danger remove-header-btn">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    },
    
    /**
     * Update the authentication form based on selected type
     */
    updateAuthForm: function(authType) {
        const authForms = document.querySelectorAll('.auth-form');
        authForms.forEach(form => form.classList.add('d-none'));
        
        if (authType !== 'none') {
            const selectedForm = document.querySelector(`.auth-form-${authType}`);
            if (selectedForm) {
                selectedForm.classList.remove('d-none');
            }
        }
    },
    
    /**
     * Add request to history
     */
    addToHistory: function(request, response, responseTime) {
        // Create history item
        const historyItem = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            method: request.method,
            endpoint: request.endpoint,
            request: request,
            response: response,
            status: response.status_code || 200,
            responseTime: responseTime
        };
        
        // Add to local history
        this.requestHistory.unshift(historyItem);
        
        // Limit history size
        const maxItems = 100;
        if (this.requestHistory.length > maxItems) {
            this.requestHistory = this.requestHistory.slice(0, maxItems);
        }
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
     * Show an error message
     */
    showError: function(message) {
        const alert = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        const contentContainer = document.querySelector('.content-container');
        if (contentContainer) {
            contentContainer.insertAdjacentHTML('afterbegin', alert);
        }
    },
    
    /**
     * Show a success message
     */
    showSuccess: function(message) {
        const alert = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        const contentContainer = document.querySelector('.content-container');
        if (contentContainer) {
            contentContainer.insertAdjacentHTML('afterbegin', alert);
        }
    }
};

// Initialize when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    apiClient.init();
});