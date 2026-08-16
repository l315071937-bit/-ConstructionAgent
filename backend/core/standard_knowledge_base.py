"""Tenant-isolated Milvus collection for standards and codes."""
from pymilvus import DataType, MilvusClient

from config import settings
from core.logger import get_logger

logger = get_logger("standard_knowledge_base")
COLLECTION = "standard_knowledge"


def get_standard_milvus() -> MilvusClient:
    return MilvusClient(uri=settings.milvus_uri)


def ensure_standard_collection(client: MilvusClient | None = None) -> None:
    client = client or get_standard_milvus()
    if not client.has_collection(COLLECTION):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("chunk_id", DataType.VARCHAR, max_length=64)
        schema.add_field("standard_document_id", DataType.VARCHAR, max_length=64)
        schema.add_field("tenant_id", DataType.INT64, is_partition_key=True)
        schema.add_field("text", DataType.VARCHAR, max_length=4096)
        schema.add_field("embedding", DataType.FLOAT_VECTOR,
                         dim=settings.embedding_dim)
        schema.add_field("page", DataType.INT64)
        schema.add_field("article", DataType.VARCHAR, max_length=64)
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="embedding", index_type="HNSW", metric_type="COSINE",
            params={"M": 16, "efConstruction": 200})
        client.create_collection(
            collection_name=COLLECTION, schema=schema,
            index_params=index_params)
        logger.info("standard collection created: dim=%s", settings.embedding_dim)
    if not client.list_indexes(COLLECTION):
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="embedding", index_type="HNSW", metric_type="COSINE",
            params={"M": 16, "efConstruction": 200})
        client.create_index(collection_name=COLLECTION,
                            index_params=index_params)
    client.load_collection(COLLECTION)


def insert_standard_chunks(client: MilvusClient, rows: list) -> None:
    if rows:
        client.insert(collection_name=COLLECTION, data=rows)


def delete_standard_document(client: MilvusClient, document_id: str) -> None:
    client.delete(
        collection_name=COLLECTION,
        filter='standard_document_id == "{}"'.format(document_id))


def search_standard_dense(client: MilvusClient, query_vec: list,
                          tenant_id: int, top_k: int = 20) -> list:
    for attempt in range(2):
        try:
            result = client.search(
                collection_name=COLLECTION, data=[query_vec],
                filter="tenant_id == {}".format(tenant_id), limit=top_k,
                output_fields=["chunk_id", "standard_document_id", "text",
                               "page", "article"])
            return [{"id": hit["id"], "distance": hit["distance"],
                     "entity": hit["entity"]} for hit in result[0]]
        except Exception as exc:
            if attempt == 0 and "not loaded" in str(exc):
                client.load_collection(COLLECTION)
                continue
            raise
