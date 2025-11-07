import click
import shutil
from datetime import datetime
from pathlib import Path
from .registry import get_app_by_name, load_json_config, save_json_config
from mxx.utils.nested import nested_get, nested_set, nested_remove


@click.group()
def cfg():
    """Configuration Export/Import Tools"""
    pass


@cfg.command()
@click.argument("app_name")
@click.option("--output", "-o", help="Output name (default: uses timestamp)")
def export(app_name, output):
    """Export application configuration folder"""
    # Get app info
    app_info = get_app_by_name(app_name)
    if not app_info:
        click.echo(f"Error: Application '{app_name}' not found in registry", err=True)
        return
    
    app_config = app_info["config"]
    uid = app_info["uid"]
    
    # Get the source config folder path
    config_folder = Path(app_config["path"]) / app_config["cfgroute"]
    if not config_folder.exists():
        click.echo(f"Error: Config folder not found at {config_folder}", err=True)
        return
    
    if not config_folder.is_dir():
        click.echo(f"Error: {config_folder} is not a directory", err=True)
        return
    
    # Determine output location
    exports_base = Path.home() / ".mxx" / "exports" / uid
    exports_base.mkdir(parents=True, exist_ok=True)
    
    if output:
        output_dir = exports_base / output
    else:
        # Use timestamp as folder name when no output name specified
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = exports_base / timestamp
    
    # Copy the entire config folder
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(config_folder, output_dir)
    
    # Process all JSON files in the copied folder to apply exclusions and remove overrides
    processed_files = []
    for json_file in output_dir.rglob("*.json"):
        try:
            config_data = load_json_config(json_file)
            
            # Apply exclusions (remove cfge keys)
            if "cfge" in app_config:
                for exclude_key in app_config["cfge"]:
                    nested_remove(config_data, exclude_key)
            
            # Apply overrides (remove cfgow keys)
            if "cfgow" in app_config:
                for override_key in app_config["cfgow"]:
                    nested_remove(config_data, override_key)
            
            # Save the processed config
            save_json_config(json_file, config_data)
            processed_files.append(json_file.name)
        except Exception as e:
            click.echo(f"Warning: Could not process {json_file.name}: {e}", err=True)
    
    click.echo(f"Exported configuration folder for '{app_name}':")
    click.echo(f"  Source: {config_folder}")
    click.echo(f"  Output: {output_dir}")
    click.echo(f"  Processed {len(processed_files)} JSON files")
    click.echo(f"  Excluded {len(app_config.get('cfge', []))} key patterns")
    click.echo(f"  Removed {len(app_config.get('cfgow', {}))} override key patterns")


@cfg.command()
@click.argument("app_name")
@click.argument("import_folder")
def import_config(app_name, import_folder):
    """Import and merge configuration folder for an application"""
    # Get app info
    app_info = get_app_by_name(app_name)
    if not app_info:
        click.echo(f"Error: Application '{app_name}' not found in registry", err=True)
        return
    
    app_config = app_info["config"]
    
    # Get the target config folder path
    target_config_folder = Path(app_config["path"]) / app_config["cfgroute"]
    
    # Resolve import folder path - first try relative to app's exports directory
    uid = app_info["uid"]
    app_exports_dir = Path.home() / ".mxx" / "exports" / uid
    
    import_path = Path(import_folder)
    
    # If it's not an absolute path, try relative to app's exports directory first
    if not import_path.is_absolute():
        relative_import_path = app_exports_dir / import_folder
        if relative_import_path.exists() and relative_import_path.is_dir():
            import_path = relative_import_path
        # Otherwise keep the original path (which might be relative to current directory)
    
    if not import_path.exists():
        click.echo(f"Error: Import folder not found at {import_path}", err=True)
        if not import_path.is_absolute():
            click.echo(f"  Also tried: {app_exports_dir / import_folder}", err=True)
        return
    
    if not import_path.is_dir():
        click.echo(f"Error: {import_path} is not a directory", err=True)
        return
    
    # Ensure target config folder exists
    target_config_folder.mkdir(parents=True, exist_ok=True)
    
    # Process all JSON files in the import folder
    processed_files = []
    preserved_counts = {}
    
    for import_json_file in import_path.rglob("*.json"):
        try:
            # Get relative path to maintain folder structure
            rel_path = import_json_file.relative_to(import_path)
            target_json_file = target_config_folder / rel_path
            
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
            processed_files.append(rel_path)
            preserved_counts[str(rel_path)] = len(preserved_values)
            
        except Exception as e:
            click.echo(f"Warning: Could not process {import_json_file.name}: {e}", err=True)
    
    total_preserved = sum(preserved_counts.values())
    
    click.echo(f"Imported configuration folder for '{app_name}':")
    click.echo(f"  Import source: {import_path}")
    click.echo(f"  Target: {target_config_folder}")
    click.echo(f"  Processed {len(processed_files)} JSON files")
    click.echo(f"  Preserved {total_preserved} excluded keys across all files")
    click.echo(f"  Applied {len(app_config.get('cfgow', {}))} override patterns to all files")
