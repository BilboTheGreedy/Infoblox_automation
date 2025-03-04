/**
 * Infoblox Mock Server - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap components
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // MAC address formatting
    const macInput = document.getElementById('mac');
    if (macInput) {
        macInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^0-9a-fA-F]/g, '');
            
            if (value.length > 12) {
                value = value.slice(0, 12);
            }
            
            // Format with colons (XX:XX:XX:XX:XX:XX)
            if (value.length > 0) {
                value = value.match(/.{1,2}/g).join(':');
            }
            
            e.target.value = value;
        });
    }
    
    // CIDR validation
    const networkInput = document.getElementById('network');
    if (networkInput) {
        networkInput.addEventListener('blur', function(e) {
            const value = e.target.value.trim();
            
            // Simple CIDR validation (IP/prefix)
            if (value && !value.match(/^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/)) {
                alert('Please enter a valid CIDR notation (e.g., 192.168.1.0/24)');
            }
        });
    }
    
    // IP address validation
    const ipInputs = document.querySelectorAll('input[id$="ipv4addr"]');
    ipInputs.forEach(function(input) {
        input.addEventListener('blur', function(e) {
            const value = e.target.value.trim();
            
            // Simple IP validation
            if (value && !value.match(/^(\d{1,3}\.){3}\d{1,3}$/)) {
                alert('Please enter a valid IP address (e.g., 192.168.1.10)');
            }
        });
    });
});

/**
 * Copy text to clipboard
 * @param {string} text - The text to copy
 */
function copyToClipboard(text) {
    // Create a temporary input
    const input = document.createElement('input');
    input.setAttribute('value', text);
    document.body.appendChild(input);
    
    // Select and copy the text
    input.select();
    document.execCommand('copy');
    
    // Remove the temporary input
    document.body.removeChild(input);
    
    // Show a temporary notification
    const button = event.currentTarget;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-check2"></i> Copied!';
    
    setTimeout(() => {
        button.innerHTML = originalText;
    }, 2000);
}