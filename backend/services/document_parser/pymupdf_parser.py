"""PyMuPDF 解析器（默认实现档，01 52.3）。
License：AGPL-3.0/商业双许可——法务决策不通过时由 router 切换实现，接口不变。"""
import pymupdf as fitz  # PyMuPDF

from services.document_parser.base import ParsedDocument, ParsedPage, ParserInterface


class PyMuPDFParser(ParserInterface):
    extensions = (".pdf",)
    quality = "text"

    def parse(self, file_path: str) -> ParsedDocument:
        doc = fitz.open(file_path)
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(ParsedPage(page_no=i + 1, text=text, char_count=len(text)))
        meta = {"total_pages": len(doc), "needs_ocr_pages": 0}
        for p in pages:
            if p.char_count < 5:
                meta["needs_ocr_pages"] += 1
        return ParsedDocument(pages=pages, meta=meta)
