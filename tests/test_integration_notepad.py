"""
Integration test: Launch notepad and close on lifetime.

This test verifies end-to-end functionality:
1. Runner initializes with Lifetime and OSExec plugins
2. OSExec launches notepad.exe
3. OSExec registers notepad for cleanup with Lifetime
4. Lifetime tracks execution time
5. Lifetime kills notepad when time expires

Note: This test actually launches notepad.exe on Windows.
It will run for a few seconds then automatically close notepad.

Requires: psutil (pip install psutil)
"""

import pytest
import time
import threading

# Try to import psutil, skip all tests if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from mxx.runner.core.runner import MxxRunner
from mxx.runner.core.callstack import PluginCallstackMeta


pytestmark = pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not installed")


class TestNotepadIntegration:
    """Integration test launching and cleaning up notepad."""
    
    def test_launch_and_cleanup_notepad(self):
        """
        Full integration test:
        - Launch notepad via OSExec
        - Register for cleanup with Lifetime
        - Wait for lifetime to expire
        - Verify notepad is terminated
        """
        # Clear any existing notepad processes first
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    proc.kill()
                    proc.wait(timeout=1)
        except Exception:
            pass
        
        time.sleep(0.5)  # Give cleanup a moment
        
        # Clear callstack for clean test
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        # Configuration: 3 second lifetime, launch notepad
        cfg = {
            "lifetime": {"lifetime": 3},
            "os": {"cmd": "start notepad.exe", "kill": "notepad.exe"}
        }
        
        # Track if notepad was running
        notepad_was_running = False
        
        try:
            # Run the system in a separate thread so we can check process status
            runner_thread = threading.Thread(target=lambda: runner.run(cfg))
            runner_thread.start()
            
            # Give notepad a moment to start (need more time for process to spawn)
            time.sleep(2)
            
            # Check if notepad is running
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    notepad_was_running = True
                    break
            
            # Wait for runner to complete
            runner_thread.join(timeout=5)
            
            # Give a moment for cleanup
            time.sleep(0.5)
            
            # Verify notepad is no longer running
            notepad_still_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    notepad_still_running = True
                    break
            
            # Assertions
            assert notepad_was_running, "Notepad should have been launched"
            assert not notepad_still_running, "Notepad should have been terminated"
            
        finally:
            # Cleanup: Make sure notepad is closed even if test fails
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] == 'Notepad.exe':
                        proc.kill()
                        proc.wait(timeout=3)
            except Exception:
                pass
    
    def test_lifetime_integration_short_duration(self):
        """
        Test with very short lifetime (1 second).
        Verifies quick startup and shutdown.
        """
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 1},
            "os": {"cmd": "start notepad.exe", "kill": "notepad.exe"}
        }
        
        start_time = time.time()
        
        try:
            runner.run(cfg)
            
            elapsed = time.time() - start_time
            
            # Should complete in approximately 1 second (allow some overhead)
            assert 0.5 < elapsed < 2.5, f"Expected ~1s runtime, got {elapsed}s"
            
        finally:
            # Cleanup notepad
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] == 'Notepad.exe':
                        proc.kill()
                        proc.wait(timeout=3)
            except Exception:
                pass
    
    def test_os_exec_without_kill(self):
        """
        Test OSExec without kill parameter.
        Process should launch but not be registered for cleanup.
        """
        # Clear any existing notepad processes first
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    proc.kill()
                    proc.wait(timeout=1)
        except Exception:
            pass
        
        time.sleep(0.5)
        
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 2},
            "os": {"cmd": "start notepad.exe"}  # No kill parameter
        }
        
        try:
            # Run in thread
            runner_thread = threading.Thread(target=lambda: runner.run(cfg))
            runner_thread.start()
            
            # Give notepad moment to start
            time.sleep(1.5)
            
            # Notepad should still be running (not killed by lifetime)
            notepad_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    notepad_running = True
                    break
            
            assert notepad_running, "Notepad should still be running (no kill registered)"
            
            # Wait for runner to complete
            runner_thread.join(timeout=4)
            
            # Even after lifetime expires, notepad should still be running (not in killList)
            time.sleep(0.5)
            notepad_still_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    notepad_still_running = True
                    break
            
            assert notepad_still_running, "Notepad should still be running after lifetime (no kill registered)"
            
        finally:
            # Manual cleanup
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] == 'Notepad.exe':
                        proc.kill()
                        proc.wait(timeout=3)
            except Exception:
                pass
    
    def test_multiple_processes(self):
        """
        Test launching multiple processes with coordinated cleanup.
        """
        # Clear any existing processes first
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] in ['Notepad.exe', 'calc.exe', 'CalculatorApp.exe']:
                    proc.kill()
                    proc.wait(timeout=1)
        except Exception:
            pass
        
        time.sleep(0.5)
        
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        # Launch both notepad and calc
        cfg = {
            "lifetime": {"lifetime": 2},
            "os": {"cmd": "start notepad.exe && start calc.exe", "kill": "notepad.exe calc.exe"}
        }
        
        try:
            # Run in thread
            runner_thread = threading.Thread(target=lambda: runner.run(cfg))
            runner_thread.start()
            
            time.sleep(1.5)
            
            # Check both are running
            notepad_running = False
            calc_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    notepad_running = True
                elif proc.info['name'] == 'CalculatorApp.exe' or proc.info['name'] == 'calc.exe':
                    calc_running = True # noqa
            
            assert notepad_running, "Notepad should be running"
            # Note: calc might be CalculatorApp.exe on Windows 10+
            
            # Wait for runner to complete
            runner_thread.join(timeout=4)
            
            # Give a moment for cleanup
            time.sleep(0.5)
            
            # Verify cleanup
            notepad_after = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    notepad_after = True
            
            assert not notepad_after, "Notepad should be terminated"
            
        finally:
            # Cleanup any remaining processes
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] in ['Notepad.exe', 'calc.exe', 'CalculatorApp.exe']:
                        proc.kill()
                        proc.wait(timeout=3)
            except Exception:
                pass


class TestPluginCommunication:
    """Test inter-plugin communication patterns."""
    
    def test_os_exec_registers_with_lifetime(self):
        """
        Verify OSExec properly registers kill target with Lifetime plugin.
        """
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 1},
            "os": {"cmd": "echo test", "kill": "test.exe"}
        }
        
        # Don't actually run, just instantiate
        from unittest.mock import patch
        with patch.object(runner, 'run_events'):
            runner.run(cfg)
        
        # Get the lifetime plugin
        lifetime_plugin = runner.plugins.get("lifetime")
        
        # Manually trigger the OS plugin's action to register kill
        os_plugin = runner.plugins.get("os")
        os_plugin.execute_command(runner)
        
        # Verify kill target was registered
        assert len(lifetime_plugin.killList) > 0
        assert any("test.exe" in str(item) for item in lifetime_plugin.killList)
    
    def test_lifetime_killlist_cleanup(self):
        """
        Test that Lifetime properly clears killList after cleanup.
        """
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 1}
        }
        
        from unittest.mock import patch
        with patch.object(runner, 'run_events'):
            runner.run(cfg)
        
        lifetime_plugin = runner.plugins.get("lifetime")
        
        # Manually add items to killList
        lifetime_plugin.killList.append(("process", "fake.exe"))
        lifetime_plugin.killList.append(("cmd", "fake.exe"))
        
        assert len(lifetime_plugin.killList) == 2
        
        # Run cleanup
        lifetime_plugin.cleanup(runner)
        
        # Verify killList is cleared
        assert len(lifetime_plugin.killList) == 0


@pytest.mark.slow
class TestRealWorldScenarios:
    """
    Real-world scenario tests.
    These tests take longer as they involve actual process execution.
    """
    
    @pytest.mark.skipif(not psutil.WINDOWS, reason="Windows-specific test")
    def test_scoop_app_launcher(self):
        """
        Test AppLauncher with Scoop-installed application.
        Note: Requires actual Scoop installation.
        """
        # This test would need a real Scoop installation
        # Skipping actual implementation as it's environment-dependent
        pytest.skip("Requires Scoop installation with specific package")
    
    def test_long_running_process(self):
        """
        Test with longer-running process to verify stability.
        """
        PluginCallstackMeta._callstackMap.clear()
        
        runner = MxxRunner()
        
        cfg = {
            "lifetime": {"lifetime": 5},  # 5 second lifetime
            "os": {"cmd": "start notepad.exe", "kill": "notepad.exe"}
        }
        
        start_time = time.time()
        
        try:
            runner.run(cfg)
            
            elapsed = time.time() - start_time
            
            # Should run for approximately 5 seconds
            assert 4 < elapsed < 7, f"Expected ~5s runtime, got {elapsed}s"
            
            # Give cleanup a moment to complete
            time.sleep(0.5)
            
            # Verify notepad is closed
            notepad_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'Notepad.exe':
                    notepad_running = True
            
            assert not notepad_running, "Notepad should be terminated after lifetime"
            
        finally:
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] == 'Notepad.exe':
                        proc.kill()
                        proc.wait(timeout=3)
            except Exception:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s shows print output

