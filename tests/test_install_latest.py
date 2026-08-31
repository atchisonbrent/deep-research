from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import shutil
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_latest", ROOT / "tools" / "install-latest.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load tools/install-latest.py")
install_latest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = install_latest
SPEC.loader.exec_module(install_latest)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class InstallLatestTests(unittest.TestCase):
    def release_checkout(self, root: Path, tag: str) -> Path:
        checkout = root / tag
        source = checkout / "skills" / "deep-research"
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text("skill\n", encoding="utf-8")
        tools = checkout / "tools"
        tools.mkdir()
        shutil.copy2(ROOT / "tools" / "install-skill.py", tools / "install-skill.py")
        subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=checkout, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=checkout, check=True)
        subprocess.run(["git", "add", "."], cwd=checkout, check=True)
        subprocess.run(["git", "commit", "-qm", "release"], cwd=checkout, check=True)
        subprocess.run(["git", "tag", "-a", tag, "-m", tag], cwd=checkout, check=True)
        return checkout

    def test_latest_release_uses_published_release_tag(self) -> None:
        payload = json.dumps({"tag_name": "v1.2.3"}).encode()
        with mock.patch.object(install_latest.urllib.request, "urlopen", return_value=Response(payload)):
            self.assertEqual("v1.2.3", install_latest.latest_release_tag("example/project"))

    def test_latest_release_rejects_non_semver_tag(self) -> None:
        payload = json.dumps({"tag_name": "nightly"}).encode()
        with mock.patch.object(install_latest.urllib.request, "urlopen", return_value=Response(payload)):
            with self.assertRaises(install_latest.BootstrapError):
                install_latest.latest_release_tag("example/project")

    def test_release_checkout_is_versioned_and_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=source, check=True)
            (source / "README.md").write_text("release\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=source, check=True)
            subprocess.run(["git", "commit", "-qm", "feat: release"], cwd=source, check=True)
            subprocess.run(["git", "tag", "-a", "v1.2.3", "-m", "v1.2.3"], cwd=source, check=True)

            installs = root / "installs"
            first = install_latest.ensure_release_checkout(str(source), installs, "v1.2.3")
            second = install_latest.ensure_release_checkout(str(source), installs, "v1.2.3")
            self.assertEqual(first, second)
            self.assertEqual("v1.2.3", install_latest.run("git", "describe", "--tags", "--exact-match", "HEAD", cwd=first))
            self.assertEqual(installs / "releases" / "v1.2.3", first)

    def test_cached_checkout_rejects_a_moved_remote_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=source, check=True)
            (source / "value.txt").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=source, check=True)
            subprocess.run(["git", "commit", "-qm", "one"], cwd=source, check=True)
            subprocess.run(["git", "tag", "-a", "v1.0.0", "-m", "v1.0.0"], cwd=source, check=True)
            installs = root / "installs"
            install_latest.ensure_release_checkout(str(source), installs, "v1.0.0")

            (source / "value.txt").write_text("two\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=source, check=True)
            subprocess.run(["git", "commit", "-qm", "two"], cwd=source, check=True)
            subprocess.run(["git", "tag", "-fa", "v1.0.0", "-m", "moved"], cwd=source, check=True)
            with self.assertRaises(install_latest.BootstrapError):
                install_latest.ensure_release_checkout(str(source), installs, "v1.0.0")

    def test_dirty_cached_release_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = root / "releases" / "v1.0.0"
            checkout.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
            subprocess.run(["git", "remote", "add", "origin", "https://example.invalid/repo.git"], cwd=checkout, check=True)
            (checkout / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            with mock.patch.object(
                install_latest, "remote_tag_commit", return_value="0" * 40
            ):
                with self.assertRaisesRegex(
                    install_latest.BootstrapError, "release checkout is dirty"
                ):
                    install_latest.ensure_release_checkout(
                        "https://example.invalid/repo.git", root, "v1.0.0"
                    )

    def test_main_defaults_to_all_consumers_and_install_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary)
            tool = checkout / "tools" / "install-skill.py"
            tool.parent.mkdir()
            tool.write_text("# test\n", encoding="utf-8")
            with (
                mock.patch.object(install_latest, "latest_release_tag", return_value="v1.2.3"),
                mock.patch.object(install_latest, "ensure_release_checkout", return_value=checkout),
                mock.patch.object(install_latest.subprocess, "run") as called,
            ):
                called.return_value.returncode = 0
                self.assertEqual(0, install_latest.main(["--install-root", temporary]))
            command = called.call_args.args[0]
            self.assertEqual("install", command[2])
            for consumer in install_latest.CONSUMER_PATHS:
                self.assertIn(consumer, command)

    def test_repository_identity_is_derived_from_remote(self) -> None:
        self.assertEqual(
            "owner/project",
            install_latest.repository_from_remote("https://github.com/owner/project.git"),
        )
        self.assertEqual(
            "owner/project",
            install_latest.repository_from_remote("git@github.com:owner/project.git"),
        )
        with self.assertRaises(install_latest.BootstrapError):
            install_latest.repository_from_remote("https://example.com/owner/project.git")

    def test_empty_xdg_data_home_uses_home_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            with mock.patch.dict(install_latest.os.environ, {"XDG_DATA_HOME": ""}):
                self.assertEqual(
                    home / ".local" / "share" / "deep-research",
                    install_latest.default_install_root(home),
                )

    def test_project_argument_requires_project_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(install_latest.BootstrapError):
                install_latest.main(["check", "--project", temporary])

    def test_check_and_uninstall_use_installed_release_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout = self.release_checkout(root, "v1.2.3")
            home = root / "home"
            subprocess.run(
                [
                    sys.executable,
                    str(checkout / "tools" / "install-skill.py"),
                    "install",
                    "--consumer",
                    "claude",
                    "--home",
                    str(home),
                ],
                check=True,
            )
            with mock.patch.object(
                install_latest.urllib.request,
                "urlopen",
                side_effect=AssertionError("network should not be used"),
            ):
                self.assertEqual(0, install_latest.main(["check", "--consumer", "claude", "--home", str(home)]))
                self.assertEqual(0, install_latest.main(["uninstall", "--consumer", "claude", "--home", str(home)]))
            self.assertFalse((home / ".claude" / "skills" / "deep-research").exists())

    def test_high_level_install_upgrades_from_one_release_to_another(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.release_checkout(root, "v1.0.0")
            second = self.release_checkout(root, "v1.1.0")
            (first / "skills" / "deep-research" / "SKILL.md").write_text("first\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=first, check=True)
            subprocess.run(["git", "commit", "-qm", "first content"], cwd=first, check=True)
            subprocess.run(["git", "tag", "-fa", "v1.0.0", "-m", "v1.0.0"], cwd=first, check=True)
            (second / "skills" / "deep-research" / "SKILL.md").write_text("second\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=second, check=True)
            subprocess.run(["git", "commit", "-qm", "second content"], cwd=second, check=True)
            subprocess.run(["git", "tag", "-fa", "v1.1.0", "-m", "v1.1.0"], cwd=second, check=True)
            home = root / "home"
            with (
                mock.patch.object(install_latest, "repository_from_remote", return_value="example/project"),
                mock.patch.object(install_latest, "ensure_release_checkout", side_effect=[first, second]),
            ):
                self.assertEqual(0, install_latest.main(["--tag", "v1.0.0", "--consumer", "claude", "--home", str(home)]))
                self.assertEqual("first\n", (home / ".claude/skills/deep-research/SKILL.md").read_text())
                self.assertEqual(0, install_latest.main(["--tag", "v1.1.0", "--consumer", "claude", "--home", str(home)]))
                self.assertEqual("second\n", (home / ".claude/skills/deep-research/SKILL.md").read_text())

    def test_check_without_installation_is_offline_and_reports_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(
                install_latest.urllib.request,
                "urlopen",
                side_effect=AssertionError("network should not be used"),
            ):
                self.assertEqual(
                    1,
                    install_latest.main(
                        ["check", "--consumer", "claude", "--home", temporary]
                    ),
                )


if __name__ == "__main__":
    unittest.main()
