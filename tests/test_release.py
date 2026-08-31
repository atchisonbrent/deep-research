from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_tool", ROOT / "tools" / "release.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load tools/release.py")
release_tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_tool
SPEC.loader.exec_module(release_tool)


class ReleaseToolTests(unittest.TestCase):
    def commit(self, message: str, sha: str = "abcdef012345"):
        return release_tool.Commit(sha=sha, message=message)

    def test_pre_one_feat_and_fix_are_patch_releases(self) -> None:
        current = release_tool.Version.parse("0.1.0")
        self.assertEqual("patch", release_tool.bump_for(current, [self.commit("feat: capability")]))
        self.assertEqual("patch", release_tool.bump_for(current, [self.commit("fix: bug")]))

    def test_pre_one_breaking_change_is_minor(self) -> None:
        current = release_tool.Version.parse("0.1.9")
        commits = [self.commit("feat!: replace schema")]
        self.assertEqual("minor", release_tool.bump_for(current, commits))
        self.assertEqual(release_tool.Version(0, 2, 0), current.bump("minor"))

    def test_stable_semver_rules(self) -> None:
        current = release_tool.Version.parse("1.4.2")
        self.assertEqual("patch", release_tool.bump_for(current, [self.commit("fix: bug")]))
        self.assertEqual("minor", release_tool.bump_for(current, [self.commit("feat: capability")]))
        self.assertEqual("major", release_tool.bump_for(current, [self.commit("fix: bug\n\nBREAKING CHANGE: contract")]))

    def test_non_release_commits_are_noop(self) -> None:
        commits = [self.commit("docs: clarify"), self.commit("chore: tidy")]
        self.assertIsNone(release_tool.bump_for(release_tool.Version.parse("0.1.0"), commits))

    def test_latest_release_tag_ignores_non_semver_tags(self) -> None:
        with mock.patch.object(
            release_tool,
            "git",
            return_value="v0.1.9\nnot-a-release\nv0.2.0\nv0.1.10",
        ):
            self.assertEqual("v0.2.0", release_tool.latest_release_tag())

    def test_apply_synchronizes_version_files_and_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "skills" / "deep-research" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text('---\nmetadata:\n  version: "0.1.0" # x-release-version\n---\n', encoding="utf-8")
            (root / "version.txt").write_text("0.1.0\n", encoding="utf-8")
            (root / "release.json").write_text('{"schema_version": 1, "version": "0.1.0"}\n', encoding="utf-8")
            (root / "CHANGELOG.md").write_text("# Changelog\n\nIntro.\n\n## [0.1.0] - 2026-08-31\n", encoding="utf-8")
            notes = root / "notes.md"
            plan = release_tool.Plan(
                current=release_tool.Version.parse("0.1.0"),
                next_version=release_tool.Version.parse("0.1.1"),
                bump="patch",
                commits=(self.commit("feat: eager releases"),),
                base_tag="v0.1.0",
            )
            with (
                mock.patch.multiple(
                    release_tool,
                    ROOT=root,
                    VERSION_FILE=root / "version.txt",
                    SKILL_FILE=skill,
                    CHANGELOG_FILE=root / "CHANGELOG.md",
                    MANIFEST_FILE=root / "release.json",
                ),
                mock.patch.dict(
                    release_tool.os.environ,
                    {
                        "GITHUB_SERVER_URL": "https://github.com",
                        "GITHUB_REPOSITORY": "example/deep-research",
                    },
                ),
            ):
                release_tool.apply(plan, notes)

            self.assertEqual("0.1.1", (root / "version.txt").read_text().strip())
            self.assertIn('  version: "0.1.1" # x-release-version', skill.read_text())
            self.assertEqual("0.1.1", json.loads((root / "release.json").read_text())["version"])
            self.assertIn("## [0.1.1]", (root / "CHANGELOG.md").read_text())
            self.assertIn("[0.1.1]: https://github.com/example/deep-research/releases/tag/v0.1.1", (root / "CHANGELOG.md").read_text())
            self.assertIn("eager releases", notes.read_text())


if __name__ == "__main__":
    unittest.main()
