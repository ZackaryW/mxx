# Technical Context: MXX

## Language & Runtime
- **Python 3.10+** (uses structural pattern matching in match/case statements)
- Type hints throughout for clarity

## Project Structure
```
mxx/
├── src/mxx/
│   ├── __init__.py
│   ├── runner/
│   │   ├── builtins/
│   │   │   ├── __init__.py
│   │   │   ├── lifetime.py
│   │   │   ├── os_exec.py
│   │   │   └── app_launcher.py
│   │   └── core/
│   │       ├── callstack.py       # Metaclass & callstack dataclass
│   │       ├── enums.py           # Hook type definitions
│   │       ├── plugin.py          # MxxPlugin base & @hook decorator
│   │       ├── registry.py        # Plugin mappings
│   │       └── runner.py          # MxxRunner execution engine
│   └── server/                    # (Not yet explored)
├── memory-bank/                   # Project documentation
├── pyproject.toml
├── README.md
└── LICENSE
```

## Dependencies

### Core
- Python standard library (dataclasses, datetime, os, subprocess, inspect)

### Optional (Plugin-specific)
- `psutil` - Process management in Lifetime plugin (with fallback to taskkill)

## Development Environment
- **OS**: Windows (uses taskkill commands, path separators)
- **Shell**: PowerShell
- **IDE**: VS Code

## Key Technical Constraints

### Windows-Specific
- Process termination uses `taskkill /IM /F`
- Path handling uses Windows separators (`~\\scoop`)
- Detached process creation uses Windows `DETACHED_PROCESS` flag

### Metaclass Timing
- `PluginCallstackMeta.__call__` executes AFTER `super().__call__()` but has access to class attributes
- Instance attributes set in `__init__` are available during hook scanning
- Class attribute `__cmdname__` must exist before instance creation completes

## Configuration Format
Currently accepts dict/kwargs format. Future likely TOML-based:
```python
cfg = {
    "lifetime": {"lifetime": 3600},
    "os": {"cmd": "start app.exe", "kill": "app.exe"},
    "app": {"scoop": True, "pkg": "myapp", "targetExe": "app.exe"}
}
runner.run(cfg)
```

## Import Patterns
- Relative imports within package: `from mxx.runner.core.plugin import MxxPlugin`
- Circular import avoidance: Import inside methods when needed
- Builtin plugins exported via `__all__` in `builtins/__init__.py`

## Testing
Not yet implemented. Future consideration.
