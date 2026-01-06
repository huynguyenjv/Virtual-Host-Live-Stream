"""
logger.py
Structured Logging cho toàn bộ hệ thống
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Các category log"""
    BRAIN = "BRAIN"           # Live Brain decisions
    STATE = "STATE"           # State machine transitions
    SPEAK = "SPEAK"           # TTS/Avatar speaks
    COMMENT = "COMMENT"       # Incoming comments
    VIEWER = "VIEWER"         # Viewer metrics
    SYSTEM = "SYSTEM"         # System events
    ERROR = "ERROR"           # Errors
    METRIC = "METRIC"         # Metrics events


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: str
    level: str
    category: str
    message: str
    data: Dict[str, Any]
    
    # Optional context
    session_id: Optional[str] = None
    service: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)
    
    def to_console(self) -> str:
        """Format for console output"""
        emoji = {
            "BRAIN": "🧠",
            "STATE": "🔄",
            "SPEAK": "🗣️",
            "COMMENT": "💬",
            "VIEWER": "👥",
            "SYSTEM": "⚙️",
            "ERROR": "❌",
            "METRIC": "📊"
        }.get(self.category, "•")
        
        data_str = ""
        if self.data:
            data_str = " | " + " ".join(f"{k}={v}" for k, v in self.data.items())
        
        return f"[{self.timestamp}] {emoji} {self.category}: {self.message}{data_str}"


class StructuredLogger:
    """
    📝 Structured Logger
    
    Outputs:
    - Console (human-readable)
    - JSON file (machine-readable)
    - Metrics collector integration
    """
    
    def __init__(self, 
                 service_name: str = "virtual-host",
                 log_dir: str = "./logs",
                 console_level: LogLevel = LogLevel.INFO,
                 file_level: LogLevel = LogLevel.DEBUG):
        
        self.service_name = service_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.console_level = console_level
        self.file_level = file_level
        
        # Session ID for this run
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Log file
        self.log_file = self.log_dir / f"{service_name}_{self.session_id}.jsonl"
        
        # Setup Python logger
        self._setup_python_logger()
    
    def _setup_python_logger(self):
        """Setup standard Python logger"""
        self.logger = logging.getLogger(self.service_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(getattr(logging, self.console_level.value))
        console.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console)
    
    def _get_level_value(self, level: LogLevel) -> int:
        """Get numeric value for level comparison"""
        levels = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }
        return levels.get(level, 1)
    
    def _should_log_console(self, level: LogLevel) -> bool:
        return self._get_level_value(level) >= self._get_level_value(self.console_level)
    
    def _should_log_file(self, level: LogLevel) -> bool:
        return self._get_level_value(level) >= self._get_level_value(self.file_level)
    
    def log(self, 
            category: LogCategory,
            message: str,
            data: Dict[str, Any] = None,
            level: LogLevel = LogLevel.INFO):
        """Main log method"""
        
        entry = LogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            level=level.value,
            category=category.value,
            message=message,
            data=data or {},
            session_id=self.session_id,
            service=self.service_name
        )
        
        # Console
        if self._should_log_console(level):
            print(entry.to_console())
        
        # File
        if self._should_log_file(level):
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(entry.to_json() + '\n')
    
    # ==================== CONVENIENCE METHODS ====================
    
    def brain(self, message: str, **kwargs):
        """Log brain decision"""
        self.log(LogCategory.BRAIN, message, kwargs)
    
    def state(self, message: str, **kwargs):
        """Log state transition"""
        self.log(LogCategory.STATE, message, kwargs)
    
    def speak(self, message: str, **kwargs):
        """Log speak event"""
        self.log(LogCategory.SPEAK, message, kwargs)
    
    def comment(self, message: str, **kwargs):
        """Log comment event"""
        self.log(LogCategory.COMMENT, message, kwargs, level=LogLevel.DEBUG)
    
    def viewer(self, message: str, **kwargs):
        """Log viewer metrics"""
        self.log(LogCategory.VIEWER, message, kwargs)
    
    def system(self, message: str, **kwargs):
        """Log system event"""
        self.log(LogCategory.SYSTEM, message, kwargs)
    
    def metric(self, message: str, **kwargs):
        """Log metric event"""
        self.log(LogCategory.METRIC, message, kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error"""
        self.log(LogCategory.ERROR, message, kwargs, level=LogLevel.ERROR)
    
    def warning(self, message: str, **kwargs):
        """Log warning"""
        self.log(LogCategory.SYSTEM, message, kwargs, level=LogLevel.WARNING)
    
    def debug(self, message: str, **kwargs):
        """Log debug info"""
        self.log(LogCategory.SYSTEM, message, kwargs, level=LogLevel.DEBUG)
    
    # ==================== SPECIAL LOGS ====================
    
    def log_decision(self, action: str, reason: str, priority: int, **extra):
        """Log brain decision with standard format"""
        self.brain(
            f"Decision: {action}",
            action=action,
            reason=reason,
            priority=priority,
            **extra
        )
    
    def log_state_transition(self, from_state: str, to_state: str, trigger: str):
        """Log state transition with standard format"""
        self.state(
            f"{from_state} → {to_state}",
            from_state=from_state,
            to_state=to_state,
            trigger=trigger
        )
    
    def log_speak_event(self, text: str, duration: float, intent: str, viewers: int):
        """Log speak event with standard format"""
        preview = text[:50] + "..." if len(text) > 50 else text
        self.speak(
            f'"{preview}"',
            duration=f"{duration:.1f}s",
            intent=intent,
            viewers=viewers
        )
    
    def log_comment_received(self, username: str, text: str, intent: str):
        """Log incoming comment"""
        preview = text[:30] + "..." if len(text) > 30 else text
        self.comment(
            f'[{username}] "{preview}"',
            intent=intent
        )
    
    def log_viewer_update(self, count: int, delta: int = 0):
        """Log viewer count update"""
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        self.viewer(
            f"Viewers: {count} ({delta_str})",
            count=count,
            delta=delta
        )
    
    def log_session_start(self, **config):
        """Log session start"""
        self.system(
            "Session started",
            session_id=self.session_id,
            **config
        )
    
    def log_session_end(self, duration: float, stats: dict):
        """Log session end with stats"""
        self.system(
            f"Session ended after {duration:.1f}s",
            **stats
        )


# Singleton instance
_logger: Optional[StructuredLogger] = None


def get_logger(service_name: str = "virtual-host") -> StructuredLogger:
    """Get singleton logger instance"""
    global _logger
    
    if _logger is None:
        _logger = StructuredLogger(service_name=service_name)
    
    return _logger
