from agno.agent import Agent
from agno.models.openai import OpenAIChat
from typing import List, Dict, Any
from vector_store import VectorStore
from reranker import SimpleReranker
import json

class HyperLiquidAgent(Agent):
    def __init__(self):
        self.vector_store = VectorStore()
        self.reranker = SimpleReranker()
        
        super().__init__(
            model=OpenAIChat(id="gpt-4o"),
            tools=[self.search_mentions, self.analyze_sentiment],
            instructions=[
                "You are a HyperLiquid market analysis expert.",
                "Always use search_mentions first to get data, then analyze_sentiment.",
                "Be direct and fast. No lengthy explanations.",
                "Show the top results with sentiment analysis."
            ],
            show_tool_calls=False,  # Remove tool call boxes
            markdown=False,  # Remove markdown formatting
            reasoning=False,  # No reasoning boxes
        )
    
    def search_mentions(self, query: str, top_k: int = 15) -> str:
        """Search Turbopuffer fast"""
        try:
            results = self.vector_store.search(query, top_k=top_k * 2)
            
            if not results:
                return "No mentions found"
            
            reranked_results = self.reranker.rerank(query, results, top_k=top_k)
            
            # Simple format
            output = f"Found {len(reranked_results)} mentions:\n\n"
            for i, result in enumerate(reranked_results, 1):
                metadata = result.get('metadata', {})
                output += f"{i}. {metadata.get('title', 'No title')}\n"
                output += f"   Source: {metadata.get('source_entity_name', 'Unknown')}\n"
                output += f"   Date: {metadata.get('published_at', 'Unknown')}\n"
                output += f"   Snippet: {result.get('text', '')[:150]}...\n"
                output += f"   Score: {result.get('cohere_score', 0):.3f}\n\n"
            
            return output
            
        except Exception as e:
            return f"Search error: {str(e)}"
    
    def analyze_sentiment(self, text: str) -> str:
        """Quick sentiment analysis"""
        try:
            # Count sentiment words
            positive_words = ['good', 'great', 'excellent', 'bullish', 'positive', 'growth', 'surge', 'success']
            negative_words = ['bad', 'poor', 'bearish', 'negative', 'risk', 'concern', 'decline', 'crash']
            
            text_lower = text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count > negative_count:
                sentiment = "POSITIVE"
            elif negative_count > positive_count:
                sentiment = "NEGATIVE"
            else:
                sentiment = "NEUTRAL"
            
            return f"Sentiment Analysis:\n- Overall: {sentiment}\n- Positive signals: {positive_count}\n- Negative signals: {negative_count}"
            
        except Exception as e:
            return f"Sentiment error: {str(e)}"

def query_hyperliquid_agent(query: str) -> None:
    """Fast query - no boxes, no delays"""
    agent = HyperLiquidAgent()
    
    print(f"\n🔍 Query: {query}")
    print("="*50)
    
    # Get results fast
    search_results = agent.search_mentions(query, 15)
    sentiment = agent.analyze_sentiment(search_results)
    
    print(search_results)
    print(sentiment)
    
    # Get AI summary quickly
    summary_prompt = f"Query: {query}\n\nData: {search_results}\n\nSentiment: {sentiment}\n\nProvide a 3-sentence summary of what people are saying."
    response = agent.run(summary_prompt)
    
    print(f"\n📝 Summary:")
    print(response.content if hasattr(response, 'content') else str(response))