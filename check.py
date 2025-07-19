from vector_store import VectorStore

def debug_search():
    vs = VectorStore()
    
    # Test basic search
    print("🔍 Testing basic search...")
    results = vs.search("HyperLiquid", top_k=5)
    print(f"Found {len(results)} results")
    
    if results:
        print("\n📊 Sample result:")
        for i, result in enumerate(results[:2]):
            print(f"Result {i+1}:")
            print(f"  ID: {result.get('id')}")
            print(f"  Text preview: {result.get('text', '')[:200]}...")
            print(f"  Metadata: {result.get('metadata', {})}")
            print("-" * 50)
    else:
        print("❌ No results found - vector store might be empty")

if __name__ == "__main__":
    debug_search()