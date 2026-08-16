"""Standard library metadata, Evidence and graph behavior tests."""
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.standard_query.graph as graph_module
from agents.standard_query import nodes
from core.exceptions import AppError
from db.models import (Base, StandardChunk, StandardDocument, Tenant, User)
from services.retrieval.base import RetrievedChunk
from services.standard_document_service import (chunk_standard_pages,
                                                 ensure_not_duplicate,
                                                 parse_date)
from services.standard_evidence_service import build_standard_evidence


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Tenant(id=1, name="标准租户"),
        User(id=7, tenant_id=1, username="standard-user", password_hash="x"),
    ])
    session.commit()
    yield session
    session.close()


def _standard(db, document_id: str, region: str, status: str,
              code: str) -> StandardDocument:
    document = StandardDocument(
        id=document_id, tenant_id=1, standard_code=code,
        standard_name=code + "规范", version="2025", region=region,
        discipline="消防", standard_type="地方标准", status=status,
        effective_date=date(2025, 1, 1), file_name=code + ".pdf",
        file_path="x.pdf", created_by=7, parse_status="READY")
    db.add(document)
    db.commit()
    return document


def test_规范日期只接受ISO格式():
    assert parse_date("2026-08-17") == date(2026, 8, 17)
    assert parse_date("") is None
    with pytest.raises(AppError) as invalid:
        parse_date("2026/08/17")
    assert invalid.value.code == "STANDARD_DATE_INVALID"


def test_相同规范编号和版本不能重复入库(db):
    _standard(db, "std-one", "全国", "active", "GB 50000")

    with pytest.raises(AppError) as duplicate:
        ensure_not_duplicate(db, 1, "GB 50000", "2025")

    assert duplicate.value.code == "STANDARD_ALREADY_EXISTS"


def test_按条款切片并保留条款号():
    page = SimpleNamespace(
        page_no=3,
        text="总则\n5.2.1 消防车道宽度应符合要求。\n5.2.2 转弯半径应符合要求。")

    chunks = chunk_standard_pages([page], 1, "standard-doc-123456")

    assert [item["article"] for item in chunks] == [None, "5.2.1", "5.2.2"]
    assert "消防车道" in chunks[1]["content"]
    assert chunks[2]["page"] == 3


def test_深圳查询排序为深圳_广东_全国_且现行优先(db):
    documents = [
        _standard(db, "std-sz", "深圳", "active", "SJG 1"),
        _standard(db, "std-gd", "广东", "active", "DBJ 2"),
        _standard(db, "std-gb", "全国", "active", "GB 3"),
        _standard(db, "std-old", "深圳", "repealed", "SJG OLD"),
    ]
    chunks = []
    for index, document in enumerate(documents):
        chunk_id = "chunk-{}".format(index)
        db.add(StandardChunk(
            chunk_id=chunk_id, standard_document_id=document.id, tenant_id=1,
            content=document.standard_code + " 条文", page=1, article="5.2.1"))
        chunks.append(RetrievedChunk(
            chunk_id, document.id, 1, document.standard_code + " 条文",
            0.9 - index * 0.01, "dense"))
    db.commit()

    evidences = build_standard_evidence(
        db, 1, chunks, "深圳", top_k=4, query="SJG 1 第5.2.1条")

    assert [item["standard_code"] for item in evidences] == [
        "SJG 1", "DBJ 2", "GB 3", "SJG OLD"]
    assert evidences[0]["status"] == "active"
    assert evidences[0]["article"] == "5.2.1"


def test_版本与地区适用性检查():
    state = {"region": "深圳", "evidences": [
        {"standard_code": "GB 1", "status": "unknown", "region": "全国"},
        {"standard_code": "DBJ 2", "status": "repealed", "region": "广东"},
    ]}

    version = nodes.check_version(state)
    applicability = nodes.check_applicability(state)

    assert len(version["version_warnings"]) == 2
    assert applicability["applicability"]["matched_count"] == 2
    assert applicability["applicability"]["needs_warning"] is False


def test_无证据必须走人工兜底():
    confidence = nodes.check_confidence({"evidences": [], "region": None})
    assert confidence["fallback_needed"] is True
    assert nodes.route_after_confidence(confidence) == "fallback"
    fallback = nodes.fallback({})
    assert fallback["human_required"] is True
    assert "未找到足够依据" in fallback["answer"]


def test_规范图成功分支保留Evidence(monkeypatch):
    evidence = {"content": "5.2.1 条要求", "score": 0.9,
                "standard_code": "GB 1", "article": "5.2.1",
                "version": "2025", "region": "全国", "status": "active"}
    monkeypatch.setattr(graph_module, "retrieve",
                        lambda state: {"evidences_raw": ["raw"]})
    monkeypatch.setattr(graph_module, "build_evidence_node",
                        lambda state: {"evidences": [evidence]})
    monkeypatch.setattr(graph_module, "generate_answer",
                        lambda state: {"answer": "应符合条文要求 [E1]"})
    monkeypatch.setattr(graph_module, "validate_answer",
                        lambda state: {"regen_requested": False})

    result = graph_module.build_graph().invoke({
        "tenant_id": 1, "user_id": 7, "project_id": 1,
        "original_query": "消防要求", "top_k": 3})

    assert result["answer"] == "应符合条文要求 [E1]"
    assert result["confidence"] == 1.0
    assert result["evidences"][0]["standard_code"] == "GB 1"
