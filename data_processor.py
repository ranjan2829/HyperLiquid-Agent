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
        seen_ids = set()  # Track seen IDs to avoid duplicates
        
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                # Read as JSON (not JSONL)
                data = json.load(file)
                
                # Extract mentions from the data structure
                raw_mentions = data.get('mentions', [])
                
                for mention in raw_mentions:
                    try:
                        # Extract publication info
                        publication = mention.get('publication', {})
                        channel = mention.get('channel', {})
                        source_entity = mention.get('source_entity', {})
                        hyperliquid_info = mention.get('hyperliquid_info', {})
                        
                        # Get the ID and check for duplicates
                        mention_id = publication.get('id', '')
                        if mention_id in seen_ids:
                            print(f"Skipping duplicate mention ID: {mention_id}")
                            continue
                        
                        seen_ids.add(mention_id)
                        
                        # Create processed mention
                        processed_mention = ProcessedMention(
                            id=mention_id,
                            title=publication.get('title', ''),
                            summary=publication.get('summary', ''),
                            content=publication.get('content', ''),
                            url=publication.get('url', ''),
                            published_at=datetime.fromisoformat(publication.get('published_at', '').replace('Z', '+00:00')) if publication.get('published_at') else datetime.now(),
                            channel_name=channel.get('name', ''),
                            channel_type=channel.get('type', ''),
                            source_entity_name=source_entity.get('name', ''),
                            hyperliquid_tokens=hyperliquid_info.get('tokens', [])
                        )
                        
                        mentions.append(processed_mention)
                        
                    except Exception as e:
                        print(f"Error processing mention: {e}")
                        continue
                        
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return []
        
        return mentions
    
    def create_chunks(self, mentions: List[ProcessedMention]) -> List[Dict[str, Any]]:
        """Create searchable chunks from mentions"""
        chunks = []
        seen_chunk_ids = set()  # Track seen chunk IDs
        
        for mention in mentions:
            # Create primary chunk from title + summary
            primary_text = f"{mention.title}\n\n{mention.summary}".strip()
            primary_chunk_id = f"{mention.id}_primary"
            
            if primary_text and primary_chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(primary_chunk_id)
                chunks.append({
                    'id': primary_chunk_id,
                    'text': primary_text,
                    'mention_id': mention.id,
                    'type': 'primary',
                    'metadata': {
                        'title': mention.title,
                        'url': mention.url,
                        'published_at': mention.published_at.isoformat(),
                        'channel_name': mention.channel_name,
                        'channel_type': mention.channel_type,
                        'source_entity_name': mention.source_entity_name,
                        'hyperliquid_tokens': mention.hyperliquid_tokens
                    }
                })
            
            # Create content chunk if content exists
            content_chunk_id = f"{mention.id}_content"
            if mention.content and content_chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(content_chunk_id)
                chunks.append({
                    'id': content_chunk_id,
                    'text': mention.content,
                    'mention_id': mention.id,
                    'type': 'content',
                    'metadata': {
                        'title': mention.title,
                        'url': mention.url,
                        'published_at': mention.published_at.isoformat(),
                        'channel_name': mention.channel_name,
                        'channel_type': mention.channel_type,
                        'source_entity_name': mention.source_entity_name,
                        'hyperliquid_tokens': mention.hyperliquid_tokens
                    }
                })
        
        print(f"Created {len(chunks)} unique chunks (removed duplicates)")
        return chunks