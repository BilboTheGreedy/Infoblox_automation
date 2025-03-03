#!/usr/bin/env python3
"""
Manages IP addresses in Infoblox - search, reserve, and find next available.

This script provides functions to search for IP addresses, get next available IP from a network,
and reserve fixed addresses. It includes thorough validation, error handling, and detailed logging.

Prerequisite: infoblox_common.py module
"""

import os
import sys
import argparse
import infoblox_common as iblox

def main():
    """Main function to process command line arguments and execute requested action"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Manage Infoblox IP addresses')
    
    # Required arguments
    parser.add_argument('--action', required=True, choices=['Search', 'NextAvailable', 'Reserve'],
                        help='Action to perform')
    
    # Optional arguments
    parser.add_argument('--ip-address', help='IP address to search or reserve')
    parser.add_argument('--network', help='Network to search or find next available IP in')
    parser.add_argument('--mac-address', help='MAC address for fixed address reservation')
    parser.add_argument('--hostname', help='Hostname to associate with the fixed address')
    parser.add_argument('--comment', help='Comment for the fixed address')
    parser.add_argument('--force', action='store_true', help='Force operation even if conflicts exist')
    parser.add_argument('--server', default='localhost', help='Infoblox server hostname or IP')
    parser.add_argument('--port', type=int, default=8080, help='Infoblox server port')
    parser.add_argument('--use-ssl', action='store_true', help='Use SSL for Infoblox connection')
    parser.add_argument('--username', help='Infoblox username')
    parser.add_argument('--password', help='Infoblox password')
    parser.add_argument('--log-file', help='Path to log file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--create-dns', action='store_true', help='Automatically create DNS record for hostname')
    
    args = parser.parse_args()
    
    # Initialize logging
    log_file_path = args.log_file if args.log_file else os.path.join(os.path.dirname(os.path.abspath(__file__)), "InfobloxIPAddresses.log")
    iblox.initialize_infoblox_logging(log_file_path=log_file_path, verbose_logging=args.verbose)
    
    # Script start
    iblox.write_infoblox_log("======= Infoblox IP Address Management Script Started =======", "INFO")
    iblox.write_infoblox_log(f"Action: {args.action}", "INFO")
    
    try:
        # Connect to Infoblox
        connection_params = {
            "server": args.server,
            "port": args.port,
            "use_ssl": args.use_ssl
        }
        
        # Add credentials if provided
        if args.username and args.password:
            connection_params["credentials"] = (args.username, args.password)
        
        # Connect to Infoblox
        connection = iblox.connect_infoblox(**connection_params)
        iblox.write_infoblox_log(f"Connected to {connection['BaseUrl']} as {connection['Username']}", "SUCCESS")
        
        # Perform the requested action
        if args.action == 'Search':
            search_ip_address(args)
        elif args.action == 'NextAvailable':
            find_next_available_ip(args)
        elif args.action == 'Reserve':
            reserve_ip_address(args)
    
    except Exception as e:
        iblox.write_infoblox_log(f"ERROR: {str(e)}", "ERROR")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        # Disconnect from Infoblox
        if iblox.test_infoblox_connection():
            iblox.disconnect_infoblox()
        
        iblox.write_infoblox_log("======= Infoblox IP Address Management Script Completed =======", "INFO")

def search_ip_address(args):
    """
    Search for IP address information
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate parameters
    if not args.ip_address and not args.network:
        raise Exception("Either --ip-address or --network parameter is required for Search action")
    
    if args.ip_address:
        iblox.write_infoblox_log(f"Searching for IP address: {args.ip_address}", "INFO")
        
        # Validate IP address format
        if not iblox.test_infoblox_ip_address(args.ip_address):
            raise Exception(f"Invalid IP address format: {args.ip_address}")
        
        search_params = {
            "endpoint_url": "ipv4address",
            "query_params": {
                "ip_address": args.ip_address
            }
        }
        
        results = iblox.invoke_infoblox_request(**search_params)
        
        if results and len(results) > 0:
            iblox.write_infoblox_log(f"Found information for IP address {args.ip_address}", "SUCCESS")
            
            # Enhance results with detailed information
            for result in results:
                if result.get("objects") and len(result["objects"]) > 0:
                    result["Status"] = "USED"
                    
                    # Get detailed information for each object
                    object_details = []
                    for obj_ref in result["objects"]:
                        try:
                            detail_params = {
                                "endpoint_url": obj_ref
                            }
                            
                            detail = iblox.invoke_infoblox_request(**detail_params)
                            object_details.append(detail)
                        except Exception as e:
                            iblox.write_infoblox_log(f"Warning: Could not get details for object {obj_ref}", "WARNING")
                    
                    result["ObjectDetails"] = object_details
                else:
                    result["Status"] = "UNUSED"
            
            iblox.format_infoblox_result(results, "IP Address Information")
        else:
            iblox.write_infoblox_log(f"No information found for IP address {args.ip_address}", "WARNING")
    
    if args.network:
        iblox.write_infoblox_log(f"Searching for network: {args.network}", "INFO")
        
        # Validate network format
        if not iblox.test_infoblox_network(args.network):
            raise Exception(f"Invalid network format: {args.network}")
        
        search_params = {
            "endpoint_url": "ipv4address",
            "query_params": {
                "network": args.network
            }
        }
        
        results = iblox.invoke_infoblox_request(**search_params)
        
        if results and len(results) > 0:
            iblox.write_infoblox_log(f"Found {len(results)} IP addresses in network {args.network}", "SUCCESS")
            
            # Group results by status
            used_ips = [ip for ip in results if ip.get("status") == "USED"]
            unused_ips = [ip for ip in results if ip.get("status") == "UNUSED"]
            
            print(f"\n\033[96mNetwork: {args.network}\033[0m")
            print(f"\033[96mTotal IPs: {len(results)}\033[0m")
            print(f"\033[93mUsed IPs: {len(used_ips)}\033[0m")
            print(f"\033[92mUnused IPs: {len(unused_ips)}\033[0m")
            print("\n\033[96mIP Usage Details:\033[0m")
            
            iblox.format_infoblox_result(results, "Network IP Usage")
        else:
            iblox.write_infoblox_log(f"No information found for network {args.network}", "WARNING")

def find_next_available_ip(args):
    """
    Find the next available IP address in a network
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    
    Returns:
        str: Next available IP address
    """
    # Validate parameters
    if not args.network:
        raise Exception("Network parameter is required for NextAvailable action")
    
    iblox.write_infoblox_log(f"Finding next available IP address in network: {args.network}", "INFO")
    
    # Validate network format
    if not iblox.test_infoblox_network(args.network):
        raise Exception(f"Invalid network format: {args.network}")
    
    # Check if network exists
    existing_network = iblox.get_infoblox_network(args.network)
    if not existing_network:
        raise Exception(f"Network {args.network} does not exist")
    
    # Get next available IP
    next_ip_params = {
        "endpoint_url": f"network/{args.network}/next_available_ip",
        "method": "POST"
    }
    
    result = iblox.invoke_infoblox_request(**next_ip_params)
    
    if result and result.get("ips") and len(result["ips"]) > 0:
        next_ip = result["ips"][0]
        iblox.write_infoblox_log(f"Next available IP address in network {args.network}: {next_ip}", "SUCCESS")
        
        print(f"\n\033[96mNext Available IP\033[0m")
        print("\033[96m================\033[0m")
        print(f"\033[96mNetwork: {args.network}\033[0m")
        print(f"\033[92mIP Address: {next_ip}\033[0m")
        
        # Return the IP address for potential further use
        return next_ip
    else:
        iblox.write_infoblox_log(f"No available IP addresses found in network {args.network}", "WARNING")
        return None

def reserve_ip_address(args):
    """
    Reserve an IP address as a fixed address
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate parameters
    if not args.ip_address:
        raise Exception("IP address parameter is required for Reserve action")
    
    if not args.mac_address:
        raise Exception("MAC address parameter is required for Reserve action")
    
    iblox.write_infoblox_log(f"Reserving IP address {args.ip_address} with MAC address {args.mac_address}", "INFO")
    
    # Validate IP address format
    if not iblox.test_infoblox_ip_address(args.ip_address):
        raise Exception(f"Invalid IP address format: {args.ip_address}")
    
    # Validate MAC address format
    if not iblox.test_infoblox_mac(args.mac_address):
        raise Exception(f"Invalid MAC address format: {args.mac_address}")
    
    # Check if IP is already in use
    existing_ip = iblox.get_infoblox_ip_address(args.ip_address)
    if existing_ip and not args.force:
        existing_objects = ", ".join(existing_ip[0].get("objects", []))
        raise Exception(f"IP address {args.ip_address} is already in use by: {existing_objects}. Use --force to override.")
    elif existing_ip:
        iblox.write_infoblox_log(f"WARNING: IP address {args.ip_address} is already in use. Proceeding due to --force flag.", "WARNING")
    
    # If hostname is provided, check if it already exists in DNS
    if args.hostname:
        iblox.write_infoblox_log(f"Checking if hostname {args.hostname} already exists", "INFO")
        
        # Validate hostname format
        if not iblox.test_infoblox_hostname(args.hostname):
            raise Exception(f"Invalid hostname format: {args.hostname}")
        
        existing_a_record = iblox.get_infoblox_a_record(args.hostname)
        existing_host_record = iblox.get_infoblox_host_record(args.hostname)
        
        if existing_a_record or existing_host_record:
            existing_record_type = "A" if existing_a_record else "Host"
            existing_record_ref = existing_a_record[0]["_ref"] if existing_a_record else existing_host_record[0]["_ref"]
            existing_record_ip = existing_a_record[0]["ipv4addr"] if existing_a_record else existing_host_record[0]["ipv4addrs"][0]["ipv4addr"]
            
            if not args.force:
                raise Exception(f"Hostname {args.hostname} already exists as {existing_record_type} record ({existing_record_ref}) with IP: {existing_record_ip}. Use --force to override.")
            
            iblox.write_infoblox_log(f"WARNING: Hostname {args.hostname} already exists as {existing_record_type} record. Proceeding due to --force flag.", "WARNING")
    
    # Prepare fixed address data
    fixed_address_data = {
        "ipv4addr": args.ip_address,
        "mac": args.mac_address
    }
    
    if args.hostname:
        iblox.write_infoblox_log(f"Setting hostname for fixed address: {args.hostname}", "INFO")
        fixed_address_data["name"] = args.hostname
    
    if args.comment:
        fixed_address_data["comment"] = args.comment
    
    # Create the fixed address
    create_params = {
        "endpoint_url": "fixedaddress",
        "method": "POST",
        "body": fixed_address_data,
        "return_ref": True
    }
    
    result = iblox.invoke_infoblox_request(**create_params)
    
    iblox.write_infoblox_log(f"IP address {args.ip_address} reserved successfully with MAC {args.mac_address}", "SUCCESS")
    iblox.format_infoblox_result(result, "IP Address Reserved")
    
    # If hostname is provided and no DNS record exists, check if we should create DNS record
    if args.hostname and not existing_a_record and not existing_host_record:
        create_dns_record = False
        
        if args.create_dns:
            # Automatically create DNS record if --create-dns parameter is specified
            create_dns_record = True
            iblox.write_infoblox_log("Automatically creating DNS record due to --create-dns parameter", "INFO")
        else:
            # Ask user if they want to create a DNS record
            print(f"\n\033[93mWould you like to create a DNS record for {args.hostname} with IP {args.ip_address}? (Y/N)\033[0m")
            response = input()
            create_dns_record = (response == "Y")
        
        if create_dns_record:
            iblox.write_infoblox_log(f"Creating Host record for {args.hostname} with IP {args.ip_address}", "INFO")
            
            # Create Host record
            host_data = {
                "name": args.hostname,
                "ipv4addrs": [
                    {
                        "ipv4addr": args.ip_address
                    }
                ],
                "view": "default"
            }
            
            if args.comment:
                host_data["comment"] = args.comment
            
            create_host_params = {
                "endpoint_url": "record:host",
                "method": "POST",
                "body": host_data,
                "return_ref": True
            }
            
            host_result = iblox.invoke_infoblox_request(**create_host_params)
            
            iblox.write_infoblox_log(f"Host record {args.hostname} -> {args.ip_address} created successfully with reference {host_result}", "SUCCESS")
            iblox.format_infoblox_result(host_result, "Host Record Created")

if __name__ == "__main__":
    main()