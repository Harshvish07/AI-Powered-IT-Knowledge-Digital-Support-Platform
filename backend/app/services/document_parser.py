"""File validation and text extraction for uploaded knowledge documents.

Kept free of API/DB concerns so it can be unit tested in isolation and reused
by both the upload endpoint and the reindex path.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}

_PDF_MAGIC = b"%PDF-"
_FILENAME_UNSAFE_RE = re.compile(r"[^A-Za-z0-9 ._()\-]+")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_INLINE_WHITESPACE_RE = re.compile(r"[ \t]+")


class UnsupportedFileTypeError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class TextExtractionError(Exception):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None
    text: str


def sanitize_filename(filename: str) -> str:
    """A display-safe version of the filename for the DB/UI. Never used to build
    a filesystem path — storage keys files by document id instead."""
    name = Path(filename).name  # drop any directory components
    name = _FILENAME_UNSAFE_RE.sub("_", name).strip(" ._")
    return (name or "upload")[:255]


def validate_upload(*, filename: str, size_bytes: int, max_size_bytes: int) -> str:
    """Validates extension and size. Returns the canonical MIME type to store.

    Raises UnsupportedFileTypeError or FileTooLargeError.
    """
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension or '(none)'}'. Supported types: {supported}."
        )
    if size_bytes > max_size_bytes:
        raise FileTooLargeError(
            f"File is {size_bytes / (1024 * 1024):.1f} MB, which exceeds the "
            f"{max_size_bytes / (1024 * 1024):.0f} MB limit."
        )
    return SUPPORTED_EXTENSIONS[extension]


def looks_like_pdf(content_prefix: bytes) -> bool:
    """Lightweight magic-byte sniff so a renamed non-PDF can't masquerade as one."""
    return content_prefix[:5] == _PDF_MAGIC


def extract_text(path: Path, mime_type: str) -> list[ExtractedPage]:
    if mime_type == "application/pdf":
        return _extract_pdf(path)
    return _extract_plain_text(path)


def _extract_plain_text(path: Path) -> list[ExtractedPage]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return [ExtractedPage(page_number=None, text=text)]


def _extract_pdf(path: Path) -> list[ExtractedPage]:
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise TextExtractionError("The PDF is password-protected and cannot be processed.")
        pages: list[ExtractedPage] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(ExtractedPage(page_number=index, text=text))
        return pages
    except TextExtractionError:
        raise
    except Exception as exc:
        raise TextExtractionError(f"Could not read the PDF: {exc}") from exc


def clean_text(text: str) -> str:
    """Normalizes line endings and whitespace and drops control characters,
    while preserving blank-line paragraph breaks for the chunker."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _INLINE_WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()
