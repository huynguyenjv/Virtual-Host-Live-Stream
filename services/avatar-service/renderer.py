"""
renderer.py
2D Vtuber Renderer
Render avatar với lip sync, biểu cảm và animations
"""

import asyncio
import math
import time
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[WARNING] PIL not installed, using placeholder renderer")


class Expression(Enum):
    """Các biểu cảm của avatar"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    THINKING = "thinking"
    SURPRISED = "surprised"
    ANGRY = "angry"


@dataclass
class AvatarState:
    """State hiện tại của avatar"""
    expression: Expression = Expression.NEUTRAL
    mouth_open: float = 0.0        # 0.0 - 1.0
    eye_open: float = 1.0          # 0.0 - 1.0 (blinking)
    head_x: float = 0.0            # Head tilt X
    head_y: float = 0.0            # Head tilt Y
    body_sway: float = 0.0         # Idle animation
    is_speaking: bool = False


@dataclass
class SpriteSet:
    """Bộ sprites cho avatar"""
    base: Optional[Image.Image] = None
    eyes_open: Optional[Image.Image] = None
    eyes_closed: Optional[Image.Image] = None
    mouth_closed: Optional[Image.Image] = None
    mouth_sprites: List[Image.Image] = field(default_factory=list)  # Các mức mở miệng
    expressions: Dict[str, Image.Image] = field(default_factory=dict)


class VtuberRenderer:
    """
    2D Vtuber Renderer
    Hỗ trợ:
    - Sprite-based rendering
    - Lip sync animation
    - Eye blinking
    - Expression changes
    - Idle animations (body sway)
    """
    
    def __init__(self, config):
        self.config = config
        self.width = config.AVATAR_WIDTH
        self.height = config.AVATAR_HEIGHT
        self.fps = config.AVATAR_FPS
        
        # Animation settings
        self.blink_interval = config.BLINK_INTERVAL
        self.blink_duration = config.BLINK_DURATION
        self.sway_amount = config.IDLE_SWAY_AMOUNT
        self.sway_speed = config.IDLE_SWAY_SPEED
        
        # State
        self.state = AvatarState()
        self.sprites: Optional[SpriteSet] = None
        self.last_blink_time = time.time()
        self.start_time = time.time()
        
        # Load sprites
        self._load_sprites()
    
    def _load_sprites(self):
        """Load sprite images từ model path"""
        model_path = self.config.get_model_path()
        
        if not model_path.exists():
            print(f"[WARNING] Model path not found: {model_path}")
            print("[INFO] Using generated placeholder avatar")
            self.sprites = self._create_placeholder_sprites()
            return
        
        try:
            self.sprites = SpriteSet()
            
            # Load base avatar
            base_path = model_path / "base.png"
            if base_path.exists():
                self.sprites.base = Image.open(base_path).convert("RGBA")
            
            # Load eyes
            eyes_open_path = model_path / "eyes_open.png"
            eyes_closed_path = model_path / "eyes_closed.png"
            if eyes_open_path.exists():
                self.sprites.eyes_open = Image.open(eyes_open_path).convert("RGBA")
            if eyes_closed_path.exists():
                self.sprites.eyes_closed = Image.open(eyes_closed_path).convert("RGBA")
            
            # Load mouth sprites (mouth_0.png, mouth_1.png, ...)
            for i in range(6):  # 6 viseme levels
                mouth_path = model_path / f"mouth_{i}.png"
                if mouth_path.exists():
                    self.sprites.mouth_sprites.append(
                        Image.open(mouth_path).convert("RGBA")
                    )
            
            # Load expressions
            for expr in Expression:
                expr_path = model_path / f"expression_{expr.value}.png"
                if expr_path.exists():
                    self.sprites.expressions[expr.value] = Image.open(expr_path).convert("RGBA")
            
            print(f"[INFO] Loaded avatar sprites from {model_path}")
            
        except Exception as e:
            print(f"[ERROR] Failed to load sprites: {e}")
            self.sprites = self._create_placeholder_sprites()
    
    def _create_placeholder_sprites(self) -> SpriteSet:
        """Tạo placeholder avatar khi không có sprites"""
        if not HAS_PIL:
            return SpriteSet()
        
        sprites = SpriteSet()
        
        # Create base - simple anime-style face
        base = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base)
        
        # Face (circle)
        face_color = (255, 224, 189, 255)  # Skin tone
        center_x, center_y = self.width // 2, self.height // 2
        face_radius = min(self.width, self.height) // 3
        draw.ellipse(
            [center_x - face_radius, center_y - face_radius,
             center_x + face_radius, center_y + face_radius],
            fill=face_color
        )
        
        # Hair (simple)
        hair_color = (60, 40, 30, 255)
        draw.ellipse(
            [center_x - face_radius - 10, center_y - face_radius - 20,
             center_x + face_radius + 10, center_y - face_radius + 40],
            fill=hair_color
        )
        
        sprites.base = base
        
        # Eyes open
        eyes_open = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(eyes_open)
        eye_y = center_y - 20
        eye_offset = 35
        eye_color = (50, 50, 50, 255)
        eye_white = (255, 255, 255, 255)
        
        # Left eye
        draw.ellipse([center_x - eye_offset - 15, eye_y - 12,
                      center_x - eye_offset + 15, eye_y + 12], fill=eye_white)
        draw.ellipse([center_x - eye_offset - 8, eye_y - 8,
                      center_x - eye_offset + 8, eye_y + 8], fill=eye_color)
        
        # Right eye
        draw.ellipse([center_x + eye_offset - 15, eye_y - 12,
                      center_x + eye_offset + 15, eye_y + 12], fill=eye_white)
        draw.ellipse([center_x + eye_offset - 8, eye_y - 8,
                      center_x + eye_offset + 8, eye_y + 8], fill=eye_color)
        
        sprites.eyes_open = eyes_open
        
        # Eyes closed
        eyes_closed = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(eyes_closed)
        draw.arc([center_x - eye_offset - 15, eye_y - 5,
                  center_x - eye_offset + 15, eye_y + 10], 0, 180, fill=eye_color, width=3)
        draw.arc([center_x + eye_offset - 15, eye_y - 5,
                  center_x + eye_offset + 15, eye_y + 10], 0, 180, fill=eye_color, width=3)
        sprites.eyes_closed = eyes_closed
        
        # Mouth sprites (6 levels: closed to wide open)
        mouth_y = center_y + 30
        mouth_color = (180, 80, 80, 255)
        
        for i in range(6):
            mouth = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(mouth)
            
            mouth_width = 20 + i * 3
            mouth_height = 2 + i * 5
            
            if i == 0:
                # Closed - simple line
                draw.line([center_x - 15, mouth_y, center_x + 15, mouth_y], 
                          fill=mouth_color, width=2)
            else:
                # Open - ellipse
                draw.ellipse([center_x - mouth_width, mouth_y - mouth_height,
                              center_x + mouth_width, mouth_y + mouth_height],
                             fill=mouth_color)
            
            sprites.mouth_sprites.append(mouth)
        
        return sprites
    
    def update_state(self, mouth_open: float = 0.0, 
                     expression: Expression = None,
                     is_speaking: bool = False):
        """Update avatar state"""
        self.state.mouth_open = max(0.0, min(1.0, mouth_open))
        self.state.is_speaking = is_speaking
        
        if expression:
            self.state.expression = expression
    
    def _update_blink(self):
        """Update eye blinking animation"""
        current_time = time.time()
        time_since_blink = current_time - self.last_blink_time
        
        if time_since_blink >= self.blink_interval:
            # Start blink
            if time_since_blink < self.blink_interval + self.blink_duration:
                # Closing
                progress = (time_since_blink - self.blink_interval) / (self.blink_duration / 2)
                self.state.eye_open = max(0.0, 1.0 - progress)
            elif time_since_blink < self.blink_interval + self.blink_duration * 2:
                # Opening
                progress = (time_since_blink - self.blink_interval - self.blink_duration) / (self.blink_duration / 2)
                self.state.eye_open = min(1.0, progress)
            else:
                # Reset blink timer
                self.last_blink_time = current_time
                self.state.eye_open = 1.0
    
    def _update_idle_sway(self):
        """Update idle body sway animation"""
        elapsed = time.time() - self.start_time
        self.state.body_sway = math.sin(elapsed * self.sway_speed * 2 * math.pi) * self.sway_amount
    
    def render_frame(self) -> Optional[Image.Image]:
        """
        Render một frame của avatar
        
        Returns:
            PIL Image hoặc None
        """
        if not HAS_PIL or not self.sprites:
            return None
        
        # Update animations
        self._update_blink()
        if not self.state.is_speaking:
            self._update_idle_sway()
        
        # Create frame
        frame = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        
        # Apply body sway offset
        offset_x = int(self.state.body_sway)
        offset_y = int(abs(self.state.body_sway) * 0.3)
        
        # Composite layers
        # 1. Base
        if self.sprites.base:
            frame.paste(self.sprites.base, (offset_x, offset_y), self.sprites.base)
        
        # 2. Eyes (blink)
        if self.state.eye_open > 0.5:
            if self.sprites.eyes_open:
                frame.paste(self.sprites.eyes_open, (offset_x, offset_y), self.sprites.eyes_open)
        else:
            if self.sprites.eyes_closed:
                frame.paste(self.sprites.eyes_closed, (offset_x, offset_y), self.sprites.eyes_closed)
        
        # 3. Mouth (lip sync)
        if self.sprites.mouth_sprites:
            mouth_index = int(self.state.mouth_open * (len(self.sprites.mouth_sprites) - 1))
            mouth_index = max(0, min(mouth_index, len(self.sprites.mouth_sprites) - 1))
            mouth_sprite = self.sprites.mouth_sprites[mouth_index]
            frame.paste(mouth_sprite, (offset_x, offset_y), mouth_sprite)
        
        # 4. Expression overlay (if available)
        expr_key = self.state.expression.value
        if expr_key in self.sprites.expressions:
            expr_sprite = self.sprites.expressions[expr_key]
            frame.paste(expr_sprite, (offset_x, offset_y), expr_sprite)
        
        return frame
    
    async def render_animation(self, 
                               lip_sync_frames: List,
                               expression: Expression = Expression.NEUTRAL,
                               duration: float = None) -> List[Image.Image]:
        """
        Render animation sequence với lip sync
        
        Args:
            lip_sync_frames: List of LipSyncFrame từ analyzer
            expression: Biểu cảm trong suốt animation
            duration: Thời lượng (seconds), None = tự động từ lip sync
            
        Returns:
            List of PIL Images
        """
        if not lip_sync_frames:
            return []
        
        frames = []
        
        for lipsync in lip_sync_frames:
            # Update state
            self.update_state(
                mouth_open=lipsync.mouth_open,
                expression=expression,
                is_speaking=lipsync.is_speaking
            )
            
            # Render
            frame = self.render_frame()
            if frame:
                frames.append(frame)
        
        return frames
    
    async def export_video(self, 
                           frames: List[Image.Image],
                           output_path: str,
                           audio_path: str = None) -> bool:
        """
        Export frames thành video file
        
        Args:
            frames: List of PIL Images
            output_path: Đường dẫn output
            audio_path: Đường dẫn audio để merge (optional)
            
        Returns:
            Success status
        """
        if not frames:
            return False
        
        try:
            import imageio
            
            # Convert PIL images to numpy arrays
            np_frames = [np.array(f) for f in frames]
            
            # Write video
            output_format = self.config.OUTPUT_FORMAT
            
            if output_format == 'gif':
                imageio.mimsave(output_path, np_frames, fps=self.fps)
            else:
                # Use ffmpeg writer for better quality
                writer = imageio.get_writer(
                    output_path,
                    fps=self.fps,
                    codec='libvpx-vp9' if output_format == 'webm' else 'libx264',
                    quality=8
                )
                for frame in np_frames:
                    writer.append_data(frame)
                writer.close()
            
            # Merge audio if provided
            if audio_path and Path(audio_path).exists():
                await self._merge_audio(output_path, audio_path)
            
            print(f"[INFO] Exported video: {output_path}")
            return True
            
        except ImportError:
            print("[ERROR] imageio not installed, cannot export video")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to export video: {e}")
            return False
    
    async def _merge_audio(self, video_path: str, audio_path: str):
        """Merge audio vào video using ffmpeg"""
        import subprocess
        
        temp_path = video_path + ".temp"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            temp_path
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                Path(video_path).unlink()
                Path(temp_path).rename(video_path)
        except Exception as e:
            print(f"[WARNING] Failed to merge audio: {e}")


class WebSocketStreamer:
    """
    Stream frames qua WebSocket cho real-time rendering
    """
    
    def __init__(self, config, renderer: VtuberRenderer):
        self.config = config
        self.renderer = renderer
        self.clients = set()
        self.running = False
    
    async def start(self):
        """Start WebSocket server"""
        if not self.config.WEBSOCKET_ENABLED:
            return
        
        try:
            import websockets
            
            self.running = True
            
            async def handler(websocket, path):
                self.clients.add(websocket)
                try:
                    await websocket.wait_closed()
                finally:
                    self.clients.discard(websocket)
            
            server = await websockets.serve(
                handler,
                self.config.WEBSOCKET_HOST,
                self.config.WEBSOCKET_PORT
            )
            
            print(f"[INFO] WebSocket server started on ws://{self.config.WEBSOCKET_HOST}:{self.config.WEBSOCKET_PORT}")
            
            # Stream loop
            while self.running:
                frame = self.renderer.render_frame()
                if frame and self.clients:
                    # Convert to base64 PNG
                    import io
                    import base64
                    
                    buffer = io.BytesIO()
                    frame.save(buffer, format='PNG')
                    frame_data = base64.b64encode(buffer.getvalue()).decode()
                    
                    # Broadcast to all clients
                    for client in self.clients.copy():
                        try:
                            await client.send(frame_data)
                        except:
                            self.clients.discard(client)
                
                await asyncio.sleep(1 / self.renderer.fps)
            
        except ImportError:
            print("[WARNING] websockets not installed, streaming disabled")
    
    def stop(self):
        """Stop WebSocket server"""
        self.running = False
