"""
Reporting and analytics features for Infoblox Mock Server
Implements IPAM utilization reports, audit logs, threat analytics, and search functionality
"""

import logging
import json
import random
import ipaddress
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Reporting data structures
ipam_utilization = {}
dns_statistics = {}
dhcp_statistics = {}
audit_logs = []
threat_analytics = {}
search_results = {}
smart_folders = {}

class IPAMReportManager:
    """Manager for IPAM utilization reports"""
    
    @staticmethod
    def generate_network_utilization_report(network=None, network_view="default"):
        """Generate a network utilization report"""
        from infoblox_mock.db import db
        
        # Create results container
        results = {
            "report_id": f"ipam_util_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "report_time": datetime.now().isoformat(),
            "networks": [],
            "summary": {
                "total_networks": 0,
                "total_ips": 0,
                "used_ips": 0,
                "available_ips": 0,
                "utilization_percentage": 0
            }
        }
        
        # If network is specified, only report on that network
        network_list = []
        if network:
            for net in db.get("network", []):
                if net["network"] == network and net.get("network_view", "default") == network_view:
                    network_list.append(net)
                    break
            
            # IPv6 networks
            if not network_list:
                for net in db.get("ipv6network", []):
                    if net["network"] == network and net.get("network_view", "default") == network_view:
                        network_list.append(net)
                        break
        else:
            # Get all networks in the specified view
            for net in db.get("network", []):
                if net.get("network_view", "default") == network_view:
                    network_list.append(net)
            
            # IPv6 networks
            for net in db.get("ipv6network", []):
                if net.get("network_view", "default") == network_view:
                    network_list.append(net)
        
        # If no networks found, return empty report
        if not network_list:
            return results
        
        # Process each network
        total_ips = 0
        used_ips = 0
        
        for net in network_list:
            # Calculate utilization for this network
            network_obj = ipaddress.ip_network(net["network"])
            is_ipv6 = isinstance(network_obj, ipaddress.IPv6Network)
            
            # For IPv4, calculate all usable IPs
            # For IPv6, only count /64 or larger networks and limit to a reasonable number
            if is_ipv6:
                if network_obj.prefixlen <= 64:
                    # For IPv6 networks, we'll simulate a smaller count for practicality
                    network_ips = 1000
                else:
                    # For smaller IPv6 networks, calculate actual count
                    network_ips = min(1000, 2 ** (128 - network_obj.prefixlen))
            else:
                # For IPv4, calculate actual usable IPs
                network_ips = max(0, network_obj.num_addresses - 2)  # Exclude network and broadcast
            
            # Count used IPs
            network_used_ips = 0
            
            if is_ipv6:
                # Count IPv6 addresses
                for record_type in ["record:aaaa", "ipv6fixedaddress"]:
                    for record in db.get(record_type, []):
                        record_ip = record.get("ipv6addr", "")
                        if record_ip:
                            try:
                                ip = ipaddress.IPv6Address(record_ip)
                                if ip in network_obj:
                                    network_used_ips += 1
                            except ValueError:
                                pass
                
                # Check host records with IPv6 addresses
                for host in db.get("record:host", []):
                    for addr in host.get("ipv6addrs", []):
                        record_ip = addr.get("ipv6addr", "")
                        if record_ip:
                            try:
                                ip = ipaddress.IPv6Address(record_ip)
                                if ip in network_obj:
                                    network_used_ips += 1
                            except ValueError:
                                pass
            else:
                # Count IPv4 addresses
                for record_type in ["record:a", "record:host", "fixedaddress", "lease"]:
                    for record in db.get(record_type, []):
                        if record_type == "record:host":
                            for addr in record.get("ipv4addrs", []):
                                record_ip = addr.get("ipv4addr", "")
                                if record_ip:
                                    try:
                                        ip = ipaddress.IPv4Address(record_ip)
                                        if ip in network_obj:
                                            network_used_ips += 1
                                    except ValueError:
                                        pass
                        else:
                            record_ip = record.get("ipv4addr", "")
                            if record_ip:
                                try:
                                    ip = ipaddress.IPv4Address(record_ip)
                                    if ip in network_obj:
                                        network_used_ips += 1
                                except ValueError:
                                    pass
            
            # Calculate utilization percentage
            if network_ips > 0:
                utilization_percentage = round((network_used_ips / network_ips) * 100, 2)
            else:
                utilization_percentage = 0
            
            # Create network report
            network_report = {
                "network": net["network"],
                "network_view": net.get("network_view", "default"),
                "comment": net.get("comment", ""),
                "total_ips": network_ips,
                "used_ips": network_used_ips,
                "available_ips": network_ips - network_used_ips,
                "utilization_percentage": utilization_percentage,
                "extattrs": net.get("extattrs", {})
            }
            
            # Add to results
            results["networks"].append(network_report)
            
            # Add to totals
            total_ips += network_ips
            used_ips += network_used_ips
        
        # Calculate summary
        results["summary"]["total_networks"] = len(network_list)
        results["summary"]["total_ips"] = total_ips
        results["summary"]["used_ips"] = used_ips
        results["summary"]["available_ips"] = total_ips - used_ips
        
        if total_ips > 0:
            results["summary"]["utilization_percentage"] = round((used_ips / total_ips) * 100, 2)
        
        # Store in cache
        ipam_utilization[results["report_id"]] = results
        
        return results
    
    @staticmethod
    def get_utilization_report(report_id):
        """Get a previously generated utilization report"""
        return ipam_utilization.get(report_id)
    
    @staticmethod
    def get_all_utilization_reports():
        """Get all utilization reports"""
        return list(ipam_utilization.values())

class DNSReportManager:
    """Manager for DNS statistics and reports"""
    
    @staticmethod
    def generate_dns_statistics(view=None):
        """Generate DNS statistics"""
        from infoblox_mock.db import db
        
        # Create results container
        results = {
            "report_id": f"dns_stats_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "report_time": datetime.now().isoformat(),
            "summary": {
                "total_zones": 0,
                "total_records": 0,
                "record_counts": {}
            },
            "views": []
        }
        
        # Get all DNS views or specified view
        view_list = []
        if view:
            from infoblox_mock.dns import dns_views
            if view in dns_views:
                view_list.append(dns_views[view])
        else:
            from infoblox_mock.dns import dns_views
            view_list = list(dns_views.values())
        
        # Process each view
        for v in view_list:
            view_name = v["name"]
            
            # Initialize view stats
            view_stats = {
                "name": view_name,
                "total_records": 0,
                "record_counts": {},
                "zones": []
            }
            
            # Get all zones in this view by looking at SOA records
            zones = {}
            for soa in db.get("record:soa", []):
                if soa.get("view", "default") == view_name:
                    zone_name = soa["name"]
                    zones[zone_name] = {
                        "name": zone_name,
                        "total_records": 1,  # Start with 1 for the SOA
                        "record_counts": {"record:soa": 1},
                        "security": {
                            "dnssec_enabled": False
                        }
                    }
            
            # Check if zones are DNSSEC enabled
            from infoblox_mock.dns import dnssec_enabled_zones
            for zone_name in zones:
                view_zone = f"{view_name}:{zone_name}"
                if view_zone in dnssec_enabled_zones:
                    zones[zone_name]["security"]["dnssec_enabled"] = True
            
            # Count records for each zone
            record_types = [
                "record:a", "record:aaaa", "record:cname", "record:ptr",
                "record:mx", "record:srv", "record:txt", "record:ns"
            ]
            
            for record_type in record_types:
                for record in db.get(record_type, []):
                    if record.get("view", "default") != view_name:
                        continue
                    
                    # Find which zone this record belongs to
                    record_name = record.get("name", "")
                    record_zone = None
                    
                    for zone_name in zones:
                        if record_name == zone_name or record_name.endswith(f".{zone_name}"):
                            record_zone = zone_name
                            break
                    
                    if record_zone:
                        # Add to zone counts
                        zones[record_zone]["total_records"] += 1
                        if record_type in zones[record_zone]["record_counts"]:
                            zones[record_zone]["record_counts"][record_type] += 1
                        else:
                            zones[record_zone]["record_counts"][record_type] = 1
                    
                    # Add to view counts
                    view_stats["total_records"] += 1
                    if record_type in view_stats["record_counts"]:
                        view_stats["record_counts"][record_type] += 1
                    else:
                        view_stats["record_counts"][record_type] = 1
            
            # Add zones to view stats
            view_stats["zones"] = list(zones.values())
            
            # Add to results
            results["views"].append(view_stats)
            
            # Add to summary
            results["summary"]["total_zones"] += len(zones)
            results["summary"]["total_records"] += view_stats["total_records"]
            
            # Merge record counts
            for record_type, count in view_stats["record_counts"].items():
                if record_type in results["summary"]["record_counts"]:
                    results["summary"]["record_counts"][record_type] += count
                else:
                    results["summary"]["record_counts"][record_type] = count
        
        # Store in cache
        dns_statistics[results["report_id"]] = results
        
        return results
    
    @staticmethod
    def get_dns_statistics(report_id):
        """Get previously generated DNS statistics"""
        return dns_statistics.get(report_id)
    
    @staticmethod
    def get_all_dns_statistics():
        """Get all DNS statistics"""
        return list(dns_statistics.values())

class DHCPReportManager:
    """Manager for DHCP statistics and reports"""
    
    @staticmethod
    def generate_dhcp_statistics():
        """Generate DHCP statistics"""
        from infoblox_mock.db import db
        
        # Create results container
        results = {
            "report_id": f"dhcp_stats_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "report_time": datetime.now().isoformat(),
            "summary": {
                "total_ranges": 0,
                "total_leases": 0,
                "active_leases": 0,
                "utilization_percentage": 0,
                "fixed_addresses": 0
            },
            "ranges": []
        }
        
        # Get all DHCP ranges (IPv4 and IPv6)
        range_list = []
        range_list.extend(db.get("range", []))
        range_list.extend(db.get("ipv6range", []))
        
        # Process each range
        total_addresses = 0
        total_leases = 0
        active_leases = 0
        
        for r in range_list:
            is_ipv6 = "ipv6" in r.get("_ref", "")
            
            # Calculate range size
            if is_ipv6:
                start = ipaddress.IPv6Address(r["start_addr"])
                end = ipaddress.IPv6Address(r["end_addr"])
                range_size = int(end) - int(start) + 1
                
                # For IPv6, limit to a reasonable number for simulation
                range_size = min(range_size, 1000)
            else:
                start = ipaddress.IPv4Address(r["start_addr"])
                end = ipaddress.IPv4Address(r["end_addr"])
                range_size = int(end) - int(start) + 1
            
            # Count leases in this range
            range_leases = 0
            range_active_leases = 0
            
            if is_ipv6:
                # Count IPv6 leases
                for lease in db.get("ipv6lease", []):
                    lease_ip = lease.get("ipv6addr", "")
                    if lease_ip:
                        try:
                            ip = ipaddress.IPv6Address(lease_ip)
                            if start <= ip <= end:
                                range_leases += 1
                                if lease.get("binding_state", "") == "active":
                                    range_active_leases += 1
                        except ValueError:
                            pass
            else:
                # Count IPv4 leases
                for lease in db.get("lease", []):
                    lease_ip = lease.get("ipv4addr", "")
                    if lease_ip:
                        try:
                            ip = ipaddress.IPv4Address(lease_ip)
                            if start <= ip <= end:
                                range_leases += 1
                                if lease.get("binding_state", "") == "active":
                                    range_active_leases += 1
                        except ValueError:
                            pass
            
            # Calculate utilization percentage
            if range_size > 0:
                utilization_percentage = round((range_leases / range_size) * 100, 2)
            else:
                utilization_percentage = 0
            
            # Create range report
            range_report = {
                "range": f"{r['start_addr']}-{r['end_addr']}",
                "network": r.get("network", ""),
                "network_view": r.get("network_view", "default"),
                "total_addresses": range_size,
                "total_leases": range_leases,
                "active_leases": range_active_leases,
                "utilization_percentage": utilization_percentage,
                "is_ipv6": is_ipv6
            }
            
            # Add to results
            results["ranges"].append(range_report)
            
            # Add to totals
            total_addresses += range_size
            total_leases += range_leases
            active_leases += range_active_leases
        
        # Count fixed addresses
        fixed_addresses = len(db.get("fixedaddress", []))
        fixed_addresses += len(db.get("ipv6fixedaddress", []))
        
        # Calculate summary
        results["summary"]["total_ranges"] = len(range_list)
        results["summary"]["total_leases"] = total_leases
        results["summary"]["active_leases"] = active_leases
        results["summary"]["fixed_addresses"] = fixed_addresses
        
        if total_addresses > 0:
            results["summary"]["utilization_percentage"] = round((total_leases / total_addresses) * 100, 2)
        
        # Store in cache
        dhcp_statistics[results["report_id"]] = results
        
        return results
    
    @staticmethod
    def get_dhcp_statistics(report_id):
        """Get previously generated DHCP statistics"""
        return dhcp_statistics.get(report_id)
    
    @staticmethod
    def get_all_dhcp_statistics():
        """Get all DHCP statistics"""
        return list(dhcp_statistics.values())

class AuditLogManager:
    """Manager for audit logs"""
    
    @staticmethod
    def add_log_entry(data):
        """Add an audit log entry"""
        if not data.get("user"):
            data["user"] = "admin"
        
        if not data.get("action"):
            data["action"] = "UNKNOWN"
        
        # Create log entry
        log_entry = {
            "id": len(audit_logs) + 1,
            "timestamp": datetime.now().isoformat(),
            "user": data["user"],
            "action": data["action"],
            "object_type": data.get("object_type", ""),
            "object_ref": data.get("object_ref", ""),
            "details": data.get("details", ""),
            "admin_type": data.get("admin_type", "LOCAL"),
            "client_ip": data.get("client_ip", ""),
            "status": data.get("status", "SUCCESS")
        }
        
        # Add to logs
        audit_logs.append(log_entry)
        
        # Keep logs pruned to a reasonable size
        if len(audit_logs) > 10000:
            audit_logs.pop(0)
        
        return log_entry["id"]
    
    @staticmethod
    def get_log_entry(log_id):
        """Get an audit log entry by ID"""
        for log in audit_logs:
            if log["id"] == log_id:
                return log
        
        return None
    
    @staticmethod
    def get_logs(filters=None, limit=100, offset=0):
        """Get audit logs with optional filtering"""
        # Start with all logs
        logs = audit_logs
        
        # Apply filters if provided
        if filters:
            filtered_logs = []
            for log in logs:
                match = True
                
                for key, value in filters.items():
                    if key in log:
                        # Handle different types of filters
                        if isinstance(value, list):
                            if log[key] not in value:
                                match = False
                                break
                        elif isinstance(log[key], str) and isinstance(value, str):
                            if value.startswith('*') and value.endswith('*'):
                                # Contains
                                if value[1:-1] not in log[key]:
                                    match = False
                                    break
                            elif value.startswith('*'):
                                # Ends with
                                if not log[key].endswith(value[1:]):
                                    match = False
                                    break
                            elif value.endswith('*'):
                                # Starts with
                                if not log[key].startswith(value[:-1]):
                                    match = False
                                    break
                            else:
                                # Exact match
                                if log[key] != value:
                                    match = False
                                    break
                        else:
                            # Exact match for other types
                            if log[key] != value:
                                match = False
                                break
                
                if match:
                    filtered_logs.append(log)
            
            logs = filtered_logs
        
        # Apply pagination
        total = len(logs)
        logs = logs[-total:] if limit is None else logs[offset:offset+limit]
        
        return {
            "logs": logs,
            "total": total,
            "returned": len(logs),
            "offset": offset,
            "limit": limit
        }

class ThreatAnalyticsManager:
    """Manager for threat analytics"""
    
    @staticmethod
    def generate_threat_report():
        """Generate a threat analytics report"""
        from infoblox_mock.db import db
        
        # Create results container
        results = {
            "report_id": f"threat_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "report_time": datetime.now().isoformat(),
            "summary": {
                "total_threats": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0
            },
            "categories": [],
            "threats": []
        }
        
        # Check if RPZ is configured
        from infoblox_mock.dns import rpz_zones, rpz_rules
        
        # Count RPZ hits (simulated)
        rpz_hits = {}
        
        for zone_id, zone in rpz_zones.items():
            for rule in rpz_rules.get(zone_id, []):
                # Simulate random hit count
                hits = random.randint(0, 100)
                
                if hits > 0:
                    # Create threat entry
                    threat = {
                        "id": len(results["threats"]) + 1,
                        "type": "RPZ",
                        "name": rule["name"],
                        "category": "DNS Security",
                        "source": zone["name"],
                        "action": rule["action"],
                        "severity": "HIGH" if hits > 50 else "MEDIUM" if hits > 10 else "LOW",
                        "hits": hits,
                        "first_seen": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                        "last_seen": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat(),
                        "details": {
                            "rule_type": rule["type"],
                            "zone": zone["name"],
                            "view": zone["view"]
                        }
                    }
                    
                    # Add to results
                    results["threats"].append(threat)
                    
                    # Update summary
                    results["summary"]["total_threats"] += 1
                    if threat["severity"] == "HIGH":
                        results["summary"]["high_severity"] += 1
                    elif threat["severity"] == "MEDIUM":
                        results["summary"]["medium_severity"] += 1
                    else:
                        results["summary"]["low_severity"] += 1
                    
                    # Update categories
                    category_exists = False
                    for category in results["categories"]:
                        if category["name"] == threat["category"]:
                            category["count"] += 1
                            category_exists = True
                            break
                    
                    if not category_exists:
                        results["categories"].append({
                            "name": threat["category"],
                            "count": 1
                        })
        
        # Add some simulated network threats
        threat_types = [
            {"name": "Botnet Communication", "category": "Network Security", "severity": "HIGH"},
            {"name": "Port Scan", "category": "Network Security", "severity": "MEDIUM"},
            {"name": "Malware Download", "category": "Malware", "severity": "HIGH"},
            {"name": "Phishing Site", "category": "Web Security", "severity": "HIGH"},
            {"name": "Suspicious DNS Query", "category": "DNS Security", "severity": "MEDIUM"},
            {"name": "DDoS Participation", "category": "Network Security", "severity": "HIGH"}
        ]
        
        # Generate random threats
        for _ in range(random.randint(5, 20)):
            threat_type = random.choice(threat_types)
            
            # Create random IP
            if random.random() < 0.5:
                # IPv4
                ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            else:
                # IPv6
                ip = f"2001:db8:{random.randint(0, 9999):x}:{random.randint(0, 9999):x}::{random.randint(1, 9999):x}"
            
            # Create threat entry
            threat = {
                "id": len(results["threats"]) + 1,
                "type": "NETWORK",
                "name": threat_type["name"],
                "category": threat_type["category"],
                "source": ip,
                "action": "BLOCK",
                "severity": threat_type["severity"],
                "hits": random.randint(1, 100),
                "first_seen": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "last_seen": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat(),
                "details": {
                    "ip": ip,
                    "protocol": random.choice(["TCP", "UDP", "HTTP", "DNS"]),
                    "destination": random.choice([
                        "malware.example.com",
                        "c2.badguy.com",
                        "phishing.example.net",
                        f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
                    ])
                }
            }
            
            # Add to results
            results["threats"].append(threat)
            
            # Update summary
            results["summary"]["total_threats"] += 1
            if threat["severity"] == "HIGH":
                results["summary"]["high_severity"] += 1
            elif threat["severity"] == "MEDIUM":
                results["summary"]["medium_severity"] += 1
            else:
                results["summary"]["low_severity"] += 1
            
            # Update categories
            category_exists = False
            for category in results["categories"]:
                if category["name"] == threat["category"]:
                    category["count"] += 1
                    category_exists = True
                    break
            
            if not category_exists:
                results["categories"].append({
                    "name": threat["category"],
                    "count": 1
                })
        
        # Store in cache
        threat_analytics[results["report_id"]] = results
        
        return results
    
    @staticmethod
    def get_threat_report(report_id):
        """Get a previously generated threat report"""
        return threat_analytics.get(report_id)
    
    @staticmethod
    def get_all_threat_reports():
        """Get all threat reports"""
        return list(threat_analytics.values())

class SearchManager:
    """Manager for search and Smart Folders"""
    
    @staticmethod
    def search(query, obj_types=None, limit=100, offset=0):
        """Search for objects matching a query"""
        from infoblox_mock.db import db
        
        # Create results container
        results = {
            "search_id": f"search_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "search_time": datetime.now().isoformat(),
            "query": query,
            "results": [],
            "summary": {
                "total": 0,
                "returned": 0
            }
        }
        
        # Default object types to search if not specified
        if not obj_types:
            obj_types = [
                "network", "ipv6network", "range", "ipv6range",
                "record:host", "record:a", "record:aaaa", "record:cname",
                "record:ptr", "record:mx", "record:txt", "record:srv",
                "record:ns", "record:soa", "fixedaddress", "ipv6fixedaddress"
            ]
        
        # Process each object type
        all_results = []
        
        for obj_type in obj_types:
            # Skip if this object type doesn't exist in the database
            if obj_type not in db:
                continue
            
            for obj in db[obj_type]:
                # Check if the object matches the query
                match = False
                
                # Search in common fields
                common_fields = ["name", "comment", "ipv4addr", "ipv6addr", "network", "host_name"]
                for field in common_fields:
                    if field in obj and isinstance(obj[field], str) and query.lower() in obj[field].lower():
                        match = True
                        break
                
                # Search in specific fields based on object type
                if not match:
                    if obj_type == "record:host":
                        # Search in IPv4 addresses
                        for addr in obj.get("ipv4addrs", []):
                            if query.lower() in addr.get("ipv4addr", "").lower():
                                match = True
                                break
                        
                        # Search in IPv6 addresses
                        if not match:
                            for addr in obj.get("ipv6addrs", []):
                                if query.lower() in addr.get("ipv6addr", "").lower():
                                    match = True
                                    break
                    elif obj_type == "record:cname":
                        if query.lower() in obj.get("canonical", "").lower():
                            match = True
                    elif obj_type == "record:ptr":
                        if query.lower() in obj.get("ptrdname", "").lower():
                            match = True
                    elif obj_type == "record:mx":
                        if query.lower() in obj.get("mail_exchanger", "").lower():
                            match = True
                    elif obj_type == "record:srv":
                        if query.lower() in obj.get("target", "").lower():
                            match = True
                
                # Search in extensible attributes
                if not match and "extattrs" in obj:
                    for attr_name, attr_value in obj["extattrs"].items():
                        if isinstance(attr_value, dict) and "value" in attr_value:
                            if query.lower() in str(attr_value["value"]).lower():
                                match = True
                                break
                        elif query.lower() in str(attr_value).lower():
                            match = True
                            break
                
                # If the object matches, add it to the results
                if match:
                    # Create a result entry
                    result = {
                        "ref": obj.get("_ref", f"{obj_type}/unknown"),
                        "type": obj_type,
                        "data": obj,
                        "match_fields": []
                    }
                    
                    # Identify matching fields for context
                    for field in common_fields:
                        if field in obj and isinstance(obj[field], str) and query.lower() in obj[field].lower():
                            result["match_fields"].append(field)
                    
                    all_results.append(result)
        
        # Apply pagination
        total = len(all_results)
        paginated_results = all_results[offset:offset+limit]
        
        # Update results
        results["results"] = paginated_results
        results["summary"]["total"] = total
        results["summary"]["returned"] = len(paginated_results)
        
        # Store in cache
        search_results[results["search_id"]] = results
        
        return results
    
    @staticmethod
    def get_search_results(search_id):
        """Get previously generated search results"""
        return search_results.get(search_id)
    
    @staticmethod
    def create_smart_folder(data):
        """Create a Smart Folder"""
        if not data.get("name"):
            return None, "Smart Folder name is required"
        
        if not data.get("query"):
            return None, "Query is required"
        
        # Generate a unique ID
        folder_id = str(len(smart_folders) + 1)
        
        # Create the smart folder
        folder_data = {
            "_ref": f"smartfolder/{folder_id}",
            "name": data["name"],
            "query": data["query"],
            "obj_types": data.get("obj_types", []),
            "comment": data.get("comment", ""),
            "owner": data.get("owner", "admin"),
            "is_shared": data.get("is_shared", False),
            "_create_time": datetime.now().isoformat(),
            "_modify_time": datetime.now().isoformat()
        }
        
        # Add to smart folders
        smart_folders[folder_id] = folder_data
        
        return folder_data["_ref"], None
    
    @staticmethod
    def get_smart_folder(folder_id):
        """Get a Smart Folder by ID"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        return smart_folders[folder_id], None
    
    @staticmethod
    def get_smart_folder_contents(folder_id):
        """Get the contents of a Smart Folder"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        folder = smart_folders[folder_id]
        
        # Execute the search
        search_results = SearchManager.search(
            folder["query"],
            obj_types=folder.get("obj_types")
        )
        
        return search_results, None
    
    @staticmethod
    def update_smart_folder(folder_id, data):
        """Update a Smart Folder"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        folder = smart_folders[folder_id]
        
        # Update fields
        for key, value in data.items():
            if key not in ["_ref", "_create_time"]:
                folder[key] = value
        
        folder["_modify_time"] = datetime.now().isoformat()
        
        return folder["_ref"], None
    
    @staticmethod
    def delete_smart_folder(folder_id):
        """Delete a Smart Folder"""
        if folder_id not in smart_folders:
            return None, f"Smart Folder not found: {folder_id}"
        
        # Delete the folder
        del smart_folders[folder_id]
        
        return folder_id, None
    
    @staticmethod
    def get_all_smart_folders(owner=None):
        """Get all Smart Folders, optionally filtered by owner"""
        if owner:
            return [folder for folder in smart_folders.values() if folder["owner"] == owner or folder["is_shared"]]
        else:
            return list(smart_folders.values())