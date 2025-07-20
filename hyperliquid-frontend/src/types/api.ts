export interface SearchRequest {
  query: string;
  top_k?: number;
  output_format?: string;
}

export interface SearchResult {
  id: string;
  title: string;
  source: string;
  published_at: string;
  url: string;
  content: string;
  cohere_score: number;
  relevance_category: string;
  days_ago: number;
}

export interface SearchResponse {
  query: string;
  timestamp: number;
  execution_time: number;
  total_results: number;
  results: SearchResult[];
  ai_analysis: string;
  performance_metrics: Record<string, any>;
}

export interface StatusResponse {
  status: string;
  agent_ready: boolean;
  vector_store_connected: boolean;
  total_documents?: number;
  performance_metrics: Record<string, any>;
}