# Product Context: MXX Runner

## Purpose
MXX consolidates and improves upon two previous runner implementations (mxx2/scriptor and ldx-1) into a unified, cleaner architecture. It provides a framework for automating workflows that need:
- Timed execution windows
- Process lifecycle management
- Application launching and cleanup
- System command execution
- Coordinated multi-plugin workflows

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
