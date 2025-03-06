<#
.SYNOPSIS
    Manages Infoblox networks - create, search, and manage network objects.
.DESCRIPTION
    This script provides functions to create, search, and manage Infoblox network objects.
    It includes thorough validation, error handling, and detailed logging.
    Modified to work with the Infoblox Mock Server.
.NOTES
    File Name      : Manage-InfobloxNetworks.ps1
    Prerequisite   : InfobloxCommon.psm1 module
.EXAMPLE
    .\Manage-InfobloxNetworks.ps1 -Action Search
    Searches for all networks in Infoblox.
.EXAMPLE
    .\Manage-InfobloxNetworks.ps1 -Action Create -Network "192.168.100.0/24" -Comment "Development Network"
    Creates a new network in Infoblox.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true)]
    [ValidateSet('Search', 'Create', 'Delete', 'Update')]
    [string]$Action,
    
    [Parameter(Mandatory=$false)]
    [string]$Network,
    
    [Parameter(Mandatory=$false)]
    [string]$Comment,
    
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
    [switch]$VerboseLogging
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
    LogFilePath = if ($LogFilePath) { $LogFilePath } else { Join-Path (Split-Path $MyInvocation.MyCommand.Path) "InfobloxNetworks.log" }
}
if ($VerboseLogging) { $loggingParams.VerboseLogging = $true }
Initialize-InfobloxLogging @loggingParams

# Script start
Write-InfobloxLog "======= Infoblox Network Management Script Started =======" -Level "INFO"
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
            Write-InfobloxLog "Searching for networks" -Level "INFO"
            
            $searchParams = @{
                EndpointUrl = "network"
                QueryParams = @{
                    "_return_fields" = "network,comment,network_view,extattrs"
                }
            }
            
            # Apply network filter if specified
            if ($Network) {
                $searchParams.QueryParams.network = $Network
                Write-InfobloxLog "Filtering by network: $Network" -Level "INFO"
            }
            
            $networks = Invoke-InfobloxRequest @searchParams
            
            if ($networks -and $networks.Count -gt 0) {
                Write-InfobloxLog "Found $($networks.Count) networks" -Level "SUCCESS"
                Format-InfobloxResult -InputObject $networks -Title "Networks"
            } else {
                Write-InfobloxLog "No networks found matching the criteria" -Level "WARNING"
                Write-Host "No networks found matching the criteria" -ForegroundColor Yellow
            }
        }
        
        'Create' {
            # Validate required parameters
            if (-not $Network) {
                throw "Network parameter is required for Create action"
            }
            
            Write-InfobloxLog "Creating network: $Network" -Level "INFO"
            
            # Validate network format
            if (-not (Test-InfobloxNetwork -Network $Network)) {
                throw "Invalid network format: $Network"
            }
            
            # Check if network already exists
            $existingNetwork = Get-InfobloxNetwork -Network $Network
            if ($existingNetwork) {
                throw "Network $Network already exists with reference $($existingNetwork._ref)"
            }
            
            # Prepare network data
            $networkData = @{
                network = $Network
                network_view = "default"
            }
            
            if ($Comment) {
                $networkData.comment = $Comment
            }
            
            # Create the network
            $createParams = @{
                EndpointUrl = "network"
                Method = "POST"
                Body = $networkData
                ReturnRef = $true
            }
            
            $result = Invoke-InfobloxRequest @createParams
            
            Write-InfobloxLog "Network $Network created successfully with reference $result" -Level "SUCCESS"
            Format-InfobloxResult -InputObject $result -Title "Network Created"
        }
        
        'Update' {
            # Validate required parameters
            if (-not $Network) {
                throw "Network parameter is required for Update action"
            }
            
            Write-InfobloxLog "Updating network: $Network" -Level "INFO"
            
            # Check if network exists
            $existingNetwork = Get-InfobloxNetwork -Network $Network
            if (-not $existingNetwork) {
                throw "Network $Network does not exist"
            }
            
            # Prepare update data
            $updateData = @{}
            
            if ($Comment) {
                $updateData.comment = $Comment
                Write-InfobloxLog "Updating comment to: $Comment" -Level "INFO"
            }
            
            if ($updateData.Keys.Count -eq 0) {
                throw "No updates specified. Please provide at least one field to update."
            }
            
            # Update the network
            $updateParams = @{
                EndpointUrl = $existingNetwork._ref
                Method = "PUT"
                Body = $updateData
                ReturnRef = $true
            }
            
            $result = Invoke-InfobloxRequest @updateParams
            
            Write-InfobloxLog "Network $Network updated successfully" -Level "SUCCESS"
            Format-InfobloxResult -InputObject $result -Title "Network Updated"
        }
        
        'Delete' {
            # Validate required parameters
            if (-not $Network) {
                throw "Network parameter is required for Delete action"
            }
            
            Write-InfobloxLog "Deleting network: $Network" -Level "INFO"
            
            # Check if network exists
            $existingNetwork = Get-InfobloxNetwork -Network $Network
            if (-not $existingNetwork) {
                throw "Network $Network does not exist"
            }
            
            # Confirm deletion
            Write-Host "Are you sure you want to delete network $Network ($($existingNetwork._ref))? (Y/N)" -ForegroundColor Yellow
            $confirmation = Read-Host
            
            if ($confirmation -ne "Y") {
                Write-InfobloxLog "Network deletion cancelled by user" -Level "WARNING"
                return
            }
            
            # Delete the network
            $deleteParams = @{
                EndpointUrl = $existingNetwork._ref
                Method = "DELETE"
                ReturnRef = $true
            }
            
            $result = Invoke-InfobloxRequest @deleteParams
            
            Write-InfobloxLog "Network $Network deleted successfully" -Level "SUCCESS"
            Format-InfobloxResult -InputObject $result -Title "Network Deleted"
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
    
    Write-InfobloxLog "======= Infoblox Network Management Script Completed =======" -Level "INFO"
}