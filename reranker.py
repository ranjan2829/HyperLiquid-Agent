from typing import List, Dict, Any
import re

class SimpleReranker:
    def __init__(self):
        self.hyperliquid_keywords = [
            'hyperliquid', 'hype', 'vault', 'vaults', 'trading',
            'liquidity', 'defi', 'protocol', 'token'
        ]
    
    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Simple reranking based on keyword matching and recency"""
        
        query_lower = query.lower()
        
        # Score each result
        scored_results = []
        for result in results:
            score = self._calculate_score(query_lower, result)
            scored_results.append((score, result))
        
        # Sort by score (descending) and return top_k
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [result for _, result in scored_results[:top_k]]
    
    def _calculate_score(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate relevance score for a result"""
        
        score = result.get('score', 0.0)  # Base similarity score
        
        # Get text content
        text = result.get('text', '').lower()
        metadata = result.get('metadata', {})
        
        # Boost for keyword matches
        for keyword in self.hyperliquid_keywords:
            if keyword in text:
                score += 0.1
        
        # Boost for query terms
        query_terms = query.split()
        for term in query_terms:
            if term in text:
                score += 0.05
        
        # Boost for title matches
        title = metadata.get('title', '').lower()
        if any(term in title for term in query_terms):
            score += 0.2
        
        # Boost for importance
        importance = metadata.get('importance_score', 0.5)
        score += importance * 0.1
        
        return score