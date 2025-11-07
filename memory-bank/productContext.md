# Product Context: MXX Runner

## Purpose
MXX consolidates and improves upon two previous runner implementations (mxx2/scriptor and ldx-1) into a unified, cleaner architecture. It provides a framework for automating workflows that need:
- Timed execution windows
- Process lifecycle management
- Application launching and cleanup
- System command execution
- Coordinated multi-plugin workflows

**CURRENT STATUS**: Core functionality implemented but **CRITICAL ISSUES PREVENT PRODUCTION USE**. Security vulnerabilities and architectural flaws must be addressed.

## Problems It Solves

### Fragmented Implementations
Previous versions (mxx2 and ldx-1) had duplicate functionality with slightly different patterns. MXX unifies these into one improved design.

### Complex Lifecycle Management
Users need to orchestrate multiple processes/applications that:
- Start together
- Run for specific durations
- Clean up automatically on shutdown
- Coordinate with each other

### Configuration Complexity
Old designs used separate Model dataclasses, adding unnecessary abstraction. MXX simplifies by accepting config directly in plugin constructors.

## Problems It Currently Has (November 2025)

### Security Vulnerabilities
- **Command injection risks**: User input flows to `os.system()` calls without validation
- **Path traversal risks**: No validation of file paths provided by users
- **No input sanitization**: Configuration values used directly in system operations

### Architecture Limitations  
- **Single-use restriction**: Metaclass design prevents plugin re-instantiation
- **Memory leaks**: Global state accumulates without cleanup
- **Platform lock-in**: Windows-only implementation with hardcoded platform calls
- **Tight coupling**: Plugins directly import and depend on each other

## How It Works

### User Perspective
1. Define configuration (likely TOML/dict format)
2. Specify which plugins to use and their settings
3. Run the MxxRunner with the config
4. System handles all lifecycle events automatically

### Plugin Developer Perspective
1. Inherit from MxxPlugin
2. Set class-level __cmdname__
3. Accept config in __init__
4. Use @hook decorators to define lifecycle methods
5. Access other plugins via runner.plugins for coordination

## Key Design Philosophy
- **Simplicity over abstraction** - No unnecessary layers
- **Direct configuration** - Config flows straight to plugin __init__
- **Class-based identity** - __cmdname__ is class attribute for metaclass
- **Composable behavior** - Plugins communicate and coordinate freely

## Critical Success Blockers (Must Fix)

### For Production Use
1. **Security** - Cannot deploy with command injection vulnerabilities
2. **Reliability** - Cannot have single-use limitation due to metaclass issues
3. **Maintainability** - Cannot have silent failures masking critical errors

### For Development Use  
1. **Testability** - Tests require manual cleanup due to global state pollution
2. **Debugging** - Silent error handling makes troubleshooting difficult
3. **Extensibility** - Tight coupling makes adding new plugins problematic

## Success Metrics (Post-Fix)
- [ ] Zero security vulnerabilities in security audit
- [ ] Successful multi-instance runner creation and cleanup
- [ ] Cross-platform compatibility (Windows + Linux minimum)
- [ ] Test suite runs cleanly without manual intervention
- [ ] Plugin development possible without coupling to builtins
- [ ] Configuration validation prevents runtime errors

## User Impact Assessment
**Current State**: Library is a development prototype only. Security issues and architectural limitations make it unsuitable for production use or distribution.

**Post-Fix State**: Could become a robust automation framework suitable for:
- CI/CD pipeline orchestration
- Development environment automation
- System administration workflows
- Process lifecycle management
