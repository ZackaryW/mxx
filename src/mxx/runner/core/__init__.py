"""
MXX Runner Core - Core components for the plugin system.

This module contains the essential components for the MXX plugin architecture:
- MxxRunner: Main execution engine
- MxxPlugin: Base plugin class
- Hook system: Lifecycle event decorators
- Registry: Plugin discovery and management
- Callstack: Plugin execution ordering
"""

from mxx.runner.core.runner import MxxRunner
from mxx.runner.core.plugin import MxxPlugin, hook
from mxx.runner.core.registry import MAPPINGS
from mxx.runner.core.callstack import MxxCallstack, PluginCallstackMeta
from mxx.runner.core.config_loader import load_config

__all__ = [
    "MxxRunner", 
    "MxxPlugin", 
    "hook", 
    "MAPPINGS", 
    "MxxCallstack", 
    "PluginCallstackMeta",
    "load_config"
]