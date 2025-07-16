from agno.agent import Agent
from agno.models.openai import OpenAIChat
from typing import List, Dict, Any
from vector_store import VectorStore
from reranker import SimpleReranker
import re

class HyperLiquidAgent(Agent):
    def __init__(self):
        super().__init__(
            model=OpenAIChat(id="gpt-4.1"),
            tools=[self.search_mentions, self.analyze_sentiment],
            show_tool_calls=True,
            markdown=True
        )
        self.vector_store = VectorStore()
        self.reranker = SimpleReranker()
    
    def search_mentions(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for HyperLiquid mentions"""
        
        # Get initial results from vector store
        results = self.vector_store.search(query, top_k=top_k * 2)
        
        # Re-rank results
        reranked_results = self.reranker.rerank(query, results, top_k=top_k)
        
        return reranked_results
    
    def analyze_sentiment(self, mentions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced sentiment analysis with better accuracy"""
        
        # Expanded keyword dictionaries with weighted scoring
        positive_keywords = {
            # Strong positive (weight 3)
            'bullish': 3, 'excellent': 3, 'amazing': 3, 'outstanding': 3, 'breakthrough': 3,
            'revolutionary': 3, 'innovative': 3, 'superior': 3, 'impressive': 3, 'fantastic': 3,
            # Medium positive (weight 2)
            'good': 2, 'great': 2, 'strong': 2, 'solid': 2, 'promising': 2, 'growth': 2,
            'rising': 2, 'surge': 2, 'boost': 2, 'momentum': 2, 'optimistic': 2, 'confidence': 2,
            # Light positive (weight 1)
            'decent': 1, 'okay': 1, 'stable': 1, 'steady': 1, 'recovery': 1, 'potential': 1,
            'opportunity': 1, 'upward': 1, 'improving': 1, 'positive': 1, 'gain': 1, 'profit': 1
        }
        
        negative_keywords = {
            # Strong negative (weight 3)
            'bearish': 3, 'terrible': 3, 'awful': 3, 'disaster': 3, 'crash': 3, 'collapse': 3,
            'plummet': 3, 'devastating': 3, 'catastrophic': 3, 'panic': 3, 'dump': 3,
            # Medium negative (weight 2)
            'bad': 2, 'poor': 2, 'weak': 2, 'decline': 2, 'drop': 2, 'fall': 2, 'risk': 2,
            'concern': 2, 'worried': 2, 'doubt': 2, 'volatile': 2, 'uncertainty': 2,
            # Light negative (weight 1)
            'cautious': 1, 'hesitant': 1, 'down': 1, 'lower': 1, 'dip': 1, 'correction': 1,
            'pullback': 1, 'struggle': 1, 'challenge': 1, 'pressure': 1, 'negative': 1
        }
        
        # Context modifiers
        negation_words = ['not', 'no', 'never', 'none', 'neither', 'nothing', 'nowhere', 'nobody']
        intensifiers = ['very', 'extremely', 'highly', 'significantly', 'massively', 'tremendously']
        
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        detailed_scores = []
        
        for mention in mentions:
            text = mention['text'].lower()
            words = re.findall(r'\b\w+\b', text)
            
            pos_score = 0
            neg_score = 0
            
            for i, word in enumerate(words):
                # Check for negation context (within 2 words)
                is_negated = any(neg in words[max(0, i-2):i] for neg in negation_words)
                
                # Check for intensifiers
                intensifier_multiplier = 1
                if any(intensifier in words[max(0, i-2):i] for intensifier in intensifiers):
                    intensifier_multiplier = 1.5
                
                # Calculate sentiment scores
                if word in positive_keywords:
                    score = positive_keywords[word] * intensifier_multiplier
                    if is_negated:
                        neg_score += score  # Negated positive becomes negative
                    else:
                        pos_score += score
                
                elif word in negative_keywords:
                    score = negative_keywords[word] * intensifier_multiplier
                    if is_negated:
                        pos_score += score  # Negated negative becomes positive
                    else:
                        neg_score += score
            
            # Determine sentiment based on weighted scores
            score_diff = pos_score - neg_score
            
            if score_diff > 1:  # Threshold for positive
                sentiment_counts['positive'] += 1
                sentiment = 'positive'
            elif score_diff < -1:  # Threshold for negative
                sentiment_counts['negative'] += 1
                sentiment = 'negative'
            else:
                sentiment_counts['neutral'] += 1
                sentiment = 'neutral'
            
            detailed_scores.append({
                'text': mention['text'][:100] + '...' if len(mention['text']) > 100 else mention['text'],
                'sentiment': sentiment,
                'positive_score': pos_score,
                'negative_score': neg_score,
                'final_score': score_diff
            })
        
        total = len(mentions)
        
        # Calculate confidence score based on score distribution
        total_abs_scores = sum(abs(score['final_score']) for score in detailed_scores)
        confidence = min(100, (total_abs_scores / total * 10) if total > 0 else 0)
        
        return {
            'total_mentions': total,
            'positive': sentiment_counts['positive'],
            'negative': sentiment_counts['negative'],
            'neutral': sentiment_counts['neutral'],
            'positive_pct': (sentiment_counts['positive'] / total) * 100 if total > 0 else 0,
            'negative_pct': (sentiment_counts['negative'] / total) * 100 if total > 0 else 0,
            'neutral_pct': (sentiment_counts['neutral'] / total) * 100 if total > 0 else 0,
            'confidence_score': round(confidence, 1),
            'detailed_analysis': detailed_scores[:10],  # Top 10 for debugging
            'methodology': 'Enhanced weighted keyword analysis with context awareness'
        }
    
    def answer_query(self, user_query: str) -> Dict[str, Any]:
        """Answer user queries about HyperLiquid mentions"""
        
        # Search for relevant mentions
        mentions = self.search_mentions(user_query, top_k=15)
        
        # Analyze sentiment
        sentiment = self.analyze_sentiment(mentions)
        
        # Generate response
        response = {
            'query': user_query,
            'reasoning': f"Found {len(mentions)} relevant mentions about HyperLiquid",
            'sentiment_analysis': sentiment,
            'top_mentions': mentions[:5],  # Show top 5
            'sources': [
                {
                    'title': m['metadata']['title'],
                    'source': m['metadata']['source_entity_name'],
                    'url': m['metadata']['url'],
                    'published_at': m['metadata']['published_at']
                }
                for m in mentions[:5]
            ]
        }
        
        return response