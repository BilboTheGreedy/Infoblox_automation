# Complete Guide to Managing Infoblox with PowerShell Scripts

This guide provides comprehensive instructions for using the PowerShell scripts to manage your Infoblox environment. These scripts enable you to manage DNS records, IP addresses, and networks through the Infoblox API.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Module Overview](#module-overview)
4. [Common Parameters](#common-parameters)
5. [Managing DNS Records](#managing-dns-records)
6. [Managing IP Addresses](#managing-ip-addresses)
7. [Managing Networks](#managing-networks)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [Advanced Usage](#advanced-usage)

## Prerequisites

Before using these scripts, ensure you have:

- PowerShell 5.1 or higher
- Network connectivity to your Infoblox server
- Appropriate credentials with API access to your Infoblox system
- For the Mock Server: Docker or a direct installation of the Infoblox Mock Server

## Installation

1. Download all the script files to a local directory:
   - `InfobloxCommon.psm1` (Core module)
   - `Manage-InfobloxDnsRecords.ps1`
   - `Manage-InfobloxIPAddresses.ps1`
   - `Manage-InfobloxNetworks.ps1`

2. Ensure all files are in the same directory or add the directory to your PowerShell module path.

3. If you're using the Mock Server, start it:
   ```
   docker run -d -p 8080:8080 --name infoblox-mock infoblox-mock-server
   ```

## Module Overview

The solution consists of four main components:

1. **InfobloxCommon.psm1**: Core module containing shared functions for authentication, API calls, validation, and logging
2. **Manage-InfobloxDnsRecords.ps1**: Script for managing A and Host records
3. **Manage-InfobloxIPAddresses.ps1**: Script for managing IP addresses, including reservation and next available IP lookup
4. **Manage-InfobloxNetworks.ps1**: Script for managing network objects

## Common Parameters

All three management scripts share these common parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-Server` | Infoblox server hostname or IP | localhost |
| `-Port` | API port number | 8080 |
| `-UseSSL` | Use HTTPS instead of HTTP | False |
| `-Credential` | PSCredential object for authentication | Prompts if not provided |
| `-LogFilePath` | Custom log file location | Script directory |
| `-VerboseLogging` | Enable detailed logging | False |

## Managing DNS Records

The `Manage-InfobloxDnsRecords.ps1` script allows you to create, search, update, and delete DNS A and Host records.

### Examples

#### Search for DNS Records

Search for all Host records:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Search -RecordType Host
```

Search for a specific Host record:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Search -RecordType Host -Hostname "server1.example.com"
```

Search for all A records:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Search -RecordType A
```

#### Create DNS Records

Create an A record:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType A -Hostname "www.example.com" -IPAddress "192.168.1.10" -Comment "Web server"
```

Create a Host record:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType Host -Hostname "db.example.com" -IPAddress "192.168.1.20" -Comment "Database server"
```

Force creation even if record exists:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType A -Hostname "www.example.com" -IPAddress "192.168.1.15" -Comment "Updated web server" -Force
```

#### Update DNS Records

Update an A record's IP address:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Update -RecordType A -Hostname "www.example.com" -IPAddress "192.168.1.11"
```

Update a Host record's comment:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Update -RecordType Host -Hostname "db.example.com" -Comment "Primary database server"
```

#### Delete DNS Records

Delete an A record:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Delete -RecordType A -Hostname "www.example.com"
```

Delete a Host record:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Delete -RecordType Host -Hostname "db.example.com"
```

## Managing IP Addresses

The `Manage-InfobloxIPAddresses.ps1` script allows you to search for IP information, find the next available IP in a network, and reserve IP addresses.

### Examples

#### Search for IP Information

Search for a specific IP address:
```powershell
.\Manage-InfobloxIPAddresses.ps1 -Action Search -IPAddress "192.168.1.10"
```

Search for all IPs in a network:
```powershell
.\Manage-InfobloxIPAddresses.ps1 -Action Search -Network "192.168.1.0/24"
```

#### Find Next Available IP

Get the next available IP in a network:
```powershell
.\Manage-InfobloxIPAddresses.ps1 -Action NextAvailable -Network "192.168.1.0/24"
```

Save the result to a variable:
```powershell
$nextIP = .\Manage-InfobloxIPAddresses.ps1 -Action NextAvailable -Network "192.168.1.0/24"
```

#### Reserve IP Addresses

Reserve an IP address with a MAC address:
```powershell
.\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.50" -MACAddress "00:11:22:33:44:55"
```

Reserve an IP with hostname and comment:
```powershell
.\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.51" -MACAddress "00:11:22:33:44:66" -Hostname "printer.example.com" -Comment "Office printer"
```

Reserve an IP and automatically create a DNS record:
```powershell
.\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.52" -MACAddress "00:11:22:33:44:77" -Hostname "scanner.example.com" -CreateDNS
```

## Managing Networks

The `Manage-InfobloxNetworks.ps1` script allows you to create, search, update, and delete network objects.

### Examples

#### Search for Networks

Search for all networks:
```powershell
.\Manage-InfobloxNetworks.ps1 -Action Search
```

Search for a specific network:
```powershell
.\Manage-InfobloxNetworks.ps1 -Action Search -Network "192.168.1.0/24"
```

#### Create Networks

Create a new network:
```powershell
.\Manage-InfobloxNetworks.ps1 -Action Create -Network "192.168.100.0/24" -Comment "Development network"
```

#### Update Networks

Update a network's comment:
```powershell
.\Manage-InfobloxNetworks.ps1 -Action Update -Network "192.168.100.0/24" -Comment "Updated development network"
```

#### Delete Networks

Delete a network:
```powershell
.\Manage-InfobloxNetworks.ps1 -Action Delete -Network "192.168.100.0/24"
```

## Troubleshooting

### Common Issues and Solutions

1. **Connection Failures**
   - Verify server hostname/IP and port
   - Check credentials
   - Ensure network connectivity
   - For SSL issues, try without `-UseSSL` first

2. **Permission Errors**
   - Ensure your account has appropriate API permissions
   - Check API version compatibility

3. **Record Not Found**
   - Verify hostname format (FQDN)
   - Check if record exists in a different view
   - For networks, ensure CIDR notation is correct

### Logging

All scripts generate detailed logs:
- Default location: Script directory
- DNS Records: `InfobloxDnsRecords.log`
- IP Addresses: `InfobloxIPAddresses.log`
- Networks: `InfobloxNetworks.log`

Enable verbose logging for detailed information:
```powershell
.\Manage-InfobloxDnsRecords.ps1 -Action Search -RecordType Host -VerboseLogging
```

## Best Practices

1. **Use Variables for Repeated Operations**
   ```powershell
   $commonParams = @{
       Server = "infoblox.example.com"
       Port = 443
       UseSSL = $true
       Credential = $cred
   }
   
   .\Manage-InfobloxDnsRecords.ps1 -Action Search -RecordType Host @commonParams
   ```

2. **Error Handling**
   ```powershell
   try {
       .\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType A -Hostname "www.example.com" -IPAddress "192.168.1.10"
   }
   catch {
       Write-Host "Error creating record: $_" -ForegroundColor Red
   }
   ```

3. **Batch Processing**
   Create a CSV file with records and process in a loop:
   ```powershell
   $records = Import-Csv -Path "records.csv"
   foreach ($record in $records) {
       .\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType A -Hostname $record.Hostname -IPAddress $record.IPAddress -Comment $record.Comment
   }
   ```

## Advanced Usage

### Custom Functions

Create wrapper functions for common operations:

```powershell
function New-DNSRecord {
    param (
        [string]$Hostname,
        [string]$IPAddress,
        [string]$Comment = "",
        [string]$Server = "localhost"
    )
    
    .\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType A -Hostname $Hostname -IPAddress $IPAddress -Comment $Comment -Server $Server
}

# Usage
New-DNSRecord -Hostname "app.example.com" -IPAddress "192.168.1.100" -Comment "Application server"
```

### Integration with Other Systems

Use the scripts in larger automation workflows:

```powershell
# Provision a new server
$serverName = "newserver.example.com"
$network = "192.168.1.0/24"

# Get next available IP
$nextIP = .\Manage-InfobloxIPAddresses.ps1 -Action NextAvailable -Network $network

# Create DNS record
.\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType Host -Hostname $serverName -IPAddress $nextIP

# Output provisioning info
Write-Host "Server provisioned with IP: $nextIP and hostname: $serverName"
```

### Working with the Mock Server for Testing

The scripts are configured to work with the Infoblox Mock Server out of the box:

```powershell
# Start mock server (Docker)
docker start infoblox-mock

# Test creating a network
.\Manage-InfobloxNetworks.ps1 -Action Create -Network "10.0.0.0/24" -Comment "Test network"

# Test creating a DNS record
.\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType A -Hostname "test.example.com" -IPAddress "10.0.0.10"
```

This allows you to safely test your automation workflows before implementing them in production.
