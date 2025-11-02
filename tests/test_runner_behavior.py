"""
Test MxxRunner behavior and execution flow.

Tests:
- Configuration export (pcfg, gcfg)
- Plugin instantiation from config
- Callstack merging
- Hook execution order
- Lifecycle phase execution
- Error handling
"""

import pytest
from unittest.mock import patch
from mxx.runner.core.runner import MxxRunner
from mxx.runner.core.plugin import MxxPlugin, hook
from mxx.runner.core.callstack import PluginCallstackMeta, MxxCallstack


@pytest.fixture(autouse=True)
def clear_callstack_map():
    """Clear the callstack map before each test to allow plugin re-instantiation."""
    PluginCallstackMeta._callstackMap.clear()
    yield
    PluginCallstackMeta._callstackMap.clear()


class TestConfigurationExport:
    """Test configuration parsing and export."""
    
    def test_export_configs_with_plugin_config(self):
        """Test exporting plugin-specific configurations."""
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 3600},
            "os": {"cmd": "echo test", "kill": "test.exe"}
        }
        
        pcfg, gcfg = runner._exportCfgs(cfg)
        
        # Should have plugin configs
        assert "lifetime" in pcfg
        assert "os" in pcfg
        assert pcfg["lifetime"] == {"lifetime": 3600}
        assert pcfg["os"] == {"cmd": "echo test", "kill": "test.exe"}
    
    def test_export_configs_with_global_config(self):
        """Test exporting with global configuration mixed in."""
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 3600},
            "global_setting": "some_value",
            "another_global": 42
        }
        
        pcfg, gcfg = runner._exportCfgs(cfg)
        
        # Plugin configs
        assert "lifetime" in pcfg
        assert pcfg["lifetime"] == {"lifetime": 3600}
        
        # Global configs
        assert "global_setting" in gcfg
        assert "another_global" in gcfg
        assert gcfg["global_setting"] == "some_value"
        assert gcfg["another_global"] == 42
    
    def test_export_configs_empty(self):
        """Test exporting empty configuration."""
        runner = MxxRunner()
        
        cfg = {}
        
        pcfg, gcfg = runner._exportCfgs(cfg)
        
        assert pcfg == {}
        assert gcfg == {}


class TestPluginInstantiation:
    """Test plugin creation from configuration."""
    
    def test_run_creates_plugins(self):
        """Test that runner creates plugin instances from config."""
        # Clear callstack to avoid conflicts
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 100}
        }
        
        with patch.object(runner, 'run_events'):
            runner.run(cfg)
        
        # Verify plugin was created
        assert "lifetime" in runner.plugins
        assert runner.plugins["lifetime"].lifetime == 100
    
    def test_run_with_multiple_plugins(self):
        """Test runner creates multiple plugins."""
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 200},
            "os": {"cmd": "echo hello"}
        }
        
        with patch.object(runner, 'run_events'):
            runner.run(cfg)
        
        # Verify both plugins created
        assert "lifetime" in runner.plugins
        assert "os" in runner.plugins
        assert runner.plugins["lifetime"].lifetime == 200
        assert runner.plugins["os"].cmd == "echo hello"
    
    def test_run_with_unknown_plugin_ignores_it(self):
        """Test that unknown plugin name is treated as global config, not plugin."""
        runner = MxxRunner()
        
        cfg = {
            "unknown_plugin": {"param": "value"},
            "lifetime": {"lifetime": 100}
        }
        
        with patch.object(runner, 'run_events'):
            runner.run(cfg)
        
        # Unknown plugin should not be in plugins dict
        assert "unknown_plugin" not in runner.plugins
        # But should be in global config
        assert "unknown_plugin" in runner.gcfg
        # Known plugin should be in plugins
        assert "lifetime" in runner.plugins


class TestCallstackMerging:
    """Test callstack merging from multiple plugins."""
    
    def test_merge_callstacks(self):
        """Test merging callstacks from multiple plugins."""
        callstack1 = MxxCallstack()
        callstack1.action.append(lambda: "action1")
        callstack1.pre_action.append(lambda: "pre1")
        
        callstack2 = MxxCallstack()
        callstack2.action.append(lambda: "action2")
        callstack2.post_action.append(lambda: "post2")
        
        # Merge callstack2 into callstack1
        callstack1.merge(callstack2)
        
        # Verify merged results
        assert len(callstack1.action) == 2
        assert len(callstack1.pre_action) == 1
        assert len(callstack1.post_action) == 1
        
        assert callstack1.action[0]() == "action1"
        assert callstack1.action[1]() == "action2"


class TestHookExecution:
    """Test hook method execution."""
    
    def test_run_action_without_parameters(self):
        """Test _run_action with method that takes no parameters."""
        runner = MxxRunner()
        
        # Create a simple function with no parameters
        def no_param_func():
            return True
        
        result = runner._run_action(no_param_func)
        assert result is True
    
    def test_run_action_with_runner_parameter(self):
        """Test _run_action with method that takes runner parameter."""
        runner = MxxRunner()
        runner.test_value = "test"
        
        # Create a function that takes one parameter
        def with_param_func(runner_arg):
            return runner_arg.test_value
        
        result = runner._run_action(with_param_func)
        assert result == "test"


class TestLifecycleExecution:
    """Test runner lifecycle phase execution."""
    
    def test_on_true_on_false_loop(self):
        """Test on_true/on_false persistent checking after actions."""
        PluginCallstackMeta._callstackMap.clear()

        class TestPlugin(MxxPlugin):
            __cmdname__ = "test"

            def __init__(self):
                super().__init__()
                self.check_count = 0

            @hook("action")
            def do_action(self, runner):
                runner.action_executed = True

            @hook("on_true")
            def wait_condition(self, runner):
                self.check_count += 1
                return self.check_count <= 2  # Continue for 2 checks, then stop

        runner = MxxRunner()
        runner.action_executed = False

        plugin = TestPlugin()
        plugins = {"test": plugin}

        with patch('mxx.runner.core.runner.sleep'):  # Don't actually sleep
            runner.run_events(plugins)

        # Verify action was executed first, then on_true loop ran
        assert runner.action_executed is True
        assert plugin.check_count > 2
    
    def test_all_cond_blocks_execution(self):
        """Test that failing all_cond prevents action execution."""
        PluginCallstackMeta._callstackMap.clear()
        
        class TestPlugin(MxxPlugin):
            __cmdname__ = "test"
            
            def __init__(self):
                super().__init__()
            
            @hook("all_cond")
            def check_condition(self, runner):
                return False  # Always fail
            
            @hook("action")
            def do_action(self, runner):
                runner.action_executed = True
        
        runner = MxxRunner()
        runner.action_executed = False
        
        plugin = TestPlugin()
        plugins = {"test": plugin}
        
        runner.run_events(plugins)
        
        # Action should NOT have been executed
        assert runner.action_executed is False
    
    def test_execution_order(self):
        """Test that hooks execute in correct order."""
        PluginCallstackMeta._callstackMap.clear()
        
        execution_order = []
        
        class TestPlugin(MxxPlugin):
            __cmdname__ = "test"
            
            def __init__(self):
                super().__init__()
            
            @hook("pre_action")
            def pre(self, runner):
                execution_order.append("pre")
            
            @hook("action")
            def act(self, runner):
                execution_order.append("action")
            
            @hook("post_action")
            def post(self, runner):
                execution_order.append("post")
        
        runner = MxxRunner()
        plugin = TestPlugin()
        plugins = {"test": plugin}
        
        runner.run_events(plugins)
        
        # Verify execution order
        assert execution_order == ["pre", "action", "post"]


class TestErrorHandling:
    """Test error handling in runner."""
    
    def test_on_error_hook_called(self):
        """Test that on_error hooks are called on exception."""
        PluginCallstackMeta._callstackMap.clear()
        
        class TestPlugin(MxxPlugin):
            __cmdname__ = "test"
            
            def __init__(self):
                super().__init__()
                self.error_handled = False
            
            @hook("action")
            def failing_action(self, runner):
                raise ValueError("Test error")
            
            @hook("on_error")
            def handle_error(self, runner):
                self.error_handled = True
                assert isinstance(runner.currentError, ValueError)
        
        runner = MxxRunner()
        plugin = TestPlugin()
        plugins = {"test": plugin}
        
        runner.run_events(plugins)
        
        # Verify error handler was called
        assert plugin.error_handled is True


class TestRunnerIntegration:
    """Test full runner integration."""
    
    def test_full_run_cycle(self):
        """Test complete run cycle with real plugins."""
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 1}  # 1 second lifetime
        }
        
        with patch.object(runner, 'run_events') as mock_run_events:
            runner.run(cfg)
            
            # Verify run_events was called
            mock_run_events.assert_called_once()
            
            # Verify plugins were created
            assert "lifetime" in runner.plugins
            assert runner.plugins["lifetime"].lifetime == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
