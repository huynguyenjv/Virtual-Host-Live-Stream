"""
talking_head.py
AI Talking Head Renderer - Tạo video người thật từ audio
Hỗ trợ: SadTalker, Wav2Lip, LivePortrait
"""

import asyncio
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


class TalkingHeadEngine(Enum):
    """Các engine hỗ trợ"""
    SADTALKER = "sadtalker"
    WAV2LIP = "wav2lip"
    LIVEPORTRAIT = "liveportrait"
    DID_API = "did"  # Cloud API


@dataclass 
class TalkingHeadConfig:
    """Config cho Talking Head"""
    engine: TalkingHeadEngine = TalkingHeadEngine.SADTALKER
    
    # Input
    source_image: str = "./models/avatar/face.png"  # Ảnh người thật
    
    # SadTalker settings
    sadtalker_path: str = "./engines/SadTalker"
    sadtalker_checkpoint: str = "./checkpoints"
    
    # Wav2Lip settings  
    wav2lip_path: str = "./engines/Wav2Lip"
    wav2lip_checkpoint: str = "./checkpoints/wav2lip_gan.pth"
    
    # LivePortrait settings
    liveportrait_path: str = "./engines/LivePortrait"
    
    # D-ID API (cloud)
    did_api_key: str = ""
    did_presenter_id: str = ""
    
    # Output
    output_dir: str = "./output"
    output_fps: int = 25
    output_size: tuple = (512, 512)
    
    # GPU
    device: str = "cuda"  # cuda or cpu


class BaseTalkingHead(ABC):
    """Base class cho Talking Head engines"""
    
    def __init__(self, config: TalkingHeadConfig):
        self.config = config
    
    @abstractmethod
    async def generate(self, audio_path: str, output_path: str) -> bool:
        """Generate video từ audio"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if engine is available"""
        pass


class SadTalkerEngine(BaseTalkingHead):
    """
    SadTalker - Learning Realistic 3D Motion Coefficients
    https://github.com/OpenTalker/SadTalker
    
    Ưu điểm:
    - Chất lượng cao
    - Realistic head movement
    - Biểu cảm tự nhiên
    
    Nhược điểm:
    - Chậm (~10s/clip trên GPU)
    - Cần GPU mạnh
    """
    
    def __init__(self, config: TalkingHeadConfig):
        super().__init__(config)
        self.engine_path = Path(config.sadtalker_path)
    
    def is_available(self) -> bool:
        inference_script = self.engine_path / "inference.py"
        return inference_script.exists()
    
    async def generate(self, audio_path: str, output_path: str) -> bool:
        """Generate video using SadTalker"""
        
        if not self.is_available():
            print("[ERROR] SadTalker not found. Run setup first.")
            return False
        
        try:
            # Build command
            cmd = [
                "python", str(self.engine_path / "inference.py"),
                "--driven_audio", audio_path,
                "--source_image", self.config.source_image,
                "--result_dir", str(Path(output_path).parent),
                "--checkpoint_dir", self.config.sadtalker_checkpoint,
                "--size", str(self.config.output_size[0]),
                "--expression_scale", "1.0",
                "--still",  # Minimal head movement
                "--preprocess", "crop",
            ]
            
            if self.config.device == "cpu":
                cmd.append("--cpu")
            
            print(f"[INFO] Running SadTalker...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.engine_path)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # SadTalker outputs to result_dir with auto name
                # Need to find and rename
                result_dir = Path(output_path).parent
                for f in result_dir.glob("*.mp4"):
                    if f.name != Path(output_path).name:
                        shutil.move(str(f), output_path)
                        break
                
                print(f"[INFO] Generated: {output_path}")
                return True
            else:
                print(f"[ERROR] SadTalker failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"[ERROR] SadTalker error: {e}")
            return False


class Wav2LipEngine(BaseTalkingHead):
    """
    Wav2Lip - Lip Sync Expert
    https://github.com/Rudrabha/Wav2Lip
    
    Ưu điểm:
    - Nhanh hơn SadTalker
    - Lip sync chính xác
    - Hoạt động với video nguồn
    
    Nhược điểm:
    - Chỉ animate miệng, không có head movement
    - Cần face crop tốt
    """
    
    def __init__(self, config: TalkingHeadConfig):
        super().__init__(config)
        self.engine_path = Path(config.wav2lip_path)
    
    def is_available(self) -> bool:
        inference_script = self.engine_path / "inference.py"
        checkpoint = Path(self.config.wav2lip_checkpoint)
        return inference_script.exists() and checkpoint.exists()
    
    async def generate(self, audio_path: str, output_path: str) -> bool:
        """Generate video using Wav2Lip"""
        
        if not self.is_available():
            print("[ERROR] Wav2Lip not found. Run setup first.")
            return False
        
        try:
            cmd = [
                "python", str(self.engine_path / "inference.py"),
                "--checkpoint_path", self.config.wav2lip_checkpoint,
                "--face", self.config.source_image,
                "--audio", audio_path,
                "--outfile", output_path,
                "--resize_factor", "1",
                "--nosmooth",
            ]
            
            print(f"[INFO] Running Wav2Lip...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.engine_path)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print(f"[INFO] Generated: {output_path}")
                return True
            else:
                print(f"[ERROR] Wav2Lip failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Wav2Lip error: {e}")
            return False


class LivePortraitEngine(BaseTalkingHead):
    """
    LivePortrait - Real-time Portrait Animation
    https://github.com/KwaiVGI/LivePortrait
    
    Ưu điểm:
    - Real-time capable
    - Chất lượng cao
    - Head pose control
    
    Nhược điểm:
    - Mới, ít stable
    - Cần config nhiều
    """
    
    def __init__(self, config: TalkingHeadConfig):
        super().__init__(config)
        self.engine_path = Path(config.liveportrait_path)
    
    def is_available(self) -> bool:
        return (self.engine_path / "inference.py").exists()
    
    async def generate(self, audio_path: str, output_path: str) -> bool:
        """Generate using LivePortrait"""
        # Implementation similar to above
        print("[WARNING] LivePortrait engine not fully implemented yet")
        return False


class DIDApiEngine(BaseTalkingHead):
    """
    D-ID API - Cloud-based Talking Avatar
    https://www.d-id.com/
    
    Ưu điểm:
    - Không cần GPU
    - Chất lượng rất cao
    - Nhiều presenter có sẵn
    
    Nhược điểm:
    - Tốn phí
    - Cần internet
    - Latency cao hơn
    """
    
    def __init__(self, config: TalkingHeadConfig):
        super().__init__(config)
        self.api_key = config.did_api_key
        self.base_url = "https://api.d-id.com"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def generate(self, audio_path: str, output_path: str) -> bool:
        """Generate using D-ID API"""
        
        if not self.is_available():
            print("[ERROR] D-ID API key not configured")
            return False
        
        try:
            import aiohttp
            import base64
            
            # Read audio file
            with open(audio_path, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode()
            
            headers = {
                "Authorization": f"Basic {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Create talk
            payload = {
                "source_url": self.config.source_image,  # or use presenter_id
                "script": {
                    "type": "audio",
                    "audio_url": f"data:audio/mp3;base64,{audio_data}"
                },
                "config": {
                    "stitch": True
                }
            }
            
            async with aiohttp.ClientSession() as session:
                # Create talk request
                async with session.post(
                    f"{self.base_url}/talks",
                    json=payload,
                    headers=headers
                ) as resp:
                    if resp.status != 201:
                        print(f"[ERROR] D-ID API error: {await resp.text()}")
                        return False
                    
                    result = await resp.json()
                    talk_id = result.get("id")
                
                # Poll for completion
                for _ in range(60):  # Max 60 seconds
                    await asyncio.sleep(1)
                    
                    async with session.get(
                        f"{self.base_url}/talks/{talk_id}",
                        headers=headers
                    ) as resp:
                        result = await resp.json()
                        status = result.get("status")
                        
                        if status == "done":
                            video_url = result.get("result_url")
                            
                            # Download video
                            async with session.get(video_url) as video_resp:
                                with open(output_path, 'wb') as f:
                                    f.write(await video_resp.read())
                            
                            print(f"[INFO] Generated: {output_path}")
                            return True
                        
                        elif status == "error":
                            print(f"[ERROR] D-ID generation failed")
                            return False
                
                print("[ERROR] D-ID timeout")
                return False
                
        except ImportError:
            print("[ERROR] aiohttp not installed for D-ID API")
            return False
        except Exception as e:
            print(f"[ERROR] D-ID error: {e}")
            return False


class TalkingHeadRenderer:
    """
    Main Talking Head Renderer
    Auto-select và manage các engine
    """
    
    def __init__(self, config: TalkingHeadConfig):
        self.config = config
        self.engine = self._init_engine()
    
    def _init_engine(self) -> BaseTalkingHead:
        """Initialize engine based on config"""
        
        engine_map = {
            TalkingHeadEngine.SADTALKER: SadTalkerEngine,
            TalkingHeadEngine.WAV2LIP: Wav2LipEngine,
            TalkingHeadEngine.LIVEPORTRAIT: LivePortraitEngine,
            TalkingHeadEngine.DID_API: DIDApiEngine,
        }
        
        engine_class = engine_map.get(self.config.engine, SadTalkerEngine)
        engine = engine_class(self.config)
        
        if engine.is_available():
            print(f"[INFO] Using engine: {self.config.engine.value}")
        else:
            print(f"[WARNING] Engine {self.config.engine.value} not available")
            # Try fallback
            for eng_type, eng_class in engine_map.items():
                fallback = eng_class(self.config)
                if fallback.is_available():
                    print(f"[INFO] Fallback to: {eng_type.value}")
                    return fallback
        
        return engine
    
    async def generate_video(self, audio_path: str, output_path: str = None) -> Optional[str]:
        """
        Generate talking head video từ audio
        
        Args:
            audio_path: Path to audio file
            output_path: Optional output path
            
        Returns:
            Path to generated video or None
        """
        
        if not output_path:
            import uuid
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"talking_{uuid.uuid4().hex[:8]}.mp4")
        
        success = await self.engine.generate(audio_path, output_path)
        
        return output_path if success else None
    
    @staticmethod
    def get_setup_instructions(engine: TalkingHeadEngine) -> str:
        """Get setup instructions for engine"""
        
        instructions = {
            TalkingHeadEngine.SADTALKER: """
# SadTalker Setup
# ================

# 1. Clone repository
git clone https://github.com/OpenTalker/SadTalker.git engines/SadTalker
cd engines/SadTalker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download checkpoints
bash scripts/download_models.sh

# 4. Test
python inference.py --driven_audio examples/driven_audio/bus.wav \\
                    --source_image examples/source_image/art_0.png
""",
            TalkingHeadEngine.WAV2LIP: """
# Wav2Lip Setup
# ==============

# 1. Clone repository
git clone https://github.com/Rudrabha/Wav2Lip.git engines/Wav2Lip
cd engines/Wav2Lip

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download checkpoints
# Download wav2lip_gan.pth from:
# https://github.com/Rudrabha/Wav2Lip#getting-the-weights

# 4. Place in checkpoints/
mkdir -p checkpoints
# Move wav2lip_gan.pth to checkpoints/
""",
            TalkingHeadEngine.LIVEPORTRAIT: """
# LivePortrait Setup
# ==================

# 1. Clone repository  
git clone https://github.com/KwaiVGI/LivePortrait.git engines/LivePortrait
cd engines/LivePortrait

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download models
python scripts/download_models.py
""",
            TalkingHeadEngine.DID_API: """
# D-ID API Setup
# ==============

# 1. Sign up at https://www.d-id.com/
# 2. Get API key from dashboard
# 3. Set environment variable:
export DID_API_KEY=your_api_key

# Or in .env file:
DID_API_KEY=your_api_key
"""
        }
        
        return instructions.get(engine, "No instructions available")
