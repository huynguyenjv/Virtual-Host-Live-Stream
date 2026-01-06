"""
config.py
Configuration cho Orchestrator Service
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


@dataclass
class Config:
    """Orchestrator Service Configuration"""
    
    # RabbitMQ Settings
    QUEUE_HOST: str = os.getenv("QUEUE_HOST", "localhost")
    QUEUE_PORT: int = int(os.getenv("QUEUE_PORT", "5672"))
    INPUT_QUEUE: str = os.getenv("INPUT_QUEUE", "nlp_results")      # Từ NLP service
    OUTPUT_QUEUE: str = os.getenv("OUTPUT_QUEUE", "chat_requests")  # Đến Chat service
    
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "admin123")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # Brain Settings
    MIN_SPEAK_INTERVAL: float = float(os.getenv("MIN_SPEAK_INTERVAL", "3.0"))
    MAX_SPEAK_INTERVAL: float = float(os.getenv("MAX_SPEAK_INTERVAL", "15.0"))
    DEFAULT_COOLDOWN: float = float(os.getenv("DEFAULT_COOLDOWN", "4.0"))
    HIGH_PRIORITY_THRESHOLD: int = int(os.getenv("HIGH_PRIORITY_THRESHOLD", "7"))
    AUTO_SPEAK_PRIORITY: int = int(os.getenv("AUTO_SPEAK_PRIORITY", "9"))
    
    # State Machine Settings
    ENABLE_STATE_MACHINE: bool = os.getenv("ENABLE_STATE_MACHINE", "true").lower() == "true"
    AUTO_STATE_TRANSITION: bool = os.getenv("AUTO_STATE_TRANSITION", "true").lower() == "true"
    
    # Observability
    METRICS_EXPORT_INTERVAL: int = int(os.getenv("METRICS_EXPORT_INTERVAL", "300"))
    METRICS_EXPORT_PATH: str = os.getenv("METRICS_EXPORT_PATH", "./metrics")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")
    
    # TikTok Integration (for viewer count)
    TIKTOK_USERNAME: str = os.getenv("TIKTOK_USERNAME", "")
    VIEWER_UPDATE_INTERVAL: float = float(os.getenv("VIEWER_UPDATE_INTERVAL", "10.0"))
    
    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def get_rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.QUEUE_HOST}:{self.QUEUE_PORT}{self.RABBITMQ_VHOST}"
        )
    
    def get_brain_config(self) -> dict:
        """Get config dict for LiveBrain"""
        return {
            "min_speak_interval": self.MIN_SPEAK_INTERVAL,
            "max_speak_interval": self.MAX_SPEAK_INTERVAL,
            "default_cooldown": self.DEFAULT_COOLDOWN,
            "high_priority_threshold": self.HIGH_PRIORITY_THRESHOLD,
            "auto_speak_priority": self.AUTO_SPEAK_PRIORITY,
        }
