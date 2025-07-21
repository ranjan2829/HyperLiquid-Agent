'use client';

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api';
import { SearchResponse } from '@/types/api';
import { Zap, Star, ExternalLink, Calendar, Clock, Activity, Search, Loader2, ArrowUp, Command, Database, Brain } from 'lucide-react';

export default function Home() {
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchStartTime, setSearchStartTime] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState(-1);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Real-time timer update
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (searchStartTime) {
      interval = setInterval(() => {
        // Force re-render to update timer
      }, 100);
    }
    return () => clearInterval(interval);
  }, [searchStartTime]);

  // Focus search on cmd+k
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;
    
    setIsLoading(true);
    setError(null);
    setSearchResults(null);
    setSearchStartTime(Date.now());
    setShowSuggestions(false);

    try {
      const results = await apiClient.search({
        query: searchQuery,
        top_k: 15,
        output_format: 'detailed'
      });
      setSearchResults(results);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
      setSearchStartTime(null);
    }
  };

  const getElapsedTime = () => {
    if (!searchStartTime) return 0;
    return ((Date.now() - searchStartTime) / 1000).toFixed(1);
  };

  const formatText = (text: string) => {
    if (!text) return '';
    
    return text
      // Main headers: ### text -> <h3>
      .replace(/^### (.*$)/gm, '<h3 class="text-2xl font-bold text-green-300 mt-8 mb-4 border-b-2 border-green-500/40 pb-3 flex items-center"><span class="bg-green-500/20 p-2 rounded-lg mr-3">🔍</span>$1</h3>')
      
      // Sub headers: #### text -> <h4>
      .replace(/^#### (.*$)/gm, '<h4 class="text-xl font-bold text-green-400 mt-6 mb-3 flex items-center"><span class="text-green-500 mr-2">▶</span>$1</h4>')
      
      // Sub-sub headers: ##### text -> <h5>
      .replace(/^##### (.*$)/gm, '<h5 class="text-lg font-semibold text-green-300 mt-4 mb-2 flex items-center"><span class="text-green-400 mr-2">•</span>$1</h5>')
      
      // Bold text: **text** -> <strong>
      .replace(/\*\*(.*?)\*\*/g, '<span class="text-green-300 font-bold bg-green-500/10 px-1 rounded">$1</span>')
      
      // Numbered lists: 1. text -> formatted list
      .replace(/^(\d+)\. (.*$)/gm, '<div class="flex items-start mb-3 ml-6"><span class="bg-green-500/20 text-green-300 px-2 py-1 rounded-full text-sm font-bold min-w-[2rem] text-center mr-3">$1</span><span class="text-gray-300 leading-relaxed">$2</span></div>')
      
      // Bullet points: - text -> formatted list
      .replace(/^- (.*$)/gm, '<div class="flex items-start mb-2 ml-4"><span class="text-green-400 mr-3 font-bold text-lg">•</span><span class="text-gray-300 leading-relaxed">$1</span></div>')
      
      // Confidence levels: **High Confidence** etc.
      .replace(/\*\*(High Confidence|Medium Confidence|Low Confidence)\*\*/g, '<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-bold bg-green-500/20 text-green-300 border border-green-400/30">$1</span>')
      
      // Sentiment indicators
      .replace(/\*\*(Bullish|Bearish|Neutral)\*\*/g, '<span class="inline-flex items-center px-2 py-1 rounded text-sm font-bold bg-blue-500/20 text-blue-300">$1</span>')
      
      // Risk indicators
      .replace(/\*\*(Risk|Warning|Concern)\*\*/g, '<span class="inline-flex items-center px-2 py-1 rounded text-sm font-bold bg-red-500/20 text-red-300">⚠️ $1</span>')
      
      // Opportunity indicators
      .replace(/\*\*(Opportunity|Bullish|Positive)\*\*/g, '<span class="inline-flex items-center px-2 py-1 rounded text-sm font-bold bg-green-500/20 text-green-300">📈 $1</span>')
      
      // Links: [text](url) -> clickable links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-green-400 hover:text-green-300 underline font-medium">$1 <span class="text-xs">↗</span></a>')
      
      // Result references: Result #1, Result #2, etc.
      .replace(/(Result #\d+)/g, '<span class="bg-green-500/20 text-green-300 px-2 py-1 rounded-md text-sm font-mono">$1</span>')
      
      // Code/emphasis: `text` -> highlighted
      .replace(/`([^`]+)`/g, '<code class="bg-gray-800 text-green-300 px-2 py-1 rounded text-sm font-mono border border-green-500/30">$1</code>')
      
      // Metrics and percentages
      .replace(/(\d+(?:\.\d+)?%)/g, '<span class="text-green-300 font-bold bg-green-500/10 px-1 rounded">$1</span>')
      .replace(/(\$\d+(?:,\d{3})*(?:\.\d{2})?[KMB]?)/g, '<span class="text-green-300 font-bold bg-green-500/10 px-1 rounded">$1</span>')
      
      // Horizontal dividers: ---
      .replace(/^---$/gm, '<hr class="border-green-500/30 my-6" />')
      
      // Executive Summary box
      .replace(/\*\*Executive Summary:\*\*/g, '<div class="bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-400/30 rounded-xl p-4 my-6"><h4 class="text-lg font-bold text-green-300 mb-3 flex items-center"><span class="mr-2">📋</span>Executive Summary</h4>')
      
      // Overall Assessment box
      .replace(/\*\*Overall Assessment:\*\*/g, '<div class="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-400/30 rounded-xl p-4 my-6"><h4 class="text-lg font-bold text-blue-300 mb-3 flex items-center"><span class="mr-2">🎯</span>Overall Assessment</h4>')
      
      // Double line breaks for paragraphs
      .replace(/\n\n/g, '</p><p class="mb-4 text-gray-300 leading-relaxed">')
      
      // Single line breaks
      .replace(/\n/g, '<br />')
      
      // Wrap in paragraph tags
      .replace(/^(.+)/, '<p class="mb-4 text-gray-300 leading-relaxed">$1')
      .replace(/(.+)$/, '$1</p>');
  };

  const formatContentText = (text: string) => {
    if (!text) return text;
    
    return text
      .replace(/\*\*(.*?)\*\*/g, '<span class="text-green-300 font-semibold">$1</span>')
      .replace(/^• (.*$)/gm, '<div class="flex items-start mb-1"><span class="text-green-400 mr-2">•</span><span>$1</span></div>')
      .replace(/\n/g, '<br />');
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-300 bg-green-500/20';
    if (score >= 0.6) return 'text-yellow-300 bg-yellow-500/20';
    return 'text-red-300 bg-red-500/20';
  };

  const suggestions = [
    "What are people saying about HyperLiquid's vaults?",
    "HYPE token price sentiment analysis",
    "Recent influencer mentions of HyperLiquid",
    "HyperLiquid trading volume trends",
    "Market maker activity on HyperLiquid",
    "HyperLiquid DEX performance analysis",
    "Liquidity mining rewards on HyperLiquid",
    "HyperLiquid vs other DEXs comparison",
    "Recent HyperLiquid partnerships and integrations",
    "HYPE token staking and rewards"
  ];

  const filteredSuggestions = suggestions.filter(suggestion =>
    suggestion.toLowerCase().includes(query.toLowerCase()) && 
    suggestion.toLowerCase() !== query.toLowerCase()
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (selectedSuggestion >= 0 && filteredSuggestions[selectedSuggestion]) {
        const selectedQuery = filteredSuggestions[selectedSuggestion];
        setQuery(selectedQuery);
        handleSearch(selectedQuery);
      } else {
        handleSearch(query);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedSuggestion(prev => 
        prev < filteredSuggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedSuggestion(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setSelectedSuggestion(-1);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setShowSuggestions(value.length > 0);
    setSelectedSuggestion(-1);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    handleSearch(suggestion);
  };

  const exampleQueries = [
    "What are people saying about HyperLiquid's vaults?",
    "Did anyone mention HYPE token and risk in the same sentence?",
    "Any influencer tweets about HyperLiquid recently?",
  ];

  return (
    <div className="h-screen bg-black flex flex-col font-mono">
      {/* Fixed Header - No Shrinking */}
      <header className="bg-black/95 backdrop-blur-xl border-b border-green-500/20 px-8 py-4 flex items-center justify-between relative overflow-hidden min-h-[80px]">
        {/* Background Gradient */}
        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 via-blue-500/5 to-green-500/5"></div>
        
        {/* Left Section - Brand */}
        <div className="flex items-center space-x-4 relative z-10">
          {/* Sexy Logo Alternative - No SVG */}
          <div className="relative">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 via-blue-500 to-green-500 rounded-xl shadow-lg shadow-purple-500/30 transform hover:scale-105 transition-all duration-300 flex items-center justify-center border border-purple-500/30">
              <div className="text-2xl font-bold text-black">H</div>
            </div>
          </div>
          
          {/* Brand Text */}
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 via-blue-400 to-green-400 bg-clip-text text-transparent">
              HyperLiquid Intelligence
            </h1>
            <div className="flex items-center space-x-3 mt-1">
              <div className="flex items-center space-x-1">
                <Brain className="h-3 w-3 text-purple-400" />
                <span className="text-gray-400 text-xs">AI-powered market analysis</span>
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-purple-500/10 border border-purple-500/30 rounded-full">
                <div className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
                <span className="text-purple-400 text-xs font-mono">v2.0</span>
              </div>
              <div className="flex items-center space-x-1 px-2 py-1 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-full">
                <span className="text-purple-400 text-xs font-mono">Official</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Center Section - Search Bar */}
        <div className="flex-1 max-w-2xl mx-8 relative">
          <div className="relative">
            <div className="absolute left-4 top-1/2 transform -translate-y-1/2">
              <Search className="h-5 w-5 text-gray-500" />
            </div>
            
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onFocus={() => setShowSuggestions(query.length > 0)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder="Ask about HyperLiquid markets, vaults, sentiment, or trading..."
              className="w-full bg-gray-900/70 border-2 border-green-500/30 rounded-xl pl-12 pr-20 py-3 text-green-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-green-400 transition-all duration-300"
              disabled={isLoading}
            />
            
            <div className="absolute right-16 top-1/2 transform -translate-y-1/2 flex items-center space-x-1 text-gray-500 text-xs">
              <Command className="h-3 w-3" />
              <span className="font-mono">K</span>
            </div>
            
            <button
              onClick={() => handleSearch(query)}
              disabled={isLoading || !query.trim()}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 bg-gradient-to-r from-green-500 to-emerald-500 text-black rounded-lg hover:from-green-400 hover:to-emerald-400 disabled:opacity-50 disabled:pointer-events-none transition-all duration-300"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowUp className="h-4 w-4 rotate-90" />
              )}
            </button>

            {/* Search Suggestions */}
            {showSuggestions && filteredSuggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-gray-900/95 backdrop-blur-xl border border-green-500/30 rounded-xl shadow-2xl z-50 max-h-80 overflow-y-auto">
                <div className="p-2">
                  <div className="text-xs text-gray-400 px-3 py-2 font-medium flex items-center">
                    <Zap className="h-3 w-3 mr-2 text-green-400" />
                    Smart Suggestions
                  </div>
                  {filteredSuggestions.slice(0, 8).map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className={`w-full text-left px-3 py-3 rounded-lg transition-all duration-200 ${
                        selectedSuggestion === index
                          ? 'bg-green-500/20 text-green-300 border border-green-500/40'
                          : 'text-gray-300 hover:bg-green-500/10 hover:text-green-300'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <Search className="h-4 w-4 text-green-400" />
                        <span className="text-sm">{suggestion}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Section - Status */}
        <div className="flex items-center space-x-4 relative z-10">
          {/* AI Status */}
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <div className="text-xs">
              <div className="text-green-400 font-medium">AI Active</div>
            </div>
          </div>
          
          {/* Data Pipeline */}
          <div className="flex items-center space-x-2 px-3 py-1 bg-green-500/10 border border-green-500/30 rounded-lg">
            <Database className="h-3 w-3 text-green-400" />
            <span className="text-green-400 text-xs font-mono">Live</span>
          </div>
        </div>
      </header>

      {/* Quick Actions - Fixed Height */}
      <div className="bg-black/80 border-b border-green-500/10 px-8 py-3 min-h-[60px] flex items-center">
        <div className="flex items-center space-x-3 flex-wrap">
          <span className="text-gray-400 text-sm font-medium flex items-center">
            <Zap className="h-4 w-4 mr-2 text-green-400" />
            Quick searches:
          </span>
          {exampleQueries.map((example, index) => (
            <button
              key={index}
              onClick={() => {
                setQuery(example);
                handleSearch(example);
              }}
              disabled={isLoading}
              className="px-3 py-1.5 bg-green-500/10 text-green-300 rounded-lg hover:bg-green-500/20 transition-all disabled:opacity-50 border border-green-500/20 text-xs font-medium whitespace-nowrap"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content - Takes remaining space */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* AI Analysis Panel - Left */}
        <div className="w-1/2 bg-black/90 border-r border-green-500/20 flex flex-col">
          <div className="p-4 border-b border-green-500/20 bg-black/50">
            <h2 className="text-lg font-bold text-green-300 flex items-center">
              <Zap className="h-4 w-4 mr-2" />
              AI Analysis
            </h2>
          </div>
          
          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="h-full flex flex-col items-center justify-center p-8">
                <div className="relative mb-6">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-green-500/30"></div>
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-green-400 border-t-transparent absolute top-0"></div>
                  <Brain className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 h-5 w-5 text-green-400" />
                </div>
                <div className="text-center space-y-2">
                  <p className="text-green-300 font-bold">Analyzing Market Intelligence</p>
                  <p className="text-gray-400 text-sm">TurboPuffer + Cohere + GPT-4</p>
                  {searchStartTime && (
                    <div className="flex items-center justify-center space-x-2 text-green-400">
                      <Clock className="h-4 w-4" />
                      <span className="font-mono">{getElapsedTime()}s</span>
                    </div>
                  )}
                  <p className="text-yellow-400 text-xs">
                    ⚡ Complex analysis takes 30-60 seconds
                  </p>
                </div>
              </div>
            ) : searchResults?.ai_analysis ? (
              <div className="h-full overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-green-500/20 scrollbar-track-transparent">
                <div 
                  className="prose prose-sm max-w-none leading-relaxed text-gray-300"
                  dangerouslySetInnerHTML={{
                    __html: formatText(searchResults.ai_analysis)
                  }}
                />
              </div>
            ) : error ? (
              <div className="h-full flex items-center justify-center p-8">
                <div className="text-center">
                  <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center mb-4 mx-auto">
                    <Activity className="h-6 w-6 text-red-400" />
                  </div>
                  <h3 className="text-red-300 font-bold mb-2">Analysis Failed</h3>
                  <p className="text-red-200 text-sm">{error}</p>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center p-8">
                <div className="text-center max-w-md">
                  <div className="w-16 h-16 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-full flex items-center justify-center mb-4 mx-auto border border-green-400/30">
                    <Zap className="h-8 w-8 text-green-400" />
                  </div>
                  <h3 className="text-lg font-bold text-green-300 mb-2">
                    Ready for Deep Analysis
                  </h3>
                  <p className="text-gray-400 text-sm leading-relaxed">
                    Enter a query to get comprehensive AI-powered market intelligence with sentiment analysis and trend insights.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Source Documents Panel - Right */}
        <div className="w-1/2 bg-black/95 flex flex-col">
          <div className="p-4 border-b border-green-500/20 bg-black/50 flex items-center justify-between">
            <h2 className="text-lg font-bold text-green-300 flex items-center">
              <Star className="h-4 w-4 mr-2" />
              Sources
              {searchResults && (
                <span className="ml-2 px-2 py-1 bg-green-500/20 text-green-300 rounded-full text-xs">
                  {searchResults.results.length}
                </span>
              )}
            </h2>
            {searchResults && (
              <div className="text-xs text-gray-400">
                {searchResults.execution_time.toFixed(1)}s • Cohere ranked
              </div>
            )}
          </div>
          
          <div className="flex-1 overflow-hidden">
            {searchResults?.results && searchResults.results.length > 0 ? (
              <div className="h-full overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-green-500/20 scrollbar-track-transparent">
                {searchResults.results.map((result, index) => (
                  <div
                    key={result.id}
                    className="bg-gray-900/50 border border-green-500/20 rounded-lg p-3 hover:border-green-400/40 transition-all duration-200 group"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="bg-green-500/20 text-green-300 px-2 py-1 rounded-full text-xs font-bold">
                            #{index + 1}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-bold ${getScoreColor(result.cohere_score)}`}>
                            {result.cohere_score.toFixed(3)}
                          </span>
                        </div>
                        
                        <h4 className="text-sm font-bold text-green-200 mb-2 leading-tight">
                          {result.title || 'Untitled'}
                        </h4>
                        
                        <div className="flex items-center space-x-2 text-xs text-gray-400 mb-2">
                          <span className="flex items-center">
                            <Calendar className="h-3 w-3 mr-1" />
                            {formatDate(result.published_at)}
                          </span>
                          <span className="text-green-400 font-medium">{result.source}</span>
                          <span>{result.days_ago}d ago</span>
                        </div>
                      </div>
                      
                      {result.url && (
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 text-green-400 hover:text-green-300 hover:bg-green-500/10 rounded transition-all opacity-0 group-hover:opacity-100"
                          title="Open source"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    
                    <div className="bg-black/30 rounded p-2">
                      <div 
                        className="text-gray-300 text-xs leading-relaxed"
                        dangerouslySetInnerHTML={{
                          __html: formatContentText(result.content.length > 120 ? result.content.substring(0, 120) + '...' : result.content)
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : !isLoading && !error ? (
              <div className="h-full flex items-center justify-center p-8">
                <div className="text-center max-w-md">
                  <div className="w-16 h-16 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-full flex items-center justify-center mb-4 mx-auto border border-green-400/30">
                    <Star className="h-8 w-8 text-green-400" />
                  </div>
                  <h3 className="text-lg font-bold text-green-300 mb-2">
                    Source Documents
                  </h3>
                  <p className="text-gray-400 text-sm leading-relaxed">
                    Ranked source documents from HyperLiquid ecosystem will appear here after your search.
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Footer Status Bar - Fixed Height */}
      <footer className="bg-black/95 border-t border-green-500/20 px-8 py-2 min-h-[40px] flex items-center justify-between">
        <div className="text-gray-400 flex items-center space-x-2 text-xs">
          <span>TurboPuffer + Cohere + OpenAI GPT-4 • Real-time Market Intelligence</span>
        </div>
      </footer>
    </div>
  );
}
