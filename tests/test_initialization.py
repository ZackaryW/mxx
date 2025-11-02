"""
Test plugin initialization and basic assertions.

Tests:
- Plugin instantiation with configuration
- __cmdname__ class attribute presence
- Callstack registration via metaclass
- Hook decorator registration
- Configuration validation
"""

import pytest
from mxx.runner.core.plugin import MxxPlugin, hook
from mxx.runner.core.callstack import PluginCallstackMeta
from mxx.runner.builtins.lifetime import Lifetime
from mxx.runner.builtins.os_exec import OSExec
from mxx.runner.builtins.app_launcher import AppLauncher


@pytest.fixture(autouse=True)
def clear_callstack_map():
    """Clear the callstack map before each test to allow plugin re-instantiation."""
    PluginCallstackMeta._callstackMap.clear()
    yield
    # Optionally clear after as well
    PluginCallstackMeta._callstackMap.clear()


class TestPluginInitialization:
    """Test basic plugin instantiation and configuration."""
    
    def test_lifetime_initialization(self):
        """Test Lifetime plugin accepts configuration."""
        plugin = Lifetime(lifetime=3600)
        
        assert plugin.__cmdname__ == "lifetime"
        assert plugin.lifetime == 3600
        assert plugin.killList == []
        assert plugin.targetStopTime is None
    
    def test_lifetime_initialization_defaults(self):
        """Test Lifetime plugin with default/no config."""
        plugin = Lifetime()
        
        assert plugin.__cmdname__ == "lifetime"
        assert plugin.lifetime is None
        assert plugin.killList == []
    
    def test_os_exec_initialization(self):
        """Test OSExec plugin accepts configuration."""
        plugin = OSExec(cmd="echo test", kill="test.exe")
        
        assert plugin.__cmdname__ == "os"
        assert plugin.cmd == "echo test"
        assert plugin.kill == "test.exe"
    
    def test_os_exec_initialization_defaults(self):
        """Test OSExec plugin with defaults."""
        plugin = OSExec()
        
        assert plugin.__cmdname__ == "os"
        assert plugin.cmd is None
        assert plugin.kill is None
    
    def test_app_launcher_initialization_scoop(self):
        """Test AppLauncher plugin with Scoop configuration."""
        plugin = AppLauncher(scoop=True, pkg="notepad", targetExe="notepad.exe")
        
        assert plugin.__cmdname__ == "app"
        assert plugin.scoop is True
        assert plugin.pkg == "notepad"
        assert plugin.targetExe == "notepad.exe"
        assert plugin.delay == 10
    
    def test_app_launcher_initialization_custom_path(self):
        """Test AppLauncher plugin with custom path configuration."""
        plugin = AppLauncher(
            scoop=False,
            path="C:/Tools",
            targetExe="tool.exe",
            delay=5
        )
        
        assert plugin.__cmdname__ == "app"
        assert plugin.scoop is False
        assert plugin.path == "C:/Tools"
        assert plugin.targetExe == "tool.exe"
        assert plugin.delay == 5


class TestPluginValidation:
    """Test plugin configuration validation."""
    
    def test_app_launcher_missing_target_exe(self):
        """Test AppLauncher fails without targetExe."""
        with pytest.raises(ValueError, match="targetExe must be specified"):
            AppLauncher(scoop=True, pkg="test")
    
    def test_app_launcher_scoop_missing_pkg(self):
        """Test AppLauncher fails when scoop=True without pkg."""
        with pytest.raises(ValueError, match="pkg must be specified"):
            AppLauncher(scoop=True, targetExe="test.exe")
    
    def test_app_launcher_scoop_with_path(self):
        """Test AppLauncher fails when scoop=True with path specified."""
        with pytest.raises(ValueError, match="path should not be specified"):
            AppLauncher(scoop=True, pkg="test", path="C:/Test", targetExe="test.exe")


class TestCallstackRegistration:
    """Test metaclass callstack registration."""
    
    def test_callstack_created_on_instantiation(self):
        """Test that metaclass creates callstack entry."""
        plugin = Lifetime(lifetime=100) # noqa
        
        # Check callstack was registered
        assert "lifetime" in PluginCallstackMeta._callstackMap
        callstack = PluginCallstackMeta._callstackMap["lifetime"]
        
        # Verify callstack has expected structure
        assert hasattr(callstack, 'any_cond')
        assert hasattr(callstack, 'all_cond')
        assert hasattr(callstack, 'action')
        assert hasattr(callstack, 'pre_action')
        assert hasattr(callstack, 'post_action')
        assert hasattr(callstack, 'on_true')
        assert hasattr(callstack, 'on_false')
        assert hasattr(callstack, 'on_error')
    
    def test_hook_methods_registered(self):
        """Test that hook-decorated methods are registered in callstack."""
        # Create fresh plugin instance
        plugin = OSExec(cmd="test")
        
        callstack = PluginCallstackMeta._callstackMap["os"]
        
        # OSExec has @hook("action") on execute_command
        assert len(callstack.action) > 0
        
        # Verify the method is actually from the plugin
        action_method = callstack.action[0]
        assert hasattr(action_method, '__self__')
        assert action_method.__self__ == plugin
    
    def test_cmdname_is_class_attribute(self):
        """Test that __cmdname__ is a class attribute, not instance."""
        # Should be accessible on class
        assert Lifetime.__cmdname__ == "lifetime"
        assert OSExec.__cmdname__ == "os"
        assert AppLauncher.__cmdname__ == "app"
        
        # Should also be accessible on instance
        plugin = Lifetime()
        assert plugin.__cmdname__ == "lifetime"
    
    def test_duplicate_plugin_raises_error(self):
        """Test that creating duplicate plugin raises exception."""
        # Clear the callstack map first
        PluginCallstackMeta._callstackMap.clear()
        
        # First instance should succeed
        plugin1 = Lifetime(lifetime=100) # noqa
        
        # Second instance with same __cmdname__ should fail
        with pytest.raises(Exception, match="Callstack for plugin 'lifetime' is already created"):
            plugin2 = Lifetime(lifetime=200) # noqa


class TestHookDecorator:
    """Test hook decorator functionality."""
    
    def test_hook_adds_attribute(self):
        """Test that @hook decorator adds _mxx_hook_types attribute."""
        
        class TestPlugin(MxxPlugin):
            __cmdname__ = "test"
            
            def __init__(self):
                super().__init__()
            
            @hook("action")
            def my_action(self, runner):
                pass
        
        # Clear callstack for test
        PluginCallstackMeta._callstackMap.clear()
        
        plugin = TestPlugin()
        
        # Check the method has the hook attribute
        assert hasattr(plugin.my_action, '_mxx_hook_types')
        assert plugin.my_action._mxx_hook_types == "action"
    
    def test_invalid_hook_type_raises_error(self):
        """Test that invalid hook type raises exception."""
        
        with pytest.raises(Exception, match="Invalid hook type"):
            
            class BadPlugin(MxxPlugin):
                __cmdname__ = "bad"
                
                def __init__(self):
                    super().__init__()
                
                @hook("invalid_hook_type")
                def bad_hook(self, runner):
                    pass
            
            PluginCallstackMeta._callstackMap.clear()
            plugin = BadPlugin() # noqa


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
