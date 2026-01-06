"""
prompt_template.py
Prompt Templates cho LLM với Persona
"""

from typing import Optional


class PromptTemplate:
    """
    Quản lý prompt templates cho Virtual Host
    """
    
    # System prompt với persona
    SYSTEM_PROMPT = """Bạn là {persona_name}, một virtual host thân thiện cho livestream bán hàng trên TikTok.

PERSONA:
- Tên: {persona_name}
- Phong cách: {persona_style}
- Vai trò: Hỗ trợ khách hàng, trả lời câu hỏi về sản phẩm

QUY TẮC:
1. Trả lời ngắn gọn (dưới {max_length} ký tự)
2. Thân thiện, không sử dụng emojis
3. Xưng hô: "em" với khách, "mình" khi nói về bản thân
4. Nếu không biết thông tin sản phẩm, hẹn kiểm tra và phản hồi sau
5. Luôn gọi tên người hỏi nếu có

NGÔN NGỮ: Tiếng Việt tự nhiên, có thể dùng teen code nhẹ."""

    # Intent-based response templates
    INTENT_PROMPTS = {
        "greeting": "Người xem chào. Hãy chào lại thân thiện và hỏi thăm.",
        "price": "Khách hỏi về giá. Nếu không có thông tin cụ thể, hãy nói sẽ kiểm tra và thông báo.",
        "product": "Khách hỏi về sản phẩm. Trả lời nếu có thông tin, hoặc hẹn kiểm tra.",
        "shipping": "Khách hỏi về giao hàng/ship. Cung cấp thông tin chung về shipping.",
        "order": "Khách muốn đặt hàng. Hướng dẫn cách đặt hoặc để lại thông tin.",
        "compliment": "Khách khen. Cảm ơn và tiếp tục tạo không khí vui vẻ.",
        "complaint": "Khách phàn nàn. Xin lỗi và hứa cải thiện.",
        "question": "Khách có câu hỏi. Trả lời hoặc hẹn tìm hiểu thêm.",
        "chitchat": "Khách nói chuyện phiếm. Phản hồi vui vẻ, giữ không khí livestream.",
    }
    
    def __init__(self, config):
        self.config = config
        self.persona_name = config.PERSONA_NAME
        self.persona_style = config.PERSONA_STYLE
        self.max_length = config.MAX_RESPONSE_LENGTH
    
    def get_system_prompt(self) -> str:
        """Get system prompt với persona"""
        return self.SYSTEM_PROMPT.format(
            persona_name=self.persona_name,
            persona_style=self.persona_style,
            max_length=self.max_length
        )
    
    def build_prompt(
        self,
        comment: str,
        username: str,
        intent: str,
        context: Optional[str] = None
    ) -> str:
        """
        Build prompt hoàn chỉnh cho LLM
        
        Args:
            comment: Nội dung comment
            username: Tên người comment
            intent: Intent đã detect
            context: Context bổ sung (từ RAG)
        """
        # Intent hint
        intent_hint = self.INTENT_PROMPTS.get(intent, "Trả lời phù hợp.")
        
        # Build user prompt
        prompt_parts = [
            f"[NGƯỜI XEM: {username}]",
            f"[COMMENT: {comment}]",
            f"[GỢI Ý: {intent_hint}]"
        ]
        
        # Add context if available
        if context:
            prompt_parts.insert(2, f"[THÔNG TIN LIÊN QUAN: {context}]")
        
        prompt_parts.append("\nHãy phản hồi ngắn gọn, tự nhiên:")
        
        return "\n".join(prompt_parts)
    
    def build_messages(
        self,
        comment: str,
        username: str,
        intent: str,
        context: Optional[str] = None
    ) -> list:
        """
        Build messages array cho OpenAI-style API
        
        Returns:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        return [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": self.build_prompt(comment, username, intent, context)}
        ]
