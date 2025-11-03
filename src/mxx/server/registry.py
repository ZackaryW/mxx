"""
Job registry for persistent storage of registered jobs.

Provides:
- Persistent storage of job configurations in ~/.mxx/server/registry.json
- Separation between scheduled jobs and on-demand jobs
- Job execution history tracking
- Registry operations (add, remove, list, trigger)
"""

from pathlib import Path
from typing import Dict, List, Optional
from mxx.server.schedule import ScheduleConfig
import json
import logging
from datetime import datetime
import threading


class JobRegistryEntry:
    """Entry in the job registry"""
    def __init__(
        self,
        job_id: str,
        config: dict,
        schedule: Optional[ScheduleConfig] = None,
        source: str = "api"
    ):
        self.job_id = job_id
        self.config = config
        self.schedule = schedule
        self.source = source  # "api", "config:filename.toml", etc.
        self.registered_at = datetime.now()
        self.last_triggered: Optional[datetime] = None
        self.execution_count = 0
    
    def to_dict(self) -> dict:
        """Convert entry to dictionary for serialization"""
        return {
            "job_id": self.job_id,
            "config": self.config,
            "schedule": {
                "trigger": self.schedule.trigger,
                "hour": self.schedule.hour,
                "minute": self.schedule.minute,
                "second": self.schedule.second,
                "day_of_week": self.schedule.day_of_week,
                "day": self.schedule.day,
                "interval_seconds": self.schedule.interval_seconds
            } if self.schedule else None,
            "source": self.source,
            "registered_at": self.registered_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "execution_count": self.execution_count
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'JobRegistryEntry':
        """Create entry from dictionary"""
        entry = JobRegistryEntry(
            job_id=data["job_id"],
            config=data["config"],
            schedule=ScheduleConfig(**data["schedule"]) if data.get("schedule") else None,
            source=data.get("source", "api")
        )
        entry.registered_at = datetime.fromisoformat(data["registered_at"])
        if data.get("last_triggered"):
            entry.last_triggered = datetime.fromisoformat(data["last_triggered"])
        entry.execution_count = data.get("execution_count", 0)
        return entry


class JobRegistry:
    """
    Persistent registry for job configurations.
    
    Jobs are stored in two categories:
    - Scheduled: Jobs with schedule config (auto-executed by scheduler)
    - On-demand: Jobs without schedule (executed via trigger API)
    
    Registry is persisted to ~/.mxx/server/registry.json
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize job registry.
        
        Args:
            registry_path: Path to registry file (default: ~/.mxx/server/registry.json)
        """
        if registry_path is None:
            registry_path = Path.home() / ".mxx" / "server" / "registry.json"
        
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._entries: Dict[str, JobRegistryEntry] = {}
        self._lock = threading.Lock()
        
        # Load existing registry
        self._load()
    
    def _load(self):
        """Load registry from disk"""
        if not self.registry_path.exists():
            logging.info(f"No existing registry found at {self.registry_path}")
            return
        
        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)
            
            for entry_data in data.get("entries", []):
                entry = JobRegistryEntry.from_dict(entry_data)
                self._entries[entry.job_id] = entry
            
            logging.info(f"Loaded {len(self._entries)} jobs from registry")
        except Exception as e:
            logging.error(f"Failed to load registry: {e}", exc_info=True)
    
    def _save(self):
        """Save registry to disk"""
        try:
            data = {
                "version": "1.0",
                "entries": [entry.to_dict() for entry in self._entries.values()]
            }
            
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logging.debug(f"Saved registry with {len(self._entries)} entries")
        except Exception as e:
            logging.error(f"Failed to save registry: {e}", exc_info=True)
    
    def register(
        self,
        job_id: str,
        config: dict,
        schedule: Optional[ScheduleConfig] = None,
        source: str = "api",
        replace_existing: bool = False
    ) -> JobRegistryEntry:
        """
        Register a job in the registry.
        
        Args:
            job_id: Unique job identifier
            config: Job configuration dict
            schedule: Optional schedule configuration
            source: Source of the job ("api", "config:filename.toml", etc.)
            replace_existing: Whether to replace existing entry
            
        Returns:
            JobRegistryEntry object
            
        Raises:
            ValueError: If job_id already exists and replace_existing is False
        """
        with self._lock:
            if job_id in self._entries and not replace_existing:
                raise ValueError(f"Job '{job_id}' already registered. Use replace_existing=True to replace.")
            
            entry = JobRegistryEntry(
                job_id=job_id,
                config=config,
                schedule=schedule,
                source=source
            )
            
            self._entries[job_id] = entry
            self._save()
            
            logging.info(f"Registered job '{job_id}' ({source})")
            return entry
    
    def unregister(self, job_id: str) -> bool:
        """
        Remove a job from registry.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was removed, False if not found
        """
        with self._lock:
            if job_id not in self._entries:
                return False
            
            del self._entries[job_id]
            self._save()
            
            logging.info(f"Unregistered job '{job_id}'")
            return True
    
    def get(self, job_id: str) -> Optional[JobRegistryEntry]:
        """Get a job entry by ID"""
        return self._entries.get(job_id)
    
    def list_all(self) -> List[JobRegistryEntry]:
        """List all registered jobs"""
        return list(self._entries.values())
    
    def list_scheduled(self) -> List[JobRegistryEntry]:
        """List jobs with schedules"""
        return [e for e in self._entries.values() if e.schedule is not None]
    
    def list_on_demand(self) -> List[JobRegistryEntry]:
        """List jobs without schedules (on-demand only)"""
        return [e for e in self._entries.values() if e.schedule is None]
    
    def mark_triggered(self, job_id: str):
        """
        Mark a job as triggered (update last_triggered time and count).
        
        Args:
            job_id: Job identifier
        """
        with self._lock:
            entry = self._entries.get(job_id)
            if entry:
                entry.last_triggered = datetime.now()
                entry.execution_count += 1
                self._save()
    
    def exists(self, job_id: str) -> bool:
        """Check if job exists in registry"""
        return job_id in self._entries
