

from dataclasses import dataclass, field


@dataclass
class MxxCallstack:
    any_cond : list[callable] = field(default_factory=list)
    all_cond : list[callable] = field(default_factory=list)
    action : list[callable] = field(default_factory=list)
    pre_action : list[callable] = field(default_factory=list)
    post_action : list[callable] = field(default_factory=list)
    on_true : list[callable] = field(default_factory=list)
    on_false : list[callable] = field(default_factory=list)
    on_error : list[callable] = field(default_factory=list)

    def merge(self, other : "MxxCallstack"):
        for hook_type in self.__dataclass_fields__.keys():
            getattr(self, hook_type).extend(getattr(other, hook_type))

class PluginCallstackMeta(type):
    _callstackMap : dict[str, MxxCallstack] = {}

    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)

        if instance.__cmdname__ in cls._callstackMap:
            raise Exception(f"Callstack for plugin '{instance.__cmdname__}' is already created")
        
        callstack = MxxCallstack()
        cls._callstackMap[instance.__cmdname__] = callstack

        # map all hook functions to the callstack
        for attr_name in dir(instance):
            attr = getattr(instance, attr_name)
            if callable(attr) and hasattr(attr, "_mxx_hook_types"):
                hook_type = attr._mxx_hook_types
                if hasattr(callstack, hook_type):
                    getattr(callstack, hook_type).append(attr)
                else:
                    raise Exception(f"Invalid hook type '{hook_type}' for function '{attr_name}'")

        return instance
    
    