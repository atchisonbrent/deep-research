from __future__ import annotations

import re
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "deep-research" / "SKILL.md"
RUBRIC = SKILL.parent / "references" / "reliability-rubric.md"
MODES = SKILL.parent / "references" / "research-modes.md"


class PublicDeepResearchSkillTests(unittest.TestCase):
    def test_skill_is_publicly_self_contained(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        frontmatter, body = text[4:].split("\n---\n", 1)

        self.assertRegex(frontmatter, r"(?m)^name: deep-research$")
        description = next(line.removeprefix("description: ") for line in frontmatter.splitlines() if line.startswith("description: "))
        self.assertGreaterEqual(len(description), 1)
        self.assertLessEqual(len(description), 1024)
        self.assertTrue(description.startswith("Use for "))
        self.assertRegex(frontmatter, r"(?m)^license: MIT$")
        self.assertRegex(frontmatter, r"(?m)^compatibility: .*Claude Code.*Codex.*OpenCode.*$")

        lowered = body.lower()
        required = (
            "technology, markets, companies",
            "independence_group",
            "probability ranges",
            "strongest credible alternative",
            "search results are discovery, not evidence",
            "unknown author history is not low reliability",
            "add-quote --from-file",
            "render-sources",
            "scan-sensitive",
            "expected visibility",
            "publishing report contents publicly requires explicit user intent",
            "never rank a pre-tax teaser against an all-in protected total",
            "exclude an option when unresolved identity",
            "never silently advance the old cutoff",
            "$framework/methodology.md",
            "$framework/schema.md",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, lowered)

        self.assertNotIn("/users/batchison", lowered)
        self.assertNotIn("skills/research/grounded-citations/scripts/sources.py", lowered)

    def test_public_references_cover_modes_and_reliability(self) -> None:
        modes = MODES.read_text(encoding="utf-8").lower()
        rubric = RUBRIC.read_text(encoding="utf-8").lower()
        for phrase in (
            "technology landscape",
            "market analysis",
            "company research",
            "release forecast",
            "scientific synthesis",
            "product landscape",
            "due diligence",
            "test simultaneous fit",
            "normalize decision-grade cost",
            "rerun the eligibility gate, workload fit, normalized totals, and ranking",
        ):
            self.assertIn(phrase, modes)

        self.assertIn("## comparative analysis", modes)
        self.assertIn("## product landscape", modes)
        comparative = modes.split("## comparative analysis", 1)[1].split("## product landscape", 1)[0]
        self.assertIn("product-buying-research", comparative)
        self.assertIn("no viable candidate within the comparison class", comparative)
        self.assertIn("lineage.supersedes", comparative)
        self.assertIn("lineage.superseded_by", comparative)
        self.assertNotIn("mark the old verdict superseded", SKILL.read_text(encoding="utf-8").lower())
        for phrase in (
            "not a points system",
            "particular claim",
            "employer prestige alone is not author evidence",
            "directness does not imply neutrality",
            "circular citation",
        ):
            self.assertIn(phrase, rubric)

    def test_skill_links_are_relative_and_present(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for path in re.findall(r"`(references/[^`]+\.md)`", text):
            self.assertTrue((SKILL.parent / path).is_file(), path)
        codex = (SKILL.parent / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("display_name: Deep Research", codex)
        self.assertIn("allow_implicit_invocation: true", codex)

    def test_release_contract_and_skill_version_are_synchronized(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        version = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
        manifest = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")

        self.assertRegex(skill, rf'(?m)^  version: "{re.escape(version)}" # x-release-version$')
        self.assertEqual(version, manifest["version"])
        self.assertEqual(1, manifest["schema_version"])
        self.assertIn("python3 tools/release.py plan", workflow)
        self.assertIn("python3 tools/release.py apply", workflow)
        self.assertIn("gh release create", workflow)
        self.assertNotIn("release-please-action", workflow)
        self.assertTrue((ROOT / "tools" / "release.py").is_file())
        self.assertTrue((ROOT / "RELEASING.md").is_file())
        self.assertTrue((ROOT / "CHANGELOG.md").is_file())

    def test_repository_publishes_a_real_example_not_an_empty_reports_shelf(self) -> None:
        example = ROOT / "examples" / "iran-war-six-month-assessment"
        for filename in ("report.md", "assessment.json", "sources-ledger.json"):
            self.assertTrue((example / filename).is_file(), filename)
        self.assertFalse((ROOT / "reports" / "index.md").exists())


if __name__ == "__main__":
    unittest.main()
