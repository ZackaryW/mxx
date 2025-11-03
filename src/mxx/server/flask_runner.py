"""
Flask-integrated runner - thin wrapper around SchedulerService.

This module provides Flask integration for the MXX scheduler service.
It auto-loads configs from ~/.mxx/jobs/ and schedules them based on their
schedule section.
"""

from flask import Flask
from mxx.server.scheduler import SchedulerService
from mxx.server.registry import JobRegistry
from mxx.runner.core.config_loader import load_config
from mxx.server.schedule import extract_schedule
from pathlib import Path
import logging


class FlaskMxxRunner:
    """
    Flask-integrated runner with APScheduler support.
    
    This wrapper:
    - Provides Flask app integration
    - Manages scheduler lifecycle
    - Auto-loads configs from ~/.mxx/jobs/ on startup
    - Schedules configs that have a schedule section
    - Exposes scheduler service for routes (dynamic scheduling)
    """
    
    def __init__(self, app: Flask, max_workers: int = 10, jobs_dir: Path = None):
        """
        Initialize Flask runner with scheduler service.
        
        Args:
            app: Flask application instance
            max_workers: Maximum number of concurrent job workers
            jobs_dir: Directory to load job configs from (default: ~/.mxx/jobs)
        """
        self.app = app
        self.jobs_dir = jobs_dir or Path.home() / ".mxx" / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry = JobRegistry()
        self.scheduler_service = SchedulerService(max_workers=max_workers, registry=self.registry)
        
        # Store reference in app context for routes
        app.config['SCHEDULER_SERVICE'] = self.scheduler_service
    
    def load_configs_from_directory(self):
        """
        Load all config files from ~/.mxx/jobs/ and register them.
        
        This method:
        1. Finds all config files (.toml, .yaml, .json) excluding templates
        2. Parses each config
        3. Checks if config has a 'schedule' section
        4. If schedule exists: Scheduled automatically
        5. If no schedule: Registered as on-demand job (trigger via API)
        """
        # Find all config files (exclude templates)
        config_files = []
        for pattern in ["*.toml", "*.yaml", "*.yml", "*.json"]:
            config_files.extend([
                f for f in self.jobs_dir.glob(pattern)
                if not f.name.endswith(".template.toml") and
                   not f.name.endswith(".template.yaml") and
                   not f.name.endswith(".template.json")
            ])
        
        logging.info(f"Loading {len(config_files)} config files from {self.jobs_dir}")
        
        for config_file in config_files:
            try:
                # Load config using config_loader
                config = load_config(config_file)
                
                # Extract schedule
                schedule_config = extract_schedule(config)
                
                # Use filename (without extension) as job_id
                job_id = config_file.stem
                
                # Register the job (with or without schedule)
                result = self.scheduler_service.schedule_job(
                    job_id=job_id,
                    config=config,
                    schedule_config=schedule_config,
                    replace_existing=True  # Allow server restarts to replace jobs
                )
                
                # Update registry source to indicate config file origin
                if self.registry.exists(job_id):
                    entry = self.registry.get(job_id)
                    entry.source = f"config:{config_file.name}"
                    self.registry._save()
                
                if schedule_config:
                    logging.info(f"Scheduled job '{job_id}' from {config_file.name}: {result}")
                else:
                    logging.info(f"Registered on-demand job '{job_id}' from {config_file.name}: {result}")
                
            except Exception as e:
                logging.error(f"Failed to load config {config_file.name}: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler and load configs from directory"""
        self.load_configs_from_directory()
        self.scheduler_service.start()
        logging.info("Flask runner started")
    
    def stop(self):
        """Stop the scheduler and wait for jobs to complete"""
        self.scheduler_service.stop()
        logging.info("Flask runner stopped")
