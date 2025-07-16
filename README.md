# 🧠 HyperLiquid Mention Agent

An AI-powered agent that analyzes HyperLiquid mentions across various channels using vector search and natural language processing.

## 🚀 Features

- **Semantic Search**: Find relevant mentions using natural language queries
- **Sentiment Analysis**: Analyze sentiment trends in HyperLiquid discussions
- **Entity Co-occurrence**: Find relationships between different entities
- **Influencer Analysis**: Track what crypto influencers are saying
- **Trend Detection**: Identify trending topics and discussions
- **Time-based Filtering**: Query mentions from specific time periods

## 🛠️ Tech Stack

- **Agent Framework**: [Agno](https://github.com/agno-ai/agno) - Multi-modal AI agent framework
- **Vector Database**: [Turbopuffer](https://turbopuffer.com/) - High-performance vector storage
- **LLM**: OpenAI GPT-4 for reasoning and analysis
- **Embeddings**: OpenAI text-embedding-3-small
- **Data Processing**: Custom pipeline for mention processing and chunking

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd HyperLiquid-Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Required API Keys**
   - `OPENAI_API_KEY`: OpenAI API key for LLM and embeddings
   - `TURBOPUFFER_API_KEY`: Turbopuffer API key for vector storage
   - `COHERE_API_KEY`: (Optional) Cohere API key for advanced re-ranking

## 🏃 Quick Start

### Option 1: Full Pipeline
```bash
python main.py
```

This will:
1. Process raw mention data from the gist
2. Generate embeddings and store in Turbopuffer
3. Initialize the agent
4. Run sample queries
5. Enter interactive mode

### Option 2: Sample Queries Demo
```bash
python sample_queries.py
```

This runs a comprehensive set of sample queries across different categories.

## 💬 Usage Examples

```python
from main import HyperLiquidAgentPipeline

# Initialize pipeline
pipeline = HyperLiquidAgentPipeline()
pipeline.setup_pipeline()

# Query the agent
response = pipeline.query_agent("What are people saying about HyperLiquid's vaults?")
print(response)

# More specific queries
response = pipeline.query_agent("Did anyone mention HYPE token and risk together?")
response = pipeline.query_agent("Show me recent influencer opinions about HyperLiquid")
```

## 🔧 Configuration

Edit `config.py` to customize:

- **Models**: Change LLM and embedding models
- **Vector Store**: Configure Turbopuffer namespace and dimensions
- **Chunking**: Adjust chunk size and overlap
- **Search**: Set default search limits and filters

## 📊 Sample Queries

The agent can handle various types of queries:

### Sentiment Analysis
- "What's the overall sentiment about HyperLiquid?"
- "Are people positive or negative about HyperLiquid vaults?"

### Entity Relationships
- "Did anyone mention HYPE token and risk together?"
- "What do people say about HyperLiquid and DeFi?"

### Influencer Tracking
- "What are crypto influencers saying about HyperLiquid?"
- "Any important tweets about HyperLiquid recently?"

### Trend Analysis
- "What are the trending topics related to HyperLiquid?"
- "What's been popular about HyperLiquid this week?"

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Source   │    │  Data Processor │    │  Vector Store   │
│   (JSONL Gist)  │───▶│   (Chunking +   │───▶│  (Turbopuffer)  │
│                 │    │   Embeddings)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  Agno Agent     │───▶│  Vector Search  │
│                 │    │  (GPT-4 + Tools)│    │   + Reasoning   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔍 Agent Tools

The agent has access to these tools:

- `search_mentions()`: Semantic search with filters
- `analyze_sentiment()`: Sentiment analysis with insights
- `find_entity_cooccurrences()`: Entity relationship analysis
- `get_trending_entities()`: Trend detection
- `analyze_influencer_mentions()`: Influencer tracking

## 📈 Performance

- **Data Processing**: ~695 mentions → ~2000+ searchable chunks
- **Vector Storage**: 1536-dimensional embeddings in Turbopuffer
- **Query Response**: ~2-5 seconds for complex queries
- **Search Accuracy**: Semantic search with re-ranking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [Agno](https://github.com/agno-ai/agno) for the agent framework
- [Turbopuffer](https://turbopuffer.com/) for vector storage
- HyperLiquid community for the mention data