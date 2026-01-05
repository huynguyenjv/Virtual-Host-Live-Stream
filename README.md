# Hệ thống Virtual Host AI cho Livestream TikTok

## 📋 Giới thiệu

Nghiên cứu xây dựng hệ thống Virtual Host sử dụng AI cho livestream TikTok dựa trên dữ liệu tương tác thời gian thực.

**English Title:** A Real-time AI-based Virtual Host System for Interactive TikTok Livestreaming

---

## 🎯 Vấn đề nghiên cứu

### Thực trạng
- ⏰ Livestream cần người dẫn 24/7
- 😫 Con người dễ mệt mỏi, phản hồi chậm, không nhất quán
- 💬 Chat quá nhiều → bỏ sót comment quan trọng

### Câu hỏi nghiên cứu
1. Làm sao crawl & xử lý comment TikTok realtime ổn định?
2. Làm sao để AI phản hồi tự nhiên, đúng ngữ cảnh live?
3. Có thể kết hợp LLM + TTS + Avatar trong thời gian thực không?
4. Độ trễ (latency) chấp nhận được là bao nhiêu?

---

## 🚀 Đóng góp chính

- ✅ Đề xuất pipeline crawl – training – inference cho livestream
- ✅ Xây dựng dataset hội thoại TikTok tiếng Việt
- ✅ Tích hợp RAG + persona cho Virtual Host
- ✅ Đánh giá độ trễ và mức độ hài lòng người xem

---

## 🏗️ Kiến trúc hệ thống

```
TikTok Live
   ↓
Live Comment Listener
   ↓
Message Queue
   ↓
AI Response Engine
   ↓
Text-to-Speech
   ↓
Avatar Renderer
   ↓
OBS → TikTok Live
```

### Các thành phần chính

#### 1. Data Collection
| Loại dữ liệu | Mục đích |
|--------------|----------|
| Live comment | Inference |
| Comment lịch sử | Training |
| Caption video | Persona |

#### 2. AI Response Engine
```
Input Comment
 → Intent Classifier (PhoBERT)
 → Retriever (Vector DB)
 → LLM Generator (Fine-tuned)
 → Response Text
```

**Điểm mới:**
- 🎯 RAG giúp giảm hallucination
- 👤 Persona được inject cố định

---

## 📊 Dataset Construction

### Làm sạch dữ liệu
- Loại spam
- Chuẩn hóa Unicode
- Loại bình luận trùng

### Gán nhãn (Semi-auto)

| Nhãn | Ví dụ |
|------|-------|
| Greeting | "chào shop" |
| Product | "giá bao nhiêu" |
| Toxic | spam/tục tĩu |
| Off-topic | không liên quan |

### Định dạng

```json
{
  "context": "livestream bán hàng",
  "user": "áo này còn không",
  "response": "Áo này còn đủ size nha em"
}
```

---

## 🤖 Mô hình AI

### Training Pipeline

| Thành phần | Công nghệ |
|------------|-----------|
| Intent Classifier | PhoBERT |
| Embedding | Sentence-BERT |
| LLM | Fine-tune nhẹ |

### Text-to-Speech & Avatar
- **TTS:** Chuyển text → giọng nói
- **Avatar:** Lipsync theo audio
- **Đánh giá:** MOS score, Latency, Đồng bộ môi

---

## ⚡ Performance

### Độ trễ (Latency)

| Stage | Thời gian (ms) |
|-------|----------------|
| Crawl | 200 |
| AI Response | 1,200 |
| TTS | 600 |
| Render | 800 |
| **Total** | **~3,000 (3s)** |

### So sánh với các giải pháp khác

| Hệ thống | Delay | Tự nhiên | Khả năng mở rộng |
|----------|-------|----------|------------------|
| Người thật | Thấp | Cao | Thấp |
| Bot rule-based | Thấp | Thấp | Trung bình |
| **Đề xuất (AI)** | **Chấp nhận** | **Cao** | **Cao** |

### Kết quả
- ✅ Hệ thống chạy ổn định với **> 1,000 comment/phút**
- ✅ Persona giúp tăng tương tác đáng kể
- ⚠️ Phụ thuộc GPU và TikTok API không chính thức

---

## 📈 Đánh giá (Evaluation)

### Metrics
- **BLEU / ROUGE:** Đánh giá độ chính xác phản hồi
- **Human Evaluation:** Khảo sát người dùng thực tế
- **MOS (Mean Opinion Score):** Chất lượng TTS

---

## 🛠️ Tech Stack

- **NLP:** PhoBERT, Sentence-BERT
- **LLM:** Fine-tuned model
- **Vector DB:** RAG implementation
- **TTS:** Vietnamese TTS engine
- **Avatar:** Lipsync rendering
- **Streaming:** OBS integration

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/your-repo/tiktok-virtual-host.git
cd tiktok-virtual-host

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env với các API keys cần thiết
```

---

## 🚦 Quick Start

```bash
# 1. Crawl data (offline)
python scripts/crawl_data.py

# 2. Train model
python scripts/train.py --config configs/train_config.yaml

# 3. Run inference
python main.py --mode live
```

---

## 👥 Team & Contribution

| Thành viên | Phần công việc |
|------------|----------------|
| Member 1 | Backend + Architecture |
| Member 2 | NLP + LLM |
| Member 3 | TTS + Avatar |
| Member 4 | Evaluation + Paper |

---

## 🔮 Hướng phát triển

- [ ] Thêm Emotion AI (phân tích cảm xúc)
- [ ] Multi-host (nhiều avatar)
- [ ] RLHF từ viewer reaction
- [ ] Tối ưu latency xuống < 2s
- [ ] Hỗ trợ multi-language

---

## 📚 Tài liệu tham khảo

1. [TikTok Live API Documentation](#)
2. [PhoBERT Paper](#)
3. [RAG Implementation Guide](#)
4. [Vietnamese TTS Research](#)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 📧 Contact

- **Email:** your.email@example.com
- **Project Link:** [https://github.com/your-repo/tiktok-virtual-host](https://github.com/your-repo/tiktok-virtual-host)

---

**Last Updated:** 05/01/2026  
**Version:** 1.0.0
