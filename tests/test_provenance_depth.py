"""Snapshot provenance, claim anchors, research-depth, calibration and audit rules."""

from __future__ import annotations

import functools
import http.server
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reportctl", ROOT / "tools" / "reportctl.py")
assert SPEC and SPEC.loader
reportctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reportctl)
snapshots = reportctl.snapshots

FIXTURE = ROOT / "tests" / "fixtures" / "minimal-report"
PAGE = """<!doctype html><html><head><title>Agency record</title><style>.x{color:red}</style>
<script>var tracking = "The event was cancelled.";</script></head>
<body><nav>Home | About</nav><main><h1>Agency record</h1>
<p>The agency confirmed that the inspection took place on 4 June 2026 and that three deficiencies were recorded.</p>
<p>The facility disputed one deficiency. The agency's final report lists all three findings and the corrective actions requested,
with a follow-up visit scheduled within ninety days of the inspection.</p></main></body></html>"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.report = self.root / "reports" / "2026" / "08" / "minimal-report"
        shutil.copytree(FIXTURE, self.report)
        patches = [
            mock.patch.object(reportctl, "ROOT", self.root),
            mock.patch.object(reportctl, "REPORTS", self.root / "reports"),
            mock.patch.dict("os.environ", {"DEEP_RESEARCH_SNAPSHOTS": str(self.root / ".snapshots")}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self._tmp.cleanup)

    def assessment(self) -> dict:
        return json.loads((self.report / "assessment.json").read_text())

    def save(self, assessment: dict) -> None:
        (self.report / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")

    def ledger(self) -> dict:
        return json.loads((self.report / "sources-ledger.json").read_text())

    def markdown(self, old: str, new: str) -> None:
        path = self.report / "report.md"
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def validate(self, **kwargs: object) -> tuple[list[str], list[str]]:
        warnings: list[str] = []
        errors = reportctl.validate_report(self.report, warnings, **kwargs)
        return errors, warnings

    def assertClean(self) -> None:
        errors, warnings = self.validate()
        self.assertEqual([], errors)
        self.assertEqual([], warnings)


class SnapshotProvenanceTests(Base):
    def serve(self) -> str:
        site = self.root / "site"
        site.mkdir()
        (site / "record.html").write_text(PAGE)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(site)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}/record.html"

    def test_html_extraction_drops_scripts_styles_and_keeps_block_breaks(self) -> None:
        text = snapshots.html_to_text(PAGE)
        self.assertIn("three deficiencies were recorded.", text)
        self.assertNotIn("tracking", text)
        self.assertNotIn("color:red", text)
        self.assertIn("Agency record\n", text)

    def test_fetch_binds_quotes_to_hashed_text_and_validates_strictly(self) -> None:
        url = self.serve()
        with mock.patch.object(reportctl, "utc_now", return_value="2026-08-31T10:30:00Z"), mock.patch.object(snapshots, "datetime") as clock:
            clock.now.return_value.replace.return_value.isoformat.return_value = "2026-08-31T10:30:00+00:00"
            source_id, digest = reportctl.fetch_source(self.report, url, "Agency record", "vault")
        self.assertEqual(2, source_id)
        stored = self.root / ".snapshots" / f"{digest}.txt"
        self.assertTrue(stored.is_file())
        self.assertEqual(digest, snapshots.sha256_text(stored.read_text()))
        record = self.ledger()["sources"][1]["snapshots"][0]
        self.assertEqual("fetch", record["method"])
        self.assertEqual(200, record["status"])
        self.assertIn("raw_sha256", record)

        assessment = self.assessment()
        second = dict(assessment["sources"][0], id=2, url=url, title="Agency record", disposition="cited")
        assessment["sources"].append(second)
        assessment["claims"][0]["source_ids"] = [1, 2]
        self.save(assessment)
        quote = "three deficiencies were recorded."
        reportctl.add_evidence(self.report, 2, quote, None, ["C1"], "main paragraph 1", "2026-08-31T10:30:00Z", snapshot=digest[:10])
        bound = self.ledger()["sources"][1]["quotes"][0]
        self.assertEqual(digest, bound["snapshot"])
        self.assertGreaterEqual(bound["offset"], 0)
        self.markdown("That absence keeps confidence below certainty.[1]", "That absence keeps confidence below certainty.[1][2]")
        reportctl.render_sources(self.report)
        notes: list[str] = []
        warnings: list[str] = []
        self.assertEqual([], reportctl.validate_report(self.report, warnings, notes=notes, verify_snapshots=True))
        self.assertEqual([], warnings)
        self.assertTrue(any("re-verified" in note for note in notes))

    def test_quote_absent_from_snapshot_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "not found verbatim in snapshot"):
            reportctl.add_evidence(self.report, 1, "The event was cancelled.", None, ["C1"], "body", "2026-08-31T10:00:00Z", snapshot="latest")

    def test_tampered_snapshot_is_an_error(self) -> None:
        stored = next((self.report / "evidence" / "snapshots").glob("*.txt"))
        stored.write_text(stored.read_text().replace("occurred", "was cancelled"))
        errors, _ = self.validate()
        self.assertTrue(any("[P3]" in error and "no longer matches its hash" in error for error in errors), errors)

    def test_quote_drift_against_intact_snapshot_is_an_error(self) -> None:
        ledger = self.ledger()
        ledger["sources"][0]["quotes"][0]["text"] = "The event was cancelled."
        (self.report / "sources-ledger.json").write_text(json.dumps(ledger))
        errors, _ = self.validate()
        self.assertTrue(any("[P3]" in error and "not present in snapshot" in error for error in errors), errors)

    def test_binding_to_unrecorded_snapshot_is_an_error(self) -> None:
        ledger = self.ledger()
        ledger["sources"][0]["quotes"][0]["snapshot"] = "0" * 64
        (self.report / "sources-ledger.json").write_text(json.dumps(ledger))
        errors, _ = self.validate()
        self.assertTrue(any("[P2]" in error for error in errors), errors)

    def test_missing_snapshot_is_a_note_unless_verification_is_required(self) -> None:
        shutil.rmtree(self.report / "evidence" / "snapshots")
        notes: list[str] = []
        errors = reportctl.validate_report(self.report, [], notes=notes)
        self.assertEqual([], errors)
        self.assertTrue(any("not present in this checkout" in note for note in notes))
        errors = reportctl.validate_report(self.report, [], verify_snapshots=True)
        self.assertTrue(any("[P4]" in error for error in errors), errors)

    def test_fabricated_file_quote_no_longer_passes_strict(self) -> None:
        """Regression for the review probe: a quote verified only against a file the analyst wrote."""
        fabricated = self.root / "fabricated.txt"
        fabricated.write_text("Officials said the event occurred on Tuesday.\n")
        reportctl.add_evidence(self.report, 1, "Officials said the event occurred", fabricated, ["C1"], "body", "2026-08-31T10:00:00Z")
        quote = self.ledger()["sources"][0]["quotes"][-1]
        self.assertIn("file_sha256", quote)
        self.assertNotIn("snapshot", quote)
        errors, warnings = self.validate()
        self.assertEqual([], errors)
        self.assertTrue(any(warning.startswith("[P1]") for warning in warnings), warnings)
        strict = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "reportctl.py"), "--root", str(self.root), "validate", "--strict", str(self.report)],
            text=True, capture_output=True, env={"DEEP_RESEARCH_SNAPSHOTS": str(self.root / ".snapshots"), "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(1, strict.returncode)
        self.assertIn("[P1]", strict.stderr)

    def test_capture_binds_legacy_quote_to_snapshot(self) -> None:
        ledger = self.ledger()
        ledger["sources"][0]["quotes"] = [{"text": "The event occurred.", "added": "2026-08-31"}]
        (self.report / "sources-ledger.json").write_text(json.dumps(ledger))
        _, warnings = self.validate()
        self.assertTrue(any("[P1]" in warning for warning in warnings))
        captured = self.root / "capture.txt"
        captured.write_text("Browser render.\nThe event occurred. Later text.\n")
        _, digest = reportctl.capture_source(self.report, "https://example.com/source", None, captured, "2026-08-31T10:40:00Z", "browser render", "vault")
        reportctl.add_quote(self.report, 1, "The event occurred.", snapshot=digest)
        self.assertEqual(digest, self.ledger()["sources"][0]["quotes"][0]["snapshot"])
        self.assertClean()

    def test_retrieval_after_cutoff_is_refused(self) -> None:
        captured = self.root / "capture.txt"
        captured.write_text("Text\n")
        with self.assertRaisesRegex(ValueError, "after the report cutoff"):
            reportctl.capture_source(self.report, "https://example.com/source", None, captured, "2027-01-01T00:00:00Z", None, "vault")

    def test_add_evidence_requires_exactly_one_origin(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            reportctl.add_evidence(self.report, 1, "The event occurred.", None, ["C1"], "body", "2026-08-31T10:00:00Z")


class AnchorTests(Base):
    def test_fixture_is_anchored_and_clean(self) -> None:
        self.assertClean()

    def test_unknown_anchor_is_an_error(self) -> None:
        self.markdown("[1]{C1}", "[1]{C9}")
        errors, _ = self.validate()
        self.assertTrue(any("[A1]" in error for error in errors), errors)

    def test_anchored_passage_cannot_cite_a_foreign_source(self) -> None:
        reportctl.add_source(self.report, "https://example.org/other", "Other", "2026-08-31")
        assessment = self.assessment()
        assessment["sources"].append(dict(assessment["sources"][0], id=2, url="https://example.org/other", title="Other"))
        self.save(assessment)
        self.markdown("occurred.[1]{C1}", "occurred.[1][2]{C1}")
        reportctl.render_sources(self.report)
        errors, _ = self.validate()
        self.assertTrue(any("[A2]" in error and "[2]" in error for error in errors), errors)

    def test_anchored_fact_must_cite_its_own_support(self) -> None:
        self.markdown("The directly inspected record says the event occurred.[1]{C1}", "The directly inspected record says the event occurred.{C1}")
        errors, _ = self.validate()
        self.assertTrue(any("[A2]" in error and "supporting sources" in error for error in errors), errors)

    def test_unanchored_load_bearing_claim_is_a_warning(self) -> None:
        self.markdown("[1]{C1}", "[1]")
        errors, warnings = self.validate()
        self.assertEqual([], errors)
        self.assertTrue(any("[A3]" in warning and "C1" in warning for warning in warnings), warnings)

    def test_inverted_prose_is_surfaced_for_audit_even_when_citations_line_up(self) -> None:
        """Deterministic checks cannot judge meaning; the audit packet must put the contradiction in front of a reviewer."""
        self.markdown("The directly inspected record says the event occurred.[1]{C1}", "The record proves the event did NOT occur.[1]{C1}")
        errors, _ = self.validate()
        self.assertEqual([], errors)
        packet = reportctl.audit_sample(self.report, 5, seed=7)
        item = next(entry for entry in packet["items"] if entry["claim_id"] == "C1")
        self.assertEqual("The event occurred.", item["claim"])
        self.assertTrue(any("did NOT occur" in passage for passage in item["report_passages"]))
        self.assertIn("The event occurred.", item["snapshot_context"])

    def test_reader_output_strips_anchors_and_citation_checks_ignore_them(self) -> None:
        reader = reportctl.reader_text(self.report)
        self.assertNotIn("{C1}", reader)
        self.assertIn("event occurred.[1]\n", reader)
        self.assertTrue(reportctl.citation_scope_valid(reportctl.strip_anchors("A sentence long enough here.[1]{C1}")))


class DepthTests(Base):
    def test_missing_search_log_is_a_warning(self) -> None:
        assessment = self.assessment()
        assessment["searches"] = []
        assessment["claims"][0].pop("counter_search_ids")
        assessment["hypotheses"][0].pop("counter_search_ids")
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any(warning.startswith("[D1] no search log") for warning in warnings), warnings)

    def test_log_search_validates_and_records(self) -> None:
        search_id = reportctl.log_search(self.report, "event audit", "example-search", "support", 1, [1], 4, "note", "2026-08-31T10:00:00Z")
        self.assertEqual("S3", search_id)
        self.assertClean()
        with self.assertRaisesRegex(ValueError, "--question"):
            reportctl.log_search(self.report, "q", "e", "support", 2, [], None, None, "2026-08-31T10:00:00Z")
        with self.assertRaisesRegex(ValueError, "after the report cutoff"):
            reportctl.log_search(self.report, "q", "e", "support", 1, [], None, None, "2027-01-01T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "no assessment.json sources entry"):
            reportctl.log_search(self.report, "q", "e", "support", 1, [9], None, None, "2026-08-31T10:00:00Z")

    def test_unsearched_question_is_a_warning(self) -> None:
        assessment = self.assessment()
        assessment["report"]["questions"].append("Who organized it?")
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("question(s) 2 have no logged search" in warning for warning in warnings), warnings)

    def test_load_bearing_inference_needs_sought_counter_evidence(self) -> None:
        assessment = self.assessment()
        claim = dict(assessment["claims"][0], id="C2", kind="inference", statement="The organizer would not misreport it.", counter_search_ids=[])
        assessment["claims"].append(claim)
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[D2]" in warning and "C2" in warning for warning in warnings), warnings)
        claim["counter_search_ids"] = ["S1"]  # S1 is a primary search, not a counter search
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[D2]" in warning and "C2" in warning for warning in warnings), warnings)
        claim["counter_search_ids"] = ["S2"]
        self.save(assessment)
        _, warnings = self.validate()
        self.assertFalse(any("[D2]" in warning for warning in warnings), warnings)
        claim["counter_search_ids"] = ["S9"]
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("unknown searches" in error for error in errors), errors)

    def test_searched_gap_kinds_need_search_ids(self) -> None:
        assessment = self.assessment()
        assessment["coverage_gaps"] = [{"kind": "missing-primary", "description": "No attendance data.", "claim_ids": ["C1"]}]
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[D3]" in warning for warning in warnings), warnings)
        assessment["coverage_gaps"][0]["search_ids"] = ["S2"]
        self.save(assessment)
        _, warnings = self.validate()
        self.assertFalse(any("[D3]" in warning for warning in warnings), warnings)
        assessment["coverage_gaps"][0]["search_ids"] = ["S7"]
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("[D3]" in error for error in errors), errors)

    def test_uncited_sources_need_a_disposition(self) -> None:
        reportctl.add_source(self.report, "https://example.org/unused", "Unused", "2026-08-31")
        assessment = self.assessment()
        extra = {k: v for k, v in assessment["sources"][0].items() if k != "disposition"}
        extra.update(id=2, url="https://example.org/unused", title="Unused")
        assessment["sources"].append(extra)
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[D4]" in warning and "(2)" in warning for warning in warnings), warnings)
        extra["disposition"] = "superseded-by-better-source"
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("disposition_note" in error for error in errors), errors)
        extra["disposition_note"] = "Source 1 is the primary record this article summarizes."
        self.save(assessment)
        self.assertClean()
        extra["disposition"] = "cited"
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("does not cite it" in error for error in errors), errors)

    def test_secondary_only_load_bearing_claim_is_flagged_unless_gap_recorded(self) -> None:
        assessment = self.assessment()
        assessment["sources"][0].update(directness="secondary")
        assessment["claims"][0]["status"] = "probable"
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[D5]" in warning for warning in warnings), warnings)
        assessment["coverage_gaps"] = [{"kind": "missing-primary", "description": "Organizer record unavailable.", "claim_ids": ["C1"], "search_ids": ["S1"]}]
        self.save(assessment)
        _, warnings = self.validate()
        self.assertFalse(any("[D5]" in warning for warning in warnings), warnings)

    def test_attributed_claims_separate_attribution_from_truth(self) -> None:
        assessment = self.assessment()
        assessment["claims"][0]["kind"] = "attributed"
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[D6]" in warning for warning in warnings), warnings)
        assessment["claims"][0]["underlying_status"] = "true"
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("[D6]" in error for error in errors), errors)
        assessment["claims"][0]["underlying_status"] = "probable"
        self.save(assessment)
        self.assertClean()

    def test_author_list_is_optional(self) -> None:
        assessment = self.assessment()
        assessment["sources"][0].pop("authors", None)
        assessment["sources"][0]["reliability"].pop("author_expertise", None)
        assessment["sources"][0]["reliability"].pop("author_track_record", None)
        self.save(assessment)
        self.assertClean()


class CalibrationAndAuditTests(Base):
    def test_open_hypothesis_needs_resolution_date_or_reason(self) -> None:
        assessment = self.assessment()
        assessment["hypotheses"][0].pop("unresolvable_reason")
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[C1]" in warning for warning in warnings), warnings)
        assessment["hypotheses"][0]["resolve_by"] = "2026-01-01"
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("must not precede the report cutoff" in error for error in errors), errors)
        assessment["hypotheses"][0]["resolve_by"] = "2026-12-31"
        self.save(assessment)
        self.assertClean()
        self.assertEqual([], reportctl.due_rows("2026-12-30"))
        due = reportctl.due_rows("2027-01-02")
        self.assertEqual(["H1"], [row["hypothesis"] for row in due])

    def test_audit_round_trip_requires_dispositions_for_problems(self) -> None:
        packet = reportctl.audit_sample(self.report, 3, seed=11)
        self.assertEqual(11, packet["seed"])
        self.assertEqual(packet, reportctl.audit_sample(self.report, 3, seed=11))
        packet["items"][0].update(excerpt_verdict="partial", prose_verdict="overstates", note="Prose says 'directly inspected'.")
        verdicts = self.root / "verdicts.json"
        verdicts.write_text(json.dumps(packet))
        summary = reportctl.record_audit(self.report, verdicts, "test reviewer")
        self.assertEqual(1, summary["excerpt_problems"])
        self.assertEqual(1, summary["undispositioned"])
        errors, _ = self.validate()
        self.assertTrue(any("[R1]" in error and "disposition" in error for error in errors), errors)
        assessment = self.assessment()
        assessment["review"]["entailment_audit"]["items"][0]["disposition"] = "Narrowed the sentence to what the record states."
        self.save(assessment)
        self.assertClean()

    def test_unjudged_audit_items_are_refused(self) -> None:
        packet = reportctl.audit_sample(self.report, 2, seed=3)
        verdicts = self.root / "verdicts.json"
        verdicts.write_text(json.dumps(packet))
        with self.assertRaisesRegex(ValueError, "no verdict"):
            reportctl.record_audit(self.report, verdicts, "reviewer")

    def test_reviewed_report_needs_audit_and_web_coverage_review(self) -> None:
        assessment = self.assessment()
        assessment["report"]["status"] = "reviewed"
        assessment["review"].update(independent_review="passed", exact_revision="abc", route="r", findings_disposition=[], rereview_required=False)
        self.save(assessment)
        self.markdown("status: draft", "status: reviewed")
        _, warnings = self.validate()
        self.assertTrue(any(warning.startswith("[R1]") for warning in warnings), warnings)
        self.assertTrue(any(warning.startswith("[R2]") for warning in warnings), warnings)
        assessment["review"]["coverage_review"] = {"route": "reviewer with search", "web_access": True, "missing_evidence": ["Organizer's attendance filing"], "disposition": "Searched; no filing exists (S2)."}
        assessment["review"]["entailment_audit"] = {"route": "r", "audited_at": "2026-09-01T00:00:00Z", "items": [{"claim_id": "C1", "evidence_id": "E1", "excerpt_verdict": "supports", "prose_verdict": "faithful"}]}
        self.save(assessment)
        self.assertClean()


class ReviewFindingRegressionTests(Base):
    """Regressions for the independent review of f3e77f0."""

    def legacy(self) -> Path:
        target = self.root / "reports" / "2026" / "08" / "legacy-v0-2-1-report"
        shutil.copytree(ROOT / "tests" / "fixtures" / "legacy-v0-2-1-report", target)
        return target

    def test_pre_030_report_still_passes_default_validate_with_brace_text(self) -> None:
        target = self.legacy()
        path = target / "report.md"
        path.write_text(path.read_text().replace(
            "Independent corroboration has not yet been located.[1]",
            "Independent corroboration of the `{JSON}` record or the {API} feed has not yet been located.[1]",
        ))
        warnings: list[str] = []
        self.assertEqual([], reportctl.validate_report(target, warnings))
        self.assertTrue(any(w.startswith("[P1]") for w in warnings))
        self.assertIn("{API}", reportctl.reader_text(target))
        self.assertIn("`{JSON}`", reportctl.reader_text(target))

    def test_citation_adjacent_unknown_anchor_is_still_an_error(self) -> None:
        self.markdown("[1]{C1}", "[1]{C1}{C7}")
        errors, _ = self.validate()
        self.assertTrue(any("[A1]" in e and "C7" in e for e in errors), errors)

    def test_standalone_known_anchor_is_recognized_and_stripped(self) -> None:
        self.markdown("That absence keeps confidence below certainty.[1]", "That absence keeps confidence below certainty {H1}.[1]")
        errors, _ = self.validate()
        self.assertEqual([], errors)
        self.assertIn("That absence keeps confidence below certainty.[1]", reportctl.reader_text(self.report))

    def test_fenced_code_keeps_anchor_like_text(self) -> None:
        path = self.report / "report.md"
        path.write_text(path.read_text().replace("## Uncertainty", "```text\nexample.[1]{C1}\n```\n\n## Uncertainty"))
        self.assertIn("example.[1]{C1}", reportctl.reader_text(self.report))

    def test_hypothesis_anchor_limits_citations_to_basis_sources(self) -> None:
        reportctl.add_source(self.report, "https://example.org/other", "Other", "2026-08-31")
        assessment = self.assessment()
        assessment["sources"].append(dict(assessment["sources"][0], id=2, url="https://example.org/other", title="Other"))
        self.save(assessment)
        self.markdown("That absence keeps confidence below certainty.[1]", "That absence keeps confidence below certainty.[2]{H1}")
        reportctl.render_sources(self.report)
        errors, _ = self.validate()
        self.assertTrue(any("[A2]" in e and "H1" in e for e in errors), errors)

    def test_redirect_to_non_http_scheme_is_refused_before_connecting(self) -> None:
        class Redirect(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header("Location", "ftp://127.0.0.1:1/secret.txt")
                self.end_headers()

            def log_message(self, *args: object) -> None:
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with self.assertRaisesRegex(ValueError, "non-http"):
            snapshots.fetch(f"http://127.0.0.1:{server.server_address[1]}/x")

    def test_private_store_inside_unignored_git_tree_is_refused(self) -> None:
        if not shutil.which("git"):
            self.skipTest("git unavailable")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        captured = self.root / "capture.txt"
        captured.write_text("The event occurred.\n")
        with self.assertRaisesRegex(ValueError, "not ignored"):
            reportctl.capture_source(self.report, "https://example.com/source", None, captured, "2026-08-31T10:40:00Z", None, "vault")
        self.assertFalse((self.root / ".snapshots").exists())
        (self.root / ".gitignore").write_text(".snapshots/\n")
        reportctl.capture_source(self.report, "https://example.com/source", None, captured, "2026-08-31T10:40:00Z", None, "vault")
        self.assertTrue(any((self.root / ".snapshots").glob("*.txt")))

    def test_report_store_commits_text_but_not_raw_bytes(self) -> None:
        captured = self.root / "capture.txt"
        captured.write_text("Public-domain record text.\n")
        _, digest = reportctl.capture_source(self.report, "https://example.gov/record", "Record", captured, "2026-08-31T10:40:00Z", None, "report")
        store = self.report / "evidence" / "snapshots"
        self.assertTrue((store / f"{digest}.txt").is_file())
        self.assertFalse((store / "raw").exists())
        self.assertEqual("report", self.ledger()["sources"][-1]["snapshots"][0]["store"])

    def test_fetch_checks_title_before_touching_the_network(self) -> None:
        with mock.patch.object(snapshots, "fetch", side_effect=AssertionError("network used")):
            with self.assertRaisesRegex(ValueError, "--title is required"):
                reportctl.fetch_source(self.report, "https://example.org/new", None, "vault")

    def test_counter_search_with_nothing_inspected_does_not_count(self) -> None:
        assessment = self.assessment()
        assessment["searches"].append({"id": "S3", "question": 1, "purpose": "counter", "engine": "e", "query": "q", "run_at": "2026-08-31T09:50:00Z", "results_considered": 0, "source_ids": []})
        claim = dict(assessment["claims"][0], id="C2", kind="inference", statement="Inference.", counter_search_ids=["S3"])
        assessment["claims"].append(claim)
        self.save(assessment)
        _, warnings = self.validate()
        self.assertTrue(any("[D2]" in w and "C2" in w for w in warnings), warnings)

    def test_crafted_snapshot_digest_cannot_escape_the_store(self) -> None:
        (self.report / "evidence" / "x.txt").write_text("outside")
        self.assertIsNone(snapshots.find_snapshot(self.root, self.report, "../x"))

    def test_record_audit_refuses_malformed_items(self) -> None:
        verdicts = self.root / "verdicts.json"
        verdicts.write_text(json.dumps({"items": ["not an object"]}))
        with self.assertRaisesRegex(ValueError, "claim_id"):
            reportctl.record_audit(self.report, verdicts, "reviewer")

    def test_search_source_ids_reject_booleans(self) -> None:
        assessment = self.assessment()
        assessment["searches"][0]["source_ids"] = [True]
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("source_ids must reference assessment sources" in e for e in errors), errors)

    def test_cli_reader_and_due(self) -> None:
        env = {"DEEP_RESEARCH_SNAPSHOTS": str(self.root / ".snapshots"), "PATH": "/usr/bin:/bin"}
        tool = str(ROOT / "tools" / "reportctl.py")
        out = self.root / "reader.md"
        subprocess.run([sys.executable, tool, "--root", str(self.root), "reader", str(self.report), "--out", str(out)], check=True, env=env, capture_output=True)
        self.assertNotIn("{C1}", out.read_text())
        assessment = self.assessment()
        assessment["hypotheses"][0]["resolve_by"] = "2026-09-01"
        self.save(assessment)
        due = subprocess.run([sys.executable, tool, "--root", str(self.root), "--json", "due", "--as-of", "2026-10-01"], check=True, env=env, capture_output=True, text=True)
        self.assertEqual(["H1"], [row["hypothesis"] for row in json.loads(due.stdout)["hypotheses"]])


class ReReviewRegressionTests(Base):
    """Regressions for the independent re-review of a184d88."""

    TOKEN = "ghp_" + "A1b2" * 9
    legacy = ReviewFindingRegressionTests.legacy

    def test_scan_sensitive_scans_a_store_set_to_the_repository_itself(self) -> None:
        (self.root / "leak.txt").write_text(f"token {self.TOKEN}\n")
        for store in (self.root, self.root.parent):
            with mock.patch.dict("os.environ", {"DEEP_RESEARCH_SNAPSHOTS": str(store)}):
                errors = reportctl.sensitive_content_errors()
            self.assertTrue(any("leak.txt" in e for e in errors), (store, errors))

    def test_scan_sensitive_skips_only_an_ignored_store(self) -> None:
        if not shutil.which("git"):
            self.skipTest("git unavailable")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        store = self.root / ".snapshots"
        store.mkdir()
        (store / "page.txt").write_text(f"quoted page {self.TOKEN}\n")
        self.assertTrue(any("page.txt" in e for e in reportctl.sensitive_content_errors()))
        (self.root / ".gitignore").write_text(".snapshots/\n")
        self.assertFalse(any("page.txt" in e for e in reportctl.sensitive_content_errors()))

    def test_record_audit_refuses_non_string_ids(self) -> None:
        verdicts = self.root / "verdicts.json"
        for item in ({"claim_id": ["C1"], "excerpt_verdict": "supports"}, {"claim_id": "C1", "evidence_id": {"x": 1}, "excerpt_verdict": "supports"}):
            verdicts.write_text(json.dumps({"items": [item]}))
            with self.assertRaises(ValueError):
                reportctl.record_audit(self.report, verdicts, "reviewer")

    def test_hand_edited_non_string_ids_are_errors_not_exceptions(self) -> None:
        assessment = self.assessment()
        assessment.setdefault("review", {})["entailment_audit"] = {
            "route": "reviewer",
            "audited_at": "2026-08-31T12:00:00Z",
            "items": [{"claim_id": ["C1"], "evidence_id": {"x": 1}, "excerpt_verdict": "supports"}],
        }
        assessment["evidence"][0]["source_id"] = [1]
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("[R1]" in e and "claim_id" in e for e in errors), errors)
        self.assertTrue(any("[R1]" in e and "evidence_id" in e for e in errors), errors)
        self.assertTrue(any("source_id is unknown" in e for e in errors), errors)

    def test_malformed_evidence_ids_and_bool_sources_are_errors_not_exceptions(self) -> None:
        assessment = self.assessment()
        assessment["evidence"][0]["id"] = ["E1"]
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any(".id invalid" in e for e in errors), errors)
        assessment["evidence"][0]["id"] = "E1"
        assessment["evidence"][0]["source_id"] = True
        self.save(assessment)
        errors, _ = self.validate()
        self.assertTrue(any("source_id is unknown" in e for e in errors), errors)

    def test_scan_sensitive_scans_an_in_repository_store_when_git_is_unavailable(self) -> None:
        store = self.root / ".snapshots"
        store.mkdir()
        (store / "page.txt").write_text(f"quoted page {self.TOKEN}\n")
        (self.root / ".gitignore").write_text(".snapshots/\n")
        with mock.patch.object(reportctl.shutil, "which", return_value=None):
            self.assertTrue(any("page.txt" in e for e in reportctl.sensitive_content_errors()))

    def test_tilde_and_longer_backtick_fences_keep_anchor_like_text(self) -> None:
        blocks = "~~~\ntilde.[1]{C1}\n~~~\n\n````md\n```\nnested.[1]{C1}\n```\n````\n\n"
        self.markdown("## Uncertainty", blocks + "## Uncertainty")
        reader = reportctl.reader_text(self.report)
        self.assertIn("tilde.[1]{C1}", reader)
        self.assertIn("nested.[1]{C1}", reader)
        errors, _ = self.validate()
        self.assertEqual([], errors)

    def test_only_citation_groups_and_anchors_make_braces_adjacent(self) -> None:
        target = self.legacy()
        path = target / "report.md"
        path.write_text(path.read_text().replace(
            "Independent corroboration has not yet been located.[1]",
            "Independent corroboration of the [alliance]{NATO} and {JSON}{FOO} records has not yet been located.[1]",
        ))
        warnings: list[str] = []
        self.assertEqual([], reportctl.validate_report(target, warnings))
        self.assertIn("[alliance]{NATO}", reportctl.reader_text(target))


class JsonSchemaSyncTests(unittest.TestCase):
    def test_published_schemas_match_validator_vocabularies(self) -> None:
        assessment = json.loads((ROOT / "schema" / "assessment.schema.json").read_text())
        ledger = json.loads((ROOT / "schema" / "sources-ledger.schema.json").read_text())
        props = assessment["properties"]
        source = props["sources"]["items"]["properties"]
        claim = props["claims"]["items"]["properties"]
        pairs = [
            (props["report"]["properties"]["mode"]["enum"], reportctl.RESEARCH_MODES),
            (props["report"]["properties"]["status"]["enum"], reportctl.REPORT_STATUS),
            (source["source_type"]["enum"], reportctl.SOURCE_TYPES),
            (source["access"]["enum"], reportctl.ACCESS),
            (source["directness"]["enum"], reportctl.DIRECTNESS),
            (source["disposition"]["enum"], reportctl.SOURCE_DISPOSITIONS),
            (claim["kind"]["enum"], reportctl.CLAIM_KINDS),
            (claim["status"]["enum"], reportctl.CLAIM_STATUS),
            (claim["underlying_status"]["enum"], reportctl.CLAIM_STATUS),
            (claim["importance"]["enum"], reportctl.IMPORTANCE),
            (props["evidence"]["items"]["properties"]["kind"]["enum"], reportctl.EVIDENCE_KINDS),
            (props["searches"]["items"]["properties"]["purpose"]["enum"], reportctl.SEARCH_PURPOSES),
            (props["coverage_gaps"]["items"]["anyOf"][1]["properties"]["kind"]["enum"], reportctl.GAP_KINDS),
        ]
        for published, expected in pairs:
            with self.subTest(expected=sorted(expected)):
                self.assertEqual(sorted(expected), sorted(published))
        audit = props["review"]["properties"]["entailment_audit"]["properties"]["items"]["items"]["properties"]
        self.assertEqual(sorted(reportctl.EXCERPT_VERDICTS), sorted(v for v in audit["excerpt_verdict"]["enum"] if v))
        self.assertEqual(sorted(reportctl.PROSE_VERDICTS), sorted(v for v in audit["prose_verdict"]["enum"] if v))
        self.assertEqual(reportctl.ID_RE.pattern, claim["id"]["pattern"])
        self.assertIn("snapshots", ledger["properties"]["sources"]["items"]["properties"])

    def test_fixture_satisfies_required_top_level_schema_fields(self) -> None:
        schema = json.loads((ROOT / "schema" / "assessment.schema.json").read_text())
        fixture = json.loads((FIXTURE / "assessment.json").read_text())
        for key in schema["required"]:
            self.assertIn(key, fixture)
        for claim in fixture["claims"]:
            for key in schema["properties"]["claims"]["items"]["required"]:
                self.assertIn(key, claim)


class CalibrationTextTests(unittest.TestCase):
    def test_small_samples_are_labelled(self) -> None:
        rows = [{"report": "r", "hypothesis": "H1", "statement": "s", "central": 0.7, "low": 0.6, "high": 0.8, "status": "resolved", "outcome": "true", "outcome_value": 1}]
        self.assertIn("too few to distinguish skill from luck", reportctl.calibration_text(rows))


if __name__ == "__main__":
    unittest.main()
