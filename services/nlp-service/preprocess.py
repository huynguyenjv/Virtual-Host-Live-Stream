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
    - Xử lý emoji (loại bỏ vì output là lời nói)
    - Loại bỏ ký tự đặc biệt
    - Detect emoji spam
    """
    
    # Emoji pattern - mở rộng để bắt được nhiều emoji hơn
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended
        "\U00002600-\U000026FF"  # misc symbols (\u2600-\u26FF)
        "\U00002700-\U000027BF"  # dingbats
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0001F000-\U0001F02F"  # mahjong tiles
        "\U0001F0A0-\U0001F0FF"  # playing cards
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
    
    def count_emojis(self, text: str) -> int:
        """Đếm số lượng emoji trong text"""
        emojis = self.EMOJI_PATTERN.findall(text)
        return sum(len(e) for e in emojis)
    
    def get_emoji_ratio(self, text: str) -> float:
        """
        Tính tỷ lệ emoji trong text
        Dùng để detect emoji spam
        
        Returns:
            0.0 - 1.0 (0 = không có emoji, 1 = toàn emoji)
        """
        if not text:
            return 0.0
        
        # Đếm tổng ký tự và emoji
        total_chars = len(text.replace(' ', ''))
        if total_chars == 0:
            return 0.0
        
        emoji_count = self.count_emojis(text)
        return min(emoji_count / total_chars, 1.0)
    
    def is_emoji_only(self, text: str) -> bool:
        """
        Kiểm tra comment chỉ có emoji (không có text thực)
        VD: "🔥🔥🔥", "❤️❤️❤️👍👍"
        """
        # Xóa emoji và whitespace
        text_without_emoji = self.EMOJI_PATTERN.sub('', text)
        text_without_emoji = text_without_emoji.strip()
        
        # Nếu không còn gì -> chỉ có emoji
        return len(text_without_emoji) == 0
    
    def process(self, text: str) -> dict:
        """
        Process text và trả về kết quả đầy đủ
        
        Returns:
            {
                "original": str,
                "cleaned": str,
                "mentions": list,
                "has_emoji": bool,
                "emoji_count": int,
                "emoji_ratio": float,
                "is_emoji_only": bool
            }
        """
        cleaned = self.clean_text(text)
        mentions = self.extract_mentions(text)
        has_emoji = bool(self.EMOJI_PATTERN.search(text))
        emoji_count = self.count_emojis(text)
        emoji_ratio = self.get_emoji_ratio(text)
        is_emoji_only = self.is_emoji_only(text)
        
        return {
            "original": text,
            "cleaned": cleaned,
            "mentions": mentions,
            "has_emoji": has_emoji,
            "emoji_count": emoji_count,
            "emoji_ratio": emoji_ratio,
            "is_emoji_only": is_emoji_only
        }
