"""Generate and retrieve reviewable DOCX/PDF plan artifacts."""
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pymupdf as fitz
from sqlalchemy.orm import Session

from config import settings
from core.exceptions import NotFoundError
from db.models import GeneratedPlanDocument, PlanTask, Project


def _safe_name(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\r\n]+', "_", value).strip(" ._")
    return cleaned[:120] or "施工方案"


def _paragraph_xml(text: str, heading=False) -> str:
    style = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' if heading else ""
    return ('<w:p>{}<w:r><w:t xml:space="preserve">{}</w:t></w:r></w:p>'
            .format(style, escape(text)))


def _write_docx(path: Path, title: str, content: str) -> None:
    paragraphs = [_paragraph_xml(title, heading=True)]
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            paragraphs.append(_paragraph_xml(line[3:], heading=True))
        elif line.startswith("# "):
            paragraphs.append(_paragraph_xml(line[2:], heading=True))
        else:
            paragraphs.append(_paragraph_xml(raw_line))
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>{}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        '</w:sectPr></w:body></w:document>').format("".join(paragraphs))
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>')
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document_xml)


def _wrapped_lines(content: str, width: int = 45):
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line:
            yield ""
            continue
        prefix = ""
        if line.startswith("## "):
            line = line[3:]
            prefix = "【"
            line += "】"
        while len(line) > width:
            yield prefix + line[:width]
            prefix = ""
            line = line[width:]
        yield prefix + line


def _write_pdf(path: Path, title: str, content: str) -> None:
    pdf = fitz.open()
    page = pdf.new_page(width=595, height=842)
    y = 64
    page.insert_text((54, y), title, fontsize=18, fontname="china-s")
    y += 34
    for line in _wrapped_lines(content):
        if y > 790:
            page = pdf.new_page(width=595, height=842)
            y = 54
        page.insert_text((54, y), line or " ", fontsize=10.5,
                         fontname="china-s")
        y += 17
    pdf.save(path)
    pdf.close()


def generate(db: Session, task: PlanTask, final_content: str) -> GeneratedPlanDocument:
    existing = db.query(GeneratedPlanDocument).filter_by(task_id=task.id).first()
    if existing:
        return existing
    project = db.query(Project).filter_by(id=task.project_id).first()
    project_name = project.name if project else "项目"
    title = "{} - 施工方案（AI辅助起草）".format(project_name)
    base_name = _safe_name("{}_{}".format(project_name, task.task_type))
    directory = Path(settings.plan_storage_dir) / str(task.tenant_id) / str(task.project_id)
    directory.mkdir(parents=True, exist_ok=True)
    docx_path = directory / (task.id + ".docx")
    pdf_path = directory / (task.id + ".pdf")
    _write_docx(docx_path, title, final_content)
    _write_pdf(pdf_path, title, final_content)
    document = GeneratedPlanDocument(
        tenant_id=task.tenant_id, project_id=task.project_id,
        task_id=task.id, file_name=base_name,
        docx_path=str(docx_path), pdf_path=str(pdf_path),
        created_by=task.user_id)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get(db: Session, tenant_id: int, project_id: int,
        document_id: str) -> GeneratedPlanDocument:
    document = (db.query(GeneratedPlanDocument)
                .filter_by(id=document_id, tenant_id=tenant_id,
                           project_id=project_id).first())
    if document is None:
        raise NotFoundError("PLAN_DOCUMENT_NOT_FOUND", "生成的方案文档不存在")
    return document
