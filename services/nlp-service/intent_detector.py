"""
intent_detector.py
Intent Classification cho Comments
Sử dụng rule-based trước, có thể upgrade lên PhoBERT sau
"""

from enum import Enum
from typing import Tuple
import re


class Intent(Enum):
    """Các loại intent"""
    GREETING = "greeting"           # Chào hỏi
    PRODUCT_INQUIRY = "product"     # Hỏi về sản phẩm
    PRICE_INQUIRY = "price"         # Hỏi giá
    SHIPPING_INQUIRY = "shipping"   # Hỏi ship/giao hàng
    COMPLIMENT = "compliment"       # Khen ngợi
    COMPLAINT = "complaint"         # Phàn nàn
    ORDER = "order"                 # Muốn đặt hàng
    GENERAL_QUESTION = "question"   # Câu hỏi chung
    CHITCHAT = "chitchat"           # Nói chuyện phiếm
    UNKNOWN = "unknown"             # Không xác định


class IntentDetector:
    """
    Rule-based Intent Detector
    Có thể thay thế bằng PhoBERT classifier sau
    """
    
    # Intent patterns
    INTENT_PATTERNS = {
        Intent.GREETING: [
            r'\b(chào|hi|hello|xin chào|alo|helu|helo)\b',
            r'^(chào shop|chào chị|chào anh|chào bạn)',
        ],
        Intent.PRICE_INQUIRY: [
            r'\b(bao nhiêu|giá|bn|bnh|giá tiền|how much)\b',
            r'\b(mấy k|mấy nghìn|mấy trăm)\b',
        ],
        Intent.PRODUCT_INQUIRY: [
            r'\b(còn (không|ko|k)|còn hàng|hết chưa|có không)\b',
            r'\b(size|màu|mẫu|kiểu|loại)\b',
            r'\b(chất liệu|vải|cotton)\b',
        ],
        Intent.SHIPPING_INQUIRY: [
            r'\b(ship|giao hàng|freeship|phí ship)\b',
            r'\b(bao lâu|mấy ngày|khi nào nhận)\b',
            r'\b(giao đến|ship về|gửi về)\b',
        ],
        Intent.ORDER: [
            r'\b(mua|đặt|order|lấy|chốt)\b',
            r'\b(em lấy|mình lấy|cho em|cho mình)\b',
        ],
        Intent.COMPLIMENT: [
            r'\b(đẹp|xinh|tuyệt|hay|thích|yêu)\b',
            r'\b(nice|good|beautiful|cute)\b',
        ],
        Intent.COMPLAINT: [
            r'\b(dở|tệ|chán|xấu|đắt|lừa đảo)\b',
            r'\b(không tốt|không đẹp|không thích)\b',
        ],
        Intent.GENERAL_QUESTION: [
            r'\?$',  # Kết thúc bằng ?
            r'\b(như nào|thế nào|sao|gì|ở đâu|tại sao|làm sao)\b',
        ],
    }
    
    def __init__(self):
        # Compile patterns
        self.compiled_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self.compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE | re.UNICODE) 
                for p in patterns
            ]
    
    def detect(self, text: str) -> Tuple[Intent, float]:
        """
        Detect intent từ text
        
        Args:
            text: Comment text
            
        Returns:
            (Intent, confidence)
        """
        text = text.strip().lower()
        
        if not text:
            return Intent.UNKNOWN, 0.0
        
        # Check từng intent pattern
        scores = {}
        for intent, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(text):
                    score += 1
            if score > 0:
                scores[intent] = score
        
        if not scores:
            return Intent.CHITCHAT, 0.5
        
        # Lấy intent có score cao nhất
        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]
        
        # Normalize confidence
        confidence = min(max_score / 2.0, 1.0)
        
        return best_intent, confidence
    
    def detect_with_details(self, text: str) -> dict:
        """
        Detect intent với đầy đủ thông tin
        
        Returns:
            {
                "intent": str,
                "confidence": float,
                "all_intents": dict
            }
        """
        intent, confidence = self.detect(text)
        
        # Get all intent scores
        all_scores = {}
        for intent_type, patterns in self.compiled_patterns.items():
            score = sum(1 for p in patterns if p.search(text.lower()))
            if score > 0:
                all_scores[intent_type.value] = score
        
        return {
            "intent": intent.value,
            "confidence": confidence,
            "all_intents": all_scores
        }
