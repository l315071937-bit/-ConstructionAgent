"""services.document_service.chunk_pages 与 services.evidence_service.build_evidence 的单元测试。

依赖策略（真实项目通用做法）：
- chunk_pages 是纯函数，直接构造最小替身对象（FakePage）；
- build_evidence 依赖 SQLAlchemy Session，用伪造 DB 替身，不连真实数据库。
"""
from services.document_service import CHUNK_MAX_CHARS, chunk_pages
from services.evidence_service import build_evidence
from services.retrieval.base import RetrievedChunk


class FakePage:
    """ParsedPage 的最小替身：只带被测函数用到的两个字段。"""

    def __init__(self, page_no: int, text: str):
        self.page_no = page_no
        self.text = text


class FakeDocument:
    def __init__(self, doc_id: str, file_name: str):
        self.id = doc_id
        self.file_name = file_name


class FakeQuery:
    """伪造 db.query(...).filter(...).first() 链式调用。"""

    def __init__(self, docs_by_id: dict):
        self._docs = docs_by_id
        self._cond = None

    def filter(self, cond):
        self._cond = cond
        return self

    def first(self):
        # cond 形如 Document.id == "doc-1"，取右侧绑定的字面量作为查询键
        doc_id = self._cond.right.value
        return self._docs.get(doc_id)


class FakeDB:
    """伪造 Session：只实现 build_evidence 用到的接口，并统计查询次数。"""

    def __init__(self, docs_by_id: dict):
        self._docs = docs_by_id
        self.query_count = 0

    def query(self, model):
        self.query_count += 1
        return FakeQuery(self._docs)


def make_chunk(document_id="doc-1234567890ab", score=0.7,
               content="内容", page=3) -> RetrievedChunk:
    return RetrievedChunk(chunk_id="c1", document_id=document_id, page=page,
                          content=content, score=score, method="dense")


# ============ chunk_pages：按页切片 + 超长分段（CHUNK_MAX_CHARS=800） ============

class TestChunkPages:
    def test_短文本一页一切片_字段齐全(self):
        chunks = chunk_pages([FakePage(1, "临时用电采用TN-S系统")], 1, "doc-1234567890ab")
        assert len(chunks) == 1
        assert chunks[0]["chunk_id"] == "doc-12345678_1_0"  # document_id 取前 12 位
        assert chunks[0]["page"] == 1
        assert chunks[0]["project_id"] == 1
        assert chunks[0]["content"] == "临时用电采用TN-S系统"
        assert chunks[0]["source_type"] == "PROJECT_DOCUMENT"

    def test_空白页被跳过(self):
        chunks = chunk_pages([FakePage(1, "  \n  "), FakePage(2, "有内容")], 1, "doc-x")
        assert len(chunks) == 1
        assert chunks[0]["page"] == 2

    def test_超长文本按800字分段_内容不丢失(self):
        text = "电" * (CHUNK_MAX_CHARS * 2 + 50)  # 1650 字 -> 3 段
        chunks = chunk_pages([FakePage(1, text)], 1, "doc-1234567890ab")
        assert len(chunks) == 3
        assert [c["chunk_id"] for c in chunks] == [
            "doc-12345678_1_0", "doc-12345678_1_1", "doc-12345678_1_2"]
        # 关键不变量：拼接回来与原文本逐字一致（不能丢字/错位）
        assert "".join(c["content"] for c in chunks) == text

    def test_恰好800字边界只切一段(self):
        chunks = chunk_pages([FakePage(1, "电" * CHUNK_MAX_CHARS)], 1, "doc-x")
        assert len(chunks) == 1


# ============ build_evidence：检索块 -> 证据 dict ============

class TestBuildEvidence:
    def test_正常映射_文件名分数截断链接齐全(self):
        db = FakeDB({"doc-1": FakeDocument("doc-1", "电气施工方案.doc")})
        evs = build_evidence(db, 7, [make_chunk(document_id="doc-1",
                                                score=0.123456789,
                                                content="长内容" * 200)])
        ev = evs[0]
        assert ev["evidence_id"] == "ev_7_0"
        assert ev["file_name"] == "电气施工方案.doc"
        assert ev["score"] == 0.1235          # round(, 4)
        assert len(ev["content"]) == 600      # 截断到 600 字
        assert ev["thumbnail_url"] == "/api/v1/projects/7/documents/doc-1/pages/3/image"
        assert ev["metadata"] == {"chunk_id": "c1", "project_id": 7, "method": "dense"}

    def test_文档查不到_文件名回退为document_id(self):
        db = FakeDB({})
        evs = build_evidence(db, 1, [make_chunk(document_id="ghost-doc")])
        assert evs[0]["file_name"] == "ghost-doc"

    def test_同文档多块_只查库一次_doc_cache生效(self):
        db = FakeDB({"doc-1": FakeDocument("doc-1", "a.doc")})
        chunks = [make_chunk(document_id="doc-1") for _ in range(3)]
        evs = build_evidence(db, 1, chunks)
        assert len(evs) == 3
        assert db.query_count == 1  # 缓存命中，后续两块不再查库
