# AI Module

Module AI/ML cho hệ thống Virtual Host Live Stream.

## 📁 Cấu trúc

```
ai/
├── embeddings/          # Vector embeddings cho RAG
│   ├── embedder.py      # Tạo embeddings từ text
│   └── build_index.py   # Build vector database
│
├── intent-classifier/   # Phân loại ý định comment
│   ├── model.py         # Model architecture
│   ├── train.py         # Training script
│   ├── infer.py         # Inference
│   └── dataset.py       # Data loading
│
├── llm/                 # Large Language Model
│   ├── base_model.py    # Base LLM wrapper
│   ├── fine_tune.py     # Fine-tuning script
│   └── inference.py     # Generate responses
│
└── rag/                 # Retrieval Augmented Generation
    ├── retriever.py     # Retrieve relevant docs
    ├── generator.py     # Generate with context
    └── pipeline.py      # Full RAG pipeline
```

## 🔄 Liên hệ với Services

```
┌─────────────────────────────────────────────────────────────┐
│                         SERVICES                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   crawl → nlp-service ──────→ chat-service → tts → avatar  │
│              │                     │                         │
│              │ uses                │ uses                    │
│              ▼                     ▼                         │
│   ┌──────────────────┐   ┌─────────────────┐                │
│   │ intent-classifier│   │   llm/ + rag/   │                │
│   │   (ai folder)    │   │  (ai folder)    │                │
│   └──────────────────┘   └─────────────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Module Mapping

| Folder | Service sử dụng | Mục đích |
|--------|-----------------|----------|
| `intent-classifier` | nlp-service | Phân loại: greeting, question, thanks... |
| `embeddings` | chat-service | Tạo vector cho RAG search |
| `rag` | chat-service | Tìm context + generate response |
| `llm` | chat-service | Generate câu trả lời |

## 🧠 Intent Classifier

Phân loại ý định của comment từ viewer:

- **greeting** - Chào hỏi ("Xin chào", "Hi")
- **question** - Câu hỏi ("Làm sao...", "Tại sao...")
- **thanks** - Cảm ơn ("Cảm ơn", "Thanks")
- **complaint** - Phàn nàn
- **request** - Yêu cầu ("Cho xin...", "Hát bài...")
- **chitchat** - Nói chuyện phiếm
- **unknown** - Không xác định

## 🔍 RAG Pipeline

```
User Query → Embedder → Vector Search → Top-K Documents
                                              │
                                              ▼
                        LLM ← Context + Query ← Retriever
                         │
                         ▼
                     Response
```

## 🚀 Quick Start

### Training Intent Classifier

```bash
cd ai/intent-classifier
python train.py --data ../data/training/intents.json --epochs 10
```

### Building Embeddings Index

```bash
cd ai/embeddings
python build_index.py --docs ../data/raw/knowledge_base/
```

### Fine-tuning LLM

```bash
cd ai/llm
python fine_tune.py --base-model vinai/PhoGPT --data ../data/training/
```

## 📦 Dependencies

```bash
# Core
torch>=2.0.0
transformers>=4.30.0
sentence-transformers>=2.2.0

# Vector DB
faiss-cpu>=1.7.4
# hoặc
chromadb>=0.4.0

# Vietnamese NLP
underthesea>=6.0.0
pyvi>=0.1.1
```

## 🔧 Models Recommended

| Task | Model | Size | Performance |
|------|-------|------|-------------|
| Intent Classification | PhoBERT-base | 135M | Fast, accurate |
| Embeddings | multilingual-e5-base | 278M | Good for Vietnamese |
| LLM | Vistral-7B-Chat | 7B | Best quality |
| LLM (lighter) | PhoGPT-4B | 4B | Faster |

## 📈 Training Data Format

### Intent Classifier

```json
[
  {"text": "Xin chào mọi người", "intent": "greeting"},
  {"text": "Làm sao để mua hàng?", "intent": "question"},
  {"text": "Cảm ơn bạn nhiều", "intent": "thanks"}
]
```

### RAG Knowledge Base

```
data/raw/knowledge_base/
├── products.txt
├── faq.txt
├── policies.txt
└── scripts.txt
```
