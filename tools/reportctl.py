#!/usr/bin/env python3
"""Initialize, validate, and index truth-assessment reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def prose_sentences(markdown: str) -> list[str]:
    sentences: list[str] = []
    in_fence = False
    lines = markdown.splitlines()
    rows = table_rows(lines)
    headers = table_header_indexes(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if (
            in_fence
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
    in_fence = False
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
        if stripped.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
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


def validate_report(directory: Path, warnings: list[str] | None = None) -> list[str]:
    """Validate one report directory.

    Returns hard errors. Advisory findings that will become errors at the next
    minor framework release are appended to ``warnings`` when a list is supplied.
    """
    errors: list[str] = []
    if warnings is None:
        warnings = []
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
    if cutoff_dt and created_dt:
        require(errors, not_after(report.get("cutoff"), report.get("created")), "report.cutoff must not be after report.created")
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
        authors = source.get("authors")
        require(errors, isinstance(authors, list), f"{where}.authors must be a list")
        if isinstance(authors, list):
            for author_index, author in enumerate(authors):
                author_where = f"{where}.authors[{author_index}]"
                require(errors, isinstance(author, dict), f"{author_where} must be an object")
                if isinstance(author, dict):
                    require(errors, text(author.get("name")), f"{author_where}.name must be non-empty")
                    for key in ("expertise_evidence", "track_record_evidence", "conflicts"):
                        require(errors, key in author, f"{author_where}.{key} is required (use 'unknown' when not researched)")
                    expertise_url = author.get("expertise_url")
                    require(errors, expertise_url is None or valid_url(expertise_url), f"{author_where}.expertise_url must be null or http(s)")
        reliability = source.get("reliability")
        require(errors, isinstance(reliability, dict), f"{where}.reliability must be an object")
        if isinstance(reliability, dict):
            for key in ("publisher_history", "author_expertise", "author_track_record", "transparency"):
                require(errors, reliability.get(key) in RATINGS, f"{where}.reliability.{key} invalid")
            require(errors, text(reliability.get("notes")), f"{where}.reliability.notes must explain the rating")
            if not authors:
                require(errors, reliability.get("author_expertise") == "unknown", f"{where} has no authors, so author_expertise must be unknown")
                require(errors, reliability.get("author_track_record") == "unknown", f"{where} has no authors, so author_track_record must be unknown")
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
        require(errors, isinstance(item.get("source_id"), int) and item.get("source_id") in source_by_id, f"{where}.source_id is unknown")
        require(errors, text(item.get("excerpt")), f"{where}.excerpt must be non-empty")
        require(errors, len(str(item.get("excerpt", ""))) <= 1000, f"{where}.excerpt exceeds 1000 characters")
        require(errors, text(item.get("location")), f"{where}.location must be non-empty")
        require(errors, valid_datetime(item.get("captured_at")), f"{where}.captured_at must be ISO-8601")
        if cutoff_dt:
            require(errors, not_after(item.get("captured_at"), report.get("cutoff")), f"{where}.captured_at is after the report cutoff")
        kind = item.get("kind", "excerpt")
        require(errors, kind in EVIDENCE_KINDS, f"{where}.kind must be one of {sorted(EVIDENCE_KINDS)}")
        if kind == "excerpt" and item.get("source_id") in ledger_by_id and text(item.get("excerpt")):
            ledger_quotes = {normalize_whitespace(str(q.get("text", ""))) for q in ledger_by_id[item["source_id"]].get("quotes", []) if isinstance(q, dict)}
            verified = normalize_whitespace(str(item["excerpt"])) in ledger_quotes
            if not verified:
                warnings.append(f"{where}.excerpt has no matching ledger quote for source {item['source_id']}; record it with `add-evidence` or `add-quote --from-file`, or set kind to 'artifact' for non-text evidence")
        supports = item.get("supports_claim_ids")
        require(errors, isinstance(supports, list) and bool(supports), f"{where}.supports_claim_ids must be non-empty")
        if isinstance(supports, list):
            require(errors, all(isinstance(c, str) for c in supports), f"{where}.supports_claim_ids entries must be claim id strings")
            supports = [c for c in supports if isinstance(c, str)]
            evidence_source = source_by_id.get(item.get("source_id")) if isinstance(item.get("source_id"), int) else None
            for claim_id in supports:
                require(errors, claim_id in claim_by_id, f"{where} references unknown claim {claim_id}")
                evidence_claims.add(claim_id)
                if claim_id in claim_by_id:
                    claim_sources = claim_by_id[claim_id].get("source_ids")
                    require(errors, isinstance(claim_sources, list) and item.get("source_id") in claim_sources, f"{where}.source_id must be listed by supported claim {claim_id}")
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
    return errors


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
    markdown_path.write_text(body.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


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


def record_quote(ledger: Any, source_id: int, quote: str) -> bool:
    """Append ``quote`` to the ledger source in memory; return True when it was new."""
    source = ledger_source(ledger, source_id)
    quotes = source.get("quotes")
    if quotes is None:
        quotes = []
        source["quotes"] = quotes
    if not isinstance(quotes, list) or not all(isinstance(item, dict) for item in quotes):
        raise ValueError(f"source {source_id} has a malformed quotes list; repair sources-ledger.json first")
    if any(isinstance(item, dict) and normalize_whitespace(str(item.get("text", ""))) == normalize_whitespace(quote) for item in quotes):
        return False
    quotes.append({"text": quote, "added": datetime.now(timezone.utc).date().isoformat()})
    return True


def add_quote(directory: Path, source_id: int, quote: str, evidence_file: Path) -> None:
    """Verify ``quote`` against ``evidence_file`` and record it in the ledger.

    The check attests that the quotation matches the caller-supplied text
    file; it does not and cannot prove the file was fetched from the
    registered URL. Keep fetched text under the report's ``evidence/``
    directory so that provenance stays inspectable.
    """
    verify_quote(quote, evidence_file)
    ledger_path = directory / "sources-ledger.json"
    ledger = load_json(ledger_path)
    if record_quote(ledger, source_id, quote):
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
    evidence_file: Path,
    claim_ids: list[str],
    location: str,
    captured_at: str,
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
    verify_quote(quote, evidence_file)

    assessment_path = directory / "assessment.json"
    ledger_path = directory / "sources-ledger.json"
    assessment = load_json(assessment_path)
    ledger = load_json(ledger_path)
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

    if record_quote(ledger, source_id, quote):
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
    import shutil

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
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
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
    add_quote_parser.add_argument("--from-file", required=True, type=Path)
    add_evidence_parser = sub.add_parser("add-evidence", help="verify a quotation and attach it to claims in one step")
    add_evidence_parser.add_argument("directory", type=Path)
    add_evidence_parser.add_argument("source_id", type=int)
    add_evidence_parser.add_argument("--text", required=True)
    add_evidence_parser.add_argument("--from-file", required=True, type=Path)
    add_evidence_parser.add_argument("--claim", action="append", required=True, dest="claims", metavar="CLAIM_ID")
    add_evidence_parser.add_argument("--location", required=True)
    add_evidence_parser.add_argument("--captured-at", required=True)
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
            errors = validate_report(args.directory, warnings)
            if args.strict:
                errors = errors + [f"strict: {warning}" for warning in warnings]
                warnings = []
            if not args.json:
                for warning in warnings:
                    print(f"WARNING: {warning}", file=sys.stderr)
            suffix = f" ({len(warnings)} warning(s))" if warnings else ""
            return emit(args, not errors, {"directory": str(args.directory), "warnings": warnings}, f"OK: {args.directory}{suffix}", errors=errors)
        if args.command == "render-sources":
            render_sources(args.directory)
            return emit(args, True, {"directory": str(args.directory)}, f"rewrote {args.directory / 'report.md'}")
        if args.command == "add-source":
            source_id = add_source(args.directory, args.url, args.title, args.accessed)
            return emit(args, True, {"source_id": source_id}, str(source_id))
        if args.command == "add-quote":
            add_quote(args.directory, args.source_id, args.text, args.from_file)
            return emit(args, True, {"source_id": args.source_id}, f"attached quote to source {args.source_id}")
        if args.command == "add-evidence":
            evidence_id = add_evidence(args.directory, args.source_id, args.text, args.from_file, args.claims, args.location, args.captured_at)
            return emit(args, True, {"evidence_id": evidence_id, "source_id": args.source_id}, evidence_id)
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
            path.write_text(expected, encoding="utf-8")
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
