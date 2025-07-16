import click
from data_processor import DataProcessor
from vector_store import VectorStore
from agent import query_hyperliquid_agent

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
    """Search HyperLiquid mentions using the agent"""
    query_hyperliquid_agent(query)

@cli.command()
def demo():
    """Run demo queries"""
    demo_queries = [
        "What are people saying about HyperLiquid's vaults?",
        "Did anyone mention HYPE token and risk in the same sentence?",
        "Any influencer tweets about HyperLiquid recently?"
    ]
    
    for query in demo_queries:
        query_hyperliquid_agent(query)
        click.echo("\n" + "="*80 + "\n")

if __name__ == "__main__":
    cli()