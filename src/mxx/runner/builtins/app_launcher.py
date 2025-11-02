"""
Application launcher plugin for launching external executables.

This plugin manages external executable applications, supporting both
Scoop-managed installations and custom paths.
"""

import os
import subprocess
from mxx.runner.core.plugin import MxxPlugin, hook


class AppLauncher(MxxPlugin):
    """
    External executable launcher plugin.
    
    Launches and manages external executables with support for:
    - Scoop package manager integration (automatic path resolution)
    - Custom executable paths
    - Automatic termination on shutdown
    
    Config Key: "app"
    
    The plugin resolves the executable path based on configuration,
    verifies the file exists, launches it in detached mode, and
    terminates it on shutdown.
    
    Example Configurations:
        Scoop-managed:
        ```toml
        [app]
        scoop = true
        pkg = "my-app"
        targetExe = "app.exe"
        ```
        
        Custom path:
        ```toml
        [app]
        scoop = false
        path = "C:/MyApps/Tool"
        targetExe = "tool.exe"
        delay = 5
        ```
    """
    
    __cmdname__ = "app"

    def __init__(self, scoop: bool = True, pkg: str = None, path: str = None, 
                 targetExe: str = None, delay: int = 10, **kwargs):
        super().__init__()
        self.scoop = scoop
        self.pkg = pkg
        self.path = path
        self.targetExe = targetExe
        self.delay = delay
        self.executable_path = None
        
        # Validation
        if not self.targetExe:
            raise ValueError("targetExe must be specified for App configuration.")
        if self.scoop and not self.pkg:
            raise ValueError("pkg must be specified when scoop is True for App configuration.")
        if self.scoop and self.path:
            raise ValueError("path should not be specified when scoop is True for App configuration.")

    @hook("action")
    def launch_application(self, runner):
        """
        Resolve executable path and launch the application.
        
        For Scoop installations, resolves path using SCOOP environment variable
        or default location. For custom paths, uses the provided directory.
        Verifies the executable exists before launching.
        
        Raises:
            FileNotFoundError: If the executable file does not exist
        """
        if self.scoop:
            scoop_path = os.environ.get("SCOOP", os.path.expanduser("~\\scoop"))
            app_path = os.path.join(scoop_path, "apps", self.pkg, "current", self.targetExe)

            if not os.path.isfile(app_path):
                raise FileNotFoundError(f"App executable not found at {app_path}")
            
            self.executable_path = app_path
        else:
            app_path = os.path.join(self.path, self.targetExe)
            if not os.path.isfile(app_path):
                raise FileNotFoundError(f"App executable not found at {app_path}")
            
            self.executable_path = app_path

        # Launch in detached mode
        self._open_detached([self.executable_path])

    @hook("post_action")
    def shutdown_application(self, runner):
        """
        Forcefully terminate the launched executable.
        
        Uses Windows taskkill command to terminate the process by executable name.
        """
        os.system(f"taskkill /IM {self.targetExe} /F")

    @staticmethod
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
