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
            # Debug: Print the first row to see what's causing issues
            if upsert_rows:
                print("Sample row structure:")
                for key, value in upsert_rows[0].items():
                    print(f"  {key}: {type(value).__name__} = {value}")
            raise
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        
        # Generate embedding for query
        query_embedding = self._generate_embeddings([query])[0]
        
        # Search in Turbopuffer
        try:
            namespace = self.client.namespace(self.namespace)
            
            # Use the query method
            results = namespace.query(
                vector=query_embedding,
                top_k=top_k,
                include_attributes=True  # Include all metadata
            )
            
            # Convert results to the expected format
            formatted_results = []
            for row in results.rows:
                # Parse JSON strings back to objects where needed
                hyperliquid_tokens = row.attributes.get('hyperliquid_tokens', '[]')
                if isinstance(hyperliquid_tokens, str):
                    try:
                        hyperliquid_tokens = json.loads(hyperliquid_tokens)
                    except:
                        hyperliquid_tokens = []
                
                formatted_results.append({
                    'id': row.id,
                    'text': row.attributes.get('text', ''),
                    'score': row.dist,
                    'metadata': {
                        'title': row.attributes.get('title', ''),
                        'url': row.attributes.get('url', ''),
                        'published_at': row.attributes.get('published_at', ''),
                        'channel_name': row.attributes.get('channel_name', ''),
                        'channel_type': row.attributes.get('channel_type', ''),
                        'source_entity_name': row.attributes.get('source_entity_name', ''),
                        'hyperliquid_tokens': hyperliquid_tokens
                    }
                })
            
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