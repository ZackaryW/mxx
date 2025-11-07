# Active Context: Current State & Focus

## Current Work: Comprehensive Issue Analysis (November 2025)
Completed deep analysis of MXX library identifying critical issues across architecture, security, and maintainability. Focus has shifted from feature development to addressing foundational problems discovered in the codebase.

### Critical Issues Discovered

#### 1. **Metaclass Callstack Map Collision**
- `PluginCallstackMeta._callstackMap` prevents plugin re-instantiation
- Causes memory leaks and breaks multiple runner instances
- Test fixtures require manual cleanup due to this issue
- **Status**: Critical - blocks production use

#### 2. **Security Vulnerabilities** 
- Command injection risks in `os.system()` calls with user strings
- Found in `lifetime.py`, `app_launcher.py` process termination
- No input validation on executable paths or command parameters
- **Status**: Critical - potential security exploit

#### 3. **Parameter Inspection Flaws**
- `_run_action()` incorrectly determines function parameters
- Doesn't distinguish between `self` and `runner` parameters properly
- Could cause hook methods to receive wrong arguments
- **Status**: High - causes runtime errors

### Architecture Analysis Results
Identified significant design issues:
- Tight coupling between plugins (direct imports)
- Platform-specific hardcoding (Windows-only)
- Configuration logic flaws in plugin vs global separation
- Missing plugin dependency management
- Silent error handling masking failures

### Recent Work Completed
Successfully migrated builtins from two previous implementations (mxx2 and ldx-1) to the new MXX architecture.

### Configuration Tool Development
Implemented a comprehensive configuration management tool (`mxx cfg_tool`) with:

1. **App Registry System** (`app.py`):
   - Register applications with path and configuration route (`cfgroute`)
   - Support for configuration overrides (`cfgow`) and exclusions (`cfge`)
   - Multiple aliases per application
   - UID-based indexing with two JSON files:
     - `~/.mxx/apps/apps.json` - UID to config mapping
     - `~/.mxx/apps/aliases.json` - Alias to UID mapping

2. **Config Export/Import** (`cfg.py`):
   - Export: Clean config by removing excluded and override keys
   - Import: Smart merge preserving local exclusions and applying overrides
   - Nested key support using `/` separator (e.g., `file/section/key`)
   - Default export location: `~/.mxx/exports/{uid}/`

3. **Independent Components** (`registry.py`):
   - JSON config loading/saving utilities
   - App registry management functions
   - Get app by name/alias functionality

4. **CLI Structure**:
   - Entry point: `mxx` (configured in pyproject.toml)
   - Command groups: `mxx app` and `mxx cfg`
   - Cross-platform folder opening support

### Migration Improvements Made
1. **Eliminated Model dataclasses** - Config now flows directly to plugin `__init__` parameters
2. **Moved __cmdname__ to class level** - Required for metaclass to access during instantiation
3. **Removed pre_action config loading** - Config loads in `__init__` where runner passes it
4. **Updated registry with actual types** - Changed from string paths to imported class references
5. **Made MAPPINGS extensible** - Starts as copy of BUILTIN_MAPPINGS for future custom plugin loading

### Current Plugin Status
All three builtin plugins migrated and functional:
- `Lifetime` - Time control and kill list management
- `OSExec` - Command execution with lifetime integration
- `AppLauncher` - Scoop/custom path executable launching

## Current Architecture State

### Working Patterns
- Plugin instantiation via `plugin_cls(**plugin_cfg)`
- Hook methods receive `runner` parameter for context access
- Inter-plugin communication via `runner.plugins`
- Class-level `__cmdname__` for metaclass registration

### Active Design Philosophy
**Simplicity and directness** - Avoid abstraction layers that don't add value. The new architecture enables plugins to be single, cohesive classes that directly accept and use their configuration.

## Immediate Priorities (Critical Path)

### HIGH PRIORITY - Security & Stability
1. **Fix command injection vulnerabilities** - Replace `os.system()` with `subprocess` calls
2. **Resolve metaclass callstack collision** - Implement per-runner or resettable callstack management
3. **Fix parameter inspection logic** - Properly handle bound method vs runner parameter distinction

### MEDIUM PRIORITY - Architecture
4. **Decouple plugins** - Remove direct plugin type imports, use registry/interface pattern
5. **Add configuration validation** - Schema validation for plugin configs before instantiation
6. **Cross-platform compatibility** - Abstract Windows-specific operations

### LOW PRIORITY - Quality
7. **Comprehensive error handling** - Replace silent fallbacks with proper error propagation
8. **Enhanced documentation** - Code-level comments and examples
9. **Extended test coverage** - Security, error conditions, integration scenarios

### Questions Still to Resolve
1. How should runner handle plugin initialization failures?
2. Should there be plugin priority/ordering for execution?
3. How will custom plugins be discovered and loaded from PLUGIN_PATH?
4. Should there be a plugin validation/testing framework?
5. **NEW**: How to maintain backward compatibility while fixing architectural issues?
6. **NEW**: Should we implement plugin versioning/compatibility checks?

## Important Learnings

### Design Evolution
The old architecture used:
- Separate Model dataclasses for validation
- `onEnvLoad()`, `onStartup()`, `onShutdown()` methods
- Instance-level `__cmdname__` assignment

The new architecture enables:
- Direct config parameters in `__init__`
- Hook decorators for lifecycle events  
- Class-level `__cmdname__` attribute
- More Pythonic and flexible patterns

### Critical Insight
The metaclass pattern requires `__cmdname__` to be a class attribute because `PluginCallstackMeta.__call__()` accesses it immediately after `super().__call__()` returns - before the instance's `__init__` has a chance to set instance attributes.

## Critical Watch Points
- **SECURITY**: Command injection vulnerabilities in process termination
- **STABILITY**: Metaclass callstack map prevents multiple runner instances
- **RELIABILITY**: Silent error handling masks critical failures
- **COUPLING**: Direct plugin imports create circular dependency risks
- **PLATFORM**: Windows-specific hardcoding limits portability
- **VALIDATION**: No configuration or input validation anywhere
- **TESTING**: Test pollution from metaclass state requires manual cleanup

## Project Status
**CURRENT STATE**: Library has good architectural foundation but critical implementation flaws prevent production use. Immediate focus must be on security and stability fixes before adding new features.
