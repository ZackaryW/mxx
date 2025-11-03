# MXX Scheduler Server

The MXX Scheduler Server provides job scheduling and management capabilities for the MXX framework.

## Installation

Install with server dependencies:

```bash
# Install with server support
pip install -e ".[server]"

# Install with client support
pip install -e ".[client]"

# Install both
pip install -e ".[all]"
```

## Quick Start

### 1. Start the Server

```bash
# Start server (default: http://127.0.0.1:5000)
mxx-server

# Start on custom port
mxx-server --port 8080

# Use custom jobs directory
mxx-server --jobs-dir /path/to/jobs

# Listen on all interfaces
mxx-server --host 0.0.0.0
```

The server will automatically load job configurations from `~/.mxx/jobs/` on startup.

### 2. Create Job Configurations

Create job configuration files in `~/.mxx/jobs/`:

**Scheduled Job** (`~/.mxx/jobs/daily_backup.toml`):
```toml
[lifetime]
lifetime = 60  # Run for 60 seconds

[os]
cmd = "echo Daily backup started"

[schedule]
trigger = "cron"
hour = 10
minute = 30
```

**On-Demand Job** (`~/.mxx/jobs/manual_task.toml`):
```toml
[lifetime]
lifetime = 30

[os]
cmd = "echo Manual task executed"

# No [schedule] section = on-demand only
```

### 3. Use the Client

```bash
# Check server health
mxx-client health

# List all jobs
mxx-client list

# List active jobs only
mxx-client list --type active

# Get job status
mxx-client status my_job_1

# Trigger on-demand job
mxx-client trigger manual_task

# Register a new job
mxx-client register --job-id my_job example_config.toml

# Cancel a scheduled job
mxx-client cancel my_job_1

# Remove completed job
mxx-client remove my_job_1

# View registry
mxx-client registry

# View registry (on-demand only)
mxx-client registry --type on_demand

# Get job info from registry
mxx-client info my_job_1

# Unregister a job
mxx-client unregister my_job_1
```

## Architecture

### Components

1. **JobRegistry** (`registry.py`)
   - Persistent storage of job configurations
   - Stored in `~/.mxx/server/registry.json`
   - Tracks scheduled and on-demand jobs
   - Records execution history

2. **SchedulerService** (`scheduler.py`)
   - APScheduler integration
   - Job execution management
   - Status tracking
   - Overlap detection

3. **FlaskMxxRunner** (`flask_runner.py`)
   - Auto-loads configs from `~/.mxx/jobs/`
   - Integrates with Flask application
   - Manages scheduler lifecycle

4. **Routes** (`routes.py`)
   - REST API endpoints
   - Job management operations
   - Status queries

5. **Server** (`server.py`)
   - Flask application
   - Command-line interface
   - Configuration management

6. **Client** (`client.py`)
   - CLI for server interaction
   - User-friendly commands
   - Colored output

### Directory Structure

```
~/.mxx/
├── jobs/                    # Job configuration files
│   ├── daily_backup.toml
│   ├── manual_task.toml
│   └── ...
└── server/
    └── registry.json        # Persistent job registry
```

## API Reference

### Base URL
`http://127.0.0.1:5000/api/scheduler`

### Endpoints

#### Schedule a Job
```http
POST /jobs
Content-Type: application/json

{
  "job_id": "my_job_1",
  "config": {
    "lifetime": {"lifetime": 3600},
    "os": {"cmd": "echo test"}
  },
  "schedule": {
    "trigger": "cron",
    "hour": 10,
    "minute": 30
  },
  "replace_existing": false
}
```

#### List Jobs
```http
GET /jobs
```

#### List Active Jobs
```http
GET /jobs/active
```

#### Get Job Status
```http
GET /jobs/{job_id}
```

#### Cancel Job
```http
DELETE /jobs/{job_id}
```

#### Remove Job
```http
POST /jobs/{job_id}/remove
```

#### Trigger On-Demand Job
```http
POST /jobs/{job_id}/trigger
```

#### List Registry
```http
GET /registry?type=all|scheduled|on_demand
```

#### Get Registry Entry
```http
GET /registry/{job_id}
```

#### Unregister Job
```http
DELETE /registry/{job_id}
```

#### Health Check
```http
GET /health
```

## Schedule Configuration

### Cron Trigger
```toml
[schedule]
trigger = "cron"
hour = 10        # Hour (0-23)
minute = 30      # Minute (0-59)
second = 0       # Second (0-59, optional)
day_of_week = 1  # Day of week (0-6, optional)
```

### Interval Trigger
```toml
[schedule]
trigger = "interval"
seconds = 60     # Run every 60 seconds
```

```toml
[schedule]
trigger = "interval"
minutes = 30     # Run every 30 minutes
```

```toml
[schedule]
trigger = "interval"
hours = 2        # Run every 2 hours
```

## Configuration

### Environment Variables

- `MXX_JOBS_DIR`: Jobs directory (default: `~/.mxx/jobs`)
- `MXX_SERVER_HOST`: Server host (default: `127.0.0.1`)
- `MXX_SERVER_PORT`: Server port (default: `5000`)

### Server Options

```bash
mxx-server --help

Options:
  --host TEXT      Host to bind to (default: 127.0.0.1)
  --port INTEGER   Port to bind to (default: 5000)
  --jobs-dir PATH  Directory containing job configurations
  --debug          Run in debug mode
  --help           Show this message and exit
```

### Client Options

```bash
mxx-client --help

Options:
  --server TEXT  Server URL (default: http://127.0.0.1:5000)
  --help         Show this message and exit
```

## Examples

### Example 1: Scheduled Daily Backup

Create `~/.mxx/jobs/daily_backup.toml`:
```toml
[lifetime]
lifetime = 300  # 5 minutes

[os]
cmd = "python backup_script.py"

[schedule]
trigger = "cron"
hour = 2
minute = 0  # Run at 2:00 AM daily
```

Start server: `mxx-server`

The job will automatically execute at 2:00 AM every day.

### Example 2: Periodic Health Check

Create `~/.mxx/jobs/health_check.toml`:
```toml
[lifetime]
lifetime = 10

[os]
cmd = "curl https://example.com/health"

[schedule]
trigger = "interval"
minutes = 5  # Run every 5 minutes
```

### Example 3: On-Demand Report Generation

Create `~/.mxx/jobs/generate_report.toml`:
```toml
[lifetime]
lifetime = 120

[os]
cmd = "python generate_report.py"

# No schedule - trigger manually
```

Trigger via client:
```bash
mxx-client trigger generate_report
```

### Example 4: Programmatic Job Registration

```python
import requests

# Register job via API
response = requests.post(
    "http://127.0.0.1:5000/api/scheduler/jobs",
    json={
        "job_id": "custom_job",
        "config": {
            "lifetime": {"lifetime": 60},
            "os": {"cmd": "echo Custom job"}
        },
        "schedule": {
            "trigger": "interval",
            "minutes": 10
        }
    }
)

print(response.json())
```

## Troubleshooting

### Server won't start
- Check if port 5000 is already in use: `netstat -ano | findstr :5000`
- Try a different port: `mxx-server --port 8080`
- Check logs for error messages

### Jobs not loading
- Verify jobs directory exists: `~/.mxx/jobs/`
- Check file format (JSON/TOML/YAML)
- Review server logs for parsing errors

### Job not executing
- Check job status: `mxx-client status job_id`
- Verify schedule configuration
- Check if job is registered: `mxx-client registry`
- View active jobs: `mxx-client list --type active`

### Cannot connect with client
- Ensure server is running
- Verify server URL: `mxx-client --server http://127.0.0.1:5000 health`
- Check firewall settings

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[all,dev]"

# Run all tests
pytest

# Run server tests only
pytest tests/test_server*.py -v
```

### API Testing with curl

```bash
# Health check
curl http://127.0.0.1:5000/api/scheduler/health

# List jobs
curl http://127.0.0.1:5000/api/scheduler/jobs

# Register job
curl -X POST http://127.0.0.1:5000/api/scheduler/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test_job",
    "config": {"lifetime": {"lifetime": 60}, "os": {"cmd": "echo test"}},
    "schedule": {"trigger": "interval", "minutes": 5}
  }'

# Trigger job
curl -X POST http://127.0.0.1:5000/api/scheduler/jobs/test_job/trigger

# Get status
curl http://127.0.0.1:5000/api/scheduler/jobs/test_job

# Unregister job
curl -X DELETE http://127.0.0.1:5000/api/scheduler/registry/test_job
```

## License

See main project LICENSE file.
