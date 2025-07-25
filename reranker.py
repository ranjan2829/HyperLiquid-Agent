import cohere
import os
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from functools import wraps
import json

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class RerankingMetrics:
    """Track reranking performance metrics"""
    query: str
    original_count: int
    reranked_count: int
    avg_relevance_score: float
    execution_time: float
    model_used: str
    success: bool
    error: Optional[str] = None

class AdvancedCohereReranker:
    """Production-grade Cohere reranker with advanced accuracy optimizations"""
    
    def __init__(self, api_key: str = None, config: Optional[Dict[str, Any]] = None):
        """Initialize with production configurations"""
        self.api_key = api_key or os.getenv('COHERE_API_KEY')
        if not self.api_key:
            raise ValueError("Cohere API key is required. Set COHERE_API_KEY environment variable.")
        
        self.config = config or {}
        self.client = cohere.Client(self.api_key)
        self.metrics_history: List[RerankingMetrics] = []
        
        # Production settings
        self.model = self.config.get('model', 'rerank-english-v3.0')
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1.0)
        self.max_doc_length = self.config.get('max_doc_length', 1000)
        self.relevance_threshold = self.config.get('relevance_threshold', 0.1)
        
        logger.info(f"Initialized AdvancedCohereReranker with model: {self.model}")
    
    def retry_on_failure(self, max_retries: int = None):
        """Decorator for API retry logic"""
        max_retries = max_retries or self.max_retries
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except cohere.errors.CohereAPIError as e:
                        last_exception = e
                        logger.warning(f"Cohere API error (attempt {attempt + 1}/{max_retries}): {e}")
                        
                        if attempt < max_retries - 1:
                            wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.info(f"Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                    except Exception as e:
                        last_exception = e
                        logger.error(f"Unexpected error in reranking: {e}")
                        break
                
                raise last_exception
            return wrapper
        return decorator
    
    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = 15) -> List[Dict[str, Any]]:
        """High-accuracy reranking with advanced document processing"""
        
        if not results:
            logger.warning("No results provided for reranking")
            return []
        
        if not query or not query.strip():
            logger.error("Empty query provided for reranking")
            return results[:top_k]
        
        start_time = time.time()
        
        # Apply retry logic manually
        max_retries = self.max_retries
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Starting Cohere reranking: query='{query[:50]}...', results={len(results)}, top_k={top_k}")
                
                # Advanced document preparation
                documents, metadata_map = self._prepare_documents_for_reranking(results)
                
                if not documents:
                    logger.warning("No valid documents after preparation")
                    return results[:top_k]
                
                # Call Cohere rerank API with optimized parameters
                response = self._call_cohere_api(query, documents, top_k)
                
                # Process and enhance results
                reranked_results = self._process_rerank_response(response, results, metadata_map)
                
                # Calculate and store metrics
                execution_time = time.time() - start_time
                self._store_metrics(query, len(results), len(reranked_results), reranked_results, execution_time, True)
                
                logger.info(f"Reranking completed: {len(reranked_results)} results in {execution_time:.3f}s")
                return reranked_results
                
            except cohere.errors.CohereAPIError as e:
                last_exception = e
                logger.warning(f"Cohere API error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in reranking: {e}")
                break
        
        # If all retries failed, store error and return fallback
        execution_time = time.time() - start_time
        logger.error(f"Reranking failed after {max_retries} attempts: {last_exception}")
        
        # Store error metrics
        self._store_metrics(query, len(results), 0, [], execution_time, False, str(last_exception))
        
        # Fallback to original results
        logger.info("Falling back to original result order")
        return results[:top_k]
    
    def _prepare_documents_for_reranking(self, results: List[Dict[str, Any]]) -> Tuple[List[str], Dict[int, int]]:
        """Advanced document preparation with context optimization"""
        documents = []
        metadata_map = {}  # Maps document index to original result index
        
        for idx, result in enumerate(results):
            try:
                doc_text = self._create_rich_document_context(result)
                
                if doc_text and len(doc_text.strip()) > 10:  # Minimum content threshold
                    documents.append(doc_text)
                    metadata_map[len(documents) - 1] = idx
                else:
                    logger.debug(f"Skipping result {idx}: insufficient content")
                    
            except Exception as e:
                logger.warning(f"Error preparing document {idx}: {e}")
                continue
        
        logger.debug(f"Prepared {len(documents)} documents from {len(results)} results")
        return documents, metadata_map
    
    def _create_rich_document_context(self, result: Dict[str, Any]) -> str:
        """Create rich, contextual document for optimal Cohere reranking"""
        metadata = result.get('metadata', {})
        content_parts = []
        
        # Priority order for HyperLiquid context
        title = metadata.get('title', '').strip()
        if title:
            content_parts.append(f"TITLE: {title}")
        
        # Enhanced source context
        source = metadata.get('source_entity_name', '').strip()
        channel = metadata.get('channel_name', '').strip()
        if source:
            source_text = f"SOURCE: {source}"
            if channel and channel != source:
                source_text += f" ({channel})"
            content_parts.append(source_text)
        
        # Temporal context
        published_at = metadata.get('published_at', '').strip()
        if published_at:
            content_parts.append(f"DATE: {published_at}")
        
        # Summary with priority
        summary = metadata.get('summary', '').strip()
        if summary:
            content_parts.append(f"SUMMARY: {summary}")
        
        # Main content with intelligent truncation
        main_content = result.get('text', '').strip()
        if main_content:
            # Intelligent content truncation preserving key information
            truncated_content = self._intelligent_truncate(main_content, self.max_doc_length - len('\n'.join(content_parts)) - 20)
            content_parts.append(f"CONTENT: {truncated_content}")
        
        # HyperLiquid-specific enhancements
        hyperliquid_tokens = metadata.get('hyperliquid_tokens')
        if hyperliquid_tokens:
            try:
                if isinstance(hyperliquid_tokens, str):
                    tokens_data = json.loads(hyperliquid_tokens)
                else:
                    tokens_data = hyperliquid_tokens
                
                if tokens_data:
                    token_names = [token.get('name', '') for token in tokens_data if isinstance(token, dict)]
                    if token_names:
                        content_parts.append(f"TOKENS: {', '.join(token_names)}")
            except Exception:
                pass
        
        # URL for credibility context
        url = metadata.get('url', '').strip()
        if url and len(url) < 200:  # Reasonable URL length
            content_parts.append(f"URL: {url}")
        
        final_doc = '\n'.join(content_parts)
        
        # Final length check and truncation
        if len(final_doc) > self.max_doc_length:
            final_doc = final_doc[:self.max_doc_length - 3] + "..."
        
        return final_doc
    
    def _intelligent_truncate(self, text: str, max_length: int) -> str:
        """Intelligent text truncation preserving important information"""
        if len(text) <= max_length:
            return text
        
        # Try to truncate at sentence boundaries
        sentences = text.split('. ')
        truncated = ""
        
        for sentence in sentences:
            if len(truncated + sentence + '. ') <= max_length:
                truncated += sentence + '. '
            else:
                break
        
        if truncated:
            return truncated.rstrip()
        
        # Fallback: truncate at word boundaries
        words = text.split()
        truncated_words = []
        
        for word in words:
            if len(' '.join(truncated_words + [word])) <= max_length - 3:
                truncated_words.append(word)
            else:
                break
        
        return ' '.join(truncated_words) + "..."
    
    def _call_cohere_api(self, query: str, documents: List[str], top_k: int) -> Any:
        """Call Cohere API with optimized parameters"""
        
        # Determine optimal top_n
        top_n = min(top_k, len(documents))
        
        # Enhanced query for better matching
        enhanced_query = self._enhance_query_for_hyperliquid(query)
        
        logger.debug(f"Calling Cohere API: model={self.model}, query_len={len(enhanced_query)}, docs={len(documents)}, top_n={top_n}")
        
        response = self.client.rerank(
            model=self.model,
            query=enhanced_query,
            documents=documents,
            top_n=top_n,
            return_documents=True,
            max_chunks_per_doc=1,  # Optimize for single chunk per document
        )
        
        return response
    
    def _enhance_query_for_hyperliquid(self, query: str) -> str:
        """Enhance query with HyperLiquid context for better matching"""
        enhanced_query = query
        
        # Add HyperLiquid context if not present
        if 'hyperliquid' not in query.lower():
            enhanced_query = f"HyperLiquid {query}"
        
        # Add crypto/DeFi context
        crypto_keywords = ['DeFi', 'DEX', 'trading', 'liquidity', 'yield', 'vault', 'token']
        if not any(keyword.lower() in query.lower() for keyword in crypto_keywords):
            enhanced_query += " cryptocurrency DeFi"
        
        return enhanced_query
    
    def _process_rerank_response(self, response: Any, original_results: List[Dict[str, Any]], metadata_map: Dict[int, int]) -> List[Dict[str, Any]]:
        """Process Cohere response with advanced result enhancement"""
        reranked_results = []
        
        for rank_idx, result in enumerate(response.results):
            try:
                # Get original result using metadata mapping
                original_idx = metadata_map.get(result.index)
                if original_idx is None:
                    logger.warning(f"No mapping found for document index {result.index}")
                    continue
                
                original_result = original_results[original_idx].copy()
                
                # Enhanced scoring information
                relevance_score = float(result.relevance_score)
                
                # Skip results below relevance threshold
                if relevance_score < self.relevance_threshold:
                    logger.debug(f"Skipping result with low relevance: {relevance_score:.4f}")
                    continue
                
                # Add comprehensive Cohere metadata
                original_result.update({
                    'cohere_score': relevance_score,
                    'cohere_rank': rank_idx + 1,
                    'cohere_model': self.model,
                    'rerank_timestamp': time.time(),
                    'original_index': original_idx
                })
                
                # Add relevance categorization
                if relevance_score >= 0.8:
                    original_result['relevance_category'] = 'high'
                elif relevance_score >= 0.5:
                    original_result['relevance_category'] = 'medium'
                elif relevance_score >= 0.2:
                    original_result['relevance_category'] = 'low'
                else:
                    original_result['relevance_category'] = 'minimal'
                
                reranked_results.append(original_result)
                
            except Exception as e:
                logger.warning(f"Error processing rerank result {rank_idx}: {e}")
                continue
        
        logger.info(f"Processed {len(reranked_results)} reranked results from {len(response.results)} Cohere results")
        return reranked_results
    
    def _store_metrics(self, query: str, original_count: int, reranked_count: int, 
                      results: List[Dict[str, Any]], execution_time: float, 
                      success: bool, error: str = None):
        """Store comprehensive reranking metrics"""
        
        avg_relevance = 0.0
        if results and success:
            relevance_scores = [r.get('cohere_score', 0) for r in results]
            avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        
        metrics = RerankingMetrics(
            query=query[:100],  # Truncate for storage
            original_count=original_count,
            reranked_count=reranked_count,
            avg_relevance_score=avg_relevance,
            execution_time=execution_time,
            model_used=self.model,
            success=success,
            error=error
        )
        
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 metrics to prevent memory issues
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        logger.debug(f"Stored reranking metrics: success={success}, avg_relevance={avg_relevance:.4f}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance analytics"""
        if not self.metrics_history:
            return {"status": "No metrics available"}
        
        successful_reranks = [m for m in self.metrics_history if m.success]
        
        if not successful_reranks:
            return {"status": "No successful reranks"}
        
        # Calculate comprehensive metrics
        total_reranks = len(self.metrics_history)
        success_rate = len(successful_reranks) / total_reranks * 100
        
        avg_execution_time = sum(m.execution_time for m in successful_reranks) / len(successful_reranks)
        avg_relevance = sum(m.avg_relevance_score for m in successful_reranks) / len(successful_reranks)
        avg_original_count = sum(m.original_count for m in successful_reranks) / len(successful_reranks)
        avg_reranked_count = sum(m.reranked_count for m in successful_reranks) / len(successful_reranks)
        
        # Recent performance (last 50 reranks)
        recent_reranks = self.metrics_history[-50:]
        recent_success_rate = len([m for m in recent_reranks if m.success]) / len(recent_reranks) * 100
        
        return {
            "total_reranking_operations": total_reranks,
            "success_rate": success_rate,
            "recent_success_rate": recent_success_rate,
            "avg_execution_time": avg_execution_time,
            "avg_relevance_score": avg_relevance,
            "avg_input_results": avg_original_count,
            "avg_output_results": avg_reranked_count,
            "model_used": self.model,
            "relevance_threshold": self.relevance_threshold,
            "recent_errors": [m.error for m in self.metrics_history[-10:] if m.error],
            "high_relevance_queries": len([m for m in successful_reranks if m.avg_relevance_score > 0.7])
        }
    
    def _generate_results_output(self, query: str, ranked_results: List[Dict[str, Any]]) -> str:
        """Generate Result + Reason format with Cohere and recency-based ranking"""
        
        if not ranked_results:
            return f"🔍 **RESULT:** No relevant information found for: {query}\n\n**REASON:** Search yielded no matches meeting relevance threshold."
        
        # Calculate enhanced hybrid scores combining Cohere relevance + recency
        scored_results = self._calculate_hybrid_scores(ranked_results)
        
        # Sort by hybrid score (Cohere + recency weight)
        final_results = sorted(scored_results, key=lambda x: x.get('final_score', 0), reverse=True)
        
        output = f"🔍 **RESULT:** Found {len(final_results)} relevant mentions about: {query}\n\n"
        
        # Add comprehensive reasoning
        output += f"**REASON:**\n"
        output += f"• Analyzed {len(ranked_results)} sources using Cohere {self.model}\n"
        
        # Cohere relevance analysis
        high_cohere = [r for r in final_results if r.get('cohere_score', 0) > 0.7]
        medium_cohere = [r for r in final_results if 0.4 <= r.get('cohere_score', 0) <= 0.7]
        
        output += f"• High relevance (>0.7): {len(high_cohere)} sources\n"
        output += f"• Medium relevance (0.4-0.7): {len(medium_cohere)} sources\n"
        
        # Recency analysis
        recent_30d = [r for r in final_results if r.get('days_ago', 999) <= 30]
        recent_7d = [r for r in final_results if r.get('days_ago', 999) <= 7]
        
        output += f"• Recent mentions (30 days): {len(recent_30d)} sources\n"
        output += f"• Very recent (7 days): {len(recent_7d)} sources\n"
        
        # Average scores
        avg_cohere = sum(r.get('cohere_score', 0) for r in final_results) / len(final_results)
        avg_final = sum(r.get('final_score', 0) for r in final_results) / len(final_results)
        
        output += f"• Average Cohere relevance: {avg_cohere:.3f}\n"
        output += f"• Average final score: {avg_final:.3f}\n\n"
        
        # Top sources with individual reasoning
        output += "📋 **TOP SOURCES:**\n\n"
        
        for i, result in enumerate(final_results[:5], 1):
            metadata = result.get('metadata', {})
            
            output += f"**#{i} - {metadata.get('title', 'No Title')}**\n"
            output += f"Source: {metadata.get('source_entity_name', 'Unknown')}\n"
            output += f"Published: {metadata.get('published_at', 'Unknown')}\n"
            
            # Individual result reasoning
            cohere_score = result.get('cohere_score', 0)
            days_ago = result.get('days_ago', 999)
            final_score = result.get('final_score', 0)
            
            output += f"Cohere Relevance: {cohere_score:.3f}\n"
            if days_ago < 999:
                output += f"Recency: {days_ago} days ago\n"
            output += f"Final Score: {final_score:.3f}\n"
            
            # Reasoning for this specific result
            output += f"**Reason Selected:** "
            if cohere_score > 0.7:
                output += "High semantic relevance"
            elif cohere_score > 0.4:
                output += "Good semantic relevance"
            else:
                output += "Moderate relevance"
                
            if days_ago <= 7:
                output += " + Very recent information"
            elif days_ago <= 30:
                output += " + Recent information"
                
            output += f"\n\nSnippet: {result.get('text', '')[:200]}...\n"
            
            url = metadata.get('url', '')
            if url:
                output += f"URL: {url}\n"
            output += "\n" + "─" * 50 + "\n\n"
        
        return output
    
    def _calculate_hybrid_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate hybrid scores combining Cohere relevance + recency for optimal accuracy"""
        scored_results = []
        
        for result in results:
            result_copy = result.copy()
            
            # Get Cohere relevance score (primary factor)
            cohere_score = result.get('cohere_score', 0.0)
            
            # Calculate recency score from metadata
            recency_score = self._calculate_recency_score(result.get('metadata', {}))
            
            # Calculate days ago for display
            days_ago = self._extract_days_ago(result.get('metadata', {}))
            result_copy['days_ago'] = days_ago
            
            # Hybrid scoring: 70% Cohere relevance + 30% recency
            # This emphasizes semantic relevance while boosting recent content
            final_score = (cohere_score * 0.7) + (recency_score * 0.3)
            
            # Boost score for very high Cohere relevance (>0.8)
            if cohere_score > 0.8:
                final_score += 0.1
                
            # Boost score for very recent content (<7 days)
            if days_ago <= 7:
                final_score += 0.05
            
            result_copy['recency_score'] = recency_score
            result_copy['final_score'] = final_score
            
            scored_results.append(result_copy)
        
        return scored_results
    
    def _calculate_recency_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate recency score with exponential decay for optimal time weighting"""
        import datetime
        
        published_at = metadata.get('published_at', '')
        if not published_at:
            return 0.1  # Low score for unknown dates
        
        try:
            # Parse different date formats
            date_formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            published_date = None
            for fmt in date_formats:
                try:
                    published_date = datetime.datetime.strptime(published_at.split('T')[0] if 'T' in published_at else published_at, fmt.split(' ')[0] if ' ' in fmt else fmt)
                    break
                except ValueError:
                    continue
            
            if not published_date:
                return 0.1
            
            # Calculate days difference
            days_ago = (datetime.datetime.now() - published_date).days
            
            # Exponential decay scoring: newer = higher score
            if days_ago <= 1:
                return 1.0  # Today/yesterday
            elif days_ago <= 7:
                return 0.9  # This week
            elif days_ago <= 30:
                return 0.7  # This month
            elif days_ago <= 90:
                return 0.5  # Last 3 months
            elif days_ago <= 365:
                return 0.3  # This year
            else:
                return 0.1  # Older than a year
                
        except Exception as e:
            logger.debug(f"Error calculating recency score: {e}")
            return 0.1
    
    def _extract_days_ago(self, metadata: Dict[str, Any]) -> int:
        """Extract days ago for display purposes"""
        import datetime
        
        published_at = metadata.get('published_at', '')
        if not published_at:
            return 999  # Unknown date indicator
        
        try:
            date_formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            published_date = None
            for fmt in date_formats:
                try:
                    published_date = datetime.datetime.strptime(published_at.split('T')[0] if 'T' in published_at else published_at, fmt.split(' ')[0] if ' ' in fmt else fmt)
                    break
                except ValueError:
                    continue
            
            if published_date:
                return (datetime.datetime.now() - published_date).days
            
        except Exception:
            pass
        
        return 999

    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = 15) -> List[Dict[str, Any]]:
        """Enhanced reranking with Cohere + recency optimization"""
        
        if not results:
            logger.warning("No results provided for reranking")
            return []
        
        if not query or not query.strip():
            logger.error("Empty query provided for reranking")
            return results[:top_k]
        
        start_time = time.time()
        
        # Apply retry logic for Cohere API
        max_retries = self.max_retries
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Starting enhanced Cohere reranking: query='{query[:50]}...', results={len(results)}, top_k={top_k}")
                
                # Prepare documents for Cohere
                documents, metadata_map = self._prepare_documents_for_reranking(results)
                
                if not documents:
                    logger.warning("No valid documents after preparation")
                    return results[:top_k]
                
                # Get Cohere reranking
                response = self._call_cohere_api(query, documents, top_k)
                
                # Process results with Cohere scores
                cohere_results = self._process_rerank_response(response, results, metadata_map)
                
                # Apply hybrid scoring (Cohere + recency)
                scored_results = self._calculate_hybrid_scores(cohere_results)
                
                # Final ranking by hybrid score
                final_results = sorted(scored_results, key=lambda x: x.get('final_score', 0), reverse=True)[:top_k]
                
                # Store metrics
                execution_time = time.time() - start_time
                self._store_metrics(query, len(results), len(final_results), final_results, execution_time, True)
                
                logger.info(f"Enhanced reranking completed: {len(final_results)} results in {execution_time:.3f}s")
                return final_results
                
            except cohere.errors.CohereAPIError as e:
                last_exception = e
                logger.warning(f"Cohere API error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in reranking: {e}")
                break
        
        # Fallback with basic recency sorting
        execution_time = time.time() - start_time
        logger.error(f"Reranking failed, using recency fallback: {last_exception}")
        
        # Store error metrics
        self._store_metrics(query, len(results), 0, [], execution_time, False, str(last_exception))
        
        # Fallback: sort by recency only
        fallback_results = self._fallback_recency_sort(results)
        return fallback_results[:top_k]
    
    def _fallback_recency_sort(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback sorting by recency when Cohere fails"""
        scored_results = []
        
        for result in results:
            result_copy = result.copy()
            recency_score = self._calculate_recency_score(result.get('metadata', {}))
            result_copy['recency_score'] = recency_score
            result_copy['final_score'] = recency_score  # Use recency as final score
            scored_results.append(result_copy)
        
        return sorted(scored_results, key=lambda x: x.get('final_score', 0), reverse=True)

# Backward compatibility
class SimpleReranker(AdvancedCohereReranker):
    """Backward compatible simple reranker"""
    
    def __init__(self, api_key: str = None):
        super().__init__(api_key)

# Production configuration
PRODUCTION_RERANKER_CONFIG = {
    'model': 'rerank-english-v3.0',
    'max_retries': 3,
    'retry_delay': 1.0,
    'max_doc_length': 1000,
    'relevance_threshold': 0.1
}

if __name__ == "__main__":
    # Example usage and testing
    reranker = AdvancedCohereReranker(config=PRODUCTION_RERANKER_CONFIG)
    
    # Test with sample data
    sample_results = [
        {
            'text': 'HyperLiquid DEX shows strong trading volume growth',
            'metadata': {
                'title': 'HyperLiquid Volume Surge',
                'source_entity_name': 'CoinDesk'
            }
        }
    ]
    
    reranked = reranker.rerank("HyperLiquid trading volume", sample_results)
    print(f"Reranked {len(reranked)} results")
    
    # Show performance metrics
    metrics = reranker.get_performance_metrics()
    print(f"Performance metrics: {metrics}")