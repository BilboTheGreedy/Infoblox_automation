<#
.SYNOPSIS
    Manages IP addresses in Infoblox - search, reserve, and find next available.
.DESCRIPTION
    This script provides functions to search for IP addresses, get next available IP from a network,
    and reserve fixed addresses. It includes thorough validation, error handling, and detailed logging.
.NOTES
    File Name      : Manage-InfobloxIPAddresses.ps1
    Prerequisite   : InfobloxCommon.psm1 module
.EXAMPLE
    .\Manage-InfobloxIPAddresses.ps1 -Action Search -IPAddress "192.168.1.10"
    Searches for information about a specific IP address.
.EXAMPLE
    .\Manage-InfobloxIPAddresses.ps1 -Action NextAvailable -Network "192.168.1.0/24"
    Finds the next available IP address in the specified network.
.EXAMPLE
    .\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.50" -MACAddress "00:11:22:33:44:55" -Hostname "printer.example.com"
    Reserves an IP address as a fixed address with specified MAC address.
.EXAMPLE
    .\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.50" -MACAddress "00:11:22:33:44:55" -Hostname "printer.example.com" -CreateDNS
    Reserves an IP address and automatically creates a DNS record for the hostname.
.EXAMPLE
    .\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.50" -MACAddress "00:11:22:33:44:55" -Hostname "printer.example.com" -CreateDNS -DNSView "external"
    Reserves an IP address and automatically creates a DNS record in the specified DNS view.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [ValidateSet('Search', 'NextAvailable', 'Reserve')]
    [string]$Action,
    
    [Parameter(Mandatory=$false)]
    [string]$IPAddress,
    
    [Parameter(Mandatory=$false)]
    [string]$Network,
    
    [Parameter(Mandatory=$false)]
    [string]$MACAddress,
    
    [Parameter(Mandatory=$false)]
    [string]$Hostname,
    
    [Parameter(Mandatory=$false)]
    [string]$Comment,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force,
    
    [Parameter(Mandatory=$false)]
    [string]$Server = "localhost",
    
    [Parameter(Mandatory=$false)]
    [int]$Port = 8080,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseSSL,
    
    [Parameter(Mandatory=$false)]
    [System.Management.Automation.PSCredential]$Credential,
    
    [Parameter(Mandatory=$false)]
    [string]$LogFilePath,
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateDNS,
    
    [Parameter(Mandatory=$false)]
    [string]$DNSView = "default"
)

# Ensure InfobloxCommon module is imported
$moduleFile = Join-Path (Split-Path $MyInvocation.MyCommand.Path) "InfobloxCommon.psm1"
if (-not (Test-Path $moduleFile)) {
    Write-Error "Required module InfobloxCommon.psm1 not found at $moduleFile"
    exit 1
}

Import-Module $moduleFile -Force

# Initialize logging
$loggingParams = @{
    LogFilePath = if ($LogFilePath) { $LogFilePath } else { Join-Path (Split-Path $MyInvocation.MyCommand.Path) "InfobloxIPAddresses.log" }
}
if ($VerbosePreference -eq 'Continue') { $loggingParams.Verbose = $true }
Initialize-InfobloxLogging @loggingParams

# Script start
Write-InfobloxLog "======= Infoblox IP Address Management Script Started =======" -Level "INFO"
Write-InfobloxLog "Action: $Action" -Level "INFO"

try {
    # Connect to Infoblox
    $connectionParams = @{
        Server = $Server
        Port = $Port
    }
    if ($UseSSL) { $connectionParams.UseSSL = $true }
    if ($Credential) { $connectionParams.Credential = $Credential }
    
    $connection = Connect-Infoblox @connectionParams
    Write-InfobloxLog "Connected to $($connection.BaseUrl) as $($connection.Username)" -Level "SUCCESS"
    
    # Perform the requested action
    switch ($Action) {
        'Search' {
            # Validate parameters
            if (-not $IPAddress -and -not $Network) {
                throw "Either IPAddress or Network parameter is required for Search action"
            }
            
            if ($IPAddress) {
                Write-InfobloxLog "Searching for IP address: $IPAddress" -Level "INFO"
                
                # Validate IP address format
                if (-not (Test-InfobloxIPAddress -IPAddress $IPAddress)) {
                    throw "Invalid IP address format: $IPAddress"
                }
                
                $searchParams = @{
                    EndpointUrl = "ipv4address"
                    QueryParams = @{
                        "ip_address" = $IPAddress
                    }
                }
                
                $results = Invoke-InfobloxRequest @searchParams
                
                if ($results.Count -gt 0) {
                    Write-InfobloxLog "Found information for IP address $IPAddress" -Level "SUCCESS"
                    
                    # Enhance results with detailed information
                    foreach ($result in $results) {
                        if ($result.objects -and $result.objects.Count -gt 0) {
                            $result | Add-Member -MemberType NoteProperty -Name "Status" -Value "USED" -Force
                            
                            # Get detailed information for each object
                            $objectDetails = @()
                            foreach ($objRef in $result.objects) {
                                try {
                                    $detailParams = @{
                                        EndpointUrl = $objRef
                                    }
                                    
                                    $detail = Invoke-InfobloxRequest @detailParams
                                    $objectDetails += $detail
                                }
                                catch {
                                    Write-InfobloxLog "Warning: Could not get details for object $objRef" -Level "WARNING"
                                }
                            }
                            $result | Add-Member -MemberType NoteProperty -Name "ObjectDetails" -Value $objectDetails -Force
                        }
                        else {
                            $result | Add-Member -MemberType NoteProperty -Name "Status" -Value "UNUSED" -Force
                        }
                    }
                    
                    Format-InfobloxResult -InputObject $results -Title "IP Address Information"
                } else {
                    Write-InfobloxLog "No information found for IP address $IPAddress" -Level "WARNING"
                }
            }
            
            if ($Network) {
                Write-InfobloxLog "Searching for network: $Network" -Level "INFO"
                
                # Validate network format
                if (-not (Test-InfobloxNetwork -Network $Network)) {
                    throw "Invalid network format: $Network"
                }
                
                $searchParams = @{
                    EndpointUrl = "ipv4address"
                    QueryParams = @{
                        "network" = $Network
                    }
                }
                
                $results = Invoke-InfobloxRequest @searchParams
                
                if ($results.Count -gt 0) {
                    Write-InfobloxLog "Found $($results.Count) IP addresses in network $Network" -Level "SUCCESS"
                    
                    # Group results by status
                    $usedIPs = $results | Where-Object { $_.status -eq "USED" }
                    $unusedIPs = $results | Where-Object { $_.status -eq "UNUSED" }
                    
                    Write-Host "`nNetwork: $Network" -ForegroundColor Cyan
                    Write-Host "Total IPs: $($results.Count)" -ForegroundColor Cyan
                    Write-Host "Used IPs: $($usedIPs.Count)" -ForegroundColor Yellow
                    Write-Host "Unused IPs: $($unusedIPs.Count)" -ForegroundColor Green
                    Write-Host "`nIP Usage Details:" -ForegroundColor Cyan
                    
                    Format-InfobloxResult -InputObject $results -Title "Network IP Usage"
                } else {
                    Write-InfobloxLog "No information found for network $Network" -Level "WARNING"
                }
            }
        }
        
        'NextAvailable' {
            # Validate parameters
            if (-not $Network) {
                throw "Network parameter is required for NextAvailable action"
            }
            
            Write-InfobloxLog "Finding next available IP address in network: $Network" -Level "INFO"
            
            # Validate network format
            if (-not (Test-InfobloxNetwork -Network $Network)) {
                throw "Invalid network format: $Network"
            }
            
            # Check if network exists
            $existingNetwork = Get-InfobloxNetwork -Network $Network
            if (-not $existingNetwork) {
                throw "Network $Network does not exist"
            }
            
            # Get next available IP
            $nextIPParams = @{
                EndpointUrl = "network/$Network/next_available_ip"
                Method = "POST"
            }
            
            $result = Invoke-InfobloxRequest @nextIPParams
            
            if ($result -and $result.ips -and $result.ips.Count -gt 0) {
                $nextIP = $result.ips[0]
                Write-InfobloxLog "Next available IP address in network ${Network}: $nextIP" -Level "SUCCESS"
                
                Write-Host "`nNext Available IP" -ForegroundColor Cyan
                Write-Host "================" -ForegroundColor Cyan
                Write-Host "Network: $Network" -ForegroundColor Cyan
                Write-Host "IP Address: $nextIP" -ForegroundColor Green
                
                # Return the IP address for potential further use
                return $nextIP
            } else {
                Write-InfobloxLog "No available IP addresses found in network $Network" -Level "WARNING"
                return $null
            }
        }
        
        'Reserve' {
            # Validate parameters
            if (-not $IPAddress) {
                throw "IPAddress parameter is required for Reserve action"
            }
            
            if (-not $MACAddress) {
                throw "MACAddress parameter is required for Reserve action"
            }
            
            Write-InfobloxLog "Reserving IP address $IPAddress with MAC address $MACAddress" -Level "INFO"
            
            # Validate IP address format
            if (-not (Test-InfobloxIPAddress -IPAddress $IPAddress)) {
                throw "Invalid IP address format: $IPAddress"
            }
            
            # Validate MAC address format
            if (-not (Test-InfobloxMAC -MACAddress $MACAddress)) {
                throw "Invalid MAC address format: $MACAddress"
            }
            
            # Check if IP is already in use
            $existingIP = Get-InfobloxIPAddress -IPAddress $IPAddress
            if ($existingIP -and -not $Force) {
                $existingObjects = $existingIP[0].objects -join ", "
                throw "IP address $IPAddress is already in use by: $existingObjects. Use -Force to override."
            } elseif ($existingIP) {
                Write-InfobloxLog "WARNING: IP address $IPAddress is already in use. Proceeding due to -Force flag." -Level "WARNING"
            }
            
            # If hostname is provided, check if it already exists in DNS
            if ($Hostname) {
                Write-InfobloxLog "Checking if hostname $Hostname already exists in view '$DNSView'" -Level "INFO"
                
                # Validate hostname format
                if (-not (Test-InfobloxHostname -Hostname $Hostname)) {
                    throw "Invalid hostname format: $Hostname"
                }
                
                # Get existing DNS records
                $existingARecord = Get-InfobloxARecord -Hostname $Hostname
                $existingHostRecord = Get-InfobloxHostRecord -Hostname $Hostname
                
                # Filter records by view if needed
                if ($existingARecord) {
                    $existingARecord = $existingARecord | Where-Object { $_.view -eq $DNSView }
                }
                
                if ($existingHostRecord) {
                    $existingHostRecord = $existingHostRecord | Where-Object { $_.view -eq $DNSView }
                }
                
                if ($existingARecord -or $existingHostRecord) {
                    $existingRecordType = if ($existingARecord) { "A" } else { "Host" }
                    $existingRecordRef = if ($existingARecord) { $existingARecord[0]._ref } else { $existingHostRecord[0]._ref }
                    $existingRecordIP = if ($existingARecord) { $existingARecord[0].ipv4addr } else { $existingHostRecord[0].ipv4addrs[0].ipv4addr }
                    
                    if (-not $Force) {
                        throw "Hostname $Hostname already exists as $existingRecordType record ($existingRecordRef) with IP: $existingRecordIP in view '$DNSView'. Use -Force to override."
                    }
                    
                    Write-InfobloxLog "WARNING: Hostname $Hostname already exists as $existingRecordType record in view '$DNSView'. Proceeding due to -Force flag." -Level "WARNING"
                }
            }
            
            # Prepare fixed address data
            $fixedAddressData = @{
                ipv4addr = $IPAddress
                mac = $MACAddress
            }
            
            if ($Hostname) {
                Write-InfobloxLog "Setting hostname for fixed address: $Hostname" -Level "INFO"
                $fixedAddressData.name = $Hostname
            }
            
            if ($Comment) {
                $fixedAddressData.comment = $Comment
            }
            
            # Create the fixed address
            $createParams = @{
                EndpointUrl = "fixedaddress"
                Method = "POST"
                Body = $fixedAddressData
                ReturnRef = $true
            }
            
            $result = Invoke-InfobloxRequest @createParams
            
            Write-InfobloxLog "IP address $IPAddress reserved successfully with MAC $MACAddress" -Level "SUCCESS"
            Format-InfobloxResult -InputObject $result -Title "IP Address Reserved"
            
            # If hostname is provided and no DNS record exists, check if we should create DNS record
            if ($Hostname -and -not $existingARecord -and -not $existingHostRecord) {
                $createDnsRecord = $false
                
                if ($CreateDNS) {
                    # Automatically create DNS record if -CreateDNS parameter is specified
                    $createDnsRecord = $true
                    Write-InfobloxLog "Automatically creating DNS record in view '$DNSView' due to -CreateDNS parameter" -Level "INFO"
                } else {
                    # Ask user if they want to create a DNS record
                    Write-Host "`nWould you like to create a DNS record for $Hostname with IP $IPAddress in view '$DNSView'? (Y/N)" -ForegroundColor Yellow
                    $response = Read-Host
                    $createDnsRecord = ($response -eq "Y")
                }
                
                if ($createDnsRecord) {
                    Write-InfobloxLog "Creating Host record for $Hostname with IP $IPAddress in view '$DNSView'" -Level "INFO"
                    
                    # Create Host record
                    $hostData = @{
                        name = $Hostname
                        ipv4addrs = @(
                            @{
                                ipv4addr = $IPAddress
                            }
                        )
                        view = $DNSView
                    }
                    
                    if ($Comment) {
                        $hostData.comment = $Comment
                    }
                    
                    $createHostParams = @{
                        EndpointUrl = "record:host"
                        Method = "POST"
                        Body = $hostData
                        ReturnRef = $true
                    }
                    
                    $hostResult = Invoke-InfobloxRequest @createHostParams
                    
                    Write-InfobloxLog "Host record $Hostname -> $IPAddress created successfully in view '$DNSView' with reference $hostResult" -Level "SUCCESS"
                    Format-InfobloxResult -InputObject $hostResult -Title "Host Record Created"
                }
            }
        }
    }
}
catch {
    Write-InfobloxLog "ERROR: $_" -Level "ERROR"
    Write-Error $_
}
finally {
    # Disconnect from Infoblox
    if (Test-InfobloxConnection) {
        Disconnect-Infoblox | Out-Null
    }
    
    Write-InfobloxLog "======= Infoblox IP Address Management Script Completed =======" -Level "INFO"
}