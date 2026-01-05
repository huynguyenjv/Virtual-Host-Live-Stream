"""
tts_engine.py
Text-to-Speech Engines
Hỗ trợ: Edge TTS (Microsoft), gTTS (Google), pyttsx3
"""

import os
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import uuid


class BaseTTSEngine(ABC):
    """Base class cho TTS engines"""
    
    @abstractmethod
    async def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to audio file
        
        Args:
            text: Text to convert
            output_path: Path to save audio file
            
        Returns:
            True if successful
        """
        pass


class EdgeTTSEngine(BaseTTSEngine):
    """
    Microsoft Edge TTS
    Free, high quality, supports Vietnamese
    pip install edge-tts
    """
    
    # Available Vietnamese voices
    VOICES = {
        "female": "vi-VN-HoaiMyNeural",
        "male": "vi-VN-NamMinhNeural"
    }
    
    def __init__(self, voice: str = None, rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice or self.VOICES["female"]
        self.rate = rate
        self.pitch = pitch
    
    async def synthesize(self, text: str, output_path: str) -> bool:
        try:
            import edge_tts
        except ImportError:
            raise ImportError("Please install edge-tts: pip install edge-tts")
        
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            
            await communicate.save(output_path)
            return True
            
        except Exception as e:
            print(f"[ERROR] Edge TTS error: {e}")
            return False
    
    async def list_voices(self, language: str = "vi") -> list:
        """List available voices"""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [v for v in voices if v["Locale"].startswith(language)]
        except:
            return []


class GTTSEngine(BaseTTSEngine):
    """
    Google Text-to-Speech
    pip install gtts
    """
    
    def __init__(self, lang: str = "vi", slow: bool = False):
        self.lang = lang
        self.slow = slow
    
    async def synthesize(self, text: str, output_path: str) -> bool:
        try:
            from gtts import gTTS
        except ImportError:
            raise ImportError("Please install gtts: pip install gtts")
        
        try:
            tts = gTTS(text=text, lang=self.lang, slow=self.slow)
            
            # gTTS is sync, run in thread
            await asyncio.to_thread(tts.save, output_path)
            return True
            
        except Exception as e:
            print(f"[ERROR] gTTS error: {e}")
            return False


class Pyttsx3Engine(BaseTTSEngine):
    """
    pyttsx3 - Offline TTS
    pip install pyttsx3
    """
    
    def __init__(self, rate: int = 150, volume: float = 1.0):
        self.rate = rate
        self.volume = volume
    
    async def synthesize(self, text: str, output_path: str) -> bool:
        try:
            import pyttsx3
        except ImportError:
            raise ImportError("Please install pyttsx3: pip install pyttsx3")
        
        try:
            def _synthesize():
                engine = pyttsx3.init()
                engine.setProperty('rate', self.rate)
                engine.setProperty('volume', self.volume)
                engine.save_to_file(text, output_path)
                engine.runAndWait()
            
            await asyncio.to_thread(_synthesize)
            return True
            
        except Exception as e:
            print(f"[ERROR] pyttsx3 error: {e}")
            return False


class MockTTSEngine(BaseTTSEngine):
    """Mock TTS for testing"""
    
    async def synthesize(self, text: str, output_path: str) -> bool:
        # Create empty file for testing
        Path(output_path).touch()
        return True


class TTSEngine:
    """
    TTS Engine Factory
    """
    
    def __init__(self, config):
        self.config = config
        self.engine = self._create_engine()
        
        # Ensure output directory exists
        os.makedirs(config.AUDIO_OUTPUT_DIR, exist_ok=True)
    
    def _create_engine(self) -> BaseTTSEngine:
        """Create TTS engine based on config"""
        engine_type = self.config.TTS_ENGINE.lower()
        
        if engine_type == "edge":
            return EdgeTTSEngine(
                voice=self.config.TTS_VOICE,
                rate=self.config.TTS_RATE,
                pitch=self.config.TTS_PITCH
            )
        
        elif engine_type == "gtts":
            return GTTSEngine(lang="vi")
        
        elif engine_type == "pyttsx3":
            return Pyttsx3Engine()
        
        else:
            print(f"[WARN] Unknown TTS engine: {engine_type}, using Mock")
            return MockTTSEngine()
    
    def _generate_filename(self) -> str:
        """Generate unique filename for audio"""
        return f"{uuid.uuid4().hex}.{self.config.AUDIO_FORMAT}"
    
    async def synthesize(self, text: str, filename: str = None) -> Optional[str]:
        """
        Synthesize text to audio
        
        Args:
            text: Text to convert
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to audio file or None if failed
        """
        if not text or not text.strip():
            return None
        
        if filename is None:
            filename = self._generate_filename()
        
        output_path = os.path.join(self.config.AUDIO_OUTPUT_DIR, filename)
        
        success = await self.engine.synthesize(text, output_path)
        
        if success and os.path.exists(output_path):
            return output_path
        
        return None
