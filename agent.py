import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import datetime
import json
from functools import wraps

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from vector_store import VectorStore
from reranker import SimpleReranker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hyperliquid_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SearchMetrics:
    """Track search performance metrics"""
    query: str
    results_count: int
    avg_relevance: float
    execution_time: float
    timestamp: datetime.datetime
    error: Optional[str] = None

class MetricsCollector:
    """Collect and analyze performance metrics"""
    
    def __init__(self):
        self.metrics: List[SearchMetrics] = []
    
    def add_metric(self, metric: SearchMetrics):
        """Add a search metric"""
        self.metrics.append(metric)
        logger.info(f"Search metric added: {metric.query} - {metric.results_count} results")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance analytics"""
        if not self.metrics:
            return {"status": "No data available"}
        
        successful_searches = [m for m in self.metrics if m.error is None]
        
        return {
            "total_searches": len(self.metrics),
            "successful_searches": len(successful_searches),
            "success_rate": len(successful_searches) / len(self.metrics) * 100,
            "avg_results_per_search": sum(m.results_count for m in successful_searches) / len(successful_searches) if successful_searches else 0,
            "avg_relevance_score": sum(m.avg_relevance for m in successful_searches) / len(successful_searches) if successful_searches else 0,
            "avg_execution_time": sum(m.execution_time for m in successful_searches) / len(successful_searches) if successful_searches else 0,
            "recent_errors": [m.error for m in self.metrics[-5:] if m.error],
        }

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying failed operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
            
            logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator

class SourceCredibilityAnalyzer:
    """Analyze and score source credibility"""
    
    def __init__(self):
        self.source_tiers = {
            'tier_1': {
                'sources': ['coindesk', 'cointelegraph', 'the block', 'decrypt', 'bloomberg', 'reuters'],
                'base_score': 0.9,
                'description': 'Premium financial and crypto news outlets'
            },
            'tier_2': {
                'sources': ['panewslab', 'cryptonews', 'wu blockchain', 'blockworks', 'coindesk'],
                'base_score': 0.7,
                'description': 'Established crypto-focused publications'
            },
            'tier_3': {
                'sources': ['odaily', 'beincrypto', 'cryptoslate', 'ambcrypto'],
                'base_score': 0.5,
                'description': 'Standard crypto news sources'
            },
            'social': {
                'sources': ['twitter', 'telegram', 'discord', 'reddit'],
                'base_score': 0.3,
                'description': 'Social media and community platforms'
            }
        }
    
    def get_source_tier(self, source: str) -> Dict[str, Any]:
        """Get source tier information"""
        source_lower = source.lower()
        
        for tier_name, tier_info in self.source_tiers.items():
            if any(s in source_lower for s in tier_info['sources']):
                return {
                    'tier': tier_name,
                    'base_score': tier_info['base_score'],
                    'description': tier_info['description']
                }
        
        return {
            'tier': 'unknown',
            'base_score': 0.1,
            'description': 'Unrecognized source'
        }

class HyperLiquidAgent(Agent):
    """Production-ready HyperLiquid market analysis agent"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize agent with production configurations"""
        self.config = config or {}
        self.metrics_collector = MetricsCollector()
        self.source_analyzer = SourceCredibilityAnalyzer()
        
        # Initialize vector store and reranker with error handling
        try:
            self.vector_store = VectorStore()
            self.reranker = SimpleReranker()
            logger.info("Successfully initialized vector store and reranker")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
        
        # Configure agent with production settings
        super().__init__(
            model=OpenAIChat(
                id=self.config.get('model_id', "gpt-4o"),
                temperature=self.config.get('temperature', 0.1),  # Lower for consistency
                max_tokens=self.config.get('max_tokens', 4000)
            ),
            tools=[self.search_mentions, self.analyze_trends],
            instructions=self._get_production_instructions(),
            show_tool_calls=self.config.get('show_tool_calls', True),
            markdown=self.config.get('markdown', True),
            reasoning=self.config.get('reasoning', True),
        )
    
    def _get_production_instructions(self) -> List[str]:
        """Get comprehensive production instructions"""
        return [
            "You are a HyperLiquid market analysis expert with deep DeFi knowledge.",
            "ACCURACY: Prioritize accuracy over speed. Verify information across multiple sources.",
            "CRITICAL SEARCH: Always search comprehensively before analysis - use multiple related queries.",
            "TEMPORAL INTELLIGENCE: Weight recent mentions (last 30 days) significantly higher.",
            "INFLUENCE MAPPING: Identify key influencers, follower counts, and engagement metrics.",
            "SENTIMENT PRECISION: Distinguish between bullish/bearish, adoption/criticism, technical/fundamental.",
            "CROSS-VALIDATION: Require corroborating evidence across multiple credible sources.",
            "MARKET CONTEXT: Consider broader crypto market conditions and macroeconomic factors.",
            "CREDIBILITY ASSESSMENT: Rate source credibility (1-10) based on track record and verification.",
            "QUANTITATIVE FOCUS: Extract specific metrics: TVL, volumes, prices, user counts, yields.",
            "COMPETITIVE INTELLIGENCE: Compare with other DEX/DeFi protocols when relevant.",
            "UNCERTAINTY TRANSPARENCY: Always state confidence levels and acknowledge limitations.",
            "BIAS AWARENESS: Identify potential conflicts of interest or promotional content.",
            "TEMPORAL TRENDS: Identify patterns across different time periods.",
            "RISK ASSESSMENT: Highlight potential risks and red flags in sentiment or data."
        ]
    
    @retry_on_failure(max_retries=3)
    def search_mentions(self, query: str, top_k: int = 15) -> str:
        """Enhanced search with comprehensive error handling and metrics"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting search for query: '{query}' with top_k={top_k}")
            
            # Input validation
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            if top_k <= 0 or top_k > 50:
                raise ValueError("top_k must be between 1 and 50")
            
            # Multi-query approach for better coverage
            base_results = self.vector_store.search(query, top_k=top_k)
            logger.info(f"Base search returned {len(base_results)} results")
            
            # Generate related queries for broader coverage
            related_queries = self._generate_related_queries(query)
            all_results = base_results.copy()
            
            for related_query in related_queries:
                try:
                    related_results = self.vector_store.search(related_query, top_k=5)
                    all_results.extend(related_results)
                    logger.debug(f"Related query '{related_query}' added {len(related_results)} results")
                except Exception as e:
                    logger.warning(f"Related query failed: {related_query} - {e}")
                    continue
            
            # Deduplicate and rerank
            unique_results = self.vector_store._deduplicate_results(all_results)
            reranked_results = self.reranker.rerank(query, unique_results, top_k=top_k)
            
            # Calculate metrics
            execution_time = time.time() - start_time
            avg_relevance = sum(r.get('cohere_score', 0) for r in reranked_results) / len(reranked_results) if reranked_results else 0
            
            # Store metrics
            metric = SearchMetrics(
                query=query,
                results_count=len(reranked_results),
                avg_relevance=avg_relevance,
                execution_time=execution_time,
                timestamp=datetime.datetime.now()
            )
            self.metrics_collector.add_metric(metric)
            
            # Enhanced formatting with temporal weighting
            return self._format_results_with_analysis(query, reranked_results)
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Search failed for query '{query}': {e}")
            
            # Store error metric
            error_metric = SearchMetrics(
                query=query,
                results_count=0,
                avg_relevance=0.0,
                execution_time=execution_time,
                timestamp=datetime.datetime.now(),
                error=str(e)
            )
            self.metrics_collector.add_metric(error_metric)
            
            return f"❌ Search error: {str(e)}"
    
    @retry_on_failure(max_retries=2)
    def analyze_trends(self, time_period: str = "30d") -> str:
        """Analyze temporal trends with enhanced analytics"""
        try:
            logger.info(f"Starting trend analysis for period: {time_period}")
            
            # Search for general HyperLiquid mentions
            all_results = self.vector_store.search("HyperLiquid", top_k=100)  # Larger sample for trends
            
            if not all_results:
                return "❌ No data available for trend analysis."
            
            # Enhanced trend analysis
            trends_data = self._analyze_temporal_patterns(all_results)
            sentiment_trends = self._analyze_sentiment_trends(all_results)
            source_distribution = self._analyze_source_distribution(all_results)
            
            # Format comprehensive trends report
            return self._format_trends_report(trends_data, sentiment_trends, source_distribution)
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return f"❌ Trends analysis error: {str(e)}"
    
    def _generate_related_queries(self, original_query: str) -> List[str]:
        """Generate semantically related queries with enhanced logic"""
        expansions = []
        query_lower = original_query.lower()
        
        # Synonym replacements
        replacements = {
            'influencer': ['trader', 'analyst', 'whale', 'investor'],
            'tweets': ['posts', 'mentions', 'comments', 'discussions'],
            'recently': ['latest', 'this week', 'this month', 'new'],
            'vault': ['vaults', 'yield farming', 'liquidity mining', 'staking'],
            'price': ['value', 'cost', 'rate', 'trading'],
            'volume': ['trading volume', 'liquidity', 'activity']
        }
        
        for original_term, alternatives in replacements.items():
            if original_term in query_lower:
                for alt in alternatives[:2]:  # Limit alternatives
                    new_query = original_query.replace(original_term, alt)
                    if new_query != original_query:
                        expansions.append(new_query)
        
        # Add HyperLiquid specific variations
        if 'hyperliquid' not in query_lower:
            expansions.append(f"HyperLiquid {original_query}")
        
        # Add HYPE token specific queries for relevant topics
        if any(term in query_lower for term in ['token', 'price', 'trading', 'volume']):
            expansions.append(original_query.replace('HyperLiquid', 'HYPE token'))
        
        return expansions[:4]  # Return top 4 variations
    
    def _calculate_importance_score(self, result: Dict[str, Any]) -> float:
        """Enhanced importance scoring with comprehensive factors"""
        metadata = result.get('metadata', {})
        text = result.get('text', '').lower()
        
        importance_score = 0.3  # Lower base score for more discrimination
        
        # Advanced source credibility scoring
        source = metadata.get('source_entity_name', '')
        source_info = self.source_analyzer.get_source_tier(source)
        importance_score += source_info['base_score'] * 0.4
        
        # Content quality indicators
        high_impact_keywords = [
            'breaking', 'exclusive', 'major', 'significant', 'record', 'milestone',
            'launch', 'partnership', 'integration', 'hack', 'exploit', 'vulnerability',
            'announcement', 'official', 'confirmed', 'verified'
        ]
        
        financial_keywords = [
            'million', 'billion', 'tvl', 'volume', 'price', '$', 'apy', 'yield',
            'profit', 'loss', 'surge', 'crash', 'growth', 'revenue', 'valuation'
        ]
        
        technical_keywords = [
            'upgrade', 'update', 'feature', 'bug', 'fix', 'optimization',
            'scalability', 'security', 'audit', 'compliance'
        ]
        
        # Weighted keyword scoring
        keyword_categories = [
            (high_impact_keywords, 0.08),
            (financial_keywords, 0.05),
            (technical_keywords, 0.03)
        ]
        
        for keywords, weight in keyword_categories:
            matches = sum(1 for keyword in keywords if keyword in text)
            importance_score += min(matches * weight, weight * 3)  # Cap per category
        
        # Channel type and engagement indicators
        channel_type = metadata.get('channel_type', '').lower()
        channel_bonus = {
            'news': 0.15,
            'official': 0.20,
            'twitter': 0.05,
            'telegram': 0.02,
            'rss': 0.10
        }
        importance_score += channel_bonus.get(channel_type, 0)
        
        # Length and content quality heuristics
        content_length = len(text)
        if content_length > 500:  # Substantial content
            importance_score += 0.05
        elif content_length < 100:  # Very short content
            importance_score -= 0.05
        
        # URL presence (indicates article vs snippet)
        if metadata.get('url') and 'http' in metadata['url']:
            importance_score += 0.03
        
        return min(importance_score, 1.0)
    
    def _format_results_with_analysis(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Production-ready result formatting with comprehensive analysis"""
        if not results:
            return "❌ No relevant mentions found for this query."
        
        try:
            current_time = datetime.datetime.now()
            enhanced_results = []
            
            for result in results:
                enhanced_result = self._enhance_result_with_scores(result, current_time)
                enhanced_results.append(enhanced_result)
            
            # Sort by hybrid score
            ranked_results = sorted(enhanced_results, key=lambda x: x.get('hybrid_score', 0), reverse=True)
            
            # Generate comprehensive output
            return self._generate_results_output(query, ranked_results)
            
        except Exception as e:
            logger.error(f"Result formatting failed: {e}")
            return f"❌ Error formatting results: {str(e)}"
    
    def _enhance_result_with_scores(self, result: Dict[str, Any], current_time: datetime.datetime) -> Dict[str, Any]:
        """Enhance result with comprehensive scoring"""
        metadata = result.get('metadata', {})
        published_at = metadata.get('published_at')
        
        # Calculate recency score with enhanced decay curve
        recency_score, days_ago = self._calculate_recency_score(published_at, current_time)
        
        # Calculate importance score
        importance_score = self._calculate_importance_score(result)
        
        # Get base Cohere relevance score
        cohere_score = result.get('cohere_score', 0)
        
        # Production hybrid scoring with configurable weights
        weights = self.config.get('scoring_weights', {
            'relevance': 0.5,
            'recency': 0.3,
            'importance': 0.2
        })
        
        hybrid_score = (
            weights['relevance'] * cohere_score +
            weights['recency'] * recency_score +
            weights['importance'] * importance_score
        )
        
        # Enhance result with all scores
        result.update({
            'cohere_score': cohere_score,
            'recency_score': recency_score,
            'importance_score': importance_score,
            'hybrid_score': hybrid_score,
            'days_ago': days_ago,
            'source_tier': self.source_analyzer.get_source_tier(metadata.get('source_entity_name', ''))
        })
        
        return result
    
    def _calculate_recency_score(self, published_at: Any, current_time: datetime.datetime) -> tuple:
        """Calculate recency score with advanced time decay"""
        if not published_at:
            return 0.1, 999
        
        try:
            if isinstance(published_at, str):
                pub_date = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            else:
                pub_date = published_at
            
            days_ago = (current_time - pub_date.replace(tzinfo=None)).days
            
            # Advanced recency scoring with smooth decay
            if days_ago <= 1:
                recency_score = 1.0
            elif days_ago <= 7:
                recency_score = 0.9
            elif days_ago <= 30:
                recency_score = 0.7
            elif days_ago <= 90:
                recency_score = 0.4
            elif days_ago <= 365:
                recency_score = 0.2
            else:
                recency_score = 0.1
            
            return recency_score, days_ago
            
        except Exception as e:
            logger.warning(f"Date parsing failed: {e}")
            return 0.1, 999
    
    def _generate_results_output(self, query: str, ranked_results: List[Dict[str, Any]]) -> str:
        """Generate comprehensive results output"""
        weights = self.config.get('scoring_weights', {'relevance': 50, 'recency': 30, 'importance': 20})
        
        output = f"🔍 **PRODUCTION SEARCH RESULTS** - Query: '{query}'\n"
        output += f"📊 **RANKING:** {weights['relevance']}% Relevance + {weights['recency']}% Recency + {weights['importance']}% Importance\n"
        output += f"📈 **PERFORMANCE:** {len(ranked_results)} results processed\n"
        output += "=" * 100 + "\n\n"
        
        for i, result in enumerate(ranked_results, 1):
            output += self._format_single_result(i, result)
            
            if i < len(ranked_results):
                output += "─" * 100 + "\n\n"
        
        # Enhanced summary with analytics
        output += self._generate_summary_analytics(ranked_results)
        
        return output
    
    def _format_single_result(self, index: int, result: Dict[str, Any]) -> str:
        """Format a single result with comprehensive information"""
        metadata = result.get('metadata', {})
        
        # Extract scores
        hybrid_score = result.get('hybrid_score', 0)
        cohere_score = result.get('cohere_score', 0)
        recency_score = result.get('recency_score', 0)
        importance_score = result.get('importance_score', 0)
        days_ago = result.get('days_ago', 999)
        source_tier = result.get('source_tier', {})
        
        # Determine indicators
        relevance_level = self._get_relevance_level(hybrid_score)
        recency_indicator = self._get_recency_indicator(days_ago)
        importance_indicator = self._get_importance_indicator(importance_score)
        
        output = f"📄 **RESULT #{index}** - {relevance_level}\n"
        output += f"├─ **Title:** {metadata.get('title', 'No title')}\n"
        output += f"├─ **Source:** {metadata.get('source_entity_name', 'Unknown')} ({source_tier.get('tier', 'unknown').upper()})\n"
        output += f"├─ **Date:** {metadata.get('published_at', 'Unknown')} ({days_ago} days ago)\n"
        output += f"├─ **Channel:** {metadata.get('channel_name', 'Unknown')} ({metadata.get('channel_type', 'Unknown')})\n"
        output += f"├─ **URL:** {metadata.get('url', 'No URL')}\n"
        output += f"│\n"
        output += f"├─ **📊 SCORING BREAKDOWN:**\n"
        output += f"│  ├─ 🎯 Hybrid Score: {hybrid_score:.4f}/1.0000 ⭐\n"
        output += f"│  ├─ 🔍 Relevance: {cohere_score:.4f}/1.0000 (50% weight)\n"
        output += f"│  ├─ ⏰ Recency: {recency_score:.4f}/1.0000 (30% weight) {recency_indicator}\n"
        output += f"│  ├─ ⭐ Importance: {importance_score:.4f}/1.0000 (20% weight) {importance_indicator}\n"
        output += f"│  └─ 📰 Source Tier: {source_tier.get('description', 'Unknown')}\n"
        output += f"│\n"
        output += f"└─ **Content Preview:** {result.get('text', '')[:400]}...\n\n"
        
        return output
    
    def _get_relevance_level(self, hybrid_score: float) -> str:
        """Get relevance level indicator"""
        if hybrid_score > 0.8:
            return "🟢 HIGHLY RELEVANT"
        elif hybrid_score > 0.6:
            return "🟡 MODERATELY RELEVANT"
        elif hybrid_score > 0.4:
            return "🟠 SOMEWHAT RELEVANT"
        else:
            return "🔴 LOW RELEVANCE"
    
    def _get_recency_indicator(self, days_ago: int) -> str:
        """Get recency indicator"""
        if days_ago <= 1:
            return "🔥 TODAY"
        elif days_ago <= 7:
            return "🔥 THIS WEEK"
        elif days_ago <= 30:
            return "⚡ THIS MONTH"
        elif days_ago <= 90:
            return "📅 LAST 3 MONTHS"
        else:
            return "📜 OLDER"
    
    def _get_importance_indicator(self, importance_score: float) -> str:
        """Get importance indicator"""
        if importance_score > 0.8:
            return "⭐ CRITICAL"
        elif importance_score > 0.6:
            return "🌟 HIGH"
        elif importance_score > 0.4:
            return "💫 MEDIUM"
        else:
            return "📝 STANDARD"
    
    def _generate_summary_analytics(self, results: List[Dict[str, Any]]) -> str:
        """Generate comprehensive summary analytics"""
        if not results:
            return ""
        
        # Calculate analytics
        total_results = len(results)
        avg_hybrid = sum(r.get('hybrid_score', 0) for r in results) / total_results
        avg_relevance = sum(r.get('cohere_score', 0) for r in results) / total_results
        avg_recency = sum(r.get('recency_score', 0) for r in results) / total_results
        avg_importance = sum(r.get('importance_score', 0) for r in results) / total_results
        
        recent_count = len([r for r in results if r.get('days_ago', 999) <= 30])
        high_importance = len([r for r in results if r.get('importance_score', 0) > 0.6])
        high_relevance = len([r for r in results if r.get('hybrid_score', 0) > 0.6])
        
        # Source distribution
        source_distribution = {}
        for result in results:
            tier = result.get('source_tier', {}).get('tier', 'unknown')
            source_distribution[tier] = source_distribution.get(tier, 0) + 1
        
        output = f"\n📊 **COMPREHENSIVE ANALYTICS:**\n"
        output += f"├─ 📈 Total Results: {total_results}\n"
        output += f"├─ 🎯 Average Hybrid Score: {avg_hybrid:.4f}\n"
        output += f"├─ 🔍 Average Relevance: {avg_relevance:.4f}\n"
        output += f"├─ ⏰ Average Recency: {avg_recency:.4f}\n"
        output += f"├─ ⭐ Average Importance: {avg_importance:.4f}\n"
        output += f"│\n"
        output += f"├─ 📊 Quality Distribution:\n"
        output += f"│  ├─ High Relevance (>0.6): {high_relevance} ({high_relevance/total_results*100:.1f}%)\n"
        output += f"│  ├─ Recent (≤30 days): {recent_count} ({recent_count/total_results*100:.1f}%)\n"
        output += f"│  └─ High Importance (>0.6): {high_importance} ({high_importance/total_results*100:.1f}%)\n"
        output += f"│\n"
        output += f"└─ 📰 Source Distribution:\n"
        
        for tier, count in sorted(source_distribution.items()):
            percentage = count / total_results * 100
            output += f"   ├─ {tier.title()}: {count} ({percentage:.1f}%)\n"
        
        return output
    
    def _analyze_temporal_patterns(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in the data"""
        # Implementation for temporal pattern analysis
        patterns = {
            'last_7_days': 0,
            'last_30_days': 0,
            'last_90_days': 0,
            'older': 0
        }
        
        current_time = datetime.datetime.now()
        
        for result in results:
            days_ago = result.get('days_ago', 999)
            if days_ago <= 7:
                patterns['last_7_days'] += 1
            elif days_ago <= 30:
                patterns['last_30_days'] += 1
            elif days_ago <= 90:
                patterns['last_90_days'] += 1
            else:
                patterns['older'] += 1
        
        return patterns
    
    def _analyze_sentiment_trends(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment trends over time"""
        # Basic sentiment analysis - can be enhanced with ML models
        positive_keywords = ['growth', 'success', 'profit', 'surge', 'bullish', 'positive']
        negative_keywords = ['loss', 'crash', 'bearish', 'negative', 'risk', 'concern']
        
        sentiment_data = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for result in results:
            text = result.get('text', '').lower()
            positive_count = sum(1 for word in positive_keywords if word in text)
            negative_count = sum(1 for word in negative_keywords if word in text)
            
            if positive_count > negative_count:
                sentiment_data['positive'] += 1
            elif negative_count > positive_count:
                sentiment_data['negative'] += 1
            else:
                sentiment_data['neutral'] += 1
        
        return sentiment_data
    
    def _analyze_source_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze distribution of sources"""
        source_counts = {}
        
        for result in results:
            source = result.get('metadata', {}).get('source_entity_name', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        return dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _format_trends_report(self, trends_data: Dict[str, Any], sentiment_trends: Dict[str, Any], source_distribution: Dict[str, Any]) -> str:
        """Format comprehensive trends report"""
        output = "📈 **TEMPORAL TRENDS ANALYSIS**\n"
        output += "=" * 60 + "\n\n"
        
        # Temporal distribution
        output += "🕒 **Time Distribution:**\n"
        for period, count in trends_data.items():
            output += f"   ├─ {period.replace('_', ' ').title()}: {count} mentions\n"
        
        output += "\n📊 **Sentiment Trends:**\n"
        total_sentiment = sum(sentiment_trends.values())
        if total_sentiment > 0:
            for sentiment, count in sentiment_trends.items():
                percentage = count / total_sentiment * 100
                output += f"   ├─ {sentiment.title()}: {count} ({percentage:.1f}%)\n"
        
        output += "\n📰 **Top Sources:**\n"
        for source, count in list(source_distribution.items())[:5]:
            output += f"   ├─ {source}: {count} mentions\n"
        
        return output
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        return self.metrics_collector.get_performance_report()

def query_hyperliquid_agent(query: str, config: Optional[Dict[str, Any]] = None) -> None:
    """Production-ready query function with comprehensive error handling"""
    start_time = time.time()
    
    try:
        # Input validation
        if not query or not query.strip():
            print("❌ Error: Query cannot be empty")
            return
        
        # Initialize agent with config
        agent = HyperLiquidAgent(config)
        
        print(f"\n🔍 HyperLiquid Market Analysis Query: {query}")
        print("=" * 100)
        
        # Search phase
        print("🔍 **SEARCHING MENTIONS...**")
        search_results = agent.search_mentions(query, 15)
        print(search_results)
        
        # Analysis phase
        print("\n" + "=" * 100)
        print("🤖 **AI MARKET ANALYSIS**")
        print("=" * 100)
        
        enhanced_prompt = f"""
        Based on the comprehensive search results above for: "{query}"
        
        **PRODUCTION ANALYSIS REQUIREMENTS:**
        
        1. **EXECUTIVE SUMMARY** (2-3 sentences):
           - Key finding with confidence level
           - Overall market sentiment
           - Primary recommendation
        
        2. **TOP 5 RESULTS ANALYSIS**:
           - Reference specific Result #X with hybrid scores
           - Content relevance and reliability assessment
           - Sentiment indicators and market implications
           - Source credibility evaluation (1-10 scale)
           - Temporal significance and trend direction
        
        3. **RANKING VALIDATION**:
           - Explain why top results ranked highly
           - Assess ranking accuracy vs actual relevance
           - Identify any anomalies or bias
        
        4. **MARKET INTELLIGENCE**:
           - Cross-reference patterns across all 15 results
           - Sentiment consistency or divergence analysis
           - Source diversity and potential echo chambers
           - Temporal trends and momentum indicators
        
        5. **INVESTMENT-GRADE SYNTHESIS**:
           - Overall market sentiment with statistical backing
           - Key actionable insights for stakeholders
           - Risk factors and opportunities identified
           - Confidence assessment (1-10) with detailed justification
           - Specific citations with result numbers and scores
        
        6. **LIMITATIONS & DISCLAIMERS**:
           - Data gaps or coverage limitations
           - Potential bias sources
           - Recommended follow-up analysis
        
        **CRITICAL REQUIREMENTS:**
        - Reference specific results by number (Result #1, #2, etc.)
        - Use actual hybrid and Cohere scores from output
        - Cite exact source names and publication dates
        - Provide quantitative confidence metrics
        - Distinguish between correlation and causation
        """
        
        response = agent.run(enhanced_prompt)
        print(response.content if hasattr(response, 'content') else str(response))
        
        # Performance metrics
        execution_time = time.time() - start_time
        metrics = agent.get_performance_metrics()
        
        print(f"\n📊 **EXECUTION METRICS:**")
        print(f"├─ Query Execution Time: {execution_time:.2f}s")
        print(f"├─ Success Rate: {metrics.get('success_rate', 0):.1f}%")
        print(f"└─ Average Relevance: {metrics.get('avg_relevance_score', 0):.3f}")
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        print(f"❌ Critical Error: {str(e)}")
        print("Please check logs for detailed error information.")

# Production configuration example
PRODUCTION_CONFIG = {
    'model_id': 'gpt-4o',
    'temperature': 0.1,
    'max_tokens': 4000,
    'scoring_weights': {
        'relevance': 0.5,
        'recency': 0.3,
        'importance': 0.2
    },
    'show_tool_calls': True,
    'markdown': True,
    'reasoning': True
}

if __name__ == "__main__":
    # Example usage with production config
    query_hyperliquid_agent("What are people saying about HyperLiquid's vaults?", PRODUCTION_CONFIG)