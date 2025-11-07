"""
Configuration file utilities for MXX cfg_tool.

Provides independent components for loading and saving JSON configuration files.
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_json_config(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON configuration from file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the loaded configuration
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    if not file_path.exists():
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_config(file_path: Path, config: Dict[str, Any]) -> None:
    """
    Save configuration to JSON file.
    
    Args:
        file_path: Path where to save the JSON file
        config: Dictionary to save as JSON
        
    Raises:
        OSError: If the file cannot be written
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_apps_registry_paths() -> tuple[Path, Path]:
    """
    Get the standard paths for apps registry files.
    
    Returns:
        Tuple of (apps_index_path, aliases_index_path)
    """
    apps_dir = Path.home() / ".mxx" / "apps"
    apps_index_path = apps_dir / "apps.json"
    aliases_index_path = apps_dir / "aliases.json"
    
    return apps_index_path, aliases_index_path


def load_apps_registry() -> tuple[Dict[str, Any], Dict[str, str]]:
    """
    Load both apps and aliases registries.
    
    Returns:
        Tuple of (apps_index, aliases_index)
    """
    apps_index_path, aliases_index_path = get_apps_registry_paths()
    
    apps_index = load_json_config(apps_index_path)
    aliases_index = load_json_config(aliases_index_path)
    
    return apps_index, aliases_index


def save_apps_registry(apps_index: Dict[str, Any], aliases_index: Dict[str, str]) -> None:
    """
    Save both apps and aliases registries.
    
    Args:
        apps_index: Apps registry dictionary
        aliases_index: Aliases registry dictionary
    """
    apps_index_path, aliases_index_path = get_apps_registry_paths()
    
    save_json_config(apps_index_path, apps_index)
    save_json_config(aliases_index_path, aliases_index)


def get_app_by_name(name: str) -> Dict[str, Any] | None:
    """
    Get application configuration by name/alias.
    
    Args:
        name: Application name or alias
        
    Returns:
        Dictionary containing app info with keys: name, uid, config
        Returns None if app not found
    """
    apps_index, aliases_index = load_apps_registry()
    
    # Check if name is an alias
    if name in aliases_index:
        uid = aliases_index[name]
        if uid in apps_index:
            app_config = apps_index[uid]
            return {
                "name": name,
                "uid": uid,
                "config": app_config
            }
    
    return None
