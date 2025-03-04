"""
Route definitions for the web UI.
This file only handles UI routes, API routes are in api.py
"""

import os
import logging
from flask import render_template, send_from_directory

logger = logging.getLogger(__name__)

def setup_ui_routes(app):
    """
    Setup UI routes for the web interface
    """
    # Create template directories if needed
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Generate template files if they don't exist
    create_template_files()
    create_static_files()
    
    # UI Routes
    @app.route('/')
    def index():
        """Main page"""
        return render_template('index.html')
    
    logger.info("UI routes initialized")
    return app

def create_template_files():
    """Create all the template files for the web UI"""
    # Only create files if they don't exist
    if not os.path.exists('templates/base.html'):
        create_base_template()
    
    if not os.path.exists('templates/index.html'):
        create_index_template()

def create_static_files():
    """Create all static files for the web UI"""
    # Only create files if they don't exist
    if not os.path.exists('static/css/styles.css'):
        create_css_file()
    
    if not os.path.exists('static/js/app.js'):
        create_js_file()
    
    logger.info("Static files checked/created")

def create_base_template():
    """Create the base HTML template"""
    with open('templates/base.html', 'w') as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Infoblox Mock Server{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.2/font/bootstrap-icons.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
""")

def create_index_template():
    """Create the index HTML template"""
    with open('templates/index.html', 'w') as f:
        f.write("""{% extends 'base.html' %}

{% block content %}
<div id="app">
    <!-- Loading indicator -->
    <div id="loader" v-if="loading" class="position-fixed top-0 start-0 end-0 bottom-0 d-flex justify-content-center align-items-center bg-white bg-opacity-75">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>

    <!-- Login Form -->
    <div id="login-container" class="container mt-5" v-if="!isLoggedIn">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h3 class="my-2">Infoblox Mock Server</h3>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-danger" v-if="errorMessage" v-html="errorMessage"></div>
                        <div class="mb-3">
                            <label for="username" class="form-label">Username</label>
                            <input type="text" class="form-control" id="username" v-model="username">
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label">Password</label>
                            <input type="password" class="form-control" id="password" v-model="password">
                        </div>
                        <button class="btn btn-primary w-100" @click="login" :disabled="loading">
                            <span class="spinner-border spinner-border-sm me-2" v-if="loading"></span>
                            Login
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Application -->
    <div id="main-container" v-if="isLoggedIn">
        <!-- Navigation code and tabs would go here -->
        <p>Main application content will be loaded here</p>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://unpkg.com/vue@next"></script>
{% endblock %}""")

def create_css_file():
    """Create the CSS file"""
    with open('static/css/styles.css', 'w') as f:
        f.write("""/* Infoblox Mock Server - Web UI Styles */
/* Basic styles for the web interface */
body {
    background-color: #f8f9fa;
}

/* Loading indicator */
#loader {
    z-index: 9999;
}

/* Card styles */
.card {
    margin-bottom: 1rem;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.card-header {
    background-color: #f8f9fa;
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
}

/* Table styles */
.table th {
    background-color: #f8f9fa;
}

.table-hover tbody tr:hover {
    background-color: rgba(0, 123, 255, 0.05);
}

/* Form styles */
label {
    font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .card-title {
        font-size: 1.25rem;
    }
    
    .btn {
        padding: 0.375rem 0.5rem;
    }
}
""")

def create_js_file():
    """Create the JavaScript file"""
    with open('static/js/app.js', 'w') as f:
        f.write("""/**
 * Infoblox Mock Server - Web UI JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the Vue application
    const app = Vue.createApp({
        data() {
            return {
                // Authentication
                isLoggedIn: false,
                username: 'admin',
                password: 'infoblox',
                
                // UI state
                loading: false,
                activeTab: 'networks',
                errorMessage: '',
                successMessage: '',
                
                // Data objects would be initialized here
            };
        },
        methods: {
            // Authentication
            async login() {
                this.loading = true;
                this.errorMessage = '';
                
                try {
                    // Call the Infoblox API to authenticate
                    const response = await fetch('/wapi/v2.11/grid/session', {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Basic ' + btoa(this.username + ':' + this.password)
                        }
                    });
                    
                    if (response.ok) {
                        this.isLoggedIn = true;
                        // We would fetch initial data here
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.Error || 'Authentication failed';
                    }
                } catch (error) {
                    this.errorMessage = 'Connection error: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // Other methods would be implemented here
        }
    });
    
    // Mount the Vue app
    app.mount('#app');
});
""")