# Data Directory

Thư mục chứa dữ liệu cho hệ thống Virtual Host Live Stream.

## 📁 Cấu trúc

```
data/
├── raw/                 # Dữ liệu thô, chưa xử lý
├── processed/           # Dữ liệu đã xử lý, sẵn sàng sử dụng
├── training/            # Dữ liệu training cho AI models
└── evaluation/          # Dữ liệu đánh giá model
```

## 📂 Chi tiết từng folder

### 📥 `raw/` - Dữ liệu thô

Dữ liệu gốc thu thập được, chưa qua xử lý.

```
raw/
├── comments/            # Comments từ TikTok Live
│   ├── 2024-01-01.jsonl
│   └── ...
├── knowledge_base/      # Tài liệu knowledge base
│   ├── products.txt     # Thông tin sản phẩm
│   ├── faq.txt          # Câu hỏi thường gặp
│   ├── policies.txt     # Chính sách
│   └── scripts.txt      # Kịch bản mẫu
└── audio/               # Audio samples
    └── ...
```

### ⚙️ `processed/` - Dữ liệu đã xử lý

Dữ liệu đã được clean, normalize, sẵn sàng cho training hoặc inference.

```
processed/
├── comments_cleaned.jsonl    # Comments đã clean
├── embeddings/               # Vector embeddings
│   ├── knowledge.faiss       # FAISS index
│   └── knowledge.pkl         # Metadata
└── vocabulary/               # Từ điển
    ├── intents.json
    └── entities.json
```

### 🎯 `training/` - Dữ liệu Training

Dữ liệu được format cho việc training models.

```
training/
├── intent_classifier/
│   ├── train.json       # 80% data
│   ├── val.json         # 10% data
│   └── test.json        # 10% data
├── llm_finetune/
│   ├── conversations.jsonl
│   └── qa_pairs.jsonl
└── rag/
    ├── queries.json
    └── documents.json
```

### 📊 `evaluation/` - Dữ liệu Đánh giá

Dữ liệu và metrics để đánh giá model performance.

```
evaluation/
├── benchmarks/
│   ├── intent_test.json
│   └── response_quality.json
├── results/
│   ├── intent_classifier_v1.json
│   └── llm_finetune_v1.json
└── human_eval/
    └── annotations.json
```

## 📝 Data Formats

### Comments (JSONL)

```json
{"id": "123", "username": "user1", "text": "Xin chào", "timestamp": 1704067200}
{"id": "124", "username": "user2", "text": "Giá bao nhiêu?", "timestamp": 1704067201}
```

### Intent Training Data (JSON)

```json
[
  {
    "text": "Xin chào mọi người",
    "intent": "greeting",
    "entities": []
  },
  {
    "text": "Sản phẩm này giá bao nhiêu?",
    "intent": "question",
    "entities": [{"type": "product", "value": "sản phẩm này"}]
  }
]
```

### LLM Fine-tune Data (JSONL)

```json
{"instruction": "Trả lời comment của viewer", "input": "Xin chào", "output": "Chào bạn! Cảm ơn bạn đã ghé thăm livestream!"}
{"instruction": "Trả lời câu hỏi về giá", "input": "Giá bao nhiêu?", "output": "Dạ sản phẩm này có giá 299k ạ!"}
```

### Knowledge Base (TXT)

```
# products.txt
[Sản phẩm A]
- Giá: 299,000đ
- Mô tả: Sản phẩm chất lượng cao
- Tính năng: Feature 1, Feature 2

[Sản phẩm B]
- Giá: 499,000đ
...
```

## 🔄 Data Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    raw/     │────▶│ Processing  │────▶│ processed/  │
│  (collect)  │     │  Scripts    │     │  (clean)    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐           ┌─────────────┐            ┌─────────────┐
            │  training/  │           │ evaluation/ │            │  Services   │
            │  (models)   │           │  (metrics)  │            │  (runtime)  │
            └─────────────┘           └─────────────┘            └─────────────┘
```

## 🛠️ Scripts

### Collect Comments

```bash
# Chạy crawl service để thu thập comments
python services/crawl-service/main.py --output data/raw/comments/
```

### Process Data

```bash
# Clean và normalize comments
python scripts/process_comments.py \
    --input data/raw/comments/ \
    --output data/processed/comments_cleaned.jsonl

# Build embeddings index
python ai/embeddings/build_index.py \
    --docs data/raw/knowledge_base/ \
    --output data/processed/embeddings/
```

### Split Training Data

```bash
# Split data cho training
python scripts/split_data.py \
    --input data/processed/comments_cleaned.jsonl \
    --output data/training/intent_classifier/ \
    --train 0.8 --val 0.1 --test 0.1
```

## 📏 Data Guidelines

### Quality Requirements

- ✅ Comments phải được clean (remove spam, duplicates)
- ✅ Labels phải consistent
- ✅ Balanced classes cho classification
- ✅ Đủ diversity trong responses

### Privacy

- ⚠️ Không lưu thông tin cá nhân nhạy cảm
- ⚠️ Anonymize user data khi cần
- ⚠️ Tuân thủ TikTok ToS

### Versioning

```
data/
├── v1/          # Version 1 (archived)
├── v2/          # Version 2 (archived)
└── current -> v3/  # Symlink to current version
```

## 📊 Statistics

Theo dõi data statistics:

```bash
python scripts/data_stats.py --path data/

# Output:
# Raw comments: 10,000
# Processed: 8,500
# Training samples: 6,800
# Unique intents: 7
# Avg comment length: 12.5 words
```
