"""
Swagger documentation for Infoblox Mock Server
"""

import logging
from infoblox_mock.config import CONFIG, WAPI_FEATURES, is_feature_supported

logger = logging.getLogger(__name__)

def generate_swagger_spec():
    """Generate a Swagger/OpenAPI specification for the mock server"""
    wapi_version = CONFIG.get('wapi_version', 'v2.11')
    
    # Base specification
    spec = {
        "swagger": "2.0",
        "info": {
            "title": "Infoblox Mock Server API",
            "description": "A mock implementation of the Infoblox WAPI",
            "version": wapi_version,
            "contact": {
                "email": "admin@example.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "host": "localhost:8080",
        "basePath": f"/wapi/{wapi_version}",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "basicAuth": {
                "type": "basic",
                "description": "HTTP Basic Authentication"
            }
        },
        "security": [
            {
                "basicAuth": []
            }
        ],
        "paths": {},
        "definitions": {}
    }
    
    # Add common object definitions
    spec["definitions"] = {
        "Error": {
            "type": "object",
            "properties": {
                "Error": {
                    "type": "string",
                    "description": "Error message"
                },
                "text": {
                    "type": "string",
                    "description": "Additional error details"
                }
            }
        },
        "StringArray": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "ExtensibleAttribute": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "The value of the attribute"
                },
                "inheritance": {
                    "type": "boolean",
                    "description": "Whether this attribute is inherited by child objects"
                },
                "inherited_from": {
                    "type": "string",
                    "description": "Reference to the object this attribute is inherited from"
                }
            }
        },
        "ExtensibleAttributes": {
            "type": "object",
            "additionalProperties": {
                "$ref": "#/definitions/ExtensibleAttribute"
            }
        }
    }
    
    # Add paths based on features supported in this WAPI version
    paths = {}
    
    # Basic IPAM paths (always included)
    paths["/network"] = {
        "get": {
            "summary": "Get networks",
            "description": "Retrieve networks based on query parameters",
            "parameters": [
                {
                    "name": "network",
                    "in": "query",
                    "description": "Network address in CIDR notation",
                    "type": "string"
                },
                {
                    "name": "network_view",
                    "in": "query",
                    "description": "Network view name",
                    "type": "string"
                },
                {
                    "name": "_return_fields",
                    "in": "query",
                    "description": "Comma-separated list of fields to return",
                    "type": "string"
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/Network"
                        }
                    }
                },
                "400": {
                    "description": "Bad request",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        },
        "post": {
            "summary": "Create a network",
            "description": "Create a new network",
            "parameters": [
                {
                    "name": "body",
                    "in": "body",
                    "description": "Network data",
                    "required": True,
                    "schema": {
                        "$ref": "#/definitions/NetworkCreate"
                    }
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {
                        "type": "string",
                        "description": "Reference to the created network"
                    }
                },
                "400": {
                    "description": "Bad request",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        }
    }
    
    # Add path for network resource by ref
    paths["/network/{ref}"] = {
        "get": {
            "summary": "Get network by reference",
            "description": "Retrieve a specific network by its reference",
            "parameters": [
                {
                    "name": "ref",
                    "in": "path",
                    "description": "Network reference",
                    "required": True,
                    "type": "string"
                },
                {
                    "name": "_return_fields",
                    "in": "query",
                    "description": "Comma-separated list of fields to return",
                    "type": "string"
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {
                        "$ref": "#/definitions/Network"
                    }
                },
                "404": {
                    "description": "Network not found",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        },
        "put": {
            "summary": "Update network",
            "description": "Update a specific network",
            "parameters": [
                {
                    "name": "ref",
                    "in": "path",
                    "description": "Network reference",
                    "required": True,
                    "type": "string"
                },
                {
                    "name": "body",
                    "in": "body",
                    "description": "Network data to update",
                    "required": True,
                    "schema": {
                        "$ref": "#/definitions/NetworkUpdate"
                    }
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {
                        "type": "string",
                        "description": "Reference to the updated network"
                    }
                },
                "404": {
                    "description": "Network not found",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        },
        "delete": {
            "summary": "Delete network",
            "description": "Delete a specific network",
            "parameters": [
                {
                    "name": "ref",
                    "in": "path",
                    "description": "Network reference",
                    "required": True,
                    "type": "string"
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {
                        "type": "string",
                        "description": "Reference to the deleted network"
                    }
                },
                "404": {
                    "description": "Network not found",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        }
    }
    
    # Next available IP endpoint
    paths["/network/{network}/next_available_ip"] = {
        "post": {
            "summary": "Get next available IP",
            "description": "Get the next available IP address in a network",
            "parameters": [
                {
                    "name": "network",
                    "in": "path",
                    "description": "Network address in CIDR notation",
                    "required": True,
                    "type": "string"
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "ips": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Array of available IP addresses"
                            }
                        }
                    }
                },
                "404": {
                    "description": "Network not found",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        }
    }
    
    # Basic DNS paths
    if is_feature_supported('basic_dns'):
        # Add DNS record endpoints
        for record_type in ['record:host', 'record:a', 'record:aaaa', 'record:cname', 'record:ptr', 
                          'record:mx', 'record:txt', 'record:srv', 'record:ns', 'record:soa']:
            paths[f"/{record_type}"] = {
                "get": {
                    "summary": f"Get {record_type} records",
                    "description": f"Retrieve {record_type} records based on query parameters",
                    "parameters": [
                        {
                            "name": "name",
                            "in": "query",
                            "description": "Record name",
                            "type": "string"
                        },
                        {
                            "name": "view",
                            "in": "query",
                            "description": "DNS view name",
                            "type": "string"
                        },
                        {
                            "name": "_return_fields",
                            "in": "query",
                            "description": "Comma-separated list of fields to return",
                            "type": "string"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "schema": {
                                "type": "array",
                                "items": {
                                    "$ref": f"#/definitions/{record_type.replace(':', '')}"
                                }
                            }
                        },
                        "400": {
                            "description": "Bad request",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        }
                    }
                },
                "post": {
                    "summary": f"Create a {record_type} record",
                    "description": f"Create a new {record_type} record",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "description": f"{record_type} data",
                            "required": True,
                            "schema": {
                                "$ref": f"#/definitions/{record_type.replace(':', '')}Create"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "schema": {
                                "type": "string",
                                "description": f"Reference to the created {record_type} record"
                            }
                        },
                        "400": {
                            "description": "Bad request",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        }
                    }
                }
            }
            
            # Add path for record resource by ref
            paths[f"/{record_type}/{{ref}}"] = {
                "get": {
                    "summary": f"Get {record_type} record by reference",
                    "description": f"Retrieve a specific {record_type} record by its reference",
                    "parameters": [
                        {
                            "name": "ref",
                            "in": "path",
                            "description": f"{record_type} reference",
                            "required": True,
                            "type": "string"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "schema": {
                                "$ref": f"#/definitions/{record_type.replace(':', '')}"
                            }
                        },
                        "404": {
                            "description": "Record not found",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        }
                    }
                },
                "put": {
                    "summary": f"Update {record_type} record",
                    "description": f"Update a specific {record_type} record",
                    "parameters": [
                        {
                            "name": "ref",
                            "in": "path",
                            "description": f"{record_type} reference",
                            "required": True,
                            "type": "string"
                        },
                        {
                            "name": "body",
                            "in": "body",
                            "description": f"{record_type} data to update",
                            "required": True,
                            "schema": {
                                "$ref": f"#/definitions/{record_type.replace(':', '')}Update"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "schema": {
                                "type": "string",
                                "description": f"Reference to the updated {record_type} record"
                            }
                        },
                        "404": {
                            "description": "Record not found",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        }
                    }
                },
                "delete": {
                    "summary": f"Delete {record_type} record",
                    "description": f"Delete a specific {record_type} record",
                    "parameters": [
                        {
                            "name": "ref",
                            "in": "path",
                            "description": f"{record_type} reference",
                            "required": True,
                            "type": "string"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "schema": {
                                "type": "string",
                                "description": f"Reference to the deleted {record_type} record"
                            }
                        },
                        "404": {
                            "description": "Record not found",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "schema": {
                                "$ref": "#/definitions/Error"
                            }
                        }
                    }
                }
            }
    
    # Add IPv6 support if available
    if is_feature_supported('ipv6_support'):
        paths["/ipv6network"] = {
            "get": {
                "summary": "Get IPv6 networks",
                "description": "Retrieve IPv6 networks based on query parameters",
                "parameters": [
                    {
                        "name": "network",
                        "in": "query",
                        "description": "Network address in CIDR notation",
                        "type": "string"
                    },
                    {
                        "name": "network_view",
                        "in": "query",
                        "description": "Network view name",
                        "type": "string"
                    },
                    {
                        "name": "_return_fields",
                        "in": "query",
                        "description": "Comma-separated list of fields to return",
                        "type": "string"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "schema": {
                            "type": "array",
                            "items": {
                                "$ref": "#/definitions/IPv6Network"
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    },
                    "401": {
                        "description": "Unauthorized",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    }
                }
            },
            "post": {
                "summary": "Create an IPv6 network",
                "description": "Create a new IPv6 network",
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "description": "IPv6 Network data",
                        "required": True,
                        "schema": {
                            "$ref": "#/definitions/IPv6NetworkCreate"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "schema": {
                            "type": "string",
                            "description": "Reference to the created IPv6 network"
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    },
                    "401": {
                        "description": "Unauthorized",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    }
                }
            }
        }
        
        # Add next available IPv6 endpoint
        paths["/ipv6network/{network}/next_available_ip"] = {
            "post": {
                "summary": "Get next available IPv6 address",
                "description": "Get the next available IPv6 address in a network",
                "parameters": [
                    {
                        "name": "network",
                        "in": "path",
                        "description": "IPv6 Network address in CIDR notation",
                        "required": True,
                        "type": "string"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "ips": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "Array of available IPv6 addresses"
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Network not found",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    },
                    "401": {
                        "description": "Unauthorized",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    }
                }
            }
        }
    
    # Add bulk operations if available
    if is_feature_supported('bulk_operations'):
        paths["/bulk"] = {
            "post": {
                "summary": "Perform bulk operations",
                "description": "Perform bulk operations (create, update, delete) on multiple objects",
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "description": "Bulk operation data",
                        "required": True,
                        "schema": {
                            "$ref": "#/definitions/BulkOperation"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "schema": {
                            "type": "array",
                            "items": {
                                "$ref": "#/definitions/BulkResult"
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    },
                    "401": {
                        "description": "Unauthorized",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    }
                }
            }
        }
        
        paths["/bulkhost"] = {
            "post": {
                "summary": "Perform bulk host operations",
                "description": "Create multiple host records in a single operation",
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "description": "Bulk host operation data",
                        "required": True,
                        "schema": {
                            "$ref": "#/definitions/BulkHostOperation"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "schema": {
                            "type": "array",
                            "items": {
                                "$ref": "#/definitions/BulkResult"
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    },
                    "401": {
                        "description": "Unauthorized",
                        "schema": {
                            "$ref": "#/definitions/Error"
                        }
                    }
                }
            }
        }
    
    # Grid session endpoints (authentication)
    paths["/grid/session"] = {
        "post": {
            "summary": "Create a session (login)",
            "description": "Create a new session (login)",
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "Logged in username"
                            }
                        }
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        },
        "delete": {
            "summary": "Delete a session (logout)",
            "description": "Delete an existing session (logout)",
            "responses": {
                "204": {
                    "description": "Successful logout (no content)"
                },
                "401": {
                    "description": "Unauthorized",
                    "schema": {
                        "$ref": "#/definitions/Error"
                    }
                }
            }
        }
    }
    
    # Add definitions for object types
    definitions = {
        "Network": {
            "type": "object",
            "properties": {
                "_ref": {
                    "type": "string",
                    "description": "Object reference"
                },
                "network": {
                    "type": "string",
                    "description": "Network address in CIDR notation"
                },
                "network_view": {
                    "type": "string",
                    "description": "Network view name"
                },
                "comment": {
                    "type": "string",
                    "description": "Comment"
                },
                "extattrs": {
                    "$ref": "#/definitions/ExtensibleAttributes"
                },
                "_create_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Creation timestamp"
                },
                "_modify_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Last modification timestamp"
                }
            }
        },
        "NetworkCreate": {
            "type": "object",
            "required": ["network"],
            "properties": {
                "network": {
                    "type": "string",
                    "description": "Network address in CIDR notation"
                },
                "network_view": {
                    "type": "string",
                    "description": "Network view name"
                },
                "comment": {
                    "type": "string",
                    "description": "Comment"
                },
                "extattrs": {
                    "$ref": "#/definitions/ExtensibleAttributes"
                }
            }
        },
        "NetworkUpdate": {
            "type": "object",
            "properties": {
                "comment": {
                    "type": "string",
                    "description": "Comment"
                },
                "extattrs": {
                    "$ref": "#/definitions/ExtensibleAttributes"
                }
            }
        },
        "recordhost": {
            "type": "object",
            "properties": {
                "_ref": {
                    "type": "string",
                    "description": "Object reference"
                },
                "name": {
                    "type": "string",
                    "description": "Host name"
                },
                "view": {
                    "type": "string",
                    "description": "DNS view name"
                },
                "ipv4addrs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ipv4addr": {
                                "type": "string",
                                "description": "IPv4 address"
                            }
                        }
                    }
                },
                "comment": {
                    "type": "string",
                    "description": "Comment"
                },
                "extattrs": {
                    "$ref": "#/definitions/ExtensibleAttributes"
                }
            }
        },
        "recordhostCreate": {
            "type": "object",
            "required": ["name", "ipv4addrs"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Host name"
                },
                "view": {
                    "type": "string",
                    "description": "DNS view name"
                },
                "ipv4addrs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ipv4addr": {
                                "type": "string",
                                "description": "IPv4 address"
                            }
                        }
                    }
                },
                "comment": {
                    "type": "string",
                    "description": "Comment"
                },
                "extattrs": {
                    "$ref": "#/definitions/ExtensibleAttributes"
                }
            }
        }
    }
    
    # Add IPv6 definitions if supported
    if is_feature_supported('ipv6_support'):
        definitions.update({
            "IPv6Network": {
                "type": "object",
                "properties": {
                    "_ref": {
                        "type": "string",
                        "description": "Object reference"
                    },
                    "network": {
                        "type": "string",
                        "description": "IPv6 Network address in CIDR notation"
                    },
                    "network_view": {
                        "type": "string",
                        "description": "Network view name"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment"
                    },
                    "extattrs": {
                        "$ref": "#/definitions/ExtensibleAttributes"
                    },
                    "_create_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Creation timestamp"
                    },
                    "_modify_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Last modification timestamp"
                    }
                }
            },
            "IPv6NetworkCreate": {
                "type": "object",
                "required": ["network"],
                "properties": {
                    "network": {
                        "type": "string",
                        "description": "IPv6 Network address in CIDR notation"
                    },
                    "network_view": {
                        "type": "string",
                        "description": "Network view name"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment"
                    },
                    "extattrs": {
                        "$ref": "#/definitions/ExtensibleAttributes"
                    }
                }
            }
        })
    
    # Add bulk operation definitions if supported
    if is_feature_supported('bulk_operations'):
        definitions.update({
            "BulkOperation": {
                "type": "object",
                "required": ["objects"],
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["create", "update", "delete"],
                        "description": "Operation to perform on the objects"
                    },
                    "objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "_object": {
                                    "type": "string",
                                    "description": "Object type"
                                },
                                "_ref": {
                                    "type": "string",
                                    "description": "Object reference (required for update and delete)"
                                }
                            },
                            "additionalProperties": True
                        }
                    }
                }
            },
            "BulkHostOperation": {
                "type": "object",
                "required": ["hosts"],
                "properties": {
                    "hosts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Host name"
                                },
                                "view": {
                                    "type": "string",
                                    "description": "DNS view name"
                                },
                                "ipv4addrs": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "ipv4addr": {
                                                "type": "string",
                                                "description": "IPv4 address"
                                            }
                                        }
                                    }
                                },
                                "comment": {
                                    "type": "string",
                                    "description": "Comment"
                                },
                                "extattrs": {
                                    "$ref": "#/definitions/ExtensibleAttributes"
                                }
                            }
                        }
                    }
                }
            },
            "BulkResult": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "Index of the object in the request array"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["SUCCESS", "ERROR"],
                        "description": "Operation status"
                    },
                    "ref": {
                        "type": "string",
                        "description": "Object reference (for successful operations)"
                    },
                    "error": {
                        "type": "string",
                        "description": "Error message (for failed operations)"
                    }
                }
            }
        })
    
    # Add all paths to the spec
    spec["paths"] = paths
    
    # Add all definitions to the spec
    spec["definitions"].update(definitions)
    
    return spec