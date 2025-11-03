"""
MXX Scheduler Server

Flask-based HTTP server for managing scheduled and on-demand jobs.

Usage:
    mxx-server [--host HOST] [--port PORT] [--jobs-dir PATH]

Environment Variables:
    MXX_JOBS_DIR: Directory containing job configurations (default: ~/.mxx/jobs)
    MXX_SERVER_HOST: Host to bind to (default: 127.0.0.1)
    MXX_SERVER_PORT: Port to bind to (default: 5000)
"""

from flask import Flask
import logging
import os
from pathlib import Path
import argparse

from mxx.server.flask_runner import FlaskMxxRunner
from mxx.server.routes import scheduler_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_jobs_directory() -> Path:
    """Get the jobs directory from environment or default"""
    jobs_dir = os.environ.get('MXX_JOBS_DIR')
    
    if jobs_dir:
        return Path(jobs_dir).expanduser()
    
    # Default to ~/.mxx/jobs
    return Path.home() / '.mxx' / 'jobs'


def create_app(jobs_dir: Path = None) -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        jobs_dir: Directory containing job configuration files.
                 If None, uses get_jobs_directory()
    
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Use provided directory or get default
    if jobs_dir is None:
        jobs_dir = get_jobs_directory()
    
    # Ensure jobs directory exists
    jobs_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Jobs directory: {jobs_dir}")
    
    # Create FlaskMxxRunner instance (pass app as first argument)
    flask_runner = FlaskMxxRunner(app=app, jobs_dir=jobs_dir)
    
    # Store in app config
    app.config['SCHEDULER_SERVICE'] = flask_runner.scheduler_service
    app.config['FLASK_RUNNER'] = flask_runner
    app.config['JOBS_DIR'] = jobs_dir
    
    # Register blueprints
    app.register_blueprint(scheduler_bp)
    
    # Add root endpoint
    @app.route('/')
    def index():
        return {
            "service": "mxx-scheduler",
            "version": "1.0.0",
            "jobs_dir": str(jobs_dir),
            "endpoints": {
                "health": "/api/scheduler/health",
                "jobs": "/api/scheduler/jobs",
                "registry": "/api/scheduler/registry"
            }
        }
    
    # Add shutdown handler
    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        """Stop scheduler on app shutdown"""
        if 'FLASK_RUNNER' in app.config:
            try:
                app.config['FLASK_RUNNER'].stop()
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}")
    
    return app


def main():
    """
    Main entry point for mxx-server command.
    """
    parser = argparse.ArgumentParser(
        description='MXX Scheduler Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  MXX_JOBS_DIR      Directory containing job configurations (default: ~/.mxx/jobs)
  MXX_SERVER_HOST   Host to bind to (default: 127.0.0.1)
  MXX_SERVER_PORT   Port to bind to (default: 5000)

Examples:
  # Start server with defaults
  mxx-server

  # Start on different port
  mxx-server --port 8080

  # Use custom jobs directory
  mxx-server --jobs-dir /path/to/jobs

  # Listen on all interfaces
  mxx-server --host 0.0.0.0
        """
    )
    
    parser.add_argument(
        '--host',
        default=os.environ.get('MXX_SERVER_HOST', '127.0.0.1'),
        help='Host to bind to (default: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('MXX_SERVER_PORT', 5000)),
        help='Port to bind to (default: 5000)'
    )
    
    parser.add_argument(
        '--jobs-dir',
        type=Path,
        default=get_jobs_directory(),
        help='Directory containing job configurations (default: ~/.mxx/jobs)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode'
    )
    
    args = parser.parse_args()
    
    # Create app
    logger.info("Starting MXX Scheduler Server...")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Jobs directory: {args.jobs_dir}")
    
    app = create_app(jobs_dir=args.jobs_dir)
    
    # Start the FlaskMxxRunner to load configs and start scheduler
    flask_runner = app.config['FLASK_RUNNER']
    flask_runner.start()
    
    logger.info("Server ready!")
    
    # Run Flask app
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False  # Disable reloader to avoid double scheduler start
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        flask_runner.stop()
        logger.info("Server stopped")


if __name__ == '__main__':
    main()
