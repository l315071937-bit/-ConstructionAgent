"""Construction Plan nodes: Evidence-first generation with four HITL gates."""
import re

from langgraph.types import interrupt

from agents.construction_plan.prompts import build_section_messages
from core.exceptions import AppError
from core.llm_factory import get_llm
from core.logger import get_logger
from db.models import PlanTask
from db.session import SessionLocal
from services import (enterprise_plan_service, plan_document_service,
                      plan_evidence_service)

logger = get_logger("agent.construction_plan")

TASK_RULES = [
    ("waterproofing", "建筑", ("防水",)),
    ("fire_road", "消防", ("消防道路", "消防车道")),
    ("earthwork", "土建", ("土方", "开挖")),
    ("deep_excavation", "土建", ("深基坑", "基坑支护")),
    ("formwork_support", "结构", ("模板支撑", "高支模")),
    ("scaffolding", "土建", ("脚手架",)),
    ("lifting", "机械", ("起重吊装", "吊装")),
    ("demolition", "土建", ("拆除",)),
    ("structure", "结构", ("主体结构", "混凝土", "钢筋")),
    ("electrical", "电气", ("临时用电", "电气")),
]
HIGH_RISK_TYPES = {
    "deep_excavation", "formwork_support", "scaffolding", "lifting",
    "demolition",
}

COMMON_OUTLINE = ["工程概况", "编制依据", "施工部署与准备", "质量控制",
                  "安全与文明施工", "验收与资料管理", "应急处置"]
SPECIAL_SECTIONS = {
    "waterproofing": ["材料与基层要求", "防水施工工艺", "节点与成品保护"],
    "fire_road": ["道路结构与材料", "施工工艺", "消防车道功能保护"],
    "earthwork": ["测量放线与降排水", "土方开挖与运输", "边坡监测"],
    "deep_excavation": ["支护与降水", "分层开挖工艺", "监测与险情处置"],
    "formwork_support": ["支撑体系设计参数", "搭设与验收", "混凝土浇筑与拆除"],
    "scaffolding": ["架体构造参数", "搭设与验收", "使用监测与拆除"],
    "lifting": ["设备与吊具选型", "吊装工艺", "试吊与警戒"],
    "demolition": ["拆除顺序", "临时支撑与防护", "废料清运"],
    "structure": ["钢筋工程", "模板工程", "混凝土工程"],
    "electrical": ["负荷与配电系统", "线路敷设与保护", "检查与测试"],
    "general": ["材料与机械", "施工工艺", "成品保护"],
}


def validate_request(state: dict) -> dict:
    request = (state.get("original_request") or "").strip()
    if not request:
        raise AppError("VALIDATION_ERROR", "方案编制要求不能为空", 422)
    if not all(state.get(key) for key in (
            "task_id", "tenant_id", "user_id", "project_id")):
        raise AppError("VALIDATION_ERROR", "方案任务上下文不完整", 422)
    return {"warnings": [], "retry_count": 0, "fallback_level": 0,
            "human_required": False}


def analyze_plan_task(state: dict) -> dict:
    request = state["original_request"]
    task_type, discipline = "general", "建筑"
    construction_object = request
    for candidate, candidate_discipline, keywords in TASK_RULES:
        if any(keyword in request for keyword in keywords):
            task_type, discipline = candidate, candidate_discipline
            construction_object = next(
                keyword for keyword in keywords if keyword in request)
            break
    return {"task_type": task_type, "discipline": discipline,
            "construction_object": construction_object,
            "high_risk": task_type in HIGH_RISK_TYPES}


def retrieve_template(state: dict) -> dict:
    db = SessionLocal()
    try:
        candidates = enterprise_plan_service.find_templates(
            db, state["tenant_id"], state["task_type"])
        serialized = [enterprise_plan_service.serialize(item, True)
                      for item in candidates]
    finally:
        db.close()
    return {"template_candidates": serialized}


def human_confirm_template(state: dict) -> dict:
    candidates = state.get("template_candidates", [])
    reason = "TEMPLATE_SELECTION" if candidates else "GENERIC_TEMPLATE_PERMISSION"
    payload = {
        "kind": reason,
        "message": ("请选择本次方案使用的企业模板。" if candidates else
                    "未找到匹配的企业模板，是否允许基于项目资料和正式规范生成通用结构？"),
        "templates": [{key: item.get(key) for key in (
            "document_id", "name", "version", "task_type", "outline")}
            for item in candidates],
        "allowed_actions": (["select_template", "use_generic", "cancel"]
                            if candidates else ["use_generic", "cancel"]),
    }
    decision = interrupt(payload)
    action = (decision or {}).get("action")
    if action == "cancel":
        raise AppError("PLAN_CANCELLED", "用户已取消方案编制", 409)
    if action == "select_template":
        template_id = (decision or {}).get("template_id")
        selected = next((item for item in candidates
                         if item["document_id"] == template_id), None)
        if selected is None:
            raise AppError("PLAN_TEMPLATE_INVALID", "所选企业模板无效", 422)
        return {"template_id": selected["document_id"],
                "template_name": selected["name"],
                "template_content": selected.get("content", ""),
                "template_outline": selected.get("outline", []),
                "human_required": False, "human_reason": None,
                "human_payload": {}}
    if action != "use_generic":
        raise AppError("PLAN_HUMAN_DECISION_INVALID", "模板确认操作无效", 422)
    return {"template_id": None, "template_name": None,
            "template_content": None, "template_outline": [],
            "human_required": False, "human_reason": None,
            "human_payload": {}}


def generate_outline(state: dict) -> dict:
    template_outline = [str(item).strip() for item in
                        state.get("template_outline", []) if str(item).strip()]
    if template_outline:
        outline = template_outline
    else:
        specialized = SPECIAL_SECTIONS.get(
            state.get("task_type", "general"), SPECIAL_SECTIONS["general"])
        outline = COMMON_OUTLINE[:3] + specialized + COMMON_OUTLINE[3:]
    return {"outline": outline[:15]}


def human_confirm_outline(state: dict) -> dict:
    payload = {"kind": "OUTLINE_CONFIRMATION",
               "message": "请确认或调整方案目录后继续。",
               "outline": state.get("outline", []),
               "allowed_actions": ["confirm", "cancel"]}
    decision = interrupt(payload)
    action = (decision or {}).get("action")
    if action == "cancel":
        raise AppError("PLAN_CANCELLED", "用户已取消方案编制", 409)
    if action != "confirm":
        raise AppError("PLAN_HUMAN_DECISION_INVALID", "目录确认操作无效", 422)
    outline = (decision or {}).get("outline") or state.get("outline", [])
    outline = [str(item).strip()[:128] for item in outline
               if str(item).strip()][:15]
    if not outline:
        raise AppError("PLAN_OUTLINE_EMPTY", "方案目录不能为空", 422)
    return {"outline": outline, "human_required": False,
            "human_reason": None, "human_payload": {}}


def retrieve_reference_plans(state: dict) -> dict:
    db = SessionLocal()
    try:
        items = enterprise_plan_service.find_reference_plans(
            db, state["tenant_id"], state["task_type"])
        references = [enterprise_plan_service.serialize(item, True)
                      for item in items]
    finally:
        db.close()
    return {"reference_plans": references}


def retrieve_project_context(state: dict) -> dict:
    query = "{} 项目名称 工程概况 施工范围 材料 尺寸 做法".format(
        state["original_request"])
    result = plan_evidence_service.retrieve_project_evidence(
        state["project_id"], query)
    return {"project_evidences": result["evidences"],
            "warnings": state.get("warnings", []) + result["warnings"]}


def retrieve_standard_context(state: dict) -> dict:
    query = "{} 现行规范 施工 质量 验收 安全".format(
        state["original_request"])
    result = plan_evidence_service.retrieve_standard_evidence(
        state["tenant_id"], query)
    return {"standard_evidences": result["evidences"],
            "warnings": state.get("warnings", []) + result["warnings"]}


def _known_facts(evidences: list) -> dict:
    facts = {}
    pattern = re.compile(
        r"(?:C\d+|HRB\d+|\d+(?:\.\d+)?\s*(?:mm|cm|m|㎡|m2|MPa|层|栋))",
        re.IGNORECASE)
    for evidence in evidences:
        for value in pattern.findall(evidence.get("content", "")):
            facts.setdefault(value.casefold(), evidence.get("evidence_id"))
    return facts


def generate_plan_sections(state: dict) -> dict:
    project_evidences = state.get("project_evidences", [])
    standard_evidences = state.get("standard_evidences", [])
    plan_facts = _known_facts(project_evidences)
    sections = []
    warnings = list(state.get("warnings", []))
    for index, title in enumerate(state.get("outline", []), start=1):
        try:
            request = state["original_request"]
            if state.get("review_feedback"):
                request += "\n终审修改意见：" + state["review_feedback"]
            content = get_llm().chat(build_section_messages(
                title, request, plan_facts,
                project_evidences, standard_evidences,
                state.get("template_content") or "",
                state.get("reference_plans", [])), max_tokens=1400)
            if not content.strip():
                raise RuntimeError("LLM returned empty content")
        except Exception as exc:
            logger.error("plan section generation failed (%s): %s", title, exc)
            content = ("本章节自动生成失败。[待人工确认]\n"
                       "请依据右侧 Project Evidence 与 Standard Evidence 补充并审核。")
            warnings.append("“{}”章节生成降级，须人工补充。".format(title))
        sections.append({"section_id": "section_{:02d}".format(index),
                         "title": title, "status": "COMPLETED",
                         "content": content,
                         "evidence_ids": [item.get("evidence_id")
                                          for item in project_evidences +
                                          standard_evidences]})
    return {"generated_sections": sections, "plan_facts": plan_facts,
            "warnings": warnings}


def fact_check(state: dict) -> dict:
    evidence_text = " ".join(item.get("content", "").casefold()
                             for item in state.get("project_evidences", []))
    pattern = re.compile(
        r"(?:C\d+|HRB\d+|\d+(?:\.\d+)?\s*(?:mm|cm|m|㎡|m2|MPa|层|栋))",
        re.IGNORECASE)
    results = []
    for section in state.get("generated_sections", []):
        unsupported = sorted({value for value in pattern.findall(
            section["content"]) if value.casefold() not in evidence_text})
        results.append({"section_id": section["section_id"],
                        "status": "REVIEW" if unsupported else "PASS",
                        "unsupported_facts": unsupported})
    return {"fact_check_results": results}


def standard_check(state: dict) -> dict:
    evidences = state.get("standard_evidences", [])
    count = len(evidences)
    results = []
    citation_pattern = re.compile(r"\[S(\d+)\]")
    for section in state.get("generated_sections", []):
        citations = [int(item) for item in citation_pattern.findall(
            section["content"])]
        invalid = [item for item in citations if item > count]
        status = "PASS" if citations and not invalid else "REVIEW"
        results.append({"section_id": section["section_id"],
                        "status": status,
                        "invalid_citations": invalid,
                        "reason": ("未引用可确认现行有效的正式规范依据"
                                   if not citations else "")})
    return {"standard_check_results": results}


def completeness_check(state: dict) -> dict:
    text = " ".join(item["title"] + item["content"]
                    for item in state.get("generated_sections", []))
    checks = {
        "施工准备": ("准备", "部署"), "材料机械": ("材料", "机械", "设备"),
        "施工工艺": ("工艺", "施工"), "质量": ("质量",),
        "安全": ("安全",), "环保文明": ("环保", "文明"),
        "成品保护": ("成品保护",), "验收": ("验收",),
    }
    results = [{"item": name,
                "status": "PASS" if any(word in text for word in words)
                else "MISSING"} for name, words in checks.items()]
    return {"completeness_results": results}


def risk_check(state: dict) -> dict:
    text = " ".join(item["content"]
                    for item in state.get("generated_sections", []))
    risk_terms = ("高处作业", "临时用电", "机械", "消防", "基坑", "吊装",
                  "防护", "应急")
    results = [{"risk": item,
                "mentioned": item in text} for item in risk_terms]
    if state.get("high_risk"):
        results.insert(0, {
            "risk": "危大工程专家论证",
            "mentioned": True,
            "severity": "CRITICAL",
            "message": "本方案为 AI 辅助起草，须经专家论证后方可实施。",
        })
    return {"risk_results": results}


def build_final_content(state: dict) -> dict:
    parts = ["# AI 辅助起草声明",
             "本施工方案由 AI 辅助起草，必须由项目专业人员审核确认后方可使用。"]
    if state.get("high_risk"):
        parts.append("\n**危大工程警示：本方案须经专家论证后方可实施。**")
    for section in state.get("generated_sections", []):
        parts.extend(["\n## " + section["title"], section["content"]])
    warnings = list(dict.fromkeys(state.get("warnings", [])))
    review_items = []
    for result in state.get("fact_check_results", []):
        if result["status"] != "PASS":
            review_items.append("事实复核：{}".format(
                "、".join(result["unsupported_facts"])))
    for result in state.get("standard_check_results", []):
        if result["status"] != "PASS":
            review_items.append("规范复核：{}".format(result["section_id"]))
    for result in state.get("completeness_results", []):
        if result["status"] != "PASS":
            review_items.append("完整性补充：{}".format(result["item"]))
    warnings.extend(review_items)
    parts.extend(["\n## 人工审核清单"] +
                 ["- " + item for item in (warnings or ["请执行最终专业审核。"])])
    parts.append("\n## 正式依据清单")
    for index, item in enumerate(state.get("project_evidences", []), start=1):
        parts.append("- [P{}] {}，第 {} 页".format(
            index, item.get("file_name"), item.get("page")))
    for index, item in enumerate(state.get("standard_evidences", []), start=1):
        parts.append("- [S{}] {} {}，第 {} 页".format(
            index, item.get("standard_code") or item.get("standard_name"),
            item.get("article") or "", item.get("page")))
    return {"final_content": "\n".join(parts),
            "warnings": list(dict.fromkeys(warnings))}


def final_review(state: dict) -> dict:
    payload = {
        "kind": "FINAL_REVIEW",
        "message": ("危大工程红色警示：须经专家论证并由专业人员终审。"
                    if state.get("high_risk") else
                    "AI 初步检查已完成，请专业人员执行最终审核。"),
        "severity": "critical" if state.get("high_risk") else "warning",
        "outline": state.get("outline", []),
        "warnings": state.get("warnings", []),
        "fact_checks": state.get("fact_check_results", []),
        "standard_checks": state.get("standard_check_results", []),
        "completeness_checks": state.get("completeness_results", []),
        "risk_checks": state.get("risk_results", []),
        "preview": state.get("final_content", ""),
        "allowed_actions": ["approve", "return_modify", "cancel"],
    }
    decision = interrupt(payload)
    action = (decision or {}).get("action")
    if action == "cancel":
        raise AppError("PLAN_CANCELLED", "用户已取消方案编制", 409)
    if action not in {"approve", "return_modify"}:
        raise AppError("PLAN_HUMAN_DECISION_INVALID", "终审操作无效", 422)
    update = {"review_action": action, "human_required": False,
              "human_reason": None, "human_payload": {}}
    if action == "return_modify" and (decision or {}).get("outline"):
        update["outline"] = [str(item).strip()[:128]
                             for item in decision["outline"]
                             if str(item).strip()][:15]
    if action == "return_modify" and (decision or {}).get("comment"):
        update["review_feedback"] = decision["comment"]
        update["warnings"] = state.get("warnings", []) + [
            "终审修改意见：" + decision["comment"]]
    return update


def route_after_final_review(state: dict) -> str:
    return "modify" if state.get("review_action") == "return_modify" else "approve"


def generate_document(state: dict) -> dict:
    db = SessionLocal()
    try:
        task = db.query(PlanTask).filter_by(id=state["task_id"]).first()
        if task is None:
            raise AppError("PLAN_TASK_NOT_FOUND", "方案任务不存在", 404)
        document = plan_document_service.generate(
            db, task, state.get("final_content", ""))
    finally:
        db.close()
    base = "/api/v1/projects/{}/plans/documents/{}".format(
        state["project_id"], document.id)
    return {"document_id": document.id,
            "download_urls": {"docx": base + "/docx",
                              "pdf": base + "/pdf"}}
