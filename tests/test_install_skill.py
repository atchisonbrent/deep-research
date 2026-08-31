from __future__ import annotations

import importlib.util
import sys
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_skill", ROOT / "tools" / "install-skill.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load tools/install-skill.py")
install_skill = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = install_skill
SPEC.loader.exec_module(install_skill)


class InstallSkillTests(unittest.TestCase):
    def release_source(self, root: Path, tag: str, content: str) -> Path:
        checkout = root / tag
        source = checkout / "skills" / "deep-research"
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text(content, encoding="utf-8")
        tools = checkout / "tools"
        tools.mkdir()
        assert install_skill.__file__ is not None
        shutil.copy2(Path(install_skill.__file__), tools / "install-skill.py")
        subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=checkout, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=checkout, check=True)
        subprocess.run(["git", "add", "."], cwd=checkout, check=True)
        subprocess.run(["git", "commit", "-qm", f"release {tag}"], cwd=checkout, check=True)
        subprocess.run(["git", "tag", "-a", tag, "-m", tag], cwd=checkout, check=True)
        return source

    def test_user_install_check_and_uninstall_all_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            args = ["--consumer", "all", "--home", str(home), "--allow-unreleased"]
            self.assertEqual(0, install_skill.main(["install", *args]))
            self.assertEqual(0, install_skill.main(["check", *args]))
            for consumer in install_skill.CONSUMERS:
                target = install_skill.target_for(consumer, scope="user", home=home, project=None)
                self.assertTrue(target.is_dir())
                self.assertFalse(target.is_symlink())
                self.assertEqual(install_skill.SOURCE.joinpath("SKILL.md").resolve(), (target / "SKILL.md").resolve())
            self.assertEqual(0, install_skill.main(["uninstall", *args]))
            for consumer in install_skill.CONSUMERS:
                target = install_skill.target_for(consumer, scope="user", home=home, project=None)
                self.assertFalse(target.exists())

    def test_project_paths_match_native_discovery_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            consumers = "claude,codex,opencode"
            args = ["--consumer", consumers, "--scope", "project", "--project", str(project), "--allow-unreleased"]
            self.assertEqual(0, install_skill.main(["install", *args]))
            self.assertTrue((project / ".claude/skills/deep-research/SKILL.md").is_symlink())
            self.assertTrue((project / ".agents/skills/deep-research/SKILL.md").is_symlink())
            self.assertTrue((project / ".opencode/skills/deep-research/SKILL.md").is_symlink())

    def test_install_refuses_unmanaged_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = install_skill.target_for("claude", scope="user", home=home, project=None)
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("unmanaged\n", encoding="utf-8")
            with self.assertRaises(install_skill.InstallError):
                install_skill.install_target(target)
            self.assertEqual("unmanaged\n", (target / "SKILL.md").read_text(encoding="utf-8"))

    def test_install_accepts_empty_target_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "deep-research"
            target.mkdir()
            install_skill.install_target(target)
            self.assertTrue((target / "SKILL.md").is_symlink())

    def test_check_detects_misdirected_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = install_skill.target_for("codex", scope="user", home=home, project=None)
            install_skill.install_target(target)
            bad = home / "bad.md"
            bad.write_text("bad\n", encoding="utf-8")
            (target / "SKILL.md").unlink()
            (target / "SKILL.md").symlink_to(bad)
            errors = install_skill.check_target(target)
            self.assertTrue(any("misdirected" in error for error in errors))

    def test_hermes_project_scope_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(install_skill.InstallError):
                install_skill.target_for(
                    "hermes",
                    scope="project",
                    home=Path(temporary),
                    project=Path(temporary),
                )

    def test_install_from_unreleased_checkout_is_rejected_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(install_skill, "exact_release_tag", return_value=None):
                with self.assertRaises(install_skill.InstallError):
                    install_skill.main(["install", "--consumer", "claude", "--home", temporary])

    def test_install_upgrades_links_between_managed_releases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.release_source(root, "v1.0.0", "first\n")
            second = self.release_source(root, "v1.1.0", "second\n")
            target = root / "home" / ".claude" / "skills" / "deep-research"
            with mock.patch.object(install_skill, "SOURCE", first):
                install_skill.install_target(target)
            self.assertEqual("first\n", (target / "SKILL.md").read_text())
            with mock.patch.object(install_skill, "SOURCE", second):
                install_skill.install_target(target)
            self.assertEqual("second\n", (target / "SKILL.md").read_text())
            self.assertEqual(second.resolve(), install_skill.managed_source_root(target))


if __name__ == "__main__":
    unittest.main()
