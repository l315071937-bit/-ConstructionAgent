"""ConstructionAgent FastAPI 入口（01 7：API 层只做参数/认证/路由）。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import auth, documents, projects, retrieval
from config import settings
from core.exceptions import AppError
from core.logger import get_logger

logger = get_logger("main")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.http_status,
                        content={"error": {"code": exc.code,
                                           "message": exc.message}})


@app.exception_handler(Exception)
async def unhandled_handler(request, exc: Exception):
    logger.exception("unhandled error: %s", exc)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500,
                        content={"error": {"code": "INTERNAL_ERROR",
                                           "message": "内部错误"}})


@app.on_event("startup")
async def startup():
    from db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    logger.info("tables ensured")
    # Milvus 集合加载：失败不阻塞启动（检索路径有自我保护兜底）
    try:
        from core.knowledge_base import ensure_collection
        ensure_collection()
    except Exception as e:
        logger.warning("milvus not ready at startup: %s", e)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(projects.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(retrieval.router, prefix=settings.api_prefix)
