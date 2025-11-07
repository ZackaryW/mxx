# System Patterns: MXX Architecture

## Core Architecture

### Metaclass-Driven Plugin System
- `PluginCallstackMeta` metaclass intercepts plugin instantiation
- Checks for `__cmdname__` class attribute immediately after `super().__call__()`
- Creates `MxxCallstack` per plugin and stores in `_callstackMap`
- Scans instance methods for `_mxx_hook_types` attribute
- Populates callstack lists with decorated hook methods

**Critical Pattern**: `__cmdname__` MUST be a class attribute, not instance attribute, because metaclass needs it before `__init__` completes.

### Hook Decorator System
```python
@hook("hook_type")
def method_name(self, runner):
    # Hook receives runner instance for context access
```

Hook types (from `enums.py`):
- `any_cond` - At least one must return True
- `all_cond` - All must return True
- `action` - Main execution phase
- `pre_action` - Setup before action
- `post_action` - Cleanup after action
- `on_true` - Persistent wait until True
- `on_false` - Persistent check, stops if True
- `on_error` - Error handling

### Runner Execution Flow
1. `run(cfg)` - Export configs, instantiate plugins, call `run_events()`
2. `run_events(plugins)` - Merge all plugin callstacks
3. Execute lifecycle phases:
   - Loop: Wait for all `on_true` and no `on_false`
   - Check: `all_cond` AND `any_cond`
   - Execute: `pre_action` → `action` → `post_action`
   - Error: `on_error` if exception

### Plugin Instantiation Pattern
```python
# Runner creates plugins with config
plugin_cls = MAPPINGS[plugin_name]
plugin_instance = plugin_cls(**plugin_cfg)
```

Plugin `__init__` receives config directly:
```python
class MyPlugin(MxxPlugin):
    __cmdname__ = "myplugin"
    
    def __init__(self, param1: str = None, param2: int = 0, **kwargs):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
```

### Inter-Plugin Communication
Plugins access each other via `runner.plugins`:
```python
@hook("action")
def my_action(self, runner):
    # Find another plugin
    lifetime = runner.plugins.get("lifetime")
    if lifetime:
        lifetime.killList.append(("process", "myapp.exe"))
```

Alternative pattern using type checking:
```python
from mxx.runner.builtins.lifetime import Lifetime

for plugin in runner.plugins.values():
    if isinstance(plugin, Lifetime):
        return plugin
```

## Registry Pattern
- `BUILTIN_MAPPINGS` - Core plugins dict
- `MAPPINGS` - Starts as copy of builtins, extended with custom plugins
- `PLUGIN_PATH` - User plugin directory (~/.mxx/plugins)
- Future: Dynamic loading of custom plugins into MAPPINGS

## Key Design Decisions

### No Model Classes
OLD (rejected):
```python
@dataclass
class LifetimeModel:
    lifetime: int

class Lifetime:
    def __init__(self):
        self.model = LifetimeModel(**cfg)
```

NEW (current):
```python
class Lifetime:
    def __init__(self, lifetime: int = None, **kwargs):
        self.lifetime = lifetime
```

**Rationale**: New architecture eliminates unnecessary abstraction. Config flows directly to plugin attributes.

### Class-Level __cmdname__
Must be class attribute for metaclass `__call__` to access it before `__init__` runs.

### Hook Signature Inspection (PROBLEMATIC)
Runner checks if hook functions take arguments via `inspect.signature()`:
- If parameters exist, passes `self` (the runner)
- Otherwise calls with no arguments

**ISSUE IDENTIFIED**: This logic is flawed because:
```python
def _run_action(self, func):
    sig = inspect.signature(func)
    if len(sig.parameters) > 0:  # This doesn't distinguish bound methods!
        return func(self)  # Passes runner as first arg
    return func()
```

Bound methods already have `self` parameter, so `len(sig.parameters) > 0` is always true for instance methods, causing incorrect argument passing.

## Identified Anti-Patterns

### 1. Global Mutable State (Metaclass)
```python
class PluginCallstackMeta(type):
    _callstackMap : dict[str, MxxCallstack] = {}  # Global shared state
```

**Problems**:
- Prevents plugin re-instantiation
- Memory leaks in long-running apps
- Test pollution (manual cleanup required)
- Thread safety issues

### 2. Unsafe Command Execution
```python
os.system(f"taskkill /IM {procName} /F")  # Command injection risk
```

**Problems**:
- No input sanitization
- Shell injection vulnerabilities
- Silent failure handling

### 3. Tight Inter-Plugin Coupling
```python
from mxx.runner.builtins.lifetime import Lifetime  # Direct import

def _find_lifetime_plugin(self, runner):
    for plugin in runner.plugins.values():
        if isinstance(plugin, Lifetime):  # Type checking creates coupling
            return plugin
```

**Problems**:
- Circular import risks
- Hard to test in isolation
- Reduces plugin composability

### 4. Configuration Logic Flaws
```python
for k, v in cfg.items():
    if k in MAPPINGS:
        if isinstance(v, dict):  # Assumes plugin configs are dicts
            pcfg[k] = v
        else:
            gcfg[k] = v  # Plugin configs that aren't dicts become global
```

**Problems**:
- Plugin configs might not always be dicts
- Logic could misclassify configurations
- No validation of config structure
