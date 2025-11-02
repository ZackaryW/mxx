# Project Brief: MXX Runner System

## Overview
MXX is a plugin-based task runner system designed for orchestrating complex automation workflows with flexible lifecycle hooks and inter-plugin communication.

## Core Requirements

### Plugin System
- Hook-based architecture for lifecycle management
- Support for conditional execution (all_cond, any_cond)
- Action phases: pre_action, action, post_action
- Event-driven control flow (on_true, on_false, on_error)
- Inter-plugin communication via shared runner context

### Builtin Plugins
1. **Lifetime** - Time-based execution control with process cleanup
2. **OSExec** - System command execution with cleanup integration
3. **AppLauncher** - External executable management with Scoop support

### Architecture Goals
- Minimal abstraction - plugins are single classes accepting config directly
- Class-level plugin identification (__cmdname__)
- Metaclass-based callstack registration
- Dynamic plugin loading from user plugin directory (~/.mxx/plugins)

## Success Criteria
- Clean, maintainable plugin API
- Easy inter-plugin communication
- Extensible through custom user plugins
- No unnecessary model/dataclass layers
- Configuration passed directly to plugin constructors
