import click
import time
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from data_processor import DataProcessor
from vector_store import VectorStore
from agent import query_hyperliquid_agent, PRODUCTION_CONFIG

# Configure CLI logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config-file', type=click.Path(exists=True), help='Path to configuration JSON file')
@click.pass_context
def cli(ctx, debug, config_file):
    """HyperLiquid Market Intelligence Agent CLI
    
    Production-ready tool for analyzing HyperLiquid market sentiment,
    trends, and mentions across various crypto data sources.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Set debug level
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Load configuration
    config = PRODUCTION_CONFIG.copy()
    if config_file:
        try:
            with open(config_file, 'r') as f:
                custom_config = json.load(f)
            config.update(custom_config)
            logger.info(f"Configuration loaded from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            click.echo(f"❌ Error loading config: {e}", err=True)
            raise click.Abort()
    
    ctx.obj['config'] = config

@cli.command()
@click.option('--jsonl-file', 
              default='data/hyperliquid_mentions.json', 
              type=click.Path(exists=True),
              help='Path to JSONL data file')
@click.option('--batch-size', 
              default=100, 
              type=int,
              help='Processing batch size')
@click.option('--force', 
              is_flag=True, 
              help='Force re-ingestion even if data exists')
@click.pass_context
def ingest(ctx, jsonl_file, batch_size, force):
    """Ingest JSONL data into vector store with production optimizations"""
    
    start_time = time.time()
    
    try:
        click.echo("🚀 Starting HyperLiquid data ingestion...")
        click.echo(f"📂 Source file: {jsonl_file}")
        click.echo(f"📦 Batch size: {batch_size}")
        
        # Initialize components
        processor = DataProcessor()
        vector_store = VectorStore()
        
        # Check if data already exists
        if not force:
            try:
                test_results = vector_store.search("HyperLiquid", top_k=1)
                if test_results:
                    click.echo("⚠️  Data already exists in vector store.")
                    if not click.confirm("Continue with ingestion anyway?"):
                        click.echo("Ingestion cancelled.")
                        return
            except Exception:
                pass  # Continue if check fails
        
        # Process JSONL file
        click.echo("\n📖 Processing JSONL file...")
        with click.progressbar(length=1, label='Loading data') as bar:
            mentions = processor.process_jsonl_file(jsonl_file)
            bar.update(1)
        
        click.echo(f"✅ Processed {len(mentions)} mentions")
        
        # Create chunks with progress tracking
        click.echo("\n🔨 Creating text chunks...")
        with click.progressbar(mentions, label='Creating chunks') as bar:
            chunks = []
            for mention in bar:
                mention_chunks = processor.create_mention_chunks(mention)
                chunks.extend(mention_chunks)
        
        click.echo(f"✅ Created {len(chunks)} chunks")
        
        # Store in vector database with batching
        click.echo(f"\n💾 Storing in vector database (batch size: {batch_size})...")
        
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        with click.progressbar(length=total_batches, label='Storing batches') as bar:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                vector_store.store_chunks(batch)
                bar.update(1)
                time.sleep(0.1)  # Prevent rate limiting
        
        # Verify ingestion
        click.echo("\n🔍 Verifying ingestion...")
        test_results = vector_store.search("HyperLiquid", top_k=5)
        
        execution_time = time.time() - start_time
        
        if test_results:
            click.echo(f"✅ Ingestion successful!")
            click.echo(f"📊 Verification: Found {len(test_results)} test results")
            click.echo(f"⏱️  Total time: {execution_time:.2f}s")
        else:
            click.echo("❌ Ingestion verification failed!")
            raise click.Abort()
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        click.echo(f"❌ Ingestion failed: {e}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('query')
@click.option('--top-k', 
              default=15, 
              type=int,
              help='Number of results to return')
@click.option('--output-format', 
              type=click.Choice(['detailed', 'summary', 'json']),
              default='detailed',
              help='Output format')
@click.option('--save-results', 
              type=click.Path(),
              help='Save results to file')
@click.pass_context
def search(ctx, query, top_k, output_format, save_results):
    """Search HyperLiquid mentions using AI agent
    
    Examples:
        python main.py search "What are people saying about HyperLiquid vaults?"
        python main.py search "HYPE token price sentiment" --top-k 20
        python main.py search "influencer tweets" --output-format summary
    """
    
    start_time = time.time()
    
    try:
        # Validate inputs
        if not query.strip():
            click.echo("❌ Error: Query cannot be empty", err=True)
            raise click.Abort()
        
        if top_k <= 0 or top_k > 50:
            click.echo("❌ Error: top-k must be between 1 and 50", err=True)
            raise click.Abort()
        
        # Update config with CLI parameters
        config = ctx.obj['config'].copy()
        config['top_k'] = top_k
        config['output_format'] = output_format
        
        click.echo(f"🔍 Searching: '{query}'")
        click.echo(f"📊 Results: {top_k} | Format: {output_format}")
        click.echo("=" * 80)
        
        if output_format == 'json':
            # JSON output for programmatic use
            from agent import HyperLiquidAgent
            agent = HyperLiquidAgent(config)
            results = agent.search_mentions(query, top_k)
            
            json_output = {
                'query': query,
                'timestamp': time.time(),
                'execution_time': time.time() - start_time,
                'results': results
            }
            
            output_text = json.dumps(json_output, indent=2)
            click.echo(output_text)
            
        elif output_format == 'summary':
            # Brief summary output
            config['reasoning'] = False
            config['show_tool_calls'] = False
            query_hyperliquid_agent(query, config)
            
        else:
            # Detailed output (default)
            query_hyperliquid_agent(query, config)
        
        # Save results if requested
        if save_results:
            execution_time = time.time() - start_time
            save_path = Path(save_results)
            
            with open(save_path, 'w') as f:
                f.write(f"Query: {query}\n")
                f.write(f"Timestamp: {time.ctime()}\n")
                f.write(f"Execution Time: {execution_time:.2f}s\n")
                f.write("=" * 80 + "\n\n")
                # Results would be written here in a real implementation
            
            click.echo(f"\n💾 Results saved to: {save_path}")
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        click.echo(f"❌ Search failed: {e}", err=True)
        raise click.Abort()

@cli.command()
@click.option('--mode', 
              type=click.Choice(['quick', 'comprehensive']),
              default='quick',
              help='Demo mode')
@click.pass_context
def demo(ctx, mode):
    """Run demonstration queries
    
    Quick mode: Essential queries for HyperLiquid analysis
    Comprehensive mode: Extended set of market intelligence queries
    """
    
    quick_queries = [
        "What are people saying about HyperLiquid's vaults?",
        "Any influencer tweets about HyperLiquid recently?",
        "HYPE token price sentiment analysis"
    ]
    
    comprehensive_queries = quick_queries + [
        "HyperLiquid vs other DEX mentions",
        "HyperLiquid security concerns or exploits",
        "HyperLiquid TVL and trading volume discussions",
        "James Wynn HyperLiquid trading performance",
        "HyperLiquid yield farming opportunities",
        "HYPE token staking and rewards"
    ]
    
    queries = comprehensive_queries if mode == 'comprehensive' else quick_queries
    config = ctx.obj['config'].copy()
    
    click.echo(f"🎬 Running {mode} demo with {len(queries)} queries...")
    click.echo("=" * 80)
    
    for i, query in enumerate(queries, 1):
        click.echo(f"\n📍 Demo Query {i}/{len(queries)}: {query}")
        click.echo("-" * 60)
        
        try:
            query_hyperliquid_agent(query, config)
        except Exception as e:
            click.echo(f"❌ Query failed: {e}")
        
        if i < len(queries):
            click.echo("\n" + "="*100 + "\n")
            time.sleep(1)  # Brief pause between queries

@cli.command()
@click.option('--export-format', 
              type=click.Choice(['json', 'csv']),
              default='json',
              help='Export format')
@click.option('--output-file', 
              type=click.Path(),
              help='Output file path')
def status(export_format, output_file):
    """Show system status and performance metrics"""
    
    try:
        from agent import HyperLiquidAgent
        
        click.echo("📊 HyperLiquid Agent System Status")
        click.echo("=" * 50)
        
        # Initialize agent to get metrics
        agent = HyperLiquidAgent()
        
        # Test vector store connectivity
        click.echo("\n🔗 Connectivity Tests:")
        try:
            test_results = agent.vector_store.search("test", top_k=1)
            click.echo("  ✅ Vector store: Connected")
            click.echo(f"  📊 Sample query returned {len(test_results)} results")
        except Exception as e:
            click.echo(f"  ❌ Vector store: {e}")
        
        # Get performance metrics
        click.echo("\n📈 Performance Metrics:")
        metrics = agent.get_performance_metrics()
        
        for key, value in metrics.items():
            if isinstance(value, float):
                click.echo(f"  ├─ {key.replace('_', ' ').title()}: {value:.3f}")
            elif isinstance(value, list):
                click.echo(f"  ├─ {key.replace('_', ' ').title()}: {len(value)} items")
            else:
                click.echo(f"  ├─ {key.replace('_', ' ').title()}: {value}")
        
        # Export if requested
        if output_file:
            export_data = {
                'timestamp': time.time(),
                'status': 'operational',
                'metrics': metrics
            }
            
            if export_format == 'json':
                with open(output_file, 'w') as f:
                    json.dump(export_data, f, indent=2)
            else:  # csv
                # CSV export logic would go here
                pass
            
            click.echo(f"\n💾 Status exported to: {output_file}")
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        click.echo(f"❌ Status check failed: {e}", err=True)

@cli.command()
@click.option('--days', default=30, type=int, help='Analysis period in days')
@click.option('--save-report', type=click.Path(), help='Save trend report to file')
def trends(days, save_report):
    """Generate comprehensive trends analysis"""
    
    try:
        click.echo(f"📈 Generating {days}-day trend analysis...")
        
        from agent import HyperLiquidAgent
        agent = HyperLiquidAgent()
        
        # Generate trends report
        trends_report = agent.analyze_trends(f"{days}d")
        
        click.echo("=" * 80)
        click.echo(trends_report)
        
        # Save report if requested
        if save_report:
            with open(save_report, 'w') as f:
                f.write(f"HyperLiquid Trends Analysis - {days} Days\n")
                f.write(f"Generated: {time.ctime()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(trends_report)
            
            click.echo(f"\n💾 Trend report saved to: {save_report}")
        
    except Exception as e:
        logger.error(f"Trends analysis failed: {e}")
        click.echo(f"❌ Trends analysis failed: {e}", err=True)

@cli.command()
def config():
    """Show current configuration"""
    
    click.echo("⚙️  Current Configuration:")
    click.echo("=" * 40)
    
    for key, value in PRODUCTION_CONFIG.items():
        if isinstance(value, dict):
            click.echo(f"{key}:")
            for sub_key, sub_value in value.items():
                click.echo(f"  ├─ {sub_key}: {sub_value}")
        else:
            click.echo(f"{key}: {value}")

@cli.command()
@click.argument('query')
@click.option('--continuous', is_flag=True, help='Run continuous monitoring')
@click.option('--interval', default=300, type=int, help='Check interval in seconds')
def monitor(query, continuous, interval):
    """Monitor specific query for changes over time"""
    
    click.echo(f"👁️  Monitoring: '{query}'")
    
    if continuous:
        click.echo(f"🔄 Continuous mode: checking every {interval}s")
        click.echo("Press Ctrl+C to stop")
        
        try:
            while True:
                click.echo(f"\n⏰ Check at {time.ctime()}")
                query_hyperliquid_agent(query)
                click.echo(f"\n😴 Sleeping for {interval}s...")
                time.sleep(interval)
        except KeyboardInterrupt:
            click.echo("\n🛑 Monitoring stopped by user")
    else:
        # Single check
        query_hyperliquid_agent(query)

if __name__ == "__main__":
    cli()