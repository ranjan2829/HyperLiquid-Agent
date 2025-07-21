import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import datetime

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from vector_store import VectorStore
from reranker import SimpleReranker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HyperLiquidAgent(Agent):
    """Queryable HyperLiquid market analysis agent"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize agent with vector store and reranker"""
        self.config = config or {}
        
        # Initialize components
        self.vector_store = VectorStore()
        self.reranker = SimpleReranker()
        
        # Configure agent
        super().__init__(
            model=OpenAIChat(
                id=self.config.get('model_id', "gpt-4o"),
                temperature=self.config.get('temperature', 0.1),
                max_tokens=self.config.get('max_tokens', 8000)  # Increased for comprehensive responses
            ),
            tools=[self.search_mentions],
            instructions=self._get_instructions(),
            show_tool_calls=False,
            markdown=True,
        )
    
    def _get_instructions(self) -> List[str]:
        """Get enhanced agent instructions for better frontend display"""
        return [
            "You are a HyperLiquid market analysis expert with deep knowledge of DeFi, trading, and market dynamics.",
            "Always search for information before answering queries to provide factual, data-driven insights.",
            "Analyze ALL search results comprehensively and structure your response for clear frontend display.",
            "Use proper markdown formatting with headers, bullet points, and emphasis for better readability.",
            "Provide detailed reasoning with specific evidence and source attributions.",
            "Include quantitative metrics, sentiment analysis, and actionable insights.",
            "Structure your analysis with clear sections for easy frontend parsing.",
            "Reference specific result numbers and include confidence levels for major findings.",
            "Focus on market trends, sentiment patterns, and strategic implications."
        ]
    
    def search_mentions(self, query: str, top_k: int = 15) -> str:
        """Search TurboPuffer and return ALL reranked results"""
        try:
            logger.info(f"🔍 Starting TurboPuffer search for: '{query}'")
            
            # Perform base search
            base_results = self.vector_store.search(query, top_k=top_k)
            logger.info(f"📊 TurboPuffer base search: {len(base_results)} results")
            
            # Generate related queries for broader coverage
            related_queries = self._generate_related_queries(query)
            all_results = base_results.copy()
            
            for i, related_query in enumerate(related_queries[:3], 1):
                try:
                    related_results = self.vector_store.search(related_query, top_k=10)
                    all_results.extend(related_results)
                    logger.info(f"🔄 Related query {i}: '{related_query}' -> +{len(related_results)} results")
                except Exception as e:
                    logger.warning(f"❌ Related query {i} failed: {e}")
                    continue
            
            # Deduplicate and rerank with Cohere
            unique_results = self._deduplicate_results(all_results)
            logger.info(f"🔧 After deduplication: {len(unique_results)} unique results")
            
            reranked_results = self.reranker.rerank(query, unique_results, top_k=top_k)
            logger.info(f"📈 Cohere reranking complete: {len(reranked_results)} final results")
            
            # Format ALL results for agent analysis
            return self._format_comprehensive_results(query, reranked_results)
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return f"Search failed: {str(e)}"
    
    def _generate_related_queries(self, original_query: str) -> List[str]:
        """Generate related search queries"""
        query_lower = original_query.lower()
        related = []
        
        # Add HyperLiquid variations
        if 'hyperliquid' not in query_lower:
            related.append(f"HyperLiquid {original_query}")
        
        # Add HYPE token variations
        if 'hype' not in query_lower and any(term in query_lower for term in ['token', 'price', 'trading']):
            related.append(original_query.replace('HyperLiquid', 'HYPE token'))
        
        # Add risk-related variations
        if 'risk' in query_lower:
            related.append(original_query.replace('risk', 'concerns'))
            related.append(original_query.replace('risk', 'warning'))
        
        # Add sentiment variations
        if any(term in query_lower for term in ['saying', 'mention', 'opinion']):
            related.append(f"{original_query} sentiment analysis")
            
        return related
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get('metadata', {}).get('url')
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            unique_results.append(result)
        
        return unique_results
    
    def _format_comprehensive_results(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Format ALL search results for comprehensive agent analysis"""
        if not results:
            return f"No relevant results found for: {query}"
        
        formatted = f"COMPREHENSIVE TURBOPUFFER SEARCH RESULTS\n"
        formatted += f"Query: {query}\n"
        formatted += f"Total Reranked Results: {len(results)}\n"
        formatted += f"Data Source: TurboPuffer + Cohere Reranking\n"
        formatted += "=" * 120 + "\n\n"
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            content = result.get('text', '')[:600]  # More content for analysis
            cohere_score = result.get('cohere_score', 0)
            
            # Extract key metadata
            title = metadata.get('title', 'No title')
            source = metadata.get('source_entity_name', 'Unknown')
            date_str = metadata.get('published_at', '')
            url = metadata.get('url', 'No URL')
            
            formatted += f"📊 **RESULT #{i}** | Cohere Relevance: {cohere_score:.4f}\n"
            formatted += f"📰 Title: {title}\n"
            formatted += f"🏢 Source: {source}\n"
            formatted += f"📅 Published: {self._format_date(date_str)}\n"
            formatted += f"🔗 URL: {url}\n"
            formatted += f"📝 Content Extract: {content}...\n"
            formatted += f"🎯 Ranking Position: #{i} of {len(results)}\n"
            formatted += "-" * 100 + "\n\n"
        
        # Add search summary
        formatted += f"SEARCH METADATA:\n"
        formatted += f"- Average Relevance Score: {sum(r.get('cohere_score', 0) for r in results) / len(results):.4f}\n"
        formatted += f"- Date Range: {self._get_date_range(results)}\n"
        formatted += f"- Unique Sources: {len(set(r.get('metadata', {}).get('source_entity_name', 'Unknown') for r in results))}\n"
        formatted += f"- Search Timestamp: {datetime.datetime.now().isoformat()}\n\n"
        
        return formatted
    
    def _format_date(self, date_str: str) -> str:
        """Format date string with days ago"""
        if not date_str:
            return "Unknown date"
        
        try:
            if isinstance(date_str, str):
                pub_date = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                pub_date = date_str
            
            days_ago = (datetime.datetime.now() - pub_date.replace(tzinfo=None)).days
            
            if days_ago == 0:
                return "Today"
            elif days_ago == 1:
                return "1 day ago"
            else:
                return f"{days_ago} days ago ({pub_date.strftime('%Y-%m-%d')})"
        except Exception:
            return f"Unknown date ({date_str})"
    
    def _get_date_range(self, results: List[Dict[str, Any]]) -> str:
        """Get date range of results"""
        dates = []
        for result in results:
            date_str = result.get('metadata', {}).get('published_at', '')
            if date_str:
                try:
                    if isinstance(date_str, str):
                        pub_date = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        dates.append(pub_date)
                except Exception:
                    continue
        
        if not dates:
            return "Unknown"
        
        oldest = min(dates)
        newest = max(dates)
        
        if oldest == newest:
            return oldest.strftime('%Y-%m-%d')
        else:
            return f"{oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"

def query_hyperliquid_agent(query: str, config: Optional[Dict[str, Any]] = None) -> None:
    """Query HyperLiquid agent with enhanced formatting for frontend display"""
    
    print(f"\n🚀 **HYPERLIQUID MARKET INTELLIGENCE QUERY**")
    print(f"🔍 Query: {query}")
    print("=" * 120)
    
    start_time = time.time()
    
    try:
        # Initialize agent
        print("🔧 Initializing HyperLiquid Agent with TurboPuffer & Cohere...")
        agent = HyperLiquidAgent(config)
        
        # Manual search to show process
        print("\n📡 **TURBOPUFFER DATA FETCH PROCESS**")
        print("-" * 60)
        
        base_results = agent.vector_store.search(query, top_k=15)
        print(f"📊 TurboPuffer base search: {len(base_results)} results")
        
        related_queries = agent._generate_related_queries(query)
        print(f"🔄 Generated {len(related_queries)} related queries: {related_queries}")
        
        all_results = base_results.copy()
        for i, related_query in enumerate(related_queries[:3], 1):
            try:
                related_results = agent.vector_store.search(related_query, top_k=10)
                all_results.extend(related_results)
                print(f"   ├─ Query {i}: '{related_query}' -> +{len(related_results)} results")
            except Exception:
                print(f"   ├─ Query {i}: Failed")
                continue
        
        unique_results = agent._deduplicate_results(all_results)
        print(f"🔧 After deduplication: {len(unique_results)} unique results")
        
        reranked_results = agent.reranker.rerank(query, unique_results, top_k=15)
        print(f"📈 Cohere reranking complete: {len(reranked_results)} final results")
        
        # Display all 15 results with reasoning
        print(f"\n📋 **ALL {len(reranked_results)} RERANKED RESULTS FROM TURBOPUFFER**")
        print("=" * 120)
        
        for i, result in enumerate(reranked_results, 1):
            metadata = result.get('metadata', {})
            cohere_score = result.get('cohere_score', 0)
            content = result.get('text', '')[:300]
            
            print(f"\n🎯 **RESULT #{i}** - Cohere Score: {cohere_score:.4f}")
            print(f"📰 **Title:** {metadata.get('title', 'No title')}")
            print(f"🏢 **Source:** {metadata.get('source_entity_name', 'Unknown')}")
            print(f"📅 **Date:** {agent._format_date(metadata.get('published_at', ''))}")
            print(f"🔗 **URL:** {metadata.get('url', 'No URL')}")
            print(f"📝 **Content:** {content}...")
            print(f"🧠 **Ranking Reasoning:** High semantic relevance to query (Cohere AI)")
            print("-" * 80)
        
        # Enhanced AI Agent Analysis with better formatting
        print(f"\n🤖 **AGNO AI AGENT COMPREHENSIVE ANALYSIS**")
        print("=" * 120)
        
        enhanced_query = f"""
        Based on the {len(reranked_results)} TurboPuffer search results for query: "{query}"
        
        Provide a comprehensive, well-structured market intelligence analysis using proper markdown formatting:
        
        ### 🔍 **DETAILED REASONING:**
        
        #### Key Themes and Trends:
        - Analyze ALL {len(reranked_results)} results comprehensively
        - Identify major themes, sentiment patterns, and market trends
        - Group findings by significance and relevance
        - Assess temporal patterns and emerging developments
        - Highlight consensus vs conflicting information
        
        #### Market Sentiment Analysis:
        - Overall sentiment (bullish/bearish/neutral) with confidence level
        - Key sentiment drivers and their impact
        - Community perception and influencer opinions
        - Risk factors and concerns identified
        
        #### Strategic Implications:
        - What this means for HyperLiquid users and investors
        - Actionable insights and recommendations
        - Potential opportunities and threats
        - Market positioning and competitive landscape
        
        ### 📊 **QUANTITATIVE INSIGHTS:**
        
        #### Key Metrics and Data Points:
        - Extract specific numbers, percentages, and financial data
        - Trading volumes, TVL changes, price movements
        - User activity and adoption metrics
        - Performance comparisons and benchmarks
        
        #### Confidence Assessment:
        - **High Confidence** findings (supported by multiple credible sources)
        - **Medium Confidence** findings (limited but credible evidence)
        - **Low Confidence** findings (requires further verification)
        
        ### 🔗 **SOURCE ATTRIBUTION:**
        
        #### Primary Evidence (Quote key sources):
        - Direct quotes from top 5-8 most relevant results
        - Include source name, date, and result number
        - Highlight credibility and authority of sources
        - Note any potential bias or limitations
        
        #### Supporting Evidence:
        - Additional corroborating information from other results
        - Cross-references and validation from multiple sources
        - Timeline of events and developments
        
        ### 💡 **EXECUTIVE SUMMARY:**
        
        #### Key Takeaways:
        1. Most important finding with confidence level
        2. Secondary insights and implications  
        3. Risk factors and considerations
        4. Recommended actions or monitoring points
        
        **Overall Assessment:** Provide a clear, actionable conclusion with confidence rating (1-10).
        
        ---
        
        **Analysis Requirements:**
        - Use proper markdown headers (###, ####) for structure
        - Include bullet points and numbered lists for clarity
        - Bold important terms and findings
        - Reference specific result numbers (Result #1, #2, etc.)
        - Provide quantitative confidence levels where possible
        - Include specific URLs for key claims
        - Structure for easy frontend parsing and display
        """
        
        response = agent.run(enhanced_query)
        print(response.content if hasattr(response, 'content') else str(response))
        
        # Performance summary
        execution_time = time.time() - start_time
        print(f"\n✅ **ANALYSIS COMPLETE**")
        print("=" * 120)
        print(f"📊 **Performance Metrics:**")
        print(f"   ├─ Total execution time: {execution_time:.2f}s")
        print(f"   ├─ Results processed: {len(reranked_results)}")
        print(f"   ├─ Average relevance score: {sum(r.get('cohere_score', 0) for r in reranked_results) / len(reranked_results):.4f}")
        print(f"   └─ Data sources: TurboPuffer + Cohere + OpenAI GPT-4")
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        print(f"❌ **CRITICAL ERROR:** {str(e)}")

# Configuration
PRODUCTION_CONFIG = {
    'model_id': 'gpt-4o',
    'temperature': 0.1,
    'max_tokens': 8000,  # Increased for comprehensive analysis
}

if __name__ == "__main__":
    # Example queries
    queries = [
        "What are people saying about HyperLiquid's vaults?",
        "Did anyone mention HYPE token and risk in the same sentence?",
        "Any influencer tweets about HyperLiquid recently?"
    ]
    
    for query in queries:
        query_hyperliquid_agent(query, PRODUCTION_CONFIG)