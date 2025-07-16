from turbopuffer import Turbopuffer
from typing import List, Dict, Any
import openai
from config import Config
import json

config = Config()

class VectorStore:
    def __init__(self):
        self.client = Turbopuffer(
            api_key=config.TURBOPUFFER_API_KEY,
            region="aws-us-east-1"
        )
        self.namespace = "hyperliquid-mentions"
        self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    
    def store_chunks(self, chunks: List[Dict[str, Any]]):
        """Store chunks in Turbopuffer"""
        
        if not chunks:
            print("No chunks to store")
            return
        
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self._generate_embeddings(texts)
        upsert_rows = []
        
        for chunk, embedding in zip(chunks, embeddings):
            row = {
                'id': chunk['id'],
                'vector': embedding,
                'text': chunk['text'],
                'mention_id': chunk['mention_id'],
                'type': chunk['type']
            }
            
            # Add metadata fields with proper type conversion
            for key, value in chunk['metadata'].items():
                # Convert complex types to strings for Turbopuffer compatibility
                if isinstance(value, (list, dict)):
                    row[key] = json.dumps(value)
                elif isinstance(value, bool):
                    row[key] = value
                elif isinstance(value, (int, float)):
                    row[key] = value
                elif value is None:
                    row[key] = None
                else:
                    # Convert everything else to string
                    row[key] = str(value)
            
            upsert_rows.append(row)
        
        # Store in Turbopuffer using the write method with upsert_rows
        try:
            namespace = self.client.namespace(self.namespace)
            
            # Use the write method with upsert_rows
            namespace.write(
                upsert_rows=upsert_rows,
                distance_metric='cosine_distance'
            )
            
            print(f"Stored {len(upsert_rows)} vectors in Turbopuffer")
            
        except Exception as e:
            print(f"Error storing vectors: {e}")
            raise
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        
        # Generate embedding for query
        query_embedding = self._generate_embeddings([query])[0]
        
        # Search in Turbopuffer
        try:
            namespace = self.client.namespace(self.namespace)
            
            # Use the correct Turbopuffer API with rank_by parameter
            results = namespace.query(
                rank_by=("vector", "ANN", query_embedding),
                top_k=top_k,
                include_attributes=True  # Include all metadata
            )
            
            # Convert results to the expected format
            formatted_results = []
            for row in results.rows:
                # Access row data properly - try different methods
                try:
                    # Method 1: Direct attribute access
                    text = getattr(row, 'text', '')
                    if not text:
                        # Method 2: Check if it's a dict-like object
                        text = row.get('text', '') if hasattr(row, 'get') else ''
                    
                    # Get hyperliquid_tokens safely
                    hyperliquid_tokens = getattr(row, 'hyperliquid_tokens', '[]')
                    if isinstance(hyperliquid_tokens, str):
                        try:
                            hyperliquid_tokens = json.loads(hyperliquid_tokens)
                        except:
                            hyperliquid_tokens = []
                    
                    formatted_results.append({
                        'id': row.id,
                        'text': text,
                        'score': getattr(row, '$dist', 0.0),
                        'metadata': {
                            'title': getattr(row, 'title', ''),
                            'url': getattr(row, 'url', ''),
                            'published_at': getattr(row, 'published_at', ''),
                            'channel_name': getattr(row, 'channel_name', ''),
                            'channel_type': getattr(row, 'channel_type', ''),
                            'source_entity_name': getattr(row, 'source_entity_name', ''),
                            'hyperliquid_tokens': hyperliquid_tokens
                        }
                    })
                except Exception as e:
                    print(f"Error processing row: {e}")
                    print(f"Row type: {type(row)}")
                    print(f"Row dir: {dir(row)}")
                    continue
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching vectors: {e}")
            raise
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI"""
        
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        
        return [data.embedding for data in response.data]