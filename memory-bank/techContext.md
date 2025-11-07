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

### Windows-Specific (PROBLEMATIC)
- Process termination uses `taskkill /IM /F` - **SECURITY RISK**: Command injection possible
- Path handling uses Windows separators (`~\\scoop`) - **PORTABILITY**: No Linux/macOS support
- Detached process creation uses Windows `DETACHED_PROCESS` flag - **PORTABILITY**: Platform-specific
- **IMPACT**: Library cannot run on non-Windows platforms

### Metaclass Timing (PROBLEMATIC) 
- `PluginCallstackMeta.__call__` executes AFTER `super().__call__()` but has access to class attributes
- Instance attributes set in `__init__` are available during hook scanning  
- Class attribute `__cmdname__` must exist before instance creation completes
- **ISSUE**: Global `_callstackMap` prevents re-instantiation and causes memory leaks

## Security Vulnerabilities Discovered

### 1. Command Injection
**Locations**: 
- `lifetime.py:95` - `os.system(f"taskkill /IM {procName} /F")`
- `lifetime.py:102` - `os.system(f"taskkill /IM {cmdName} /F")`
- `app_launcher.py:91` - `os.system(f"taskkill /IM {self.targetExe} /F")`

**Risk**: If user controls `procName`, `cmdName`, or `targetExe`, arbitrary commands can be executed.

### 2. Path Traversal  
**Locations**: Throughout codebase
- No validation of file paths
- User-provided paths used directly in file operations
**Risk**: Arbitrary file system access

### 3. Unsafe Imports
**Pattern**: Dynamic plugin loading planned but no security model
**Risk**: Code injection if malicious plugins loaded from `PLUGIN_PATH`

## Technical Debt

### 1. Error Handling
- Silent failures with `except Exception` and fallbacks
- No error propagation strategy
- Missing logging in critical paths

### 2. Testing Infrastructure
- Manual cleanup required for metaclass state
- Test pollution between test runs
- Limited error condition coverage

### 3. Dependencies
- Optional `psutil` dependency not handled consistently
- Missing dependency declarations for optional features
- No version constraints on critical dependencies

## Configuration Format (NEEDS VALIDATION)
Currently accepts dict/kwargs format. Future likely TOML-based:
```python
cfg = {
    "lifetime": {"lifetime": 3600},
    "os": {"cmd": "start app.exe", "kill": "app.exe"},  # SECURITY RISK: No validation
    "app": {"scoop": True, "pkg": "myapp", "targetExe": "app.exe"}  # SECURITY RISK: No path validation
}
runner.run(cfg)
```

**CRITICAL ISSUE**: No validation of configuration values, allowing potential security exploits.

## Import Patterns (PROBLEMATIC)
- Relative imports within package: `from mxx.runner.core.plugin import MxxPlugin`
- **ISSUE**: Circular import avoidance done by importing inside methods - fragile pattern
- Builtin plugins exported via `__all__` in `builtins/__init__.py`
- **ISSUE**: Direct plugin type imports create tight coupling

## Testing (PROBLEMATIC)
- Tests exist but require manual metaclass cleanup
- Limited coverage of error conditions
- No security-focused tests
- Test pollution issues due to global metaclass state

## Recommended Technical Changes

### Immediate (Security)
1. Replace `os.system()` with `subprocess.run()` and proper argument escaping
2. Add input validation for all user-provided strings
3. Implement configuration schema validation

### Short Term (Architecture)  
1. Fix metaclass callstack management (per-runner instances)
2. Improve parameter inspection logic for hooks
3. Add proper error handling and propagation

### Long Term (Platform Support)
1. Abstract platform-specific operations
2. Add Linux/macOS support
3. Implement cross-platform process management
