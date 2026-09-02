from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import unittest
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reportctl", ROOT / "tools" / "reportctl.py")
assert SPEC and SPEC.loader
reportctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reportctl)


class ReportCtlTests(unittest.TestCase):
    def copy_fixture(self, temporary: str) -> Path:
        fixture = ROOT / "tests" / "fixtures" / "minimal-report"
        target = Path(temporary) / "minimal-report"
        shutil.copytree(fixture, target)
        return target

    def test_repository_with_no_reports_has_stable_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(reportctl, "REPORTS", Path(temporary) / "reports"):
                self.assertIn("_No reports yet._", reportctl.index_text())

    def test_init_creates_expected_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reports = Path(temporary) / "reports"
            with mock.patch.object(reportctl, "REPORTS", reports):
                directory = reportctl.init_report(
                    Namespace(slug="test-event", title="Test event", cutoff="2026-08-31T10:49:00Z", mode="general", domain="testing")
                )
            self.assertEqual(reports / "2026" / "08" / "test-event", directory)
            self.assertTrue((directory / "report.md").is_file())
            self.assertTrue((directory / "assessment.json").is_file())
            self.assertTrue((directory / "sources-ledger.json").is_file())
            self.assertTrue((directory / "evidence").is_dir())
            assessment = json.loads((directory / "assessment.json").read_text())
            self.assertEqual("general", assessment["report"]["mode"])
            self.assertEqual("testing", assessment["report"]["domain"])

    def test_cli_root_targets_a_separate_report_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "reportctl.py"),
                    "--root",
                    str(root),
                    "init",
                    "--slug",
                    "consumer-report",
                    "--title",
                    "Consumer report",
                    "--mode",
                    "technology-landscape",
                    "--domain",
                    "artificial-intelligence",
                    "--cutoff",
                    "2026-08-31T10:49:00Z",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn(str(root / "reports" / "2026" / "08" / "consumer-report"), result.stdout)
            self.assertTrue((root / "reports" / "2026" / "08" / "consumer-report" / "assessment.json").is_file())

    def test_validator_rejects_placeholder_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reports = Path(temporary) / "reports"
            with mock.patch.object(reportctl, "REPORTS", reports):
                directory = reportctl.init_report(
                    Namespace(slug="test-event", title="Test event", cutoff="2026-08-31T10:49:00Z", mode="general", domain="testing")
                )
            errors = reportctl.validate_report(directory)
            self.assertTrue(any("assessment.sources" in error for error in errors))
            self.assertTrue(any("claims" in error for error in errors))

    def test_validator_rejects_source_ledger_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["sources"][0]["url"] = "https://wrong.example/source"
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            errors = reportctl.validate_report(target)
            self.assertIn("source 1 URL differs from citation ledger", errors)

    def test_self_contained_source_registration_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            source_id = reportctl.add_source(target, "https://example.org/new", "New source", "2026-08-31")
            duplicate_id = reportctl.add_source(target, "https://example.org/new", "New source", "2026-08-31")
            self.assertEqual(source_id, duplicate_id)
            ledger = json.loads((target / "sources-ledger.json").read_text())
            self.assertEqual(2, len(ledger["sources"]))

    def test_render_sources_omits_consulted_but_uncited_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            reportctl.add_source(target, "https://example.org/uncited", "Uncited source", "2026-08-31")
            assessment = json.loads((target / "assessment.json").read_text())
            second = dict(assessment["sources"][0])
            second.update({"id": 2, "url": "https://example.org/uncited", "title": "Uncited source"})
            assessment["sources"].append(second)
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            reportctl.render_sources(target)
            rendered = (target / "report.md").read_text()
            self.assertIn("[1] https://example.com/source", rendered)
            self.assertNotIn("[2] https://example.org/uncited", rendered)
            self.assertEqual([], reportctl.validate_report(target))

    def test_self_contained_quote_requires_verbatim_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            evidence = Path(temporary) / "source.txt"
            evidence.write_text("The exact evidence sentence appears here.\n")
            reportctl.add_quote(target, 1, "The exact evidence sentence appears here.", evidence)
            ledger = json.loads((target / "sources-ledger.json").read_text())
            self.assertEqual("The exact evidence sentence appears here.", ledger["sources"][0]["quotes"][-1]["text"])
            with self.assertRaisesRegex(ValueError, "not found verbatim"):
                reportctl.add_quote(target, 1, "A fabricated quotation.", evidence)

    def test_validator_rejects_narrow_single_group_indirect_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["sources"][0]["directness"] = "secondary"
            assessment["claims"][0]["confidence"] = [0.9, 0.99]
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            errors = reportctl.validate_report(target)
            self.assertTrue(any("single-group indirect evidence" in error for error in errors))

    def test_validator_rejects_evidence_source_outside_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            ledger = json.loads((target / "sources-ledger.json").read_text())
            second = dict(assessment["sources"][0])
            second.update({"id": 2, "url": "https://example.org/second", "title": "Second source"})
            assessment["sources"].append(second)
            assessment["evidence"][0]["source_id"] = 2
            ledger["sources"].append({"id": 2, "url": "https://example.org/second", "title": "Second source", "accessed": "2026-08-31"})
            report = (target / "report.md").read_text().replace("## Sources", "The second source provides context.[2]\n\n## Sources").replace("[1] https://", "[2] https://example.org/second — Second source\n[1] https://")
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            (target / "sources-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
            (target / "report.md").write_text(report)
            errors = reportctl.validate_report(target)
            self.assertIn("evidence[0].source_id must be listed by supported claim C1", errors)

    def test_table_body_rows_are_part_of_citation_coverage(self) -> None:
        units = reportctl.prose_units("| Candidate | Metric | Basis |\n|---|---|---|\n| Alpha | 123 units | common basis [1] |")
        self.assertEqual(1, len(units))
        self.assertIn("123 units", units[0])

    def test_table_header_rows_are_not_citation_units(self) -> None:
        markdown = "| Candidate | Price basis | Legroom |\n|---|---|---|\n| M5 | all-in refundable | 36.2 in [1] |"
        units = reportctl.prose_units(markdown)
        self.assertEqual(1, len(units))
        self.assertNotIn("Candidate", units[0])
        self.assertNotIn("Candidate | Price basis | Legroom", reportctl.prose_sentences(markdown))

    def test_wrapped_list_item_is_one_citation_unit(self) -> None:
        markdown = "- The first list item begins here and\n  continues on an indented line with its citation.[1]\n- Second item stands alone with enough words.[2]\n"
        units = reportctl.prose_units(markdown)
        self.assertEqual(2, len(units))
        self.assertTrue(all(reportctl.citation_scope_valid(unit) for unit in units))

    def test_abbreviations_do_not_split_sentences(self) -> None:
        unit = "U.S. forces struck the site, e.g. the depot.[1] Iran Inc. responded with drones.[2]"
        self.assertEqual(
            ["U.S. forces struck the site, e.g. the depot.[1]", "Iran Inc. responded with drones.[2]"],
            reportctl.split_cited_sentences(unit),
        )
        self.assertTrue(reportctl.citation_scope_valid(unit))

    def test_closing_quote_before_citation_ends_sentence(self) -> None:
        unit = 'The minister said "we are done."[1] Analysts disagreed with that framing.'
        self.assertFalse(reportctl.citation_scope_valid(unit))

    def test_one_citation_can_cover_a_single_source_paragraph(self) -> None:
        markdown = "The first sentence comes from the source.\nThe second sentence does too.[1]\n"
        units = reportctl.prose_units(markdown)
        self.assertEqual(1, len(units))
        self.assertTrue(reportctl.citation_scope_valid(units[0]))

    def test_nonterminal_single_citation_does_not_cover_paragraph(self) -> None:
        unit = "The first fact is cited.[1] This uncited claim follows."
        self.assertFalse(reportctl.citation_scope_valid(unit))

    def test_mixed_source_paragraph_requires_each_sentence_cited(self) -> None:
        valid = "The first claim is supported.[1] The second uses another source.[2]"
        invalid = "The first claim is supported.[1] The second is uncited. A third is supported.[2]"
        self.assertTrue(reportctl.citation_scope_valid(valid))
        self.assertFalse(reportctl.citation_scope_valid(invalid))

    def test_blank_line_creates_a_new_citation_unit(self) -> None:
        markdown = "This paragraph has evidence.[1]\n\nThis paragraph has no citation.\n"
        units = reportctl.prose_units(markdown)
        self.assertEqual(2, len(units))
        self.assertRegex(units[0], reportctl.CITE_RE)
        self.assertNotRegex(units[1], reportctl.CITE_RE)

    def test_orphan_report_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            reports = Path(temporary) / "reports"
            orphan = reports / "wrong" / "place"
            orphan.mkdir(parents=True)
            (orphan / "report.md").write_text("orphan")
            with mock.patch.object(reportctl, "ROOT", Path(temporary)), mock.patch.object(reportctl, "REPORTS", reports):
                self.assertTrue(reportctl.orphan_report_errors())

    def test_sensitive_filename_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".env").write_text("EXAMPLE=value")
            with mock.patch.object(reportctl, "ROOT", root):
                self.assertEqual(["forbidden sensitive filename: .env"], reportctl.sensitive_content_errors())

    def test_reviewed_status_requires_passed_independent_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["report"]["status"] = "reviewed"
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            report = (target / "report.md").read_text().replace("status: draft", "status: reviewed")
            (target / "report.md").write_text(report)
            self.assertIn(
                "reviewed reports require review.independent_review=passed",
                reportctl.validate_report(target),
            )

    def test_cutoff_cannot_postdate_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["report"]["created"] = "2026-08-30T00:00:00Z"
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            self.assertIn("report.cutoff must not be after report.created", reportctl.validate_report(target))

    def test_minimal_fixture_validates(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "minimal-report"
        self.assertEqual([], reportctl.validate_report(fixture))

    def test_descriptive_research_can_have_no_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["report"]["mode"] = "technology-landscape"
            assessment["report"]["domain"] = "artificial-intelligence"
            assessment["hypotheses"] = []
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            report = (target / "report.md").read_text().replace("mode: general", "mode: technology-landscape").replace("domain: testing", "domain: artificial-intelligence")
            (target / "report.md").write_text(report)
            self.assertEqual([], reportctl.validate_report(target))

    def test_release_forecast_requires_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["report"]["mode"] = "release-forecast"
            assessment["report"]["domain"] = "artificial-intelligence"
            assessment["hypotheses"] = []
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            report = (target / "report.md").read_text().replace("mode: general", "mode: release-forecast").replace("domain: testing", "domain: artificial-intelligence")
            (target / "report.md").write_text(report)
            self.assertTrue(any("require at least one hypothesis" in error for error in reportctl.validate_report(target)))

    def test_event_assessment_requires_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["report"]["mode"] = "event-assessment"
            assessment["hypotheses"] = []
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            report = (target / "report.md").read_text().replace("mode: general", "mode: event-assessment")
            (target / "report.md").write_text(report)
            self.assertTrue(any("require at least one hypothesis" in error for error in reportctl.validate_report(target)))

    def test_new_modes_are_accepted_and_scaffold_their_sections(self) -> None:
        for mode in ("historical-analysis", "state-of-practice", "entity-background", "legal-regulatory", "security-incident"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                reports = Path(temporary) / "reports"
                with mock.patch.object(reportctl, "REPORTS", reports):
                    directory = reportctl.init_report(Namespace(slug="scaffold", title="Scaffold", cutoff="2026-08-31T10:49:00Z", mode=mode, domain="testing"))
                report = (directory / "report.md").read_text()
                for heading in reportctl.MODE_SECTIONS[mode]:
                    self.assertIn(f"## {heading}", report)
                self.assertIn(f"mode: {mode}", report)
                self.assertTrue(report.rstrip().endswith("## Sources"))

    def test_every_mode_has_a_reference_file_and_matching_sections(self) -> None:
        modes_dir = ROOT / "skills" / "deep-research" / "references" / "modes"
        for mode in sorted(reportctl.RESEARCH_MODES):
            with self.subTest(mode=mode):
                reference = modes_dir / f"{mode}.md"
                self.assertTrue(reference.is_file(), reference)
                text = reference.read_text(encoding="utf-8")
                for heading in ("## Choose this mode when", "## Evidence hierarchy", "## Decomposition pattern", "## Mode gates", "## Output sections", "## Completion criteria", "## Pitfalls"):
                    self.assertIn(heading, text)
                output_block = text.split("## Output sections", 1)[1].split("## Completion criteria", 1)[0]
                listed = [line[2:].strip() for line in output_block.splitlines() if line.startswith("- ")]
                listed = [re.sub(r"\s*\(.*\)$", "", item) for item in listed]
                self.assertEqual(reportctl.MODE_SECTIONS[mode], listed, f"{mode}: reportctl MODE_SECTIONS and reference Output sections have drifted")

    def test_forecast_claim_requires_hypotheses_in_general_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["claims"][0]["kind"] = "forecast"
            assessment["hypotheses"] = []
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            self.assertTrue(any("require at least one hypothesis" in error for error in reportctl.validate_report(target)))

    def test_generic_source_types_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            for source_type in ("technical-documentation", "code-repository", "benchmark", "market-data", "regulatory-filing", "company-communication", "academic-paper", "patent"):
                assessment = json.loads((target / "assessment.json").read_text())
                assessment["sources"][0]["source_type"] = source_type
                (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
                with self.subTest(source_type=source_type):
                    self.assertEqual([], reportctl.validate_report(target))

    def mutate_fixture(self, temporary: str, mutate) -> tuple[list[str], list[str]]:
        target = self.copy_fixture(temporary)
        assessment = json.loads((target / "assessment.json").read_text())
        report = (target / "report.md").read_text()
        assessment, report = mutate(assessment, report)
        (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
        (target / "report.md").write_text(report)
        warnings: list[str] = []
        errors = reportctl.validate_report(target, warnings)
        return errors, warnings

    def test_minimal_fixture_has_no_warnings(self) -> None:
        warnings: list[str] = []
        self.assertEqual([], reportctl.validate_report(ROOT / "tests" / "fixtures" / "minimal-report", warnings))
        self.assertEqual([], warnings)

    def test_timestamps_after_cutoff_are_rejected(self) -> None:
        def mutate(assessment, report):
            assessment["sources"][0]["retrieved_at"] = "2027-01-01"
            assessment["claims"][0]["last_checked"] = "2027-01-01T00:00:00Z"
            assessment["evidence"][0]["captured_at"] = "2027-01-01T00:00:00Z"
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, mutate)
        self.assertIn("sources[0].retrieved_at is after the report cutoff", errors)
        self.assertIn("claims[0].last_checked is after the report cutoff", errors)
        self.assertIn("evidence[0].captured_at is after the report cutoff", errors)

    def test_publication_after_retrieval_is_rejected(self) -> None:
        def mutate(assessment, report):
            assessment["sources"][0]["published_at"] = "2026-09-15"
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, mutate)
        self.assertIn("sources[0].published_at is after retrieved_at", errors)

    def test_date_only_retrieval_on_cutoff_day_is_accepted(self) -> None:
        def mutate(assessment, report):
            assessment["sources"][0]["retrieved_at"] = "2026-08-31"
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, mutate)
        self.assertEqual([], errors)

    def test_snippet_only_sources_cannot_carry_load_bearing_claims(self) -> None:
        def mutate(assessment, report):
            assessment["sources"][0]["access"] = "snippet"
            assessment["sources"][0]["directness"] = "secondary"
            assessment["claims"][0]["confidence"] = [0.5, 0.75]
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, mutate)
        self.assertIn("claims[0] load-bearing claim cannot rest on snippet-only sources", errors)

    def test_status_and_confidence_must_cohere(self) -> None:
        def confirmed_low(assessment, report):
            assessment["claims"][0]["status"] = "confirmed"
            assessment["claims"][0]["confidence"] = [0.1, 0.3]
            return assessment, report

        def unsupported_high(assessment, report):
            assessment["claims"][0]["status"] = "unsupported"
            assessment["claims"][0]["confidence"] = [0.9, 0.95]
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, confirmed_low)
            self.assertTrue(any("status 'confirmed' requires confidence low >= 0.80" in error for error in errors))
        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, unsupported_high)
            self.assertTrue(any("status 'unsupported' requires confidence high <= 0.50" in error for error in errors))

    def test_init_placeholders_are_rejected(self) -> None:
        def mutate(assessment, report):
            assessment["report"]["summary"] = "Replace with the decision-grade verdict."
            report = report.replace("## Uncertainty", "## Competing hypotheses\n\nReplace with calibrated ranges and update triggers.[unverified]\n\n## Uncertainty")
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, mutate)
        self.assertIn("report.summary still contains the init placeholder", errors)
        self.assertIn("report.md still contains init placeholder text", errors)

    def test_frontmatter_title_must_match_assessment(self) -> None:
        def mutate(assessment, report):
            return assessment, report.replace("title: Minimal report", "title: Different title")

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, mutate)
        self.assertIn("report.md frontmatter title differs from assessment.json", errors)

    def test_hypotheses_require_a_named_alternative(self) -> None:
        def mutate(assessment, report):
            assessment["hypotheses"][0]["alternatives"] = []
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, mutate)
        self.assertIn("hypotheses[0].alternatives must name at least one credible alternative", errors)

    def test_unverified_excerpt_is_a_warning_not_an_error(self) -> None:
        def mutate(assessment, report):
            assessment["evidence"][0]["excerpt"] = "This sentence was never verified against the source."
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, warnings = self.mutate_fixture(temporary, mutate)
        self.assertEqual([], errors)
        self.assertEqual(1, len(warnings))
        self.assertIn("evidence[0].excerpt has no verified ledger quote", warnings[0])

    def test_artifact_evidence_does_not_require_a_ledger_quote(self) -> None:
        def mutate(assessment, report):
            assessment["evidence"][0]["kind"] = "artifact"
            assessment["evidence"][0]["excerpt"] = "Figure 2, panel B: measured latency 12 ms at p99"
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, warnings = self.mutate_fixture(temporary, mutate)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_strict_validation_promotes_warnings_to_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["evidence"][0]["excerpt"] = "This sentence was never verified against the source."
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            lenient = subprocess.run([sys.executable, str(ROOT / "tools" / "reportctl.py"), "--root", temporary, "validate", str(target)], text=True, capture_output=True)
            strict = subprocess.run([sys.executable, str(ROOT / "tools" / "reportctl.py"), "--root", temporary, "--json", "validate", "--strict", str(target)], text=True, capture_output=True)
        self.assertEqual(0, lenient.returncode, lenient.stderr)
        self.assertIn("WARNING:", lenient.stderr)
        self.assertEqual(1, strict.returncode)
        payload = json.loads(strict.stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(any(error.startswith("strict: evidence[0].excerpt") for error in payload["errors"]))

    def test_add_evidence_verifies_records_and_links_in_one_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            fetched = Path(temporary) / "fetched.txt"
            fetched.write_text("Preamble.\n\nThe record states that the event occurred on schedule.\n")
            evidence_id = reportctl.add_evidence(
                target, 1, "The record states that the event occurred on schedule.", fetched, ["C1"], "record body", "2026-08-31T10:00:00Z"
            )
            self.assertEqual("E2", evidence_id)
            ledger = json.loads((target / "sources-ledger.json").read_text())
            self.assertEqual("The record states that the event occurred on schedule.", ledger["sources"][0]["quotes"][-1]["text"])
            assessment = json.loads((target / "assessment.json").read_text())
            self.assertEqual("excerpt", assessment["evidence"][1]["kind"])
            self.assertEqual(["C1"], assessment["evidence"][1]["supports_claim_ids"])
            warnings: list[str] = []
            self.assertEqual([], reportctl.validate_report(target, warnings))
            self.assertEqual([], [w for w in warnings if "E2" in w or "evidence[1]" in w])
            with self.assertRaisesRegex(ValueError, "unknown claim id"):
                reportctl.add_evidence(target, 1, "The record states that the event occurred on schedule.", fetched, ["C9"], "record body", "2026-08-31T10:00:00Z")
            with self.assertRaisesRegex(ValueError, "not found verbatim"):
                reportctl.add_evidence(target, 1, "A fabricated quotation.", fetched, ["C1"], "record body", "2026-08-31T10:00:00Z")

    def test_add_evidence_refuses_source_not_listed_by_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            reportctl.add_source(target, "https://example.org/second", "Second source", "2026-08-31")
            fetched = Path(temporary) / "fetched.txt"
            fetched.write_text("Second source text.\n")
            with self.assertRaisesRegex(ValueError, "does not list source 2"):
                reportctl.add_evidence(target, 2, "Second source text.", fetched, ["C1"], "body", "2026-08-31T10:00:00Z")

    def test_sensitive_scan_catches_common_api_key_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "notes.md").write_text(
                "openai sk-proj-" + "a" * 40 + "\n"
                "slack xoxb-1234567890-" + "b" * 24 + "\n"
                "google AIza" + "C" * 35 + "\n"
                "-----BEGIN PGP " + "PRIVATE KEY BLOCK-----\n"
            )
            with mock.patch.object(reportctl, "ROOT", root):
                findings = reportctl.sensitive_content_errors()
        labels = {finding.split(" in ")[0] for finding in findings}
        self.assertEqual({"possible OpenAI-style key", "possible Slack token", "possible Google API key", "possible private key"}, labels)

    def test_json_output_for_validate(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "minimal-report"
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "reportctl.py"), "--root", str(ROOT), "--json", "validate", str(fixture)], text=True, capture_output=True, check=True)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual([], payload["errors"])
        self.assertEqual([], payload["warnings"])

    def make_vault_with_fixture(self, temporary: str) -> tuple[Path, Path]:
        root = Path(temporary)
        report_dir = root / "reports" / "2026" / "08" / "minimal-report"
        shutil.copytree(ROOT / "tests" / "fixtures" / "minimal-report", report_dir)
        return root, report_dir

    def test_supersede_links_lineage_both_ways_and_preserves_predecessor_cutoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, predecessor = self.make_vault_with_fixture(temporary)
            with mock.patch.object(reportctl, "ROOT", root), mock.patch.object(reportctl, "REPORTS", root / "reports"):
                successor = reportctl.supersede_report(predecessor, "minimal-update", "Minimal update", "2026-09-15T00:00:00Z")
                pred = json.loads((predecessor / "assessment.json").read_text())
                succ = json.loads((successor / "assessment.json").read_text())
                self.assertEqual("superseded", pred["report"]["status"])
                self.assertEqual("reports/2026/09/minimal-update", pred["report"]["lineage"]["superseded_by"])
                self.assertEqual("2026-08-31T10:49:00Z", pred["report"]["cutoff"])
                self.assertIn("status: superseded", (predecessor / "report.md").read_text())
                self.assertEqual("reports/2026/08/minimal-report", succ["report"]["lineage"]["supersedes"])
                self.assertEqual(pred["report"]["questions"], succ["report"]["questions"])
                self.assertEqual("general", succ["report"]["mode"])
                # predecessor still validates with its new status
                self.assertEqual([], reportctl.validate_report(predecessor))
                with self.assertRaisesRegex(ValueError, "already superseded"):
                    reportctl.supersede_report(predecessor, "again", "Again", "2026-10-01T00:00:00Z")

    def test_supersede_rejects_non_advancing_cutoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, predecessor = self.make_vault_with_fixture(temporary)
            with mock.patch.object(reportctl, "ROOT", root), mock.patch.object(reportctl, "REPORTS", root / "reports"):
                with self.assertRaisesRegex(ValueError, "later than the predecessor"):
                    reportctl.supersede_report(predecessor, "early", "Early", "2026-08-31T10:49:00Z")
                self.assertEqual("draft", json.loads((predecessor / "assessment.json").read_text())["report"]["status"])

    def test_resolve_hypothesis_records_outcome_without_editing_range(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            reportctl.resolve_hypothesis(target, "H1", "true", "2026-10-01")
            assessment = json.loads((target / "assessment.json").read_text())
            hypothesis = assessment["hypotheses"][0]
            self.assertEqual({"status": "resolved", "outcome": "true", "resolved_at": "2026-10-01", "outcome_value": 1}, hypothesis["resolution"])
            self.assertEqual({"low": 0.55, "central": 0.65, "high": 0.75}, hypothesis["probability"])
            self.assertEqual([], reportctl.validate_report(target))
            with self.assertRaisesRegex(ValueError, "already resolved"):
                reportctl.resolve_hypothesis(target, "H1", "false", "2026-10-02")
            with self.assertRaisesRegex(ValueError, "unknown hypothesis"):
                reportctl.resolve_hypothesis(target, "H9", "true", "2026-10-02")

    def test_calibration_scores_resolved_binary_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, report_dir = self.make_vault_with_fixture(temporary)
            reportctl.resolve_hypothesis(report_dir, "H1", "true", "2026-10-01")
            with mock.patch.object(reportctl, "ROOT", root), mock.patch.object(reportctl, "REPORTS", root / "reports"):
                rows = reportctl.calibration_rows()
                text = reportctl.calibration_text(rows)
            self.assertEqual(1, len(rows))
            self.assertIn("Brier score (central estimates): 0.122", text)
            self.assertIn("Outcomes inside stated interval: 0/1", text)

    def test_structured_coverage_gaps_are_validated(self) -> None:
        def good(assessment, report):
            assessment["coverage_gaps"] = [
                "Legacy free-text gap remains accepted.",
                {"kind": "matrix-cell", "candidate": "Alpha", "criterion": "delivered cost", "description": "No all-in quote at cutoff.", "claim_ids": ["C1"]},
                {"kind": "access", "description": "Paywalled filing not retrieved."},
            ]
            return assessment, report

        def bad(assessment, report):
            assessment["coverage_gaps"] = [
                {"kind": "matrix-cell", "description": "missing candidate and criterion"},
                {"kind": "nonsense", "description": "x"},
                {"kind": "access", "description": "ok", "claim_ids": ["C9"]},
            ]
            return assessment, report

        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, good)
            self.assertEqual([], errors)
        with tempfile.TemporaryDirectory() as temporary:
            errors, _ = self.mutate_fixture(temporary, bad)
        self.assertIn("coverage_gaps[0] matrix-cell gaps must name candidate and criterion", errors)
        self.assertTrue(any("coverage_gaps[1].kind must be one of" in e for e in errors))
        self.assertIn("coverage_gaps[2].claim_ids must reference known claims", errors)


if __name__ == "__main__":
    unittest.main()
