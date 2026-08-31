from __future__ import annotations

import re
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
        self.assertRegex(frontmatter, r"(?m)^description: .{1,60}\.$")
        self.assertRegex(frontmatter, r"(?m)^license: MIT$")

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
        ):
            self.assertIn(phrase, modes)
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


if __name__ == "__main__":
    unittest.main()
