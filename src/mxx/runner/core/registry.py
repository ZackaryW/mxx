
from pathlib import Path
from mxx.runner.builtins.lifetime import Lifetime
from mxx.runner.builtins.os_exec import OSExec
from mxx.runner.builtins.app_launcher import AppLauncher

#home/.mxx/plugins
PLUGIN_PATH = Path.home() / ".mxx" / "plugins"

BUILTIN_MAPPINGS = {
    "lifetime": Lifetime,
    "os": OSExec,
    "app": AppLauncher,
}

# Start with builtins, will be extended with custom plugins from PLUGIN_PATH
MAPPINGS = BUILTIN_MAPPINGS.copy()