# Avatar Service - 2D Vtuber

## Mô tả

Service render 2D Vtuber avatar với lip sync từ audio. Nhận audio từ TTS Service, phân tích lip sync, render animation và đẩy sang OBS Service.

## Pipeline

```
TTS Audio → Lip Sync Analysis → Render Frames → Export Video → OBS
```

## Tính năng

### 🎭 Lip Sync
- Phân tích audio amplitude (RMS)
- Map thành 6 viseme levels
- Smoothing để tránh giật
- Threshold để loại bỏ noise

### 👁️ Eye Animation
- Auto blinking mỗi 3 giây
- Smooth transition open/close
- Configurable interval và duration

### 😊 Expressions
- **Neutral** - Mặc định
- **Happy** - Vui vẻ (greeting, thanks)
- **Sad** - Buồn (complaint)
- **Thinking** - Suy nghĩ (question)
- **Surprised** - Ngạc nhiên
- **Angry** - Giận dữ

### 🌊 Idle Animation
- Body sway nhẹ khi không nói
- Configurable amplitude và speed

### 📺 Output Formats
- **WebM** - Recommended, transparent background
- **MP4** - Universal compatibility
- **GIF** - Lightweight, social sharing

## Cấu trúc Avatar Model

```
models/avatar/
├── base.png           # Body, face shape
├── eyes_open.png      # Eyes open state
├── eyes_closed.png    # Eyes closed (blink)
├── mouth_0.png        # Mouth closed
├── mouth_1.png        # Mouth slightly open
├── mouth_2.png        # Mouth open
├── mouth_3.png        # Mouth wide
├── mouth_4.png        # Mouth round
├── mouth_5.png        # Mouth very wide
├── expression_happy.png    # (Optional)
├── expression_sad.png      # (Optional)
└── expression_thinking.png # (Optional)
```

> **Note:** Nếu không có sprites, service sẽ tự động generate placeholder avatar đơn giản.

## Cài đặt

```bash
cd services/avatar-service
pip install -r requirements.txt
```

### Dependencies hệ thống

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg libgl1

# macOS
brew install ffmpeg

# Windows
# Download ffmpeg từ https://ffmpeg.org/download.html
```

## Chạy Service

```bash
# Basic
python main.py

# With debug
python main.py --debug

# Custom settings
python main.py --width 720 --height 720 --fps 24

# With WebSocket streaming
python main.py --websocket
```

## Environment Variables

```bash
# RabbitMQ
QUEUE_HOST=localhost
QUEUE_PORT=5672
INPUT_QUEUE=tts_audio
OUTPUT_QUEUE=avatar_video
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=admin123

# Avatar
AVATAR_MODEL_PATH=./models/avatar
AVATAR_WIDTH=512
AVATAR_HEIGHT=512
AVATAR_FPS=30

# Animation
BLINK_INTERVAL=3.0
BLINK_DURATION=0.15
MOUTH_SMOOTHING=0.3
IDLE_SWAY_AMOUNT=2.0
IDLE_SWAY_SPEED=1.5

# Lip Sync
LIPSYNC_THRESHOLD=0.02
LIPSYNC_SENSITIVITY=1.5

# Output
OUTPUT_FORMAT=webm
OUTPUT_DIR=./output
ENABLE_TRANSPARENCY=true

# WebSocket (optional)
WEBSOCKET_ENABLED=false
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765

# Debug
DEBUG=false
```

## Input Message Format

```json
{
  "user_id": "123456",
  "username": "user123",
  "nickname": "User",
  "original_comment": "Xin chào!",
  "response": "Chào bạn! Cảm ơn đã ghé thăm livestream!",
  "intent": "greeting",
  "priority": 2,
  "audio_path": "/path/to/audio.mp3",
  "audio_duration": 3.5,
  "processed_at": 1704537600.0
}
```

## Output Message Format

```json
{
  "user_id": "123456",
  "username": "user123",
  "nickname": "User",
  "original_comment": "Xin chào!",
  "response": "Chào bạn! Cảm ơn đã ghé thăm livestream!",
  "intent": "greeting",
  "priority": 2,
  "audio_path": "/path/to/audio.mp3",
  "audio_duration": 3.5,
  "video_path": "/path/to/avatar_20240106_120000.webm",
  "video_duration": 3.5,
  "frame_count": 105,
  "fps": 30,
  "processed_at": 1704537601.0
}
```

## WebSocket Streaming

Khi bật `WEBSOCKET_ENABLED=true`, service sẽ stream frames real-time qua WebSocket.

### Client Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onmessage = (event) => {
  const frameData = event.data; // Base64 PNG
  const img = document.getElementById('avatar');
  img.src = 'data:image/png;base64,' + frameData;
};
```

### Use Cases
- Real-time avatar preview
- OBS Browser Source integration
- Interactive streaming overlay

## Tạo Custom Avatar

### 1. Từ ảnh PNG

Chuẩn bị các layer riêng biệt:
- Body layer (không có mắt, miệng)
- Eyes layer (mắt mở, mắt nhắm)
- Mouth layers (6 trạng thái)

### 2. Từ Live2D Model

*(Coming soon)* - Hỗ trợ import Live2D model.

### 3. Từ AI Generated

Sử dụng các tool như:
- Stable Diffusion + ControlNet
- Live Portrait
- Talking Face AI

## Performance

| Resolution | FPS | CPU Usage | RAM Usage |
|------------|-----|-----------|-----------|
| 256x256    | 30  | ~15%      | ~200MB    |
| 512x512    | 30  | ~30%      | ~400MB    |
| 720x720    | 30  | ~45%      | ~600MB    |
| 1080x1080  | 30  | ~70%      | ~1GB      |

> **Tip:** Sử dụng 512x512 cho balance giữa chất lượng và performance.

## Troubleshooting

### "librosa not found"
```bash
pip install librosa
```

### "ffmpeg not found"
Cài đặt ffmpeg và thêm vào PATH.

### "Cannot export WebM with transparency"
Đảm bảo codec `libvpx-vp9` được hỗ trợ trong ffmpeg build.

### Lip sync không khớp
Điều chỉnh `LIPSYNC_SENSITIVITY` và `MOUTH_SMOOTHING`.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Avatar Service                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Consumer   │───▶│  LipSync     │───▶│  Renderer │ │
│  │  (RabbitMQ)  │    │  Analyzer    │    │ (Vtuber)  │ │
│  └──────────────┘    └──────────────┘    └─────┬─────┘ │
│                                                 │       │
│                                                 ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Publisher  │◀───│   Export     │◀───│  Frames   │ │
│  │  (RabbitMQ)  │    │   Video      │    │  (PIL)    │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              WebSocket Streamer                   │   │
│  │              (Optional Real-time)                 │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Future Improvements

- [ ] Live2D model support
- [ ] Multiple avatar presets
- [ ] Dynamic expression detection from text
- [ ] GPU acceleration (OpenGL/Vulkan)
- [ ] Real-time audio streaming input
- [ ] Motion capture integration
