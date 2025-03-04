"""
Database initialization for the Infoblox Mock Server.
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def initialize_db(db):
    """Initialize the database with default data"""
    # Initialize the structure
    for obj_type in [
        "network", "network_container", "record:host", "record:a", 
        "record:ptr", "record:cname", "record:mx", "record:srv", 
        "record:txt", "range", "lease", "fixedaddress"
    ]:
        if obj_type not in db:
            db[obj_type] = []
    
    # Initialize grid and member data if not present
    if "grid" not in db:
        db["grid"] = [{
            "_ref": "grid/1",
            "name": "Infoblox Mock Grid",
            "version": "NIOS 8.6.0",
            "status": "ONLINE",
            "license_type": "ENTERPRISE",
            "allow_recursive_deletion": True,
            "support_email": "support@example.com",
            "restart_status": {
                "restart_required": False
            }
        }]
    
    if "member" not in db:
        db["member"] = [{
            "_ref": "member/1",
            "host_name": "infoblox.example.com",
            "config_addr_type": "IPV4",
            "platform": "PHYSICAL",
            "service_status": "WORKING",
            "node_status": "ONLINE",
            "ha_status": "ACTIVE",
            "ip_address": "192.168.1.2"
        }]
    
    if "activeuser" not in db:
        db["activeuser"] = {}
    
    # Add a network container if none exists
    if not db["network_container"]:
        db["network_container"].append({
            "_ref": f"networkcontainer/ZG5zLm5ldHdvcmtfY29udGFpbmVyJDEwLjAuMC4wLzg:10.0.0.0/8",
            "network": "10.0.0.0/8",
            "network_view": "default",
            "comment": "Default network container",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    # Add default networks if none exist
    if not db["network"]:
        db["network"].append({
            "_ref": f"network/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:10.10.10.0/24",
            "network": "10.10.10.0/24",
            "network_view": "default",
            "comment": "Development network",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
        
        db["network"].append({
            "_ref": f"network/ZG5zLm5ldHdvcmskMTkyLjE2OC4xLjAvMjQ:192.168.1.0/24",
            "network": "192.168.1.0/24",
            "network_view": "default",
            "comment": "Management network",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    # Add a DHCP range if none exists
    if not db["range"]:
        db["range"].append({
            "_ref": f"range/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:10.10.10.100-10.10.10.200",
            "network": "10.10.10.0/24",
            "network_view": "default",
            "start_addr": "10.10.10.100",
            "end_addr": "10.10.10.200",
            "comment": "DHCP range for development",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    # Add some host records if none exist
    if not db["record:host"]:
        db["record:host"].append({
            "_ref": f"record:host/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:server1.example.com",
            "name": "server1.example.com",
            "view": "default",
            "ipv4addrs": [{"ipv4addr": "10.10.10.5"}],
            "comment": "Application server",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    # Add some A records if none exist
    if not db["record:a"]:
        db["record:a"].append({
            "_ref": f"record:a/ZG5zLm5ldHdvcmskMTAuMTAuMTAuMC8yNA:www.example.com",
            "name": "www.example.com",
            "view": "default",
            "ipv4addr": "10.10.10.6",
            "comment": "Web server",
            "extattrs": {},
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        })
    
    logger.info("Database initialized with default data")