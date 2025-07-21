'use client';

import { SearchResponse } from '@/types/api';
import { ExternalLink, Calendar, Zap, Star, Clock } from 'lucide-react';

interface SearchResultsProps {
  data: SearchResponse;
}

// Enhanced helper function to format markdown-like text
const formatText = (text: string) => {
  if (!text) return '';
  
  const formatted = text
    // Headers: ### text -> <h3>text</h3>
    .replace(/^### (.*$)/gm, '<h3 class="text-xl font-bold text-green-300 mt-6 mb-3 border-b border-green-500/30 pb-2">$1</h3>')
    .replace(/^#### (.*$)/gm, '<h4 class="text-lg font-bold text-green-400 mt-4 mb-2">$1</h4>')
    
    // Bold text: **text** -> <strong>text</strong>
    .replace(/\*\*(.*?)\*\*/g, '<span class="text-green-300 font-bold">$1</span>')
    
    // Bullet points: • text -> formatted list
    .replace(/^• (.*$)/gm, '<div class="flex items-start mb-2 ml-4"><span class="text-green-400 mr-3 font-bold">•</span><span class="text-gray-300">$1</span></div>')
    
    // Numbers: 1. text -> formatted list  
    .replace(/^(\d+)\. (.*$)/gm, '<div class="flex items-start mb-2 ml-4"><span class="text-green-400 mr-3 font-bold min-w-[1.5rem]">$1.</span><span class="text-gray-300">$2</span></div>')
    
    // Links: [text](url) -> clickable links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-green-400 hover:text-green-300 underline">$1</a>')
    
    // Source attribution: [Source, Date, Result #X](url)
    .replace(/\[([^,]+),\s*([^,]+),\s*([^\]]+)\]\(([^)]+)\)/g, '<a href="$4" target="_blank" rel="noopener noreferrer" class="text-green-400 hover:text-green-300 underline text-sm">[$1, $2, $3]</a>')
    
    // Code/emphasis: `text` -> highlighted
    .replace(/`([^`]+)`/g, '<code class="bg-green-500/20 text-green-300 px-1 py-0.5 rounded text-sm">$1</code>')
    
    // Double line breaks for paragraphs
    .replace(/\n\n/g, '</p><p class="mb-4 text-gray-300">')
    
    // Single line breaks
    .replace(/\n/g, '<br />')
    
    // Wrap in paragraph tags
    .replace(/^(.+)/, '<p class="mb-4 text-gray-300">$1')
    .replace(/(.+)$/, '$1</p>');
    
  return formatted;
};

// Helper function to format content text specifically
const formatContentText = (text: string) => {
  if (!text) return text;
  
  return text
    // Bold text
    .replace(/\*\*(.*?)\*\*/g, '<span class="text-green-300 font-semibold">$1</span>')
    // Bullet points
    .replace(/^• (.*$)/gm, '<div class="flex items-start mb-1"><span class="text-green-400 mr-2">•</span><span>$1</span></div>')
    // Line breaks
    .replace(/\n/g, '<br />');
};

export default function SearchResults({ data }: SearchResultsProps) {
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

  return (
    <div className="space-y-6">
      {/* Clean Search Header */}
      <div className="bg-black/40 border border-green-500/30 rounded-2xl p-6 backdrop-blur-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-green-300">
            &quot;{data.query}&quot;
          </h2>
          <div className="flex items-center space-x-4 text-sm">
            <span className="text-green-400">{data.results.length} results</span>
            <span className="text-gray-400 flex items-center">
              <Clock className="h-4 w-4 mr-1" />
              {data.execution_time.toFixed(1)}s
            </span>
          </div>
        </div>
      </div>

      {/* Side by Side Layout: AI Analysis + Search Results */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        {/* AI Analysis Panel - Left Side */}
        {data.ai_analysis && (
          <div className="bg-black/40 border border-green-500/30 rounded-2xl p-6 backdrop-blur-xl">
            <h3 className="text-xl font-bold text-green-300 mb-4 flex items-center">
              <Zap className="h-5 w-5 mr-3" />
              AI Analysis
            </h3>
            <div className="bg-black/20 rounded-xl p-6 max-h-[700px] overflow-y-auto scrollbar-thin scrollbar-thumb-green-500/20 scrollbar-track-transparent">
              <div 
                className="prose prose-sm max-w-none leading-relaxed [&>p]:text-gray-300 [&>h3]:text-green-300 [&>h4]:text-green-400 [&>div]:text-gray-300"
                dangerouslySetInnerHTML={{
                  __html: formatText(data.ai_analysis)
                }}
              />
            </div>
          </div>
        )}

        {/* Source Documents Panel - Right Side */}
        <div className="bg-black/40 border border-green-500/30 rounded-2xl p-6 backdrop-blur-xl">
          <h3 className="text-xl font-bold text-green-300 mb-4 flex items-center">
            <Star className="h-5 w-5 mr-3" />
            Sources
          </h3>
          
          {/* Clean Results List */}
          <div className="space-y-4">
            {data.results.map((result, index) => (
              <div
                key={result.id}
                className="bg-gray-900/70 border border-green-500/20 rounded-xl p-4 hover:shadow-2xl transition-all duration-200 hover:border-green-400/40 backdrop-blur-sm"
              >
                {/* Result Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="bg-green-500/20 text-green-300 px-2 py-1 rounded-full text-xs font-bold border border-green-400/30">
                        #{index + 1}
                      </span>
                      <span className={`px-2 py-1 rounded-full border text-xs font-medium ${getScoreColor(result.cohere_score)}`}>
                        {result.cohere_score.toFixed(3)}
                      </span>
                    </div>
                    
                    <h4 className="text-base font-semibold text-green-200 mb-2 leading-tight line-clamp-2">
                      {result.title || 'Untitled'}
                    </h4>
                    
                    <div className="flex items-center space-x-3 text-xs text-gray-400 mb-3">
                      <span className="flex items-center">
                        <Calendar className="h-3 w-3 mr-1" />
                        {formatDate(result.published_at)}
                      </span>
                      <span>
                        <span className="text-green-400">Source:</span> {result.source}
                      </span>
                      <span className="text-gray-500">
                        {result.days_ago}d ago
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-1 ml-2">
                    {result.url && (
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 text-green-400 hover:text-green-300 hover:bg-green-500/10 rounded-lg transition-colors border border-green-500/20 hover:border-green-400/40"
                        title="Open source"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </div>
                
                {/* Content */}
                <div className="bg-gray-800/50 rounded-lg p-3 border border-green-500/20">
                  <div 
                    className="text-gray-300 text-xs leading-relaxed [&>div]:mb-1 line-clamp-4"
                    dangerouslySetInnerHTML={{
                      __html: formatContentText(result.content.length > 200 ? result.content.substring(0, 200) + '...' : result.content)
                    }}
                  />
                </div>
                
                {/* Result Footer */}
                <div className="mt-2 pt-2 border-t border-green-500/20 flex items-center justify-between text-xs">
                  <span className="text-gray-500">ID: {result.id.split('_')[1]}</span>
                  <span className="text-green-400 font-medium">#{index + 1}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Search Summary Footer */}
      <div className="bg-green-500/20 border border-green-400/30 rounded-xl p-4 text-center">
        <p className="text-green-300 text-sm font-medium">
          <span className="text-green-200 font-bold">Search completed successfully!</span> 
          {' '}Analyzed {data.results.length} results from TurboPuffer + Cohere reranking + OpenAI GPT-4 analysis.
        </p>
        <p className="text-green-400 text-xs mt-1">
          Data pipeline: Vector Search → Cohere Reranking → AI Analysis → Frontend Display
        </p>
      </div>
    </div>
  );
}