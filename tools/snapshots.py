"""Content-addressed source snapshots for deep-research reports.

A snapshot is the extracted text of a retrieved source, stored under the
SHA-256 of its UTF-8 bytes. Quotations bound to a snapshot can be re-verified
by anyone holding the snapshot store, and the hash in the ledger lets anyone
without it detect a different text.

Stores are searched in order:

1. ``<report>/evidence/snapshots/`` — committed with the report. Use only for
   text that may be redistributed (public-domain government records, openly
   licensed papers, the analyst's own measurements).
2. ``$DEEP_RESEARCH_SNAPSHOTS`` or ``<vault>/.snapshots/`` — a private,
   Git-ignored store for everything else. Back it up like any other evidence.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

USER_AGENT = "deep-research-snapshot/0.3 (+https://github.com/atchisonbrent/deep-research)"
MAX_BYTES = 40 * 1024 * 1024
TIMEOUT_SECONDS = 45
SHA_RE = re.compile(r"^[0-9a-f]{64}$")

_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "caption", "dd", "div", "dl", "dt",
    "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
    "li", "main", "nav", "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul",
}
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self.skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return canonical_text("".join(parser.parts))


def canonical_text(value: str) -> str:
    """Normalize line endings and runs of blank space so equal text hashes equally."""
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in value.split("\n")]
    collapsed: list[str] = []
    for line in lines:
        if line or (collapsed and collapsed[-1]):
            collapsed.append(line)
    return "\n".join(collapsed).strip() + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def locate(quote: str, snapshot_text: str) -> int:
    """Return the offset of ``quote`` in the whitespace-normalized snapshot, or -1."""
    return normalize_whitespace(snapshot_text).find(normalize_whitespace(quote))


def context(quote: str, snapshot_text: str, radius: int = 450) -> str:
    haystack = normalize_whitespace(snapshot_text)
    offset = locate(quote, snapshot_text)
    if offset < 0:
        return ""
    start = max(0, offset - radius)
    end = min(len(haystack), offset + len(normalize_whitespace(quote)) + radius)
    return ("…" if start else "") + haystack[start:end] + ("…" if end < len(haystack) else "")


def vault_store(root: Path) -> Path:
    configured = os.environ.get("DEEP_RESEARCH_SNAPSHOTS")
    return Path(configured).expanduser() if configured else root / ".snapshots"


def report_store(report: Path) -> Path:
    return report / "evidence" / "snapshots"


def stores(root: Path, report: Path) -> list[Path]:
    return [report_store(report), vault_store(root)]


def find_snapshot(root: Path, report: Path, digest: str) -> Path | None:
    for store in stores(root, report):
        candidate = store / f"{digest}.txt"
        if candidate.is_file():
            return candidate
    return None


def read_snapshot(root: Path, report: Path, digest: str) -> str | None:
    path = find_snapshot(root, report, digest)
    return path.read_text(encoding="utf-8") if path else None


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def store_snapshot(store: Path, text: str, metadata: dict[str, Any], raw: bytes | None = None) -> str:
    """Write canonical ``text`` and its metadata; return the text digest."""
    text = canonical_text(text)
    digest = sha256_text(text)
    target = store / f"{digest}.txt"
    if not target.exists():
        _write_atomic(target, text.encode("utf-8"))
    meta_path = store / f"{digest}.json"
    if not meta_path.exists():
        _write_atomic(meta_path, (json.dumps({"sha256": digest, **metadata}, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    if raw is not None and metadata.get("raw_sha256"):
        raw_path = store / "raw" / str(metadata["raw_sha256"])
        if not raw_path.exists():
            _write_atomic(raw_path, raw)
    return digest


def _pdf_to_text(raw: bytes) -> str:
    tool = shutil.which("pdftotext")
    if not tool:
        raise ValueError(
            "the response is a PDF and pdftotext (poppler) is not installed; extract the text with another tool "
            "and record it with `capture --from-file`"
        )
    result = subprocess.run([tool, "-layout", "-enc", "UTF-8", "-", "-"], input=raw, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise ValueError(f"pdftotext failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout.decode("utf-8", "replace")


def fetch(url: str) -> tuple[str, dict[str, Any], bytes]:
    """Retrieve ``url`` and return ``(text, metadata, raw_bytes)``.

    Raises ``ValueError`` for non-success responses, oversize bodies, and
    content that cannot be converted to text.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain,application/json;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code} retrieving {url}; record an access gap or capture an archive copy") from None
    except urllib.error.URLError as exc:
        raise ValueError(f"could not retrieve {url}: {exc.reason}") from None
    if len(raw) > MAX_BYTES:
        raise ValueError(f"response exceeds {MAX_BYTES} bytes; capture the relevant text manually")
    lowered = content_type.lower()
    if "pdf" in lowered or raw[:5] == b"%PDF-":
        text = _pdf_to_text(raw)
        kind = "pdf"
    elif "html" in lowered or raw.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html")):
        text = html_to_text(raw.decode(charset, "replace"))
        kind = "html"
    elif lowered.startswith("text/") or "json" in lowered or "xml" in lowered or not lowered:
        text = raw.decode(charset, "replace")
        kind = "text"
    else:
        raise ValueError(f"unsupported content type {content_type!r}; capture extracted text with `capture --from-file`")
    text = canonical_text(text)
    if len(normalize_whitespace(text)) < 200:
        raise ValueError(
            "retrieved text is under 200 characters, which usually means a script-rendered page, consent wall or block; "
            "capture the rendered text with a browser and `capture --from-file`"
        )
    metadata = {
        "method": "fetch",
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "extraction": kind,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "retrieved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    return text, metadata, raw


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))
