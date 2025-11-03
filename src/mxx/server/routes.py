"""
Flask routes for MXX scheduler service.

Provides HTTP API for:
- Scheduling jobs
- Listing jobs and their status
- Checking active jobs
- Canceling jobs
- Removing completed jobs
- Triggering on-demand jobs
"""

from flask import Blueprint, request, jsonify, current_app
from mxx.server.schedule import ScheduleConfig
import logging

# Create blueprint for scheduler routes
scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')


def get_scheduler_service():
    """Get scheduler service from Flask app config"""
    return current_app.config.get('SCHEDULER_SERVICE')


@scheduler_bp.route('/jobs', methods=['POST'])
def schedule_job():
    """
    Schedule a new job.
    
    Request body:
    {
        "job_id": "my_job_1",
        "config": {
            "lifetime": {"lifetime": 3600},
            "os": {"cmd": "echo test"}
        },
        "schedule": {  // Optional - if omitted, registered as on-demand
            "trigger": "cron",
            "hour": 10,
            "minute": 30
        },
        "replace_existing": false  // Optional - default false
    }
    
    Returns:
        200: Job scheduled successfully
        400: Invalid request or schedule overlap
        500: Server error
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        job_id = data.get('job_id')
        config = data.get('config')
        schedule_data = data.get('schedule')
        replace_existing = data.get('replace_existing', False)
        
        if not job_id:
            return jsonify({"error": "job_id is required"}), 400
        
        if not config:
            return jsonify({"error": "config is required"}), 400
        
        # Parse schedule if provided
        schedule_config = None
        if schedule_data:
            try:
                schedule_config = ScheduleConfig(**schedule_data)
            except Exception as e:
                return jsonify({"error": f"Invalid schedule configuration: {str(e)}"}), 400
        
        # Schedule the job
        scheduler = get_scheduler_service()
        result = scheduler.schedule_job(
            job_id=job_id,
            config=config,
            schedule_config=schedule_config,
            replace_existing=replace_existing
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error scheduling job: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """
    List all jobs with their status.
    
    Returns:
        200: List of all jobs
    """
    try:
        scheduler = get_scheduler_service()
        jobs = scheduler.list_jobs()
        return jsonify({"jobs": jobs, "count": len(jobs)}), 200
    except Exception as e:
        logging.error(f"Error listing jobs: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/jobs/active', methods=['GET'])
def list_active_jobs():
    """
    List currently running jobs.
    
    Returns:
        200: List of active jobs
    """
    try:
        scheduler = get_scheduler_service()
        active_jobs = scheduler.list_active_jobs()
        return jsonify({"jobs": active_jobs, "count": len(active_jobs)}), 200
    except Exception as e:
        logging.error(f"Error listing active jobs: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """
    Get status of a specific job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        200: Job status
        404: Job not found
    """
    try:
        scheduler = get_scheduler_service()
        status = scheduler.get_job_status(job_id)
        
        if not status:
            return jsonify({"error": f"Job '{job_id}' not found"}), 404
        
        return jsonify(status), 200
    except Exception as e:
        logging.error(f"Error getting job status: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/jobs/<job_id>', methods=['DELETE'])
def cancel_job(job_id: str):
    """
    Cancel a scheduled job (cannot stop running jobs).
    
    Args:
        job_id: Job identifier
        
    Returns:
        200: Job cancelled successfully
        400: Cannot cancel running job
        404: Job not found
    """
    try:
        scheduler = get_scheduler_service()
        
        # Check if job exists
        status = scheduler.get_job_status(job_id)
        if not status:
            return jsonify({"error": f"Job '{job_id}' not found"}), 404
        
        # Check if job is running
        if status['status'] == 'running':
            return jsonify({
                "error": "Cannot cancel running job",
                "hint": "Running jobs cannot be stopped mid-execution"
            }), 400
        
        # Cancel the job
        success = scheduler.cancel_job(job_id)
        
        if success:
            return jsonify({"message": f"Job '{job_id}' cancelled successfully"}), 200
        else:
            return jsonify({"error": "Failed to cancel job"}), 500
            
    except Exception as e:
        logging.error(f"Error cancelling job: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/jobs/<job_id>/remove', methods=['POST'])
def remove_job(job_id: str):
    """
    Remove a completed/failed job from tracking.
    
    Args:
        job_id: Job identifier
        
    Returns:
        200: Job removed successfully
        400: Cannot remove active job
        404: Job not found
    """
    try:
        scheduler = get_scheduler_service()
        
        # Check if job exists
        status = scheduler.get_job_status(job_id)
        if not status:
            return jsonify({"error": f"Job '{job_id}' not found"}), 404
        
        # Check if job can be removed
        if status['status'] in ['pending', 'running']:
            return jsonify({
                "error": "Cannot remove active job",
                "hint": "Cancel the job first before removing it"
            }), 400
        
        # Remove the job
        success = scheduler.remove_job(job_id)
        
        if success:
            return jsonify({"message": f"Job '{job_id}' removed successfully"}), 200
        else:
            return jsonify({"error": "Failed to remove job"}), 500
            
    except Exception as e:
        logging.error(f"Error removing job: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/jobs/<job_id>/trigger', methods=['POST'])
def trigger_job(job_id: str):
    """
    Trigger an on-demand job to run immediately.
    
    This creates a one-time execution of a registered job that
    doesn't have a schedule.
    
    Args:
        job_id: Job identifier from registry
        
    Returns:
        200: Job triggered successfully
        404: Job not found
        400: Job cannot be triggered (validation failed)
    """
    try:
        scheduler = get_scheduler_service()
        result = scheduler.trigger_job(job_id)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 404 if "not found" in str(e).lower() else 400
    except Exception as e:
        logging.error(f"Error triggering job: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/registry', methods=['GET'])
def list_registry():
    """
    List all registered jobs.
    
    Query parameters:
        type: Filter by type ("scheduled", "on_demand", "all" - default: "all")
    
    Returns:
        200: List of registered jobs
    """
    try:
        scheduler = get_scheduler_service()
        registry = scheduler.registry
        
        filter_type = request.args.get('type', 'all')
        
        if filter_type == 'scheduled':
            entries = registry.list_scheduled()
        elif filter_type == 'on_demand':
            entries = registry.list_on_demand()
        else:
            entries = registry.list_all()
        
        jobs = [entry.to_dict() for entry in entries]
        
        return jsonify({
            "jobs": jobs,
            "count": len(jobs),
            "filter": filter_type
        }), 200
        
    except Exception as e:
        logging.error(f"Error listing registry: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/registry/<job_id>', methods=['GET'])
def get_registry_entry(job_id: str):
    """
    Get a specific job from registry.
    
    Args:
        job_id: Job identifier
        
    Returns:
        200: Job details
        404: Job not found
    """
    try:
        scheduler = get_scheduler_service()
        entry = scheduler.registry.get(job_id)
        
        if not entry:
            return jsonify({"error": f"Job '{job_id}' not found in registry"}), 404
        
        return jsonify(entry.to_dict()), 200
        
    except Exception as e:
        logging.error(f"Error getting registry entry: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/registry/<job_id>', methods=['DELETE'])
def unregister_job(job_id: str):
    """
    Remove a job from registry.
    
    This also cancels any scheduled execution and removes from tracking.
    
    Args:
        job_id: Job identifier
        
    Returns:
        200: Job unregistered successfully
        404: Job not found
    """
    try:
        scheduler = get_scheduler_service()
        
        # Try to cancel scheduled execution
        scheduler.cancel_job(job_id)
        
        # Remove from registry
        success = scheduler.registry.unregister(job_id)
        
        if success:
            return jsonify({"message": f"Job '{job_id}' unregistered successfully"}), 200
        else:
            return jsonify({"error": f"Job '{job_id}' not found in registry"}), 404
            
    except Exception as e:
        logging.error(f"Error unregistering job: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@scheduler_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        200: Service is healthy
    """
    return jsonify({
        "status": "healthy",
        "service": "mxx-scheduler"
    }), 200
