"""
response_generator.py
LLM Response Generator
Hỗ trợ: OpenAI, Ollama, Gemini, Groq, HuggingFace

Lưu ý: Output được strip emoji vì đây là lời nói (TTS)
"""

import re
import asyncio
from typing import Optional
from abc import ABC, abstractmethod


# Emoji pattern - loại bỏ emoji khỏi response vì đây là lời nói
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
    "\U00002600-\U000026FF"  # misc symbols
    "]+",
    flags=re.UNICODE
)


def strip_emoji(text: str) -> str:
    """Loại bỏ emoji khỏi text vì đây là lời nói (TTS không đọc được emoji)"""
    # Remove emojis
    text = EMOJI_PATTERN.sub('', text)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class BaseLLM(ABC):
    """Base class cho LLM providers"""
    
    @abstractmethod
    async def generate(self, messages: list, max_tokens: int = 150) -> str:
        pass


class OpenAILLM(BaseLLM):
    """OpenAI GPT"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.client = None
    
    async def _init_client(self):
        if self.client is None:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
    
    async def generate(self, messages: list, max_tokens: int = 150) -> str:
        await self._init_client()
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()


class OllamaLLM(BaseLLM):
    """Ollama Local LLM"""
    
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    async def generate(self, messages: list, max_tokens: int = 150) -> str:
        import aiohttp
        
        # Convert messages to Ollama format
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\nAssistant:"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                }
            ) as response:
                data = await response.json()
                return data.get("response", "").strip()


class GeminiLLM(BaseLLM):
    """Google Gemini"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
    
    async def generate(self, messages: list, max_tokens: int = 150) -> str:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Please install google-generativeai: pip install google-generativeai")
        
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        
        # Combine messages
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config={"max_output_tokens": max_tokens}
        )
        
        return response.text.strip()


class GroqLLM(BaseLLM):
    """
    Groq - Free, fast inference for Llama, Mixtral, Gemma
    Get free API key at: https://console.groq.com/keys
    """
    
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
    
    async def generate(self, messages: list, max_tokens: int = 150) -> str:
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise Exception(f"Groq API error: {error}")
                
                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()


class HuggingFaceLLM(BaseLLM):
    """
    HuggingFace Inference API - Free tier available
    Get free API key at: https://huggingface.co/settings/tokens
    """
    
    def __init__(self, api_key: str, model: str = "microsoft/DialoGPT-medium"):
        self.api_key = api_key
        self.model = model
    
    async def generate(self, messages: list, max_tokens: int = 150) -> str:
        import aiohttp
        
        # Combine messages into prompt
        prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                prompt += f"{msg['content']}\n\n"
            elif msg["role"] == "user":
                prompt += f"User: {msg['content']}\nAssistant:"
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api-inference.huggingface.co/models/{self.model}",
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {"max_new_tokens": max_tokens}
                }
            ) as response:
                data = await response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("generated_text", "").strip()
                
                return str(data)


class MockLLM(BaseLLM):
    """Mock LLM cho testing"""
    
    MOCK_RESPONSES = {
        "greeting": "Chào bạn nha! Cảm ơn bạn đã ghé livestream của mình!",
        "price": "Dạ sản phẩm này giá 299k thôi ạ! Hôm nay có giảm 10% nữa nha!",
        "product": "Dạ sản phẩm còn đủ size và màu nha bạn!",
        "shipping": "Shop có freeship từ 300k nha! Giao hàng 2-5 ngày ạ.",
        "order": "Bạn để lại SĐT hoặc inbox shop nha! Mình sẽ hỗ trợ đặt hàng liền!",
        "default": "Dạ mình ghi nhận nha! Cảm ơn bạn đã quan tâm!"
    }
    
    async def generate(self, messages: list, max_tokens: int = 150) -> str:
        # Extract intent from prompt
        user_msg = messages[-1]["content"] if messages else ""
        
        for intent, response in self.MOCK_RESPONSES.items():
            if intent in user_msg.lower():
                return response
        
        return self.MOCK_RESPONSES["default"]


class ResponseGenerator:
    """
    Response Generator
    Orchestrates LLM calls với RAG context
    """
    
    def __init__(self, config):
        self.config = config
        self.llm = self._create_llm()
    
    def _create_llm(self) -> BaseLLM:
        """Create LLM based on config"""
        provider = self.config.LLM_PROVIDER.lower()
        
        if provider == "openai":
            if not self.config.LLM_API_KEY:
                print("[WARN] No OpenAI API key, using MockLLM")
                return MockLLM()
            return OpenAILLM(
                api_key=self.config.LLM_API_KEY,
                model=self.config.LLM_MODEL
            )
        
        elif provider == "ollama":
            return OllamaLLM(
                model=self.config.LLM_MODEL,
                base_url=self.config.LLM_BASE_URL or "http://localhost:11434"
            )
        
        elif provider == "gemini":
            if not self.config.LLM_API_KEY:
                print("[WARN] No Gemini API key, using MockLLM")
                return MockLLM()
            return GeminiLLM(
                api_key=self.config.LLM_API_KEY,
                model=self.config.LLM_MODEL
            )
        
        elif provider == "groq":
            if not self.config.LLM_API_KEY:
                print("[WARN] No Groq API key, using MockLLM")
                print("[INFO] Get free key at: https://console.groq.com/keys")
                return MockLLM()
            return GroqLLM(
                api_key=self.config.LLM_API_KEY,
                model=self.config.LLM_MODEL
            )
        
        elif provider == "huggingface":
            if not self.config.LLM_API_KEY:
                print("[WARN] No HuggingFace API key, using MockLLM")
                return MockLLM()
            return HuggingFaceLLM(
                api_key=self.config.LLM_API_KEY,
                model=self.config.LLM_MODEL
            )
        
        else:
            print(f"[WARN] Unknown provider: {provider}, using MockLLM")
            return MockLLM()
    
    async def generate(
        self,
        messages: list,
        timeout: float = 10.0
    ) -> Optional[str]:
        """
        Generate response với timeout
        
        Args:
            messages: OpenAI-style messages
            timeout: Max time to wait
            
        Returns:
            Response text hoặc None nếu timeout/error
        """
        try:
            response = await asyncio.wait_for(
                self.llm.generate(messages, self.config.MAX_RESPONSE_LENGTH),
                timeout=timeout
            )
            # Strip emoji vì đây là lời nói (TTS không đọc được emoji)
            if response:
                response = strip_emoji(response)
            return response
        
        except asyncio.TimeoutError:
            print(f"[WARN] LLM timeout after {timeout}s")
            return None
        
        except Exception as e:
            print(f"[ERROR] LLM error: {e}")
            return None
