"""
config.py
Configuration cho TTS Service
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
    """TTS Service Configuration"""
    
    # RabbitMQ Settings
    QUEUE_HOST: str = os.getenv("QUEUE_HOST", "localhost")
    QUEUE_PORT: int = int(os.getenv("QUEUE_PORT", "5672"))
    INPUT_QUEUE: str = os.getenv("INPUT_QUEUE", "chat_responses")
    OUTPUT_QUEUE: str = os.getenv("OUTPUT_QUEUE", "tts_audio")
    
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "admin123")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # TTS Settings
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "edge")  # edge, gtts, pyttsx3, coqui
    TTS_VOICE: str = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")  # For Edge TTS
    TTS_RATE: str = os.getenv("TTS_RATE", "+10%")  # Speed adjustment
    TTS_PITCH: str = os.getenv("TTS_PITCH", "+0Hz")  # Pitch adjustment
    
    # Audio Settings
    AUDIO_FORMAT: str = os.getenv("AUDIO_FORMAT", "mp3")
    AUDIO_OUTPUT_DIR: str = os.getenv("AUDIO_OUTPUT_DIR", "./audio_output")
    
    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def get_rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.QUEUE_HOST}:{self.QUEUE_PORT}{self.RABBITMQ_VHOST}"
        )
