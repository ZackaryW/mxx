"""
Built-in plugins for the Mxx runner system.

This module provides a collection of ready-to-use plugins for common tasks:
- lifetime: Time-based execution control and process cleanup
- os_exec: Execute arbitrary system commands
- app_launcher: Launch external applications with Scoop integration
"""

from .lifetime import Lifetime
from .os_exec import OSExec
from .app_launcher import AppLauncher

__all__ = [
    "Lifetime",
    "OSExec",
    "AppLauncher",
]
