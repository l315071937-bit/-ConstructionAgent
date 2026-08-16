"""页面缩略图渲染（03 5 的 page image 接口）。PyMuPDF 渲染 JPEG。"""
import pymupdf as fitz


def render_page(file_path: str, page_no: int, width: int = 400) -> bytes:
    doc = fitz.open(file_path)
    if page_no < 1 or page_no > len(doc):
        raise ValueError("页码超出范围")
    page = doc[page_no - 1]
    zoom = max(width / max(page.rect.width, 1), 0.1)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return pix.tobytes("jpeg")
