# System Patterns: MXX Architecture

## Core Architecture

### Metaclass-Driven Plugin System
- `PluginCallstackMeta` metaclass intercepts plugin instantiation
- Checks for `__cmdname__` class attribute immediately after `super().__call__()`
- Creates `MxxCallstack` per plugin and stores in `_callstackMap`
- Scans instance methods for `_mxx_hook_types` attribute
- Populates callstack lists with decorated hook methods

**Critical Pattern**: `__cmdname__` MUST be a class attribute, not instance attribute, because metaclass needs it before `__init__` completes.

**Callstack Management**: The scheduler clears `_callstackMap` before each job execution to prevent collisions. This works because jobs run in isolated threads.

### Hook Decorator System with Priority
```python
@hook("hook_type", priority=100)
def method_name(self, runner):
    # Hook receives runner instance for context access
    # Higher priority number = executes first
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

Priority system:
- Default priority: 0
- Higher numbers execute first
- Hooks sorted after callstack merge: `callstack.sort_by_priority()`
- Example: Launch emulator (priority=100) before running app (priority=0)

### Runner Execution Flow
1. `run(cfg)` - Export configs, instantiate plugins, call `run_events()`
2. `run_events(plugins)` - Merge all plugin callstacks
3. **Sort by priority** - All hooks ordered by priority (high to low)
4. Execute lifecycle phases:
   - Check: `all_cond` AND `any_cond`
   - Execute: `pre_action` → `action` → `post_action`
   - Loop: Wait for all `on_true` and no `on_false` (0.5s sleep between checks)
   - Error: `on_error` if exception

### Scheduler Service Architecture
```
SchedulerService (scheduler.py)
├── BackgroundScheduler (APScheduler)
│   ├── ThreadPoolExecutor (max_workers=10)
│   └── Job registry and execution
├── JobExecutionContext - Tracks job state
│   ├── status: pending/running/completed/failed
│   ├── start_time, end_time
│   └── error message if failed
└── JobRegistry - Persistent job configs
    └── ~/.mxx/jobs/ (TOML files)

REST API (routes.py)
├── POST /api/scheduler/jobs - Register/schedule job
├── GET /api/scheduler/jobs - List all jobs
├── POST /api/scheduler/jobs/{id}/trigger - Trigger on-demand
├── GET /api/scheduler/plugins - List available plugins
└── Various other management endpoints
```

**Key Pattern**: Jobs execute `runner.run(config)` in background thread. Runner blocks for full lifetime, allowing proper cleanup via `post_action` hooks.

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
- Dynamic loading: Custom plugins loaded on registry initialization
- Plugin discovery: Scans .py files, finds MxxPlugin subclasses, registers by `__cmdname__`

### Custom Plugin Loading
```python
# registry.py initialization
def _load_custom_plugins():
    for plugin_file in PLUGIN_PATH.glob("*.py"):
        # Load module dynamically
        # Find MxxPlugin subclasses
        # Register by __cmdname__ attribute
        plugin_name = getattr(attr, '__cmdname__', ...)
        MAPPINGS[plugin_name] = plugin_class
```

## Subprocess Management Patterns

### Detached Process Spawning (Windows)
```python
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

subprocess.Popen(
    args,
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
    close_fds=True  # CRITICAL: prevents blocking on inherited file descriptors
)
```

**Critical**: `close_fds=True` is essential to prevent Python from waiting for child process handles.

### APScheduler Integration Patterns

#### One-Time Job Execution
```python
scheduler.add_job(
    func=callback,
    args=[job_id],
    trigger='date',  # Important: specifies one-time execution
    id=unique_id,
    misfire_grace_time=None
)
```

#### Handling JobLookupError Race Condition
APScheduler 3.x has a bug where it tries to remove completed one-time jobs twice. Solution:
```python
# Monkey-patch scheduler.remove_job
original_remove = scheduler.remove_job
def patched_remove(job_id, jobstore=None):
    try:
        return original_remove(job_id, jobstore)
    except JobLookupError:
        pass  # Suppress double-removal error
scheduler.remove_job = patched_remove
```

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
