from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from ai_takehome.rag.api import app, get_engine


def test_http_ingest_query_and_health(tmp_path, monkeypatch) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "policy.md").write_text(
        "# Retention.\n\nBackups are retained for 30 days.", encoding="utf-8"
    )
    reports_dir = tmp_path / "results"
    reports_dir.mkdir()
    for name in (
        "rag_evaluation.json",
        "judge_report.json",
        "judge_validation.json",
        "cost_comparison.json",
    ):
        (reports_dir / name).write_text(
            json.dumps({"artifact": name}), encoding="utf-8"
        )
    monkeypatch.setenv("AI_TAKEHOME_HOME", str(tmp_path))
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "api-chroma"))
    monkeypatch.setenv("QUERY_LOG_PATH", str(tmp_path / "api-queries.jsonl"))
    monkeypatch.setenv("EMBEDDING_DIM", "256")
    monkeypatch.setenv("CHUNK_SIZE_WORDS", "40")
    monkeypatch.setenv("CHUNK_OVERLAP_WORDS", "8")
    monkeypatch.setenv("MIN_RELEVANCE_SCORE", "0.08")
    monkeypatch.setenv("MAX_UPLOAD_FILES", "2")
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_engine.cache_clear()
    client = TestClient(app)
    ingested = client.post("/ingest", json={"path": str(corpus)})
    assert ingested.status_code == 200
    assert ingested.json()["total_vectors"] == 1
    answer = client.post(
        "/query", json={"question": "How long are backups retained?", "k": 2}
    )
    assert answer.status_code == 200
    assert answer.json()["citations"]
    health = client.get("/health")
    assert health.json()["vectors"] == 1
    assert health.json()["chunk_size_words"] == 40
    assert health.json()["chunk_overlap_words"] == 8

    uploaded = client.post(
        "/upload",
        files=[
            (
                "files",
                (
                    "uploaded-policy.md",
                    b"# Access.\n\nAccess reviews run every 90 days.",
                    "text/markdown",
                ),
            )
        ],
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["documents"] == 1
    assert uploaded.json()["total_vectors"] == 2
    assert uploaded.json()["results"][0]["stored_name"] == (
        "uploaded-policy.md"
    )

    reuploaded = client.post(
        "/upload",
        files=[
            (
                "files",
                (
                    "uploaded-policy.md",
                    b"# Access.\n\nAccess reviews now run every 60 days.",
                    "text/markdown",
                ),
            )
        ],
    )
    assert reuploaded.status_code == 200
    assert reuploaded.json()["total_vectors"] == 2

    pdf_buffer = BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 72 720 Td "
        b"(Uploaded PDF retention is 45 days.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(pdf_buffer)
    uploaded_pdf = client.post(
        "/upload",
        files=[
            (
                "files",
                (
                    "retention.pdf",
                    pdf_buffer.getvalue(),
                    "application/pdf",
                ),
            )
        ],
    )
    assert uploaded_pdf.status_code == 200
    assert uploaded_pdf.json()["total_vectors"] == 3
    assert uploaded_pdf.json()["results"][0]["stored_name"] == "retention.pdf"

    unsupported = client.post(
        "/upload",
        files=[("files", ("notes.txt", b"not supported", "text/plain"))],
    )
    assert unsupported.status_code == 400

    corrupt_pdf = client.post(
        "/upload",
        files=[
            (
                "files",
                ("corrupt.pdf", b"%PDF-1.7\nnot-a-real-pdf", "application/pdf"),
            )
        ],
    )
    assert corrupt_pdf.status_code == 400
    assert "corrupt" in corrupt_pdf.json()["detail"].lower()

    documents = client.get("/documents")
    assert documents.status_code == 200
    by_source = {
        item["source"]: item for item in documents.json()["documents"]
    }
    assert by_source["policy.md"]["chunks"] == 1
    assert by_source["uploaded-policy.md"]["chunks"] == 1
    assert by_source["uploaded-policy.md"]["managed_upload"] is True
    assert by_source["retention.pdf"]["chunks"] == 1
    assert by_source["retention.pdf"]["managed_upload"] is True
    reports = client.get("/reports")
    assert reports.status_code == 200
    assert reports.json()["rag"]["artifact"] == "rag_evaluation.json"

    uploaded_source_id = by_source["uploaded-policy.md"]["source_id"]
    deleted = client.delete(f"/documents/{uploaded_source_id}")
    assert deleted.status_code == 200
    assert deleted.json()["chunks_deleted"] == 1
    assert deleted.json()["file_deleted"] is True
    assert not (
        tmp_path / ".runtime" / "uploads" / "uploaded-policy.md"
    ).exists()
    remaining = client.get("/documents").json()["documents"]
    assert uploaded_source_id not in {
        item["source_id"] for item in remaining
    }

    missing = client.delete(f"/documents/{uploaded_source_id}")
    assert missing.status_code == 404
    missing_via_post = client.post(
        f"/documents/{uploaded_source_id}/delete"
    )
    assert missing_via_post.status_code == 404
    get_engine.cache_clear()


def test_engine_initialization_is_single_flight(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AI_TAKEHOME_HOME", str(tmp_path))
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "concurrent-chroma"))
    get_engine.cache_clear()

    with ThreadPoolExecutor(max_workers=8) as executor:
        engines = list(executor.map(lambda _: get_engine(), range(24)))

    assert len({id(engine) for engine in engines}) == 1
    assert engines[0].store.count() == 0
    get_engine.cache_clear()
