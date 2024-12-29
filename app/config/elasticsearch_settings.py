audit_index_settings = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "url_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "url": {"type": "text", "analyzer": "url_analyzer"},
            "meta_title": {"type": "text"},
            "meta_description": {"type": "text"},
            "status": {"type": "keyword"},
            "created_at": {"type": "date"},
            "audit_data": {"type": "object"},
            "suggestions_data": {"type": "object"}
        }
    }
} 