"""
config.py
Configuration cho Chat Service
"""

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


@dataclass
class Config:
    """Chat Service Configuration"""
    
    # RabbitMQ Settings
    QUEUE_HOST: str = os.getenv("QUEUE_HOST", "localhost")
    QUEUE_PORT: int = int(os.getenv("QUEUE_PORT", "5672"))
    INPUT_QUEUE: str = os.getenv("INPUT_QUEUE", "processed_comments")
    OUTPUT_QUEUE: str = os.getenv("OUTPUT_QUEUE", "chat_responses")
    
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "admin123")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, ollama, gemini
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")  # For Ollama
    
    # Response Settings
    MAX_RESPONSE_LENGTH: int = int(os.getenv("MAX_RESPONSE_LENGTH", "150"))
    RESPONSE_TIMEOUT: float = float(os.getenv("RESPONSE_TIMEOUT", "10.0"))
    
    # Persona Settings
    PERSONA_NAME: str = os.getenv("PERSONA_NAME", "Shop Assistant")
    PERSONA_STYLE: str = os.getenv("PERSONA_STYLE", "friendly")
    
    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def get_rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.QUEUE_HOST}:{self.QUEUE_PORT}{self.RABBITMQ_VHOST}"
        )
