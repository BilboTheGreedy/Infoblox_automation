# Infoblox Ansible Automation

This repository contains Ansible playbooks for managing Infoblox IPAM and DNS resources. It uses the official Infoblox NIOS collection to interact with the Infoblox Grid.

## Prerequisites

- Ansible 2.9 or newer
- Python 3.6 or newer
- Network access to Infoblox Grid

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/bilbothegreedy/infoblox_automation.git
   cd infoblox_automation
   ```

2. Install the required collections:
   ```
   ansible-galaxy collection install -r requirements.yml
   ```

## Configuration

Set your Infoblox credentials using environment variables:

```bash
export INFOBLOX_HOST="127.0.0.1:5000"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="infoblox"
export INFOBLOX_WAPI_VERSION="2.11"  # Optional
```

Alternatively, configure the provider in `group_vars/all.yml` or pass the credentials as command-line arguments.

## Usage

### Main Entry Point

Use the main playbook as a unified entry point for all operations:

```bash
# Search for a network
ansible-playbook playbooks/main.yml -e "resource=network action=search network=192.168.1.0/24"

# Create a network
ansible-playbook playbooks/main.yml -e "resource=network action=create network=192.168.2.0/24 comment='Development Network'"

# Find next available IP in a network
ansible-playbook playbooks/main.yml -e "resource=ip_address action=next_available network=192.168.1.0/24"

# Reserve an IP address
ansible-playbook playbooks/main.yml -e "resource=ip_address action=reserve ip_address=192.168.1.50 mac_address=00:11:22:33:44:55 hostname=printer.example.com"

# Create a DNS record
ansible-playbook playbooks/main.yml -e "resource=dns_record action=create record_type=a hostname=www.example.com ip_address=192.168.1.10"
```

### Direct Playbook Execution

You can also run each playbook directly:

#### Network Management

```bash
# Search all networks
ansible-playbook playbooks/manage_networks.yml -e "action=search"

# Search for a specific network
ansible-playbook playbooks/manage_networks.yml -e "action=search network=192.168.1.0/24"

# Create a network
ansible-playbook playbooks/manage_networks.yml -e "action=create network=192.168.2.0/24 comment='Development Network'"

# Update a network
ansible-playbook playbooks/manage_networks.yml -e "action=update network=192.168.2.0/24 comment='Updated Development Network'"

# Delete a network
ansible-playbook playbooks/manage_networks.yml -e "action=delete network=192.168.2.0/24"
```

#### IP Address Management

```bash
# Search for an IP address
ansible-playbook playbooks/manage_ip_addresses.yml -e "action=search ip_address=192.168.1.10"

# Get next available IP in a network
ansible-playbook playbooks/manage_ip_addresses.yml -e "action=next_available network=192.168.1.0/24"

# Reserve an IP address
ansible-playbook playbooks/manage_ip_addresses.yml -e "action=reserve ip_address=192.168.1.50 mac_address=00:11:22:33:44:55"

# Reserve an IP address with hostname and DNS record
ansible-playbook playbooks/manage_ip_addresses.yml -e "action=reserve ip_address=192.168.1.50 mac_address=00:11:22:33:44:55 hostname=printer.example.com create_dns=true"
```

#### DNS Record Management

```bash
# Search for A records
ansible-playbook playbooks/manage_dns_records.yml -e "action=search record_type=a"

# Search for specific hostname record
ansible-playbook playbooks/manage_dns_records.yml -e "action=search record_type=a hostname=www.example.com"

# Create an A record
ansible-playbook playbooks/manage_dns_records.yml -e "action=create record_type=a hostname=www.example.com ip_address=192.168.1.10"

# Create a Host record
ansible-playbook playbooks/manage_dns_records.yml -e "action=create record_type=host hostname=server.example.com ip_address=192.168.1.20"

# Update a DNS record
ansible-playbook playbooks/manage_dns_records.yml -e "action=update record_type=a hostname=www.example.com ip_address=192.168.1.11"

# Delete a DNS record
ansible-playbook playbooks/manage_dns_records.yml -e "action=delete record_type=a hostname=www.example.com"
```

## Logging

All operations are logged to a file specified by the `log_file` variable (default: `infoblox_operations.log`). You can change the log file path:

```bash
ansible-playbook playbooks/main.yml -e "log_file=/path/to/custom.log resource=network action=search"
```

Enable verbose logging with:

```bash
ansible-playbook playbooks/main.yml -e "verbose_logging=true resource=network action=search"
```

## Forcing Operations

For operations that require confirmation or might overwrite existing data, you can use the `force` parameter:

```bash
ansible-playbook playbooks/manage_dns_records.yml -e "action=create record_type=a hostname=www.example.com ip_address=192.168.1.10 force=true"
```

## License

MIT

## Author

Daniel Rapp
