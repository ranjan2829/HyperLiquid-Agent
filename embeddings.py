import openai
from typing import List
from config import Config

class EmbeddingService:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        self.model = Config.EMBEDDING_MODEL
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        response = openai.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = openai.embeddings.create(
                model=self.model,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
        
        return embeddings