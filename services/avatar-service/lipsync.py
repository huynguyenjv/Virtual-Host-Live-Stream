"""
lipsync.py
Lip Sync Analysis từ Audio cho 2D Vtuber
Phân tích audio amplitude để điều khiển miệng avatar
"""

import asyncio
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LipSyncFrame:
    """Data cho một frame lip sync"""
    timestamp: float          # Thời điểm trong audio (seconds)
    mouth_open: float        # Độ mở miệng (0.0 - 1.0)
    volume: float            # Volume level (0.0 - 1.0)
    is_speaking: bool        # Đang nói hay không


class LipSyncAnalyzer:
    """
    Phân tích audio để tạo lip sync data
    Sử dụng RMS amplitude và frequency analysis
    """
    
    def __init__(self, config):
        self.config = config
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.threshold = config.LIPSYNC_THRESHOLD
        self.sensitivity = config.LIPSYNC_SENSITIVITY
        self.smoothing = config.MOUTH_SMOOTHING
    
    async def analyze(self, audio_path: str, fps: int = 30) -> List[LipSyncFrame]:
        """
        Phân tích audio file và trả về lip sync data
        
        Args:
            audio_path: Đường dẫn tới audio file
            fps: Frame rate của animation
            
        Returns:
            List[LipSyncFrame]: Lip sync data cho mỗi frame
        """
        try:
            # Load audio
            audio_data, duration = await self._load_audio(audio_path)
            
            if audio_data is None:
                return []
            
            # Calculate frames
            total_frames = int(duration * fps)
            samples_per_frame = len(audio_data) / total_frames
            
            frames = []
            prev_mouth_open = 0.0
            
            for i in range(total_frames):
                # Get audio segment for this frame
                start_idx = int(i * samples_per_frame)
                end_idx = int((i + 1) * samples_per_frame)
                segment = audio_data[start_idx:end_idx]
                
                # Calculate RMS amplitude
                rms = np.sqrt(np.mean(segment ** 2)) if len(segment) > 0 else 0
                
                # Normalize and apply sensitivity
                normalized = min(1.0, rms * self.sensitivity)
                
                # Apply threshold
                is_speaking = normalized > self.threshold
                mouth_open = normalized if is_speaking else 0.0
                
                # Apply smoothing (lerp with previous frame)
                mouth_open = prev_mouth_open + (mouth_open - prev_mouth_open) * (1 - self.smoothing)
                prev_mouth_open = mouth_open
                
                # Create frame data
                frame = LipSyncFrame(
                    timestamp=i / fps,
                    mouth_open=mouth_open,
                    volume=normalized,
                    is_speaking=is_speaking
                )
                frames.append(frame)
            
            return frames
            
        except Exception as e:
            print(f"[ERROR] Lip sync analysis failed: {e}")
            return []
    
    async def _load_audio(self, audio_path: str) -> Tuple[Optional[np.ndarray], float]:
        """
        Load audio file và convert sang numpy array
        
        Returns:
            Tuple[audio_data, duration_seconds]
        """
        path = Path(audio_path)
        if not path.exists():
            print(f"[ERROR] Audio file not found: {audio_path}")
            return None, 0.0
        
        try:
            # Try librosa first (better quality)
            import librosa
            audio_data, sr = librosa.load(str(path), sr=self.sample_rate, mono=True)
            duration = len(audio_data) / sr
            return audio_data, duration
            
        except ImportError:
            # Fallback to pydub
            try:
                from pydub import AudioSegment
                
                audio = AudioSegment.from_file(str(path))
                audio = audio.set_frame_rate(self.sample_rate).set_channels(1)
                
                # Convert to numpy
                samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
                samples = samples / (2 ** 15)  # Normalize to [-1, 1]
                
                duration = len(audio) / 1000.0  # ms to seconds
                return samples, duration
                
            except Exception as e:
                print(f"[ERROR] Failed to load audio: {e}")
                return None, 0.0
    
    def get_phoneme_mouth_shape(self, phoneme: str) -> float:
        """
        Map phoneme sang mouth shape (cho advanced lip sync)
        
        Args:
            phoneme: Phoneme code (ví dụ: 'AA', 'EE', 'OO', ...)
            
        Returns:
            Mouth open value (0.0 - 1.0)
        """
        phoneme_map = {
            # Vowels - miệng mở
            'AA': 0.9,  # "ah" - mở rộng
            'AE': 0.7,  # "a" 
            'AH': 0.6,
            'AO': 0.8,  # "o"
            'AW': 0.7,
            'AY': 0.6,
            'EH': 0.5,
            'ER': 0.4,
            'EY': 0.5,
            'IH': 0.3,
            'IY': 0.2,  # "ee" - ít mở
            'OW': 0.7,
            'OY': 0.6,
            'UH': 0.5,
            'UW': 0.3,  # "oo" - chu môi
            
            # Consonants - miệng đóng hoặc ít mở
            'B': 0.0,   # Đóng
            'CH': 0.2,
            'D': 0.1,
            'DH': 0.2,
            'F': 0.1,
            'G': 0.2,
            'HH': 0.3,
            'JH': 0.2,
            'K': 0.1,
            'L': 0.3,
            'M': 0.0,   # Đóng
            'N': 0.1,
            'NG': 0.2,
            'P': 0.0,   # Đóng
            'R': 0.3,
            'S': 0.1,
            'SH': 0.2,
            'T': 0.1,
            'TH': 0.2,
            'V': 0.1,
            'W': 0.2,
            'Y': 0.2,
            'Z': 0.1,
            'ZH': 0.2,
            
            # Silence
            'SIL': 0.0,
            '': 0.0
        }
        
        return phoneme_map.get(phoneme.upper(), 0.3)


class VisemeMapper:
    """
    Map mouth shapes sang visemes cho 2D avatar
    Viseme = Visual Phoneme
    """
    
    # 6 basic visemes cho 2D Vtuber đơn giản
    VISEMES = {
        'closed': 0,      # Miệng đóng (M, B, P)
        'slightly_open': 1,  # Hơi mở (F, V)
        'open': 2,        # Mở (AH)
        'wide': 3,        # Mở rộng (AA, AE)
        'round': 4,       # Tròn môi (O, OO)
        'smile': 5        # Cười (EE, IY)
    }
    
    @classmethod
    def mouth_to_viseme(cls, mouth_open: float) -> str:
        """
        Convert mouth_open value sang viseme name
        
        Args:
            mouth_open: 0.0 - 1.0
            
        Returns:
            Viseme name
        """
        if mouth_open < 0.1:
            return 'closed'
        elif mouth_open < 0.3:
            return 'slightly_open'
        elif mouth_open < 0.5:
            return 'open'
        elif mouth_open < 0.7:
            return 'wide'
        else:
            return 'round'
    
    @classmethod
    def get_viseme_index(cls, mouth_open: float) -> int:
        """Get viseme index cho sprite selection"""
        viseme = cls.mouth_to_viseme(mouth_open)
        return cls.VISEMES.get(viseme, 0)
