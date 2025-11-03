"""
MXX Scheduler Client

Command-line interface for interacting with the MXX Scheduler Server.

Usage:
    mxx-client [OPTIONS] COMMAND [ARGS]...

Commands:
    list        List all jobs
    status      Get status of a specific job
    trigger     Trigger an on-demand job
    cancel      Cancel a scheduled job
    remove      Remove a completed/failed job
    register    Register a new job
    unregister  Unregister a job
    registry    List registered jobs
    health      Check server health
"""

import click
import requests
import json
import os
from pathlib import Path
from typing import Optional
import sys


def get_server_url() -> str:
    """Get server URL from environment or default"""
    host = os.environ.get('MXX_SERVER_HOST', '127.0.0.1')
    port = os.environ.get('MXX_SERVER_PORT', '5000')
    return f"http://{host}:{port}"


def handle_response(response: requests.Response, success_message: str = None):
    """
    Handle HTTP response and print formatted output.
    
    Args:
        response: Response object
        success_message: Optional message to show on success
    """
    try:
        data = response.json()
    except Exception:
        data = {"text": response.text}
    
    if response.status_code >= 200 and response.status_code < 300:
        if success_message:
            click.echo(click.style(success_message, fg='green'))
        
        # Pretty print JSON data
        if data:
            click.echo(json.dumps(data, indent=2))
    else:
        click.echo(click.style(f"Error: {response.status_code}", fg='red'), err=True)
        if 'error' in data:
            click.echo(click.style(data['error'], fg='red'), err=True)
            if 'hint' in data:
                click.echo(click.style(f"Hint: {data['hint']}", fg='yellow'), err=True)
        else:
            click.echo(json.dumps(data, indent=2), err=True)
        sys.exit(1)


@click.group()
@click.option('--server', default=None, help='Server URL (default: http://127.0.0.1:5000)')
@click.pass_context
def cli(ctx, server: Optional[str]):
    """MXX Scheduler Client - Manage scheduled jobs"""
    ctx.ensure_object(dict)
    ctx.obj['SERVER_URL'] = server or get_server_url()


@cli.command()
@click.pass_context
def health(ctx):
    """Check server health"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.get(f"{server_url}/api/scheduler/health", timeout=5)
        handle_response(response)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.option('--type', 'filter_type', type=click.Choice(['all', 'active', 'scheduled']), 
              default='all', help='Filter jobs by type')
@click.pass_context
def list(ctx, filter_type: str):
    """List all jobs"""
    server_url = ctx.obj['SERVER_URL']
    
    if filter_type == 'active':
        endpoint = f"{server_url}/api/scheduler/jobs/active"
    else:
        endpoint = f"{server_url}/api/scheduler/jobs"
    
    try:
        response = requests.get(endpoint, timeout=5)
        handle_response(response)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.pass_context
def status(ctx, job_id: str):
    """Get status of a specific job"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.get(f"{server_url}/api/scheduler/jobs/{job_id}", timeout=5)
        handle_response(response)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.pass_context
def trigger(ctx, job_id: str):
    """Trigger an on-demand job to run immediately"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.post(f"{server_url}/api/scheduler/jobs/{job_id}/trigger", timeout=5)
        handle_response(response, f"Job '{job_id}' triggered successfully")
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.pass_context
def cancel(ctx, job_id: str):
    """Cancel a scheduled job"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.delete(f"{server_url}/api/scheduler/jobs/{job_id}", timeout=5)
        handle_response(response, f"Job '{job_id}' cancelled successfully")
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.pass_context
def remove(ctx, job_id: str):
    """Remove a completed/failed job from tracking"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.post(f"{server_url}/api/scheduler/jobs/{job_id}/remove", timeout=5)
        handle_response(response, f"Job '{job_id}' removed successfully")
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--job-id', required=True, help='Unique identifier for the job')
@click.option('--replace', is_flag=True, help='Replace existing job if it exists')
@click.pass_context
def register(ctx, config_file: str, job_id: str, replace: bool):
    """
    Register a new job from a configuration file.
    
    The config file should be in JSON, TOML, or YAML format.
    It may include an optional [schedule] section.
    
    Example TOML:
    \b
        [lifetime]
        lifetime = 3600
        
        [os]
        cmd = "echo hello"
        
        [schedule]
        trigger = "cron"
        hour = 10
        minute = 30
    """
    server_url = ctx.obj['SERVER_URL']
    
    # Load config file
    config_path = Path(config_file)
    
    try:
        from mxx.runner.core.config_loader import load_config
        config_data = load_config(config_path)
        
        # Extract schedule if present
        schedule_data = config_data.pop('schedule', None)
        
        # Prepare request payload
        payload = {
            'job_id': job_id,
            'config': config_data,
            'replace_existing': replace
        }
        
        if schedule_data:
            payload['schedule'] = schedule_data
        
        # Send request
        response = requests.post(
            f"{server_url}/api/scheduler/jobs",
            json=payload,
            timeout=10
        )
        
        handle_response(response, f"Job '{job_id}' registered successfully")
        
    except ImportError:
        click.echo(click.style("Error: mxx package not properly installed", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error loading config: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.pass_context
def unregister(ctx, job_id: str):
    """Unregister a job from the registry"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.delete(f"{server_url}/api/scheduler/registry/{job_id}", timeout=5)
        handle_response(response, f"Job '{job_id}' unregistered successfully")
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.option('--type', 'filter_type', 
              type=click.Choice(['all', 'scheduled', 'on_demand']),
              default='all', 
              help='Filter by job type')
@click.pass_context
def registry(ctx, filter_type: str):
    """List all registered jobs"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.get(
            f"{server_url}/api/scheduler/registry",
            params={'type': filter_type},
            timeout=5
        )
        handle_response(response)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.pass_context
def info(ctx, job_id: str):
    """Get detailed information about a registered job"""
    server_url = ctx.obj['SERVER_URL']
    
    try:
        response = requests.get(f"{server_url}/api/scheduler/registry/{job_id}", timeout=5)
        handle_response(response)
    except requests.exceptions.ConnectionError:
        click.echo(click.style(f"Error: Cannot connect to server at {server_url}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
