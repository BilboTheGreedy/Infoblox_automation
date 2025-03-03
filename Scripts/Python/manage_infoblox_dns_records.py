#!/usr/bin/env python3
"""
Manages Infoblox DNS records - create, search, update, and delete A and Host records.

This script provides functions to create, search, update, and delete Infoblox DNS A and Host records.
It includes thorough validation, error handling, detailed logging, and verification of existing records.

Prerequisite: infoblox_common.py module
"""

import os
import sys
import argparse
import infoblox_common as iblox

def main():
    """Main function to process command line arguments and execute requested action"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Manage Infoblox DNS records')
    
    # Required arguments
    parser.add_argument('--action', required=True, choices=['Search', 'Create', 'Delete', 'Update'],
                        help='Action to perform')
    parser.add_argument('--record-type', required=True, choices=['A', 'Host'],
                        help='Type of DNS record')
    
    # Optional arguments
    parser.add_argument('--hostname', help='Hostname for the DNS record')
    parser.add_argument('--ip-address', help='IP address for the DNS record')
    parser.add_argument('--comment', help='Comment for the DNS record')
    parser.add_argument('--force', action='store_true', help='Force operation even if conflicts exist')
    parser.add_argument('--server', default='localhost', help='Infoblox server hostname or IP')
    parser.add_argument('--port', type=int, default=8080, help='Infoblox server port')
    parser.add_argument('--use-ssl', action='store_true', help='Use SSL for Infoblox connection')
    parser.add_argument('--username', help='Infoblox username')
    parser.add_argument('--password', help='Infoblox password')
    parser.add_argument('--log-file', help='Path to log file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Initialize logging
    log_file_path = args.log_file if args.log_file else os.path.join(os.path.dirname(os.path.abspath(__file__)), "InfobloxDnsRecords.log")
    iblox.initialize_infoblox_logging(log_file_path=log_file_path, verbose_logging=args.verbose)
    
    # Script start
    iblox.write_infoblox_log("======= Infoblox DNS Record Management Script Started =======", "INFO")
    iblox.write_infoblox_log(f"Action: {args.action}, RecordType: {args.record_type}", "INFO")
    
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
            search_records(args)
        elif args.action == 'Create':
            create_record(args)
        elif args.action == 'Update':
            update_record(args)
        elif args.action == 'Delete':
            delete_record(args)
    
    except Exception as e:
        iblox.write_infoblox_log(f"ERROR: {str(e)}", "ERROR")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        # Disconnect from Infoblox
        if iblox.test_infoblox_connection():
            iblox.disconnect_infoblox()
        
        iblox.write_infoblox_log("======= Infoblox DNS Record Management Script Completed =======", "INFO")

def search_records(args):
    """
    Search for DNS records
    
    Args:
        args: Command line arguments
    """
    iblox.write_infoblox_log(f"Searching for {args.record_type} records", "INFO")
    
    search_params = {
        "endpoint_url": f"record:{args.record_type.lower()}"
    }
    
    # Apply hostname filter if specified
    if args.hostname:
        search_params["query_params"] = {"name": args.hostname}
        iblox.write_infoblox_log(f"Filtering by hostname: {args.hostname}", "INFO")
    
    records = iblox.invoke_infoblox_request(**search_params)
    
    if records and len(records) > 0:
        iblox.write_infoblox_log(f"Found {len(records)} {args.record_type} records", "SUCCESS")
        iblox.format_infoblox_result(records, f"{args.record_type} Records")
    else:
        iblox.write_infoblox_log(f"No {args.record_type} records found matching the criteria", "WARNING")

def create_record(args):
    """
    Create a new DNS record
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate required parameters
    if not args.hostname:
        raise Exception("Hostname parameter is required for Create action")
    
    if not args.ip_address:
        raise Exception("IP address parameter is required for Create action")
    
    iblox.write_infoblox_log(f"Creating {args.record_type} record: {args.hostname} -> {args.ip_address}", "INFO")
    
    # Validate hostname format
    if not iblox.test_infoblox_hostname(args.hostname):
        raise Exception(f"Invalid hostname format: {args.hostname}")
    
    # Validate IP address format
    if not iblox.test_infoblox_ip_address(args.ip_address):
        raise Exception(f"Invalid IP address format: {args.ip_address}")
    
    # Check for existing DNS records with same hostname (both A and Host records)
    existing_a_record = iblox.get_infoblox_a_record(args.hostname)
    existing_host_record = iblox.get_infoblox_host_record(args.hostname)
    
    if existing_a_record or existing_host_record:
        existing_record_type = "A" if existing_a_record else "Host"
        existing_record_ref = existing_a_record[0]["_ref"] if existing_a_record else existing_host_record[0]["_ref"]
        existing_record_ip = existing_a_record[0]["ipv4addr"] if existing_a_record else existing_host_record[0]["ipv4addrs"][0]["ipv4addr"]
        
        if not args.force:
            raise Exception(f"Hostname {args.hostname} already exists as {existing_record_type} record ({existing_record_ref}) with IP: {existing_record_ip}. Use --force to override.")
        
        iblox.write_infoblox_log(f"WARNING: Hostname {args.hostname} already exists as {existing_record_type} record. Proceeding due to --force flag.", "WARNING")
    
    # Check if IP address is already in use
    existing_ip = iblox.get_infoblox_ip_address(args.ip_address)
    if existing_ip and not args.force:
        existing_objects = ", ".join(existing_ip[0].get("objects", []))
        raise Exception(f"IP address {args.ip_address} is already in use by: {existing_objects}. Use --force to override.")
    elif existing_ip:
        iblox.write_infoblox_log(f"WARNING: IP address {args.ip_address} is already in use. Proceeding due to --force flag.", "WARNING")
    
    # Prepare record data based on type
    if args.record_type == "A":
        record_data = {
            "name": args.hostname,
            "ipv4addr": args.ip_address,
            "view": "default"
        }
        
        if args.comment:
            record_data["comment"] = args.comment
        
        # Create the A record
        create_params = {
            "endpoint_url": "record:a",
            "method": "POST",
            "body": record_data,
            "return_ref": True
        }
        
        result = iblox.invoke_infoblox_request(**create_params)
        
        iblox.write_infoblox_log(f"A record {args.hostname} -> {args.ip_address} created successfully with reference {result}", "SUCCESS")
        iblox.format_infoblox_result(result, "A Record Created")
    
    elif args.record_type == "Host":
        record_data = {
            "name": args.hostname,
            "ipv4addrs": [
                {
                    "ipv4addr": args.ip_address
                }
            ],
            "view": "default"
        }
        
        if args.comment:
            record_data["comment"] = args.comment
        
        # Create the Host record
        create_params = {
            "endpoint_url": "record:host",
            "method": "POST",
            "body": record_data,
            "return_ref": True
        }
        
        result = iblox.invoke_infoblox_request(**create_params)
        
        iblox.write_infoblox_log(f"Host record {args.hostname} -> {args.ip_address} created successfully with reference {result}", "SUCCESS")
        iblox.format_infoblox_result(result, "Host Record Created")

def update_record(args):
    """
    Update an existing DNS record
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate required parameters
    if not args.hostname:
        raise Exception("Hostname parameter is required for Update action")
    
    iblox.write_infoblox_log(f"Updating {args.record_type} record: {args.hostname}", "INFO")
    
    # Get existing record
    existing_record = None
    if args.record_type == "A":
        existing_record = iblox.get_infoblox_a_record(args.hostname)
    else:
        existing_record = iblox.get_infoblox_host_record(args.hostname)
    
    if not existing_record:
        raise Exception(f"{args.record_type} record for {args.hostname} does not exist")
    
    # Prepare update data
    update_data = {}
    
    if args.ip_address:
        iblox.write_infoblox_log(f"Updating IP address to: {args.ip_address}", "INFO")
        
        # Validate IP address format
        if not iblox.test_infoblox_ip_address(args.ip_address):
            raise Exception(f"Invalid IP address format: {args.ip_address}")
        
        # Check if IP address is already in use by another record
        existing_ip = iblox.get_infoblox_ip_address(args.ip_address)
        if existing_ip and not args.force:
            existing_objects = ", ".join(existing_ip[0].get("objects", []))
            if existing_record[0]["_ref"] not in existing_objects:
                raise Exception(f"IP address {args.ip_address} is already in use by: {existing_objects}. Use --force to override.")
        elif existing_ip and args.force:
            iblox.write_infoblox_log(f"WARNING: IP address {args.ip_address} is already in use. Proceeding due to --force flag.", "WARNING")
        
        if args.record_type == "A":
            update_data["ipv4addr"] = args.ip_address
        else:
            update_data["ipv4addrs"] = [
                {
                    "ipv4addr": args.ip_address
                }
            ]
    
    if args.comment:
        update_data["comment"] = args.comment
        iblox.write_infoblox_log(f"Updating comment to: {args.comment}", "INFO")
    
    if not update_data:
        raise Exception("No updates specified. Please provide at least one field to update.")
    
    # Update the record
    update_params = {
        "endpoint_url": existing_record[0]["_ref"],
        "method": "PUT",
        "body": update_data,
        "return_ref": True
    }
    
    result = iblox.invoke_infoblox_request(**update_params)
    
    iblox.write_infoblox_log(f"{args.record_type} record {args.hostname} updated successfully", "SUCCESS")
    iblox.format_infoblox_result(result, f"{args.record_type} Record Updated")

def delete_record(args):
    """
    Delete a DNS record
    
    Args:
        args: Command line arguments
    
    Raises:
        Exception: If required parameters are missing or validation fails
    """
    # Validate required parameters
    if not args.hostname:
        raise Exception("Hostname parameter is required for Delete action")
    
    iblox.write_infoblox_log(f"Deleting {args.record_type} record: {args.hostname}", "INFO")
    
    # Get existing record
    existing_record = None
    if args.record_type == "A":
        existing_record = iblox.get_infoblox_a_record(args.hostname)
    else:
        existing_record = iblox.get_infoblox_host_record(args.hostname)
    
    if not existing_record:
        raise Exception(f"{args.record_type} record for {args.hostname} does not exist")
    
    # Confirm deletion
    print(f"\033[93mAre you sure you want to delete {args.record_type} record {args.hostname} ({existing_record[0]['_ref']})? (Y/N)\033[0m")
    confirmation = input()
    
    if confirmation != "Y":
        iblox.write_infoblox_log(f"{args.record_type} record deletion cancelled by user", "WARNING")
        return
    
    # Delete the record
    delete_params = {
        "endpoint_url": existing_record[0]["_ref"],
        "method": "DELETE",
        "return_ref": True
    }
    
    result = iblox.invoke_infoblox_request(**delete_params)
    
    iblox.write_infoblox_log(f"{args.record_type} record {args.hostname} deleted successfully", "SUCCESS")
    iblox.format_infoblox_result(result, f"{args.record_type} Record Deleted")

if __name__ == "__main__":
    main()