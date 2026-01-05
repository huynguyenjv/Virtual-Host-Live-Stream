"""
audio_utils.py
Audio Utilities
Xử lý, convert, normalize audio
"""

import os
import asyncio
from typing import Optional
from pathlib import Path


class AudioUtils:
    """Audio processing utilities"""
    
    @staticmethod
    async def get_duration(audio_path: str) -> Optional[float]:
        """
        Get audio duration in seconds
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds or None
        """
        try:
            # Try using mutagen (lightweight)
            from mutagen.mp3 import MP3
            audio = MP3(audio_path)
            return audio.info.length
        except ImportError:
            pass
        except:
            pass
        
        try:
            # Fallback to pydub
            from pydub import AudioSegment
            audio = await asyncio.to_thread(AudioSegment.from_file, audio_path)
            return len(audio) / 1000.0
        except ImportError:
            pass
        except:
            pass
        
        return None
    
    @staticmethod
    async def convert_format(
        input_path: str,
        output_format: str = "wav"
    ) -> Optional[str]:
        """
        Convert audio to different format
        
        Args:
            input_path: Input audio file
            output_format: Target format (wav, mp3, ogg)
            
        Returns:
            Path to converted file or None
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            print("[WARN] pydub not installed, cannot convert audio")
            return None
        
        try:
            audio = await asyncio.to_thread(AudioSegment.from_file, input_path)
            
            output_path = Path(input_path).with_suffix(f".{output_format}")
            await asyncio.to_thread(
                audio.export,
                str(output_path),
                format=output_format
            )
            
            return str(output_path)
            
        except Exception as e:
            print(f"[ERROR] Audio convert error: {e}")
            return None
    
    @staticmethod
    async def normalize_audio(
        audio_path: str,
        target_dbfs: float = -20.0
    ) -> bool:
        """
        Normalize audio volume
        
        Args:
            audio_path: Path to audio file
            target_dbfs: Target volume in dBFS
            
        Returns:
            True if successful
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            return False
        
        try:
            audio = await asyncio.to_thread(AudioSegment.from_file, audio_path)
            
            # Calculate change needed
            change_in_dbfs = target_dbfs - audio.dBFS
            
            # Apply normalization
            normalized = audio.apply_gain(change_in_dbfs)
            
            # Save back
            await asyncio.to_thread(
                normalized.export,
                audio_path,
                format=Path(audio_path).suffix[1:]
            )
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Normalize error: {e}")
            return False
    
    @staticmethod
    async def add_silence(
        audio_path: str,
        before_ms: int = 0,
        after_ms: int = 0
    ) -> bool:
        """
        Add silence before/after audio
        
        Args:
            audio_path: Path to audio file
            before_ms: Silence before (milliseconds)
            after_ms: Silence after (milliseconds)
            
        Returns:
            True if successful
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            return False
        
        try:
            audio = await asyncio.to_thread(AudioSegment.from_file, audio_path)
            
            # Create silence
            if before_ms > 0:
                silence_before = AudioSegment.silent(duration=before_ms)
                audio = silence_before + audio
            
            if after_ms > 0:
                silence_after = AudioSegment.silent(duration=after_ms)
                audio = audio + silence_after
            
            # Save back
            await asyncio.to_thread(
                audio.export,
                audio_path,
                format=Path(audio_path).suffix[1:]
            )
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Add silence error: {e}")
            return False
    
    @staticmethod
    def cleanup_old_files(directory: str, max_age_hours: int = 1):
        """
        Cleanup old audio files
        
        Args:
            directory: Audio output directory
            max_age_hours: Max file age in hours
        """
        import time
        
        try:
            now = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file in Path(directory).glob("*"):
                if file.is_file():
                    file_age = now - file.stat().st_mtime
                    if file_age > max_age_seconds:
                        file.unlink()
                        
        except Exception as e:
            print(f"[WARN] Cleanup error: {e}")
