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
            # Prepare documents for Cohere API
            documents = []
            for result in results:
                # Combine title and text for better reranking
                text = result.get('text', '')
                title = result.get('metadata', {}).get('title', '')
                combined_text = f"{title} {text}".strip()
                documents.append(combined_text)
            
            # Call Cohere rerank API
            response = self.client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=top_k
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