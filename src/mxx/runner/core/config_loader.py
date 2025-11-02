"""
Configuration file loader for MXX runner.

Supports loading configuration from YAML, TOML, and JSON files.
Auto-detects format based on file extension.
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_config(filepath: str | Path) -> Dict[str, Any]:
    """
    Load configuration from a file.
    
    Supports:
    - YAML (.yaml, .yml)
    - TOML (.toml)
    - JSON (.json)
    
    Args:
        filepath: Path to configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If file format is unsupported
        ImportError: If required library for format is not installed
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")
    
    suffix = path.suffix.lower()
    
    if suffix == '.json':
        return _load_json(path)
    elif suffix == '.toml':
        return _load_toml(path)
    elif suffix in ['.yaml', '.yml']:
        return _load_yaml(path)
    else:
        raise ValueError(f"Unsupported config file format: {suffix}")


def _load_json(path: Path) -> Dict[str, Any]:
    """Load JSON configuration."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_toml(path: Path) -> Dict[str, Any]:
    """Load TOML configuration."""
    try:
        import tomli
    except ImportError:
        try:
            import tomllib as tomli  # Python 3.11+
        except ImportError:
            raise ImportError(
                "TOML support requires 'tomli' package. "
                "Install with: pip install tomli"
            )
    
    with open(path, 'rb') as f:
        return tomli.load(f)


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML configuration."""
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "YAML support requires 'pyyaml' package. "
            "Install with: pip install pyyaml"
        )
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
