from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import Path


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        elif tag in {"p", "br", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in {"p", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def load_document(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return path.read_text(encoding="utf-8"), "md"
    if suffix in {".html", ".htm"}:
        parser = _HTMLTextExtractor()
        parser.feed(path.read_text(encoding="utf-8"))
        text = html.unescape(" ".join(parser.parts))
        return re.sub(r"\n\s*\n+", "\n\n", text), "html"
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            from pypdf.errors import PyPdfError
        except ImportError as exc:
            raise RuntimeError(
                "PDF support requires pypdf; install project dependencies."
            ) from exc
        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise ValueError(
                    f"Encrypted PDF {path.name!r} cannot be ingested."
                )
            pages = [page.extract_text() or "" for page in reader.pages]
        except (PyPdfError, OSError) as exc:
            raise ValueError(
                f"Could not read PDF {path.name!r}; the file may be corrupt."
            ) from exc
        return "\n\n".join(pages), "pdf"
    raise ValueError(f"Unsupported file type: {path.suffix}")


def infer_topic(path: Path, text: str) -> str:
    for line in text.splitlines():
        candidate = re.sub(r"^[#\s]+", "", line).strip()
        if candidate:
            return candidate[:80].lower().replace(" ", "-")
    return path.stem.lower().replace(" ", "-")
