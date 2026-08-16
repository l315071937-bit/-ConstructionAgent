"""页面缩略图渲染（03 5 的 page image 接口）。PyMuPDF 渲染 JPEG。"""
import os

import pymupdf as fitz

from services.document_parser.router import OFFICE_EXTS


def get_preview_file_path(file_path: str) -> str:
    """Resolve the full PDF used by both thumbnails and document viewing."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return file_path
    if ext in OFFICE_EXTS:
        base = os.path.splitext(os.path.basename(file_path))[0]
        converted = os.path.join(os.path.dirname(file_path), "converted",
                                 base + ".pdf")
        if os.path.isfile(converted):
            return converted
    raise FileNotFoundError("renderable PDF not found")


def render_page(file_path: str, page_no: int, width: int = 400) -> bytes:
    doc = fitz.open(get_preview_file_path(file_path))
    if page_no < 1 or page_no > len(doc):
        raise ValueError("页码超出范围")
    page = doc[page_no - 1]
    zoom = max(width / max(page.rect.width, 1), 0.1)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return pix.tobytes("jpeg")
