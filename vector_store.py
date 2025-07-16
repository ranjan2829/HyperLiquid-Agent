from turbopuffer import Turbopuffer
from typing import List, Dict, Any
import openai
from config import Config
import json

class VectorStore:
    def __init__(self):
        config = Config()
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
        
        print(f"Generating embeddings for {len(chunks)} chunks...")
        
        # Generate embeddings for all texts
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self._generate_embeddings(texts)
        
        # Prepare upsert data for Turbopuffer
        upsert_rows = []
        for chunk, embedding in zip(chunks, embeddings):
            row = {
                'id': chunk['id'],
                'vector': embedding,
                'text': chunk['text'][:1000],  # Limit text length
                'title': chunk['metadata']['title'],
                'summary': chunk['metadata']['summary'],
                'url': chunk['metadata']['url'],
                'published_at': chunk['metadata']['published_at'],
                'channel_name': chunk['metadata']['channel_name'],
                'channel_type': chunk['metadata']['channel_type'],
                'source_entity_name': chunk['metadata']['source_entity_name'],
                'hyperliquid_tokens': json.dumps(chunk['metadata']['hyperliquid_tokens'])  # Convert to JSON string
            }
            upsert_rows.append(row)
        
        # Store in Turbopuffer using the correct API
        try:
            namespace = self.client.namespace(self.namespace)
            
            # Use the write method with upsert_rows
            namespace.write(
                upsert_rows=upsert_rows,
                distance_metric='cosine_distance'
            )
            
            print(f"✅ Successfully stored {len(upsert_rows)} chunks in Turbopuffer")
            
        except Exception as e:
            print(f"❌ Error storing chunks: {e}")
            raise
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = self._generate_embeddings([query])[0]
            
            # Search in Turbopuffer using the correct API
            namespace = self.client.namespace(self.namespace)
            
            # Use the correct Turbopuffer API with rank_by parameter
            results = namespace.query(
                rank_by=("vector", "ANN", query_embedding),
                top_k=top_k,
                include_attributes=True  # Include all metadata
            )
            
            # Format results for the agent
            formatted_results = []
            for row in results.rows:
                try:
                    # Get hyperliquid_tokens safely
                    hyperliquid_tokens = getattr(row, 'hyperliquid_tokens', '[]')
                    if isinstance(hyperliquid_tokens, str):
                        try:
                            hyperliquid_tokens = json.loads(hyperliquid_tokens)
                        except:
                            hyperliquid_tokens = []
                    
                    formatted_results.append({
                        'id': row.id,
                        'text': getattr(row, 'text', ''),
                        'score': getattr(row, '$dist', 0.0),
                        'metadata': {
                            'title': getattr(row, 'title', ''),
                            'summary': getattr(row, 'summary', ''),
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
                    continue
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI's text-embedding-3-small"""
        embeddings = []
        batch_size = 100  # Process in batches to avoid rate limits
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                print(f"✅ Generated embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            except Exception as e:
                print(f"❌ Error generating embeddings for batch {i//batch_size + 1}: {e}")
                # Add zero embeddings as fallback
                embeddings.extend([[0.0] * 1536 for _ in batch])
        
        return embeddings