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
    "general", "event-assessment", "technology-landscape", "market-analysis",
    "company-research", "release-forecast", "policy-analysis",
    "scientific-synthesis", "comparative-analysis", "product-landscape",
    "due-diligence",
}


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


def parse_temporal(value: Any) -> datetime | None:
    """Parse an ISO date or datetime; date-only means unknown time."""
    if not text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


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
    """Split sentences while retaining trailing citation groups."""
    return [
        part.strip()
        for part in re.findall(r".*?[.!?](?:\[\d+\])*(?=\s+|$)|.+$", value)
        if part.strip()
    ]


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


def prose_sentences(markdown: str) -> list[str]:
    sentences: list[str] = []
    in_fence = False
    for line in markdown.splitlines():
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
        is_table = stripped.startswith("|")
        if is_table:
            if re.fullmatch(r"[| :\-]+", stripped):
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
    """Return citation units: prose paragraphs, list items, and table rows."""
    units: list[str] = []
    paragraph: list[str] = []
    in_fence = False
    in_frontmatter = False

    def flush() -> None:
        if paragraph:
            units.append(" ".join(paragraph))
            paragraph.clear()

    for line_number, line in enumerate(markdown.splitlines()):
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
        if stripped.startswith("|"):
            flush()
            if not re.fullmatch(r"[| :\-]+", stripped):
                units.append(stripped)
            continue
        if re.match(r"^(?:>|[-*]|\d+[.)])\s+", stripped):
            flush()
            units.append(stripped)
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


def validate_report(directory: Path) -> list[str]:
    errors: list[str] = []
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
        require(errors, cutoff_dt <= created_dt, "report.cutoff must not be after report.created")
    if created_dt and updated_dt:
        require(errors, created_dt <= updated_dt, "report.created must not be after report.updated")
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
                    target_cutoff = parse_temporal(load_json(target_assessment)["report"]["cutoff"])
                except (ValueError, KeyError, TypeError):
                    target_cutoff = None
                require(errors, target_cutoff is not None, f"report.lineage.{key} target has invalid cutoff")
                if target_cutoff and key == "supersedes":
                    require(errors, target_cutoff < cutoff_dt, "a superseded report must have an earlier cutoff")
                if target_cutoff and key == "superseded_by":
                    require(errors, target_cutoff > cutoff_dt, "a successor report must have a later cutoff")
    questions = report.get("questions")
    require(errors, isinstance(questions, list) and bool(questions) and all(text(q) for q in questions), "report.questions must be a non-empty text list")
    if text(report.get("slug")):
        require(errors, directory.name == report["slug"], "report.slug must match the directory name")

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
        require(errors, text(claim.get("rationale")), f"{where}.rationale must be non-empty")
        require(errors, valid_datetime(claim.get("last_checked")), f"{where}.last_checked must be ISO-8601")
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
                require(errors, high_confidence <= 0.95, f"{where} single-group indirect evidence cannot exceed 0.95 confidence")
                require(errors, high_confidence - low_confidence >= 0.15, f"{where} single-group indirect evidence requires a confidence width of at least 0.15")
        if claim_id:
            require(errors, claim_id not in claim_by_id, f"duplicate claim id: {claim_id}")
            claim_by_id[claim_id] = claim

    evidence = assessment.get("evidence")
    require(errors, isinstance(evidence, list), "evidence must be a list")
    if not isinstance(evidence, list):
        evidence = []
    evidence_claims: set[str] = set()
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        where = f"evidence[{index}]"
        require(errors, isinstance(item, dict), f"{where} must be an object")
        if not isinstance(item, dict):
            continue
        raw_evidence_id = item.get("id")
        evidence_id = raw_evidence_id if isinstance(raw_evidence_id, str) else ""
        require(errors, bool(evidence_id) and bool(ID_RE.fullmatch(evidence_id)), f"{where}.id invalid")
        require(errors, evidence_id not in evidence_ids, f"duplicate evidence id: {evidence_id}")
        if evidence_id:
            evidence_ids.add(evidence_id)
        require(errors, item.get("source_id") in source_by_id, f"{where}.source_id is unknown")
        require(errors, text(item.get("excerpt")), f"{where}.excerpt must be non-empty")
        require(errors, len(str(item.get("excerpt", ""))) <= 1000, f"{where}.excerpt exceeds 1000 characters")
        require(errors, text(item.get("location")), f"{where}.location must be non-empty")
        require(errors, valid_datetime(item.get("captured_at")), f"{where}.captured_at must be ISO-8601")
        supports = item.get("supports_claim_ids")
        require(errors, isinstance(supports, list) and bool(supports), f"{where}.supports_claim_ids must be non-empty")
        if isinstance(supports, list):
            for claim_id in supports:
                require(errors, claim_id in claim_by_id, f"{where} references unknown claim {claim_id}")
                evidence_claims.add(claim_id)
                if claim_id in claim_by_id:
                    require(errors, item.get("source_id") in claim_by_id[claim_id].get("source_ids", []), f"{where}.source_id must be listed by supported claim {claim_id}")
    for claim_id, claim in claim_by_id.items():
        if claim.get("importance") == "load-bearing" and claim.get("kind") in {"fact", "attributed"}:
            require(errors, claim_id in evidence_claims, f"load-bearing claim {claim_id} requires a short evidence excerpt")

    hypotheses = assessment.get("hypotheses")
    require(errors, isinstance(hypotheses, list), "hypotheses must be a list")
    if not isinstance(hypotheses, list):
        hypotheses = []
    has_forecast_claim = any(claim.get("kind") == "forecast" for claim in claims if isinstance(claim, dict))
    if report.get("mode") == "release-forecast" or has_forecast_claim:
        require(errors, bool(hypotheses), "release forecasts and forecast claims require at least one hypothesis")
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
            for claim_id in basis:
                require(errors, claim_id in claim_by_id, f"{where} references unknown claim {claim_id}")
        alternatives = hypothesis.get("alternatives")
        require(errors, isinstance(alternatives, list), f"{where}.alternatives must be a list")
        triggers = hypothesis.get("update_triggers")
        require(errors, isinstance(triggers, list) and bool(triggers) and all(text(t) for t in triggers), f"{where}.update_triggers must be non-empty text")
        require(errors, text(hypothesis.get("rationale")), f"{where}.rationale must be non-empty")
        resolution = hypothesis.get("resolution")
        require(errors, isinstance(resolution, dict), f"{where}.resolution must be an object")
        if isinstance(resolution, dict):
            require(errors, resolution.get("status") in {"open", "resolved", "superseded"}, f"{where}.resolution.status invalid")
            if resolution.get("status") == "resolved":
                require(errors, text(resolution.get("outcome")), f"{where} resolved hypothesis requires an outcome")
                require(errors, parse_temporal(resolution.get("resolved_at")) is not None, f"{where} resolved hypothesis requires resolved_at")
            else:
                require(errors, resolution.get("resolved_at") is None, f"{where} unresolved hypothesis resolved_at must be null")

    gaps = assessment.get("coverage_gaps")
    require(errors, isinstance(gaps, list), "coverage_gaps must be a list")
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
    require(errors, coverage >= 0.45, f"paragraph/table citation coverage {coverage:.0%} is below 45% ({len(covered)}/{len(units)})")
    over_cited = [sentence for sentence in sentences if len(CITE_RE.findall(sentence)) > 3]
    require(errors, not over_cited, f"{len(over_cited)} sentence(s) carry more than three citations")

    cutoff = str(report.get("cutoff", ""))
    require(errors, cutoff in markdown, "report.md must display the exact report cutoff")
    require(errors, "assessment.json" in markdown, "report.md must link to assessment.json")
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", markdown, re.DOTALL)
    require(errors, frontmatter_match is not None, "report.md must start with frontmatter")
    if frontmatter_match:
        fields = dict(re.findall(r"^([a-z_]+):\s*(.+)$", frontmatter_match.group(1), re.MULTILINE))
        for key in ("slug", "mode", "domain", "cutoff", "status"):
            require(errors, fields.get(key) == str(report.get(key, "")), f"report.md frontmatter {key} differs from assessment.json")
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
    for source in sources:
        if source.get("url") == url:
            source["accessed"] = accessed
            ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return int(source["id"])
    source_id = max((int(source["id"]) for source in sources), default=0) + 1
    sources.append({"id": source_id, "url": url, "title": title, "accessed": accessed})
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return source_id


def add_quote(directory: Path, source_id: int, quote: str, evidence_file: Path) -> None:
    evidence = evidence_file.read_text(encoding="utf-8")

    def normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    if normalize(quote) not in normalize(evidence):
        raise ValueError("quote was not found verbatim in the evidence file")
    ledger_path = directory / "sources-ledger.json"
    ledger = load_json(ledger_path)
    source = next((item for item in ledger.get("sources", []) if item.get("id") == source_id), None)
    if source is None:
        raise ValueError(f"unknown source id: {source_id}")
    quotes = source.setdefault("quotes", [])
    if not any(normalize(item.get("text", "")) == normalize(quote) for item in quotes):
        quotes.append({"text": quote, "added": datetime.now(timezone.utc).date().isoformat()})
        ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
            "summary": "Replace with the decision-grade verdict.",
            "questions": ["Replace with the first research question."],
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
    (directory / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n", encoding="utf-8")
    (directory / "sources-ledger.json").write_text('{\n  "version": 1,\n  "sources": []\n}\n', encoding="utf-8")
    report = f"""---
title: {args.title}
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

## Verdict

Replace with the decision-grade answer.[unverified]

## What is observed

Replace with cited observations.[unverified]

## What is assessed

Replace with explicitly labeled inference.[unverified]

## Competing hypotheses

Replace with calibrated ranges and update triggers.[unverified]

## Gaps and falsifiers

Replace with what is missing and what would change the conclusion.[unverified]

## Sources
"""
    (directory / "report.md").write_text(report, encoding="utf-8")
    return directory


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


def sensitive_content_errors() -> list[str]:
    errors: list[str] = []
    forbidden_names = {".env", "auth.json", "credentials.json", "id_rsa", "id_ed25519"}
    patterns = {
        "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
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
        for label, pattern in patterns.items():
            if pattern.search(content):
                errors.append(f"possible {label} in {path.relative_to(ROOT)}")
    return errors


def main() -> int:
    global ROOT, REPORTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root containing reports/ (default: framework checkout)")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create a report skeleton")
    init.add_argument("--slug", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--cutoff", required=True)
    init.add_argument("--mode", choices=sorted(RESEARCH_MODES), default="general")
    init.add_argument("--domain", default="general")
    validate = sub.add_parser("validate", help="validate one report directory")
    validate.add_argument("directory", type=Path)
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
    index = sub.add_parser("index", help="regenerate reports/index.md")
    index.add_argument("--check", action="store_true")
    sub.add_parser("scan-sensitive", help="scan repository text for high-confidence secret material")
    args = parser.parse_args()
    ROOT = args.root.resolve()
    REPORTS = ROOT / "reports"

    if args.command == "init":
        print(init_report(args))
        return 0
    if args.command == "validate":
        errors = validate_report(args.directory)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"OK: {args.directory}")
        return 0
    if args.command == "render-sources":
        render_sources(args.directory)
        print(f"rewrote {args.directory / 'report.md'}")
        return 0
    if args.command == "add-source":
        try:
            source_id = add_source(args.directory, args.url, args.title, args.accessed)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(source_id)
        return 0
    if args.command == "add-quote":
        try:
            add_quote(args.directory, args.source_id, args.text, args.from_file)
        except (ValueError, OSError, UnicodeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"attached quote to source {args.source_id}")
        return 0
    if args.command == "index":
        path = REPORTS / "index.md"
        expected = index_text()
        if args.check:
            orphan_errors = orphan_report_errors()
            if orphan_errors:
                for error in orphan_errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            if not path.is_file():
                print("ERROR: reports/index.md is missing; run reportctl.py index", file=sys.stderr)
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("ERROR: reports/index.md is stale; run reportctl.py index", file=sys.stderr)
                return 1
            print("OK: reports/index.md")
            return 0
        path.write_text(expected, encoding="utf-8")
        print(f"rewrote {path}")
        return 0
    if args.command == "scan-sensitive":
        errors = sensitive_content_errors()
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("OK: no high-confidence sensitive material found")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
