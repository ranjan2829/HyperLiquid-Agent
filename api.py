from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import json
import logging
import time
import subprocess
import sys
from contextlib import asynccontextmanager
import uvicorn
import re
from datetime import datetime, timedelta

from agent import HyperLiquidAgent, PRODUCTION_CONFIG
from data_processor import DataProcessor
from vector_store import VectorStore
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global agent_instance
    try:
        logger.info("🚀 Initializing HyperLiquid Agent...")
        agent_instance = HyperLiquidAgent(PRODUCTION_CONFIG)
        logger.info("✅ Agent initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        agent_instance = None
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down HyperLiquid Agent")

app = FastAPI(
    title="HyperLiquid Market Intelligence API",
    description="AI-powered market analysis for HyperLiquid ecosystem",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 15
    output_format: Optional[str] = "detailed"

class SearchResult(BaseModel):
    id: str
    title: str
    source: str
    published_at: str
    url: str
    content: str
    cohere_score: float
    relevance_category: str
    days_ago: int

class SearchResponse(BaseModel):
    query: str
    timestamp: float
    execution_time: float
    total_results: int
    results: List[SearchResult]
    ai_analysis: str
    performance_metrics: Dict[str, Any]

class IngestRequest(BaseModel):
    file_path: str
    batch_size: Optional[int] = 100
    force: Optional[bool] = False

class StatusResponse(BaseModel):
    status: str
    agent_ready: bool
    vector_store_connected: bool
    total_documents: Optional[int]
    performance_metrics: Dict[str, Any]

def parse_cli_output_to_structured_data(cli_output: str, query: str, execution_time: float) -> Dict[str, Any]:
    """Parse the CLI output into structured data for the frontend"""
    
    # Extract AI analysis section
    ai_analysis = ""
    ai_section_start = cli_output.find("🤖 **AGNO AI AGENT COMPREHENSIVE ANALYSIS**")
    if ai_section_start != -1:
        ai_section = cli_output[ai_section_start:]
        # Extract everything after the analysis header until performance metrics
        analysis_start = ai_section.find("### 🔍 **DETAILED REASONING:**")
        if analysis_start != -1:
            analysis_content = ai_section[analysis_start:]
            performance_start = analysis_content.find("📊 **Performance Metrics:**")
            if performance_start != -1:
                ai_analysis = analysis_content[:performance_start].strip()
            else:
                ai_analysis = analysis_content.strip()
    
    # Extract structured results
    results = []
    result_sections = re.findall(
        r'🎯 \*\*RESULT #(\d+)\*\* - Cohere Score: ([\d.]+)\s*'
        r'📰 \*\*Title:\*\* (.+?)\s*'
        r'🏢 \*\*Source:\*\* (.+?)\s*'
        r'📅 \*\*Date:\*\* (\d+) days ago \(([^)]+)\)\s*'
        r'🔗 \*\*URL:\*\* (.+?)\s*'
        r'📝 \*\*Content:\*\* (.+?)(?=🧠|\n🎯|\Z)',
        cli_output,
        re.DOTALL
    )
    
    for match in result_sections:
        rank, score, title, source, days_ago, date, url, content = match
        
        # Clean up the content
        content = content.strip().replace('\n', ' ')
        if len(content) > 500:
            content = content[:500] + "..."
        
        # Determine relevance category based on score
        score_float = float(score)
        if score_float >= 0.8:
            relevance_category = "high"
        elif score_float >= 0.5:
            relevance_category = "medium"
        else:
            relevance_category = "low"
        
        results.append(SearchResult(
            id=f"result_{rank}_{int(time.time())}",
            title=title.strip(),
            source=source.strip(),
            published_at=date.strip(),
            url=url.strip(),
            content=content,
            cohere_score=score_float,
            relevance_category=relevance_category,
            days_ago=int(days_ago)
        ))
    
    # Extract performance metrics
    performance_metrics = {
        "execution_time": execution_time,
        "total_results_found": len(results),
        "average_relevance_score": sum(r.cohere_score for r in results) / len(results) if results else 0,
        "unique_sources": len(set(r.source for r in results)),
        "data_pipeline": "TurboPuffer + Cohere + OpenAI GPT-4",
        "search_method": "CLI Subprocess (Reliable)"
    }
    
    return {
        "query": query,
        "timestamp": time.time(),
        "execution_time": execution_time,
        "total_results": len(results),
        "results": [r.dict() for r in results],
        "ai_analysis": ai_analysis,
        "performance_metrics": performance_metrics
    }

# API Routes

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "message": "HyperLiquid Market Intelligence API",
        "status": "operational",
        "docs": "/docs",
        "agent_ready": agent_instance is not None
    }

@app.get("/status", response_model=StatusResponse, tags=["System"])
async def get_status():
    """Get system status and performance metrics"""
    try:
        # Check agent status
        agent_ready = agent_instance is not None
        
        # Check vector store connectivity
        vector_store_connected = False
        total_documents = None
        
        if agent_ready:
            try:
                test_results = agent_instance.vector_store.search("test", top_k=1)
                vector_store_connected = True
                total_documents = len(test_results) if test_results else 0
            except Exception as e:
                logger.warning(f"Vector store connection test failed: {e}")
        
        # Get performance metrics
        performance_metrics = {}
        if agent_ready:
            try:
                performance_metrics = agent_instance.reranker.get_performance_metrics()
            except Exception as e:
                logger.warning(f"Failed to get performance metrics: {e}")
                performance_metrics = {"error": str(e)}
        
        return StatusResponse(
            status="operational" if agent_ready and vector_store_connected else "degraded",
            agent_ready=agent_ready,
            vector_store_connected=vector_store_connected,
            total_documents=total_documents,
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_hyperliquid(request: SearchRequest):
    """Search HyperLiquid mentions with AI analysis - BACK TO CLI METHOD (IT WORKS!)"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if request.top_k <= 0 or request.top_k > 50:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 50")
    
    start_time = time.time()
    
    try:
        logger.info(f"🔍 Processing search request: '{request.query}'")
        
        # BACK TO THE WORKING CLI METHOD - DON'T BREAK WHAT WORKS!
        cmd = [
            sys.executable, "main.py", "search", 
            request.query,
            "--top-k", str(request.top_k),
            "--output-format", "detailed"
        ]
        
        # Execute the command and capture output - NO TIMEOUT
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            # REMOVED TIMEOUT - LET IT RUN AS LONG AS NEEDED
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode != 0:
            logger.error(f"CLI command failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Search failed: {result.stderr}")
        
        # Parse the CLI output into structured data
        structured_data = parse_cli_output_to_structured_data(
            result.stdout, 
            request.query, 
            execution_time
        )
        
        logger.info(f"✅ Search completed in {execution_time:.2f}s with {len(structured_data['results'])} results")
        return SearchResponse(**structured_data)
        
    except subprocess.TimeoutExpired:
        logger.error("Search timeout")
        raise HTTPException(status_code=504, detail="Search request timed out")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/search/stream", tags=["Search"])
async def search_stream(request: SearchRequest):
    """Stream search results in real-time"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    async def generate_stream():
        try:
            # Yield initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting search...'})}\n\n"
            
            # Yield search progress
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Searching TurboPuffer...'})}\n\n"
            
            # Run the search using CLI (the method that works)
            cmd = [
                sys.executable, "main.py", "search", 
                request.query,
                "--top-k", str(request.top_k),
                "--output-format", "detailed"
            ]
            
            # Execute and stream results
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                yield f"data: {json.dumps({'type': 'complete', 'output': stdout})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': stderr})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/ingest", tags=["Data Management"])
async def ingest_data(request: IngestRequest, background_tasks: BackgroundTasks):
    """Ingest data into vector store"""
    try:
        # Add ingestion as background task
        background_tasks.add_task(run_ingestion, request.file_path, request.batch_size, request.force)
        
        return {
            "message": "Ingestion started in background",
            "file_path": request.file_path,
            "batch_size": request.batch_size,
            "force": request.force
        }
        
    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")

async def run_ingestion(file_path: str, batch_size: int, force: bool):
    """Background task for data ingestion"""
    try:
        logger.info(f"🚀 Starting background ingestion: {file_path}")
        
        processor = DataProcessor()
        vector_store = VectorStore()
        
        # Process file
        mentions = processor.process_jsonl_file(file_path)
        chunks = processor.create_chunks(mentions)
        
        # Store in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vector_store.store_chunks(batch)
            await asyncio.sleep(0.1)  # Prevent rate limiting
        
        logger.info(f"✅ Ingestion completed: {len(chunks)} chunks processed")
        
    except Exception as e:
        logger.error(f"❌ Background ingestion failed: {e}")

@app.get("/demo", tags=["Demo"])
async def run_demo():
    """Run demonstration queries"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    demo_queries = [
        "What are people saying about HyperLiquid's vaults?",
        "Any influencer tweets about HyperLiquid recently?",
        "HYPE token price sentiment analysis"
    ]
    
    results = []
    
    for query in demo_queries:
        try:
            # Run a smaller search for demo
            search_request = SearchRequest(query=query, top_k=5)
            search_response = await search_hyperliquid(search_request)
            
            results.append({
                "query": query,
                "results": search_response.results[:3],  # Limit for demo
                "execution_time": search_response.execution_time
            })
        except Exception as e:
            results.append({
                "query": query,
                "error": str(e)
            })
    
    return {"demo_results": results}

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )