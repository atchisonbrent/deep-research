from __future__ import annotations

import importlib.util
import json
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
            self.assertEqual("The exact evidence sentence appears here.", ledger["sources"][0]["quotes"][0]["text"])
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

    def test_table_rows_are_part_of_citation_coverage(self) -> None:
        units = reportctl.prose_units("| Metric | 123 units |\n|---|---|")
        self.assertEqual(1, len(units))
        self.assertIn("123 units", units[0])

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
            self.assertIn(
                "release forecasts and forecast claims require at least one hypothesis",
                reportctl.validate_report(target),
            )

    def test_forecast_claim_requires_hypotheses_in_general_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            assessment = json.loads((target / "assessment.json").read_text())
            assessment["claims"][0]["kind"] = "forecast"
            assessment["hypotheses"] = []
            (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
            self.assertIn(
                "release forecasts and forecast claims require at least one hypothesis",
                reportctl.validate_report(target),
            )

    def test_generic_source_types_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_fixture(temporary)
            for source_type in ("technical-documentation", "code-repository", "benchmark", "market-data", "regulatory-filing", "company-communication", "academic-paper", "patent"):
                assessment = json.loads((target / "assessment.json").read_text())
                assessment["sources"][0]["source_type"] = source_type
                (target / "assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
                with self.subTest(source_type=source_type):
                    self.assertEqual([], reportctl.validate_report(target))


if __name__ == "__main__":
    unittest.main()
