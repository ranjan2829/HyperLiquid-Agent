'use client';

import { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

interface SearchFormProps {
  onSearch: (query: string, topK: number) => void;
  isLoading: boolean;
}

export default function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(15);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), topK);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex flex-col space-y-2">
        <label htmlFor="query" className="text-sm font-medium text-green-300">
          Search Query
        </label>
        <div className="relative">
          <input
            id="query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about HyperLiquid markets, vaults, or sentiment..."
            className="w-full px-4 py-3 pr-12 bg-gray-800/50 border border-green-500/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-green-400 text-green-200 placeholder-gray-500"
            disabled={isLoading}
          />
          <Search className="absolute right-3 top-3 h-5 w-5 text-green-400" />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <label htmlFor="topK" className="text-sm font-medium text-green-300">
            Results:
          </label>
          <select
            id="topK"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="px-3 py-1 bg-gray-800/50 border border-green-500/30 rounded focus:outline-none focus:ring-2 focus:ring-green-400 text-green-200"
            disabled={isLoading}
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={15}>15</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="flex items-center space-x-2 h-10 px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-black rounded-md hover:from-green-400 hover:to-emerald-400 disabled:opacity-50 disabled:pointer-events-none transition-all font-semibold shadow-lg shadow-green-500/30"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          <span>Search</span>
        </button>
      </div>
    </form>
  );
}