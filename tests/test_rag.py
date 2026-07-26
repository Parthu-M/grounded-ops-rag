from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from ai_takehome.rag.generation import NO_CONTEXT_ANSWER
from ai_takehome.rag.service import RAGEngine


def test_reingest_is_idempotent_and_replaces_obsolete_chunks(
    tmp_path: Path, settings_factory
) -> None:
    document = tmp_path / "policy.md"
    document.write_text(
        "# Policy.\n\n" + " ".join(f"token{i}" for i in range(95)),
        encoding="utf-8",
    )
    engine = RAGEngine(settings_factory())
    first = engine.ingest(document)[0]
    first_ids = {chunk.id for chunk in engine.store.all_chunks()}
    second = engine.ingest(document)[0]
    assert second.chunks_written == first.chunks_written
    assert engine.store.count() == first.chunks_written
    assert {chunk.id for chunk in engine.store.all_chunks()} == first_ids

    document.write_text(
        "# Policy.\n\n" + " ".join(f"replacement{i}" for i in range(55)),
        encoding="utf-8",
    )
    changed = engine.ingest(document)[0]
    changed_ids = {chunk.id for chunk in engine.store.all_chunks()}
    assert engine.store.count() == changed.chunks_written
    assert changed_ids.isdisjoint(first_ids)


def test_metadata_filter_and_no_context_abstention(
    tmp_path: Path, settings_factory
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "policy.md").write_text(
        "# Keys.\n\nAPI keys expire after seven days.", encoding="utf-8"
    )
    (tmp_path / "docs" / "hooks.html").write_text(
        "<h1>Hooks.</h1><p>Webhook signatures use HMAC-SHA256.</p>",
        encoding="utf-8",
    )
    engine = RAGEngine(settings_factory())
    engine.ingest(tmp_path / "docs")
    filtered = engine.store.search(
        "Which algorithm signs webhook requests?",
        k=3,
        metadata_filter={"doc_type": "html"},
        min_score=0,
    )
    assert filtered
    assert all(item.chunk.metadata["doc_type"] == "html" for item in filtered)

    response = engine.ask("What is the cafeteria aardvark menu?")
    assert response["answer"] == NO_CONTEXT_ANSWER
    assert response["contexts"] == []


def test_query_log_has_latency_chunk_count_and_usage(
    tmp_path: Path, settings_factory
) -> None:
    document = tmp_path / "facts.md"
    document.write_text(
        "# Facts.\n\nBackups are retained for 30 days.", encoding="utf-8"
    )
    settings = settings_factory()
    engine = RAGEngine(settings)
    engine.ingest(document)
    response = engine.ask("How long are backups retained?")
    assert response["citations"]
    line = settings.query_log_path.read_text(encoding="utf-8")
    assert '"retrieved_chunk_count"' in line
    assert '"latency_ms"' in line
    assert '"total_tokens"' in line


def test_pdf_text_is_ingested(tmp_path: Path, settings_factory) -> None:
    pdf_path = tmp_path / "retention.pdf"
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
        b"(PDF backups are retained for 45 days.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    with pdf_path.open("wb") as handle:
        writer.write(handle)

    engine = RAGEngine(settings_factory())
    result = engine.ingest(pdf_path)[0]
    assert result.chunks_written == 1
    chunk = engine.store.all_chunks()[0]
    assert chunk.metadata["doc_type"] == "pdf"
    assert "retained for 45 days" in chunk.text
