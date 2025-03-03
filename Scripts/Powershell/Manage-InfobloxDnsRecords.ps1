<#
.SYNOPSIS
    Manages Infoblox DNS records - create, search, update, and delete A and Host records.
.DESCRIPTION
    This script provides functions to create, search, update, and delete Infoblox DNS A and Host records.
    It includes thorough validation, error handling, detailed logging, and verification of existing records.
.NOTES
    File Name      : Manage-InfobloxDnsRecords.ps1
    Prerequisite   : InfobloxCommon.psm1 module
.EXAMPLE
    .\Manage-InfobloxDnsRecords.ps1 -Action Search -RecordType Host
    Searches for all host records in Infoblox.
.EXAMPLE
    .\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType A -Hostname "www.example.com" -IPAddress "192.168.1.10" -Comment "Web server"
    Creates a new A record in Infoblox with verification of existing records.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [ValidateSet('Search', 'Create', 'Delete', 'Update')]
    [string]$Action,
    
    [Parameter(Mandatory=$true)]
    [ValidateSet('A', 'Host')]
    [string]$RecordType,
    
    [Parameter(Mandatory=$false)]
    [string]$Hostname,
    
    [Parameter(Mandatory=$false)]
    [string]$IPAddress,
    
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
    [string]$LogFilePath
    
    # Removed the duplicate Verbose parameter here
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
    LogFilePath = if ($LogFilePath) { $LogFilePath } else { Join-Path (Split-Path $MyInvocation.MyCommand.Path) "InfobloxDnsRecords.log" }
}
if ($VerbosePreference -eq 'Continue') { $loggingParams.Verbose = $true }
Initialize-InfobloxLogging @loggingParams

# Script start
Write-InfobloxLog "======= Infoblox DNS Record Management Script Started =======" -Level "INFO"
Write-InfobloxLog "Action: $Action, RecordType: $RecordType" -Level "INFO"

try {
    # Connect to Infoblox
    $connectionParams = @{
        Server = $Server
        Port = $Port
    }
    if ($UseSSL) { $connectionParams.UseSSL = $true }
    if ($Credential) { $connectionParams.Credential = $Credential }
    
# Connect to Infoblox (continued)
$connection = Connect-Infoblox @connectionParams
Write-InfobloxLog "Connected to $($connection.BaseUrl) as $($connection.Username)" -Level "SUCCESS"

# Perform the requested action
switch ($Action) {
    'Search' {
        Write-InfobloxLog "Searching for $RecordType records" -Level "INFO"
        
        $searchParams = @{
            EndpointUrl = "record:$($RecordType.ToLower())"
        }
        
        # Apply hostname filter if specified
        if ($Hostname) {
            $searchParams.QueryParams = @{ name = $Hostname }
            Write-InfobloxLog "Filtering by hostname: $Hostname" -Level "INFO"
        }
        
        $records = Invoke-InfobloxRequest @searchParams
        
        if ($records.Count -gt 0) {
            Write-InfobloxLog "Found $($records.Count) $RecordType records" -Level "SUCCESS"
            Format-InfobloxResult -InputObject $records -Title "$RecordType Records"
        } else {
            Write-InfobloxLog "No $RecordType records found matching the criteria" -Level "WARNING"
        }
    }
    
    'Create' {
        # Validate required parameters
        if (-not $Hostname) {
            throw "Hostname parameter is required for Create action"
        }
        
        if (-not $IPAddress) {
            throw "IPAddress parameter is required for Create action"
        }
        
        Write-InfobloxLog "Creating $RecordType record: $Hostname -> $IPAddress" -Level "INFO"
        
        # Validate hostname format
        if (-not (Test-InfobloxHostname -Hostname $Hostname)) {
            throw "Invalid hostname format: $Hostname"
        }
        
        # Validate IP address format
        if (-not (Test-InfobloxIPAddress -IPAddress $IPAddress)) {
            throw "Invalid IP address format: $IPAddress"
        }
        
        # Check for existing DNS records with same hostname (both A and Host records)
        $existingARecord = Get-InfobloxARecord -Hostname $Hostname
        $existingHostRecord = Get-InfobloxHostRecord -Hostname $Hostname
        
        if ($existingARecord -or $existingHostRecord) {
            $existingRecordType = if ($existingARecord) { "A" } else { "Host" }
            $existingRecordRef = if ($existingARecord) { $existingARecord[0]._ref } else { $existingHostRecord[0]._ref }
            $existingRecordIP = if ($existingARecord) { $existingARecord[0].ipv4addr } else { $existingHostRecord[0].ipv4addrs[0].ipv4addr }
            
            if (-not $Force) {
                throw "Hostname $Hostname already exists as $existingRecordType record ($existingRecordRef) with IP: $existingRecordIP. Use -Force to override."
            }
            
            Write-InfobloxLog "WARNING: Hostname $Hostname already exists as $existingRecordType record. Proceeding due to -Force flag." -Level "WARNING"
        }
        
        # Check if IP address is already in use
        $existingIP = Get-InfobloxIPAddress -IPAddress $IPAddress
        if ($existingIP -and -not $Force) {
            $existingObjects = $existingIP[0].objects -join ", "
            throw "IP address $IPAddress is already in use by: $existingObjects. Use -Force to override."
        } elseif ($existingIP) {
            Write-InfobloxLog "WARNING: IP address $IPAddress is already in use. Proceeding due to -Force flag." -Level "WARNING"
        }
        
        # Prepare record data based on type
        if ($RecordType -eq "A") {
            $recordData = @{
                name = $Hostname
                ipv4addr = $IPAddress
                view = "default"
            }
            
            if ($Comment) {
                $recordData.comment = $Comment
            }
            
            # Create the A record
            $createParams = @{
                EndpointUrl = "record:a"
                Method = "POST"
                Body = $recordData
                ReturnRef = $true
            }
            
            $result = Invoke-InfobloxRequest @createParams
            
            Write-InfobloxLog "A record $Hostname -> $IPAddress created successfully with reference $result" -Level "SUCCESS"
            Format-InfobloxResult -InputObject $result -Title "A Record Created"
        }
        elseif ($RecordType -eq "Host") {
            $recordData = @{
                name = $Hostname
                ipv4addrs = @(
                    @{
                        ipv4addr = $IPAddress
                    }
                )
                view = "default"
            }
            
            if ($Comment) {
                $recordData.comment = $Comment
            }
            
            # Create the Host record
            $createParams = @{
                EndpointUrl = "record:host"
                Method = "POST"
                Body = $recordData
                ReturnRef = $true
            }
            
            $result = Invoke-InfobloxRequest @createParams
            
            Write-InfobloxLog "Host record $Hostname -> $IPAddress created successfully with reference $result" -Level "SUCCESS"
            Format-InfobloxResult -InputObject $result -Title "Host Record Created"
        }
    }
    
    'Update' {
        # Validate required parameters
        if (-not $Hostname) {
            throw "Hostname parameter is required for Update action"
        }
        
        Write-InfobloxLog "Updating $RecordType record: $Hostname" -Level "INFO"
        
        # Get existing record
        $existingRecord = if ($RecordType -eq "A") {
            Get-InfobloxARecord -Hostname $Hostname
        } else {
            Get-InfobloxHostRecord -Hostname $Hostname
        }
        
        if (-not $existingRecord) {
            throw "$RecordType record for $Hostname does not exist"
        }
        
        # Prepare update data
        $updateData = @{}
        
        if ($IPAddress) {
            Write-InfobloxLog "Updating IP address to: $IPAddress" -Level "INFO"
            
            # Validate IP address format
            if (-not (Test-InfobloxIPAddress -IPAddress $IPAddress)) {
                throw "Invalid IP address format: $IPAddress"
            }
            
            # Check if IP address is already in use by another record
            $existingIP = Get-InfobloxIPAddress -IPAddress $IPAddress
            if ($existingIP -and -not $Force) {
                $existingObjects = $existingIP[0].objects -join ", "
                if (-not $existingObjects.Contains($existingRecord[0]._ref)) {
                    throw "IP address $IPAddress is already in use by: $existingObjects. Use -Force to override."
                }
            } elseif ($existingIP -and $Force) {
                Write-InfobloxLog "WARNING: IP address $IPAddress is already in use. Proceeding due to -Force flag." -Level "WARNING"
            }
            
            if ($RecordType -eq "A") {
                $updateData.ipv4addr = $IPAddress
            } else {
                $updateData.ipv4addrs = @(
                    @{
                        ipv4addr = $IPAddress
                    }
                )
            }
        }
        
        if ($Comment) {
            $updateData.comment = $Comment
            Write-InfobloxLog "Updating comment to: $Comment" -Level "INFO"
        }
        
        if ($updateData.Keys.Count -eq 0) {
            throw "No updates specified. Please provide at least one field to update."
        }
        
        # Update the record
        $updateParams = @{
            EndpointUrl = $existingRecord[0]._ref
            Method = "PUT"
            Body = $updateData
            ReturnRef = $true
        }
        
        $result = Invoke-InfobloxRequest @updateParams
        
        Write-InfobloxLog "$RecordType record $Hostname updated successfully" -Level "SUCCESS"
        Format-InfobloxResult -InputObject $result -Title "$RecordType Record Updated"
    }
    
    'Delete' {
        # Validate required parameters
        if (-not $Hostname) {
            throw "Hostname parameter is required for Delete action"
        }
        
        Write-InfobloxLog "Deleting $RecordType record: $Hostname" -Level "INFO"
        
        # Get existing record
        $existingRecord = if ($RecordType -eq "A") {
            Get-InfobloxARecord -Hostname $Hostname
        } else {
            Get-InfobloxHostRecord -Hostname $Hostname
        }
        
        if (-not $existingRecord) {
            throw "$RecordType record for $Hostname does not exist"
        }
        
        # Confirm deletion
        Write-Host "Are you sure you want to delete $RecordType record $Hostname ($($existingRecord[0]._ref))? (Y/N)" -ForegroundColor Yellow
        $confirmation = Read-Host
        
        if ($confirmation -ne "Y") {
            Write-InfobloxLog "$RecordType record deletion cancelled by user" -Level "WARNING"
            return
        }
        
        # Delete the record
        $deleteParams = @{
            EndpointUrl = $existingRecord[0]._ref
            Method = "DELETE"
            ReturnRef = $true
        }
        
        $result = Invoke-InfobloxRequest @deleteParams
        
        Write-InfobloxLog "$RecordType record $Hostname deleted successfully" -Level "SUCCESS"
        Format-InfobloxResult -InputObject $result -Title "$RecordType Record Deleted"
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

Write-InfobloxLog "======= Infoblox DNS Record Management Script Completed =======" -Level "INFO"
}