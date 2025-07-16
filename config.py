import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TURBOPUFFER_API_KEY = os.getenv("TURBOPUFFER_API_KEY")
    EMBEDDING_MODEL = "text-embedding-3-small"
    VECTOR_NAMESPACE = "hyperliquid-mentions"
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    TOP_K_SEARCH = 20