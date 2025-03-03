import requests
import json
import argparse
import sys

class InfobloxClient:
    def __init__(self, base_url="http://localhost:8080/wapi/v2.11", username="admin", password="infoblox"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        
    def login(self):
        """Simulate login to Infoblox"""
        response = self.session.post(f"{self.base_url}/grid/session")
        if response.status_code == 200:
            print(f"Successfully logged in as {self.username}")
            return True
        else:
            print(f"Login failed: {response.text}")
            return False

    def logout(self):
        """Simulate logout from Infoblox"""
        response = self.session.delete(f"{self.base_url}/grid/session")
        if response.status_code == 204:
            print("Successfully logged out")
            return True
        else:
            print(f"Logout failed: {response.text}")
            return False
    
    def get_objects(self, obj_type, query_params=None, return_fields=None):
        """Get objects with specified query parameters"""
        params = query_params or {}
        if return_fields:
            params['_return_fields'] = ','.join(return_fields)
            
        response = self.session.get(f"{self.base_url}/{obj_type}", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting objects: {response.text}")
            return None
    
    def create_object(self, obj_type, data):
        """Create a new object"""
        response = self.session.post(f"{self.base_url}/{obj_type}", json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error creating object: {response.text}")
            return None
    
    def get_object(self, ref, return_fields=None):
        """Get a specific object by reference"""
        params = {}
        if return_fields:
            params['_return_fields'] = ','.join(return_fields)
            
        response = self.session.get(f"{self.base_url}/{ref}", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting object: {response.text}")
            return None
    
    def update_object(self, ref, data):
        """Update an existing object"""
        response = self.session.put(f"{self.base_url}/{ref}", json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error updating object: {response.text}")
            return None
    
    def delete_object(self, ref):
        """Delete an object"""
        response = self.session.delete(f"{self.base_url}/{ref}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error deleting object: {response.text}")
            return None
    
    def next_available_ip(self, network):
        """Get next available IP in a network"""
        response = self.session.post(f"{self.base_url}/network/{network}/next_available_ip")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting next available IP: {response.text}")
            return None
    
    def search_ip(self, ip_addr=None, network=None):
        """Search for an IP address or network"""
        params = {}
        if ip_addr:
            params['ip_address'] = ip_addr
        if network:
            params['network'] = network
            
        response = self.session.get(f"{self.base_url}/ipv4address", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error searching IP: {response.text}")
            return None
    
    def get_grid_info(self):
        """Get grid information"""
        response = self.session.get(f"{self.base_url}/grid")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting grid info: {response.text}")
            return None
    
    def get_members(self):
        """Get grid members"""
        response = self.session.get(f"{self.base_url}/member")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting members: {response.text}")
            return None

def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))

def main():
    parser = argparse.ArgumentParser(description='Infoblox API Client')
    parser.add_argument('--url', default='http://localhost:8080/wapi/v2.11', help='Infoblox API base URL')
    parser.add_argument('--username', default='admin', help='Username')
    parser.add_argument('--password', default='infoblox', help='Password')
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Get objects
    get_parser = subparsers.add_parser('get', help='Get objects')
    get_parser.add_argument('obj_type', help='Object type')
    get_parser.add_argument('--query', action='append', help='Query parameters (key=value)')
    get_parser.add_argument('--fields', help='Return fields (comma-separated)')
    
    # Create object
    create_parser = subparsers.add_parser('create', help='Create object')
    create_parser.add_argument('obj_type', help='Object type')
    create_parser.add_argument('--json_file', help='JSON file containing data')
    create_parser.add_argument('--data', help='JSON data string')
    create_group = create_parser.add_mutually_exclusive_group(required=True)
    create_group.add_argument('--network', help='Network (e.g., 192.168.1.0/24)')
    create_group.add_argument('--host', help='Hostname and IP (e.g., host.example.com:192.168.1.10)')
    create_group.add_argument('--a_record', help='A record name and IP (e.g., www.example.com:192.168.1.10)')
    create_group.add_argument('--ptr_record', help='PTR record IP and name (e.g., 192.168.1.10:host.example.com)')
    create_group.add_argument('--range', help='DHCP range (e.g., 192.168.1.100-192.168.1.200)')
    create_group.add_argument('--fixed_address', help='Fixed address MAC and IP (e.g., aa:bb:cc:dd:ee:ff:192.168.1.50)')
    create_group.add_argument('--json', help='Use JSON data from --data or --json_file', action='store_true')
    create_parser.add_argument('--comment', help='Comment for the object')
    
    # Get object by ref
    get_obj_parser = subparsers.add_parser('get_obj', help='Get object by reference')
    get_obj_parser.add_argument('ref', help='Object reference')
    get_obj_parser.add_argument('--fields', help='Return fields (comma-separated)')
    
    # Update object
    update_parser = subparsers.add_parser('update', help='Update object')
    update_parser.add_argument('ref', help='Object reference')
    update_parser.add_argument('--json_file', help='JSON file containing data')
    update_parser.add_argument('--data', help='JSON data string')
    update_parser.add_argument('--comment', help='Comment for the object')
    
    # Delete object
    delete_parser = subparsers.add_parser('delete', help='Delete object')
    delete_parser.add_argument('ref', help='Object reference')
    
    # Next available IP
    next_ip_parser = subparsers.add_parser('next_ip', help='Get next available IP')
    next_ip_parser.add_argument('network', help='Network')
    
    # Search IP
    search_ip_parser = subparsers.add_parser('search_ip', help='Search IP')
    search_ip_parser.add_argument('--ip', help='IP address')
    search_ip_parser.add_argument('--network', help='Network')
    
    # Grid info
    subparsers.add_parser('grid_info', help='Get grid info')
    
    # Members
    subparsers.add_parser('members', help='Get grid members')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    client = InfobloxClient(args.url, args.username, args.password)
    if not client.login():
        sys.exit(1)
    
    try:
        if args.command == 'get':
            query = {}
            if args.query:
                for q in args.query:
                    key, value = q.split('=', 1)
                    query[key] = value
                    
            fields = None
            if args.fields:
                fields = args.fields.split(',')
                
            result = client.get_objects(args.obj_type, query, fields)
            print_json(result)
            
        elif args.command == 'create':
            data = {}
            
            # Parse JSON data if provided
            if args.json:
                if args.json_file:
                    with open(args.json_file, 'r') as f:
                        data = json.load(f)
                elif args.data:
                    try:
                        data = json.loads(args.data)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON data: {e}")
                        sys.exit(1)
                else:
                    print("Either --json_file or --data must be provided with --json")
                    sys.exit(1)
            else:
                # Create data based on object type
                if args.network:
                    data = {
                        "network": args.network,
                        "comment": args.comment or f"Network {args.network}"
                    }
                    args.obj_type = "network"
                
                elif args.host:
                    parts = args.host.split(':')
                    if len(parts) != 2:
                        print("Host format should be 'hostname:ip'")
                        sys.exit(1)
                    
                    hostname, ip = parts
                    data = {
                        "name": hostname,
                        "ipv4addrs": [{"ipv4addr": ip}],
                        "comment": args.comment or f"Host {hostname}"
                    }
                    args.obj_type = "record:host"
                
                elif args.a_record:
                    parts = args.a_record.split(':')
                    if len(parts) != 2:
                        print("A record format should be 'name:ip'")
                        sys.exit(1)
                    
                    name, ip = parts
                    data = {
                        "name": name,
                        "ipv4addr": ip,
                        "comment": args.comment or f"A record {name}"
                    }
                    args.obj_type = "record:a"
                
                elif args.ptr_record:
                    parts = args.ptr_record.split(':')
                    if len(parts) != 2:
                        print("PTR record format should be 'ip:name'")
                        sys.exit(1)
                    
                    ip, name = parts
                    data = {
                        "ptrdname": name,
                        "ipv4addr": ip,
                        "comment": args.comment or f"PTR record {ip}"
                    }
                    args.obj_type = "record:ptr"
                
                elif args.range:
                    parts = args.range.split('-')
                    if len(parts) != 2:
                        print("Range format should be 'start-end'")
                        sys.exit(1)
                    
                    start, end = parts
                    data = {
                        "start_addr": start,
                        "end_addr": end,
                        "comment": args.comment or f"Range {start}-{end}"
                    }
                    args.obj_type = "range"
                
                elif args.fixed_address:
                    parts = args.fixed_address.split(':')
                    if len(parts) != 2:
                        print("Fixed address format should be 'mac:ip'")
                        sys.exit(1)
                    
                    mac, ip = parts
                    data = {
                        "mac": mac,
                        "ipv4addr": ip,
                        "comment": args.comment or f"Fixed address {ip}"
                    }
                    args.obj_type = "fixedaddress"
            
            print(f"Creating {args.obj_type} with data:")
            print_json(data)
            result = client.create_object(args.obj_type, data)
            print("Result:")
            print_json(result)
            
        elif args.command == 'get_obj':
            fields = None
            if args.fields:
                fields = args.fields.split(',')
                
            result = client.get_object(args.ref, fields)
            print_json(result)
            
        elif args.command == 'update':
            data = {}
            
            if args.json_file:
                with open(args.json_file, 'r') as f:
                    data = json.load(f)
            elif args.data:
                try:
                    data = json.loads(args.data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON data: {e}")
                    sys.exit(1)
            elif args.comment:
                data = {"comment": args.comment}
            else:
                print("Either --json_file, --data, or --comment must be provided")
                sys.exit(1)
            
            result = client.update_object(args.ref, data)
            print_json(result)
            
        elif args.command == 'delete':
            result = client.delete_object(args.ref)
            print_json(result)
            
        elif args.command == 'next_ip':
            result = client.next_available_ip(args.network)
            print_json(result)
            
        elif args.command == 'search_ip':
            result = client.search_ip(args.ip, args.network)
            print_json(result)
            
        elif args.command == 'grid_info':
            result = client.get_grid_info()
            print_json(result)
            
        elif args.command == 'members':
            result = client.get_members()
            print_json(result)
    
    finally:
        client.logout()

if __name__ == '__main__':
    main()