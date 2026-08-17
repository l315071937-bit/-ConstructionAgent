from pydantic_settings import BaseSettings

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent




class Settings(BaseSettings):
    app_name: str = "ConstructionAgent"
    api_prefix: str = "/api/v1"

    secret_key: str = "dev-secret-change-me"
    jwt_expire_seconds: int = 86400

    database_url: str = "postgresql+psycopg2://ca:ca@localhost:5432/constructionagent"
    redis_url: str = "redis://localhost:6379/0"

    milvus_uri: str = "http://localhost:19530"

    storage_dir: str = str(BASE_DIR / "storage")
    standard_storage_dir: str = str(BASE_DIR / "storage" / "standards")
    plan_storage_dir: str = str(BASE_DIR / "storage" / "plans")
    max_upload_mb: int = 50

    # Embedding（默认实现档，01 52.3：接口冻结、实现可换）
    embedding_mode: str = "api"          # api | local
    embedding_api_base: str = "https://api.siliconflow.cn/v1"
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_local_model: str = "BAAI/bge-m3"

    # LLM
    llm_api_base: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.2

    # Conversation memory: raw messages remain in SQL; only prompt context slides.
    conversation_recent_token_budget: int = 3000
    conversation_summary_trigger_tokens: int = 6000
    conversation_keep_recent_messages: int = 8
    memory_recall_limit: int = 5

    # 检索置信度规则阈值（V0.1 规则版，后续由 evaluation/ 实验数据校准）
    # 注意：Milvus COSINE 度量下，0.3~0.4 已是正常相关水平
    retrieval_confidence_threshold: float = 0.25

    model_config = {"env_file": str(BASE_DIR / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
