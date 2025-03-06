#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Demonstrates all major features of the Infoblox PowerShell management scripts.
.DESCRIPTION
    This comprehensive script showcases the capabilities of the Infoblox management
    PowerShell scripts by running through a series of real-world examples for
    managing DNS records, IP addresses, and networks.
.NOTES
    File Name      : Demo-InfobloxScripts.ps1
    Prerequisite   : InfobloxCommon.psm1 module and management scripts
    Author         : System Administrator
    Version        : 1.0
.EXAMPLE
    .\Demo-InfobloxScripts.ps1
    Runs the full demonstration of Infoblox management capabilities.
.EXAMPLE
    .\Demo-InfobloxScripts.ps1 -Server "infoblox.company.com" -Credentials $myCreds
    Runs the demonstration against a specific Infoblox server with provided credentials.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$false)]
    [string]$Server = "localhost",
    
    [Parameter(Mandatory=$false)]
    [int]$Port = 8080,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseSSL,
    
    [Parameter(Mandatory=$false)]
    [System.Management.Automation.PSCredential]$Credentials,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipNetworks,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipDNS,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipIPAddresses,
    
    [Parameter(Mandatory=$false)]
    [switch]$VerboseLogging
)

# Ensure all scripts exist in the same directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$commonModulePath = Join-Path $scriptDir "InfobloxCommon.psm1"
$dnsScriptPath = Join-Path $scriptDir "Manage-InfobloxDnsRecords.ps1"
$ipScriptPath = Join-Path $scriptDir "Manage-InfobloxIPAddresses.ps1"
$networkScriptPath = Join-Path $scriptDir "Manage-InfobloxNetworks.ps1"

# Check if required files exist
$missingFiles = @()
if (-not (Test-Path $commonModulePath)) { $missingFiles += "InfobloxCommon.psm1" }
if (-not (Test-Path $dnsScriptPath)) { $missingFiles += "Manage-InfobloxDnsRecords.ps1" }
if (-not (Test-Path $ipScriptPath)) { $missingFiles += "Manage-InfobloxIPAddresses.ps1" }
if (-not (Test-Path $networkScriptPath)) { $missingFiles += "Manage-InfobloxNetworks.ps1" }

if ($missingFiles.Count -gt 0) {
    Write-Error "Missing required files: $($missingFiles -join ', '). Ensure all scripts are in the same directory."
    exit 1
}

# Import the common module
Import-Module $commonModulePath -Force

# Initialize logging
Initialize-InfobloxLogging -LogFilePath (Join-Path $scriptDir "Infoblox-Demo.log") -VerboseLogging:$VerboseLogging
Write-InfobloxLog "======= Infoblox Demo Script Started =======" -Level "INFO"

# Setup common parameters
$commonParams = @{
    Server = $Server
    Port = $Port
}

if ($UseSSL) { $commonParams.UseSSL = $true }
if ($VerboseLogging) { $commonParams.VerboseLogging = $true }

# Get or create credentials
if (-not $Credentials) {
    # For mock server on localhost, use default credentials
    if ($Server -eq "localhost" -or $Server -eq "127.0.0.1") {
        $securePassword = ConvertTo-SecureString "infoblox" -AsPlainText -Force
        $Credentials = New-Object System.Management.Automation.PSCredential("admin", $securePassword)
        Write-Host "Using default credentials for mock server: admin/infoblox" -ForegroundColor Yellow
    }
    else {
        $Credentials = Get-Credential -Message "Enter Infoblox credentials"
    }
}

$commonParams.Credential = $Credentials

# Helper function to display section headers
function Write-SectionHeader {
    param (
        [string]$Title
    )
    
    $separator = "=" * $Title.Length
    Write-Host "`n$separator" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "$separator`n" -ForegroundColor Cyan
}

# Helper function to pause between examples
function Pause-Demo {
    param (
        [string]$Message = "Press Enter to continue..."
    )
    
    Write-Host $Message -ForegroundColor Yellow
    Read-Host | Out-Null
}

#region Network Management

if (-not $SkipNetworks) {
    Write-SectionHeader "NETWORK MANAGEMENT DEMO"
    
    # Demo network parameters
    $demoNetwork = "192.168.200.0/24"
    $demoNetworkComment = "Demo Network for PowerShell Scripts"
    $updatedComment = "Updated Demo Network Comment"

    try {
        # 1. Search all networks
        Write-Host "Searching for all networks..." -ForegroundColor Green
        & $networkScriptPath -Action Search @commonParams
        Pause-Demo

        # 2. Search for a specific network
        Write-Host "Searching for network 10.10.10.0/24..." -ForegroundColor Green
        & $networkScriptPath -Action Search -Network "10.10.10.0/24" @commonParams
        Pause-Demo

        # 3. Create a new network
        Write-Host "Creating new network $demoNetwork..." -ForegroundColor Green
        & $networkScriptPath -Action Create -Network $demoNetwork -Comment $demoNetworkComment @commonParams
        Pause-Demo

        # 4. Update the network
        Write-Host "Updating network $demoNetwork comment..." -ForegroundColor Green
        & $networkScriptPath -Action Update -Network $demoNetwork -Comment $updatedComment @commonParams
        Pause-Demo

        # 5. Verify the update
        Write-Host "Verifying updated network..." -ForegroundColor Green
        & $networkScriptPath -Action Search -Network $demoNetwork @commonParams
        Pause-Demo

        # 6. Delete the network at the end of demo
        Write-Host "Deleting network $demoNetwork..." -ForegroundColor Green
        & $networkScriptPath -Action Delete -Network $demoNetwork @commonParams

        Write-Host "Network management demo completed successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "Error in network management demo: $_" -ForegroundColor Red
    }
}

#endregion

#region DNS Record Management

if (-not $SkipDNS) {
    Write-SectionHeader "DNS RECORD MANAGEMENT DEMO"
    
    # Demo DNS parameters
    $demoARecord = "demo-a.example.com"
    $demoHostRecord = "demo-host.example.com"
    $demoIPAddress1 = "192.168.1.100"
    $demoIPAddress2 = "192.168.1.101"
    $demoComment = "Demo DNS Record"
    $updatedComment = "Updated Demo DNS Record"

    try {
        # 1. Search for all A records
        Write-Host "Searching for all A records..." -ForegroundColor Green
        & $dnsScriptPath -Action Search -RecordType A @commonParams
        Pause-Demo

        # 2. Search for all Host records
        Write-Host "Searching for all Host records..." -ForegroundColor Green
        & $dnsScriptPath -Action Search -RecordType Host @commonParams
        Pause-Demo

        # 3. Create an A record
        Write-Host "Creating A record $demoARecord..." -ForegroundColor Green
        & $dnsScriptPath -Action Create -RecordType A -Hostname $demoARecord -IPAddress $demoIPAddress1 -Comment $demoComment @commonParams
        Pause-Demo

        # 4. Create a Host record
        Write-Host "Creating Host record $demoHostRecord..." -ForegroundColor Green
        & $dnsScriptPath -Action Create -RecordType Host -Hostname $demoHostRecord -IPAddress $demoIPAddress2 -Comment $demoComment @commonParams
        Pause-Demo

        # 5. Search for specific records
        Write-Host "Searching for A record $demoARecord..." -ForegroundColor Green
        & $dnsScriptPath -Action Search -RecordType A -Hostname $demoARecord @commonParams
        Pause-Demo

        Write-Host "Searching for Host record $demoHostRecord..." -ForegroundColor Green
        & $dnsScriptPath -Action Search -RecordType Host -Hostname $demoHostRecord @commonParams
        Pause-Demo

        # 6. Update records
        Write-Host "Updating A record $demoARecord comment..." -ForegroundColor Green
        & $dnsScriptPath -Action Update -RecordType A -Hostname $demoARecord -Comment $updatedComment @commonParams
        Pause-Demo

        Write-Host "Updating Host record $demoHostRecord IP address..." -ForegroundColor Green
        & $dnsScriptPath -Action Update -RecordType Host -Hostname $demoHostRecord -IPAddress "192.168.1.102" @commonParams
        Pause-Demo

        # 7. Verify updates
        Write-Host "Verifying updated records..." -ForegroundColor Green
        & $dnsScriptPath -Action Search -RecordType A -Hostname $demoARecord @commonParams
        & $dnsScriptPath -Action Search -RecordType Host -Hostname $demoHostRecord @commonParams
        Pause-Demo

        # 8. Delete records
        Write-Host "Deleting A record $demoARecord..." -ForegroundColor Green
        & $dnsScriptPath -Action Delete -RecordType A -Hostname $demoARecord @commonParams
        Pause-Demo

        Write-Host "Deleting Host record $demoHostRecord..." -ForegroundColor Green
        & $dnsScriptPath -Action Delete -RecordType Host -Hostname $demoHostRecord @commonParams

        Write-Host "DNS record management demo completed successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "Error in DNS record management demo: $_" -ForegroundColor Red
    }
}

#endregion

#region IP Address Management

if (-not $SkipIPAddresses) {
    Write-SectionHeader "IP ADDRESS MANAGEMENT DEMO"
    
    # Demo IP parameters
    $demoNetwork = "10.10.10.0/24"  # Use existing network in mock server
    $demoFixedIP = "10.10.10.150"
    $demoMAC = "aa:bb:cc:dd:ee:ff"
    $demoHostname = "reserved-ip.example.com"
    $demoComment = "Demo Fixed Address"

    try {
        # 1. Search for IPs in a network
        Write-Host "Searching for IPs in network $demoNetwork..." -ForegroundColor Green
        & $ipScriptPath -Action Search -Network $demoNetwork @commonParams
        Pause-Demo

        # 2. Get next available IP
        Write-Host "Getting next available IP in network $demoNetwork..." -ForegroundColor Green
        $nextIP = & $ipScriptPath -Action NextAvailable -Network $demoNetwork @commonParams
        Pause-Demo
        
        Write-Host "Next available IP is: $nextIP" -ForegroundColor Magenta
        
        # If no IP was returned, use a default one for demonstration
        if (-not $nextIP) {
            $nextIP = $demoFixedIP
            Write-Host "Using default IP $nextIP for demonstration" -ForegroundColor Yellow
        }

        # 3. Reserve an IP address
        Write-Host "Reserving IP address $nextIP with MAC $demoMAC..." -ForegroundColor Green
        & $ipScriptPath -Action Reserve -IPAddress $nextIP -MACAddress $demoMAC -Hostname $demoHostname -Comment $demoComment @commonParams
        Pause-Demo

        # 4. Search for the reserved IP
        Write-Host "Searching for reserved IP $nextIP..." -ForegroundColor Green
        & $ipScriptPath -Action Search -IPAddress $nextIP @commonParams
        Pause-Demo

        # 5. Search for the hostname
        Write-Host "Verifying DNS record was created for $demoHostname..." -ForegroundColor Green
        & $dnsScriptPath -Action Search -RecordType Host -Hostname $demoHostname @commonParams
        Pause-Demo

        # 6. Delete the fixed address by deleting the host record
        Write-Host "Cleaning up by deleting host record for $demoHostname..." -ForegroundColor Green
        & $dnsScriptPath -Action Delete -RecordType Host -Hostname $demoHostname @commonParams

        Write-Host "IP address management demo completed successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "Error in IP address management demo: $_" -ForegroundColor Red
    }
}

#endregion

Write-SectionHeader "DEMO COMPLETED"
Write-Host "The Infoblox management script demonstration has completed." -ForegroundColor Green
Write-Host "You've seen examples of managing:" -ForegroundColor Green
if (-not $SkipNetworks) { Write-Host "- Networks (create, search, update, delete)" -ForegroundColor Green }
if (-not $SkipDNS) { Write-Host "- DNS Records (A and Host records)" -ForegroundColor Green }
if (-not $SkipIPAddresses) { Write-Host "- IP Addresses (search, next available, reservation)" -ForegroundColor Green }

Write-InfobloxLog "======= Infoblox Demo Script Completed =======" -Level "INFO"