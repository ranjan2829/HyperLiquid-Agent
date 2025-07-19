import cohere
import os
from typing import List, Dict, Any

class SimpleReranker:
    def __init__(self, api_key: str = None):
        """Initialize Cohere reranker"""
        self.client = cohere.Client(api_key or os.getenv('COHERE_API_KEY'))
    
    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Rerank results using Cohere's rerank API"""
        if not results:
            return []
        
        try:
            # Prepare better documents for reranking
            documents = []
            for result in results:
                metadata = result.get('metadata', {})
                
                # Create rich context for Cohere
                parts = []
                if metadata.get('title'):
                    parts.append(f"Title: {metadata['title']}")
                if metadata.get('summary'):
                    parts.append(f"Summary: {metadata['summary']}")
                if metadata.get('source_entity_name'):
                    parts.append(f"Source: {metadata['source_entity_name']}")
                if result.get('text'):
                    parts.append(f"Content: {result['text'][:500]}")
                    
                combined_text = "\n".join(parts)
                documents.append(combined_text)
            
            # Call Cohere rerank API
            response = self.client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=min(top_k, len(documents)),
                return_documents=True  # Get document text back
            )
            
            # Reorder results based on Cohere's ranking
            reranked_results = []
            for result in response.results:
                original_result = results[result.index]
                # Add Cohere's relevance score
                original_result['cohere_score'] = result.relevance_score
                reranked_results.append(original_result)
            
            return reranked_results
            
        except Exception as e:
            print(f"Error in Cohere reranking: {e}")
            # Fallback to original results if Cohere fails
            return results[:top_k]