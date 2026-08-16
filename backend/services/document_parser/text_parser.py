"""Plain-text parser with the common encodings used by project documents."""
from services.document_parser.base import ParsedDocument, ParsedPage, ParserInterface


class TextParser(ParserInterface):
    extensions = (".txt",)
    quality = "text"

    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, "rb") as f:
            raw = f.read()
        text = None
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("utf-8", errors="replace")
        page = ParsedPage(page_no=1, text=text, char_count=len(text))
        return ParsedDocument(pages=[page], meta={"total_pages": 1,
                                                   "needs_ocr_pages": 0})
