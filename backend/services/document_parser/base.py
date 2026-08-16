"""ParserInterface（01 52.2 抽象层）：文档解析统一契约。
真实可替换场景：PyMuPDF(AGPL 待法务) 与 pypdf/pdfplumber；
复杂版面 MinerU 兜底；扫描件 PaddleOCR。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedPage:
    page_no: int
    text: str
    char_count: int = 0
    bbox: dict | None = None


@dataclass
class ParsedDocument:
    pages: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class ParserInterface(ABC):
    extensions: tuple = ()
    quality: str = "text"

    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument: ...
