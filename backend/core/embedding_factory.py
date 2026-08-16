"""EmbeddingFactory：向量化统一入口（默认实现档，01 52.3）。
两个真实实现：api（OpenAI 兼容 BGE-M3 服务）/ local（sentence-transformers）。
A/B 评测切换（如 Qwen3-Embedding）只改配置，不动业务代码。"""
from typing import Protocol

from config import settings
from core.logger import get_logger
from core.retry import retry

logger = get_logger("embedding_factory")


class Embedder(Protocol):
    def embed_texts(self, texts: list) -> list: ...


class APIEmbedder:
    def __init__(self):
        if not settings.embedding_api_key:
            raise RuntimeError("EMBEDDING_API_KEY 未配置：请在项目根 .env 中设置对应 API 密钥")
        from openai import OpenAI
        self._client = OpenAI(api_key=settings.embedding_api_key,
                              base_url=settings.embedding_api_base)

    @retry(max_attempts=3)
    def embed_texts(self, texts: list) -> list:
        if not texts:
            return []
        resp = self._client.embeddings.create(
            model=settings.embedding_model, input=texts)
        data = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in data]


class LocalEmbedder:
    """本地 sentence-transformers 模式（需安装 sentence-transformers）。"""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(settings.embedding_local_model)

    def embed_texts(self, texts: list) -> list:
        if not texts:
            return []
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]


_embedder = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        if settings.embedding_mode == "local":
            logger.info("EmbeddingFactory: local mode, model=%s",
                        settings.embedding_local_model)
            _embedder = LocalEmbedder()
        else:
            if not settings.embedding_api_key:
                logger.warning("EMBEDDING_API_KEY 未配置，向量化将失败")
            logger.info("EmbeddingFactory: api mode, model=%s",
                        settings.embedding_model)
            _embedder = APIEmbedder()
    return _embedder
