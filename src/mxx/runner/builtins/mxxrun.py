


"""
MXX App Runner plugin for launching registered applications.

This plugin loads applications from the MXX app registry and launches them
with proper configuration override handling.
"""

import os
import subprocess
from pathlib import Path
from mxx.runner.core.plugin import MxxPlugin, hook
from mxx.cfg_tool.registry import get_app_by_name, load_json_config, save_json_config
from mxx.utils.nested import nested_set


class MxxRun(MxxPlugin):
    """
    Registered application launcher plugin.
    
    Loads applications from the MXX app registry (~/.mxx/apps) and launches them
    with configuration overrides applied. Supports automatic config modification
    and application termination.
    
    Config Key: "mxxrun"
    
    Example Configuration:
        ```toml
        [mxxrun]
        app_name = "myapp"  # Name/alias from registry
        temp_config = true  # Optional: use temporary config copy
        ```
    """
    
    __cmdname__ = "mxxrun"

    def __init__(self, app_name: str = None, temp_config: bool = False, **kwargs):
        super().__init__()
        self.app_name = app_name
        self.temp_config = temp_config
        self.app_info = None
        self.executable_path = None
        self.config_path = None
        self.original_config_path = None
        
        # Validation
        if not self.app_name:
            raise ValueError("app_name must be specified for MxxRun configuration.")

    @hook("pre_action")
    def load_and_prepare_app(self, runner):
        """
        Load app from registry and prepare configuration with overrides.
        
        Raises:
            ValueError: If app not found in registry
            FileNotFoundError: If app executable or config not found
        """
        # Load app from registry
        self.app_info = get_app_by_name(self.app_name)
        if not self.app_info:
            raise ValueError(f"Application '{self.app_name}' not found in MXX registry")
        
        app_config = self.app_info["config"]
        
        # Resolve paths from registry
        app_path = Path(app_config["path"])
        self.executable_path = app_path / app_config["app"]
        self.original_config_path = app_path / app_config["cfgroute"]
        
        # Validate paths exist
        if not self.executable_path.exists():
            raise FileNotFoundError(f"App executable not found at {self.executable_path}")
        if not self.original_config_path.exists():
            raise FileNotFoundError(f"App config folder not found at {self.original_config_path}")
        
        # Apply config overrides if any exist
        if app_config.get("cfgow"):
            self._apply_config_overrides(app_config["cfgow"])

    def _apply_config_overrides(self, overrides):
        """
        Apply configuration overrides to all JSON files in config folder.
        
        Args:
            overrides: Dictionary of nested key->value overrides
        """
        import shutil
        import tempfile
        
        if self.temp_config:
            # Create temporary config copy
            temp_dir = Path(tempfile.mkdtemp(prefix="mxx_config_"))
            shutil.copytree(self.original_config_path, temp_dir / "config")
            self.config_path = temp_dir / "config"
        else:
            # Modify original config in place
            self.config_path = self.original_config_path
        
        # Apply overrides to all JSON files
        for json_file in self.config_path.rglob("*.json"):
            try:
                config_data = load_json_config(json_file)
                
                # Apply each override
                for override_key, override_value in overrides.items():
                    nested_set(config_data, override_key, override_value)
                
                # Save modified config
                save_json_config(json_file, config_data)
                
            except Exception as e:
                print(f"Warning: Could not apply overrides to {json_file.name}: {e}")

    @hook("action")
    def launch_application(self, runner):
        """
        Launch the registered application in detached mode.
        """
        self._open_detached([str(self.executable_path)])

    @hook("post_action")
    def cleanup(self, runner):
        """
        Clean up temporary files and terminate the application.
        """
        # Clean up temporary config if used
        if self.temp_config and self.config_path and self.config_path != self.original_config_path:
            import shutil
            try:
                shutil.rmtree(self.config_path.parent)
            except Exception as e:
                print(f"Warning: Could not clean up temporary config: {e}")
        
        # Terminate the application using executable name from registry
        if self.app_info:
            executable_name = Path(self.app_info["config"]["app"]).name
            os.system(f"taskkill /IM {executable_name} /F")

    @staticmethod
    def _open_detached(args):
        """
        Open a process in detached mode (doesn't block).
        
        Args:
            args: List of command arguments, first element is the executable path
        """
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            args,
            creationflags=DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )

