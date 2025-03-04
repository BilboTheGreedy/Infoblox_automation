/**
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
                
                // Data
                networks: [],
                hosts: [],
                records: [],
                fixedAddresses: [],
                config: {},
                grid: {},
                selectedNetwork: '',
                nextAvailableIp: '',
                
                // Form data
                newNetwork: {
                    network: '',
                    comment: ''
                },
                newHost: {
                    name: '',
                    ipv4addr: '',
                    comment: ''
                },
                newRecord: {
                    name: '',
                    ipv4addr: '',
                    comment: ''
                },
                newFixed: {
                    ipv4addr: '',
                    mac: '',
                    name: '',
                    comment: ''
                }
            };
        },
        mounted() {
            // Initialize Bootstrap tooltips
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
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
                        this.fetchInitialData();
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
            
            async logout() {
                this.loading = true;
                
                try {
                    await fetch('/wapi/v2.11/grid/session', {
                        method: 'DELETE'
                    });
                    
                    this.isLoggedIn = false;
                } catch (error) {
                    this.errorMessage = 'Logout failed: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // UI Navigation
            setActiveTab(tab) {
                this.activeTab = tab;
                
                // Load data for the new tab if needed
                switch (tab) {
                    case 'networks':
                        this.fetchNetworks();
                        break;
                    case 'hosts':
                        this.fetchHosts();
                        break;
                    case 'records':
                        this.fetchRecords();
                        break;
                    case 'fixed':
                        this.fetchFixed();
                        break;
                    case 'config':
                        this.fetchConfig();
                        break;
                    case 'tools':
                        // Load multiple resources for tools tab
                        this.fetchNetworks();
                        this.fetchGridInfo();
                        break;
                }
            },
            
            // Clipboard helper
            copyToClipboard(text) {
                navigator.clipboard.writeText(text).then(() => {
                    this.showToast('Copied to clipboard');
                }).catch(err => {
                    console.error('Failed to copy text: ', err);
                });
            },
            
            // Toast helper
            showToast(message) {
                const toastEl = this.$refs.ipToast;
                if (toastEl) {
                    const toast = new bootstrap.Toast(toastEl);
                    toast.show();
                }
            },
            
            // Initial data loading
            async fetchInitialData() {
                this.fetchNetworks();
                this.fetchConfig();
                this.fetchGridInfo();
            },
            
            // API Methods - Networks
            async fetchNetworks() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/networks');
                    if (response.ok) {
                        this.networks = await response.json();
                        
                        // Set default selected network if none selected
                        if (!this.selectedNetwork && this.networks.length > 0) {
                            this.selectedNetwork = this.networks[0].network;
                        }
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to fetch networks';
                    }
                } catch (error) {
                    this.errorMessage = 'Error fetching networks: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async createNetwork() {
                if (!this.newNetwork.network) {
                    this.errorMessage = 'Network CIDR is required';
                    return;
                }
                
                this.loading = true;
                this.errorMessage = '';
                
                try {
                    const response = await fetch('/api/networks', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(this.newNetwork)
                    });
                    
                    if (response.ok) {
                        // Reset form
                        this.newNetwork = { network: '', comment: '' };
                        
                        // Refresh networks
                        await this.fetchNetworks();
                        
                        this.successMessage = 'Network created successfully';
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to create network';
                    }
                } catch (error) {
                    this.errorMessage = 'Error creating network: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async deleteNetwork(network) {
                if (!confirm(`Are you sure you want to delete network ${network.network}?`)) {
                    return;
                }
                
                this.loading = true;
                
                try {
                    const response = await fetch(`/api/networks/${encodeURIComponent(network._ref)}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        // Refresh networks
                        await this.fetchNetworks();
                        
                        this.successMessage = `Network ${network.network} deleted`;
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to delete network';
                    }
                } catch (error) {
                    this.errorMessage = 'Error deleting network: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // API Methods - Host Records
            async fetchHosts() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/hosts');
                    if (response.ok) {
                        this.hosts = await response.json();
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to fetch host records';
                    }
                } catch (error) {
                    this.errorMessage = 'Error fetching host records: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async createHost() {
                if (!this.newHost.name) {
                    this.errorMessage = 'Hostname is required';
                    return;
                }
                
                if (!this.newHost.ipv4addr) {
                    this.errorMessage = 'IP address is required';
                    return;
                }
                
                this.loading = true;
                this.errorMessage = '';
                
                try {
                    const response = await fetch('/api/hosts', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(this.newHost)
                    });
                    
                    if (response.ok) {
                        // Reset form
                        this.newHost = { name: '', ipv4addr: '', comment: '' };
                        
                        // Refresh hosts
                        await this.fetchHosts();
                        
                        this.successMessage = 'Host record created successfully';
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to create host record';
                    }
                } catch (error) {
                    this.errorMessage = 'Error creating host record: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async deleteHost(host) {
                if (!confirm(`Are you sure you want to delete host record ${host.name}?`)) {
                    return;
                }
                
                this.loading = true;
                
                try {
                    const response = await fetch(`/api/hosts/${encodeURIComponent(host._ref)}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        // Refresh hosts
                        await this.fetchHosts();
                        
                        this.successMessage = `Host record ${host.name} deleted`;
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to delete host record';
                    }
                } catch (error) {
                    this.errorMessage = 'Error deleting host record: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // API Methods - A Records
            async fetchRecords() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/records');
                    if (response.ok) {
                        this.records = await response.json();
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to fetch A records';
                    }
                } catch (error) {
                    this.errorMessage = 'Error fetching A records: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async createRecord() {
                if (!this.newRecord.name) {
                    this.errorMessage = 'Name is required';
                    return;
                }
                
                if (!this.newRecord.ipv4addr) {
                    this.errorMessage = 'IP address is required';
                    return;
                }
                
                this.loading = true;
                this.errorMessage = '';
                
                try {
                    const response = await fetch('/api/records', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(this.newRecord)
                    });
                    
                    if (response.ok) {
                        // Reset form
                        this.newRecord = { name: '', ipv4addr: '', comment: '' };
                        
                        // Refresh records
                        await this.fetchRecords();
                        
                        this.successMessage = 'A record created successfully';
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to create A record';
                    }
                } catch (error) {
                    this.errorMessage = 'Error creating A record: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async deleteRecord(record) {
                if (!confirm(`Are you sure you want to delete A record ${record.name}?`)) {
                    return;
                }
                
                this.loading = true;
                
                try {
                    const response = await fetch(`/api/records/${encodeURIComponent(record._ref)}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        // Refresh records
                        await this.fetchRecords();
                        
                        this.successMessage = `A record ${record.name} deleted`;
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to delete A record';
                    }
                } catch (error) {
                    this.errorMessage = 'Error deleting A record: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // API Methods - Fixed Addresses
            async fetchFixed() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/fixedaddresses');
                    if (response.ok) {
                        this.fixedAddresses = await response.json();
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to fetch fixed addresses';
                    }
                } catch (error) {
                    this.errorMessage = 'Error fetching fixed addresses: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async createFixed() {
                if (!this.newFixed.ipv4addr) {
                    this.errorMessage = 'IP address is required';
                    return;
                }
                
                if (!this.newFixed.mac) {
                    this.errorMessage = 'MAC address is required';
                    return;
                }
                
                this.loading = true;
                this.errorMessage = '';
                
                try {
                    const response = await fetch('/api/fixedaddresses', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(this.newFixed)
                    });
                    
                    if (response.ok) {
                        // Reset form
                        this.newFixed = { ipv4addr: '', mac: '', name: '', comment: '' };
                        
                        // Refresh fixed addresses
                        await this.fetchFixed();
                        
                        this.successMessage = 'Fixed address created successfully';
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to create fixed address';
                    }
                } catch (error) {
                    this.errorMessage = 'Error creating fixed address: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async deleteFixed(fixed) {
                if (!confirm(`Are you sure you want to delete fixed address ${fixed.ipv4addr}?`)) {
                    return;
                }
                
                this.loading = true;
                
                try {
                    const response = await fetch(`/api/fixedaddresses/${encodeURIComponent(fixed._ref)}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        // Refresh fixed addresses
                        await this.fetchFixed();
                        
                        this.successMessage = `Fixed address ${fixed.ipv4addr} deleted`;
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to delete fixed address';
                    }
                } catch (error) {
                    this.errorMessage = 'Error deleting fixed address: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // API Methods - Next Available IP
            async getNextAvailableIp(network) {
                if (!network) {
                    this.errorMessage = 'Please select a network';
                    return;
                }
                
                this.loading = true;
                
                try {
                    const response = await fetch(`/api/nextavailableip/${encodeURIComponent(network)}`);
                    
                    if (response.ok) {
                        const data = await response.json();
                        this.nextAvailableIp = data.ipv4addr;
                        // Show toast with the IP
                        this.showToast();
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to get next available IP';
                    }
                } catch (error) {
                    this.errorMessage = 'Error getting next available IP: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            useNextIp(type) {
                // First try to get an IP for the selected network
                if (this.selectedNetwork) {
                    this.getNextAvailableIp(this.selectedNetwork).then(() => {
                        if (this.nextAvailableIp) {
                            this.applyNextIp(type);
                        }
                    });
                } else if (this.networks.length > 0) {
                    // If no network selected, use the first one
                    this.selectedNetwork = this.networks[0].network;
                    this.getNextAvailableIp(this.selectedNetwork).then(() => {
                        if (this.nextAvailableIp) {
                            this.applyNextIp(type);
                        }
                    });
                } else {
                    this.errorMessage = 'No networks available';
                }
            },
            
            applyNextIp(type) {
                if (!this.nextAvailableIp) return;
                
                switch (type) {
                    case 'host':
                        this.newHost.ipv4addr = this.nextAvailableIp;
                        break;
                    case 'record':
                        this.newRecord.ipv4addr = this.nextAvailableIp;
                        break;
                    case 'fixed':
                        this.newFixed.ipv4addr = this.nextAvailableIp;
                        break;
                }
            },
            
            // API Methods - Server Configuration
            async fetchConfig() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/config');
                    if (response.ok) {
                        this.config = await response.json();
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to fetch configuration';
                    }
                } catch (error) {
                    this.errorMessage = 'Error fetching configuration: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async saveConfig() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/config', {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(this.config)
                    });
                    
                    if (response.ok) {
                        this.successMessage = 'Configuration saved successfully';
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to save configuration';
                    }
                } catch (error) {
                    this.errorMessage = 'Error saving configuration: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // API Methods - Grid Info
            async fetchGridInfo() {
                this.loading = true;
                
                try {
                    const response = await fetch('/wapi/v2.11/grid/1');
                    if (response.ok) {
                        this.grid = await response.json();
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to fetch grid information';
                    }
                } catch (error) {
                    this.errorMessage = 'Error fetching grid information: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            // API Methods - Database Management
            confirmReset() {
                if (confirm('Are you sure you want to reset the database? This will delete all data and restore defaults.')) {
                    this.resetDatabase();
                }
            },
            
            async resetDatabase() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/reset', {
                        method: 'POST'
                    });
                    
                    if (response.ok) {
                        // Refresh all data
                        await this.fetchInitialData();
                        
                        this.successMessage = 'Database reset successfully';
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to reset database';
                    }
                } catch (error) {
                    this.errorMessage = 'Error resetting database: ' + error.message;
                } finally {
                    this.loading = false;
                }
            },
            
            async exportDatabase() {
                this.loading = true;
                
                try {
                    const response = await fetch('/api/export');
                    
                    if (response.ok) {
                        const data = await response.json();
                        
                        // Create download link
                        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'infoblox_mock_db.json';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        
                        this.successMessage = 'Database exported successfully';
                    } else {
                        const data = await response.json();
                        this.errorMessage = data.error || 'Failed to export database';
                    }
                } catch (error) {
                    this.errorMessage = 'Error exporting database: ' + error.message;
                } finally {
                    this.loading = false;
                }
            }
        }
    });
    
    // Mount the Vue app
    app.mount('#app');
});