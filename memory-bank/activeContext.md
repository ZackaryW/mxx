# Active Context: Current State & Focus

## Recent Work Completed
Successfully migrated builtins from two previous implementations (mxx2 and ldx-1) to the new MXX architecture.

### NEW: Configuration Tool Development
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

## Next Steps & Considerations

### Immediate
- Test the migrated builtins with actual runner execution
- Verify metaclass callstack registration works correctly
- Ensure inter-plugin communication (OSExec → Lifetime) functions

### Near Future
- Implement custom plugin loading from `PLUGIN_PATH`
- Consider TOML configuration file support
- Add example usage/documentation
- Error handling improvements

### Questions to Resolve
1. How should runner handle plugin initialization failures?
2. Should there be plugin priority/ordering for execution?
3. How will custom plugins be discovered and loaded from PLUGIN_PATH?
4. Should there be a plugin validation/testing framework?

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

## Watch Points
- Circular import issues when plugins reference each other
- Windows-specific code (taskkill, paths) limits portability
- psutil optional dependency handling in Lifetime plugin
- Hook signature inspection relies on parameter count (fragile?)
