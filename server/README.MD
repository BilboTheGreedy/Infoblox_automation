# Infoblox Mock Server

A comprehensive mock server that simulates the Infoblox WAPI (Web API) for development and testing purposes.

## Overview

The Infoblox Mock Server provides a lightweight, configurable implementation of the Infoblox WAPI, allowing developers to build and test applications that interact with Infoblox without requiring access to an actual Infoblox grid.

Key features:

- Simulates core Infoblox WAPI functionality
- Supports network, IPAM, and DNS record management
- Provides authentication and session management
- Configurable delay and failure simulation for testing edge cases
- Persistent storage option for maintaining state between runs
- Rate limiting and detailed logging
- Extensible architecture for adding new features

## Installation

### Prerequisites

- Python 3.6 or later
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/infoblox-mock-server.git
   cd infoblox-mock-server
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Starting the Server

Run the server with default settings:

```
python run_server.py
```

Run with custom options:

```
python run_server.py --host 127.0.0.1 --port 8080 --debug --config config.json
```

### Configuration Options

The server can be configured either by passing a configuration file or by updating the configuration through the API. Available configuration options:

- `simulate_delay`: Add random delay to responses (boolean)
- `min_delay_ms`: Minimum delay in milliseconds (integer)
- `max_delay_ms`: Maximum delay in milliseconds (integer)
- `simulate_failures`: Randomly simulate server failures (boolean)
- `failure_rate`: Failure rate if simulation enabled (float, 0-1)
- `detailed_logging`: Enable detailed request/response logging (boolean)
- `persistent_storage`: Enable file-based persistent storage (boolean)
- `storage_file`: File to use for persistent storage (string)
- `auth_required`: Require authentication (boolean)
- `rate_limit`: Enable rate limiting (boolean)
- `rate_limit_requests`: Number of requests allowed per minute (integer)
- `simulate_db_lock`: Simulate database locks (boolean)
- `lock_probability`: Lock probability per operation (float, 0-1)
- `wapi_version`: WAPI version to simulate (string)

### Example Client Usage

The `examples` directory contains sample scripts demonstrating how to interact with the mock server:

```python
from examples.basic_client import InfobloxClient

# Create client
client = InfobloxClient(base_url="http://localhost:8080/wapi/v2.11")

# Login
client.login()

# Get networks
networks = client.get_objects("network")
print(networks)

# Create a host record
host_data = {
    "name": "test.example.com",
    "ipv4addrs": [{"ipv4addr": "10.10.10.10"}]
}
host_ref = client.create_object("record:host", host_data)

# Logout
client.logout()
```

## Project Structure

```
infoblox_mock_server/
├── README.md
├── requirements.txt
├── run_server.py                # Main entry point
├── tests/                       # Test directory
│   ├── __init__.py
│   └── test_server.py           # Basic test cases
├── infoblox_mock/               # Main package directory
│   ├── __init__.py              # Package initialization
│   ├── server.py                # Main Flask application
│   ├── config.py                # Configuration management
│   ├── db.py                    # Database operations
│   ├── middleware.py            # Decorators and middleware
│   ├── validators.py            # Data validation functions
│   ├── utils.py                 # Utility functions
│   └── models/                  # Model definitions
│       ├── __init__.py
│       ├── base.py              # Base model functionality
│       ├── network.py           # Network-related models
│       ├── dns_records.py       # DNS record models
│       ├── dhcp.py              # DHCP-related models
│       ├── grid.py              # Grid and member models
│       └── security.py          # Authentication and security models
├── examples/                    # Example scripts
│   ├── basic_client.py          # Basic operations
│   ├── dns_client.py            # DNS record operations
│   └── dhcp_client.py           # DHCP operations
└── data/                        # Data directory (for persistent storage)
    └── .gitkeep
```

## Supported Features

### DNS Records
- A Records
- AAAA Records (IPv6)
- CNAME Records
- MX Records
- TXT Records
- SRV Records
- PTR Records
- NS Records
- SOA Records
- DNSSEC Records (DNSKEY, RRSIG, DS, NSEC, NSEC3)
- CAA Records

### Network Management
- Networks
- Network Containers
- Next available IP functionality
- IP address management

### DHCP
- DHCP Ranges
- Fixed Addresses
- Leases

### Grid and Members
- Grid information
- Member management
- Session handling (login/logout)

## Extending the Server

The modular architecture makes it easy to add new features:

1. Add new object types to the database structure in `db.py`
2. Implement validation for new object types in `validators.py`
3. Add any specific handling in the appropriate route in `routes.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Infoblox for their excellent WAPI documentation
- The Flask team for their lightweight web framework