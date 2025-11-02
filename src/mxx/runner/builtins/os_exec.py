"""
OS command execution plugin for running arbitrary system commands.

This plugin executes system commands at startup and optionally registers
processes for cleanup via the lifetime plugin.
"""

import os
from mxx.runner.core.plugin import MxxPlugin, hook


class OSExec(MxxPlugin):
    """
    System command execution plugin.
    
    Executes arbitrary OS commands at startup and optionally registers
    processes for cleanup when the lifetime plugin is present.
    
    Config Key: "os"
    
    Features:
        - Execute any system command via os.system()
        - Register processes for automatic cleanup on shutdown
        - Integrates with lifetime plugin for process management
    
    Example Configuration:
        ```toml
        [os]
        cmd = "start C:/Tools/monitor.exe"
        kill = "monitor.exe"
        
        [lifetime]
        lifetime = 3600
        ```
    
    Notes:
        - Commands are executed synchronously
        - If 'kill' is specified and lifetime plugin is loaded, the process
          will be added to the lifetime plugin's kill list
        - Supports both simple process names and commands with arguments
    """
    
    __cmdname__ = "os"

    def __init__(self, cmd: str = None, kill: str = None, **kwargs):
        super().__init__()
        self.cmd = cmd
        self.kill = kill

    @hook("action")
    def execute_command(self, runner):
        """
        Execute the configured system command.
        
        If a kill target is specified and the lifetime plugin is loaded,
        registers the process for automatic termination on shutdown.
        """
        if self.cmd:
            os.system(self.cmd)
            
            # Try to register with lifetime plugin if it exists
            if self.kill:
                lifetime_plugin = self._find_lifetime_plugin(runner)
                if lifetime_plugin:
                    if " " in self.kill:
                        lifetime_plugin.killList.append(("cmd", self.kill.split(" ")[0]))
                    else:
                        lifetime_plugin.killList.append(("process", self.kill))

    def _find_lifetime_plugin(self, runner):
        """Find the lifetime plugin in the runner's plugins."""
        from mxx.runner.builtins.lifetime import Lifetime
        
        if hasattr(runner, 'plugins'):
            for plugin in runner.plugins.values():
                if isinstance(plugin, Lifetime):
                    return plugin
        return None
