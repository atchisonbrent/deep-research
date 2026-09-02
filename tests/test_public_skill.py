from __future__ import annotations

import re
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "deep-research" / "SKILL.md"
RUBRIC = SKILL.parent / "references" / "reliability-rubric.md"
MODES = SKILL.parent / "references" / "research-modes.md"
MODES_DIR = SKILL.parent / "references" / "modes"


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
            "never silently advance the old cutoff",
            "references/modes/readme.md",
            "the mode file is the contract, not a suggestion",
            "add-evidence --help",
            "validate --help | grep -q -- --strict",
            "$framework/methodology.md",
            "$framework/schema.md",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, lowered)

        self.assertNotIn("/users/batchison", lowered)
        self.assertNotIn("skills/research/grounded-citations/scripts/sources.py", lowered)
        # Private, deployment-specific skills must not be named in the public skill.
        for private_skill in ("quota-aware-independent-review", "structured-agent-handoff", "safe-repository-automation"):
            self.assertNotIn(private_skill, lowered)
        # Comparative-analysis mechanics belong in the mode file, not the spine.
        self.assertNotIn("pre-tax teaser", lowered)
        self.assertLess(len(body.split()), 3600, "SKILL.md spine should stay compact; mode detail belongs in references/modes/")

    def test_public_references_cover_modes_and_reliability(self) -> None:
        pointer = MODES.read_text(encoding="utf-8").lower()
        self.assertIn("modes/readme.md", pointer)
        readme = (MODES_DIR / "README.md").read_text(encoding="utf-8").lower()
        for mode in ("general", "event-assessment", "historical-analysis", "technology-landscape", "state-of-practice", "market-analysis", "company-research", "entity-background", "release-forecast", "policy-analysis", "legal-regulatory", "scientific-synthesis", "security-incident", "comparative-analysis", "product-landscape", "due-diligence"):
            with self.subTest(mode=mode):
                self.assertIn(f"[{mode}.md]({mode}.md)", readme)
                self.assertTrue((MODES_DIR / f"{mode}.md").is_file())
        comparative = (MODES_DIR / "comparative-analysis.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "product-buying-research",
            "no viable candidate within the comparison class",
            "common-basis value",
            "justified `n/a`",
            "unresolved gap",
            "assessment.json.coverage_gaps",
            "insufficient evidence to rank",
            "one shared, mutually comparable basis",
            "declared baseline",
            "never rank a pre-tax teaser against an all-in protected total",
            "exclude an option when unresolved identity",
            "never rank a measured value against silence",
            "proxy-only cells are not secretly evidence",
            "a shared table can still be asymmetric",
            "lineage.supersedes",
            "lineage.superseded_by",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, comparative)
        entity = (MODES_DIR / "entity-background.md").read_text(encoding="utf-8").lower()
        self.assertIn("does not cover private individuals", entity)
        legal = (MODES_DIR / "legal-regulatory.md").read_text(encoding="utf-8").lower()
        self.assertIn("not legal advice", legal)
        rubric = RUBRIC.read_text(encoding="utf-8").lower()
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
        for mode_file in MODES_DIR.glob("*.md"):
            for link in re.findall(r"\]\(([a-z-]+\.md)\)", mode_file.read_text(encoding="utf-8")):
                self.assertTrue((MODES_DIR / link).is_file(), f"{mode_file.name} -> {link}")
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
