# Infoblox Mock Server

This is an enhanced mock server that simulates the Infoblox WAPI (Web API) for testing and development purposes. It implements the core functionality of Infoblox NIOS, allowing you to develop and test automation scripts without requiring an actual Infoblox Grid.

## Features

- Simulates Infoblox WAPI v2.11
- Supports core object types (networks, DNS records, fixed addresses, etc.)
- Includes realistic validation and error handling
- Optional database persistence
- Configurable delay and failure simulation
- Rate limiting and authentication
- Detailed logging
- Thread safety for concurrent requests
- Simulated database operations with locking
- Realistic next-available-IP logic

## Installation

### Prerequisites

- Python 3.6+
- Flask

### Setup

1. Install dependencies:
   ```
   pip install flask ipaddress
   ```

2. Run the server:
   ```
   python infoblox_mock_server.py
   ```

### Command Line Options

- `--port` - Port to run the server on (default: 8080)
- `--host` - Host to bind the server to (default: 0.0.0.0)
- `--debug` - Run in debug mode
- `--persistence` - Enable database persistence
- `--storage-file` - Path to database storage file
- `--delay` - Simulate network delay
- `--failures` - Simulate random failures

Example:
```
python infoblox_mock_server.py --port 5000 --persistence --storage-file db.json --delay
```

## Using the Mock Server

The mock server exposes the same API endpoints as a real Infoblox WAPI, making it a drop-in replacement for testing. Simply point your scripts to the mock server URL.

### Authentication

Like a real Infoblox system, the mock server requires authentication:

```
curl -u admin:infoblox -X POST http://localhost:8080/wapi/v2.11/grid/session
```

### Basic Operations

Here are some examples of how to use the API:

#### Search for networks
```
curl -u admin:infoblox "http://localhost:8080/wapi/v2.11/network"
```

#### Create a network
```
curl -u admin:infoblox -X POST -H "Content-Type: application/json" -d '{"network": "192.168.1.0/24", "comment": "Test network"}' "http://localhost:8080/wapi/v2.11/network"
```

#### Get next available IP
```
curl -u admin:infoblox -X POST "http://localhost:8080/wapi/v2.11/network/192.168.1.0%2F24/next_available_ip"
```

#### Create a DNS record
```
curl -u admin:infoblox -X POST -H "Content-Type: application/json" -d '{"name": "test.example.com", "ipv4addr": "192.168.1.10"}' "http://localhost:8080/wapi/v2.11/record:a"
```

## Configuration Options

You can modify the behavior of the mock server by updating the configuration:

```
curl -u admin:infoblox -X PUT -H "Content-Type: application/json" -d '{"simulate_delay": true, "min_delay_ms": 100, "max_delay_ms": 500}' "http://localhost:8080/wapi/v2.11/config"
```

Configuration options:

| Option | Description | Default |
|--------|-------------|---------|
| simulate_delay | Add random delay to responses | False |
| min_delay_ms | Minimum delay in milliseconds | 50 |
| max_delay_ms | Maximum delay in milliseconds | 300 |
| simulate_failures | Randomly simulate server failures | False |
| failure_rate | Chance of failure if simulation enabled | 0.05 (5%) |
| detailed_logging | Enable detailed request/response logging | True |
| persistent_storage | Enable file-based persistent storage | False |
| storage_file | File to use for persistent storage | infoblox_mock_db.json |
| auth_required | Require authentication | True |
| rate_limit | Enable rate limiting | True |
| rate_limit_requests | Number of requests allowed per minute | 100 |
| simulate_db_lock | Simulate database locks | False |
| lock_probability | Chance of a lock per operation | 0.01 (1%) |

## Special Endpoints

The mock server includes some special endpoints not found in the real Infoblox API:

### Reset Database
```
curl -X POST "http://localhost:8080/wapi/v2.11/db/reset"
```

### Export Database
```
curl -u admin:infoblox "http://localhost:8080/wapi/v2.11/db/export"
```

### Health Check
```
curl "http://localhost:8080/wapi/v2.11/health"
```

## Supported Object Types

The mock server supports the following Infoblox object types:

- network
- network_container
- record:host
- record:a
- record:ptr
- record:cname
- record:mx
- record:srv
- record:txt
- range
- lease
- fixedaddress
- grid
- member

## Limitations

While the mock server aims to replicate the behavior of a real Infoblox system, it has some limitations:

- Some advanced features and object types are not supported
- Query performance does not scale like a real database
- Authentication is simplified (accepts any username/password)
- Some complex validations may be missing
- Extensible attributes (EAs) are supported but not validated

## Customization

You can extend the mock server to add support for additional object types or custom behaviors. The code is modular and well-documented to make it easy to modify.

## Troubleshooting

Check the log file (`infoblox_mock_server.log`) for detailed information about requests, responses, and errors.

If you're having issues with authentication, make sure you're creating a session first:
```
curl -u admin:infoblox -X POST http://localhost:8080/wapi/v2.11/grid/session
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.