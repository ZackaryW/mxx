"""
Test configuration file loading (YAML, TOML, JSON).

Tests verify that configuration can be loaded from external files
and used with the MxxRunner system.
"""

import pytest
import tempfile
import time
from pathlib import Path

from mxx.runner.core.runner import MxxRunner
from mxx.runner.core.callstack import PluginCallstackMeta
from mxx.runner.core.config_loader import load_config


# Helper functions for checking optional dependency availability

def _has_toml_support() -> bool:
    """Check if TOML support is available."""
    try:
        import tomli  # noqa
        return True
    except ImportError:
        try:
            import tomllib  # noqa
            return True
        except ImportError:
            return False


def _has_yaml_support() -> bool:
    """Check if YAML support is available."""
    try:
        import yaml  # noqa
        return True
    except ImportError:
        return False


class TestConfigFileFormats:
    """Test loading configuration from different file formats."""
    
    def test_load_json_config(self):
        """Test loading configuration from JSON file."""
        config_content = """{
    "lifetime": {
        "lifetime": 2
    },
    "os": {
        "cmd": "echo test",
        "kill": null
    }
}"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cfg = load_config(config_path)
            
            assert "lifetime" in cfg
            assert cfg["lifetime"]["lifetime"] == 2
            assert "os" in cfg
            assert cfg["os"]["cmd"] == "echo test"
        finally:
            Path(config_path).unlink()
    
    @pytest.mark.skipif(not _has_toml_support(), reason="TOML support not available")
    def test_load_toml_config(self):
        """Test loading configuration from TOML file."""
        config_content = """[lifetime]
lifetime = 2

[os]
cmd = "echo test"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cfg = load_config(config_path)
            
            assert "lifetime" in cfg
            assert cfg["lifetime"]["lifetime"] == 2
            assert "os" in cfg
            assert cfg["os"]["cmd"] == "echo test"
        finally:
            Path(config_path).unlink()
    
    @pytest.mark.skipif(not _has_yaml_support(), reason="YAML support not available")
    def test_load_yaml_config(self):
        """Test loading configuration from YAML file."""
        config_content = """lifetime:
  lifetime: 2

os:
  cmd: echo test
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cfg = load_config(config_path)
            
            assert "lifetime" in cfg
            assert cfg["lifetime"]["lifetime"] == 2
            assert "os" in cfg
            assert cfg["os"]["cmd"] == "echo test"
        finally:
            Path(config_path).unlink()
    
    def test_load_nonexistent_file(self):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_config.json")
    
    def test_load_unsupported_format(self):
        """Test that unsupported file format raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test")
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported config file format"):
                load_config(config_path)
        finally:
            Path(config_path).unlink()


class TestRunnerWithConfigFiles:
    """Test MxxRunner with configuration loaded from files."""
    
    def test_runner_with_json_config(self):
        """Test running MxxRunner with JSON configuration file."""
        PluginCallstackMeta._callstackMap.clear()
        
        config_content = """{
    "lifetime": {
        "lifetime": 1
    },
    "os": {
        "cmd": "echo Testing JSON config"
    }
}"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cfg = load_config(config_path)
            
            runner = MxxRunner()
            start_time = time.time()
            runner.run(cfg)
            elapsed = time.time() - start_time
            
            # Should run for approximately 1 second
            assert 0.5 < elapsed < 2.5, f"Expected ~1s runtime, got {elapsed}s"
        finally:
            Path(config_path).unlink()
    
    @pytest.mark.skipif(not _has_toml_support(), reason="TOML support not available")
    def test_runner_with_toml_config(self):
        """Test running MxxRunner with TOML configuration file."""
        PluginCallstackMeta._callstackMap.clear()
        
        config_content = """[lifetime]
lifetime = 1

[os]
cmd = "echo Testing TOML config"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cfg = load_config(config_path)
            
            runner = MxxRunner()
            start_time = time.time()
            runner.run(cfg)
            elapsed = time.time() - start_time
            
            # Should run for approximately 1 second
            assert 0.5 < elapsed < 2.5, f"Expected ~1s runtime, got {elapsed}s"
        finally:
            Path(config_path).unlink()
    
    @pytest.mark.skipif(not _has_yaml_support(), reason="YAML support not available")
    def test_runner_with_yaml_config(self):
        """Test running MxxRunner with YAML configuration file."""
        PluginCallstackMeta._callstackMap.clear()
        
        config_content = """lifetime:
  lifetime: 1

os:
  cmd: echo Testing YAML config
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cfg = load_config(config_path)
            
            runner = MxxRunner()
            start_time = time.time()
            runner.run(cfg)
            elapsed = time.time() - start_time
            
            # Should run for approximately 1 second
            assert 0.5 < elapsed < 2.5, f"Expected ~1s runtime, got {elapsed}s"
        finally:
            Path(config_path).unlink()
    
    def test_runner_with_complex_config(self):
        """Test runner with more complex configuration including all plugin types."""
        PluginCallstackMeta._callstackMap.clear()
        
        config_content = """{
    "lifetime": {
        "lifetime": 1
    },
    "os": {
        "cmd": "echo Complex config test"
    },
    "app": {
        "scoop": false,
        "path": "C:/Tools",
        "targetExe": "tool.exe",
        "delay": 5
    }
}"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cfg = load_config(config_path)
            
            # Verify all plugins are configured
            assert "lifetime" in cfg
            assert "os" in cfg
            assert "app" in cfg
            
            # Verify nested values
            assert cfg["app"]["scoop"] is False
            assert cfg["app"]["path"] == "C:/Tools"
            assert cfg["app"]["delay"] == 5
        finally:
            Path(config_path).unlink()


class TestConfigValidation:
    """Test configuration validation and error handling."""
    
    def test_invalid_json_syntax(self):
        """Test that invalid JSON syntax raises an error."""
        config_content = """{
    "lifetime": {
        "lifetime": 2
    }  # Invalid comment in JSON
}"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            with pytest.raises(Exception):  # json.JSONDecodeError
                load_config(config_path)
        finally:
            Path(config_path).unlink()
    
    @pytest.mark.skipif(not _has_toml_support(), reason="TOML support not available")
    def test_invalid_toml_syntax(self):
        """Test that invalid TOML syntax raises an error."""
        config_content = """[lifetime
lifetime = 2  # Missing closing bracket
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            with pytest.raises(Exception):  # TOMLDecodeError
                load_config(config_path)
        finally:
            Path(config_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

