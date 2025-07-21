const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://bc325114acc7.ngrok-free.app";

interface SearchRequest {
  query: string;
  top_k?: number;
  output_format?: string;
}

interface SearchResponse {
  query: string;
  timestamp: number;
  execution_time: number;
  total_results: number;
  results: Array<{
    id: string;
    title: string;
    source: string;
    published_at: string;
    url: string;
    content: string;
    cohere_score: number;
    relevance_category: string;
    days_ago: number;
  }>;
  ai_analysis: string;
  performance_metrics: Record<string, number | string | boolean>;
}

interface StatusResponse {
  status: string;
  agent_ready: boolean;
  vector_store_connected: boolean;
  total_documents?: number;
  performance_metrics: Record<string, number | string | boolean>;
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`API Request failed: ${error.message}`);
      }
      throw new Error('API Request failed: Unknown error');
    }
  }

  async search(request: SearchRequest): Promise<SearchResponse> {
    return this.request<SearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getStatus(): Promise<StatusResponse> {
    return this.request<StatusResponse>('/status');
  }

  async runDemo(): Promise<unknown> {
    return this.request<unknown>('/demo');
  }
}

export const apiClient = new APIClient();
export type { SearchRequest, SearchResponse, StatusResponse };