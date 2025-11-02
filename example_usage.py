"""
Example: Using MXX Runner with configuration files.

Demonstrates loading configuration from TOML, YAML, or JSON files.
"""

from mxx.runner.core.runner import MxxRunner
from mxx.runner.core.config_loader import load_config


def main():
    # Load configuration from file
    # Supports: .toml, .yaml, .yml, .json
    cfg = load_config("example_config.toml")
    
    # Or from other formats:
    # cfg = load_config("example_config.json")
    # cfg = load_config("example_config.yaml")
    
    # Create and run the runner
    runner = MxxRunner()
    runner.run(cfg)
    
    print("Runner completed!")


if __name__ == "__main__":
    main()
