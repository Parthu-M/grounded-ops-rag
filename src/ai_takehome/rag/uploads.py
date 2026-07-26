from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from ai_takehome.rag.ingestion import SUPPORTED_SUFFIXES


class UploadValidationError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class SavedUpload:
    original_name: str
    stored_name: str
    path: Path
    size_bytes: int


def _safe_filename(filename: str | None) -> str:
    original = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if not original:
        raise UploadValidationError("Every upload must have a filename.")
    suffix = Path(original).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise UploadValidationError(
            f"Unsupported file type for {original!r}. Supported: {supported}."
        )
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(original).stem).strip(
        ".-_"
    )
    if not stem:
        stem = "document"
    return f"{stem[:120]}{suffix}"


async def save_uploads(
    files: list[UploadFile],
    *,
    upload_dir: Path,
    max_files: int,
    max_bytes_per_file: int,
) -> list[SavedUpload]:
    if not files:
        raise UploadValidationError("Select at least one document to upload.")
    if len(files) > max_files:
        raise UploadValidationError(
            f"Upload at most {max_files} documents per request."
        )

    prepared: list[tuple[str, str, bytes]] = []
    seen_names: set[str] = set()
    for upload in files:
        stored_name = _safe_filename(upload.filename)
        key = stored_name.lower()
        if key in seen_names:
            raise UploadValidationError(
                f"Duplicate filename in this upload: {stored_name!r}."
            )
        seen_names.add(key)
        payload = await upload.read(max_bytes_per_file + 1)
        await upload.close()
        if len(payload) > max_bytes_per_file:
            limit_mb = max_bytes_per_file / (1024 * 1024)
            raise UploadValidationError(
                f"{stored_name!r} exceeds the {limit_mb:g} MB file limit.",
                status_code=413,
            )
        if not payload:
            raise UploadValidationError(f"{stored_name!r} is empty.")
        if Path(stored_name).suffix.lower() == ".pdf":
            if b"%PDF-" not in payload[:1024]:
                raise UploadValidationError(
                    f"{stored_name!r} does not appear to be a valid PDF."
                )
        prepared.append((upload.filename or stored_name, stored_name, payload))

    upload_dir.mkdir(parents=True, exist_ok=True)
    saved: list[SavedUpload] = []
    for original_name, stored_name, payload in prepared:
        destination = (upload_dir / stored_name).resolve()
        if upload_dir.resolve() not in destination.parents:
            raise UploadValidationError("Unsafe upload filename.")
        temporary = upload_dir / f".{stored_name}.{uuid.uuid4().hex}.tmp"
        temporary.write_bytes(payload)
        temporary.replace(destination)
        saved.append(
            SavedUpload(
                original_name=original_name,
                stored_name=stored_name,
                path=destination,
                size_bytes=len(payload),
            )
        )
    return saved
