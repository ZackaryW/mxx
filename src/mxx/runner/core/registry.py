
from pathlib import Path
import importlib.util
import sys
import logging
from mxx.runner.builtins.lifetime import Lifetime
from mxx.runner.builtins.os_exec import OSExec
from mxx.runner.builtins.app_launcher import AppLauncher
from mxx.runner.builtins.mxxrun import MxxRun
from mxx.runner.builtins.mxxset import MxxSet
from mxx.runner.core.plugin import BasePlugin

#home/.mxx/plugins
PLUGIN_PATH = Path.home() / ".mxx" / "plugins"

BUILTIN_MAPPINGS = {
    "lifetime": Lifetime,
    "os": OSExec,
    "app": AppLauncher,
    "mxxrun": MxxRun,
    "mxxset": MxxSet,
}

# Start with builtins, will be extended with custom plugins from PLUGIN_PATH
MAPPINGS = BUILTIN_MAPPINGS.copy()


def _load_custom_plugins():
    """
    Load custom plugins from ~/.mxx/plugins/*.py
    
    Scans the plugins directory for Python files and loads classes
    that inherit from BasePlugin.
    """
    if not PLUGIN_PATH.exists():
        PLUGIN_PATH.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created plugin directory: {PLUGIN_PATH}")
        return
    
    # Find all .py files in plugins directory
    plugin_files = list(PLUGIN_PATH.glob("*.py"))
    
    if not plugin_files:
        logging.debug(f"No custom plugins found in {PLUGIN_PATH}")
        return
    
    loaded_count = 0
    
    for plugin_file in plugin_files:
        # Skip __init__.py and private files
        if plugin_file.name.startswith("_"):
            continue
        
        try:
            # Load the module dynamically
            module_name = f"mxx.plugins.{plugin_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            
            if spec is None or spec.loader is None:
                logging.warning(f"Could not load spec for {plugin_file.name}")
                continue
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find all BasePlugin subclasses in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it's a class and inherits from BasePlugin
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr is not BasePlugin):
                    
                    # Use the plugin's name attribute or class name
                    plugin_name = getattr(attr, 'name', attr_name.lower())
                    
                    # Register the plugin
                    MAPPINGS[plugin_name] = attr
                    loaded_count += 1
                    logging.info(f"Loaded custom plugin '{plugin_name}' from {plugin_file.name}")
            
        except Exception as e:
            logging.error(f"Failed to load plugin from {plugin_file.name}: {e}", exc_info=True)
    
    if loaded_count > 0:
        logging.info(f"Loaded {loaded_count} custom plugin(s) from {PLUGIN_PATH}")


def initialize_registry():
    """
    Initialize the plugin registry by loading custom plugins.
    
    This should be called once at application startup.
    """
    _load_custom_plugins()


# Auto-initialize on import
initialize_registry()