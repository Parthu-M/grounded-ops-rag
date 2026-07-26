from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_takehome.config import Settings
from ai_takehome.rag.ingestion import SUPPORTED_SUFFIXES, source_id_for
from ai_takehome.rag.service import RAGEngine
from ai_takehome.rag.uploads import UploadValidationError, save_uploads

app = FastAPI(
    title="Cost-Efficient RAG",
    version="1.0.0",
    description="Local Chroma-backed QA with grounded chunk citations.",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    path: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=2)
    k: int | None = Field(default=None, ge=1, le=50)
    metadata_filter: dict[str, Any] | None = None


_engine: RAGEngine | None = None
_engine_lock = Lock()


def get_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = RAGEngine(Settings.from_env())
    return _engine


def clear_engine_cache() -> None:
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.close()
            _engine = None


# Keep the familiar cache-clear hook used by tests and development tooling.
get_engine.cache_clear = clear_engine_cache  # type: ignore[attr-defined]


def upload_dir_for(settings: Settings) -> Path:
    upload_dir = Path(
        os.getenv("UPLOAD_DIR", str(settings.project_root / ".runtime/uploads"))
    )
    if not upload_dir.is_absolute():
        upload_dir = settings.project_root / upload_dir
    return upload_dir.resolve()


def managed_uploads(settings: Settings) -> dict[str, Path]:
    upload_dir = upload_dir_for(settings)
    if not upload_dir.exists():
        return {}
    return {
        source_id_for(candidate): candidate
        for candidate in upload_dir.iterdir()
        if candidate.is_file()
        and candidate.suffix.lower() in SUPPORTED_SUFFIXES
    }


@app.get("/health")
def health() -> dict[str, Any]:
    engine = get_engine()
    return {
        "status": "ok",
        "vectors": engine.store.count(),
        "store": "chroma",
        "embedding_model": engine.embedder.model_name,
        "embedding_dim": engine.embedder.dimensions,
        "chunk_size_words": engine.settings.chunk_size_words,
        "chunk_overlap_words": engine.settings.chunk_overlap_words,
        "max_upload_mb": int(os.getenv("MAX_UPLOAD_MB", "15")),
        "max_upload_files": int(os.getenv("MAX_UPLOAD_FILES", "10")),
    }


@app.post("/ingest")
def ingest(request: IngestRequest) -> dict[str, Any]:
    settings = Settings.from_env()
    path = Path(request.path)
    if not path.is_absolute():
        path = settings.project_root / path
    path = path.resolve()
    project_root = settings.project_root.resolve()
    if path != project_root and project_root not in path.parents:
        raise HTTPException(
            status_code=403,
            detail="Server-path ingestion is restricted to the project root.",
        )
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    try:
        results = get_engine().ingest(path)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "documents": len(results),
        "chunks_written": sum(item.chunks_written for item in results),
        "results": [item.__dict__ for item in results],
        "total_vectors": get_engine().store.count(),
    }


@app.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    settings = Settings.from_env()
    upload_dir = upload_dir_for(settings)
    max_files = max(1, int(os.getenv("MAX_UPLOAD_FILES", "10")))
    max_upload_mb = max(1, int(os.getenv("MAX_UPLOAD_MB", "15")))
    try:
        saved = await save_uploads(
            files,
            upload_dir=upload_dir,
            max_files=max_files,
            max_bytes_per_file=max_upload_mb * 1024 * 1024,
        )
        results = []
        for item in saved:
            ingested = get_engine().ingest(item.path)[0]
            results.append(
                {
                    **ingested.__dict__,
                    "original_name": item.original_name,
                    "stored_name": item.stored_name,
                    "size_bytes": item.size_bytes,
                }
            )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=str(exc)
        ) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "documents": len(results),
        "chunks_written": sum(item["chunks_written"] for item in results),
        "results": results,
        "total_vectors": get_engine().store.count(),
    }


@app.post("/query")
def query(request: QueryRequest) -> dict[str, Any]:
    try:
        return get_engine().ask(
            request.question,
            k=request.k,
            metadata_filter=request.metadata_filter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/documents")
def documents() -> dict[str, Any]:
    uploads = managed_uploads(Settings.from_env())
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "source": "",
            "source_id": "",
            "doc_type": "",
            "topic": "",
            "chunks": 0,
            "content_sha256": "",
            "managed_upload": False,
        }
    )
    for chunk in get_engine().store.all_chunks():
        metadata = chunk.metadata
        source_id = str(metadata.get("source_id", "unknown"))
        record = grouped[source_id]
        record.update(
            {
                "source": metadata.get("source", "unknown"),
                "source_id": source_id,
                "doc_type": metadata.get("doc_type", "unknown"),
                "topic": metadata.get("topic", "unknown"),
                "content_sha256": metadata.get("content_sha256", ""),
                "managed_upload": source_id in uploads,
            }
        )
        record["chunks"] += 1
    return {
        "documents": sorted(
            grouped.values(), key=lambda item: str(item["source"])
        )
    }


@app.delete("/documents/{source_id}")
def delete_document(source_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"s_[0-9a-f]{16}", source_id):
        raise HTTPException(status_code=400, detail="Invalid source ID.")

    engine = get_engine()
    chunks = engine.store.source_chunk_count(source_id)
    if chunks == 0:
        raise HTTPException(status_code=404, detail="Document not found.")

    upload_path = managed_uploads(Settings.from_env()).get(source_id)
    chunks_deleted = engine.store.delete_source(source_id)
    file_deleted = False
    if upload_path is not None and upload_path.exists():
        try:
            upload_path.unlink()
            file_deleted = True
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Vectors were removed, but the managed upload file "
                    f"could not be deleted: {exc}"
                ),
            ) from exc

    return {
        "source_id": source_id,
        "chunks_deleted": chunks_deleted,
        "file_deleted": file_deleted,
        "total_vectors": engine.store.count(),
    }


@app.post("/documents/{source_id}/delete")
def delete_document_compatibility(source_id: str) -> dict[str, Any]:
    """POST fallback for gateways that do not forward DELETE requests."""
    return delete_document(source_id)


@app.get("/reports")
def reports() -> dict[str, Any]:
    root = Settings.from_env().project_root

    def load(name: str) -> dict[str, Any]:
        path = root / "results" / name
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Report artifact is not available: {name}",
            )
        return json.loads(path.read_text(encoding="utf-8"))

    return {
        "rag": load("rag_evaluation.json"),
        "judge": load("judge_report.json"),
        "validation": load("judge_validation.json"),
        "cost": load("cost_comparison.json"),
    }


_STATIC_DIR = Path(__file__).resolve().parent / "static"
if (_STATIC_DIR / "index.html").exists():
    assets_dir = _STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="frontend-assets",
        )

    @app.get("/", include_in_schema=False)
    def frontend_root() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_fallback(path: str) -> FileResponse:
        candidate = (_STATIC_DIR / path).resolve()
        if (
            candidate.is_file()
            and _STATIC_DIR.resolve() in candidate.parents
        ):
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")
