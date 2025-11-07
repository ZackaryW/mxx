import click
import uuid
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from pprint import pprint
from .registry import load_apps_registry, save_apps_registry, get_apps_registry_paths, get_app_by_name, load_json_config, save_json_config
from mxx.utils.nested import nested_set

@click.group()
def app():
    """MXX App Registry Tool"""
    pass

@app.command()
@click.argument("path")
@click.argument("app")
@click.argument("cfgroute")
@click.option("-cfgow","--cfgoverwrite", multiple=True, help="Configuration overrides in KEY=VALUE format")
@click.option("--alias", multiple=True, help="Aliases for the application")
@click.option("-cfge", "--cfgexclude", multiple=True, help="Configuration keys to exclude")
def register(path, app, cfgroute, cfgoverwrite, alias, cfgexclude):
    """Register an application
    
    Arguments:
        PATH - Path to the application folder
        APP - Executable name relative to the path
        CFGROUTE - Configuration route
    """
    # Load existing registries
    apps_index, aliases_index = load_apps_registry()
    
    # Generate a simple UID
    simple_uid = str(uuid.uuid4())
    
    # Parse configuration overrides into a dictionary
    cfgow_dict = {}
    for override in cfgoverwrite:
        if "=" in override:
            key, value = override.split("=", 1)
            cfgow_dict[key] = value
        else:
            click.echo(f"Warning: Invalid configuration override format '{override}'. Expected KEY=VALUE", err=True)
    
    # Create the app entry
    app_entry = {
        "path": str(Path(path).resolve()),
        "app": app,
        "cfgroute": cfgroute,
        "cfgow": cfgow_dict
    }
    
    # Add configuration exclusions if provided
    if cfgexclude:
        app_entry["cfge"] = list(cfgexclude)
    
    # Add to apps index
    apps_index[simple_uid] = app_entry
    
    # Handle aliases
    if alias:
        # Use provided aliases
        for a in alias:
            aliases_index[a] = simple_uid
    else:
        # Use app executable name if no aliases provided
        app_name = Path(app).stem
        aliases_index[app_name] = simple_uid
    
    # Save both registries
    save_apps_registry(apps_index, aliases_index)
    
    # Get registry location for feedback
    apps_index_path, _ = get_apps_registry_paths()
    apps_dir = apps_index_path.parent
    
    # Provide feedback
    click.echo("Successfully registered application:")
    click.echo(f"  UID: {simple_uid}")
    click.echo(f"  Path: {app_entry['path']}")
    click.echo(f"  App: {app_entry['app']}")
    click.echo(f"  Config route: {cfgroute}")
    if cfgow_dict:
        click.echo(f"  Config overrides: {cfgow_dict}")
    if cfgexclude:
        click.echo(f"  Config exclusions: {list(cfgexclude)}")
    
    if alias:
        click.echo(f"  Aliases: {', '.join(alias)}")
    else:
        click.echo(f"  Alias: {Path(app).stem}")
    
    click.echo(f"  Registry location: {apps_dir}")


@app.command()
@click.argument("name", required=True)
def get(name):
    """Get application configuration by name/alias"""
    app_info = get_app_by_name(name)
    
    if app_info:
        click.echo(f"Configuration for '{name}':")
        pprint(app_info)
    else:
        click.echo(f"Error: Application '{name}' not found in registry", err=True)


@app.command()
@click.argument("app_name")
@click.option("--temp-config", is_flag=True, help="Use temporary config copy (preserves original)")
@click.option("--no-overrides", is_flag=True, help="Skip applying configuration overrides")
def run(app_name, temp_config, no_overrides):
    """Run a registered application
    
    Arguments:
        APP_NAME - Name or alias of the registered application
    """
    try:
        # Load app from registry
        app_info = get_app_by_name(app_name)
        if not app_info:
            click.echo(f"Error: Application '{app_name}' not found in MXX registry", err=True)
            return
        
        app_config = app_info["config"]
        
        # Resolve paths from registry
        app_path = Path(app_config["path"])
        executable_path = app_path / app_config["app"]
        original_config_path = app_path / app_config["cfgroute"]
        
        # Validate paths exist
        if not executable_path.exists():
            click.echo(f"Error: App executable not found at {executable_path}", err=True)
            return
        if not original_config_path.exists():
            click.echo(f"Error: App config folder not found at {original_config_path}", err=True)
            return
        
        config_path = original_config_path
        temp_dir = None
        
        # Apply config overrides if any exist and not disabled
        if not no_overrides and app_config.get("cfgow"):
            click.echo("Applying configuration overrides...")
            
            if temp_config:
                # Create temporary config copy
                temp_dir = Path(tempfile.mkdtemp(prefix="mxx_config_"))
                shutil.copytree(original_config_path, temp_dir / "config")
                config_path = temp_dir / "config"
                click.echo(f"Using temporary config at: {config_path}")
            else:
                click.echo("Modifying original config in place")
            
            # Apply overrides to all JSON files
            overrides_applied = 0
            for json_file in config_path.rglob("*.json"):
                try:
                    config_data = load_json_config(json_file)
                    
                    # Apply each override
                    for override_key, override_value in app_config["cfgow"].items():
                        nested_set(config_data, override_key, override_value)
                        overrides_applied += 1
                    
                    # Save modified config
                    save_json_config(json_file, config_data)
                    
                except Exception as e:
                    click.echo(f"Warning: Could not apply overrides to {json_file.name}: {e}", err=True)
            
            click.echo(f"Applied {len(app_config['cfgow'])} override(s) to config files")
        
        # Launch the application
        click.echo(f"Launching application: {executable_path}")
        _open_detached([str(executable_path)])
        click.echo(f"Application '{app_name}' launched successfully")
        
        # Show cleanup information
        if temp_dir:
            click.echo("Temporary config will be cleaned up when the application terminates")
        if not no_overrides and app_config.get("cfgow") and not temp_config:
            click.echo("Warning: Original config was modified. Use --temp-config to preserve original.")
        
    except Exception as e:
        click.echo(f"Error running application '{app_name}': {e}", err=True)


@app.command()
@click.argument("app_name")
def stop(app_name):
    """Stop a running registered application
    
    Arguments:
        APP_NAME - Name or alias of the registered application
    """
    try:
        # Load app from registry
        app_info = get_app_by_name(app_name)
        if not app_info:
            click.echo(f"Error: Application '{app_name}' not found in MXX registry", err=True)
            return
        
        app_config = app_info["config"]
        executable_name = Path(app_config["app"]).name
        
        click.echo(f"Stopping application: {executable_name}")
        result = os.system(f"taskkill /IM {executable_name} /F")
        
        if result == 0:
            click.echo(f"Application '{app_name}' stopped successfully")
        else:
            click.echo(f"Warning: Could not stop application '{app_name}' (may not be running)", err=True)
            
    except Exception as e:
        click.echo(f"Error stopping application '{app_name}': {e}", err=True)


@app.command()
def open_folder():
    """Open the apps registry folder"""
    apps_index_path, _ = get_apps_registry_paths()
    apps_dir = apps_index_path.parent
    
    # Ensure directory exists
    apps_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        subprocess.run(["explorer", str(apps_dir)], check=True)
        click.echo(f"Opened registry folder: {apps_dir}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error opening folder: {e}", err=True)
    except FileNotFoundError:
        click.echo(f"Could not open folder. Path: {apps_dir}", err=True)


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


