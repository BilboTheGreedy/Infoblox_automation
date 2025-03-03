.\Manage-InfobloxNetworks.ps1 -Action Create -Network "192.168.1.0/24" -Comment "Test Network" -Verbose -Credential $cred

.\Manage-InfobloxDnsRecords.ps1 -Action Search -RecordType Host -Verbose -Credential $cred
.\Manage-InfobloxDnsRecords.ps1 -Action Create -RecordType Host -Hostname "server1.example.com" -IPAddress "192.168.1.20" -Comment "Application Server" -Verbose -Credential $cred

.\Manage-InfobloxNetworks.ps1 -Action Create -Network "192.168.1.0/24" -Comment "Test Network" -Verbose -Credential $cred
.\Manage-InfobloxIPAddresses.ps1 -Action NextAvailable -Network "192.168.1.0/24" -Verbose -Credential $cred


.\Manage-InfobloxIPAddresses.ps1 -Action Search -IPAddress "192.168.1.10" -Verbose -Credential $cred

# Prompt for DNS record creation
.\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.51" -MACAddress "00:11:22:33:44:88" -Hostname "printerr.example.com" -Comment "Network Printer" -Verbose -Credential $cred 

# Auto create record
.\Manage-InfobloxIPAddresses.ps1 -Action Reserve -IPAddress "192.168.1.51" -MACAddress "00:11:22:33:44:88" -Hostname "printerr.example.com" -Comment "Network Printer" -Verbose -Credential $cred -CreateDNS $True