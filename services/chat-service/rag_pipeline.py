"""
rag_pipeline.py
RAG (Retrieval-Augmented Generation) Pipeline
Tìm context liên quan từ knowledge base
"""

from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Document:
    """Document trong knowledge base"""
    content: str
    metadata: dict
    score: float = 0.0


class SimpleRAG:
    """
    Simple RAG implementation
    Có thể upgrade lên vector DB (ChromaDB, Pinecone) sau
    """
    
    def __init__(self):
        # In-memory knowledge base (demo)
        # Sau này có thể load từ file hoặc vector DB
        self.documents: List[Document] = []
        self._load_default_knowledge()
    
    def _load_default_knowledge(self):
        """Load default knowledge base"""
        # Demo data - thay bằng data thực
        default_docs = [
            {
                "content": "Shop có freeship cho đơn từ 300k. Giao hàng toàn quốc 2-5 ngày.",
                "metadata": {"category": "shipping", "keywords": ["ship", "giao hàng", "freeship"]}
            },
            {
                "content": "Đổi trả trong 7 ngày nếu sản phẩm lỗi. Hoàn tiền 100%.",
                "metadata": {"category": "policy", "keywords": ["đổi", "trả", "hoàn tiền"]}
            },
            {
                "content": "Thanh toán COD hoặc chuyển khoản. Hỗ trợ mọi ngân hàng.",
                "metadata": {"category": "payment", "keywords": ["thanh toán", "cod", "chuyển khoản"]}
            },
            {
                "content": "Size S: 40-50kg, M: 50-60kg, L: 60-70kg, XL: 70-80kg",
                "metadata": {"category": "size", "keywords": ["size", "cân nặng"]}
            },
            {
                "content": "Hotline hỗ trợ: 0123456789. Làm việc 8h-22h hàng ngày.",
                "metadata": {"category": "contact", "keywords": ["hotline", "liên hệ", "hỗ trợ"]}
            }
        ]
        
        for doc in default_docs:
            self.documents.append(Document(
                content=doc["content"],
                metadata=doc["metadata"]
            ))
    
    def add_document(self, content: str, metadata: dict = None):
        """Add document vào knowledge base"""
        self.documents.append(Document(
            content=content,
            metadata=metadata or {}
        ))
    
    def search(self, query: str, top_k: int = 3) -> List[Document]:
        """
        Simple keyword-based search
        Sau này thay bằng semantic search với embeddings
        """
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            score = 0
            
            # Check keywords in metadata
            keywords = doc.metadata.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 2
            
            # Check content overlap
            content_words = doc.content.lower().split()
            query_words = query_lower.split()
            for word in query_words:
                if word in content_words:
                    score += 1
            
            if score > 0:
                doc.score = score
                results.append(doc)
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def get_context(self, query: str, intent: str = None) -> Optional[str]:
        """
        Get relevant context cho query
        
        Returns:
            Combined context string hoặc None
        """
        # Search documents
        results = self.search(query, top_k=2)
        
        if not results:
            return None
        
        # Combine contexts
        contexts = [doc.content for doc in results]
        return " | ".join(contexts)


class RAGPipeline:
    """
    Full RAG Pipeline
    Query → Retrieve → Augment → Generate
    """
    
    def __init__(self, config=None):
        self.config = config
        self.retriever = SimpleRAG()
    
    def retrieve(self, query: str, intent: str = None) -> Optional[str]:
        """Retrieve relevant context"""
        return self.retriever.get_context(query, intent)
    
    def add_knowledge(self, content: str, metadata: dict = None):
        """Add knowledge to the base"""
        self.retriever.add_document(content, metadata)
    
    def load_knowledge_from_file(self, filepath: str):
        """Load knowledge từ file JSON"""
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    self.add_knowledge(
                        content=item.get("content", ""),
                        metadata=item.get("metadata", {})
                    )
        except Exception as e:
            print(f"[WARN] Could not load knowledge file: {e}")
