"""core 层与检索器实现的单元测试：异常 / 重试 / 工厂单例 / dense / lexical / db 会话。

依赖策略：外部服务（OpenAI、Milvus、sentence-transformers）全部用替身隔离。
"""
from unittest.mock import MagicMock, patch

import pytest

import core.llm_factory as llm_factory
import core.embedding_factory as embedding_factory
import db.session as session_mod
from core.exceptions import AuthError, NotFoundError, PermissionError_
from core.retry import retry
from services.retrieval.dense_retriever import DenseRetriever
from services.retrieval.lexical_retriever import LexicalRetriever


# ================= core/exceptions：错误码约定 =================

class TestExceptions:
    def test_AuthError_默认401(self):
        e = AuthError()
        assert e.http_status == 401
        assert e.code == "AUTH_TOKEN_INVALID"

    def test_PermissionError_403(self):
        assert PermissionError_("无权").http_status == 403

    def test_NotFoundError_404_自定义code(self):
        e = NotFoundError("DOCUMENT_NOT_FOUND", "文档不存在")
        assert e.http_status == 404
        assert e.code == "DOCUMENT_NOT_FOUND"


# ================= core/retry：指数退避重试 =================

class TestRetry:
    def test_一次成功_不重试不睡眠(self):
        calls = {"n": 0}

        @retry(max_attempts=3)
        def ok():
            calls["n"] += 1
            return "done"

        with patch("core.retry.time.sleep") as sleep:
            assert ok() == "done"
        assert calls["n"] == 1
        sleep.assert_not_called()

    def test_失败两次第三次成功_退避间隔翻倍(self):
        calls = {"n": 0}

        @retry(max_attempts=3, base_delay=1.0)
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("boom")
            return "recovered"

        with patch("core.retry.time.sleep") as sleep:
            assert flaky() == "recovered"
        assert calls["n"] == 3
        assert [c.args[0] for c in sleep.call_args_list] == [1.0, 2.0]

    def test_超过次数_抛原始异常(self):
        calls = {"n": 0}

        @retry(max_attempts=3, base_delay=0.01)
        def always_fail():
            calls["n"] += 1
            raise ValueError("always fail")

        with patch("core.retry.time.sleep"), pytest.raises(ValueError):
            always_fail()
        assert calls["n"] == 3

    def test_非目标异常_立即抛出不重试(self):
        calls = {"n": 0}

        @retry(max_attempts=3, exceptions=(ValueError,))
        def type_error():
            calls["n"] += 1
            raise TypeError("not in retry list")

        with pytest.raises(TypeError):
            type_error()
        assert calls["n"] == 1

# ================= core/llm_factory：统一 LLM 入口 =================

class FakeOpenAI:
    def __init__(self, content=None):
        self._content = content
        self.chat = MagicMock()
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        self.chat.completions.create.return_value = resp


class TestLLMClient:
    def test_无密钥构造_抛RuntimeError(self, monkeypatch):
        monkeypatch.setattr(llm_factory.settings, "llm_api_key", "")
        with pytest.raises(RuntimeError):
            llm_factory.LLMClient()

    def test_chat_返回内容(self, monkeypatch):
        monkeypatch.setattr(llm_factory.settings, "llm_api_key", "sk-test")
        fake = FakeOpenAI(content="TN-S system")
        monkeypatch.setattr(llm_factory, "OpenAI", lambda **kw: fake)
        client = llm_factory.LLMClient()
        assert client.chat([{"role": "user", "content": "hi"}]) == "TN-S system"

    def test_chat_内容为空_返回空串(self, monkeypatch):
        monkeypatch.setattr(llm_factory.settings, "llm_api_key", "sk-test")
        fake = FakeOpenAI(content=None)
        monkeypatch.setattr(llm_factory, "OpenAI", lambda **kw: fake)
        client = llm_factory.LLMClient()
        assert client.chat([]) == ""


class TestGetLLM:
    def test_单例_只构造一次(self, monkeypatch):
        fake = MagicMock()
        monkeypatch.setattr(llm_factory, "_llm", None)
        monkeypatch.setattr(llm_factory, "LLMClient", fake)
        a = llm_factory.get_llm()
        b = llm_factory.get_llm()
        assert a is b
        assert fake.call_count == 1


# ================= core/embedding_factory =================

class TestAPIEmbedder:
    def test_无密钥构造_抛RuntimeError(self, monkeypatch):
        monkeypatch.setattr(embedding_factory.settings, "embedding_api_key", "")
        with pytest.raises(RuntimeError):
            embedding_factory.APIEmbedder()

    def test_空列表直接返回(self):
        e = object.__new__(embedding_factory.APIEmbedder)
        e._client = MagicMock()
        assert e.embed_texts([]) == []

    def test_按index排序还原输入顺序(self):
        e = object.__new__(embedding_factory.APIEmbedder)
        fake = MagicMock()
        resp = MagicMock()
        resp.data = [MagicMock(index=1, embedding=[0.2]),
                     MagicMock(index=0, embedding=[0.1])]
        fake.embeddings.create.return_value = resp
        e._client = fake
        assert e.embed_texts(["a", "b"]) == [[0.1], [0.2]]


class TestGetEmbedder:
    def test_api模式_单例缓存(self, monkeypatch):
        monkeypatch.setattr(embedding_factory.settings, "embedding_mode", "api")
        monkeypatch.setattr(embedding_factory, "_embedder", None)
        fake_cls = MagicMock()
        monkeypatch.setattr(embedding_factory, "APIEmbedder", fake_cls)
        a = embedding_factory.get_embedder()
        b = embedding_factory.get_embedder()
        assert a is b
        assert fake_cls.call_count == 1

    def test_local模式_构造LocalEmbedder(self, monkeypatch):
        monkeypatch.setattr(embedding_factory.settings, "embedding_mode", "local")
        monkeypatch.setattr(embedding_factory, "_embedder", None)
        fake_cls = MagicMock()
        monkeypatch.setattr(embedding_factory, "LocalEmbedder", fake_cls)
        embedding_factory.get_embedder()
        assert fake_cls.called


# ================= 检索器实现 =================

class TestDenseRetriever:
    def test_向量检索_命中映射为RetrievedChunk(self, monkeypatch):
        # 单测不得依赖真实 Milvus：连 get_milvus 一起替身
        # （2026-08-16 CI 教训：不替身时 Windows 本地碰巧有 Milvus 能过，
        #  干净 Linux CI 上连接 localhost:19530 失败）
        monkeypatch.setattr(
            "services.retrieval.dense_retriever.get_milvus",
            lambda: MagicMock())
        monkeypatch.setattr(
            "services.retrieval.dense_retriever.get_embedder",
            lambda: MagicMock(embed_texts=lambda t: [[0.1, 0.2]]))
        monkeypatch.setattr(
            "services.retrieval.dense_retriever.search_dense",
            lambda client, vec, pid, top_k: [
                {"entity": {"chunk_id": "c1", "document_id": "d1",
                            "page": 5, "text": "hello"},
                 "distance": 0.73}])
        results = DenseRetriever().retrieve("question", project_id=1, top_k=8)
        assert len(results) == 1
        c = results[0]
        assert (c.chunk_id, c.document_id, c.page, c.content, c.score, c.method) == \
               ("c1", "d1", 5, "hello", 0.73, "dense")


class TestLexicalRetriever:
    def test_未启用_返回空列表_不参与召回(self):
        r = LexicalRetriever()
        assert r.enabled is False
        assert r.retrieve("q", 1) == []

    def test_启用时_明确抛未实现(self):
        r = LexicalRetriever()
        r.enabled = True
        with pytest.raises(NotImplementedError):
            r.retrieve("q", 1)


# ================= db/session：get_db 生成器 =================

class TestGetDB:
    def test_生成会话_结束必关闭(self, monkeypatch):
        fake_db = MagicMock()
        monkeypatch.setattr(session_mod, "SessionLocal", lambda: fake_db)
        gen = session_mod.get_db()
        assert next(gen) is fake_db
        gen.close()
        fake_db.close.assert_called_once()

    def test_会话中途异常_也保证关闭(self, monkeypatch):
        fake_db = MagicMock()
        monkeypatch.setattr(session_mod, "SessionLocal", lambda: fake_db)
        gen = session_mod.get_db()
        next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("boom"))   # 异常向上传播
        fake_db.close.assert_called_once()    # 但 finally 保证连接关闭
