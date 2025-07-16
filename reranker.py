from typing import List, Dict, Any
import re
from datetime import datetime, timedelta

class SimpleReranker:
    def __init__(self):
        self.hyperliquid_keywords = [
            'hyperliquid', 'hype', 'hl', 'vaults', 'perps', 'dex',
            'perpetual', 'trading', 'defi', 'yield', 'liquidity'
        ]
        
        self.risk_keywords = [
            'risk', 'danger', 'concern', 'worry', 'problem', 'issue',
            'warning', 'caution', 'alert', 'threat', 'vulnerable'
        ]
        
        self.positive_keywords = [
            'bullish', 'good', 'great', 'excellent', 'impressive',
            'growth', 'profit', 'gains', 'success', 'strong'
        ]
        
        self.negative_keywords = [
            'bearish', 'bad', 'terrible', 'awful', 'crash',
            'loss', 'dump', 'down', 'weak', 'fail'
        ]
    
    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Rerank results based on relevance and recency"""
        
        if not results:
            return []
        
        # Calculate relevance scores
        scored_results = []
        for result in results:
            score = self._calculate_score(query, result)
            result['relevance_score'] = score
            scored_results.append(result)
        
        # Sort by relevance score (higher is better)
        scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return scored_results[:top_k]
    
    def _calculate_score(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate relevance score for a result"""
        
        text = result['text'].lower()
        query_lower = query.lower()
        title = result['metadata'].get('title', '').lower()
        
        score = 0.0
        
        # Base similarity score (from vector search)
        base_score = 1.0 - result.get('score', 0.5)  # Convert distance to similarity
        score += base_score * 0.4
        
        # Keyword matching
        query_words = query_lower.split()
        text_words = text.split()
        title_words = title.split()
        
        # Exact query word matches
        for word in query_words:
            if word in text:
                score += 0.1
            if word in title:
                score += 0.2  # Title matches are more important
        
        # HyperLiquid-specific keyword boost
        for keyword in self.hyperliquid_keywords:
            if keyword in text:
                score += 0.05
            if keyword in title:
                score += 0.1
        
        # Risk-related queries
        if any(risk_word in query_lower for risk_word in self.risk_keywords):
            for risk_word in self.risk_keywords:
                if risk_word in text:
                    score += 0.15
        
        # Sentiment relevance
        if 'sentiment' in query_lower or 'opinion' in query_lower:
            sentiment_words = self.positive_keywords + self.negative_keywords
            for word in sentiment_words:
                if word in text:
                    score += 0.1
        
        # Recency boost
        published_at = result['metadata'].get('published_at', '')
        if published_at:
            try:
                pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                days_ago = (datetime.now(pub_date.tzinfo) - pub_date).days
                
                # Boost recent content
                if days_ago <= 1:
                    score += 0.3
                elif days_ago <= 7:
                    score += 0.2
                elif days_ago <= 30:
                    score += 0.1
            except:
                pass
        
        # Source credibility boost
        source = result['metadata'].get('source_entity_name', '').lower()
        if any(term in source for term in ['official', 'team', 'founder', 'ceo']):
            score += 0.2
        
        # Channel type boost
        channel_type = result['metadata'].get('channel_type', '').lower()
        if channel_type in ['twitter', 'telegram', 'discord']:
            score += 0.1
        
        return max(0.0, min(score, 2.0))  # Clamp between 0 and 2