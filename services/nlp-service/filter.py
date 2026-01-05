"""
filter.py
Comment Filter - Lọc spam, toxic, comment không hợp lệ
"""

import re
from typing import Tuple
from dataclasses import dataclass


@dataclass
class FilterResult:
    """Kết quả lọc comment"""
    is_valid: bool
    should_respond: bool
    reason: str
    priority: int  # 1-5, 5 = cao nhất
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "should_respond": self.should_respond,
            "reason": self.reason,
            "priority": self.priority
        }


class CommentFilter:
    """
    Lọc và phân loại comment
    - Loại spam
    - Loại toxic/tục tĩu
    - Xác định priority
    """
    
    # Spam patterns
    SPAM_PATTERNS = [
        r'(.)\1{4,}',  # Lặp ký tự > 4 lần (aaaaaaa)
        r'(..)\1{3,}',  # Lặp chuỗi > 3 lần (hahahahaha)
        r'^[!@#$%^&*()]+$',  # Chỉ có ký tự đặc biệt
        r'^\d+$',  # Chỉ có số
    ]
    
    # Toxic keywords (có thể mở rộng)
    TOXIC_KEYWORDS = [
        'địt', 'đụ', 'lồn', 'buồi', 'cặc', 'đéo', 'vãi',
        'ngu', 'óc chó', 'thằng khốn', 'con đĩ',
        # Thêm từ khác nếu cần
    ]
    
    # Greeting keywords (priority cao)
    GREETING_KEYWORDS = [
        'chào', 'hi', 'hello', 'xin chào', 'alo',
        'chào shop', 'chào chị', 'chào anh', 'chào bạn'
    ]
    
    # Product/Question keywords (priority cao)
    QUESTION_KEYWORDS = [
        'bao nhiêu', 'giá', 'còn không', 'còn hàng', 'size',
        'ship', 'giao hàng', 'freeship', 'mua', 'đặt',
        'như nào', 'thế nào', 'sao', 'gì', 'ở đâu'
    ]
    
    def __init__(self, config=None):
        self.config = config
        self.min_length = config.MIN_COMMENT_LENGTH if config else 2
        self.max_length = config.MAX_COMMENT_LENGTH if config else 500
        
        # Compile patterns
        self.spam_patterns = [re.compile(p, re.IGNORECASE) for p in self.SPAM_PATTERNS]
    
    def is_spam(self, text: str) -> bool:
        """Kiểm tra spam"""
        for pattern in self.spam_patterns:
            if pattern.search(text):
                return True
        return False
    
    def is_toxic(self, text: str) -> bool:
        """Kiểm tra toxic/tục tĩu"""
        text_lower = text.lower()
        for keyword in self.TOXIC_KEYWORDS:
            if keyword in text_lower:
                return True
        return False
    
    def get_priority(self, text: str) -> int:
        """
        Xác định priority của comment
        1 = thấp, 5 = cao
        """
        text_lower = text.lower()
        
        # Greeting = priority 4
        for keyword in self.GREETING_KEYWORDS:
            if keyword in text_lower:
                return 4
        
        # Question/Product = priority 5
        for keyword in self.QUESTION_KEYWORDS:
            if keyword in text_lower:
                return 5
        
        # Có dấu ? = priority 4
        if '?' in text:
            return 4
        
        # Mặc định
        return 2
    
    def filter(self, text: str) -> FilterResult:
        """
        Lọc và đánh giá comment
        
        Args:
            text: Comment text đã được clean
            
        Returns:
            FilterResult
        """
        # Kiểm tra độ dài
        if len(text) < self.min_length:
            return FilterResult(
                is_valid=False,
                should_respond=False,
                reason="too_short",
                priority=0
            )
        
        if len(text) > self.max_length:
            return FilterResult(
                is_valid=False,
                should_respond=False,
                reason="too_long",
                priority=0
            )
        
        # Kiểm tra spam
        if self.is_spam(text):
            return FilterResult(
                is_valid=False,
                should_respond=False,
                reason="spam",
                priority=0
            )
        
        # Kiểm tra toxic
        if self.is_toxic(text):
            return FilterResult(
                is_valid=True,
                should_respond=False,
                reason="toxic",
                priority=0
            )
        
        # Comment hợp lệ
        priority = self.get_priority(text)
        
        return FilterResult(
            is_valid=True,
            should_respond=True,
            reason="ok",
            priority=priority
        )
