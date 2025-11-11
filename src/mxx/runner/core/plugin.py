
from mxx.runner.core.callstack import PluginCallstackMeta
from mxx.runner.core.enums import hook_types

class MxxPlugin(metaclass=PluginCallstackMeta):
    __cmdname__ : str = None
    __priority__ : int = 0  # Default priority, higher number = runs first

def hook(hook_type : str, priority: int = 0):
    """
    Decorator to mark a method as a hook.
    
    Args:
        hook_type: Type of hook (action, pre_action, post_action, etc.)
        priority: Execution priority (default 0). Higher values execute first.
    """
    def decorator(func):
        if hook_type not in hook_types:
            raise Exception(f"Invalid hook type: {hook_type}")

        if hasattr(func, "_mxx_hook_types"):
            raise Exception("Function is already registered as a hook")

        # Mark the function with hook type and priority
        # Note: At class definition time, this is an unbound function
        # The metaclass will bind it to the instance and register it
        func._mxx_hook_types = hook_type
        func._mxx_hook_priority = priority
        return func
        
    return decorator

