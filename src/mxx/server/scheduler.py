"""
Scheduler service for managing APScheduler jobs.

Provides decoupled job management with:
- Dynamic job scheduling
- Job status tracking
- Overlap detection
- Active job monitoring
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from mxx.runner.core.callstack import PluginCallstackMeta
from mxx.runner.core.runner import MxxRunner
from mxx.server.schedule import ScheduleConfig
from mxx.server.registry import JobRegistry
from datetime import datetime
from typing import Dict, List, Optional
import logging
import threading


class JobExecutionContext:
    """Context for a job execution"""
    def __init__(self, job_id: str, config: dict):
        self.job_id = job_id
        self.config = config
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.status: str = "pending"  # pending, running, completed, failed
        self.error: Optional[str] = None


class SchedulerService:
    """
    Decoupled scheduler service for managing plugin execution jobs.
    
    Features:
    - Dynamic job scheduling via API
    - Job status tracking and monitoring
    - Overlap detection for scheduled jobs
    - Thread-safe job management
    - Persistent job registry integration
    """
    
    def __init__(self, max_workers: int = 10, registry: Optional[JobRegistry] = None):
        self.scheduler = BackgroundScheduler(
            executors={'default': ThreadPoolExecutor(max_workers=max_workers)},
            job_defaults={
                'coalesce': True,      # Combine missed runs
                'max_instances': 1     # Only one instance per job
            }
        )
        self.job_contexts: Dict[str, JobExecutionContext] = {}
        self.registry = registry or JobRegistry()
        self._lock = threading.Lock()
        self._started = False
        
        # Monkey-patch scheduler's remove_job to handle JobLookupError gracefully
        self._patch_scheduler_remove_job()
        
        # Add listener to handle job completion
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
    
    def _patch_scheduler_remove_job(self):
        """Patch APScheduler's remove_job to suppress JobLookupError for one-time jobs"""
        original_remove_job = self.scheduler.remove_job
        
        def patched_remove_job(job_id, jobstore=None):
            try:
                return original_remove_job(job_id, jobstore)
            except JobLookupError:
                # Suppress error for already-removed jobs (common with one-time triggers)
                logging.debug(f"Job {job_id} already removed from jobstore")
        
        self.scheduler.remove_job = patched_remove_job
    
    def _job_executed_listener(self, event):
        """Handle job execution completion to prevent JobLookupError"""
        # APScheduler will auto-remove one-time jobs, suppress any errors
        pass
    
    def start(self):
        """Start the scheduler"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logging.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler and wait for jobs to complete"""
        if self._started:
            try:
                self.scheduler.shutdown(wait=True)
                self._started = False
                logging.info("Scheduler stopped")
            except Exception as e:
                logging.error(f"Error stopping scheduler: {e}")
                self._started = False
    
    def schedule_job(
        self,
        job_id: str,
        config: dict,
        schedule_config: Optional[ScheduleConfig] = None,
        replace_existing: bool = False
    ) -> Dict[str, any]:
        """
        Schedule a new job for plugin execution.
        
        Args:
            job_id: Unique identifier for the job
            config: Configuration dict for MxxRunner
            schedule_config: Optional schedule configuration (if None, registers as on-demand)
            replace_existing: Whether to replace existing job with same ID
            
        Returns:
            Dict with job info and status
            
        Raises:
            ValueError: If job_id already exists and replace_existing is False
            ValueError: If schedule overlaps with existing jobs
        """
        with self._lock:
            # Check if job already exists
            if job_id in self.job_contexts and not replace_existing:
                raise ValueError(f"Job '{job_id}' already exists. Use replace_existing=True to replace.")
            
            # Check for overlaps if scheduling
            if schedule_config:
                overlap_info = self._check_overlaps(job_id, schedule_config)
                if overlap_info:
                    raise ValueError(f"Schedule overlaps with existing jobs: {overlap_info}")
            
            # Create job context
            context = JobExecutionContext(job_id, config)
            self.job_contexts[job_id] = context
            
            # Register job in registry
            self.registry.register(
                job_id=job_id,
                config=config,
                schedule=schedule_config,
                source="api",
                replace_existing=replace_existing
            )
            
            # Schedule or just register as on-demand
            if schedule_config:
                # Job has schedule - schedule it with APScheduler
                schedule_dict = schedule_config.to_apscheduler_config()
                self.scheduler.add_job(
                    func=self._execute_job,
                    args=[job_id],
                    **schedule_dict,
                    id=job_id,
                    name=f"Job: {job_id}",
                    replace_existing=replace_existing
                )
                logging.info(f"Scheduled job '{job_id}' with schedule: {schedule_dict}")
                
                # Get next run time from the job trigger
                scheduled_job = self.scheduler.get_job(job_id)
                next_run = None
                if scheduled_job and hasattr(scheduled_job.trigger, 'get_next_fire_time'):
                    next_run = scheduled_job.trigger.get_next_fire_time(None, datetime.now())
                
                return {
                    "job_id": job_id,
                    "status": "scheduled",
                    "schedule": schedule_dict,
                    "next_run": next_run.isoformat() if next_run else None
                }
            else:
                # No schedule - register as on-demand job
                logging.info(f"Registered on-demand job '{job_id}' (trigger via API)")
                return {
                    "job_id": job_id,
                    "status": "registered",
                    "on_demand": True,
                    "hint": f"Trigger execution via POST /api/scheduler/jobs/{job_id}/trigger"
                }
    
    def _check_overlaps(self, new_job_id: str, schedule_config: ScheduleConfig) -> Optional[str]:
        """
        Check if the new schedule overlaps with existing jobs.
        
        Returns:
            String describing overlap if found, None otherwise
        """
        # Get all scheduled jobs (excluding the new one if replacing)
        scheduled_jobs = [
            job for job in self.scheduler.get_jobs()
            if job.id != new_job_id
        ]
        
        if not scheduled_jobs:
            return None
        
        # For interval-based schedules, check if any job would run simultaneously
        if schedule_config.trigger == "interval":
            # Check if any other interval jobs might overlap
            for job in scheduled_jobs:
                if hasattr(job.trigger, 'interval'):
                    # Calculate potential overlap window
                    # If two interval jobs exist, they might overlap
                    return f"Interval-based job '{job.id}' may overlap"
        
        # For cron-based schedules, check for exact time matches
        elif schedule_config.trigger == "cron":
            for job in scheduled_jobs:
                if hasattr(job.trigger, 'fields'):
                    # Check if cron expressions match
                    # This is a simplified check - exact matching
                    trigger = job.trigger
                    if (hasattr(trigger, 'hour') and trigger.hour and 
                        str(schedule_config.hour) in str(trigger.hour) and
                        hasattr(trigger, 'minute') and trigger.minute and
                        str(schedule_config.minute) in str(trigger.minute)):
                        return f"Cron job '{job.id}' scheduled at same time"
        
        return None
    
    def _execute_job(self, job_id: str):
        """
        Execute a job by running all its plugins through MxxRunner.
        """
        context = self.job_contexts.get(job_id)
        if not context:
            logging.error(f"Job context not found for job '{job_id}'")
            return
        
        context.status = "running"
        context.start_time = datetime.now()
        logging.info(f"Starting execution of job '{job_id}'")
        
        try:
            # Clear callstack for this job execution
            PluginCallstackMeta._callstackMap.clear()
            
            # Log the config being used
            logging.info(f"Job '{job_id}' config: {context.config}")
            
            # Create runner and execute
            runner = MxxRunner()
            runner.run(context.config)
            
            context.status = "completed"
            logging.info(f"Job '{job_id}' completed successfully")
            
        except Exception as e:
            context.status = "failed"
            context.error = str(e)
            logging.error(f"Job '{job_id}' failed: {e}", exc_info=True)
        
        finally:
            context.end_time = datetime.now()
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status information for a specific job"""
        context = self.job_contexts.get(job_id)
        if not context:
            return None
        
        job = self.scheduler.get_job(job_id)
        
        result = {
            "job_id": job_id,
            "status": context.status,
            "start_time": context.start_time.isoformat() if context.start_time else None,
            "end_time": context.end_time.isoformat() if context.end_time else None,
            "error": context.error
        }
        
        if job:
            # In APScheduler 3.x, get next_run_time from the trigger
            next_run = job.trigger.get_next_fire_time(None, datetime.now()) if hasattr(job.trigger, 'get_next_fire_time') else None
            result["next_run_time"] = next_run.isoformat() if next_run else None
            result["scheduled"] = True
        else:
            result["scheduled"] = False
        
        return result
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs with their status"""
        jobs = []
        for job_id in self.job_contexts.keys():
            status = self.get_job_status(job_id)
            if status:
                jobs.append(status)
        return jobs
    
    def list_active_jobs(self) -> List[Dict]:
        """List currently running jobs"""
        return [
            self.get_job_status(job_id)
            for job_id, context in self.job_contexts.items()
            if context.status == "running"
        ]
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled job (cannot stop already running jobs).
        
        Returns:
            True if job was cancelled, False if not found or already running
        """
        context = self.job_contexts.get(job_id)
        if not context:
            return False
        
        if context.status == "running":
            logging.warning(f"Cannot cancel running job '{job_id}'")
            return False
        
        job = self.scheduler.get_job(job_id)
        if job:
            try:
                job.remove()
                logging.info(f"Cancelled job '{job_id}'")
            except JobLookupError:
                # Job already removed by APScheduler
                logging.debug(f"Job '{job_id}' was already removed")
        
        # Clean up context
        with self._lock:
            if job_id in self.job_contexts:
                del self.job_contexts[job_id]
        
        return True
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from tracking (for completed/failed jobs).
        
        Returns:
            True if job was removed, False if not found or still scheduled
        """
        context = self.job_contexts.get(job_id)
        if not context:
            return False
        
        if context.status in ["pending", "running"]:
            logging.warning(f"Cannot remove active job '{job_id}'")
            return False
        
        with self._lock:
            del self.job_contexts[job_id]
        
        logging.info(f"Removed job '{job_id}' from tracking")
        return True
    
    def trigger_job(self, job_id: str) -> Dict[str, any]:
        """
        Trigger an on-demand job to run immediately.
        
        This creates a one-time execution of a registered job.
        
        Args:
            job_id: Job identifier from registry
            
        Returns:
            Dict with execution info
            
        Raises:
            ValueError: If job not found in registry
        """
        # Get job from registry
        entry = self.registry.get(job_id)
        if not entry:
            raise ValueError(f"Job '{job_id}' not found in registry")
        
        # Create unique execution ID
        execution_id = f"{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self._lock:
            # Create job context
            context = JobExecutionContext(execution_id, entry.config)
            self.job_contexts[execution_id] = context
        
        # Schedule immediate execution (one-time job)
        self.scheduler.add_job(
            func=self._execute_job,
            args=[execution_id],
            trigger='date',  # One-time trigger
            id=execution_id,
            name=f"Trigger: {job_id}",
            misfire_grace_time=None  # No grace period for missed runs
        )
        
        # Mark in registry
        self.registry.mark_triggered(job_id)
        
        logging.info(f"Triggered on-demand job '{job_id}' as execution '{execution_id}'")
        
        return {
            "job_id": job_id,
            "execution_id": execution_id,
            "status": "triggered",
            "message": f"Job '{job_id}' triggered for immediate execution"
        }
