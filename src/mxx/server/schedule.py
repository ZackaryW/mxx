"""
Schedule configuration for MXX jobs.

Supports cron-style and interval-based scheduling compatible with APScheduler.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ScheduleConfig:
    """
    Configuration for job scheduling.
    
    Supports two trigger types:
    1. cron: Time-based scheduling (daily, weekly, specific times)
    2. interval: Interval-based scheduling (every N seconds)
    
    Examples:
        # Daily at 10:30 AM
        ScheduleConfig(trigger="cron", hour=10, minute=30)
        
        # Every hour
        ScheduleConfig(trigger="cron", minute=0)
        
        # Every 5 minutes
        ScheduleConfig(trigger="interval", interval_seconds=300)
    """
    
    trigger: str  # "cron" or "interval"
    
    # Cron parameters
    hour: Optional[int] = None
    minute: Optional[int] = None
    second: Optional[int] = None
    day_of_week: Optional[str] = None  # "mon", "tue", etc. or "*"
    day: Optional[int] = None  # Day of month
    
    # Interval parameters
    interval_seconds: Optional[int] = None
    
    def __post_init__(self):
        """Validate schedule configuration"""
        if self.trigger not in ["cron", "interval"]:
            raise ValueError(f"Invalid trigger type: {self.trigger}. Must be 'cron' or 'interval'")
        
        if self.trigger == "interval" and not self.interval_seconds:
            raise ValueError("interval_seconds required for interval trigger")
        
        if self.trigger == "cron":
            # At least one time component should be specified
            if all(v is None for v in [self.hour, self.minute, self.second, self.day_of_week, self.day]):
                raise ValueError("At least one time parameter required for cron trigger")
    
    def to_apscheduler_config(self) -> Dict[str, Any]:
        """
        Convert to APScheduler configuration dict.
        
        Returns:
            Dict suitable for APScheduler's add_job(**config)
        """
        if self.trigger == "interval":
            return {
                "trigger": "interval",
                "seconds": self.interval_seconds
            }
        else:  # cron
            config = {"trigger": "cron"}
            
            if self.hour is not None:
                config["hour"] = self.hour
            if self.minute is not None:
                config["minute"] = self.minute
            if self.second is not None:
                config["second"] = self.second
            if self.day_of_week is not None:
                config["day_of_week"] = self.day_of_week
            if self.day is not None:
                config["day"] = self.day
            
            return config
    
    @staticmethod
    def from_dict(data: dict) -> 'ScheduleConfig':
        """Create ScheduleConfig from dictionary"""
        return ScheduleConfig(**data)


def extract_schedule(config: dict) -> Optional[ScheduleConfig]:
    """
    Extract schedule configuration from a job config dict.
    
    Args:
        config: Job configuration dict that may contain 'schedule' key
        
    Returns:
        ScheduleConfig if schedule section exists, None otherwise
    """
    schedule_data = config.get('schedule')
    if not schedule_data:
        return None
    
    try:
        return ScheduleConfig.from_dict(schedule_data)
    except Exception as e:
        raise ValueError(f"Invalid schedule configuration: {e}")
