"""
MXX Config Set plugin for importing configurations to registered applications.

This plugin imports configuration folders/files to registered applications,
similar to the mxx cfg import command but usable within runner workflows.
"""

from pathlib import Path
from mxx.runner.core.plugin import MxxPlugin, hook
from mxx.cfg_tool.registry import get_app_by_name, load_json_config, save_json_config
from mxx.utils.nested import nested_get, nested_set


class MxxSet(MxxPlugin):
    """
    Configuration import plugin for registered applications.
    
    Imports and merges configuration folders for registered applications,
    preserving excluded keys and applying overrides. This provides the same
    functionality as `mxx cfg import` but within runner workflows.
    
    Config Key: "mxxset"
    
    Example Configuration:
        ```toml
        [mxxset]
        app_name = "myapp"           # Name/alias from registry
        import_source = "backup1"    # Import folder (relative to exports or absolute)
        ```
    """
    
    __cmdname__ = "mxxset"

    def __init__(self, app_name: str = None, import_source: str = None, **kwargs):
        super().__init__()
        self.app_name = app_name
        self.import_source = import_source
        self.app_info = None
        
        # Validation
        if not self.app_name:
            raise ValueError("app_name must be specified for MxxSet configuration.")
        if not self.import_source:
            raise ValueError("import_source must be specified for MxxSet configuration.")

    @hook("action")
    def import_configuration(self, runner):
        """
        Import and merge configuration for the registered application.
        
        Loads the app from registry, resolves import source path, and performs
        the same smart merge as the cfg import command.
        
        Raises:
            ValueError: If app not found in registry
            FileNotFoundError: If import source not found
        """
        # Load app from registry
        self.app_info = get_app_by_name(self.app_name)
        if not self.app_info:
            raise ValueError(f"Application '{self.app_name}' not found in MXX registry")
        
        app_config = self.app_info["config"]
        uid = self.app_info["uid"]
        
        # Get target config folder path
        target_config_folder = Path(app_config["path"]) / app_config["cfgroute"]
        
        # Resolve import path - first try relative to app's exports directory
        import_path = self._resolve_import_path(uid)
        
        if not import_path.exists():
            raise FileNotFoundError(f"Import source not found at {import_path}")
        
        if not import_path.is_dir():
            raise ValueError(f"Import source is not a directory: {import_path}")
        
        # Ensure target config folder exists
        target_config_folder.mkdir(parents=True, exist_ok=True)
        
        # Import configuration
        self._import_config_folder(import_path, target_config_folder, app_config)

    def _resolve_import_path(self, uid: str) -> Path:
        """
        Resolve import source path, trying exports directory first.
        
        Args:
            uid: App UID for exports directory resolution
            
        Returns:
            Resolved Path object
        """
        import_path = Path(self.import_source)
        
        # If not absolute, try relative to app's exports directory first
        if not import_path.is_absolute():
            app_exports_dir = Path.home() / ".mxx" / "exports" / uid
            relative_import_path = app_exports_dir / self.import_source
            
            if relative_import_path.exists() and relative_import_path.is_dir():
                return relative_import_path
        
        return import_path

    def _import_config_folder(self, import_path: Path, target_path: Path, app_config: dict):
        """
        Import configuration folder with smart merging.
        
        Args:
            import_path: Source folder to import from
            target_path: Target folder to import to
            app_config: App configuration containing cfge and cfgow settings
        """
        processed_files = 0
        total_preserved = 0
        
        # Process all JSON files in the import folder
        for import_json_file in import_path.rglob("*.json"):
            try:
                # Get relative path to maintain folder structure
                rel_path = import_json_file.relative_to(import_path)
                target_json_file = target_path / rel_path
                
                # Ensure target directory exists
                target_json_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Load import data
                import_config_data = load_json_config(import_json_file)
                
                # Load existing target config or create empty
                if target_json_file.exists():
                    target_config = load_json_config(target_json_file)
                else:
                    target_config = {}
                
                # Preserve excluded keys (cfge) from target
                preserved_values = {}
                if "cfge" in app_config:
                    for exclude_key in app_config["cfge"]:
                        value = nested_get(target_config, exclude_key)
                        if value is not None:
                            preserved_values[exclude_key] = value
                
                # Update target config with imported data
                target_config.update(import_config_data)
                
                # Restore preserved excluded keys
                for key, value in preserved_values.items():
                    nested_set(target_config, key, value)
                
                # Apply overrides (cfgow)
                if "cfgow" in app_config:
                    for override_key, override_value in app_config["cfgow"].items():
                        nested_set(target_config, override_key, override_value)
                
                # Save updated config
                save_json_config(target_json_file, target_config)
                
                processed_files += 1
                total_preserved += len(preserved_values)
                
            except Exception as e:
                print(f"Warning: Could not process {import_json_file.name}: {e}")
        
        print(f"MxxSet imported configuration for '{self.app_name}':")
        print(f"  Source: {import_path}")
        print(f"  Target: {target_path}")
        print(f"  Processed {processed_files} JSON files")
        print(f"  Preserved {total_preserved} excluded keys")
        print(f"  Applied {len(app_config.get('cfgow', {}))} override patterns")
