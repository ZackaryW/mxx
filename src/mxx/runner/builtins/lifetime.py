"""
Lifetime control plugin for time-based execution limits.

This plugin manages the duration of runner execution and provides cleanup
capabilities for processes, commands, and tasks at shutdown.
"""

import datetime
import logging
import os
from mxx.runner.core.plugin import MxxPlugin, hook


class Lifetime(MxxPlugin):
    """
    Time-based execution control plugin.
    
    Controls how long the runner executes and provides process cleanup at shutdown.
    Other plugins can register items to kill on shutdown by adding to the killList.
    
    Config Key: "lifetime"
    
    Features:
        - Sets execution duration in seconds
        - Stops runner when time expires
        - Kills registered processes/commands on shutdown
        - Integrates with other plugins for cleanup coordination
    
    Example Configuration:
        ```toml
        [lifetime]
        lifetime = 3600  # Run for 1 hour
        ```
    
    Kill List Format:
        Plugins can add items to self.killList as tuples:
        - ("process", "process_name.exe") - Terminate by process name using psutil
        - ("cmd", "command") - Terminate using taskkill /IM
        - ("taskkill", "task_name") - Terminate using taskkill /IM
    """
    
    __cmdname__ = "lifetime"

    def __init__(self, lifetime: int = None, **kwargs):
        super().__init__()
        self.lifetime = lifetime
        self.killList = []
        self.targetStopTime = None

    @hook("all_cond")
    def can_run(self, runner):
        """Check if lifetime is valid (greater than 0)."""
        if self.lifetime is None:
            return True
        return self.lifetime > 0

    @hook("action")
    def calculate_stop_time(self, runner):
        """Calculate and store the target stop time."""
        if self.lifetime:
            self.targetStopTime = datetime.datetime.now() + datetime.timedelta(seconds=self.lifetime)

    @hook("on_true")
    def should_continue(self, runner):
        """Return True to continue, False to stop."""
        if self.targetStopTime:
            # Continue while time hasn't expired
            return datetime.datetime.now() < self.targetStopTime
        # No lifetime set, continue indefinitely
        return True

    @hook("post_action")
    def cleanup(self, runner):
        """
        Terminate all registered processes, commands, and tasks.
        
        Iterates through killList and terminates items based on their type:
        - process: Uses psutil to find and terminate by name
        - cmd/taskkill: Uses Windows taskkill command
        """
        for killItem in self.killList:
            match killItem:
                case ("process", procName):
                    logging.info(f"Terminating process: {procName}")
                    try:
                        import psutil
                        killed = False
                        for proc in psutil.process_iter(['name']):
                            try:
                                if proc.info['name'] == procName:
                                    proc.kill()
                                    proc.wait(timeout=5)
                                    killed = True
                                    logging.info(f"Successfully killed {procName}")
                            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                                logging.warning(f"Could not kill process {procName}: {e}")
                        
                        if not killed:
                            logging.warning(f"Process {procName} not found, trying taskkill")
                            os.system(f"taskkill /IM {procName} /F")
                    except Exception as e:
                        logging.error(f"Failed to terminate process {procName}: {e}")
                        # Fallback to taskkill
                        os.system(f"taskkill /IM {procName} /F")
                case ("cmd", cmdName):
                    logging.info(f"Terminating command: {cmdName}")
                    os.system(f"taskkill /IM {cmdName} /F")
                case ("taskkill", taskName):
                    logging.info(f"Terminating task: {taskName}")
                    os.system(f"taskkill /IM {taskName} /F")
                case _:
                    pass

        self.killList.clear()
