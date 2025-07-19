from turbopuffer import Turbopuffer
from typing import List, Dict, Any
import openai
from config import Config
import json
from data_processor import ProcessedMention  # Add this import

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
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self._generate_embeddings(texts)
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
            # Simple single query approach for now
            query_embedding = self._generate_embeddings([query])[0]
            
            # Search in Turbopuffer using the correct API
            namespace = self.client.namespace(self.namespace)
            
            # Use the correct Turbopuffer API with rank_by parameter
            results = namespace.query(
                rank_by=("vector", "ANN", query_embedding),
                top_k=top_k,
                include_attributes=True  # Include all metadata
            )
            
            # Convert Row objects to dictionaries
            converted_results = []
            for row in results.rows:
                result_dict = {
                    'id': getattr(row, 'id', None),
                    'text': getattr(row, 'text', ''),
                    'metadata': {
                        'title': getattr(row, 'title', None),
                        'summary': getattr(row, 'summary', None),
                        'url': getattr(row, 'url', None),
                        'published_at': getattr(row, 'published_at', None),
                        'channel_name': getattr(row, 'channel_name', None),
                        'channel_type': getattr(row, 'channel_type', None),
                        'source_entity_name': getattr(row, 'source_entity_name', None),
                        'hyperliquid_tokens': getattr(row, 'hyperliquid_tokens', None)
                    }
                }
                converted_results.append(result_dict)
            
            return converted_results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def search_with_filters(self, query: str, filters: Dict = None, top_k: int = 10):
        """Search with optional metadata filters"""
        base_filters = []
        
        if filters:
            if 'date_range' in filters:
                base_filters.append(('published_at', 'gte', filters['date_range']['start']))
                base_filters.append(('published_at', 'lte', filters['date_range']['end']))
                
            if 'sources' in filters:
                base_filters.append(('source_entity_name', 'in', filters['sources']))
                
            if 'tokens' in filters:
                base_filters.append(('hyperliquid_tokens', 'contains', filters['tokens']))
        
        try:
            query_embedding = self._generate_embeddings([query])[0]
            
            namespace = self.client.namespace(self.namespace)
            
            results = namespace.query(
                rank_by=("vector", "ANN", query_embedding),
                top_k=top_k,
                filters=base_filters,
                include_attributes=True
            )
            
            # Convert Row objects to dictionaries (same as in search method)
            converted_results = []
            for row in results.rows:
                result_dict = {
                    'id': getattr(row, 'id', None),
                    'text': getattr(row, 'text', ''),
                    'metadata': {
                        'title': getattr(row, 'title', None),
                        'summary': getattr(row, 'summary', None),
                        'url': getattr(row, 'url', None),
                        'published_at': getattr(row, 'published_at', None),
                        'channel_name': getattr(row, 'channel_name', None),
                        'channel_type': getattr(row, 'channel_type', None),
                        'source_entity_name': getattr(row, 'source_entity_name', None),
                        'hyperliquid_tokens': getattr(row, 'hyperliquid_tokens', None)
                    }
                }
                converted_results.append(result_dict)
            
            return converted_results
        
        except Exception as e:
            print(f"❌ Filtered search error: {e}")
            return []
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI's text-embedding-3-large"""
        embeddings = []
        batch_size = 100  # Process in batches to avoid rate limits
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-large",  # Upgrade from small to large
                    input=batch,
                    dimensions=1536  # Specify dimensions for consistency
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                print(f"✅ Generated embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            except Exception as e:
                print(f"❌ Error generating embeddings for batch {i//batch_size + 1}: {e}")
                # Add zero embeddings as fallback
                embeddings.extend([[0.0] * 1536 for _ in batch])

        return embeddings

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on ID"""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            result_id = result.get('id')
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
        
        return unique_results

    # Enhanced chunk creation
    def create_enhanced_chunks(self, mentions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []  # Add this line to collect chunks
        for mention in mentions:
            # Add more context to chunks
            text_parts = []
            
            # Add source context
            if mention.get('source_entity_name'):
                text_parts.append(f"Source: {mention['source_entity_name']}")
                
            # Add temporal context
            if mention.get('published_at'):
                date_str = mention['published_at'].strftime("%Y-%m-%d") if hasattr(mention['published_at'], 'strftime') else str(mention['published_at'])
                text_parts.append(f"Published: {date_str}")
            
            # Add HyperLiquid token context
            if mention.get('hyperliquid_tokens'):
                tokens_str = ", ".join(mention['hyperliquid_tokens'])
                text_parts.append(f"HyperLiquid Tokens: {tokens_str}")
                
            # Main content
            if mention.get('title'):
                text_parts.append(f"Title: {mention['title']}")
            if mention.get('summary'):
                text_parts.append(f"Summary: {mention['summary']}")
            if mention.get('content'):
                text_parts.append(f"Content: {mention['content'][:1000]}")  # Limit content
                
            text = "\n".join(text_parts)
            
            # Create chunk dictionary
            chunk = {
                'id': mention.get('id', f"chunk_{len(chunks)}"),
                'text': text,
                'metadata': {
                    'title': mention.get('title'),
                    'summary': mention.get('summary'),
                    'url': mention.get('url'),
                    'published_at': mention.get('published_at'),
                    'channel_name': mention.get('channel_name'),
                    'channel_type': mention.get('channel_type'),
                    'source_entity_name': mention.get('source_entity_name'),
                    'hyperliquid_tokens': mention.get('hyperliquid_tokens')
                }
            }
            chunks.append(chunk)  # Add this line to append the chunk to the list
        
        return chunks
    
    def search_with_temporal_boost(self, query: str, top_k: int = 10, recency_weight: float = 0.3):
        """Search with recency boosting"""
        try:
            results = self.search(query, top_k=top_k * 2)
            
            # Apply temporal scoring
            import datetime
            now = datetime.datetime.now()
            
            for result in results:
                metadata = result.get('metadata', {})
                published_at = metadata.get('published_at')
                
                if published_at:
                    # Parse date and calculate recency score
                    try:
                        if isinstance(published_at, str):
                            pub_date = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        else:
                            pub_date = published_at
                        
                        days_ago = (now - pub_date.replace(tzinfo=None)).days
                        recency_score = max(0, 1 - (days_ago / 365))  # Decay over a year
                        
                        # Combine with existing Cohere score
                        original_score = result.get('cohere_score', 0)
                        result['combined_score'] = (1 - recency_weight) * original_score + recency_weight * recency_score
                        result['recency_score'] = recency_score
                        result['days_ago'] = days_ago
                        
                    except Exception as e:
                        result['combined_score'] = result.get('cohere_score', 0)
            
            # Re-sort by combined score
            results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
            return results[:top_k]
            
        except Exception as e:
            return self.search(query, top_k)  # Fallback