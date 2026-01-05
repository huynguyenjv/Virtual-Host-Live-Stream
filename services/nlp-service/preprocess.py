"""
preprocess.py
Text Preprocessing cho Vietnamese Comments
"""

import re
import unicodedata
from typing import Optional


class TextPreprocessor:
    """
    Tiền xử lý text tiếng Việt
    - Chuẩn hóa Unicode
    - Xử lý emoji
    - Loại bỏ ký tự đặc biệt
    """
    
    # Emoji pattern
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    # URL pattern
    URL_PATTERN = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    # Mention pattern (@username)
    MENTION_PATTERN = re.compile(r'@[\w\.]+')
    
    def __init__(self, remove_emoji: bool = False, remove_urls: bool = True):
        self.remove_emoji = remove_emoji
        self.remove_urls = remove_urls
    
    def normalize_unicode(self, text: str) -> str:
        """Chuẩn hóa Unicode tiếng Việt"""
        # NFC normalization cho tiếng Việt
        text = unicodedata.normalize('NFC', text)
        return text
    
    def clean_text(self, text: str) -> str:
        """Làm sạch text"""
        if not text:
            return ""
        
        # Normalize unicode
        text = self.normalize_unicode(text)
        
        # Remove URLs
        if self.remove_urls:
            text = self.URL_PATTERN.sub('', text)
        
        # Remove emoji (optional)
        if self.remove_emoji:
            text = self.EMOJI_PATTERN.sub('', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def extract_mentions(self, text: str) -> list:
        """Trích xuất mentions (@username)"""
        return self.MENTION_PATTERN.findall(text)
    
    def process(self, text: str) -> dict:
        """
        Process text và trả về kết quả đầy đủ
        
        Returns:
            {
                "original": str,
                "cleaned": str,
                "mentions": list,
                "has_emoji": bool
            }
        """
        cleaned = self.clean_text(text)
        mentions = self.extract_mentions(text)
        has_emoji = bool(self.EMOJI_PATTERN.search(text))
        
        return {
            "original": text,
            "cleaned": cleaned,
            "mentions": mentions,
            "has_emoji": has_emoji
        }
