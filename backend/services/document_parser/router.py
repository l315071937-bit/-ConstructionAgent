"""DocumentParserRouter（01 52.2 冻结架构）：按文件类型路由解析器。
V0.1 已实现：.pdf → PyMuPDF
V0.1 占位：Office 系 → LibreOffice 转 PDF（需本机 soffice）
V0.1 未接：扫描件 PaddleOCR / 复杂版面 MinerU（预留扩展点）"""
import os
import shutil
import threading
import subprocess

from core.exceptions import AppError
from core.logger import get_logger
from services.document_parser.base import ParsedDocument, ParserInterface
from services.document_parser.pymupdf_parser import PyMuPDFParser

logger = get_logger("document_parser")

OFFICE_EXTS = {".doc", ".docx", ".xls", ".xlsx"}

# LibreOffice 单实例约束：并发转换会撞用户配置文件锁，必须串行
_soffice_lock = threading.Lock()


class DocumentParserRouter:
    def __init__(self):
        self._parsers: dict[str, ParserInterface] = {}
        for p in [PyMuPDFParser()]:
            for ext in p.extensions:
                self._parsers[ext] = p

    def register(self, ext: str, parser: ParserInterface) -> None:
        self._parsers[ext] = parser

    def parse(self, file_path: str) -> ParsedDocument:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self._parsers:
            return self._parsers[ext].parse(file_path)
        if ext in OFFICE_EXTS:
            return self._parsers[".pdf"].parse(self._to_pdf(file_path))
        raise AppError("UNSUPPORTED_FILE_TYPE",
                       "不支持的文件类型: {}".format(ext), 415)

    def _to_pdf(self, file_path: str) -> str:
        """LibreOffice headless 转 PDF（老式 .doc 的行业通用兜底）。"""
        # 优先 PATH，回退标准安装路径（MSI 安装后新进程可能未刷新 PATH）
        candidates = [
            shutil.which("soffice"), shutil.which("libreoffice"),
            r"C:/Program Files/LibreOffice/program/soffice.exe",
            r"C:/Program Files (x86)/LibreOffice/program/soffice.exe",
        ]
        soffice = next((c for c in candidates if c and os.path.exists(c)), None)
        if soffice is None:
            raise AppError("PARSE_FAILED",
                           "Office 文档解析需要 LibreOffice，请安装后重试或仅上传 PDF",
                           422)
        out_dir = os.path.join(os.path.dirname(file_path), "converted")
        os.makedirs(out_dir, exist_ok=True)
        with _soffice_lock:
            subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                            "--outdir", out_dir, file_path],
                           check=True, timeout=300, capture_output=True)
        base = os.path.splitext(os.path.basename(file_path))[0]
        pdf_path = os.path.join(out_dir, base + ".pdf")
        if not os.path.exists(pdf_path):
            raise AppError("PARSE_FAILED", "Office 转 PDF 失败", 422)
        logger.info("converted office file to pdf: %s", pdf_path)
        return pdf_path


_router = None


def get_parser_router() -> DocumentParserRouter:
    global _router
    if _router is None:
        _router = DocumentParserRouter()
    return _router
