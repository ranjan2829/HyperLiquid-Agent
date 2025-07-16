from agno.agent import Agent
from agno.models.openai import OpenAIChat
from typing import List, Dict, Any
from vector_store import VectorStore
from reranker import SimpleReranker

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
        """Simple sentiment analysis"""
        
        positive_keywords = ['bullish', 'good', 'great', 'excellent', 'impressive', 'growth']
        negative_keywords = ['bearish', 'bad', 'risk', 'concern', 'worried', 'down']
        
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for mention in mentions:
            text_lower = mention['text'].lower()
            
            pos_count = sum(1 for word in positive_keywords if word in text_lower)
            neg_count = sum(1 for word in negative_keywords if word in text_lower)
            
            if pos_count > neg_count:
                sentiment_counts['positive'] += 1
            elif neg_count > pos_count:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
        
        total = len(mentions)
        return {
            'total_mentions': total,
            'positive': sentiment_counts['positive'],
            'negative': sentiment_counts['negative'],
            'neutral': sentiment_counts['neutral'],
            'positive_pct': (sentiment_counts['positive'] / total) * 100 if total > 0 else 0,
            'negative_pct': (sentiment_counts['negative'] / total) * 100 if total > 0 else 0,
            'neutral_pct': (sentiment_counts['neutral'] / total) * 100 if total > 0 else 0
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