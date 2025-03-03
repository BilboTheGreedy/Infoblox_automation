# InfobloxCommon.psm1
# Common functions for Infoblox API interaction

# Set TLS 1.2 for all web requests
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Module-scoped variables
$script:InfobloxSession = $null
$script:BaseUrl = $null
$script:LogFile = $null
$script:Credential = $null
$script:VerboseLogging = $false

#region Logging Functions

function Initialize-InfobloxLogging {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$false)]
        [string]$LogFilePath = "$(Split-Path $MyInvocation.MyCommand.Path)\InfobloxOperations.log",
        
        [Parameter(Mandatory=$false)]
        [switch]$VerboseLogging
    )
    
    $script:LogFile = $LogFilePath
    $script:VerboseLogging = $VerboseLogging
    
    # Initialize log file with header if it doesn't exist
    if (-not (Test-Path $script:LogFile)) {
        $logHeader = @"
#########################################################
# Infoblox Operations Log File
# Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
#########################################################

"@
        $logHeader | Out-File -FilePath $script:LogFile -Encoding utf8
    }
    
    Write-InfobloxLog "Logging initialized to $script:LogFile"
}

function Write-InfobloxLog {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARNING", "ERROR", "SUCCESS")]
        [string]$Level = "INFO"
    )
    
    # Only proceed if logging is initialized
    if (-not $script:LogFile) {
        return
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to log file
    $logEntry | Out-File -FilePath $script:LogFile -Append -Encoding utf8
    
    # Output to console based on level
    switch ($Level) {
        "INFO" {
            if ($script:VerboseLogging) { Write-Host $logEntry -ForegroundColor Gray }
        }
        "WARNING" { Write-Host $logEntry -ForegroundColor Yellow }
        "ERROR" { Write-Host $logEntry -ForegroundColor Red }
        "SUCCESS" { Write-Host $logEntry -ForegroundColor Green }
    }
}

#endregion

#region Connection Functions

function Connect-Infoblox {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Server,
        
        [Parameter(Mandatory=$false)]
        [int]$Port = 8080,
        
        [Parameter(Mandatory=$false)]
        [string]$ApiVersion = "v2.11",
        
        [Parameter(Mandatory=$false)]
        [switch]$UseSSL,
        
        [Parameter(Mandatory=$false)]
        [System.Management.Automation.PSCredential]$Credential
    )
    
    try {
        # Build the base URL
        $protocol = if ($UseSSL) { "https" } else { "http" }
        $script:BaseUrl = "${protocol}://${Server}:${Port}/wapi/${ApiVersion}"
        Write-InfobloxLog "Connecting to Infoblox at $script:BaseUrl"
        
        # Store credential
        if ($Credential) {
            $script:Credential = $Credential
        }
        else {
            $script:Credential = Get-Credential -Message "Enter Infoblox credentials"
        }
        
        # Initialize web session
        $script:InfobloxSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        
        # Test connection with grid info request
        $params = @{
            Uri = "$script:BaseUrl/grid/session"
            Method = 'POST'
            Credential = $script:Credential
            SessionVariable = 'script:InfobloxSession'
            ErrorAction = 'Stop'
        }
        
        $response = Invoke-RestMethod @params
        Write-InfobloxLog "Successfully connected to Infoblox as $($script:Credential.UserName)" -Level "SUCCESS"
        
        # Return connection info
        return @{
            BaseUrl = $script:BaseUrl
            Username = $script:Credential.UserName
            Connected = $true
        }
    }
    catch {
        Write-InfobloxLog "Failed to connect to Infoblox: $_" -Level "ERROR"
        throw "Failed to connect to Infoblox: $_"
    }
}

function Disconnect-Infoblox {
    [CmdletBinding()]
    param()
    
    try {
        if ($script:BaseUrl -and $script:InfobloxSession) {
            Write-InfobloxLog "Disconnecting from Infoblox"
            
            $params = @{
                Uri = "$script:BaseUrl/grid/session"
                Method = 'DELETE'
                WebSession = $script:InfobloxSession
                ErrorAction = 'Stop'
            }
            
            $null = Invoke-RestMethod @params
            $script:InfobloxSession = $null
            Write-InfobloxLog "Successfully disconnected from Infoblox" -Level "SUCCESS"
            return $true
        }
        else {
            Write-InfobloxLog "No active Infoblox session to disconnect" -Level "WARNING"
            return $false
        }
    }
    catch {
        Write-InfobloxLog "Error disconnecting from Infoblox: $_" -Level "ERROR"
        return $false
    }
}

function Test-InfobloxConnection {
    [CmdletBinding()]
    param()
    
    if (-not $script:BaseUrl -or -not $script:InfobloxSession) {
        Write-InfobloxLog "No active Infoblox connection" -Level "WARNING"
        return $false
    }
    
    try {
        # Attempt to get grid info as a connection test
        $params = @{
            Uri = "$script:BaseUrl/grid"
            Method = 'GET'
            WebSession = $script:InfobloxSession
            ErrorAction = 'Stop'
        }
        
        $response = Invoke-RestMethod @params
        Write-InfobloxLog "Infoblox connection is active"
        return $true
    }
    catch {
        Write-InfobloxLog "Infoblox connection test failed: $_" -Level "ERROR"
        return $false
    }
}

#endregion

#region API Helper Functions

function Invoke-InfobloxRequest {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$EndpointUrl,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet('GET', 'POST', 'PUT', 'DELETE')]
        [string]$Method = 'GET',
        
        [Parameter(Mandatory=$false)]
        [object]$Body,
        
        [Parameter(Mandatory=$false)]
        [hashtable]$QueryParams,
        
        [Parameter(Mandatory=$false)]
        [switch]$ReturnRef
    )
    
    # Verify connection
    if (-not (Test-InfobloxConnection)) {
        throw "No active Infoblox connection. Please run Connect-Infoblox first."
    }
    
    # Build full URL
    $uri = "$script:BaseUrl/$EndpointUrl"
    
    # Add query parameters if specified
    if ($QueryParams -and $QueryParams.Count -gt 0) {
        $queryString = @()
        foreach ($key in $QueryParams.Keys) {
            $queryString += "$key=$([System.Web.HttpUtility]::UrlEncode($QueryParams[$key]))"
        }
        $uri += "?" + ($queryString -join "&")
    }
    
    Write-InfobloxLog "Sending $Method request to $uri"
    
    try {
        $params = @{
            Uri = $uri
            Method = $Method
            WebSession = $script:InfobloxSession
            ContentType = 'application/json'
            ErrorAction = 'Stop'
        }
        
        # Add body for POST and PUT requests
        if ($Method -in @('POST', 'PUT') -and $Body) {
            $jsonBody = if ($Body -is [string]) { $Body } else { $Body | ConvertTo-Json -Depth 10 }
            $params.Body = $jsonBody
            
            # Log the body (truncate if too long)
            $logBody = if ($jsonBody.Length -gt 500) { "$($jsonBody.Substring(0, 497))..." } else { $jsonBody }
            Write-InfobloxLog "Request body: $logBody"
        }
        
        $response = Invoke-RestMethod @params
        
        # Log response (truncate if too long)
        $responseJson = $response | ConvertTo-Json -Compress
        $logResponse = if ($responseJson.Length -gt 500) { "$($responseJson.Substring(0, 497))..." } else { $responseJson }
        Write-InfobloxLog "Response: $logResponse"
        
        # If ReturnRef is specified and response is a reference string, return it
        if ($ReturnRef -and $response -is [string] -and $response -match "^[a-zA-Z0-9_]+/[^:]+:.+$") {
            return $response
        }
        
        return $response
    }
    catch {
        $errorDetails = if ($_.ErrorDetails.Message) {
            try { $_.ErrorDetails.Message | ConvertFrom-Json } catch { $_.ErrorDetails.Message }
        } else {
            $_.Exception.Message
        }
        
        Write-InfobloxLog "Infoblox API request failed: $errorDetails" -Level "ERROR"
        throw "Infoblox API request failed: $errorDetails"
    }
}

function Format-InfobloxResult {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true, ValueFromPipeline=$true)]
        [object]$InputObject,
        
        [Parameter(Mandatory=$false)]
        [string]$Title
    )
    
    process {
        if ($Title) {
            Write-Host "`n$Title" -ForegroundColor Cyan
            Write-Host "=" * $Title.Length -ForegroundColor Cyan
        }
        
        if ($null -eq $InputObject) {
            Write-Host "No results found." -ForegroundColor Yellow
            return
        }
        
        if ($InputObject -is [string]) {
            # Handle reference strings
            if ($InputObject -match "^[a-zA-Z0-9_]+/[^:]+:.+$") {
                Write-Host "Reference: $InputObject" -ForegroundColor Green
            } else {
                Write-Host $InputObject
            }
            return
        }
        
        if ($InputObject -is [array]) {
            Write-Host "Found $($InputObject.Count) results:" -ForegroundColor Cyan
            
            foreach ($item in $InputObject) {
                if ($item -is [string]) {
                    Write-Host "- $item"
                } else {
                    $item | Format-List
                    Write-Host "------------------------"
                }
            }
            return
        }
        
        # Default to Format-List for objects
        $InputObject | Format-List
    }
}

#endregion

#region Validation Functions

function Test-InfobloxIPAddress {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$IPAddress
    )
    
    try {
        $ipObj = [System.Net.IPAddress]::Parse($IPAddress)
        Write-InfobloxLog "Validated IP address format: $IPAddress"
        return $true
    }
    catch {
        Write-InfobloxLog "Invalid IP address format: $IPAddress" -Level "ERROR"
        return $false
    }
}

function Test-InfobloxHostname {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Hostname
    )
    
    # RFC 1123 compliant hostname regex pattern
    $pattern = "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"
    
    $isValid = $Hostname -match $pattern
    
    if ($isValid) {
        Write-InfobloxLog "Validated hostname format: $Hostname"
    } else {
        Write-InfobloxLog "Invalid hostname format: $Hostname" -Level "ERROR"
    }
    
    return $isValid
}

function Test-InfobloxNetwork {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Network
    )
    
    try {
        # Split CIDR notation to extract IP and prefix
        $parts = $Network -split '/'
        
        # Validate IP address
        if (-not (Test-InfobloxIPAddress -IPAddress $parts[0])) {
            return $false
        }
        
        # Validate prefix length if present
        if ($parts.Count -gt 1) {
            $prefix = [int]$parts[1]
            if ($prefix -lt 0 -or $prefix -gt 32) {
                Write-InfobloxLog "Invalid network prefix: $prefix (must be between 0 and 32)" -Level "ERROR"
                return $false
            }
        }
        
        Write-InfobloxLog "Validated network format: $Network"
        return $true
    }
    catch {
        Write-InfobloxLog "Invalid network format: $Network" -Level "ERROR"
        return $false
    }
}

function Test-InfobloxMAC {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$MACAddress
    )
    
    # Accept formats: 00:11:22:33:44:55, 00-11-22-33-44-55, or 001122334455
    $pattern = '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$'
    
    $isValid = $MACAddress -match $pattern
    
    if ($isValid) {
        Write-InfobloxLog "Validated MAC address format: $MACAddress"
    } else {
        Write-InfobloxLog "Invalid MAC address format: $MACAddress" -Level "ERROR"
    }
    
    return $isValid
}

function Get-InfobloxHostRecord {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Hostname
    )
    
    try {
        $params = @{
            EndpointUrl = "record:host"
            QueryParams = @{
                "name" = $Hostname
            }
        }
        
        $result = Invoke-InfobloxRequest @params
        
        if ($result -and $result.Count -gt 0) {
            Write-InfobloxLog "Host record found for $Hostname" -Level "INFO"
            return $result
        }
        else {
            Write-InfobloxLog "No host record found for $Hostname" -Level "INFO"
            return $null
        }
    }
    catch {
        Write-InfobloxLog "Error checking host record: $_" -Level "ERROR"
        throw "Error checking host record: $_"
    }
}

function Get-InfobloxARecord {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Hostname
    )
    
    try {
        $params = @{
            EndpointUrl = "record:a"
            QueryParams = @{
                "name" = $Hostname
            }
        }
        
        $result = Invoke-InfobloxRequest @params
        
        if ($result -and $result.Count -gt 0) {
            Write-InfobloxLog "A record found for $Hostname" -Level "INFO"
            return $result
        }
        else {
            Write-InfobloxLog "No A record found for $Hostname" -Level "INFO"
            return $null
        }
    }
    catch {
        Write-InfobloxLog "Error checking A record: $_" -Level "ERROR"
        throw "Error checking A record: $_"
    }
}

function Get-InfobloxIPAddress {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$IPAddress
    )
    
    try {
        $params = @{
            EndpointUrl = "ipv4address"
            QueryParams = @{
                "ip_address" = $IPAddress
            }
        }
        
        $result = Invoke-InfobloxRequest @params
        
        if ($result -and $result.Count -gt 0 -and $result[0].status -eq "USED") {
            Write-InfobloxLog "IP address $IPAddress is already in use" -Level "INFO"
            return $result
        }
        else {
            Write-InfobloxLog "IP address $IPAddress is available" -Level "INFO"
            return $null
        }
    }
    catch {
        Write-InfobloxLog "Error checking IP address: $_" -Level "ERROR"
        throw "Error checking IP address: $_"
    }
}

function Get-InfobloxNetwork {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory=$true)]
        [string]$Network
    )
    
    try {
        $params = @{
            EndpointUrl = "network"
            QueryParams = @{
                "network" = $Network
            }
        }
        
        $result = Invoke-InfobloxRequest @params
        
        if ($result -and $result.Count -gt 0) {
            Write-InfobloxLog "Network $Network found" -Level "INFO"
            return $result[0]
        }
        else {
            Write-InfobloxLog "Network $Network not found" -Level "INFO"
            return $null
        }
    }
    catch {
        Write-InfobloxLog "Error checking network: $_" -Level "ERROR"
        throw "Error checking network: $_"
    }
}

#endregion

# Export module functions
Export-ModuleMember -Function @(
    'Initialize-InfobloxLogging',
    'Write-InfobloxLog',
    'Connect-Infoblox',
    'Disconnect-Infoblox',
    'Test-InfobloxConnection',
    'Invoke-InfobloxRequest',
    'Format-InfobloxResult',
    'Test-InfobloxIPAddress',
    'Test-InfobloxHostname',
    'Test-InfobloxNetwork',
    'Test-InfobloxMAC',
    'Get-InfobloxHostRecord',
    'Get-InfobloxARecord',
    'Get-InfobloxIPAddress',
    'Get-InfobloxNetwork'
)