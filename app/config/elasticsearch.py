from elasticsearch import AsyncElasticsearch

es_client = AsyncElasticsearch(
    hosts=['http://localhost:9200']
)

audit_index_settings = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mappings": {
        "properties": {
            "url": {"type": "keyword"},
            "meta_title": {"type": "text"},
            "meta_description": {"type": "text"},
            "status": {"type": "keyword"},
            "created_at": {"type": "date"},
            "audit_data": {"type": "object"},
            "suggestions_data": {"type": "object"}
        }
    }
} 