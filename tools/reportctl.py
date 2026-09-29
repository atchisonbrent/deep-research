#!/usr/bin/env python3
"""Initialize, validate, and index truth-assessment reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snapshots  # noqa: E402  (sibling standard-library module)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CITE_RE = re.compile(r"\[(\d+)\]")
CITE_GROUP_RE = re.compile(r"(?:\[\d+\])+")
SOURCE_LINE_RE = re.compile(r"^\[(\d+)\]\s+(https?://\S+?)(?:\s+—\s+.*)?$")
SOURCES_HEADER_RE = re.compile(r"^## Sources\s*$", re.IGNORECASE)
ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{1,31}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Abbreviations whose trailing period must not end a sentence. Matched
# case-sensitively as whole tokens; extend deliberately rather than broadly.
ABBREVIATIONS = (
    "U.S.", "U.K.", "U.N.", "E.U.", "U.A.E.", "D.C.", "e.g.", "i.e.", "etc.",
    "vs.", "cf.", "al.", "approx.", "Dr.", "Mr.", "Mrs.", "Ms.", "Jr.", "Sr.",
    "Inc.", "Ltd.", "Co.", "Corp.", "No.", "St.", "Fig.", "Gen.", "Lt.", "Col.",
    "Sen.", "Rep.", "Gov.", "Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.",
    "Aug.", "Sep.", "Sept.", "Oct.", "Nov.", "Dec.",
)
# An abbreviation is protected only when the next token does not look like a
# sentence start: it is followed by a lowercase word, a digit, a citation
# group, or punctuation continuing the clause. ``Acme Inc. It filed`` splits;
# ``Dr. Smith`` and ``U.S. forces`` do not. Title forms followed by a
# capitalised proper noun are listed separately and always protected.
TITLE_ABBREVIATIONS = ("Dr.", "Mr.", "Mrs.", "Ms.", "Jr.", "Sr.", "St.", "Gen.", "Lt.", "Col.", "Sen.", "Rep.", "Gov.", "Fig.", "No.")
_ABBR_ALT = "|".join(re.escape(a) for a in sorted(ABBREVIATIONS, key=len, reverse=True))
_TITLE_ALT = "|".join(re.escape(a) for a in sorted(TITLE_ABBREVIATIONS, key=len, reverse=True))
# A citation group directly after the period (``Jan.[1]``) marks a sentence
# end, so it is deliberately *not* a protecting context.
ABBREVIATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:(" + _TITLE_ALT + r")(?=\s+[A-Z0-9])|(" + _ABBR_ALT + r")(?=\s+[a-z0-9(\"'\u201c\u2018]|\s*[,;:)\]]))"
)
SENTENCE_RE = re.compile(r".*?[.!?][\"'\u201d\u2019)]*(?:\[\d+\])*(?=\s+|$)|.+$")
# Scaffold placeholder marker. ``init`` writes it into every placeholder
# sentence; the validator rejects any remaining occurrence. Ordinary prose that
# happens to say "replace with" is unaffected.
PLACEHOLDER_MARKER = "[[deep-research placeholder]]"
PLACEHOLDER_PREFIX = PLACEHOLDER_MARKER + " Replace with "
EVIDENCE_KINDS = {"excerpt", "artifact"}
# Claim anchors tie report prose to assessment claims or hypotheses: ``…text.[3]{C4}``.
ANCHOR_RE = re.compile(r"\{([A-Z][A-Z0-9_-]{1,31}(?:\s*,\s*[A-Z][A-Z0-9_-]{1,31})*)\}")
SEARCH_PURPOSES = {"map", "support", "counter", "primary", "gap", "update"}
SOURCE_DISPOSITIONS = {"cited", "background-only", "superseded-by-better-source", "duplicate", "irrelevant", "failed-retrieval", "rejected-unreliable"}
EXCERPT_VERDICTS = {"supports", "partial", "contradicts", "unrelated"}
PROSE_VERDICTS = {"faithful", "overstates", "understates", "contradicts", "not-anchored"}
# Gaps that claim evidence was sought must show the searches that sought it.
SEARCHED_GAP_KINDS = {"missing-primary", "access", "unresolved-contradiction"}
GAP_KINDS = {"matrix-cell", "access", "missing-primary", "unresolved-identity", "unresolved-contradiction", "not-researched", "other"}

SOURCE_TYPES = {
    "primary-record", "wire-service", "specialist", "government",
    "advocacy", "analysis", "social", "technical-documentation",
    "code-repository", "benchmark", "market-data", "regulatory-filing",
    "company-communication", "academic-paper", "patent", "other",
}
ACCESS = {"full", "partial", "snippet"}
DIRECTNESS = {"direct", "near-direct", "secondary", "commentary"}
RATINGS = {"high", "medium", "low", "unknown"}
CLAIM_KINDS = {"fact", "attributed", "inference", "forecast", "unknown"}
CLAIM_STATUS = {"confirmed", "probable", "contested", "unsupported", "unknown"}
IMPORTANCE = {"load-bearing", "supporting", "context"}
REPORT_STATUS = {"draft", "reviewed", "superseded"}
RESEARCH_MODES = {
    "general", "event-assessment", "historical-analysis", "technology-landscape",
    "state-of-practice", "market-analysis", "company-research", "entity-background",
    "release-forecast", "policy-analysis", "legal-regulatory", "scientific-synthesis",
    "security-incident", "comparative-analysis", "product-landscape", "due-diligence",
}
# Modes whose questions are inherently causal or forecast-shaped and therefore
# require at least one competing hypothesis. Other modes may still add
# hypotheses when a forecast claim exists.
HYPOTHESIS_REQUIRED_MODES = {"release-forecast", "event-assessment", "security-incident"}
# Mode-specific report.md skeletons. Section lists mirror the "Output sections"
# of skills/deep-research/references/modes/<mode>.md; keep them in sync.
MODE_SECTIONS: dict[str, list[str]] = {
    "general": ["Verdict", "What is observed", "What is assessed", "Competing hypotheses", "Gaps and falsifiers"],
    "event-assessment": ["Bottom line", "What happened", "Disputed claims and competing accounts", "Goals and results", "Human and economic cost", "Consequences and second-order effects", "Forecast and update triggers", "Source-confidence map", "Gaps and falsifiers"],
    "historical-analysis": ["Verdict", "Established fact pattern", "Interpretive disputes and their evidence", "Causal assessment", "What the record cannot support", "Sources and provenance notes"],
    "technology-landscape": ["Verdict", "State of the technology", "Capability boundaries and maturity", "Deployment reality", "Alternatives and tradeoffs", "Unresolved bottlenecks", "Trajectory and update triggers", "Gaps"],
    "state-of-practice": ["Verdict", "Established practice", "Emerging and contested practice", "Deprecated or discredited practice", "Evidence linking practice to outcomes", "Context dependence and transfer limits", "Gaps"],
    "market-analysis": ["Verdict", "Market definition and boundary", "Size range and basis", "Segments and structure", "Economics and drivers", "Competitive structure", "Scenarios and sensitivities", "Forecast triggers", "Gaps"],
    "company-research": ["Verdict", "Products and business model", "Execution record", "Financial and operational position", "Competitive position and claimed advantages", "Dependencies and risks", "Open questions", "Gaps"],
    "entity-background": ["Verdict", "Identity resolution", "Affiliations and roles", "Track record", "Documented conflicts or controversies", "Not established", "Gaps"],
    "release-forecast": ["Verdict", "Release ladder status", "Evidence path for each signal", "Base rates and dependencies", "Blockers", "Earliest, central, and late cases", "Update triggers", "Gaps"],
    "policy-analysis": ["Verdict", "The actual rule", "Implementation and enforcement state", "Affected groups and incentives", "Observed and modelled effects", "Legal and operational uncertainty", "Scenarios and triggers", "Gaps"],
    "legal-regulatory": ["Verdict", "Jurisdiction, actors, and date", "Obligations and exposures", "Enforcement record", "Open interpretive questions", "Outcome scenarios", "Where professional judgment is required", "Gaps"],
    "scientific-synthesis": ["Verdict", "Research question", "Evidence body", "Methods, populations, and effect sizes", "Replication and retraction state", "Consensus and live disputes", "Limitations and confounders", "Gaps"],
    "security-incident": ["Bottom line", "Vector and vulnerability", "Timeline", "Scope and impact", "Attribution and its evidence", "Remediation state", "Competing accounts and forecast", "Gaps and falsifiers"],
    "comparative-analysis": ["Verdict", "Comparison contract", "Eligibility gate", "Criteria matrix", "Normalized cost table", "Identity and fit gaps", "Who should choose each option", "Sensitivity to changed priorities", "Refresh-at-decision checklist"],
    "product-landscape": ["Verdict", "Category map and segments", "Decision criteria that matter", "Option families and tradeoffs", "Value frontier and premium cases", "Reliability, repairability, and lock-in", "Category direction", "Purchase-time facts to refresh"],
    "due-diligence": ["Verdict and go/no-go conditions", "Decision, threshold, and red-flag list", "Verified facts", "Unresolved representations", "Red flags", "Dependency and concentration map", "Downside cases", "Evidence requests", "Gaps"],
}
assert set(MODE_SECTIONS) == RESEARCH_MODES


def write_json(path: Path, payload: Any) -> None:
    """Atomically replace ``path`` with ``payload`` serialized as JSON."""
    import os
    import tempfile

    data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
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


def write_text_atomic(path: Path, content: str) -> None:
    import os
    import tempfile

    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing required file: {path.name}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path.name}: {exc}") from None


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_datetime(value: Any) -> bool:
    if not text(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_temporal(value: Any) -> datetime | None:
    """Parse an ISO date or datetime; date-only means unknown time.

    Timezone-naive datetimes are interpreted as UTC.
    """
    if not text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def is_date_only(value: Any) -> bool:
    return isinstance(value, str) and bool(DATE_ONLY_RE.fullmatch(value.strip()))


def not_after(earlier: Any, later: Any) -> bool:
    """True when ``earlier`` is at or before ``later``.

    Two full datetimes compare as UTC instants. If either side is date-only,
    the comparison falls back to calendar days in UTC, because a date carries
    no time of day to compare against.
    """
    earlier_dt = parse_temporal(earlier)
    later_dt = parse_temporal(later)
    if earlier_dt is None or later_dt is None:
        return True
    if is_date_only(earlier) or is_date_only(later):
        return earlier_dt.astimezone(timezone.utc).date() <= later_dt.astimezone(timezone.utc).date()
    return earlier_dt <= later_dt


def strictly_before(earlier: Any, later: Any) -> bool:
    """True when ``earlier`` is strictly before ``later`` under the same
    instant/calendar-day semantics as :func:`not_after`."""
    earlier_dt = parse_temporal(earlier)
    later_dt = parse_temporal(later)
    if earlier_dt is None or later_dt is None:
        return True
    if is_date_only(earlier) or is_date_only(later):
        return earlier_dt.astimezone(timezone.utc).date() < later_dt.astimezone(timezone.utc).date()
    return earlier_dt < later_dt


def approx_ge(value: float, threshold: float) -> bool:
    """Float-tolerant ``value >= threshold`` for probability arithmetic."""
    return value + 1e-9 >= threshold


def valid_url(value: Any) -> bool:
    if not text(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def valid_range(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
        and 0 <= value[0] <= value[1] <= 1
    )


def split_cited_sentences(value: str) -> list[str]:
    """Split sentences while retaining trailing citation groups.

    Known abbreviations (``U.S.``, ``e.g.``, ``Inc.``) do not end a sentence,
    and a closing quote or parenthesis may sit between the terminal
    punctuation and its citation group.
    """
    marker = "\u0000"
    protected = ABBREVIATION_RE.sub(lambda m: (m.group(1) or m.group(2)).replace(".", marker), value)
    return [
        part.replace(marker, ".").strip()
        for part in SENTENCE_RE.findall(protected)
        if part.strip()
    ]


def frontmatter_scalar(raw: str) -> str:
    """Decode a frontmatter scalar: a JSON/YAML double-quoted string, a
    single-quoted YAML string, or a bare value with surrounding whitespace
    removed."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            decoded = json.loads(value)
            if isinstance(decoded, str):
                return decoded
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def frontmatter_encode(value: str) -> str:
    """Encode a free-text scalar for generated frontmatter.

    Titles are always JSON-quoted so no YAML consumer can coerce them to a
    number, date, or boolean; :func:`frontmatter_scalar` decodes the result.
    """
    return json.dumps(value, ensure_ascii=False)


def report_body_and_sources(markdown: str) -> tuple[str, dict[int, str]]:
    lines = markdown.splitlines()
    header = -1
    for index, line in enumerate(lines):
        if SOURCES_HEADER_RE.match(line.strip()):
            header = index
    if header < 0:
        return markdown, {}
    listed: dict[int, str] = {}
    for line in lines[header + 1 :]:
        match = SOURCE_LINE_RE.match(line.strip())
        if match:
            listed[int(match.group(1))] = match.group(2).rstrip(".,")
    return "\n".join(lines[:header]), listed


def is_table_separator(stripped: str) -> bool:
    return "-" in stripped and bool(re.fullmatch(r"\|?(?:\s*:?-{1,}:?\s*\|)*\s*:?-{1,}:?\s*\|?", stripped))


def table_rows(lines: list[str]) -> set[int]:
    """Return indexes of lines that belong to a Markdown table.

    A table is a header line, a separator line, then body lines, each with at
    least one ``|`` cell delimiter. Outer pipes are optional; the separator
    row is what makes a pipe-bearing run of lines a table.
    """
    rows: set[int] = set()
    index = 0
    while index < len(lines) - 1:
        header = lines[index].strip()
        separator = lines[index + 1].strip()
        if "|" in header and not is_table_separator(header) and is_table_separator(separator) and "|" in separator:
            rows.add(index)
            rows.add(index + 1)
            index += 2
            while index < len(lines) and lines[index].strip() and "|" in lines[index]:
                rows.add(index)
                index += 1
            continue
        index += 1
    return rows


def table_header_indexes(lines: list[str]) -> set[int]:
    """Return indexes of table header rows: the line immediately above a separator row within a table."""
    rows = table_rows(lines)
    return {index for index in rows if index + 1 in rows and is_table_separator(lines[index + 1].strip()) and not is_table_separator(lines[index].strip())}


FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def fence_step(stripped: str, fence: str | None) -> tuple[bool, str | None]:
    """Track fenced code blocks line by line.

    ``fence`` is the open fence's marker, or None outside a fence. Returns
    whether ``stripped`` is itself a fence line and the marker after it. As in
    CommonMark, backtick and tilde fences both count, and a fence closes only on
    a bare marker of the same character at least as long as the opener.
    """
    match = FENCE_RE.match(stripped)
    if not match:
        return False, fence
    marker = match.group(1)
    if fence is None:
        return True, marker
    if marker[0] == fence[0] and len(marker) >= len(fence) and not stripped[len(marker):].strip():
        return True, None
    return False, fence


def prose_sentences(markdown: str) -> list[str]:
    sentences: list[str] = []
    fence: str | None = None
    lines = markdown.splitlines()
    rows = table_rows(lines)
    headers = table_header_indexes(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        fence_line, fence = fence_step(stripped, fence)
        if fence_line:
            continue
        if (
            fence
            or not stripped
            or stripped.startswith("#")
            or stripped == "---"
            or re.match(r"^[a-z_]+:\s", stripped)
        ):
            continue
        if index in rows:
            if is_table_separator(stripped) or index in headers:
                continue
            stripped = stripped.strip("| ")
            if len(stripped.split()) >= 2:
                sentences.append(stripped)
            continue
        stripped = re.sub(r"^(?:>|[-*]|\d+[.)])\s+", "", stripped)
        for part in split_cited_sentences(stripped):
            if len(part.split()) >= 4:
                sentences.append(part)
    return sentences


def prose_units(markdown: str) -> list[str]:
    """Return citation units: prose paragraphs, list items, and table body rows.

    Table header rows label columns and carry no evidence, so they are not
    citation units. A list item that wraps onto indented continuation lines is
    one unit, not one unit per physical line.
    """
    units: list[str] = []
    paragraph: list[str] = []
    list_item: list[str] = []
    fence: str | None = None
    in_frontmatter = False
    lines = markdown.splitlines()
    rows = table_rows(lines)
    headers = table_header_indexes(lines)

    def flush() -> None:
        if list_item:
            units.append(" ".join(list_item))
            list_item.clear()
        if paragraph:
            units.append(" ".join(paragraph))
            paragraph.clear()

    for line_number, line in enumerate(lines):
        stripped = line.strip()
        if line_number == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        fence_line, fence = fence_step(stripped, fence)
        if fence_line:
            flush()
            continue
        if fence:
            continue
        if not stripped:
            flush()
            continue
        if stripped.startswith("#"):
            flush()
            continue
        if line_number in rows:
            flush()
            if not is_table_separator(stripped) and line_number not in headers:
                units.append(stripped)
            continue
        if re.match(r"^(?:>|[-*]|\d+[.)])\s+", stripped):
            flush()
            list_item.append(stripped)
            continue
        if list_item:
            # Indented continuation or CommonMark lazy continuation: a
            # non-blank, non-marker line directly after a list item belongs
            # to that item.
            list_item.append(stripped)
            continue
        paragraph.append(stripped)
    flush()
    return [unit for unit in units if len(unit.split()) >= 4]


def citation_scope_valid(unit: str) -> bool:
    """Accept one terminal paragraph citation or fully local mixed citations."""
    groups = list(CITE_GROUP_RE.finditer(unit))
    if not groups:
        return False
    if len(groups) == 1:
        remainder = unit[groups[0].end() :].strip().strip("*_`|)")
        return not remainder
    sentences = [part for part in split_cited_sentences(unit) if len(part.split()) >= 4]
    return bool(sentences) and all(CITE_RE.search(sentence) for sentence in sentences)


STATUS_CONFIDENCE_FLOOR = {"confirmed": 0.80, "probable": 0.50}
STATUS_CONFIDENCE_CEILING = {"unsupported": 0.50, "contested": 0.90}


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def validate_report(directory: Path, warnings: list[str] | None = None, *, verify_snapshots: bool = False, notes: list[str] | None = None) -> list[str]:
    """Validate one report directory.

    Returns hard errors. Advisory findings that will become errors at the next
    minor framework release are appended to ``warnings`` when a list is supplied.
    ``notes`` receives informational findings that never fail validation, such
    as snapshots that are not present in this checkout. With
    ``verify_snapshots``, every snapshot-bound quotation must be re-verified
    against locally present snapshot text.
    """
    errors: list[str] = []
    if warnings is None:
        warnings = []
    if notes is None:
        notes = []
    directory = directory.resolve()
    require(errors, directory.is_dir(), f"report directory does not exist: {directory}")
    if errors:
        return errors

    assessment_path = directory / "assessment.json"
    ledger_path = directory / "sources-ledger.json"
    markdown_path = directory / "report.md"

    try:
        assessment = load_json(assessment_path)
        ledger = load_json(ledger_path)
        markdown = markdown_path.read_text(encoding="utf-8")
    except (ValueError, FileNotFoundError) as exc:
        return [str(exc)]

    require(errors, isinstance(assessment, dict), "assessment.json must be an object")
    require(errors, isinstance(ledger, dict), "sources-ledger.json must be an object")
    if not isinstance(assessment, dict) or not isinstance(ledger, dict):
        return errors

    require(errors, assessment.get("schema_version") == 1, "schema_version must be 1")
    report = assessment.get("report")
    require(errors, isinstance(report, dict), "report must be an object")
    if not isinstance(report, dict):
        report = {}

    for key in ("slug", "title", "domain", "cutoff", "created", "updated", "status", "summary"):
        require(errors, text(report.get(key)), f"report.{key} must be non-empty text")
    require(errors, bool(SLUG_RE.fullmatch(str(report.get("slug", "")))), "report.slug must be lowercase kebab-case")
    require(errors, bool(SLUG_RE.fullmatch(str(report.get("domain", "")))), "report.domain must be lowercase kebab-case")
    require(errors, report.get("status") in REPORT_STATUS, f"report.status must be one of {sorted(REPORT_STATUS)}")
    require(errors, report.get("mode") in RESEARCH_MODES, f"report.mode must be one of {sorted(RESEARCH_MODES)}")
    for key in ("cutoff", "created", "updated"):
        require(errors, valid_datetime(report.get(key)), f"report.{key} must be an ISO-8601 date/time")
    cutoff_dt = parse_temporal(report.get("cutoff"))
    created_dt = parse_temporal(report.get("created"))
    updated_dt = parse_temporal(report.get("updated"))
    # A draft is created before its evidence window closes; the cutoff is
    # bounded by the latest edit, not by scaffold creation.
    if cutoff_dt and updated_dt:
        require(errors, not_after(report.get("cutoff"), report.get("updated")), "report.cutoff must not be after report.updated")
    if created_dt and updated_dt:
        require(errors, not_after(report.get("created"), report.get("updated")), "report.created must not be after report.updated")
    lineage = report.get("lineage")
    require(errors, isinstance(lineage, dict), "report.lineage must be an object")
    if isinstance(lineage, dict):
        for key in ("supersedes", "superseded_by"):
            value = lineage.get(key)
            require(errors, value is None or text(value), f"report.lineage.{key} must be null or a report-relative directory")
        if report.get("status") == "superseded":
            require(errors, text(lineage.get("superseded_by")), "superseded reports require report.lineage.superseded_by")
        for key in ("supersedes", "superseded_by"):
            value = lineage.get(key)
            if not text(value):
                continue
            value_str = str(value)
            target = (ROOT / value_str).resolve()
            require(errors, target.is_relative_to(REPORTS.resolve()), f"report.lineage.{key} must stay under reports/")
            target_assessment = target / "assessment.json"
            require(errors, target_assessment.is_file(), f"report.lineage.{key} target lacks assessment.json: {value}")
            if target_assessment.is_file() and cutoff_dt:
                try:
                    target_cutoff_raw = load_json(target_assessment)["report"]["cutoff"]
                    target_cutoff = parse_temporal(target_cutoff_raw)
                except (ValueError, KeyError, TypeError):
                    target_cutoff_raw, target_cutoff = None, None
                require(errors, target_cutoff is not None, f"report.lineage.{key} target has invalid cutoff")
                if target_cutoff and key == "supersedes":
                    require(errors, strictly_before(target_cutoff_raw, report.get("cutoff")), "a superseded report must have an earlier cutoff")
                if target_cutoff and key == "superseded_by":
                    require(errors, strictly_before(report.get("cutoff"), target_cutoff_raw), "a successor report must have a later cutoff")
    questions = report.get("questions")
    require(errors, isinstance(questions, list) and bool(questions) and all(text(q) for q in questions), "report.questions must be a non-empty text list")
    if text(report.get("slug")):
        require(errors, directory.name == report["slug"], "report.slug must match the directory name")
    require(errors, PLACEHOLDER_MARKER not in str(report.get("summary", "")), "report.summary still contains the init placeholder")
    if isinstance(questions, list):
        require(errors, not any(PLACEHOLDER_MARKER in str(q) for q in questions), "report.questions still contain the init placeholder")

    ledger_sources = ledger.get("sources")
    require(errors, ledger.get("version") == 1, "sources-ledger.json version must be 1")
    require(errors, isinstance(ledger_sources, list), "sources-ledger.json sources must be a list")
    if not isinstance(ledger_sources, list):
        ledger_sources = []
    ledger_by_id: dict[int, dict[str, Any]] = {}
    ledger_urls: set[str] = set()
    for index, source in enumerate(ledger_sources):
        where = f"sources-ledger.sources[{index}]"
        require(errors, isinstance(source, dict), f"{where} must be an object")
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        require(errors, isinstance(source_id, int) and source_id > 0, f"{where}.id must be a positive integer")
        require(errors, valid_url(source.get("url")), f"{where}.url must be http(s)")
        require(errors, text(source.get("title")), f"{where}.title must be non-empty")
        require(errors, parse_temporal(source.get("accessed")) is not None, f"{where}.accessed must be an ISO date or datetime")
        quotes = source.get("quotes", [])
        if quotes is None:
            quotes = []
        require(errors, isinstance(quotes, list), f"{where}.quotes must be a list when present")
        if not isinstance(quotes, list):
            source["quotes"] = []
        else:
            for quote_index, quote in enumerate(quotes):
                require(errors, isinstance(quote, dict) and text(quote.get("text")), f"{where}.quotes[{quote_index}].text must be non-empty")
            source["quotes"] = [quote for quote in quotes if isinstance(quote, dict) and text(quote.get("text"))]
        if isinstance(source_id, int):
            require(errors, source_id not in ledger_by_id, f"duplicate ledger source id: {source_id}")
            ledger_by_id[source_id] = source
        if text(source.get("url")):
            require(errors, source["url"] not in ledger_urls, f"duplicate ledger URL: {source['url']}")
            ledger_urls.add(source["url"])

    sources = assessment.get("sources")
    require(errors, isinstance(sources, list) and bool(sources), "assessment.sources must be a non-empty list")
    if not isinstance(sources, list):
        sources = []
    source_by_id: dict[int, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        where = f"sources[{index}]"
        require(errors, isinstance(source, dict), f"{where} must be an object")
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        require(errors, isinstance(source_id, int) and source_id > 0, f"{where}.id must be a positive integer")
        require(errors, valid_url(source.get("url")), f"{where}.url must be http(s)")
        for key in ("title", "publisher", "independence_group", "independence_rationale"):
            require(errors, text(source.get(key)), f"{where}.{key} must be non-empty text")
        require(errors, source.get("published_at") is None or parse_temporal(source.get("published_at")) is not None, f"{where}.published_at must be null or an ISO date/datetime")
        require(errors, parse_temporal(source.get("retrieved_at")) is not None, f"{where}.retrieved_at must be an ISO date or datetime")
        if cutoff_dt:
            require(errors, not_after(source.get("retrieved_at"), report.get("cutoff")), f"{where}.retrieved_at is after the report cutoff")
        if source.get("published_at") is not None:
            require(errors, not_after(source.get("published_at"), source.get("retrieved_at")), f"{where}.published_at is after retrieved_at")
        require(errors, source.get("source_type") in SOURCE_TYPES, f"{where}.source_type invalid")
        require(errors, source.get("access") in ACCESS, f"{where}.access invalid")
        require(errors, source.get("directness") in DIRECTNESS, f"{where}.directness invalid")
        for key in ("incentives", "limitations"):
            require(errors, isinstance(source.get(key), list), f"{where}.{key} must be a list")
        # Author audits are optional: most sources never receive one, and an
        # omitted list means "not researched", which forces unknown ratings.
        authors = source.get("authors", [])
        require(errors, isinstance(authors, list), f"{where}.authors must be a list when present")
        if isinstance(authors, list):
            for author_index, author in enumerate(authors):
                author_where = f"{where}.authors[{author_index}]"
                require(errors, isinstance(author, dict), f"{author_where} must be an object")
                if isinstance(author, dict):
                    require(errors, text(author.get("name")), f"{author_where}.name must be non-empty")
                    expertise_url = author.get("expertise_url")
                    require(errors, expertise_url is None or valid_url(expertise_url), f"{author_where}.expertise_url must be null or http(s)")
        reliability = source.get("reliability")
        require(errors, isinstance(reliability, dict), f"{where}.reliability must be an object")
        if isinstance(reliability, dict):
            for key in ("publisher_history", "transparency"):
                require(errors, reliability.get(key) in RATINGS, f"{where}.reliability.{key} invalid")
            for key in ("author_expertise", "author_track_record"):
                require(errors, reliability.get(key, "unknown") in RATINGS, f"{where}.reliability.{key} invalid")
            require(errors, text(reliability.get("notes")), f"{where}.reliability.notes must explain the rating")
            if not authors:
                require(errors, reliability.get("author_expertise", "unknown") == "unknown", f"{where} has no authors, so author_expertise must be unknown")
                require(errors, reliability.get("author_track_record", "unknown") == "unknown", f"{where} has no authors, so author_track_record must be unknown")
            if reliability.get("author_expertise") == "high" and isinstance(authors, list):
                require(errors, any(valid_url(author.get("expertise_url")) for author in authors if isinstance(author, dict)), f"{where} high author expertise requires a retrievable expertise_url")
        if isinstance(source_id, int):
            require(errors, source_id not in source_by_id, f"duplicate assessment source id: {source_id}")
            source_by_id[source_id] = source
            ledger_source = ledger_by_id.get(source_id)
            require(errors, ledger_source is not None, f"assessment source {source_id} missing from citation ledger")
            if ledger_source:
                require(errors, source.get("url") == ledger_source.get("url"), f"source {source_id} URL differs from citation ledger")
                require(errors, source.get("title") == ledger_source.get("title"), f"source {source_id} title differs from citation ledger")
    require(errors, set(source_by_id) == set(ledger_by_id), "assessment and citation ledger must contain the same source IDs")

    claims = assessment.get("claims")
    require(errors, isinstance(claims, list) and bool(claims), "claims must be a non-empty list")
    if not isinstance(claims, list):
        claims = []
    claim_by_id: dict[str, dict[str, Any]] = {}
    for index, claim in enumerate(claims):
        where = f"claims[{index}]"
        require(errors, isinstance(claim, dict), f"{where} must be an object")
        if not isinstance(claim, dict):
            continue
        raw_claim_id = claim.get("id")
        claim_id = raw_claim_id if isinstance(raw_claim_id, str) else ""
        require(errors, bool(claim_id) and bool(ID_RE.fullmatch(claim_id)), f"{where}.id must match {ID_RE.pattern}")
        require(errors, text(claim.get("statement")), f"{where}.statement must be non-empty")
        require(errors, claim.get("kind") in CLAIM_KINDS, f"{where}.kind invalid")
        require(errors, claim.get("status") in CLAIM_STATUS, f"{where}.status invalid")
        require(errors, claim.get("importance") in IMPORTANCE, f"{where}.importance invalid")
        confidence_mode = claim.get("confidence_mode", "quantitative")
        require(errors, confidence_mode in ("quantitative", "qualitative"), f"{where}.confidence_mode invalid")
        if confidence_mode == "qualitative":
            require(errors, "confidence" not in claim, f"{where} qualitative mode must omit numerical confidence")
            require(errors, claim.get("kind") != "forecast", f"{where} forecast requires quantitative confidence")
            require(errors, text(claim.get("confidence_limitations")), f"{where}.confidence_limitations must be non-empty")
            falsifiers = claim.get("falsifiers")
            require(errors, isinstance(falsifiers, list) and bool(falsifiers) and all(text(item) for item in falsifiers), f"{where} qualitative mode requires non-empty falsifiers")
        else:
            require(errors, valid_range(claim.get("confidence")), f"{where}.confidence must be [low, high] within 0..1")
        for key in ("source_ids", "contradicting_source_ids", "falsifiers"):
            require(errors, isinstance(claim.get(key), list), f"{where}.{key} must be a list")
            if not isinstance(claim.get(key), list):
                claim[key] = []
            elif key != "falsifiers":
                require(errors, all(isinstance(c, int) and not isinstance(c, bool) for c in claim[key]), f"{where}.{key} entries must be integer source ids")
                claim[key] = [c for c in claim[key] if isinstance(c, int) and not isinstance(c, bool)]
        require(errors, text(claim.get("rationale")), f"{where}.rationale must be non-empty")
        require(errors, valid_datetime(claim.get("last_checked")), f"{where}.last_checked must be ISO-8601")
        if cutoff_dt:
            require(errors, not_after(claim.get("last_checked"), report.get("cutoff")), f"{where}.last_checked is after the report cutoff")
        for source_id in claim.get("source_ids", []) + claim.get("contradicting_source_ids", []):
            require(errors, source_id in source_by_id, f"{where} references unknown source {source_id}")
        if claim.get("importance") == "load-bearing" and claim.get("kind") not in {"forecast", "unknown"}:
            require(errors, bool(claim.get("source_ids")), f"{where} load-bearing claim requires supporting sources")
        supporting = [source_by_id[source_id] for source_id in claim.get("source_ids", []) if source_id in source_by_id]
        groups = {source.get("independence_group") for source in supporting}
        has_direct_full = any(source.get("directness") == "direct" and source.get("access") == "full" for source in supporting)
        if claim.get("importance") == "load-bearing" and claim.get("status") == "confirmed" and claim.get("kind") in {"fact", "attributed"}:
            require(errors, has_direct_full or len(groups) >= 2, f"{where} confirmed load-bearing claim requires direct full evidence or two independence groups")
        confidence = claim.get("confidence")
        if isinstance(confidence, list) and valid_range(confidence):
            low_confidence = float(confidence[0])
            high_confidence = float(confidence[1])
            if supporting and len(groups) <= 1 and not has_direct_full:
                require(errors, approx_ge(0.95, high_confidence), f"{where} single-group indirect evidence cannot exceed 0.95 confidence")
                require(errors, approx_ge(high_confidence - low_confidence, 0.15), f"{where} single-group indirect evidence requires a confidence width of at least 0.15")
            status = claim.get("status")
            if status in STATUS_CONFIDENCE_FLOOR:
                require(errors, approx_ge(low_confidence, STATUS_CONFIDENCE_FLOOR[status]), f"{where} status {status!r} requires confidence low >= {STATUS_CONFIDENCE_FLOOR[status]:.2f}")
            if status in STATUS_CONFIDENCE_CEILING:
                require(errors, approx_ge(STATUS_CONFIDENCE_CEILING[status], high_confidence), f"{where} status {status!r} requires confidence high <= {STATUS_CONFIDENCE_CEILING[status]:.2f}")
            if status == "unknown":
                require(errors, approx_ge(high_confidence - low_confidence, 0.30), f"{where} status 'unknown' must carry a wide confidence interval (>= 0.30)")
        if claim_id:
            require(errors, claim_id not in claim_by_id, f"duplicate claim id: {claim_id}")
            claim_by_id[claim_id] = claim

    evidence = assessment.get("evidence")
    require(errors, isinstance(evidence, list), "evidence must be a list")
    if not isinstance(evidence, list):
        evidence = []
    evidence_claims: set[str] = set()
    evidence_ids: set[str] = set()
    # claim id -> access levels of sources that actually carry evidence for it
    evidence_access_by_claim: dict[str, set[str]] = {}
    for index, item in enumerate(evidence):
        where = f"evidence[{index}]"
        require(errors, isinstance(item, dict), f"{where} must be an object")
        if not isinstance(item, dict):
            continue
        raw_evidence_id = item.get("id")
        evidence_id = raw_evidence_id if isinstance(raw_evidence_id, str) else ""
        if evidence_id:
            where = f"evidence[{index}] ({evidence_id})"
        require(errors, bool(evidence_id) and bool(ID_RE.fullmatch(evidence_id)), f"{where}.id invalid")
        require(errors, evidence_id not in evidence_ids, f"duplicate evidence id: {evidence_id}")
        if evidence_id:
            evidence_ids.add(evidence_id)
        source_id = item.get("source_id")
        source_id = source_id if isinstance(source_id, int) and not isinstance(source_id, bool) else None
        require(errors, source_id in source_by_id, f"{where}.source_id is unknown")
        require(errors, text(item.get("excerpt")), f"{where}.excerpt must be non-empty")
        require(errors, len(str(item.get("excerpt", ""))) <= 1000, f"{where}.excerpt exceeds 1000 characters")
        require(errors, text(item.get("location")), f"{where}.location must be non-empty")
        require(errors, valid_datetime(item.get("captured_at")), f"{where}.captured_at must be ISO-8601")
        if cutoff_dt:
            require(errors, not_after(item.get("captured_at"), report.get("cutoff")), f"{where}.captured_at is after the report cutoff")
        kind = item.get("kind", "excerpt")
        require(errors, kind in EVIDENCE_KINDS, f"{where}.kind must be one of {sorted(EVIDENCE_KINDS)}")
        if kind == "excerpt" and source_id in ledger_by_id and text(item.get("excerpt")):
            ledger_quotes = {normalize_whitespace(str(q.get("text", ""))) for q in ledger_by_id[source_id].get("quotes", []) if isinstance(q, dict)}
            verified = normalize_whitespace(str(item["excerpt"])) in ledger_quotes
            if not verified:
                warnings.append(f"{where}.excerpt has no matching ledger quote for source {source_id}; record it with `add-evidence` or `add-quote --from-file`, or set kind to 'artifact' for non-text evidence")
        supports = item.get("supports_claim_ids")
        require(errors, isinstance(supports, list) and bool(supports), f"{where}.supports_claim_ids must be non-empty")
        if isinstance(supports, list):
            require(errors, all(isinstance(c, str) for c in supports), f"{where}.supports_claim_ids entries must be claim id strings")
            supports = [c for c in supports if isinstance(c, str)]
            evidence_source = source_by_id.get(source_id)
            for claim_id in supports:
                require(errors, claim_id in claim_by_id, f"{where} references unknown claim {claim_id}")
                evidence_claims.add(claim_id)
                if claim_id in claim_by_id:
                    claim_sources = claim_by_id[claim_id].get("source_ids")
                    require(errors, isinstance(claim_sources, list) and source_id in claim_sources, f"{where}.source_id must be listed by supported claim {claim_id}")
                    if evidence_source is not None:
                        evidence_access_by_claim.setdefault(str(claim_id), set()).add(str(evidence_source.get("access")))
    for claim_id, claim in claim_by_id.items():
        if claim.get("importance") == "load-bearing" and claim.get("kind") in {"fact", "attributed"}:
            require(errors, claim_id in evidence_claims, f"load-bearing claim {claim_id} requires a short evidence excerpt")
            if claim_id in evidence_claims:
                require(
                    errors,
                    bool(evidence_access_by_claim.get(claim_id, set()) & {"full", "partial"}),
                    f"load-bearing claim {claim_id} cannot rest on snippet-only evidence; attach evidence from a full or partial source",
                )

    hypotheses = assessment.get("hypotheses")
    require(errors, isinstance(hypotheses, list), "hypotheses must be a list")
    if not isinstance(hypotheses, list):
        hypotheses = []
    has_forecast_claim = any(claim.get("kind") == "forecast" for claim in claims if isinstance(claim, dict))
    if report.get("mode") in HYPOTHESIS_REQUIRED_MODES or has_forecast_claim:
        require(errors, bool(hypotheses), f"modes {sorted(HYPOTHESIS_REQUIRED_MODES)} and forecast claims require at least one hypothesis")
    hypothesis_ids: set[str] = set()
    for index, hypothesis in enumerate(hypotheses):
        where = f"hypotheses[{index}]"
        require(errors, isinstance(hypothesis, dict), f"{where} must be an object")
        if not isinstance(hypothesis, dict):
            continue
        raw_hypothesis_id = hypothesis.get("id")
        hypothesis_id = raw_hypothesis_id if isinstance(raw_hypothesis_id, str) else ""
        require(errors, bool(hypothesis_id) and bool(ID_RE.fullmatch(hypothesis_id)), f"{where}.id invalid")
        require(errors, hypothesis_id not in hypothesis_ids, f"duplicate hypothesis id: {hypothesis_id}")
        if hypothesis_id:
            hypothesis_ids.add(hypothesis_id)
        require(errors, text(hypothesis.get("statement")), f"{where}.statement must be non-empty")
        probability = hypothesis.get("probability")
        valid_probability = (
            isinstance(probability, dict)
            and all(isinstance(probability.get(k), (int, float)) and not isinstance(probability.get(k), bool) for k in ("low", "central", "high"))
            and 0 <= probability["low"] <= probability["central"] <= probability["high"] <= 1
        )
        require(errors, valid_probability, f"{where}.probability must be ordered low/central/high within 0..1")
        basis = hypothesis.get("basis_claim_ids")
        require(errors, isinstance(basis, list) and bool(basis), f"{where}.basis_claim_ids must be non-empty")
        if isinstance(basis, list):
            require(errors, all(isinstance(c, str) for c in basis), f"{where}.basis_claim_ids entries must be claim id strings")
            for claim_id in [c for c in basis if isinstance(c, str)]:
                require(errors, claim_id in claim_by_id, f"{where} references unknown claim {claim_id}")
        alternatives = hypothesis.get("alternatives")
        require(errors, isinstance(alternatives, list), f"{where}.alternatives must be a list")
        if isinstance(alternatives, list):
            require(errors, bool(alternatives) and all(text(a) for a in alternatives), f"{where}.alternatives must name at least one credible alternative")
        triggers = hypothesis.get("update_triggers")
        require(errors, isinstance(triggers, list) and bool(triggers) and all(text(t) for t in triggers), f"{where}.update_triggers must be non-empty text")
        require(errors, text(hypothesis.get("rationale")), f"{where}.rationale must be non-empty")
        resolution = hypothesis.get("resolution")
        require(errors, isinstance(resolution, dict), f"{where}.resolution must be an object")
        if isinstance(resolution, dict):
            require(errors, resolution.get("status") in {"open", "resolved", "superseded"}, f"{where}.resolution.status invalid")
            if resolution.get("status") in {"resolved", "superseded"}:
                require(errors, text(resolution.get("outcome")), f"{where} {resolution.get('status')} hypothesis requires an outcome")
                require(errors, parse_temporal(resolution.get("resolved_at")) is not None, f"{where} {resolution.get('status')} hypothesis requires resolved_at")
                if parse_temporal(resolution.get("resolved_at")) is not None and cutoff_dt:
                    require(errors, not_after(report.get("cutoff"), resolution.get("resolved_at")), f"{where}.resolution.resolved_at must not precede report.cutoff")
            else:
                require(errors, resolution.get("resolved_at") is None, f"{where} open hypothesis resolved_at must be null")

    gaps = assessment.get("coverage_gaps")
    require(errors, isinstance(gaps, list), "coverage_gaps must be a list")
    if isinstance(gaps, list):
        for index, gap in enumerate(gaps):
            where = f"coverage_gaps[{index}]"
            if isinstance(gap, str):
                require(errors, text(gap), f"{where} must be non-empty text")
                continue
            require(errors, isinstance(gap, dict), f"{where} must be a string or an object")
            if not isinstance(gap, dict):
                continue
            require(errors, gap.get("kind") in GAP_KINDS, f"{where}.kind must be one of {sorted(GAP_KINDS)}")
            require(errors, text(gap.get("description")), f"{where}.description must be non-empty")
            if gap.get("kind") == "matrix-cell":
                require(errors, text(gap.get("candidate")) and text(gap.get("criterion")), f"{where} matrix-cell gaps must name candidate and criterion")
            if "claim_ids" in gap:
                claim_refs = gap["claim_ids"]
                require(errors, isinstance(claim_refs, list) and all(isinstance(c, str) and c in claim_by_id for c in claim_refs), f"{where}.claim_ids must reference known claims")
    review = assessment.get("review")
    require(errors, isinstance(review, dict), "review must be an object")
    if isinstance(review, dict):
        require(errors, isinstance(review.get("deterministic_checks"), list), "review.deterministic_checks must be a list")
        require(errors, review.get("independent_review") in {"not-run", "passed", "findings", "blocked"}, "review.independent_review invalid")
        require(errors, text(review.get("notes")), "review.notes must be non-empty")
        if report.get("status") == "reviewed":
            require(errors, review.get("independent_review") == "passed", "reviewed reports require review.independent_review=passed")
        if review.get("independent_review") == "passed":
            require(errors, text(review.get("exact_revision")), "passed independent review requires review.exact_revision")
            require(errors, text(review.get("route")), "passed independent review requires review.route")
            require(errors, isinstance(review.get("findings_disposition"), list), "passed independent review requires review.findings_disposition list")
            require(errors, isinstance(review.get("rereview_required"), bool), "passed independent review requires review.rereview_required boolean")

    cited = {int(value) for value in CITE_RE.findall(report_body_and_sources(markdown)[0])}
    unknown_cites = sorted(cited - set(ledger_by_id))
    require(errors, not unknown_cites, f"report.md has unknown citations: {unknown_cites}")
    require(errors, cited <= set(ledger_by_id), "every report citation must exist in the ledger")
    body, listed = report_body_and_sources(markdown)
    require(errors, bool(listed), "report.md must end with a generated ## Sources block")
    require(errors, set(listed) == cited, "Sources block IDs must exactly match report citations")
    for source_id, url in listed.items():
        if source_id in ledger_by_id:
            require(errors, url == ledger_by_id[source_id]["url"], f"Sources block URL for [{source_id}] differs from ledger")
    anchored_body = body
    anchor_targets = set(claim_by_id) | {h.get("id") for h in hypotheses if isinstance(h, dict) and isinstance(h.get("id"), str)}
    body = strip_anchors(body, anchor_targets)
    sentences = prose_sentences(body)
    units = prose_units(body)
    covered = [unit for unit in units if citation_scope_valid(unit)]
    coverage = len(covered) / len(units) if units else 0
    require(errors, coverage >= 0.40, f"paragraph/table citation coverage {coverage:.0%} is below 40% ({len(covered)}/{len(units)})")
    over_cited = [sentence for sentence in sentences if len(CITE_RE.findall(sentence)) > 3]
    require(errors, not over_cited, f"{len(over_cited)} sentence(s) carry more than three citations")

    cutoff = str(report.get("cutoff", ""))
    require(errors, cutoff in markdown, "report.md must display the exact report cutoff")
    require(errors, "assessment.json" in markdown, "report.md must link to assessment.json")
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", markdown, re.DOTALL)
    require(errors, frontmatter_match is not None, "report.md must start with frontmatter")
    if frontmatter_match:
        fields = {key: frontmatter_scalar(raw) for key, raw in re.findall(r"^([a-z_]+):\s*(.+)$", frontmatter_match.group(1), re.MULTILINE)}
        for key in ("title", "slug", "mode", "domain", "cutoff", "status"):
            require(errors, fields.get(key) == str(report.get(key, "")), f"report.md frontmatter {key} differs from assessment.json")
    require(errors, PLACEHOLDER_MARKER not in body, "report.md still contains init placeholder text")

    hypothesis_by_id = {h["id"]: h for h in hypotheses if isinstance(h, dict) and isinstance(h.get("id"), str)}
    context = ReportContext(
        directory=directory,
        assessment=assessment,
        report=report,
        ledger_by_id=ledger_by_id,
        source_by_id=source_by_id,
        claim_by_id=claim_by_id,
        hypothesis_by_id=hypothesis_by_id,
        evidence=[item for item in evidence if isinstance(item, dict)],
        gaps=gaps if isinstance(gaps, list) else [],
        review=review if isinstance(review, dict) else {},
        body=anchored_body,
        cited=cited,
    )
    check_provenance(context, errors, warnings, notes, verify_snapshots)
    check_anchors(context, errors, warnings)
    check_depth(context, errors, warnings)
    check_calibration(context, errors, warnings)
    check_review_evidence(context, errors, warnings)
    return errors


INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _anchor_matches(line: str, known: set[str] | None) -> list[tuple[re.Match[str], list[str]]]:
    """Return brace groups in ``line`` that are claim anchors.

    A brace group is an anchor when it directly follows a citation group or
    another anchor (``…[3]{C4}``), or when every ID in it names a known claim or
    hypothesis. Other brace-wrapped uppercase text, such as ``{JSON}`` in older
    prose, is ordinary text. Inline code spans are never anchors.
    """
    code = [(m.start(), m.end()) for m in INLINE_CODE_RE.finditer(line)]
    citation_ends = {m.end() for m in CITE_GROUP_RE.finditer(line)}
    found = []
    anchor_ends: set[int] = set()
    for match in ANCHOR_RE.finditer(line):
        if any(start <= match.start() < end for start, end in code):
            continue
        ids = [part.strip() for part in match.group(1).split(",")]
        adjacent = match.start() in citation_ends or match.start() in anchor_ends
        if adjacent or (known is not None and all(value in known for value in ids)):
            found.append((match, ids))
            anchor_ends.add(match.end())
    return found


def strip_anchors(value: str, known: set[str] | None = None) -> str:
    """Remove claim anchors so reader-facing text and citation checks see plain prose.

    Fenced code blocks and inline code are left untouched.
    """
    lines = value.split("\n")
    fence: str | None = None
    for index, line in enumerate(lines):
        fence_line, fence = fence_step(line.strip(), fence)
        if fence_line or fence:
            continue
        matches = _anchor_matches(line, known)
        for match, _ids in reversed(matches):
            start = match.start()
            while start > 0 and line[start - 1] in " \t":
                start -= 1
            line = line[:start] + line[match.end():]
        lines[index] = line
    return "\n".join(lines)


def anchor_ids(unit: str, known: set[str] | None = None) -> list[str]:
    return [value for _match, ids in _anchor_matches(unit, known) for value in ids]


def shorten(value: str, limit: int = 90) -> str:
    value = normalize_whitespace(value)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def summarize_ids(values: list[Any], limit: int = 12) -> str:
    shown = ", ".join(str(value) for value in values[:limit])
    return shown + (f", … (+{len(values) - limit} more)" if len(values) > limit else "")


class ReportContext:
    """Parsed report state shared by the rule families below."""

    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)
        self.cutoff = self.report.get("cutoff")
        questions = self.report.get("questions")
        self.questions = questions if isinstance(questions, list) else []

    def claim_sources(self, claim_id: str, *, contradicting: bool = True) -> set[int]:
        claim = self.claim_by_id.get(claim_id) or {}
        found = set(claim.get("source_ids") or [])
        if contradicting:
            found |= set(claim.get("contradicting_source_ids") or [])
        return {value for value in found if isinstance(value, int)}


def check_provenance(ctx: ReportContext, errors: list[str], warnings: list[str], notes: list[str], verify_snapshots: bool) -> None:
    """[P] Ledger quotations must be bound to fetched or captured source text.

    A quote bound to a snapshot names the SHA-256 of the extracted text it was
    verified against. When that text is present locally, the validator
    re-verifies both the hash and the quotation, so edited snapshots and
    drifted quotes fail. When it is absent (for example in CI without the
    private store), the binding is still checked structurally.
    """
    unbound: list[int] = []
    absent: list[str] = []
    verified = 0
    for source_id, source in sorted(ctx.ledger_by_id.items()):
        records = source.get("snapshots")
        if records is None:
            records = []
        if not isinstance(records, list):
            errors.append(f"[P2] sources-ledger source {source_id}.snapshots must be a list")
            records = []
        digests: set[str] = set()
        for index, record in enumerate(records):
            where = f"[P2] sources-ledger source {source_id}.snapshots[{index}]"
            if not isinstance(record, dict):
                errors.append(f"{where} must be an object")
                continue
            require(errors, snapshots.valid_digest(record.get("sha256")), f"{where}.sha256 must be a lowercase SHA-256 hex digest")
            require(errors, record.get("method") in {"fetch", "capture"}, f"{where}.method must be fetch or capture")
            require(errors, parse_temporal(record.get("retrieved_at")) is not None, f"{where}.retrieved_at must be an ISO date or datetime")
            if ctx.cutoff and parse_temporal(record.get("retrieved_at")) is not None:
                require(errors, not_after(record.get("retrieved_at"), ctx.cutoff), f"{where}.retrieved_at is after the report cutoff")
            if snapshots.valid_digest(record.get("sha256")):
                digests.add(record["sha256"])
        for index, quote in enumerate(source.get("quotes") or []):
            digest = quote.get("snapshot")
            if digest is None:
                unbound.append(source_id)
                continue
            where = f"[P2] sources-ledger source {source_id}.quotes[{index}]"
            if not snapshots.valid_digest(digest) or digest not in digests:
                errors.append(f"{where}.snapshot does not name a snapshot recorded on source {source_id}")
                continue
            snapshot_text = snapshots.read_snapshot(ROOT, ctx.directory, digest)
            if snapshot_text is None:
                absent.append(digest[:12])
                continue
            if snapshots.sha256_text(snapshot_text) != digest:
                errors.append(f"[P3] snapshot {digest[:12]}… for source {source_id} no longer matches its hash; the stored text was altered")
            elif snapshots.locate(str(quote.get("text", "")), snapshot_text) < 0:
                errors.append(f"[P3] {where} is not present in snapshot {digest[:12]}…")
            else:
                verified += 1
    if unbound:
        warnings.append(
            f"[P1] {len(unbound)} ledger quotation(s) are not bound to a fetched or captured snapshot (sources {summarize_ids(sorted(set(unbound)))}); "
            "record source text with `fetch` or `capture`, then `add-evidence --snapshot`"
        )
    if absent:
        unique = sorted(set(absent))
        message = f"{len(unique)} snapshot(s) bound to quotations are not present in this checkout ({summarize_ids(unique, 5)})"
        if verify_snapshots:
            errors.append(f"[P4] {message}; restore the snapshot store before claiming re-verification")
        else:
            notes.append(f"{message}; quotations were checked structurally only. Use --verify-snapshots where the store is available")
    if verified:
        notes.append(f"{verified} snapshot-bound quotation(s) re-verified against stored source text")


def check_anchors(ctx: ReportContext, errors: list[str], warnings: list[str]) -> None:
    """[A] Claim anchors bind passages of prose to the claims they assert.

    In an anchored passage, every citation must belong to an anchored claim
    (as support or contradiction), and a factual or attributed claim must be
    cited through at least one of its own sources. Load-bearing claims that
    never appear in the prose are reported so a reader can find where each
    conclusion is made.
    """
    anchored: set[str] = set()
    known = set(ctx.claim_by_id) | set(ctx.hypothesis_by_id)
    for unit in prose_units(ctx.body):
        ids = anchor_ids(unit, known)
        if not ids:
            continue
        unknown = [value for value in ids if value not in ctx.claim_by_id and value not in ctx.hypothesis_by_id]
        if unknown:
            errors.append(f"[A1] anchor {{{','.join(unknown)}}} names no claim or hypothesis: {shorten(strip_anchors(unit, known))}")
            continue
        anchored.update(ids)
        allowed: set[int] = set()
        for value in ids:
            if value in ctx.claim_by_id:
                allowed |= ctx.claim_sources(value)
            else:
                for basis in ctx.hypothesis_by_id[value].get("basis_claim_ids") or []:
                    if isinstance(basis, str):
                        allowed |= ctx.claim_sources(basis)
        cited_here = {int(value) for value in CITE_RE.findall(unit)}
        extra = sorted(cited_here - allowed)
        if extra:
            errors.append(f"[A2] passage anchored to {','.join(ids)} cites {extra}, which no anchored claim lists as support or contradiction: {shorten(strip_anchors(unit, known))}")
        for value in ids:
            claim = ctx.claim_by_id.get(value)
            if claim and claim.get("kind") in {"fact", "attributed"} and claim.get("source_ids"):
                if not cited_here & ctx.claim_sources(value, contradicting=False):
                    errors.append(f"[A2] passage anchored to {value} cites none of that claim's supporting sources: {shorten(strip_anchors(unit, known))}")
    missing = [claim_id for claim_id, claim in ctx.claim_by_id.items() if claim.get("importance") == "load-bearing" and claim_id not in anchored]
    if missing:
        warnings.append(f"[A3] {len(missing)} load-bearing claim(s) are not anchored in report.md ({summarize_ids(missing)}); mark where each is asserted with {{CLAIM-ID}} after its citation")


def check_depth(ctx: ReportContext, errors: list[str], warnings: list[str]) -> None:
    """[D] Research depth: a search log, sought counter-evidence, dispositioned sources."""
    searches = ctx.assessment.get("searches", [])
    search_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(searches, list):
        errors.append("[D1] searches must be a list when present")
        searches = []
    for index, search in enumerate(searches):
        where = f"[D1] searches[{index}]"
        if not isinstance(search, dict):
            errors.append(f"{where} must be an object")
            continue
        search_id = search.get("id")
        if not (isinstance(search_id, str) and ID_RE.fullmatch(search_id)):
            errors.append(f"{where}.id must match {ID_RE.pattern}")
            continue
        require(errors, search_id not in search_by_id, f"{where} duplicates search id {search_id}")
        search_by_id[search_id] = search
        require(errors, text(search.get("query")), f"{where}.query must be non-empty")
        require(errors, text(search.get("engine")), f"{where}.engine must name the search tool or database")
        require(errors, search.get("purpose") in SEARCH_PURPOSES, f"{where}.purpose must be one of {sorted(SEARCH_PURPOSES)}")
        require(errors, parse_temporal(search.get("run_at")) is not None, f"{where}.run_at must be an ISO date or datetime")
        if ctx.cutoff and parse_temporal(search.get("run_at")) is not None:
            require(errors, not_after(search.get("run_at"), ctx.cutoff), f"{where}.run_at is after the report cutoff")
        question = search.get("question")
        require(errors, question is None or (isinstance(question, int) and not isinstance(question, bool) and 1 <= question <= len(ctx.questions)), f"{where}.question must be null or a 1-based report question number")
        considered = search.get("results_considered")
        require(errors, considered is None or (isinstance(considered, int) and not isinstance(considered, bool) and considered >= 0), f"{where}.results_considered must be null or a non-negative integer")
        found = search.get("source_ids", [])
        require(errors, isinstance(found, list) and all(isinstance(value, int) and not isinstance(value, bool) and value in ctx.source_by_id for value in found), f"{where}.source_ids must reference assessment sources")

    if not search_by_id:
        warnings.append("[D1] no search log; record discovery, primary-record and counter-evidence searches with `log-search` so coverage and selection can be audited")
    else:
        unsearched = [number for number in range(1, len(ctx.questions) + 1) if not any(s.get("question") == number for s in search_by_id.values())]
        if unsearched:
            warnings.append(f"[D1] report question(s) {summarize_ids(unsearched)} have no logged search")

    def counter_searched(item: dict[str, Any], where: str) -> bool:
        refs = item.get("counter_search_ids", [])
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
            errors.append(f"[D2] {where}.counter_search_ids must be a list of search ids")
            return False
        unknown = [ref for ref in refs if ref not in search_by_id]
        if unknown:
            errors.append(f"[D2] {where}.counter_search_ids reference unknown searches {unknown}")
        # A counter-search counts only when results were actually inspected;
        # logging a query that nobody read is not seeking disconfirmation.
        return any(
            search_by_id.get(ref, {}).get("purpose") == "counter"
            and isinstance(search_by_id[ref].get("results_considered"), int)
            and search_by_id[ref]["results_considered"] >= 1
            for ref in refs
            if ref in search_by_id
        )

    unchallenged: list[str] = []
    for claim_id, claim in ctx.claim_by_id.items():
        searched = counter_searched(claim, f"claim {claim_id}")
        if claim.get("importance") != "load-bearing" or claim.get("kind") not in {"inference", "forecast"}:
            continue
        if not claim.get("contradicting_source_ids") and not searched:
            unchallenged.append(claim_id)
    for hypothesis_id, hypothesis in ctx.hypothesis_by_id.items():
        if not counter_searched(hypothesis, f"hypothesis {hypothesis_id}"):
            unchallenged.append(hypothesis_id)
    if unchallenged:
        warnings.append(
            f"[D2] {len(unchallenged)} load-bearing judgment(s) show no sought counter-evidence ({summarize_ids(unchallenged)}); "
            "record contradicting sources or link a `counter` search through counter_search_ids"
        )

    unsearched_gaps: list[int] = []
    missing_primary_claims: set[str] = set()
    for index, gap in enumerate(ctx.gaps):
        if not isinstance(gap, dict):
            continue
        refs = gap.get("search_ids", [])
        if not isinstance(refs, list) or any(ref not in search_by_id for ref in refs):
            errors.append(f"[D3] coverage_gaps[{index}].search_ids must reference logged searches")
            refs = []
        if gap.get("kind") in SEARCHED_GAP_KINDS and not refs:
            unsearched_gaps.append(index)
        if gap.get("kind") == "missing-primary":
            missing_primary_claims.update(value for value in gap.get("claim_ids", []) if isinstance(value, str))
    if unsearched_gaps:
        warnings.append(f"[D3] coverage gap(s) {summarize_ids(unsearched_gaps)} assert evidence was missing or inaccessible without linking the searches that tried; add search_ids")

    undispositioned: list[int] = []
    for source_id, source in ctx.source_by_id.items():
        disposition = source.get("disposition")
        if disposition is not None:
            require(errors, disposition in SOURCE_DISPOSITIONS, f"[D4] source {source_id}.disposition must be one of {sorted(SOURCE_DISPOSITIONS)}")
            if disposition == "cited":
                require(errors, source_id in ctx.cited, f"[D4] source {source_id} is dispositioned 'cited' but report.md does not cite it")
            elif disposition in SOURCE_DISPOSITIONS - {"cited"}:
                require(errors, text(source.get("disposition_note")), f"[D4] source {source_id}.disposition_note must explain why a retrieved source is not cited")
        elif source_id not in ctx.cited:
            undispositioned.append(source_id)
    if undispositioned:
        warnings.append(
            f"[D4] {len(undispositioned)} retrieved source(s) are neither cited nor dispositioned ({summarize_ids(sorted(undispositioned))}); "
            "use them or record why not, so strong evidence is not silently left on the table"
        )

    secondary_only: list[str] = []
    for claim_id, claim in ctx.claim_by_id.items():
        if claim.get("importance") != "load-bearing" or claim_id in missing_primary_claims:
            continue
        supporting = [ctx.source_by_id[value] for value in claim.get("source_ids") or [] if value in ctx.source_by_id]
        if supporting and all(source.get("directness") in {"secondary", "commentary"} for source in supporting):
            secondary_only.append(claim_id)
    if secondary_only:
        warnings.append(f"[D5] load-bearing claim(s) {summarize_ids(secondary_only)} rest only on secondary or commentary sources; trace them to primary evidence or record a missing-primary gap naming the claim")

    unassessed: list[str] = []
    for claim_id, claim in ctx.claim_by_id.items():
        if claim.get("kind") != "attributed":
            continue
        underlying = claim.get("underlying_status")
        if underlying is not None:
            require(errors, underlying in CLAIM_STATUS, f"[D6] claim {claim_id}.underlying_status must be one of {sorted(CLAIM_STATUS)}")
        elif claim.get("importance") == "load-bearing":
            unassessed.append(claim_id)
    if unassessed:
        warnings.append(
            f"[D6] load-bearing attributed claim(s) {summarize_ids(unassessed)} lack underlying_status; `status` says whether the source said it, "
            "underlying_status says whether what it said is established"
        )


def check_calibration(ctx: ReportContext, errors: list[str], warnings: list[str]) -> None:
    """[C] Open hypotheses need a date on which they can be scored, or a reason they cannot."""
    undated: list[str] = []
    for hypothesis_id, hypothesis in ctx.hypothesis_by_id.items():
        resolve_by = hypothesis.get("resolve_by")
        if resolve_by is not None:
            require(errors, parse_temporal(resolve_by) is not None, f"[C1] hypothesis {hypothesis_id}.resolve_by must be null or an ISO date")
            if ctx.cutoff and parse_temporal(resolve_by) is not None:
                require(errors, not_after(ctx.cutoff, resolve_by), f"[C1] hypothesis {hypothesis_id}.resolve_by must not precede the report cutoff")
        resolution = hypothesis.get("resolution") if isinstance(hypothesis.get("resolution"), dict) else {}
        if resolution.get("status") == "open" and resolve_by is None and not text(hypothesis.get("unresolvable_reason")):
            undated.append(hypothesis_id)
    if undated:
        warnings.append(f"[C1] open hypothesis(es) {summarize_ids(undated)} have neither resolve_by nor unresolvable_reason; unscored forecasts cannot calibrate anything")


def check_review_evidence(ctx: ReportContext, errors: list[str], warnings: list[str]) -> None:
    """[R] Semantic audit and coverage review records."""
    evidence_ids = {item["id"] for item in ctx.evidence if isinstance(item.get("id"), str)}
    audit = ctx.review.get("entailment_audit")
    if audit is not None:
        if not isinstance(audit, dict):
            errors.append("[R1] review.entailment_audit must be an object")
        else:
            require(errors, text(audit.get("route")), "[R1] review.entailment_audit.route must name who judged the sample")
            require(errors, parse_temporal(audit.get("audited_at")) is not None, "[R1] review.entailment_audit.audited_at must be ISO-8601")
            items = audit.get("items")
            require(errors, isinstance(items, list) and bool(items), "[R1] review.entailment_audit.items must be a non-empty list")
            for index, item in enumerate(items if isinstance(items, list) else []):
                where = f"[R1] review.entailment_audit.items[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{where} must be an object")
                    continue
                claim_id, evidence_id = item.get("claim_id"), item.get("evidence_id")
                require(errors, isinstance(claim_id, str) and claim_id in ctx.claim_by_id, f"{where}.claim_id must name a claim")
                require(errors, evidence_id is None or (isinstance(evidence_id, str) and evidence_id in evidence_ids), f"{where}.evidence_id must be null or name an evidence record")
                excerpt_verdict = item.get("excerpt_verdict")
                prose_verdict = item.get("prose_verdict")
                require(errors, excerpt_verdict is None or excerpt_verdict in EXCERPT_VERDICTS, f"{where}.excerpt_verdict must be null or one of {sorted(EXCERPT_VERDICTS)}")
                require(errors, prose_verdict is None or prose_verdict in PROSE_VERDICTS, f"{where}.prose_verdict must be null or one of {sorted(PROSE_VERDICTS)}")
                require(errors, excerpt_verdict is not None or prose_verdict is not None, f"{where} must record an excerpt or prose verdict")
                problem = (excerpt_verdict not in (None, "supports")) or (prose_verdict not in (None, "faithful", "not-anchored"))
                if problem:
                    require(errors, text(item.get("disposition")), f"{where} records a problem verdict and needs a disposition describing the repair or why it stands")
    coverage = ctx.review.get("coverage_review")
    if coverage is not None:
        if not isinstance(coverage, dict):
            errors.append("[R2] review.coverage_review must be an object")
        else:
            require(errors, text(coverage.get("route")), "[R2] review.coverage_review.route must name the reviewer")
            require(errors, isinstance(coverage.get("web_access"), bool), "[R2] review.coverage_review.web_access must be a boolean")
            require(errors, isinstance(coverage.get("missing_evidence"), list), "[R2] review.coverage_review.missing_evidence must list what the reviewer found missing (empty when nothing)")
            require(errors, text(coverage.get("disposition")), "[R2] review.coverage_review.disposition must say how the findings were handled")
    if ctx.report.get("status") == "reviewed":
        if audit is None:
            warnings.append("[R1] reviewed report has no entailment audit; sample claim/excerpt/prose pairs with `audit-sample` and record verdicts with `record-audit`")
        if not isinstance(coverage, dict) or coverage.get("web_access") is not True:
            warnings.append("[R2] reviewed report has no coverage review with web access; a reviewer limited to the supplied files cannot find what the research missed")


def render_sources(directory: Path) -> None:
    ledger = load_json(directory / "sources-ledger.json")
    markdown_path = directory / "report.md"
    markdown = markdown_path.read_text(encoding="utf-8")
    body, _listed = report_body_and_sources(markdown)
    lines = ["## Sources", ""]
    cited = {int(value) for value in CITE_RE.findall(body)}
    for source in ledger.get("sources", []):
        if source["id"] in cited:
            lines.append(f"[{source['id']}] {source['url']} — {source['title']}")
    write_text_atomic(markdown_path, body.rstrip() + "\n\n" + "\n".join(lines) + "\n")


def add_source(directory: Path, url: str, title: str, accessed: str) -> int:
    if not valid_url(url):
        raise ValueError("source URL must be http(s)")
    if parse_temporal(accessed) is None:
        raise ValueError("accessed must be an ISO date or datetime")
    ledger_path = directory / "sources-ledger.json"
    ledger = load_json(ledger_path)
    sources = ledger.setdefault("sources", [])
    if not isinstance(sources, list) or not all(isinstance(item, dict) for item in sources):
        raise ValueError("sources-ledger.json sources must be a list of objects")
    for source in sources:
        if source.get("url") == url:
            source["accessed"] = accessed
            write_json(ledger_path, ledger)
            return int(source["id"])
    source_id = max((int(source["id"]) for source in sources if isinstance(source.get("id"), int)), default=0) + 1
    sources.append({"id": source_id, "url": url, "title": title, "accessed": accessed})
    write_json(ledger_path, ledger)
    return source_id


def verify_quote(quote: str, evidence_file: Path) -> None:
    """Raise ``ValueError`` unless ``quote`` appears verbatim (whitespace-normalized) in ``evidence_file``."""
    if not text(quote):
        raise ValueError("quote text must be non-empty")
    if len(quote) > 1000:
        raise ValueError("quote exceeds 1000 characters; keep excerpts short")
    evidence = evidence_file.read_text(encoding="utf-8")
    if normalize_whitespace(quote) not in normalize_whitespace(evidence):
        raise ValueError("quote was not found verbatim in the evidence file")


def ledger_source(ledger: Any, source_id: int) -> dict[str, Any]:
    sources = ledger.get("sources") if isinstance(ledger, dict) else None
    if not isinstance(sources, list):
        raise ValueError("sources-ledger.json sources must be a list")
    source = next((item for item in sources if isinstance(item, dict) and item.get("id") == source_id), None)
    if source is None:
        raise ValueError(f"unknown source id: {source_id}")
    return source


def record_quote(ledger: Any, source_id: int, quote: str, binding: dict[str, Any] | None = None) -> bool:
    """Record ``quote`` on the ledger source in memory; return True when the ledger changed.

    ``binding`` carries provenance: ``{"snapshot": digest, "offset": n}`` for
    snapshot-verified text or ``{"file_sha256": digest}`` for an
    analyst-supplied file. An existing unbound record of the same text gains a
    snapshot binding; an existing snapshot binding is never replaced.
    """
    source = ledger_source(ledger, source_id)
    quotes = source.get("quotes")
    if quotes is None:
        quotes = []
        source["quotes"] = quotes
    if not isinstance(quotes, list) or not all(isinstance(item, dict) for item in quotes):
        raise ValueError(f"source {source_id} has a malformed quotes list; repair sources-ledger.json first")
    binding = binding or {}
    for item in quotes:
        if normalize_whitespace(str(item.get("text", ""))) == normalize_whitespace(quote):
            if binding.get("snapshot") and not item.get("snapshot"):
                item.pop("file_sha256", None)
                item.update(binding)
                return True
            return False
    quotes.append({"text": quote, "added": datetime.now(timezone.utc).date().isoformat(), **binding})
    return True


def quote_binding(directory: Path, ledger: Any, source_id: int, quote: str, evidence_file: Path | None, snapshot: str | None) -> dict[str, Any]:
    """Verify ``quote`` against a recorded snapshot or a supplied file and return its provenance binding."""
    if (evidence_file is None) == (snapshot is None):
        raise ValueError("supply exactly one of --snapshot or --from-file")
    if evidence_file is not None:
        verify_quote(quote, evidence_file)
        return {"file_sha256": hashlib.sha256(evidence_file.read_bytes()).hexdigest()}
    if not text(quote):
        raise ValueError("quote text must be non-empty")
    if len(quote) > 1000:
        raise ValueError("quote exceeds 1000 characters; keep excerpts short")
    source = ledger_source(ledger, source_id)
    records = [record for record in source.get("snapshots") or [] if isinstance(record, dict) and snapshots.valid_digest(record.get("sha256"))]
    if not records:
        raise ValueError(f"source {source_id} has no recorded snapshot; run `fetch` or `capture` first")
    if snapshot == "latest":
        digest = records[-1]["sha256"]
    else:
        matches = [record["sha256"] for record in records if record["sha256"].startswith(str(snapshot))]
        if len(matches) != 1:
            raise ValueError(f"--snapshot {snapshot!r} does not identify exactly one snapshot recorded on source {source_id}")
        digest = matches[0]
    snapshot_text = snapshots.read_snapshot(ROOT, directory, digest)
    if snapshot_text is None:
        raise ValueError(f"snapshot {digest[:12]}… is recorded but not present in any snapshot store")
    if snapshots.sha256_text(snapshot_text) != digest:
        raise ValueError(f"snapshot {digest[:12]}… does not match its hash; the stored text was altered")
    offset = snapshots.locate(quote, snapshot_text)
    if offset < 0:
        raise ValueError(f"quote was not found verbatim in snapshot {digest[:12]}…")
    return {"snapshot": digest, "offset": offset}


def add_quote(directory: Path, source_id: int, quote: str, evidence_file: Path | None = None, snapshot: str | None = None) -> None:
    """Verify ``quote`` and record it in the ledger with its provenance binding.

    With ``snapshot``, the quote is checked against source text captured by
    ``fetch`` or ``capture`` and bound to that text's hash. With
    ``evidence_file``, the check attests only that the quotation matches a
    caller-supplied file; the file's hash is recorded, but nothing ties it to
    the registered URL.
    """
    ledger_path = directory / "sources-ledger.json"
    ledger = load_json(ledger_path)
    binding = quote_binding(directory, ledger, source_id, quote, evidence_file, snapshot)
    if record_quote(ledger, source_id, quote, binding):
        write_json(ledger_path, ledger)


def next_prefixed_id(existing: list[str], prefix: str) -> str:
    highest = 0
    for value in existing:
        match = re.fullmatch(rf"{re.escape(prefix)}(\d+)", str(value))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}{highest + 1}"


def add_evidence(
    directory: Path,
    source_id: int,
    quote: str,
    evidence_file: Path | None,
    claim_ids: list[str],
    location: str,
    captured_at: str,
    snapshot: str | None = None,
) -> str:
    """Verify a quotation, record it in the ledger, and attach a claim-facing evidence record.

    This is the one-step path that keeps ``sources-ledger.json`` quotes and
    ``assessment.json.evidence`` in agreement, so the validator can confirm the
    excerpt corresponds to a quotation that was checked against supplied text.

    All inputs are validated before the first write. Both files are then
    replaced atomically, ledger first: if the second write fails, the ledger
    holds an extra verified quote and re-running the same command is
    idempotent, whereas an assessment record without its quote would be
    exactly the unverifiable state the validator warns about.
    """
    if not claim_ids:
        raise ValueError("at least one --claim is required")
    if not text(location):
        raise ValueError("--location must be non-empty")
    if not valid_datetime(captured_at):
        raise ValueError("--captured-at must be ISO-8601")

    assessment_path = directory / "assessment.json"
    ledger_path = directory / "sources-ledger.json"
    assessment = load_json(assessment_path)
    ledger = load_json(ledger_path)
    binding = quote_binding(directory, ledger, source_id, quote, evidence_file, snapshot)
    if not isinstance(assessment, dict):
        raise ValueError("assessment.json must be an object")
    ledger_entry = ledger_source(ledger, source_id)
    if not isinstance(ledger_entry.get("quotes", []), list) or not all(isinstance(q, dict) for q in ledger_entry.get("quotes") or []):
        raise ValueError(f"source {source_id} has a malformed quotes list; repair sources-ledger.json first")
    assessment_sources = assessment.get("sources")
    if not isinstance(assessment_sources, list) or not any(isinstance(src, dict) and src.get("id") == source_id for src in assessment_sources):
        raise ValueError(f"source {source_id} is registered in the ledger but has no assessment.json sources entry; add its assessment first")
    report = assessment.get("report") if isinstance(assessment.get("report"), dict) else {}
    if report.get("cutoff") and not not_after(captured_at, report.get("cutoff")):
        raise ValueError("--captured-at is after the report cutoff")

    claims = assessment.get("claims")
    if not isinstance(claims, list) or not all(isinstance(claim, dict) for claim in claims):
        raise ValueError("assessment.json claims must be a list of objects")
    known = {claim.get("id") for claim in claims}
    missing = [claim_id for claim_id in claim_ids if claim_id not in known]
    if missing:
        raise ValueError(f"unknown claim id(s): {', '.join(missing)}")
    for claim in claims:
        if claim.get("id") in claim_ids:
            claim_sources = claim.get("source_ids")
            if not isinstance(claim_sources, list) or source_id not in claim_sources:
                raise ValueError(f"claim {claim['id']} does not list source {source_id}; add it to source_ids first")

    evidence = assessment.get("evidence")
    if evidence is None:
        evidence = []
        assessment["evidence"] = evidence
    if not isinstance(evidence, list) or not all(isinstance(item, dict) for item in evidence):
        raise ValueError("assessment.json evidence must be a list of objects")
    seen_evidence_ids: set[str] = set()
    for item in evidence:
        item_id = item.get("id")
        if not (isinstance(item_id, str) and ID_RE.fullmatch(item_id)):
            raise ValueError(f"an existing evidence record has an invalid id {item_id!r}; repair assessment.json first")
        if item_id in seen_evidence_ids:
            raise ValueError(f"duplicate evidence id {item_id}; repair assessment.json first")
        seen_evidence_ids.add(item_id)
        if not isinstance(item.get("supports_claim_ids", []), list):
            raise ValueError(f"evidence {item_id} has a malformed supports_claim_ids")
        if not text(item.get("location")) or not valid_datetime(item.get("captured_at")):
            raise ValueError(f"evidence {item_id} has a malformed location or captured_at; repair assessment.json first")

    existing = next(
        (
            item
            for item in evidence
            if item.get("kind", "excerpt") == "excerpt"
            and item.get("source_id") == source_id
            and normalize_whitespace(str(item.get("excerpt", ""))) == normalize_whitespace(quote)
        ),
        None,
    )
    if existing is not None and not text(existing.get("id")):
        raise ValueError("an existing matching evidence record has no id; repair assessment.json first")
    new_id = None if existing is not None else next_prefixed_id([item.get("id") for item in evidence], "E")
    if existing is not None and (str(existing.get("location")) != location or str(existing.get("captured_at")) != captured_at):
        raise ValueError(
            f"evidence {existing['id']} already records this excerpt with location {existing.get('location')!r} "
            f"captured at {existing.get('captured_at')}; reuse those values or edit the record deliberately"
        )

    if record_quote(ledger, source_id, quote, binding):
        write_json(ledger_path, ledger)
    if existing is not None:
        if str(existing.get("location")) != location or str(existing.get("captured_at")) != captured_at:
            raise ValueError(
                f"evidence {existing['id']} already records this excerpt with location {existing.get('location')!r} "
                f"captured at {existing.get('captured_at')}; reuse those values or edit the record deliberately"
            )
        existing["supports_claim_ids"] = sorted(set(existing.get("supports_claim_ids", [])) | set(claim_ids))
        write_json(assessment_path, assessment)
        return str(existing["id"])
    evidence.append(
        {
            "id": new_id,
            "kind": "excerpt",
            "source_id": source_id,
            "excerpt": quote,
            "location": location,
            "supports_claim_ids": list(claim_ids),
            "captured_at": captured_at,
        }
    )
    write_json(assessment_path, assessment)
    return str(new_id)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def snapshot_preflight(directory: Path, url: str, title: str | None, store: str, retrieved_at: str) -> tuple[dict[str, Any] | None, Path]:
    """Check everything that can fail before any network or file work; return the existing ledger entry and target store."""
    if store not in {"vault", "report"}:
        raise ValueError("--store must be vault or report")
    ledger = load_json(directory / "sources-ledger.json")
    sources = ledger.get("sources") if isinstance(ledger, dict) else None
    if not isinstance(sources, list):
        raise ValueError("sources-ledger.json sources must be a list")
    existing = next((item for item in sources if isinstance(item, dict) and item.get("url") == url), None)
    if existing is None and not text(title):
        raise ValueError("--title is required when the URL is not yet in the ledger")
    assessment = load_json(directory / "assessment.json")
    cutoff = (assessment.get("report") or {}).get("cutoff") if isinstance(assessment, dict) else None
    if cutoff and not not_after(retrieved_at, cutoff):
        raise ValueError(f"retrieval time {retrieved_at} is after the report cutoff {cutoff}; a later retrieval belongs in a dated successor")
    target = snapshots.report_store(directory) if store == "report" else snapshots.vault_store(ROOT)
    if store == "vault":
        snapshots.ensure_private(target)
    return existing, target


def record_snapshot(directory: Path, url: str, title: str | None, text_value: str, metadata: dict[str, Any], raw: bytes | None, store: str) -> tuple[int, str]:
    """Store a snapshot, register or update its ledger source, and attach the snapshot record."""
    retrieved_at = str(metadata.get("retrieved_at") or utc_now())
    existing, target = snapshot_preflight(directory, url, title, store, retrieved_at)
    ledger_path = directory / "sources-ledger.json"
    digest = snapshots.store_snapshot(target, text_value, {**metadata, "retrieved_at": retrieved_at}, raw)
    source_id = add_source(directory, url, title or str(existing.get("title")), retrieved_at[:10])
    ledger = load_json(ledger_path)
    source = ledger_source(ledger, source_id)
    records = source.setdefault("snapshots", [])
    if not isinstance(records, list):
        raise ValueError(f"source {source_id} has a malformed snapshots list")
    if not any(isinstance(record, dict) and record.get("sha256") == digest for record in records):
        entry = {"sha256": digest, "method": metadata.get("method", "capture"), "retrieved_at": retrieved_at, "store": store}
        for key in ("final_url", "status", "content_type", "raw_sha256", "note"):
            if metadata.get(key) is not None:
                entry[key] = metadata[key]
        records.append(entry)
        write_json(ledger_path, ledger)
    return source_id, digest


def fetch_source(directory: Path, url: str, title: str | None, store: str) -> tuple[int, str]:
    if not valid_url(url):
        raise ValueError("source URL must be http(s)")
    snapshot_preflight(directory, url, title, store, utc_now())
    text_value, metadata, raw = snapshots.fetch(url)
    return record_snapshot(directory, url, title, text_value, metadata, raw if store == "vault" else None, store)


def capture_source(directory: Path, url: str, title: str | None, text_file: Path, retrieved_at: str | None, note: str | None, store: str) -> tuple[int, str]:
    """Record text obtained outside ``fetch`` (a browser render, PDF extraction, archive copy)."""
    if not valid_url(url):
        raise ValueError("source URL must be http(s)")
    if retrieved_at is not None and parse_temporal(retrieved_at) is None:
        raise ValueError("--retrieved-at must be ISO-8601")
    text_value = text_file.read_text(encoding="utf-8")
    if not text(text_value):
        raise ValueError("captured text is empty")
    metadata = {"method": "capture", "url": url, "retrieved_at": retrieved_at or utc_now(), "note": note}
    return record_snapshot(directory, url, title, text_value, metadata, None, store)


def log_search(directory: Path, query: str, engine: str, purpose: str, question: int | None, source_ids: list[int], considered: int | None, note: str | None, run_at: str | None) -> str:
    if purpose not in SEARCH_PURPOSES:
        raise ValueError(f"--purpose must be one of {sorted(SEARCH_PURPOSES)}")
    if not text(query) or not text(engine):
        raise ValueError("--query and --engine must be non-empty")
    run_at = run_at or utc_now()
    if parse_temporal(run_at) is None:
        raise ValueError("--at must be ISO-8601")
    path = directory / "assessment.json"
    assessment = load_json(path)
    if not isinstance(assessment, dict):
        raise ValueError("assessment.json must be an object")
    report = assessment.get("report") if isinstance(assessment.get("report"), dict) else {}
    if report.get("cutoff") and not not_after(run_at, report["cutoff"]):
        raise ValueError("search time is after the report cutoff")
    questions = report.get("questions") if isinstance(report.get("questions"), list) else []
    if question is not None and not 1 <= question <= len(questions):
        raise ValueError(f"--question must be between 1 and {len(questions)}")
    known = {item.get("id") for item in assessment.get("sources", []) if isinstance(item, dict)}
    unknown = [value for value in source_ids if value not in known]
    if unknown:
        raise ValueError(f"--source ids {unknown} have no assessment.json sources entry")
    searches = assessment.setdefault("searches", [])
    if not isinstance(searches, list):
        raise ValueError("assessment.json searches must be a list")
    search_id = next_prefixed_id([item.get("id") for item in searches if isinstance(item, dict)], "S")
    entry: dict[str, Any] = {"id": search_id, "question": question, "purpose": purpose, "engine": engine, "query": query, "run_at": run_at, "results_considered": considered, "source_ids": source_ids}
    if text(note):
        entry["notes"] = note
    searches.append(entry)
    write_json(path, assessment)
    return search_id


def audit_sample(directory: Path, size: int, seed: int | None) -> dict[str, Any]:
    """Draw a reproducible sample of claim/evidence/prose triples for semantic review.

    Every load-bearing claim is eligible; the sample prefers load-bearing
    claims and then fills with others. Each item carries the claim, its
    evidence excerpt with surrounding snapshot context when available, and the
    anchored report passages that assert it, so a reviewer can judge both
    whether the excerpt supports the claim and whether the prose is faithful to it.
    """
    if size < 1:
        raise ValueError("--size must be positive")
    seed = seed if seed is not None else random.SystemRandom().randrange(1, 2**31)
    assessment = load_json(directory / "assessment.json")
    ledger = load_json(directory / "sources-ledger.json")
    body, _ = report_body_and_sources((directory / "report.md").read_text(encoding="utf-8"))
    claims = {c["id"]: c for c in assessment.get("claims", []) if isinstance(c, dict) and isinstance(c.get("id"), str)}
    evidence = [e for e in assessment.get("evidence", []) if isinstance(e, dict)]
    passages: dict[str, list[str]] = {}
    known = set(claims) | {h.get("id") for h in assessment.get("hypotheses", []) if isinstance(h, dict) and isinstance(h.get("id"), str)}
    for unit in prose_units(body):
        for claim_id in anchor_ids(unit, known):
            passages.setdefault(claim_id, []).append(strip_anchors(unit, known))
    pairs: list[tuple[str, dict[str, Any] | None]] = []
    for claim_id, claim in claims.items():
        items = [e for e in evidence if claim_id in (e.get("supports_claim_ids") or [])]
        for item in items or [None]:
            pairs.append((claim_id, item))
    rng = random.Random(seed)
    load_bearing = [pair for pair in pairs if claims[pair[0]].get("importance") == "load-bearing"]
    others = [pair for pair in pairs if pair not in load_bearing]
    rng.shuffle(load_bearing)
    rng.shuffle(others)
    chosen = (load_bearing + others)[:size]
    ledger_by_id = {s.get("id"): s for s in ledger.get("sources", []) if isinstance(s, dict)}
    items_out = []
    for claim_id, item in chosen:
        context_text = ""
        if item is not None and item.get("kind", "excerpt") == "excerpt":
            for quote in (ledger_by_id.get(item.get("source_id")) or {}).get("quotes", []) or []:
                if normalize_whitespace(str(quote.get("text", ""))) == normalize_whitespace(str(item.get("excerpt", ""))) and quote.get("snapshot"):
                    snapshot_text = snapshots.read_snapshot(ROOT, directory, quote["snapshot"])
                    if snapshot_text:
                        context_text = snapshots.context(item["excerpt"], snapshot_text)
                    break
        claim = claims[claim_id]
        items_out.append({
            "claim_id": claim_id,
            "claim": claim.get("statement"),
            "claim_kind": claim.get("kind"),
            "claim_status": claim.get("status"),
            "evidence_id": item.get("id") if item else None,
            "evidence_kind": item.get("kind", "excerpt") if item else None,
            "source_id": item.get("source_id") if item else None,
            "source_url": (ledger_by_id.get(item.get("source_id")) or {}).get("url") if item else None,
            "excerpt": item.get("excerpt") if item else None,
            "snapshot_context": context_text or None,
            "report_passages": passages.get(claim_id, []),
            "excerpt_verdict": None,
            "prose_verdict": None,
            "note": "",
            "disposition": "",
        })
    return {"seed": seed, "population": len(pairs), "size": len(items_out), "instructions": AUDIT_INSTRUCTIONS, "items": items_out}


AUDIT_INSTRUCTIONS = (
    "For each item judge two relations independently. excerpt_verdict: does the excerpt (read in its snapshot context) "
    "support the claim as stated? One of supports, partial, contradicts, unrelated; null when there is no excerpt. "
    "prose_verdict: do the report passages say what the claim says, no stronger and no weaker? One of faithful, "
    "overstates, understates, contradicts; not-anchored when no passage is marked. Explain every non-supporting or "
    "non-faithful verdict in note. The author later fills disposition with the repair."
)


def record_audit(directory: Path, verdict_file: Path, route: str) -> dict[str, Any]:
    if not text(route):
        raise ValueError("--route must name the model, person or process that judged the sample")
    packet = load_json(verdict_file)
    items = packet.get("items") if isinstance(packet, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("verdict file must contain a non-empty items list")
    kept_keys = ("claim_id", "evidence_id", "excerpt_verdict", "prose_verdict", "note", "disposition")
    for item in items:
        if not isinstance(item, dict) or not text(item.get("claim_id")):
            raise ValueError("every verdict item must be an object naming its claim_id as a string")
        if item.get("evidence_id") is not None and not text(item.get("evidence_id")):
            raise ValueError(f"item for claim {item['claim_id']} has an evidence_id that is not a string")
    recorded = [{key: item.get(key) for key in kept_keys} for item in items]
    for item in recorded:
        if item["excerpt_verdict"] is None and item["prose_verdict"] is None:
            raise ValueError(f"item for claim {item['claim_id']} has no verdict; every sampled item must be judged")
    path = directory / "assessment.json"
    assessment = load_json(path)
    review = assessment.setdefault("review", {})
    audit = {"route": route, "audited_at": utc_now(), "seed": packet.get("seed"), "population": packet.get("population"), "items": recorded}
    review["entailment_audit"] = audit
    write_json(path, assessment)
    judged_excerpts = [i for i in recorded if i["excerpt_verdict"] is not None]
    judged_prose = [i for i in recorded if i["prose_verdict"] not in (None, "not-anchored")]
    return {
        "items": len(recorded),
        "excerpt_problems": sum(1 for i in judged_excerpts if i["excerpt_verdict"] != "supports"),
        "excerpts_judged": len(judged_excerpts),
        "prose_problems": sum(1 for i in judged_prose if i["prose_verdict"] != "faithful"),
        "prose_judged": len(judged_prose),
        "undispositioned": sum(1 for i in recorded if ((i["excerpt_verdict"] not in (None, "supports")) or (i["prose_verdict"] not in (None, "faithful", "not-anchored"))) and not text(i.get("disposition"))),
    }


def due_rows(as_of: str) -> list[dict[str, Any]]:
    """Open hypotheses whose resolve_by date has arrived."""
    if parse_temporal(as_of) is None:
        raise ValueError("--as-of must be ISO-8601")
    rows = []
    for assessment_path in sorted(REPORTS.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/*/assessment.json")):
        try:
            assessment = load_json(assessment_path)
        except ValueError:
            continue
        for hypothesis in assessment.get("hypotheses", []) or []:
            if not isinstance(hypothesis, dict):
                continue
            resolution = hypothesis.get("resolution") if isinstance(hypothesis.get("resolution"), dict) else {}
            resolve_by = hypothesis.get("resolve_by")
            if resolution.get("status") == "open" and parse_temporal(resolve_by) is not None and not_after(resolve_by, as_of):
                rows.append({"report": str(assessment_path.parent.relative_to(ROOT)), "hypothesis": hypothesis.get("id"), "resolve_by": resolve_by, "statement": hypothesis.get("statement"), "central": (hypothesis.get("probability") or {}).get("central")})
    return rows


def reader_text(directory: Path) -> str:
    """Report Markdown with claim anchors removed, for presentation builds."""
    assessment = load_json(directory / "assessment.json")
    known = {item.get("id") for key in ("claims", "hypotheses") for item in (assessment.get(key) or []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    return strip_anchors((directory / "report.md").read_text(encoding="utf-8"), known)


def init_report(args: argparse.Namespace) -> Path:
    if not SLUG_RE.fullmatch(args.slug):
        raise SystemExit("error: --slug must be lowercase kebab-case")
    try:
        cutoff = datetime.fromisoformat(args.cutoff.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"error: invalid --cutoff: {exc}") from None
    directory = REPORTS / f"{cutoff.year:04d}" / f"{cutoff.month:02d}" / args.slug
    if directory.exists():
        raise SystemExit(f"error: report already exists: {directory}")
    (directory / "evidence").mkdir(parents=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    assessment = {
        "schema_version": 1,
        "report": {
            "slug": args.slug,
            "title": args.title,
            "mode": args.mode,
            "domain": args.domain,
            "cutoff": args.cutoff,
            "created": now,
            "updated": now,
            "status": "draft",
            "lineage": {"supersedes": None, "superseded_by": None},
            "summary": f"{PLACEHOLDER_PREFIX}the decision-grade verdict.",
            "questions": [f"{PLACEHOLDER_PREFIX}the first research question."],
        },
        "sources": [],
        "claims": [],
        "evidence": [],
        "hypotheses": [],
        "searches": [],
        "coverage_gaps": [],
        "review": {
            "deterministic_checks": [],
            "independent_review": "not-run",
            "notes": "Independent review has not run.",
        },
    }
    write_json(directory / "assessment.json", assessment)
    write_json(directory / "sources-ledger.json", {"version": 1, "sources": []})
    sections = "\n\n".join(
        f"## {heading}\n\n{PLACEHOLDER_PREFIX}the {heading.lower()} content for this {args.mode} report.[unverified]"
        for heading in MODE_SECTIONS[args.mode]
    )
    report = f"""---
title: {frontmatter_encode(args.title)}
slug: {args.slug}
mode: {args.mode}
domain: {args.domain}
cutoff: {args.cutoff}
status: draft
assessment: assessment.json
---

# {args.title}

**Cutoff:** {args.cutoff}

**Structured assessment:** [assessment.json](assessment.json)

{sections}

## Sources
"""
    write_text_atomic(directory / "report.md", report)
    return directory



def supersede_report(predecessor: Path, slug: str, title: str, cutoff: str, mode: str | None = None, domain: str | None = None) -> Path:
    """Create a dated successor of ``predecessor`` and link lineage in both directions.

    The predecessor keeps its cutoff and content; only ``status`` and
    ``lineage.superseded_by`` change. The successor starts as a scaffold with
    the predecessor's questions copied so the update can state what changed.

    Every input is checked before the first write. If any later write fails,
    the predecessor's two files are restored byte-for-byte and the partially
    created successor directory is removed.
    """
    predecessor = predecessor.resolve()
    try:
        pred_rel = predecessor.relative_to(REPORTS.resolve())
    except ValueError:
        raise ValueError("predecessor must live under the vault's reports/ directory") from None
    pred_rel = Path("reports") / pred_rel
    pred_assessment_path = predecessor / "assessment.json"
    pred_markdown_path = predecessor / "report.md"
    pred_assessment_bytes = pred_assessment_path.read_bytes()
    pred_markdown_bytes = pred_markdown_path.read_bytes()
    pred_assessment = json.loads(pred_assessment_bytes.decode("utf-8"))
    pred_markdown = pred_markdown_bytes.decode("utf-8")
    pred_report = pred_assessment.get("report") if isinstance(pred_assessment, dict) else None
    if not isinstance(pred_report, dict) or not isinstance(pred_report.get("lineage"), dict):
        raise ValueError("predecessor assessment.json must contain report.lineage; repair it before superseding")
    if pred_report["lineage"].get("superseded_by"):
        raise ValueError(f"predecessor is already superseded by {pred_report['lineage']['superseded_by']}")
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("--slug must be lowercase kebab-case")
    if parse_temporal(pred_report.get("cutoff")) is None or parse_temporal(cutoff) is None:
        raise ValueError("both predecessor and successor cutoffs must be valid ISO-8601")
    if not strictly_before(pred_report.get("cutoff"), cutoff):
        raise ValueError("successor cutoff must be later than the predecessor cutoff")
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", pred_markdown, re.DOTALL)
    if frontmatter_match is None:
        raise ValueError("predecessor report.md must start with frontmatter")
    status_line = re.compile(r"(?m)^status:[ \t]*(.+?)[ \t]*$")
    status_match = status_line.search(frontmatter_match.group(1))
    if status_match is None or frontmatter_scalar(status_match.group(1)) not in {"draft", "reviewed"}:
        raise ValueError("predecessor report.md frontmatter has no status: draft|reviewed line to retire")
    new_cutoff_dt = parse_temporal(cutoff)
    assert new_cutoff_dt is not None
    successor = REPORTS / f"{new_cutoff_dt.year:04d}" / f"{new_cutoff_dt.month:02d}" / slug
    if successor.exists():
        raise ValueError(f"report already exists: {successor}")
    succ_rel = Path("reports") / successor.resolve().relative_to(REPORTS.resolve())

    new_frontmatter = frontmatter_match.group(1)[: status_match.start()] + "status: superseded" + frontmatter_match.group(1)[status_match.end() :]
    new_markdown = "---\n" + new_frontmatter + "\n---\n" + pred_markdown[frontmatter_match.end() :]
    pred_assessment["report"]["status"] = "superseded"
    pred_assessment["report"]["lineage"]["superseded_by"] = str(succ_rel)
    pred_assessment["report"]["updated"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    args = argparse.Namespace(
        slug=slug,
        title=title,
        cutoff=cutoff,
        mode=mode or pred_report.get("mode", "general"),
        domain=domain or pred_report.get("domain", "general"),
    )
    created = successor
    try:
        init_report(args)
        succ_assessment_path = created / "assessment.json"
        succ_assessment = load_json(succ_assessment_path)
        succ_assessment["report"]["lineage"]["supersedes"] = str(pred_rel)
        succ_assessment["report"]["questions"] = list(pred_report.get("questions") or succ_assessment["report"]["questions"])
        write_json(succ_assessment_path, succ_assessment)
        write_json(pred_assessment_path, pred_assessment)
        write_text_atomic(pred_markdown_path, new_markdown)
    except BaseException:
        # Roll back to the exact prior bytes; a half-linked lineage is worse than no update.
        try:
            pred_assessment_path.write_bytes(pred_assessment_bytes)
            pred_markdown_path.write_bytes(pred_markdown_bytes)
        finally:
            if created.exists():
                shutil.rmtree(created, ignore_errors=True)
        raise
    return created


def resolve_hypothesis(directory: Path, hypothesis_id: str, outcome: str, resolved_at: str, status: str = "resolved") -> None:
    """Score a hypothesis after the fact without editing its original range.

    ``resolved`` records an outcome and date. ``superseded`` marks the
    hypothesis as re-framed by a later report; it records the same
    ``outcome`` text (use it to name the successor hypothesis) and date so the
    calibration record shows when and why scoring stopped.
    """
    if status not in {"resolved", "superseded"}:
        raise ValueError("status must be resolved or superseded")
    if not text(outcome):
        raise ValueError("--outcome must be non-empty")
    if parse_temporal(resolved_at) is None:
        raise ValueError("--at must be an ISO date or datetime")
    assessment_path = directory / "assessment.json"
    assessment = load_json(assessment_path)
    if not isinstance(assessment, dict) or not isinstance(assessment.get("hypotheses"), list):
        raise ValueError("assessment.json hypotheses must be a list")
    hypothesis = next((h for h in assessment["hypotheses"] if isinstance(h, dict) and h.get("id") == hypothesis_id), None)
    if hypothesis is None:
        raise ValueError(f"unknown hypothesis id: {hypothesis_id}")
    resolution = hypothesis.get("resolution") or {}
    if resolution.get("status") != "open":
        raise ValueError(f"hypothesis {hypothesis_id} is already {resolution.get('status')}")
    report_cutoff = (assessment.get("report") or {}).get("cutoff") if isinstance(assessment.get("report"), dict) else None
    if parse_temporal(report_cutoff) is not None and not not_after(report_cutoff, resolved_at):
        raise ValueError("--at must not precede the report cutoff; a hypothesis cannot be scored before it was made")
    hypothesis["resolution"] = {"status": status, "outcome": outcome, "resolved_at": resolved_at}
    if status == "resolved":
        lowered = outcome.strip().lower()
        if lowered in {"true", "yes", "occurred", "confirmed"}:
            hypothesis["resolution"]["outcome_value"] = 1
        elif lowered in {"false", "no", "did-not-occur", "refuted"}:
            hypothesis["resolution"]["outcome_value"] = 0
    write_json(assessment_path, assessment)


def calibration_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for assessment_path in sorted(REPORTS.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/*/assessment.json")):
        try:
            assessment = load_json(assessment_path)
        except ValueError:
            continue
        report = assessment.get("report") or {}
        for hypothesis in assessment.get("hypotheses", []):
            if not isinstance(hypothesis, dict):
                continue
            resolution = hypothesis.get("resolution") or {}
            probability = hypothesis.get("probability") or {}
            rows.append(
                {
                    "report": str(assessment_path.parent.relative_to(ROOT)),
                    "cutoff": report.get("cutoff"),
                    "hypothesis": hypothesis.get("id"),
                    "statement": hypothesis.get("statement"),
                    "central": probability.get("central"),
                    "low": probability.get("low"),
                    "high": probability.get("high"),
                    "status": resolution.get("status"),
                    "outcome": resolution.get("outcome"),
                    "outcome_value": resolution.get("outcome_value"),
                }
            )
    return rows


def calibration_text(rows: list[dict[str, Any]]) -> str:
    def numeric(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    scored = [r for r in rows if r["status"] == "resolved" and r.get("outcome_value") in (0, 1) and all(numeric(r.get(k)) for k in ("low", "central", "high"))]
    open_rows = [r for r in rows if r["status"] == "open"]
    resolved_rows = [r for r in rows if r["status"] == "resolved"]
    superseded_rows = [r for r in rows if r["status"] == "superseded"]
    lines = ["# Forecast calibration", "", f"- Hypotheses: {len(rows)}", f"- Open: {len(open_rows)}", f"- Resolved: {len(resolved_rows)}", f"- Superseded: {len(superseded_rows)}", f"- Resolved with binary outcome (scored): {len(scored)}"]
    if scored:
        brier = sum((float(r["central"]) - r["outcome_value"]) ** 2 for r in scored) / len(scored)
        inside = sum(1 for r in scored if float(r["low"]) <= r["outcome_value"] <= float(r["high"]))
        lines.append(f"- Brier score (central estimates): {brier:.3f}")
        lines.append(f"- Outcomes inside stated interval: {inside}/{len(scored)}")
        if len(scored) < 20:
            lines.append(f"- Caution: {len(scored)} scored outcome(s) is too few to distinguish skill from luck; treat these numbers as a ledger, not a calibration estimate.")
        lines.extend(["", "| Report | Hypothesis | Central | Outcome | Squared error |", "|---|---|---|---|---|"])
        for r in scored:
            lines.append(f"| {r['report']} | {r['hypothesis']} | {float(r['central']):.2f} | {r['outcome_value']} | {(float(r['central']) - r['outcome_value']) ** 2:.3f} |")
    if open_rows:
        lines.extend(["", "## Open hypotheses", ""])
        for r in open_rows:
            lines.append(f"- {r['report']} {r['hypothesis']}: {r['statement']} (central {r['central']})")
    return "\n".join(lines) + "\n"


def index_text() -> str:
    entries: list[tuple[str, str, str, str, str, str, str]] = []
    for assessment_path in REPORTS.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/*/assessment.json"):
        try:
            assessment = load_json(assessment_path)
            report = assessment["report"]
            rel = assessment_path.parent.relative_to(ROOT)
            entries.append((report["cutoff"], report["title"], report["mode"], report["domain"], report["status"], report["summary"], str(rel / "report.md")))
        except (ValueError, KeyError, TypeError):
            continue
    entries.sort(reverse=True)
    lines = [
        "# Research Report Index",
        "",
        "> Generated by `python3 tools/reportctl.py index`. Do not hand-edit entries.",
        "",
    ]
    if not entries:
        lines.append("_No reports yet._")
    else:
        for cutoff, title, mode, domain, status, summary, path in entries:
            lines.extend((f"## [{title}](../{path})", "", f"- **Mode:** {mode}", f"- **Domain:** {domain}", f"- **Cutoff:** {cutoff}", f"- **Status:** {status}", f"- **Verdict:** {summary}", ""))
    return "\n".join(lines).rstrip() + "\n"


def orphan_report_errors() -> list[str]:
    root = ROOT.resolve()
    expected = {
        path.parent.resolve()
        for path in REPORTS.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/*/assessment.json")
    }
    candidates = {
        path.parent.resolve()
        for pattern in ("**/report.md", "**/assessment.json", "**/sources-ledger.json")
        for path in REPORTS.glob(pattern)
        if path.name != "index.md"
    }
    return [
        f"orphan or malformed report path: {path.relative_to(root)}"
        for path in sorted(candidates - expected)
    ]


SENSITIVE_ALLOWLIST_FILE = ".sensitive-allowlist"


def sensitive_allowlist() -> set[str]:
    """Reviewed literal strings that ``scan-sensitive`` must not flag.

    One entry per line in ``<root>/.sensitive-allowlist``; ``#`` starts a
    comment. Use it for documented example values (public JWTs, redacted key
    shapes) that a report legitimately quotes. The file is itself committed
    and reviewable, so every suppression is visible in history.
    """
    path = ROOT / SENSITIVE_ALLOWLIST_FILE
    if not path.is_file():
        return set()
    entries: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped:
            entries.add(stripped)
    return entries


def sensitive_content_errors() -> list[str]:
    errors: list[str] = []
    forbidden_names = {".env", "auth.json", "credentials.json", "id_rsa", "id_ed25519"}
    allowlist = sensitive_allowlist()
    patterns = {
        # A key header followed by base64 body content; the bare header alone
        # is ordinary text about keys, not a key.
        "private key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----\s*(?:[A-Za-z-]+:.*\n\s*)*[A-Za-z0-9+/=]{16,}"),
        "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
        "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        "OpenAI-style key": re.compile(r"\bsk-(?:proj-|ant-|live-)?[A-Za-z0-9_-]{32,}\b"),
        "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{20,}\b"),
        "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "Stripe key": re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}\b"),
    }
    # A Git-ignored private store holds third-party text, not repository
    # content. Skip it only when it sits strictly inside the repository and is
    # ignored: a store misconfigured as the repository or an ancestor, or one
    # Git would commit, is scanned like everything else.
    root = ROOT.resolve()
    private_store = snapshots.vault_store(ROOT).resolve()
    skip_store = (
        private_store != root
        and private_store.is_relative_to(root)
        and shutil.which("git") is not None
        and not snapshots.committable(private_store)
    )
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if skip_store and path.resolve().is_relative_to(private_store):
            continue
        if path.name in forbidden_names or path.name.startswith(".env."):
            errors.append(f"forbidden sensitive filename: {path.relative_to(ROOT)}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if path.name == SENSITIVE_ALLOWLIST_FILE:
            continue
        for label, pattern in patterns.items():
            for match in pattern.finditer(content):
                candidate = match.group(0)
                if candidate.strip() in allowlist or low_entropy(candidate):
                    continue
                errors.append(f"possible {label} in {path.relative_to(ROOT)}")
                break
    return errors


KNOWN_SECRET_PREFIX_RE = re.compile(
    r"^(?:-----BEGIN [A-Z ]+-----\s*|sk-(?:proj-|ant-|live-)?|xox[abprs]-(?:\d+-)?|AIza|AKIA|ASIA|gh[pousr]_|github_pat_|[sr]k_live_)"
)


def low_entropy(candidate: str) -> bool:
    """True for obvious dummy values: a run of one or two repeated characters,
    or a trivial ascending sequence, in the secret-bearing part after any
    known prefix."""
    tail = KNOWN_SECRET_PREFIX_RE.sub("", candidate).strip()
    if len(tail) < 8:
        return False
    if len(set(tail)) <= 2:
        return True
    lowered = tail.lower()
    return lowered in ("0123456789abcdef" * 8)[: len(tail)] or lowered in ("abcdefghijklmnopqrstuvwxyz" * 4)[: len(tail)] or lowered in ("0123456789" * 12)[: len(tail)]


def emit(args: argparse.Namespace, ok: bool, payload: dict[str, Any], human: str, *, errors: list[str] | None = None) -> int:
    """Print a result in JSON or human form and return the exit status.

    JSON mode always writes one object to stdout with ``ok``, ``command``,
    ``errors``, and command-specific fields; nothing goes to stderr. Human mode
    writes errors to stderr as ``ERROR: …`` lines.
    """
    errors = errors or []
    if args.json:
        body = {"ok": ok, "command": args.command, "errors": errors}
        body.update(payload)
        print(json.dumps(body, indent=2, ensure_ascii=False))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if ok and human:
            print(human)
    return 0 if ok else 1


def main() -> int:
    global ROOT, REPORTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root containing reports/ (default: framework checkout)")
    parser.add_argument("--json", action="store_true", help="emit one JSON object on stdout for every command and error path")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create a report skeleton")
    init.add_argument("--slug", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--cutoff", required=True)
    init.add_argument("--mode", choices=sorted(RESEARCH_MODES), default="general")
    init.add_argument("--domain", default="general")
    validate = sub.add_parser("validate", help="validate one report directory")
    validate.add_argument("directory", type=Path)
    validate.add_argument("--strict", action="store_true", help="treat advisory warnings as errors")
    validate.add_argument("--verify-snapshots", action="store_true", help="fail when a snapshot bound to a quotation is not present locally for re-verification")
    render = sub.add_parser("render-sources", help="rewrite report Sources from the local ledger")
    render.add_argument("directory", type=Path)
    add_source_parser = sub.add_parser("add-source", help="register a source in a report-local ledger")
    add_source_parser.add_argument("directory", type=Path)
    add_source_parser.add_argument("url")
    add_source_parser.add_argument("--title", required=True)
    add_source_parser.add_argument("--accessed", required=True)
    add_quote_parser = sub.add_parser("add-quote", help="verify and attach a short source excerpt")
    add_quote_parser.add_argument("directory", type=Path)
    add_quote_parser.add_argument("source_id", type=int)
    add_quote_parser.add_argument("--text", required=True)
    quote_origin = add_quote_parser.add_mutually_exclusive_group(required=True)
    quote_origin.add_argument("--snapshot", help="snapshot digest or unique prefix recorded on the source, or 'latest'")
    quote_origin.add_argument("--from-file", type=Path, help="analyst-supplied text file (weaker provenance than --snapshot)")
    add_evidence_parser = sub.add_parser("add-evidence", help="verify a quotation and attach it to claims in one step")
    add_evidence_parser.add_argument("directory", type=Path)
    add_evidence_parser.add_argument("source_id", type=int)
    add_evidence_parser.add_argument("--text", required=True)
    evidence_origin = add_evidence_parser.add_mutually_exclusive_group(required=True)
    evidence_origin.add_argument("--snapshot", help="snapshot digest or unique prefix recorded on the source, or 'latest'")
    evidence_origin.add_argument("--from-file", type=Path, help="analyst-supplied text file (weaker provenance than --snapshot)")
    add_evidence_parser.add_argument("--claim", action="append", required=True, dest="claims", metavar="CLAIM_ID")
    add_evidence_parser.add_argument("--location", required=True)
    add_evidence_parser.add_argument("--captured-at", required=True)
    fetch_parser = sub.add_parser("fetch", help="retrieve a URL, store its extracted text as a snapshot, and register the source")
    fetch_parser.add_argument("directory", type=Path)
    fetch_parser.add_argument("url")
    fetch_parser.add_argument("--title", help="required when the URL is new to the ledger")
    fetch_parser.add_argument("--store", choices=("vault", "report"), default="vault", help="vault: private Git-ignored store (default); report: commit under evidence/snapshots (redistributable text only)")
    capture_parser = sub.add_parser("capture", help="record source text obtained another way (browser render, PDF extraction, archive copy)")
    capture_parser.add_argument("directory", type=Path)
    capture_parser.add_argument("url")
    capture_parser.add_argument("--from-file", required=True, type=Path)
    capture_parser.add_argument("--title")
    capture_parser.add_argument("--retrieved-at")
    capture_parser.add_argument("--note", help="how the text was obtained, e.g. 'browser render after consent wall'")
    capture_parser.add_argument("--store", choices=("vault", "report"), default="vault")
    search_parser = sub.add_parser("log-search", help="record a search in the report's search log")
    search_parser.add_argument("directory", type=Path)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--engine", required=True, help="search tool, database or catalogue used")
    search_parser.add_argument("--purpose", required=True, choices=sorted(SEARCH_PURPOSES))
    search_parser.add_argument("--question", type=int, help="1-based report question this search serves")
    search_parser.add_argument("--source", type=int, action="append", default=[], dest="sources", help="source id registered from this search (repeatable)")
    search_parser.add_argument("--considered", type=int, help="number of results actually inspected")
    search_parser.add_argument("--note")
    search_parser.add_argument("--at", dest="run_at")
    sample_parser = sub.add_parser("audit-sample", help="write a reproducible claim/evidence/prose sample for semantic review")
    sample_parser.add_argument("directory", type=Path)
    sample_parser.add_argument("--size", type=int, default=12)
    sample_parser.add_argument("--seed", type=int)
    sample_parser.add_argument("--out", type=Path, required=True)
    record_parser = sub.add_parser("record-audit", help="store reviewer verdicts from a completed audit sample")
    record_parser.add_argument("directory", type=Path)
    record_parser.add_argument("--from-file", required=True, type=Path)
    record_parser.add_argument("--route", required=True)
    due_parser = sub.add_parser("due", help="list open hypotheses whose resolve_by date has arrived")
    due_parser.add_argument("--as-of", default=None)
    reader_parser = sub.add_parser("reader", help="print report.md without claim anchors, for presentation builds")
    reader_parser.add_argument("directory", type=Path)
    reader_parser.add_argument("--out", type=Path)
    supersede = sub.add_parser("supersede", help="create a dated successor report and link lineage both ways")
    supersede.add_argument("predecessor", type=Path)
    supersede.add_argument("--slug", required=True)
    supersede.add_argument("--title", required=True)
    supersede.add_argument("--cutoff", required=True)
    supersede.add_argument("--mode", choices=sorted(RESEARCH_MODES))
    supersede.add_argument("--domain")
    resolve = sub.add_parser("resolve", help="record the outcome of a hypothesis without editing its forecast")
    resolve.add_argument("directory", type=Path)
    resolve.add_argument("hypothesis_id")
    resolve.add_argument("--outcome", required=True, help="free text; 'true'/'false' (or yes/no, occurred/did-not-occur) also records a binary outcome_value for scoring")
    resolve.add_argument("--at", required=True, dest="resolved_at")
    resolve.add_argument("--status", choices=("resolved", "superseded"), default="resolved")
    sub.add_parser("calibration", help="summarize resolved hypotheses across the vault")
    index = sub.add_parser("index", help="regenerate reports/index.md")
    index.add_argument("--check", action="store_true")
    sub.add_parser("scan-sensitive", help="scan repository text for high-confidence secret material")
    argv = sys.argv[1:]
    if "--json" in argv:
        # Argparse usage errors would otherwise bypass the JSON envelope and
        # write usage text to stderr.
        import contextlib
        import io

        captured = io.StringIO()
        try:
            with contextlib.redirect_stderr(captured):
                args = parser.parse_args(argv)
        except SystemExit as exc:
            if exc.code in (None, 0):
                raise  # --help: human-readable text on stdout, exit 0, is the one intentional exception
            detail = captured.getvalue().strip().splitlines()
            print(json.dumps({"ok": False, "command": None, "errors": [detail[-1] if detail else "invalid command line"]}, indent=2))
            return 2
    else:
        args = parser.parse_args(argv)
    ROOT = args.root.resolve()
    REPORTS = ROOT / "reports"

    try:
        if args.command == "init":
            directory = init_report(args)
            return emit(args, True, {"directory": str(directory)}, str(directory))
        if args.command == "validate":
            warnings: list[str] = []
            notes: list[str] = []
            errors = validate_report(args.directory, warnings, verify_snapshots=args.verify_snapshots, notes=notes)
            if args.strict:
                errors = errors + [f"strict: {warning}" for warning in warnings]
                warnings = []
            if not args.json:
                for warning in warnings:
                    print(f"WARNING: {warning}", file=sys.stderr)
                for note in notes:
                    print(f"NOTE: {note}", file=sys.stderr)
            suffix = f" ({len(warnings)} warning(s))" if warnings else ""
            return emit(args, not errors, {"directory": str(args.directory), "warnings": warnings, "notes": notes}, f"OK: {args.directory}{suffix}", errors=errors)
        if args.command == "render-sources":
            render_sources(args.directory)
            return emit(args, True, {"directory": str(args.directory)}, f"rewrote {args.directory / 'report.md'}")
        if args.command == "add-source":
            source_id = add_source(args.directory, args.url, args.title, args.accessed)
            return emit(args, True, {"source_id": source_id}, str(source_id))
        if args.command == "add-quote":
            add_quote(args.directory, args.source_id, args.text, args.from_file, args.snapshot)
            return emit(args, True, {"source_id": args.source_id}, f"attached quote to source {args.source_id}")
        if args.command == "add-evidence":
            evidence_id = add_evidence(args.directory, args.source_id, args.text, args.from_file, args.claims, args.location, args.captured_at, args.snapshot)
            return emit(args, True, {"evidence_id": evidence_id, "source_id": args.source_id}, evidence_id)
        if args.command in {"fetch", "capture"}:
            if args.command == "fetch":
                source_id, digest = fetch_source(args.directory, args.url, args.title, args.store)
            else:
                source_id, digest = capture_source(args.directory, args.url, args.title, args.from_file, args.retrieved_at, args.note, args.store)
            return emit(args, True, {"source_id": source_id, "snapshot": digest}, f"source {source_id} snapshot {digest}")
        if args.command == "log-search":
            search_id = log_search(args.directory, args.query, args.engine, args.purpose, args.question, args.sources, args.considered, args.note, args.run_at)
            return emit(args, True, {"search_id": search_id}, search_id)
        if args.command == "audit-sample":
            packet = audit_sample(args.directory, args.size, args.seed)
            write_text_atomic(args.out, json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
            return emit(args, True, {"path": str(args.out), "seed": packet["seed"], "size": packet["size"], "population": packet["population"]}, f"wrote {packet['size']} of {packet['population']} items to {args.out} (seed {packet['seed']})")
        if args.command == "record-audit":
            summary = record_audit(args.directory, args.from_file, args.route)
            human = (
                f"recorded {summary['items']} item(s): {summary['excerpt_problems']}/{summary['excerpts_judged']} excerpt problem(s), "
                f"{summary['prose_problems']}/{summary['prose_judged']} prose problem(s), {summary['undispositioned']} awaiting disposition"
            )
            return emit(args, True, summary, human)
        if args.command == "due":
            rows = due_rows(args.as_of or utc_now())
            human = "\n".join(f"{r['report']} {r['hypothesis']} (due {r['resolve_by']}, central {r['central']}): {r['statement']}" for r in rows) or "no hypotheses due"
            return emit(args, True, {"hypotheses": rows}, human)
        if args.command == "reader":
            content = reader_text(args.directory)
            if args.out:
                write_text_atomic(args.out, content)
                return emit(args, True, {"path": str(args.out)}, f"wrote {args.out}")
            if args.json:
                return emit(args, True, {"markdown": content}, "")
            print(content, end="")
            return 0
        if args.command == "supersede":
            successor = supersede_report(args.predecessor, args.slug, args.title, args.cutoff, args.mode, args.domain)
            return emit(args, True, {"successor": str(successor)}, str(successor))
        if args.command == "resolve":
            resolve_hypothesis(args.directory, args.hypothesis_id, args.outcome, args.resolved_at, args.status)
            return emit(args, True, {"hypothesis": args.hypothesis_id, "status": args.status}, f"{args.status}: {args.hypothesis_id}")
        if args.command == "calibration":
            rows = calibration_rows()
            if args.json:
                return emit(args, True, {"hypotheses": rows}, "")
            print(calibration_text(rows), end="")
            return 0
        if args.command == "index":
            path = REPORTS / "index.md"
            expected = index_text()
            if args.check:
                errors = orphan_report_errors()
                if not errors and not path.is_file():
                    errors = ["reports/index.md is missing; run reportctl.py index"]
                elif not errors and path.read_text(encoding="utf-8") != expected:
                    errors = ["reports/index.md is stale; run reportctl.py index"]
                return emit(args, not errors, {"path": str(path)}, "OK: reports/index.md", errors=errors)
            write_text_atomic(path, expected)
            return emit(args, True, {"path": str(path)}, f"rewrote {path}")
        if args.command == "scan-sensitive":
            errors = sensitive_content_errors()
            return emit(args, not errors, {}, "OK: no high-confidence sensitive material found", errors=errors)
    except (ValueError, OSError, UnicodeError, TypeError, KeyError, AttributeError) as exc:
        return emit(args, False, {}, "", errors=[f"{type(exc).__name__}: {exc}"])
    except SystemExit as exc:
        # init_report raises SystemExit with a message for user errors.
        message = str(exc.code) if exc.code not in (None, 0) else ""
        if not message:
            raise
        return emit(args, False, {}, "", errors=[message.removeprefix("error: ")])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
