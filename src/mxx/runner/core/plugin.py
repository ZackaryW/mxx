
from mxx.runner.core.callstack import PluginCallstackMeta
from mxx.runner.core.enums import hook_types

class MxxPlugin(metaclass=PluginCallstackMeta):
    __cmdname__ : str = None

def hook(hook_type : str):
    def decorator(func):
        if hook_type not in hook_types:
            raise Exception(f"Invalid hook type: {hook_type}")

        if hasattr(func, "_mxx_hook_types"):
            raise Exception("Function is already registered as a hook")

        # Mark the function with hook type
        # Note: At class definition time, this is an unbound function
        # The metaclass will bind it to the instance and register it
        func._mxx_hook_types = hook_type
        return func
        
    return decorator

