# Active Context: Current State & Focus

## Current Work: Scheduler Server & Plugin System Enhancements (November 2025)

### Recent Accomplishments

#### 1. **Scheduler Server Implementation**
Implemented a complete Flask-based scheduler service for managing plugin execution jobs:
- APScheduler integration with background execution
- Job registry system for persistent job configurations
- On-demand and scheduled job execution support
- RESTful API for job management
- Client CLI tool (`mxx-cli`) for remote control

#### 2. **Plugin Priority System**
Added execution priority control to plugin hooks:
- `@hook("action", priority=100)` - High priority executes first
- Default priority is 0, higher numbers run first
- Automatic sorting of all hooks by priority after callstack merge
- Enables proper ordering (e.g., launch emulator before running app)

#### 3. **APScheduler JobLookupError Fix**
Resolved race condition with one-time job removal:
- Monkey-patched `scheduler.remove_job()` to suppress `JobLookupError`
- Added proper `trigger='date'` for triggered jobs
- Prevents noisy exceptions from APScheduler's internal double-removal bug

#### 4. **Plugin Registry CLI Command**
Added `mxx-cli plugins` command to inspect loaded plugins:
- Lists all builtin and custom plugins
- Shows class names, modules, and documentation
- Filter options: `--builtin` or `--custom`
- Helps debug plugin loading issues

#### 5. **LDPlayer Custom Plugin**
Created production custom plugin for LDPlayer emulator:
- Located at `~/.mxx/plugins/ld.py`
- Launches/quits LDPlayer instances via `ldpx` CLI
- Uses detached process spawning (non-blocking)
- Proper Windows process flags: `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`
- Added `close_fds=True` to prevent file descriptor inheritance blocking

### Current Architecture State

#### Scheduler Service Components
```
mxx-server (Flask app)
├── scheduler.py - SchedulerService with APScheduler
├── routes.py - REST API endpoints
├── registry.py - JobRegistry for persistent jobs
├── schedule.py - ScheduleConfig dataclass
└── flask_runner.py - Job execution wrapper
```

#### Plugin System Enhancements
- Hook priority system fully operational
- Custom plugin loading from `~/.mxx/plugins/`
- Plugin registry inspection via API and CLI
- Proper subprocess detachment for non-blocking execution

### Active Design Philosophy
**Job orchestration with proper lifecycle management** - The scheduler runs jobs in thread pool, each job gets full runner lifecycle including lifetime management, ensuring proper cleanup of launched processes.

## Critical Fixes Applied

### 1. Plugin Registry Loading
**Issue**: Custom plugins weren't registering properly
**Fix**: Changed `getattr(attr, 'name', ...)` to `getattr(attr, '__cmdname__', ...)` in registry loader

### 2. Subprocess Blocking
**Issue**: `subprocess.Popen` was blocking even with `DETACHED_PROCESS`
**Fix**: Added `close_fds=True` and additional process creation flags

### 3. Incorrect CLI Command Structure
**Issue**: Plugin used `ldpx console exec launch` but correct syntax is `ldpx console launch`
**Fix**: Removed non-existent `exec` subcommand

### 4. APScheduler Race Condition
**Issue**: JobLookupError when APScheduler tries to remove completed one-time jobs
**Fix**: Monkey-patch + proper trigger configuration + exception suppression

## Immediate Next Steps

### Testing & Validation
1. Verify scheduler executes jobs with proper plugin ordering
2. Test lifetime-controlled job cleanup
3. Validate multi-job concurrent execution
4. Confirm LDPlayer launch/quit cycle works end-to-end

### Potential Enhancements
- Job execution history/logging
- Job status persistence across server restarts
- Webhook notifications on job completion
- Web UI for scheduler management

## Known Issues Being Monitored

### Metaclass Callstack Clearing
Currently using `PluginCallstackMeta._callstackMap.clear()` before each job execution. This works for scheduler but may cause issues if:
- Multiple runners execute simultaneously in same process
- Plugins are instantiated outside of job context

**Mitigation**: Scheduler uses thread pool, each job runs in own thread with cleared callstack at start.

### Debug Logging Added
Temporary debug logging added to track:
- Job config being executed
- Plugin instantiation with parameters
- Hook counts in merged callstack

Should be removed or made conditional once system is stable.
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
