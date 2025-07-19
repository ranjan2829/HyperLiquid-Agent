from agno.agent import Agent
from agno.models.openai import OpenAIChat
from typing import List, Dict, Any
from vector_store import VectorStore
from reranker import SimpleReranker
import json
import datetime

class HyperLiquidAgent(Agent):
    def __init__(self):
        self.vector_store = VectorStore()
        self.reranker = SimpleReranker()
        
        super().__init__(
            model=OpenAIChat(id="gpt-4o"),
            tools=[self.search_mentions, self.analyze_trends],  # Keep both tools
            instructions=[
                "You are a HyperLiquid market analysis expert with deep DeFi knowledge.",
                "CRITICAL: Always search comprehensively before analysis - use multiple related queries if needed.",
                "TEMPORAL PRIORITY: Weight recent mentions (last 30 days) higher than older ones.",
                "INFLUENCE ASSESSMENT: Identify key influencers, their follower counts, and engagement metrics when available.",
                "SENTIMENT GRANULARITY: Distinguish between bullish/bearish, adoption/criticism, technical/fundamental sentiment.",
                "CROSS-REFERENCE: Look for corroborating evidence across multiple sources before conclusions.",
                "MARKET CONTEXT: Consider broader crypto market conditions when analyzing HyperLiquid sentiment.",
                "CREDIBILITY SCORING: Rate source credibility (1-10) based on: verified accounts, domain authority, track record.",
                "QUANTITATIVE METRICS: Extract specific numbers: trading volumes, TVL, token prices, user counts.",
                "COMPETITIVE ANALYSIS: Compare mentions with other DEX/DeFi protocols when relevant.",
                "UNCERTAINTY ACKNOWLEDGMENT: Clearly state confidence levels and data limitations."
            ],
            show_tool_calls=True,  # Show tool calls for transparency
            markdown=True,         # Enable markdown for better formatting
            reasoning=True,        # Enable reasoning to show thought process
        )
    
    def search_mentions(self, query: str, top_k: int = 15) -> str:
        """Enhanced search with multiple strategies"""
        try:
            # Multi-query approach for better coverage
            base_results = self.vector_store.search(query, top_k=top_k)
            
            # Generate related queries for broader coverage
            related_queries = self._generate_related_queries(query)
            all_results = base_results.copy()
            
            for related_query in related_queries:
                related_results = self.vector_store.search(related_query, top_k=5)
                all_results.extend(related_results)
            
            # Deduplicate and rerank
            unique_results = self.vector_store._deduplicate_results(all_results)
            reranked_results = self.reranker.rerank(query, unique_results, top_k=top_k)
            
            # Enhanced formatting with temporal weighting
            return self._format_results_with_analysis(query, reranked_results)
            
        except Exception as e:
            return f"❌ Search error: {str(e)}"
    
    def analyze_trends(self, time_period: str = "30d") -> str:
        """Analyze temporal trends in HyperLiquid mentions"""
        try:
            # Search for general HyperLiquid mentions
            all_results = self.vector_store.search("HyperLiquid", top_k=50)
            
            if not all_results:
                return "No data available for trend analysis."
            
            # Group by time periods
            trends = {}
            current_time = datetime.datetime.now()
            
            for result in all_results:
                metadata = result.get('metadata', {})
                published_at = metadata.get('published_at')
                
                if published_at:
                    try:
                        if isinstance(published_at, str):
                            pub_date = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        else:
                            pub_date = published_at
                        
                        days_ago = (current_time - pub_date.replace(tzinfo=None)).days
                        
                        # Categorize by time periods
                        if days_ago <= 7:
                            period = "Last 7 days"
                        elif days_ago <= 30:
                            period = "Last 30 days"
                        elif days_ago <= 90:
                            period = "Last 3 months"
                        else:
                            period = "Older than 3 months"
                        
                        trends.setdefault(period, []).append({
                            'title': metadata.get('title', 'No title'),
                            'source': metadata.get('source_entity_name', 'Unknown'),
                            'days_ago': days_ago,
                            'text': result.get('text', '')[:200]
                        })
                        
                    except Exception as e:
                        continue
            
            # Format trends analysis
            output = "📈 **TEMPORAL TRENDS ANALYSIS**\n"
            output += "=" * 50 + "\n\n"
            
            for period in ["Last 7 days", "Last 30 days", "Last 3 months", "Older than 3 months"]:
                if period in trends:
                    mentions = trends[period]
                    output += f"🕒 **{period}**: {len(mentions)} mentions\n"
                    
                    # Show top mentions for this period
                    for i, mention in enumerate(mentions[:3], 1):
                        output += f"   {i}. {mention['title']} (from {mention['source']})\n"
                    
                    if len(mentions) > 3:
                        output += f"   ... and {len(mentions) - 3} more\n"
                    output += "\n"
            
            return output
            
        except Exception as e:
            return f"❌ Trends analysis error: {str(e)}"
    
    def _generate_related_queries(self, original_query: str) -> List[str]:
        """Generate semantically related queries"""
        # Enhanced query expansion
        expansions = []
        
        # Basic replacements
        if "influencer" in original_query.lower():
            expansions.append(original_query.replace("influencer", "trader"))
            expansions.append(original_query.replace("influencer", "analyst"))
        
        if "tweets" in original_query.lower():
            expansions.append(original_query.replace("tweets", "posts"))
            expansions.append(original_query.replace("tweets", "mentions"))
        
        if "recently" in original_query.lower():
            expansions.append(original_query.replace("recently", "latest"))
            expansions.append(original_query.replace("recently", "this week"))
        
        # Add HyperLiquid specific variations
        if "hyperliquid" not in original_query.lower():
            expansions.append(f"HyperLiquid {original_query}")
        
        return expansions[:3]  # Return top 3 variations
    
    def _format_results_with_analysis(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Format search results with advanced hybrid ranking (recency + relevance + importance)"""
        if not results:
            return "No relevant mentions found for this query."
        
        current_time = datetime.datetime.now()
        enhanced_results = []
        
        for result in results:
            metadata = result.get('metadata', {})
            published_at = metadata.get('published_at')
            
            # Calculate recency score (0-1, higher = more recent)
            if published_at:
                try:
                    if isinstance(published_at, str):
                        pub_date = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    else:
                        pub_date = published_at
                    
                    days_ago = (current_time - pub_date.replace(tzinfo=None)).days
                    
                    # Advanced recency scoring with different decay rates
                    if days_ago <= 7:
                        recency_score = 1.0  # Last week = maximum recency
                    elif days_ago <= 30:
                        recency_score = 0.8  # Last month = high recency
                    elif days_ago <= 90:
                        recency_score = 0.5  # Last 3 months = medium recency
                    elif days_ago <= 365:
                        recency_score = 0.2  # Last year = low recency
                    else:
                        recency_score = 0.1  # Older = minimal recency
                        
                except Exception:
                    recency_score = 0.1
                    days_ago = 999
            else:
                recency_score = 0.1
                days_ago = 999
            
            # Calculate importance score based on source and content indicators
            importance_score = self._calculate_importance_score(result)
            
            # Get base Cohere relevance score
            cohere_score = result.get('cohere_score', 0)
            
            # Hybrid scoring with configurable weights
            # You can adjust these weights based on your priorities
            relevance_weight = 0.5    # 50% - How relevant is the content
            recency_weight = 0.3      # 30% - How recent is it
            importance_weight = 0.2   # 20% - How important is the source/content
            
            hybrid_score = (
                relevance_weight * cohere_score +
                recency_weight * recency_score +
                importance_weight * importance_score
            )
            
            # Store all scores for analysis
            result['cohere_score'] = cohere_score
            result['recency_score'] = recency_score
            result['importance_score'] = importance_score
            result['hybrid_score'] = hybrid_score
            result['days_ago'] = days_ago
            
            enhanced_results.append(result)
        
        # Sort by hybrid score (highest first)
        ranked_results = sorted(enhanced_results, key=lambda x: x.get('hybrid_score', 0), reverse=True)
        
        # Format results with detailed scoring information
        output = f"🔍 **HYBRID-RANKED SEARCH RESULTS** - Found {len(ranked_results)} relevant mentions:\n"
        output += f"📊 **RANKING FORMULA:** 50% Relevance + 30% Recency + 20% Importance\n"
        output += "=" * 80 + "\n\n"
        
        for i, result in enumerate(ranked_results, 1):
            metadata = result.get('metadata', {})
            
            # Get all scores
            cohere_score = result.get('cohere_score', 0)
            recency_score = result.get('recency_score', 0)
            importance_score = result.get('importance_score', 0)
            hybrid_score = result.get('hybrid_score', 0)
            days_ago = result.get('days_ago', 999)
            
            # Determine overall relevance level based on hybrid score
            if hybrid_score > 0.8:
                relevance_level = "🟢 HIGHLY RELEVANT"
            elif hybrid_score > 0.6:
                relevance_level = "🟡 MODERATELY RELEVANT"
            elif hybrid_score > 0.4:
                relevance_level = "🟠 SOMEWHAT RELEVANT"
            else:
                relevance_level = "🔴 LOW RELEVANCE"
            
            # Get recency indicator
            if days_ago <= 7:
                recency_indicator = "🔥 VERY RECENT"
            elif days_ago <= 30:
                recency_indicator = "⚡ RECENT"
            elif days_ago <= 90:
                recency_indicator = "📅 SOMEWHAT RECENT"
            else:
                recency_indicator = "📜 OLDER"
            
            # Get importance indicator
            if importance_score > 0.8:
                importance_indicator = "⭐ HIGH IMPORTANCE"
            elif importance_score > 0.6:
                importance_indicator = "🌟 MEDIUM IMPORTANCE"
            else:
                importance_indicator = "💫 STANDARD"
            
            output += f"📄 **RESULT #{i}** - {relevance_level}\n"
            output += f"├─ **Title:** {metadata.get('title', 'No title')}\n"
            output += f"├─ **Source:** {metadata.get('source_entity_name', 'Unknown')}\n"
            output += f"├─ **Date:** {metadata.get('published_at', 'Unknown')} ({days_ago} days ago)\n"
            output += f"├─ **Channel:** {metadata.get('channel_name', 'Unknown')} ({metadata.get('channel_type', 'Unknown')})\n"
            output += f"├─ **URL:** {metadata.get('url', 'No URL')}\n"
            output += f"│\n"
            output += f"├─ **📊 SCORING BREAKDOWN:**\n"
            output += f"│  ├─ Hybrid Score: {hybrid_score:.4f}/1.0000 ⭐\n"
            output += f"│  ├─ Cohere Relevance: {cohere_score:.4f}/1.0000 (50% weight)\n"
            output += f"│  ├─ Recency Score: {recency_score:.4f}/1.0000 (30% weight) {recency_indicator}\n"
            output += f"│  └─ Importance Score: {importance_score:.4f}/1.0000 (20% weight) {importance_indicator}\n"
            output += f"│\n"
            output += f"└─ **Content Preview:** {result.get('text', '')[:350]}...\n\n"
            
            # Add separator between results
            if i < len(ranked_results):
                output += "─" * 80 + "\n\n"
        
        # Enhanced summary statistics
        output += f"\n📊 **ENHANCED SEARCH SUMMARY:**\n"
        output += f"├─ Total Results: {len(ranked_results)}\n"
        output += f"├─ Average Hybrid Score: {sum(r.get('hybrid_score', 0) for r in ranked_results) / len(ranked_results):.4f}\n"
        output += f"├─ Average Relevance: {sum(r.get('cohere_score', 0) for r in ranked_results) / len(ranked_results):.4f}\n"
        output += f"├─ Average Recency: {sum(r.get('recency_score', 0) for r in ranked_results) / len(ranked_results):.4f}\n"
        output += f"├─ Average Importance: {sum(r.get('importance_score', 0) for r in ranked_results) / len(ranked_results):.4f}\n"
        output += f"├─ Recent Results (≤30 days): {len([r for r in ranked_results if r.get('days_ago', 999) <= 30])}\n"
        output += f"└─ High Importance Results: {len([r for r in ranked_results if r.get('importance_score', 0) > 0.8])}\n\n"
        
        return output
    
    def _calculate_importance_score(self, result: Dict[str, Any]) -> float:
        """Calculate importance score based on source credibility and content indicators"""
        metadata = result.get('metadata', {})
        text = result.get('text', '').lower()
        
        importance_score = 0.5  # Base score
        
        # Source credibility scoring
        source = metadata.get('source_entity_name', '').lower()
        
        # Tier 1 sources (highest credibility)
        tier_1_sources = ['coindesk', 'cointelegraph', 'the block', 'decrypt', 'bloomberg']
        if any(s in source for s in tier_1_sources):
            importance_score += 0.4
        # Tier 2 sources (high credibility)  
        elif any(s in source for s in ['panewslab', 'cryptonews', 'wu blockchain', 'blockworks']):
            importance_score += 0.3
        # Tier 3 sources (medium credibility)
        elif any(s in source for s in ['odaily', 'beincrypto', 'cryptoslate']):
            importance_score += 0.2
        
        # Content importance indicators
        high_impact_keywords = [
            'breaking', 'exclusive', 'major', 'significant', 'record', 'milestone',
            'launch', 'partnership', 'integration', 'hack', 'exploit', 'vulnerability'
        ]
        
        # Financial/numeric indicators
        financial_keywords = [
            'million', 'billion', 'tvl', 'volume', 'price', '$', 'apy', 'yield',
            'profit', 'loss', 'surge', 'crash', 'growth'
        ]
        
        # Add points for high-impact content
        for keyword in high_impact_keywords:
            if keyword in text:
                importance_score += 0.05
        
        for keyword in financial_keywords:
            if keyword in text:
                importance_score += 0.03
        
        # Channel type bonus
        channel_type = metadata.get('channel_type', '').lower()
        if channel_type in ['news', 'official']:
            importance_score += 0.1
        elif channel_type == 'twitter':
            importance_score += 0.05
        
        # Cap at 1.0
        return min(importance_score, 1.0)

def query_hyperliquid_agent(query: str) -> None:
    """Query HyperLiquid agent with improved AI analysis and reasoning - shows search results + analysis"""
    agent = HyperLiquidAgent()
    
    print(f"\n🔍 Query: {query}")
    print("="*80)
    
    # First, show the raw search results
    print("🔍 **SEARCHING FOR MENTIONS...**\n")
    search_results = agent.search_mentions(query, 15)
    print(search_results)
    
    # Then provide AI analysis
    print("\n" + "="*80)
    print("🤖 **AI ANALYSIS & REASONING**")
    print("="*80)
    
    # Enhanced prompt that encourages detailed analysis of each result
    enhanced_prompt = f"""
    Based on the search results above for the query: "{query}"
    
    **ANALYSIS FRAMEWORK:**
    
    1. **SEARCH RESULTS REVIEW:** Reference the specific search results shown above by their result numbers (#1, #2, etc.)
    
    2. **INDIVIDUAL RESULT ANALYSIS:** For the top 5 search results, provide:
       - Content relevance assessment 
       - Sentiment indicators found in the text
       - Key HyperLiquid features mentioned
       - Source credibility evaluation (rate 1-10)
       - Temporal context significance (how recent/relevant)
    
    3. **COHERE RANKING ANALYSIS:** 
       - Explain why results ranked high/low based on their Cohere scores
       - Assess if Cohere's ranking aligns with actual relevance
       - Identify any ranking anomalies
    
    4. **CROSS-RESULT PATTERNS:**
       - Common themes across the top 15 results
       - Sentiment consistency or divergence
       - Source diversity and potential bias
       - Temporal trends in the data
    
    5. **COMPREHENSIVE SYNTHESIS:**
       - Overall market sentiment with evidence from specific results
       - Key insights and takeaways
       - Confidence level (1-10) with justification
       - Specific citations from top-ranked results with their result numbers
    
    **IMPORTANT:** 
    - Reference specific results by their numbers (e.g., "Result #1", "Result #3")
    - Use the actual Cohere scores shown above
    - Cite the actual source names and titles from the search results
    - Consider the temporal weighting scores shown
    """
    
    response = agent.run(enhanced_prompt)
    print(response.content if hasattr(response, 'content') else str(response))