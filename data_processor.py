import json
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ProcessedMention:
    id: str
    title: str
    summary: str
    content: str
    url: str
    published_at: datetime
    channel_name: str
    channel_type: str
    source_entity_name: str
    hyperliquid_tokens: List[str]

class DataProcessor:
    def __init__(self):
        pass
    
    def process_jsonl_file(self, file_path: str) -> List[ProcessedMention]:
        """Process JSON file and extract mentions"""
        mentions = []
        seen_ids = set()
        
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            print(f"Total mentions in dataset: {data.get('metadata', {}).get('total_mentions', 0)}")
            
            for mention_data in data.get('mentions', []):
                try:
                    # Extract nested data
                    publication = mention_data.get('publication', {})
                    channel = mention_data.get('channel', {})
                    source_entity = mention_data.get('source_entity', {})
                    hyperliquid_info = mention_data.get('hyperliquid_info', {})
                    
                    # Get unique ID from publication
                    mention_id = publication.get('id')
                    if not mention_id or mention_id in seen_ids:
                        continue
                    
                    seen_ids.add(mention_id)
                    
                    # Parse published_at
                    try:
                        published_at_str = publication.get('published_at', '')
                        if published_at_str:
                            if published_at_str.endswith('Z'):
                                published_at_str = published_at_str.replace('Z', '+00:00')
                            published_at = datetime.fromisoformat(published_at_str)
                        else:
                            published_at = datetime.now()
                    except Exception as e:
                        print(f"Error parsing date for mention {mention_id}: {e}")
                        published_at = datetime.now()
                    
                    # Create processed mention
                    processed_mention = ProcessedMention(
                        id=mention_id,
                        title=publication.get('title', ''),
                        summary=publication.get('summary', ''),
                        content=publication.get('content', ''),
                        url=publication.get('url', ''),
                        published_at=published_at,
                        channel_name=channel.get('name', ''),
                        channel_type=channel.get('type', ''),
                        source_entity_name=source_entity.get('name', ''),
                        hyperliquid_tokens=hyperliquid_info.get('tokens', [])
                    )
                    
                    mentions.append(processed_mention)
                    
                except Exception as e:
                    print(f"Error processing mention: {e}")
                    continue
        
        print(f"Successfully processed {len(mentions)} unique mentions")
        return mentions
    
    def create_chunks(self, mentions: List[ProcessedMention]) -> List[Dict[str, Any]]:
        """Create searchable chunks from mentions"""
        chunks = []
        
        for mention in mentions:
            # Combine title, summary, and content for better search
            text_parts = []
            if mention.title:
                text_parts.append(f"Title: {mention.title}")
            if mention.summary:
                text_parts.append(f"Summary: {mention.summary}")
            if mention.content:
                text_parts.append(f"Content: {mention.content}")
            
            # If no content, skip this mention
            if not text_parts:
                continue
            
            text = "\n\n".join(text_parts)
            
            chunk = {
                'id': mention.id,
                'text': text,
                'metadata': {
                    'title': mention.title,
                    'summary': mention.summary,
                    'url': mention.url,
                    'published_at': mention.published_at.isoformat(),
                    'channel_name': mention.channel_name,
                    'channel_type': mention.channel_type,
                    'source_entity_name': mention.source_entity_name,
                    'hyperliquid_tokens': mention.hyperliquid_tokens
                }
            }
            chunks.append(chunk)
        
        print(f"Created {len(chunks)} chunks from {len(mentions)} mentions")
        return chunks