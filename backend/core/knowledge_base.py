"""Milvus 访问层（01 25：先 Metadata Filter 再检索，禁止全库搜索）。
V0.1 集合：project_knowledge（partition_key=project_id，仅作查询性能优化，
安全边界在 Service 层——01 52.2）。"""
from pymilvus import DataType, MilvusClient

from config import settings
from core.logger import get_logger

logger = get_logger("knowledge_base")

COLLECTION = "project_knowledge"


def get_milvus() -> MilvusClient:
    return MilvusClient(uri=settings.milvus_uri)


def ensure_collection(client: MilvusClient | None = None) -> None:
    client = client or get_milvus()
    if not client.has_collection(COLLECTION):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("chunk_id", DataType.VARCHAR, max_length=64)
        schema.add_field("document_id", DataType.VARCHAR, max_length=64)
        schema.add_field("project_id", DataType.INT64, is_partition_key=True)
        schema.add_field("text", DataType.VARCHAR, max_length=4096)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
        schema.add_field("page", DataType.INT64)
        schema.add_field("source_type", DataType.VARCHAR, max_length=64)
        index_params = client.prepare_index_params()
        index_params.add_index(field_name="embedding", index_type="HNSW",
                                metric_type="COSINE",
                                params={"M": 16, "efConstruction": 200})
        client.create_collection(
            collection_name=COLLECTION,
            schema=schema,
            index_params=index_params,
        )
        logger.info("milvus collection created: %s (dim=%s)",
                    COLLECTION, settings.embedding_dim)
    # 兼容历史集合缺索引的情况（创建中途失败会留下无索引集合）
    if not client.list_indexes(COLLECTION):
        index_params = client.prepare_index_params()
        index_params.add_index(field_name="embedding", index_type="HNSW",
                                metric_type="COSINE",
                                params={"M": 16, "efConstruction": 200})
        client.create_index(collection_name=COLLECTION, index_params=index_params)
        logger.info("milvus index created for existing collection")
    # 检索前必须加载集合（服务重启后集合仍在，需重新 load）
    client.load_collection(COLLECTION)
    logger.info("milvus collection loaded: %s", COLLECTION)


def insert_chunks(client: MilvusClient, rows: list) -> None:
    if not rows:
        return
    client.insert(collection_name=COLLECTION, data=rows)


def delete_by_document(client: MilvusClient, document_id: str) -> None:
    client.delete(collection_name=COLLECTION,
                  filter='document_id == "{}"'.format(document_id))


def search_dense(client: MilvusClient, query_vec: list, project_id: int,
                 top_k: int = 20) -> list:
    # 检索路径自我保护：集合未加载（如服务重启后）则先加载再重试一次
    for attempt in range(2):
        try:
            return _do_search(client, query_vec, project_id, top_k)
        except Exception as e:
            if attempt == 0 and "not loaded" in str(e):
                logger.warning("collection not loaded, loading now: %s", e)
                client.load_collection(COLLECTION)
                continue
            raise


def _do_search(client: MilvusClient, query_vec: list, project_id: int,
               top_k: int = 20) -> list:
    res = client.search(
        collection_name=COLLECTION,
        data=[query_vec],
        filter="project_id == {}".format(project_id),
        limit=top_k,
        output_fields=["chunk_id", "document_id", "text", "page", "source_type"],
    )
    hits = []
    for r in res[0]:
        hits.append({"id": r["id"], "distance": r["distance"],
                     "entity": r["entity"]})
    return hits
