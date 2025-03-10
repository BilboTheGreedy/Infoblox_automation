"""
Utility functions for formatting data
"""

import json
import datetime
import re


def format_json(data, indent=2):
    """
    Format JSON data for display.
    
    Args:
        data: Data to format
        indent (int): Indentation level
        
    Returns:
        str: Formatted JSON string
    """
    if isinstance(data, str):
        try:
            # Try to parse if it's a JSON string
            data = json.loads(data)
        except json.JSONDecodeError:
            # If not valid JSON, return as is
            return data
    
    try:
        return json.dumps(data, indent=indent, sort_keys=True)
    except (TypeError, ValueError):
        # If not JSON serializable, return string representation
        return str(data)


def format_timestamp(timestamp, format_str="%Y-%m-%d %H:%M:%S"):
    """
    Format timestamp for display.
    
    Args:
        timestamp (str): ISO format timestamp
        format_str (str): Desired output format
        
    Returns:
        str: Formatted timestamp
    """
    if not timestamp:
        return ""
        
    try:
        if isinstance(timestamp, str):
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
        return dt.strftime(format_str)
    except (ValueError, TypeError):
        return timestamp


def format_status_code(status_code):
    """
    Format HTTP status code with descriptive text.
    
    Args:
        status_code (int): HTTP status code
        
    Returns:
        str: Formatted status code with description
    """
    status_descriptions = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable"
    }
    
    description = status_descriptions.get(status_code, "")
    if description:
        return f"{status_code} - {description}"
    return str(status_code)


def format_size(size_bytes):
    """
    Format byte size to human readable form.
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size
    """
    if size_bytes is None:
        return "0 B"
        
    # Convert to integer in case it's a string
    try:
        size_bytes = int(size_bytes)
    except (ValueError, TypeError):
        return str(size_bytes)
        
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024 or unit == 'TB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024


def truncate_text(text, max_length=100, suffix="..."):
    """
    Truncate text to specified length.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        suffix (str): Suffix to add to truncated text
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def highlight_search_term(text, term, case_sensitive=False):
    """
    Highlight search term in text with HTML span.
    
    Args:
        text (str): Text to search in
        term (str): Term to highlight
        case_sensitive (bool): Whether search should be case sensitive
        
    Returns:
        str: Text with highlighted terms
    """
    if not term or not text:
        return text
    
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.escape(term)
    
    return re.sub(
        f'({pattern})', 
        r'<span class="highlight">\1</span>', 
        text, 
        flags=flags
    )


def format_duration(seconds):
    """
    Format a duration in seconds to a human-readable format.
    
    Args:
        seconds (float): Duration in seconds
        
    Returns:
        str: Formatted duration
    """
    if seconds < 0.001:
        return f"{seconds * 1000 * 1000:.0f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} sec"
    else:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{int(minutes)} min {int(remaining_seconds)} sec"


def format_method(method):
    """
    Format HTTP method with appropriate color class.
    
    Args:
        method (str): HTTP method
        
    Returns:
        tuple: (method, css_class)
    """
    method = method.upper()
    method_classes = {
        'GET': 'text-primary',
        'POST': 'text-success',
        'PUT': 'text-info',
        'DELETE': 'text-danger',
        'PATCH': 'text-warning'
    }
    
    return method, method_classes.get(method, '')