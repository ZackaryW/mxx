import click
import uuid
from pathlib import Path
from pprint import pprint
from .registry import load_apps_registry, save_apps_registry, get_apps_registry_paths, get_app_by_name

@click.group()
def app():
    """MXX App Registry Tool"""
    pass

@app.command()
@click.argument("path", help="Path to the application folder")
@click.argument("app", help="Executable name relative to the path")
@click.argument("cfgroute", help="Configuration route")
@click.option("-cfgow","--cfgoverwrite", multiple=True, help="Configuration overrides in KEY=VALUE format")
@click.option("--alias", multiple=True, help="Aliases for the application")
@click.option("-cfge", "--cfgexclude", multiple=True, help="Configuration keys to exclude")
def register(path, app, cfgroute, cfgoverwrite, alias, cfgexclude):
    """Register an application"""
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
def open_folder():
    """Open the apps registry folder"""
    import subprocess
    
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
