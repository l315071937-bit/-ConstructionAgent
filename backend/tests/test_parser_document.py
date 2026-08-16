"""文档解析器（真实 PDF）与 document_service 落盘/入库/删除的单元测试。

注意：PyMuPDF 用例是"真文件"测试——用 fitz 现场生成 PDF 再解析，验证真实解析链路；
document_service 的 DB 依赖全部用替身，文件 IO 用 pytest 的 tmp_path 隔离。
"""
import os
from unittest.mock import MagicMock

import pytest

import services.document_service as doc_service
import services.preview_service as preview_service
from core.exceptions import NotFoundError
from services.document_parser.pymupdf_parser import PyMuPDFParser
from services.document_parser.text_parser import TextParser


# ============ PyMuPDFParser：真实 PDF 解析链路 ============

class TestPyMuPDFParser:
    def test_解析真实PDF_文本与OCR标记正确(self, tmp_path):
        import pymupdf as fitz

        pdf_path = tmp_path / "sample.pdf"
        d = fitz.open()
        p1 = d.new_page()
        p1.insert_text((72, 72), "TN-S system for temporary power")
        d.new_page()  # 第二页留空，应被标记为需要 OCR
        d.save(str(pdf_path))
        d.close()

        parsed = PyMuPDFParser().parse(str(pdf_path))

        assert parsed.meta["total_pages"] == 2
        assert parsed.meta["needs_ocr_pages"] == 1
        assert len(parsed.pages) == 2
        assert parsed.pages[0].page_no == 1
        assert "TN-S system" in parsed.pages[0].text
        assert parsed.pages[1].char_count == 0


class TestTextParser:
    @pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "gb18030"])
    def test_常用编码文本可解析(self, tmp_path, encoding):
        txt_path = tmp_path / "说明.txt"
        txt_path.write_bytes("配电箱安装要求".encode(encoding))

        parsed = TextParser().parse(str(txt_path))

        assert parsed.meta["total_pages"] == 1
        assert parsed.pages[0].page_no == 1
        assert parsed.pages[0].text == "配电箱安装要求"


class TestPreviewFile:
    def test_Office原文件解析到转换后的完整PDF(self, tmp_path):
        source = tmp_path / "document.docx"
        source.write_bytes(b"office")
        converted_dir = tmp_path / "converted"
        converted_dir.mkdir()
        converted = converted_dir / "document.pdf"
        converted.write_bytes(b"%PDF-preview")

        resolved = preview_service.get_preview_file_path(str(source))

        assert resolved == str(converted)

    def test_PDF直接作为完整预览文件(self, tmp_path):
        source = tmp_path / "document.pdf"
        source.write_bytes(b"%PDF-source")
        assert preview_service.get_preview_file_path(str(source)) == str(source)


# ============ save_upload：上传落盘 ============

class TestSaveUpload:
    def test_落盘_内容一致_扩展名小写保留(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doc_service.settings, "storage_dir", str(tmp_path))
        path = doc_service.save_upload(1, "电气方案.DOC", b"\x01\x02raw-bytes")
        assert os.path.exists(path)
        assert path.endswith(".doc")            # 扩展名转小写
        assert os.path.dirname(path) == str(tmp_path / "1")  # 按项目分目录
        with open(path, "rb") as f:
            assert f.read() == b"\x01\x02raw-bytes"

    def test_无扩展名_默认bin(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doc_service.settings, "storage_dir", str(tmp_path))
        path = doc_service.save_upload(1, "noext", b"x")
        assert path.endswith(".bin")

    def test_两次上传_文件名不冲突(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doc_service.settings, "storage_dir", str(tmp_path))
        p1 = doc_service.save_upload(1, "a.doc", b"1")
        p2 = doc_service.save_upload(1, "a.doc", b"2")
        assert p1 != p2  # uuid 文件名，不会覆盖


# ============ create_document / get_document / delete_document ============

class FakeDoc:
    def __init__(self, id="doc-1", file_path=None):
        self.id = id
        self.file_path = file_path
        self.project_id = 1
        self.parse_status = "READY"


class FakeQuery:
    """支持多条件 filter 的查询替身（Document.id == x, Document.project_id == y）。"""

    def __init__(self, docs_by_id):
        self._docs = docs_by_id
        self._conds = []

    def filter(self, *conds):
        self._conds = conds
        return self

    def first(self):
        for c in self._conds:
            if c.left.key == "id":
                return self._docs.get(c.right.value)
        return None


class FakeDB:
    def __init__(self, docs_by_id):
        self._docs = docs_by_id
        self.deleted = []

    def query(self, model):
        return FakeQuery(self._docs)

    def add(self, obj):
        self._docs[obj.id] = obj

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        pass


class TestCreateDocument:
    def test_创建文档_状态PENDING_字段齐全(self):
        db = FakeDB({})
        doc = doc_service.create_document(
            db, project_id=1, file_name="方案.doc",
            file_path="/tmp/x.doc", file_size=1024, user_id=7)
        assert doc.parse_status == "PENDING"
        assert doc.project_id == 1
        assert doc.file_name == "方案.doc"
        assert doc.created_by == 7
        assert doc.id in db._docs            # 已 add 进会话


class TestGetDocument:
    def test_文档存在_返回文档(self):
        db = FakeDB({"doc-1": FakeDoc("doc-1")})
        assert doc_service.get_document(db, 1, "doc-1").id == "doc-1"

    def test_文档不存在_抛404(self):
        db = FakeDB({})
        with pytest.raises(NotFoundError) as exc:
            doc_service.get_document(db, 1, "missing")
        assert exc.value.http_status == 404
        assert exc.value.code == "DOCUMENT_NOT_FOUND"


class TestDeleteDocument:
    def test_删除_清Milvus_删块_删库_删文件(self, tmp_path, monkeypatch):
        target = tmp_path / "a.doc"
        target.write_bytes(b"data")
        db = MagicMock()                      # 链式 delete 用 MagicMock 更省事
        milvus = MagicMock()
        monkeypatch.setattr(doc_service, "get_milvus", lambda: milvus)
        monkeypatch.setattr(doc_service, "delete_by_document", MagicMock())

        doc_service.delete_document(db, FakeDoc("doc-1", str(target)))

        doc_service.delete_by_document.assert_called_once_with(milvus, "doc-1")
        db.query.return_value.filter.return_value.delete.assert_called_once()
        db.delete.assert_called_once()
        assert not os.path.exists(target)     # 磁盘文件已删除

    def test_Milvus清理失败_不阻断数据库删除(self, tmp_path, monkeypatch):
        target = tmp_path / "a.doc"
        target.write_bytes(b"data")
        db = MagicMock()

        def boom(*args, **kwargs):
            raise RuntimeError("milvus down")

        monkeypatch.setattr(doc_service, "get_milvus", lambda: MagicMock())
        monkeypatch.setattr(doc_service, "delete_by_document", boom)

        doc_service.delete_document(db, FakeDoc("doc-1", str(target)))

        db.delete.assert_called_once()        # Milvus 挂了也要删干净 DB
        assert not os.path.exists(target)
