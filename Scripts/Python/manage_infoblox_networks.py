#!/usr/bin/env python3
"""
Manages Infoblox networks - create, search, and manage network objects.

This script provides functions to create, search, and manage Infoblox network objects.
It includes thorough validation, error handling, and detailed logging.

Prerequisite: infoblox_common.py module
"""

import os
import sys
import argparse
import infoblox_common as iblox

def main():
    """Main function to process command line arguments and execute requested action"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Manage Infoblox networks')
    
    # Required arguments
    parser.add_argument('--action', required=True, choices=['Search', 'Create', 'Delete', 'Update'],
                        help='Action to perform')
    
    # Optional arguments
    parser.add_argument('--network', help='Network in CIDR notation (e.g., 192.168.1.0/24)')
    parser.add_argument('--comment', help='Comment for the network')
    parser.add_argument('--server', default='localhost', help='Infoblox server hostname or IP')
    parser.add_argument('--port', type=int, default=8080, help='Infoblox server port')
    parser.add_argument('--use-ssl', action='store_true', help='Use SSL for Infoblox connection')
    parser.add_argument('--username', help='Infoblox username')
    parser.add_argument('--password', help='Infoblox password')
    parser.add_argument('--log-file', help='Path to log file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Initialize logging
    log_file_path = args.log_file if args.log_file else os.path.join(os.path.dirname(os.path.abspath(__file__)), "InfobloxNetworks.log")
    iblox.initialize_infoblox_logging(log_file_path=log_file_path, verbose_logging_param=args.verbose)
    
    # Script start
    iblox.write_infoblox_log("======= Infoblox Network Management Script Started =======", "INFO")
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
            search_networks(args)
        elif args.action == 'Create':
            create_network(args)
        elif args.action == 'Update':
            update_network(args)
        elif args.action == 'Delete':
            delete_network(args)
    
    except Exception as e:
        iblox.write_infoblox_log(f"ERROR: {str(e)}", "ERROR")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        # Disconnect from Infoblox
        if iblox.test_infoblox_connection():
            iblox.disconnect_infoblox()
        
        iblox.write_infoblox_log("======= Infoblox Network Management Script Completed =======", "INFO")

def search_networks(args):
    """
    Search for networks
    
    Args:
        args: Command line arguments
    """
    iblox.write_infoblox_log("Searching for networks", "INFO")
    
    search_params = {
        "endpoint_url": "network",
        "query_params": {
            "_return_fields": "network,comment,network_view,extattrs"
        }
    }
    
    # Apply network filter if specified
    if args.network:
        search_params["query_params"]["network"] = args.network
        iblox.write_infoblox_log(f"Filtering by network: {args.network}", "INFO")
    
    networks = iblox.invoke_infoblox_request(**search_params)
    
    if networks and len(networks) > 0:
        iblox.write_infoblox_log(f"Found {len(networks)} networks", "SUCCESS")
        iblox.format_infoblox_result(networks, "Networks")
    else:
        iblox.write_infoblox_log("No networks found matching the criteria", "WARNING")

def create_network(args):
    """
    Create a new network
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate required parameters
    if not args.network:
        raise Exception("Network parameter is required for Create action")
    
    iblox.write_infoblox_log(f"Creating network: {args.network}", "INFO")
    
    # Validate network format
    if not iblox.test_infoblox_network(args.network):
        raise Exception(f"Invalid network format: {args.network}")
    
    # Check if network already exists
    existing_network = iblox.get_infoblox_network(args.network)
    if existing_network:
        raise Exception(f"Network {args.network} already exists with reference {existing_network['_ref']}")
    
    # Prepare network data
    network_data = {
        "network": args.network,
        "network_view": "default"
    }
    
    if args.comment:
        network_data["comment"] = args.comment
    
    # Create the network
    create_params = {
        "endpoint_url": "network",
        "method": "POST",
        "body": network_data,
        "return_ref": True
    }
    
    result = iblox.invoke_infoblox_request(**create_params)
    
    iblox.write_infoblox_log(f"Network {args.network} created successfully with reference {result}", "SUCCESS")
    iblox.format_infoblox_result(result, "Network Created")

def update_network(args):
    """
    Update an existing network
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate required parameters
    if not args.network:
        raise Exception("Network parameter is required for Update action")
    
    iblox.write_infoblox_log(f"Updating network: {args.network}", "INFO")
    
    # Check if network exists
    existing_network = iblox.get_infoblox_network(args.network)
    if not existing_network:
        raise Exception(f"Network {args.network} does not exist")
    
    # Prepare update data
    update_data = {}
    
    if args.comment:
        update_data["comment"] = args.comment
        iblox.write_infoblox_log(f"Updating comment to: {args.comment}", "INFO")
    
    if not update_data:
        raise Exception("No updates specified. Please provide at least one field to update.")
    
    # Update the network
    update_params = {
        "endpoint_url": existing_network["_ref"],
        "method": "PUT",
        "body": update_data,
        "return_ref": True
    }
    
    result = iblox.invoke_infoblox_request(**update_params)
    
    iblox.write_infoblox_log(f"Network {args.network} updated successfully", "SUCCESS")
    iblox.format_infoblox_result(result, "Network Updated")

def delete_network(args):
    """
    Delete a network
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate required parameters
    if not args.network:
        raise Exception("Network parameter is required for Delete action")
    
    iblox.write_infoblox_log(f"Deleting network: {args.network}", "INFO")
    
    # Check if network exists
    existing_network = iblox.get_infoblox_network(args.network)
    if not existing_network:
        raise Exception(f"Network {args.network} does not exist")
    
    # Confirm deletion
    print(f"\033[93mAre you sure you want to delete network {args.network} ({existing_network['_ref']})? (Y/N)\033[0m")
    confirmation = input()
    
    if confirmation != "Y":
        iblox.write_infoblox_log("Network deletion cancelled by user", "WARNING")
        return
    
    # Delete the network
    delete_params = {
        "endpoint_url": existing_network["_ref"],
        "method": "DELETE",
        "return_ref": True
    }
    
    result = iblox.invoke_infoblox_request(**delete_params)
    
    iblox.write_infoblox_log(f"Network {args.network} deleted successfully", "SUCCESS")
    iblox.format_infoblox_result(result, "Network Deleted")

if __name__ == "__main__":
    main()