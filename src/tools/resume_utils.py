"""
Helpers for extracting raw text from an uploaded resume file (PDF or DOCX),
and small regex utilities used across the pipeline (finding emails / URLs
inside scraped or generated text).

These are plain Python helpers, not LangChain tools — resume parsing itself
happens later via an LLM call on the extracted text.
"""

import io
import re

import docx  # python-docx
from pypdf import PdfReader

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
URL_RE = re.compile(r"https?://[^\s)\]\"'<>]+")


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from an uploaded resume file.
    Supports .pdf and .docx. Raises ValueError for unsupported types.
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            text_parts.append(extracted)
        text = "\n".join(text_parts)

    elif lower.endswith(".docx"):
        document = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in document.paragraphs)

    elif lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")

    else:
        raise ValueError(
            f"Unsupported file type for '{filename}'. Please upload a .pdf, .docx, or .txt resume."
        )

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ValueError(
            "No extractable text was found in this file. If it's a scanned/image PDF, "
            "text extraction won't work — try a text-based export instead."
        )
    return text


def find_emails(text: str) -> list[str]:
    """Return a de-duplicated list of email addresses found in text."""
    seen = []
    for m in EMAIL_RE.findall(text or ""):
        if m not in seen:
            seen.append(m)
    return seen


def find_urls(text: str) -> list[str]:
    """Return a de-duplicated list of http(s) URLs found in text."""
    seen = []
    for m in URL_RE.findall(text or ""):
        cleaned = m.rstrip(".,;:)")
        if cleaned not in seen:
            seen.append(cleaned)
    return seen
