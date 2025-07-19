import turbopuffer
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

tpuf = turbopuffer.Turbopuffer(
    api_key=os.getenv('TURBOPUFFER_API_KEY'),
    region='aws-us-east-1', # pick the right region: https://turbopuffer.com/docs/regions
)

# List all namespaces
namespaces = tpuf.namespaces()
for namespace in namespaces:
    print('Namespace', namespace.id)

/Users/ranjanshahajishitole/Desktop/HyperLiquid-Agent/data/hyperliquid_mentions.json