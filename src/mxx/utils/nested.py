"""
Nested dictionary utilities for handling x/y/z key paths.

Provides functions to get, set, and remove values from nested dictionaries
using path-like keys with '/' separators.
"""

from typing import Any, Dict


def nested_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Get a nested value from dictionary using path-like key.
    
    Args:
        data: Dictionary to search in
        key: Nested key in format "x/y/z"
        default: Default value if key not found
        
    Returns:
        Value if found, default otherwise
        
    Example:
        >>> data = {"config": {"server": {"port": 8080}}}
        >>> nested_get(data, "config/server/port")
        8080
        >>> nested_get(data, "config/missing/key", "default")
        'default'
    """
    if not key:
        return data
    
    parts = key.split('/')
    current = data
    
    try:
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current
    except (KeyError, TypeError):
        return default


def nested_set(data: Dict[str, Any], key: str, value: Any) -> None:
    """
    Set a nested value in dictionary using path-like key.
    Creates intermediate dictionaries as needed.
    
    Args:
        data: Dictionary to modify
        key: Nested key in format "x/y/z"
        value: Value to set
        
    Example:
        >>> data = {}
        >>> nested_set(data, "config/server/port", 8080)
        >>> data
        {'config': {'server': {'port': 8080}}}
    """
    if not key:
        raise ValueError("Key cannot be empty")
    
    parts = key.split('/')
    current = data
    
    # Navigate/create nested structure
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            # Overwrite non-dict values with dict to continue nesting
            current[part] = {}
        current = current[part]
    
    # Set the final value
    current[parts[-1]] = value


def nested_remove(data: Dict[str, Any], key: str) -> bool:
    """
    Remove a nested key from dictionary using path-like key.
    
    Args:
        data: Dictionary to modify
        key: Nested key in format "x/y/z"
        
    Returns:
        True if key was found and removed, False otherwise
        
    Example:
        >>> data = {"config": {"server": {"port": 8080, "host": "localhost"}}}
        >>> nested_remove(data, "config/server/port")
        True
        >>> data
        {'config': {'server': {'host': 'localhost'}}}
    """
    if not key:
        return False
    
    parts = key.split('/')
    current = data
    
    try:
        # Navigate to parent of target key
        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False  # Path doesn't exist
        
        # Remove the final key if it exists
        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
            return True
        else:
            return False
    except (KeyError, TypeError):
        return False


def nested_update(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """
    Deep update target dictionary with source dictionary.
    Unlike dict.update(), this merges nested dictionaries recursively.
    
    Args:
        target: Dictionary to update (modified in place)
        source: Dictionary with values to merge in
        
    Example:
        >>> target = {"config": {"server": {"port": 8080}}}
        >>> source = {"config": {"server": {"host": "localhost"}, "client": {"timeout": 30}}}
        >>> nested_update(target, source)
        >>> target
        {'config': {'server': {'port': 8080, 'host': 'localhost'}, 'client': {'timeout': 30}}}
    """
    for key, value in source.items():
        if (key in target and 
            isinstance(target[key], dict) and 
            isinstance(value, dict)):
            # Recursively merge nested dictionaries
            nested_update(target[key], value)
        else:
            # Direct assignment for non-dict values or new keys
            target[key] = value