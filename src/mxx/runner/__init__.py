"""
MXX Runner - Plugin-based task runner system.

This package provides the core runner functionality for executing
plugin-based workflows with lifecycle management.
"""

from mxx.runner.core.runner import MxxRunner
from mxx.runner.core.plugin import MxxPlugin, hook

__all__ = ["MxxRunner", "MxxPlugin", "hook"]