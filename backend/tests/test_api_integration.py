"""Focused API contract tests with authentication and infrastructure replaced."""
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import api.v1.documents as documents_api
import api.v1.assistant as assistant_api
import api.v1.folders as folders_api
import api.v1.projects as projects_api
import api.v1.retrieval as retrieval_api
import api.v1.standard_query as standard_query_api
import api.v1.standards as standards_api
from core.exceptions import AppError
from db.session import get_db
from dependencies import get_current_project, get_current_user


def make_app(router):
    app = FastAPI()

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc):
        return JSONResponse(status_code=exc.http_status,
                            content={"error": {"code": exc.code,
                                               "message": exc.message}})

    app.dependency_overrides[get_current_project] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=7, tenant_id=1, role="admin")
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    app.include_router(router, prefix="/api/v1")
    return app


class TestRetrievalAPI:
    def test_top_k传入graph_state并返回SSE(self, monkeypatch):
        received = {}
        conversation = SimpleNamespace(id="conv-1")

        class FakeGraph:
            async def astream(self, state, stream_mode):
                received.update(state)
                yield "updates", {"retrieve": {}}
                yield "values", {"answer": "回答", "evidences": [],
                                 "confidence": 0.0}

        monkeypatch.setattr(retrieval_api, "build_graph", lambda: FakeGraph())
        monkeypatch.setattr(
            retrieval_api.conversation_service, "get_or_create_conversation",
            lambda db, tenant_id, user_id, project_id, conversation_id: conversation)
        monkeypatch.setattr(retrieval_api.conversation_service,
                            "build_context", lambda db, item, query: "历史上下文")
        monkeypatch.setattr(retrieval_api.conversation_service,
                            "append_message", lambda *args, **kwargs: None)
        monkeypatch.setattr(retrieval_api.conversation_service,
                            "compact_if_needed", lambda *args, **kwargs: False)
        client = TestClient(make_app(retrieval_api.router))

        resp = client.post("/api/v1/projects/1/retrieval/query",
                           json={"question": "项目采用什么系统？", "top_k": 3})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert received["top_k"] == 3
        assert received["conversation_context"] == "历史上下文"
        assert '"conversation_id": "conv-1"' in resp.text
        assert "event: done" in resp.text

    def test_top_k越界由请求模型拒绝(self):
        client = TestClient(make_app(retrieval_api.router))
        resp = client.post("/api/v1/projects/1/retrieval/query",
                           json={"question": "问题", "top_k": 21})
        assert resp.status_code == 422


class TestDocumentsAPI:
    def test_不支持的扩展名立即返回415(self):
        client = TestClient(make_app(documents_api.router))
        resp = client.post("/api/v1/projects/1/documents",
                           files={"file": ("malware.exe", b"data")})
        assert resp.status_code == 415
        assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_受保护原文件以内联方式返回(self, tmp_path, monkeypatch):
        pdf = tmp_path / "sample.pdf"
        pdf.write_bytes(b"%PDF-test")
        doc = SimpleNamespace(id="doc-1", project_id=1,
                              file_name="sample.pdf", file_path=str(pdf))
        monkeypatch.setattr(documents_api.document_service, "get_document",
                            lambda db, project_id, document_id: doc)
        client = TestClient(make_app(documents_api.router))

        resp = client.get("/api/v1/projects/1/documents/doc-1/file")

        assert resp.status_code == 200
        assert resp.content == b"%PDF-test"
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.headers["content-disposition"].startswith("inline")

    def test_完整预览PDF以内联方式返回(self, tmp_path, monkeypatch):
        pdf = tmp_path / "converted.pdf"
        pdf.write_bytes(b"%PDF-preview")
        doc = SimpleNamespace(id="doc-1", project_id=1,
                              file_name="方案.docx", file_path="source.docx")
        monkeypatch.setattr(documents_api.document_service, "get_document",
                            lambda db, project_id, document_id: doc)
        monkeypatch.setattr(documents_api.preview_service,
                            "get_preview_file_path", lambda path: str(pdf))
        client = TestClient(make_app(documents_api.router))

        resp = client.get("/api/v1/projects/1/documents/doc-1/preview")

        assert resp.status_code == 200
        assert resp.content == b"%PDF-preview"
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.headers["content-disposition"].startswith("inline")


class TestProjectsAPI:
    def test_项目联想只返回服务层允许的项目(self, monkeypatch):
        received = {}
        project = SimpleNamespace(id=9, name="深圳市龙华区幼儿园")

        def suggest(db, user_id, query, limit):
            received.update(user_id=user_id, query=query, limit=limit)
            return [project]

        monkeypatch.setattr(projects_api.project_service,
                            "suggest_projects", suggest)
        monkeypatch.setattr(
            projects_api.project_service, "project_cards",
            lambda db, items: [{"project_id": item.id, "name": item.name,
                                "description": "", "document_count": 12,
                                "created_at": "2026-08-16T00:00:00Z"}
                               for item in items])
        client = TestClient(make_app(projects_api.router))

        resp = client.get("/api/v1/projects/suggestions",
                          params={"q": "深圳", "limit": 3})

        assert resp.status_code == 200
        assert resp.json()["items"][0]["project_id"] == 9
        assert received == {"user_id": 7, "query": "深圳", "limit": 3}

    def test_项目联想参数限制(self):
        client = TestClient(make_app(projects_api.router))

        assert client.get("/api/v1/projects/suggestions?q=深").status_code == 422
        assert client.get(
            "/api/v1/projects/suggestions?q=深圳&limit=4").status_code == 422


class TestFoldersAPI:
    def test_创建子文件夹传递父目录与当前项目(self, monkeypatch):
        received = {}
        folder = SimpleNamespace(
            id="child-1", parent_id="root-1", name="电气",
            created_at=SimpleNamespace(
                isoformat=lambda: "2026-08-17T00:00:00"))

        def create(db, project_id, user_id, name, parent_id):
            received.update(project_id=project_id, user_id=user_id,
                            name=name, parent_id=parent_id)
            return folder

        monkeypatch.setattr(folders_api.folder_service,
                            "create_folder", create)
        client = TestClient(make_app(folders_api.router))

        resp = client.post("/api/v1/projects/1/folders", json={
            "name": "电气", "parent_id": "root-1"})

        assert resp.status_code == 201
        assert resp.json()["parent_id"] == "root-1"
        assert received == {"project_id": 1, "user_id": 7,
                            "name": "电气", "parent_id": "root-1"}

    def test_目录下文档归档使用当前项目权限链(self, monkeypatch):
        received = {}

        def assign(db, project_id, document_id, folder_id):
            received.update(project_id=project_id, document_id=document_id,
                            folder_id=folder_id)

        monkeypatch.setattr(folders_api.folder_service,
                            "assign_document", assign)
        client = TestClient(make_app(folders_api.router))

        resp = client.put(
            "/api/v1/projects/1/folders/folder-1/documents/doc-1")

        assert resp.status_code == 204
        assert received == {"project_id": 1, "document_id": "doc-1",
                            "folder_id": "folder-1"}


class TestAssistantAPI:
    def test_输入路由使用当前登录用户(self, monkeypatch):
        received = {}

        def route_input(db, user_id, query, active_agent):
            received.update(user_id=user_id, query=query,
                            active_agent=active_agent)
            return {"type": "RULE_REPLY", "answer": "你好"}

        monkeypatch.setattr(assistant_api.input_router_service,
                            "route_input", route_input)
        client = TestClient(make_app(assistant_api.router))

        resp = client.post("/api/v1/assistant/route", json={"query": "你好"})

        assert resp.status_code == 200
        assert resp.json()["type"] == "RULE_REPLY"
        assert received == {"user_id": 7, "query": "你好",
                            "active_agent": "project"}


class TestStandardsAPI:
    def test_规范库拒绝不支持的文件类型(self):
        client = TestClient(make_app(standards_api.router))

        resp = client.post(
            "/api/v1/standards/documents",
            data={"standard_name": "测试规范"},
            files={"file": ("standard.exe", b"bad")})

        assert resp.status_code == 415
        assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_规范查询返回SSE与独立会话(self, monkeypatch):
        received = {}
        conversation = SimpleNamespace(id="standard-conv")

        class FakeGraph:
            async def astream(self, state, stream_mode):
                received.update(state)
                yield "updates", {"build_evidence": {"evidences": [{
                    "standard_code": "GB 1", "content": "条文"}]}}
                yield "values", {"answer": "规范回答 [E1]", "evidences": [{
                    "standard_code": "GB 1", "content": "条文"}],
                    "confidence": 1.0, "version_warnings": []}

        monkeypatch.setattr(standard_query_api, "build_graph", lambda: FakeGraph())
        monkeypatch.setattr(
            standard_query_api.conversation_service,
            "get_or_create_conversation",
            lambda db, tenant_id, user_id, project_id, conversation_id,
            agent_type: conversation)
        monkeypatch.setattr(standard_query_api.conversation_service,
                            "build_context", lambda *args: "规范历史")
        monkeypatch.setattr(standard_query_api.conversation_service,
                            "append_message", lambda *args, **kwargs: None)
        monkeypatch.setattr(standard_query_api.conversation_service,
                            "compact_if_needed", lambda *args: False)
        client = TestClient(make_app(standard_query_api.router))

        resp = client.post("/api/v1/projects/1/standards/query", json={
            "question": "GB 1 有什么要求", "top_k": 3})

        assert resp.status_code == 200
        assert "event: evidence" in resp.text
        assert "standard-conv" in resp.text
        assert received["tenant_id"] == 1
        assert received["conversation_context"] == "规范历史"
