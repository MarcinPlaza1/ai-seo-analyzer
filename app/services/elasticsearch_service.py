from elasticsearch import NotFoundError, AsyncElasticsearch
from ..config.settings import settings
from ..config.elasticsearch_settings import audit_index_settings

es_client = AsyncElasticsearch(
    hosts=[f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"],
    retry_on_timeout=True,
    max_retries=3
)

class ElasticsearchService:
    INDEX_NAME = "audits"
    
    @classmethod
    async def init_index(cls):
        if not await es_client.indices.exists(index=cls.INDEX_NAME):
            await es_client.indices.create(
                index=cls.INDEX_NAME,
                body=audit_index_settings
            )
    
    @classmethod
    async def index_audit(cls, audit):
        await es_client.index(
            index=cls.INDEX_NAME,
            id=str(audit.id),
            body={
                "url": audit.url,
                "meta_title": audit.meta_title,
                "meta_description": audit.meta_description,
                "status": audit.status,
                "created_at": audit.created_at.isoformat(),
                "audit_data": audit.audit_data,
                "suggestions_data": audit.suggestions_data
            }
        )
    
    @classmethod
    async def search_audits(cls, query: str, filters: dict = None):
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {"multi_match": {
                            "query": query,
                            "fields": ["url^2", "meta_title", "meta_description"]
                        }}
                    ]
                }
            },
            "sort": [{"created_at": "desc"}]
        }
        
        if filters:
            search_body["query"]["bool"]["filter"] = [
                {"term": {k: v}} for k, v in filters.items()
            ]
        
        results = await es_client.search(
            index=cls.INDEX_NAME,
            body=search_body
        )
        return results["hits"]["hits"] 