from __future__ import annotations

import importlib.util
import sys
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
    def test_user_install_check_and_uninstall_all_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            args = ["--consumer", "all", "--home", str(home)]
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
            args = ["--consumer", consumers, "--scope", "project", "--project", str(project)]
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


if __name__ == "__main__":
    unittest.main()
