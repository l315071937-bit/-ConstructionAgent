"""Construction Plan graph, durable HITL and formal-basis safety tests."""
import zipfile
from pathlib import Path
from uuid import uuid4
from types import SimpleNamespace

from langgraph.types import Command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.construction_plan import nodes
from agents.construction_plan.graph import build_graph
from db.models import (Base, EnterprisePlanDocument, PlanTask, Project,
                       ProjectMember, Tenant, User)
from services import (plan_document_service, plan_evidence_service,
                      plan_task_service)
from services.sqlalchemy_checkpointer import SQLAlchemyCheckpointSaver


def _database():
    database_path = (Path(plan_document_service.settings.storage_dir) /
                     ("plan-test-" + uuid4().hex + ".sqlite3"))
    engine = create_engine(
        "sqlite:///{}".format(database_path.as_posix()),
        connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    db.add_all([
        Tenant(id=1, name="方案租户"),
        User(id=7, tenant_id=1, username="planner", password_hash="x"),
        Project(id=9, tenant_id=1, name="测试项目", description="",
                created_by=7),
        ProjectMember(project_id=9, user_id=7, role="owner"),
        EnterprisePlanDocument(
            id="tpl-1", tenant_id=1, document_type="template",
            name="企业防水模板", task_type="waterproofing",
            discipline="建筑", version="2026", content="企业格式要求",
            outline_json=["工程概况", "防水施工工艺", "质量与安全"],
            created_by=7),
        PlanTask(
            id="plan-test", tenant_id=1, user_id=7, project_id=9,
            request="编制地下室防水施工方案", status="RUNNING",
            state_json={}),
    ])
    db.commit()
    return factory, db


class FakeLLM:
    def chat(self, messages, **kwargs):
        return "依据项目资料组织施工，防水高度 300mm [P1]；质量要求按现行条文执行 [S1]。"


def _project_evidence():
    return {"evidences": [{
        "evidence_id": "ev-1", "file_id": "doc-1",
        "file_name": "设计说明.pdf", "source_type": "PROJECT_DOCUMENT",
        "page": 2, "content": "地下室防水高度为300mm。", "score": 0.9,
        "thumbnail_url": None, "metadata": {},
    }], "warnings": []}


def _standard_evidence():
    return {"evidences": [{
        "evidence_id": "std-1", "file_id": "std-doc-1",
        "file_name": "GB正式规范.pdf", "source_type": "STANDARD_DOCUMENT",
        "page": 5, "content": "防水施工质量应按规定验收。", "score": 0.9,
        "standard_code": "GB 1", "standard_name": "正式规范",
        "article": "5.1", "status": "active", "metadata": {},
    }], "warnings": []}


def test_三个HITL节点可跨Graph实例恢复并生成文档(monkeypatch):
    factory, db = _database()
    monkeypatch.setattr(nodes, "SessionLocal", factory)
    output_dir = Path(plan_document_service.settings.storage_dir) / "plan-test-output"
    monkeypatch.setattr(plan_document_service.settings, "plan_storage_dir",
                        str(output_dir))
    monkeypatch.setattr(nodes, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(
        nodes.plan_evidence_service, "retrieve_project_evidence",
        lambda *args, **kwargs: _project_evidence())
    monkeypatch.setattr(
        nodes.plan_evidence_service, "retrieve_standard_evidence",
        lambda *args, **kwargs: _standard_evidence())
    config = {"configurable": {"thread_id": "plan-test"}}
    initial = {
        "task_id": "plan-test", "request_id": "plan-test",
        "tenant_id": 1, "user_id": 7, "project_id": 9,
        "original_request": "编制地下室防水施工方案",
    }

    graph = build_graph(SQLAlchemyCheckpointSaver(factory))
    graph.invoke(initial, config=config)
    first = graph.get_state(config)
    assert first.interrupts[0].value["kind"] == "TEMPLATE_SELECTION"

    graph = build_graph(SQLAlchemyCheckpointSaver(factory))
    graph.invoke(Command(resume={"action": "select_template",
                                 "template_id": "tpl-1"}), config=config)
    second = graph.get_state(config)
    assert second.interrupts[0].value["kind"] == "OUTLINE_CONFIRMATION"
    assert second.interrupts[0].value["outline"] == [
        "工程概况", "防水施工工艺", "质量与安全"]

    graph = build_graph(SQLAlchemyCheckpointSaver(factory))
    graph.invoke(Command(resume={"action": "confirm",
                                 "outline": ["工程概况", "防水施工工艺"]}),
                 config=config)
    third = graph.get_state(config)
    assert third.interrupts[0].value["kind"] == "FINAL_REVIEW"
    assert third.values["fact_check_results"][0]["status"] == "PASS"
    assert third.values["standard_evidences"][0]["status"] == "active"

    graph = build_graph(SQLAlchemyCheckpointSaver(factory))
    graph.invoke(Command(resume={"action": "approve"}), config=config)
    final = graph.get_state(config)
    assert not final.next
    assert final.values["document_id"]
    document = plan_document_service.get(
        db, 1, 9, final.values["document_id"])
    assert zipfile.is_zipfile(document.docx_path)
    assert Path(document.pdf_path).read_bytes()[:4] == b"%PDF"
    db.close()


def test_危大工程触发专家论证红色警示():
    analyzed = nodes.analyze_plan_task({
        "original_request": "编制深基坑支护施工方案"})
    risk = nodes.risk_check({
        **analyzed, "generated_sections": [{"content": "基坑应急措施"}]})

    assert analyzed["high_risk"] is True
    assert risk["risk_results"][0]["severity"] == "CRITICAL"
    assert "专家论证" in risk["risk_results"][0]["message"]


def test_测试样例和非现行规范不能作为正式依据():
    active = {"status": "active", "file_name": "GB 50000.pdf",
              "standard_name": "正式规范", "standard_code": "GB 50000"}
    test_sample = {**active, "file_name": "规范测试样例.txt"}
    unknown = {**active, "status": "unknown"}

    assert plan_evidence_service._is_formal_standard(active) is True
    assert plan_evidence_service._is_formal_standard(test_sample) is False
    assert plan_evidence_service._is_formal_standard(unknown) is False


def test_无模板时生成任务类型相关而非固定目录():
    waterproof = nodes.generate_outline({"task_type": "waterproofing"})
    lifting = nodes.generate_outline({"task_type": "lifting"})

    assert "防水施工工艺" in waterproof["outline"]
    assert "吊装工艺" in lifting["outline"]
    assert waterproof["outline"] != lifting["outline"]


def test_启动恢复只调度未完成方案任务(monkeypatch):
    factory, db = _database()
    db.add(PlanTask(
        id="plan-done", tenant_id=1, user_id=7, project_id=9,
        request="已完成", status="COMPLETED", state_json={}))
    db.commit()
    scheduled = []

    class FakeThread:
        def __init__(self, target, args, **kwargs):
            scheduled.append(args[0])

        def start(self):
            pass

    monkeypatch.setattr(plan_task_service, "SessionLocal", factory)
    monkeypatch.setattr(plan_task_service.threading, "Thread", FakeThread)

    count = plan_task_service.recover_incomplete_tasks()

    assert count == 1
    assert scheduled == ["plan-test"]
    db.close()
