import click
from data_processor import DataProcessor
from vector_store import VectorStore
from agent import HyperLiquidAgent

@click.group()
def cli():
    """HyperLiquid Mention Agent CLI"""
    pass

@cli.command()
@click.option('--jsonl-file', default='data/hyperliquid_mentions.json', type=click.Path(exists=True))
def ingest(jsonl_file):
    """Ingest JSONL data into vector store"""
    
    click.echo("Processing JSONL file...")
    processor = DataProcessor()
    mentions = processor.process_jsonl_file(jsonl_file)
    
    click.echo(f"Processed {len(mentions)} mentions")
    
    click.echo("Creating chunks...")
    chunks = processor.create_chunks(mentions)
    
    click.echo(f"Created {len(chunks)} chunks")
    
    click.echo("Storing in vector database...")
    vector_store = VectorStore()
    vector_store.store_chunks(chunks)
    
    click.echo("✅ Ingestion complete!")

@cli.command()
@click.argument('query')
def search(query):
    """Search HyperLiquid mentions"""
    
    agent = HyperLiquidAgent()
    response = agent.answer_query(query)
    
    click.echo(f"\n🔍 Query: {response['query']}")
    click.echo(f"📊 Reasoning: {response['reasoning']}")
    
    # Sentiment analysis
    sentiment = response['sentiment_analysis']
    click.echo(f"\n📈 Sentiment Analysis:")
    click.echo(f"  Total mentions: {sentiment['total_mentions']}")
    click.echo(f"  Positive: {sentiment['positive']} ({sentiment['positive_pct']:.1f}%)")
    click.echo(f"  Negative: {sentiment['negative']} ({sentiment['negative_pct']:.1f}%)")
    click.echo(f"  Neutral: {sentiment['neutral']} ({sentiment['neutral_pct']:.1f}%)")
    
    # Top mentions
    click.echo(f"\n🔗 Top Sources:")
    for i, source in enumerate(response['sources'], 1):
        click.echo(f"  {i}. {source['title']}")
        click.echo(f"     Source: {source['source']}")
        click.echo(f"     URL: {source['url']}")
        click.echo(f"     Published: {source['published_at']}")
        click.echo()

@cli.command()
def demo():
    """Run demo queries"""
    
    agent = HyperLiquidAgent()
    
    demo_queries = [
        "What are people saying about HyperLiquid's vaults?",
        "Did anyone mention HYPE token and risk in the same sentence?",
        "Any recent news about HyperLiquid?"
    ]
    
    for query in demo_queries:
        click.echo(f"\n{'='*50}")
        click.echo(f"Demo Query: {query}")
        click.echo(f"{'='*50}")
        
        response = agent.answer_query(query)
        
        click.echo(f"🔍 Reasoning: {response['reasoning']}")
        sentiment = response['sentiment_analysis']
        click.echo(f"📊 Sentiment: {sentiment['positive']} pos, {sentiment['negative']} neg, {sentiment['neutral']} neutral")
        
        click.echo("📰 Top mentions:")
        for mention in response['top_mentions'][:3]:
            click.echo(f"  - {mention['title'][:80]}...")
            click.echo(f"    Source: {mention['source_entity_name']}")

if __name__ == "__main__":
    cli()