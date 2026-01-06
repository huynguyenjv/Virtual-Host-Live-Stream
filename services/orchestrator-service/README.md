# Orchestrator Service

## Mô tả

🧠 **Central Brain** - Service quyết định comment nào được respond.

Đây là "não" của hệ thống, nằm giữa NLP và Chat service, quyết định:
- Comment nào đáng để trả lời (SPEAK)
- Comment nào bỏ qua (SKIP)
- Comment nào đưa vào queue chờ (QUEUE)

## Pipeline

```
Crawl → NLP → 🧠 ORCHESTRATOR → Chat → TTS → Avatar → OBS
                    │
                    ├── SPEAK → Forward to Chat
                    ├── SKIP  → Drop
                    └── QUEUE → Priority Queue
```

## Components

### 🧠 Live Brain
- Đánh giá priority của comment
- Quyết định SPEAK/SKIP/QUEUE
- Quản lý cooldown giữa các lần nói

### 🔄 State Machine
- Quản lý sale flow: IDLE → WARM_UP → INTEREST → PRICE → CTA → COOLDOWN
- Điều chỉnh response style theo state
- Auto transition dựa trên intent

### 📊 Observability
- Log tất cả decisions
- Track metrics: response rate, speak interval, viewer delta
- Export metrics định kỳ

## Input Format (từ NLP Service)

```json
{
  "user_id": "123456",
  "username": "user123",
  "nickname": "Người dùng",
  "original_comment": "Sản phẩm này giá bao nhiêu?",
  "intent": "price_question",
  "entities": [],
  "confidence": 0.95,
  "priority": 5,
  "is_follower": true,
  "is_subscriber": false,
  "timestamp": 1704067200.0
}
```

## Output Format (đến Chat Service)

```json
{
  // Original data from NLP
  "user_id": "123456",
  "username": "user123",
  "nickname": "Người dùng",
  "original_comment": "Sản phẩm này giá bao nhiêu?",
  "intent": "price_question",
  
  // Brain decision
  "brain_decision": {
    "action": "SPEAK",
    "reason": "PRICE_QUESTION",
    "priority": 9,
    "cooldown": 3.5,
    "confidence": 0.9
  },
  
  // State info
  "sale_state": "INTEREST",
  "response_style": "informative",
  
  // Timing
  "orchestrator_timestamp": 1704067201.0
}
```

## Environment Variables

```bash
# RabbitMQ
QUEUE_HOST=localhost
QUEUE_PORT=5672
INPUT_QUEUE=nlp_results
OUTPUT_QUEUE=chat_requests
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=admin123

# Brain
MIN_SPEAK_INTERVAL=3.0
MAX_SPEAK_INTERVAL=15.0
DEFAULT_COOLDOWN=4.0
HIGH_PRIORITY_THRESHOLD=7
AUTO_SPEAK_PRIORITY=9

# State Machine
ENABLE_STATE_MACHINE=true
AUTO_STATE_TRANSITION=true

# Observability
METRICS_EXPORT_INTERVAL=300
METRICS_EXPORT_PATH=./metrics
LOG_DIR=./logs

# Debug
DEBUG=false
```

## Chạy Service

```bash
cd services/orchestrator-service

# Install dependencies
pip install -r requirements.txt

# Run
python main.py

# With debug
python main.py --debug

# Without state machine
python main.py --no-state-machine
```

## Decision Logic

### Priority Calculation

```
Base Priority (from intent)
    × State Modifier (current sale state)
    × Viewer Modifier (viewer count)
    + Bonus (follower, subscriber, gift)
    = Final Priority (1-10)
```

### Priority Thresholds

| Priority | Action |
|----------|--------|
| 9-10 | Auto SPEAK |
| 7-8 | SPEAK (if queue not full) |
| 4-6 | SKIP (low priority) |
| 1-3 | SKIP (spam/duplicate) |

### Intent Base Priorities

| Intent | Priority |
|--------|----------|
| purchase_intent | 10 |
| price_question | 9 |
| product_question | 8 |
| complaint | 7 |
| greeting | 6 |
| request | 6 |
| thanks | 5 |
| chitchat | 4 |
| unknown | 3 |
| spam | 1 |

## State Machine Flow

```
┌──────────────────────────────────────────────────────────┐
│                                                           │
│   IDLE ──────▶ WARM_UP ──────▶ INTEREST ──────▶ PRICE   │
│     ▲            │                                  │    │
│     │            │                                  ▼    │
│     │            └──────────────────────────────▶ CTA   │
│     │                                               │    │
│     └───────────────── COOLDOWN ◀───────────────────┘    │
│                                                           │
│   At any time: → HANDLING_QUESTION → (return)           │
│   At any time: → CRISIS → COOLDOWN                      │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## Metrics Tracked

- ⏱️ **Speak Interval**: Time giữa 2 lần nói (avg, min, max)
- 📊 **Response Rate**: % comments được respond
- 💰 **Sale Phrase Rate**: % câu nói có chứa sale phrases
- 👥 **Viewer Delta**: Thay đổi viewer sau mỗi lần nói
- 🔄 **State Transitions**: Số lần chuyển state

## Logs

### Console Output
```
[09:30:15] 💬 COMMENT: [user123] "Giá bao nhiêu?" | intent=price_question
[09:30:15] 🧠 DECISION: action=SPEAK reason=PRICE_QUESTION priority=9
[09:30:15] ✅ SPEAK → Chat | reason=PRICE_QUESTION priority=9
[09:30:15] 🔄 STATE: INTEREST → PRICE (trigger: price_question)
```

### JSON Log (file)
```json
{
  "timestamp": "2024-01-06 09:30:15.123",
  "level": "INFO",
  "category": "BRAIN",
  "message": "Decision: SPEAK",
  "data": {
    "action": "SPEAK",
    "reason": "PRICE_QUESTION",
    "priority": 9,
    "intent": "price_question"
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR SERVICE                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐                                       │
│  │   Consumer   │◀── nlp_results queue                  │
│  │  (RabbitMQ)  │                                       │
│  └──────┬───────┘                                       │
│         │                                                │
│         ▼                                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │                  LIVE BRAIN                      │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │    │
│  │  │ Priority│  │Duplicate│  │    Cooldown     │ │    │
│  │  │  Calc   │  │  Check  │  │    Manager      │ │    │
│  │  └─────────┘  └─────────┘  └─────────────────┘ │    │
│  └─────────────────────┬───────────────────────────┘    │
│                        │                                 │
│         ┌──────────────┼──────────────┐                 │
│         │              │              │                 │
│         ▼              ▼              ▼                 │
│    ┌─────────┐   ┌─────────┐   ┌─────────┐             │
│    │  SPEAK  │   │  SKIP   │   │  QUEUE  │             │
│    └────┬────┘   └─────────┘   └─────────┘             │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐                                       │
│  │  Publisher   │──▶ chat_requests queue                │
│  │  (RabbitMQ)  │                                       │
│  └──────────────┘                                       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              OBSERVABILITY LAYER                 │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │    │
│  │  │ Metrics │  │ Logger  │  │  State Machine  │ │    │
│  │  └─────────┘  └─────────┘  └─────────────────┘ │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```
